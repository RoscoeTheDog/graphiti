"""Configuration validator for Graphiti config files.

Provides multi-level validation (syntax, schema, semantic, cross-field) with
helpful error messages and suggestions.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from pydantic import ValidationError

from mcp_server.unified_config import GraphitiConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """A validation error or warning."""

    level: str  # "ERROR" or "WARNING"
    path: str  # Field path (e.g., "session_tracking.watch_path")
    message: str
    suggestion: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    config: Optional[GraphitiConfig] = None

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def add_error(
        self,
        path: str,
        message: str,
        suggestion: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> None:
        """Add an error to the result."""
        self.errors.append(
            ValidationIssue(
                level="ERROR",
                path=path,
                message=message,
                suggestion=suggestion,
                line=line,
                column=column,
            )
        )
        self.valid = False

    def add_warning(
        self,
        path: str,
        message: str,
        suggestion: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> None:
        """Add a warning to the result."""
        self.warnings.append(
            ValidationIssue(
                level="WARNING",
                path=path,
                message=message,
                suggestion=suggestion,
                line=line,
                column=column,
            )
        )


class ConfigValidator:
    """Validator for Graphiti configuration files."""

    def __init__(self):
        """Initialize the validator."""
        self.logger = logging.getLogger(__name__)

    def validate_syntax(self, file_path: Path) -> ValidationResult:
        """Validate JSON syntax.

        Args:
            file_path: Path to config file

        Returns:
            ValidationResult with syntax errors
        """
        result = ValidationResult(valid=True)

        try:
            with open(file_path, "r") as f:
                json.load(f)
        except FileNotFoundError:
            result.add_error(
                path=str(file_path),
                message=f"Configuration file not found: {file_path}",
                suggestion="Check file path and permissions",
            )
        except json.JSONDecodeError as e:
            result.add_error(
                path=str(file_path),
                message=f"Invalid JSON syntax: {e.msg}",
                suggestion="Check for trailing commas, missing quotes, or unescaped characters",
                line=e.lineno,
                column=e.colno,
            )
        except Exception as e:
            result.add_error(
                path=str(file_path), message=f"Error reading file: {str(e)}"
            )

        return result

    def validate_schema(
        self, file_path: Path, json_data: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate against Pydantic schema.

        Args:
            file_path: Path to config file
            json_data: Optional pre-parsed JSON data

        Returns:
            ValidationResult with schema errors
        """
        result = ValidationResult(valid=True)

        # Load JSON if not provided
        if json_data is None:
            syntax_result = self.validate_syntax(file_path)
            if syntax_result.has_errors:
                return syntax_result

            with open(file_path, "r") as f:
                json_data = json.load(f)

        # Validate with Pydantic
        try:
            config = GraphitiConfig.model_validate(json_data)
            result.config = config
        except ValidationError as e:
            for error in e.errors():
                path = ".".join(str(p) for p in error["loc"])
                message = error["msg"]
                error_type = error["type"]

                # Try to suggest corrections for unknown fields
                suggestion = None
                if error_type == "extra_forbidden":
                    # Extract the unknown field name
                    unknown_field = error["loc"][-1] if error["loc"] else None
                    if unknown_field:
                        # Get valid fields from the schema
                        valid_fields = self._get_valid_fields_for_path(
                            json_data, error["loc"][:-1]
                        )
                        suggested = self._suggest_field_name(
                            str(unknown_field), valid_fields
                        )
                        if suggested:
                            suggestion = f"Did you mean '{suggested}'?"

                result.add_error(
                    path=path, message=message, suggestion=suggestion
                )

        return result

    def validate_semantics(
        self,
        config: GraphitiConfig,
        check_paths: bool = True,
        check_env: bool = True,
    ) -> ValidationResult:
        """Validate semantic constraints.

        Args:
            config: Parsed configuration
            check_paths: Whether to check file paths exist
            check_env: Whether to check environment variables are set

        Returns:
            ValidationResult with semantic errors/warnings
        """
        result = ValidationResult(valid=True, config=config)

        # Validate database URI format
        if config.database.backend == "neo4j" and config.database.neo4j:
            uri = config.database.neo4j.uri
            if not self._validate_uri(uri, ["bolt", "neo4j", "neo4j+s", "neo4j+ssc"]):
                result.add_error(
                    path="database.neo4j.uri",
                    message=f"Invalid Neo4j URI format: {uri}",
                    suggestion="Expected format: bolt://host:port or neo4j://host:port",
                )

            # Check password environment variable
            if check_env and config.database.neo4j.password_env:
                env_var = config.database.neo4j.password_env
                is_set, msg = self._check_env_var(env_var)
                if not is_set:
                    result.add_warning(
                        path="database.neo4j.password_env",
                        message=msg,
                        suggestion=f"Set environment variable: export {env_var}='your-password'",
                    )

        # Validate session tracking paths
        if config.session_tracking.enabled and config.session_tracking.watch_path:
            watch_path = Path(config.session_tracking.watch_path).expanduser()
            if check_paths and not watch_path.exists():
                result.add_warning(
                    path="session_tracking.watch_path",
                    message=f"Path does not exist: {watch_path}",
                    suggestion="Create directory or update path",
                )

        # Validate LLM API key environment variable
        if check_env:
            if config.llm.provider == "openai" and config.llm.openai:
                env_var = config.llm.openai.api_key_env
                is_set, msg = self._check_env_var(env_var)
                if not is_set:
                    result.add_warning(
                        path="llm.openai.api_key_env",
                        message=msg,
                        suggestion=f"Set environment variable: export {env_var}='your-api-key'",
                    )

        # Validate extraction template files
        if config.extraction.preprocessing_prompt:
            self._validate_extraction_template(config, result, check_paths)

        # Validate project_overrides structure
        if config.project_overrides:
            self._validate_project_overrides(config, result, check_paths)

        return result

    def validate_cross_fields(self, config: GraphitiConfig) -> ValidationResult:
        """Validate cross-field constraints.

        Args:
            config: Parsed configuration

        Returns:
            ValidationResult with cross-field errors
        """
        result = ValidationResult(valid=True, config=config)

        # Database backend must have corresponding config
        if config.database.backend == "neo4j" and not config.database.neo4j:
            result.add_error(
                path="database.backend",
                message="Backend is 'neo4j' but no neo4j configuration provided",
                suggestion="Add 'neo4j' section under 'database'",
            )

        # LLM provider must have corresponding config
        if config.llm.provider == "openai" and not config.llm.openai:
            result.add_error(
                path="llm.provider",
                message="Provider is 'openai' but no openai configuration provided",
                suggestion="Add 'openai' section under 'llm'",
            )

        # Session tracking enabled requires watch_path
        if config.session_tracking.enabled and not config.session_tracking.watch_path:
            result.add_error(
                path="session_tracking.enabled",
                message="Session tracking enabled but watch_path is null",
                suggestion="Set 'watch_path' to the directory to monitor",
            )

        return result

    def validate_all(
        self,
        file_path: Path,
        level: str = "full",
        check_paths: bool = True,
        check_env: bool = True,
    ) -> ValidationResult:
        """Run all validations.

        Args:
            file_path: Path to config file
            level: Validation level ("syntax", "schema", "semantic", "full")
            check_paths: Whether to check file paths exist
            check_env: Whether to check environment variables are set

        Returns:
            Combined ValidationResult
        """
        result = ValidationResult(valid=True)

        # Level 1: Syntax
        syntax_result = self.validate_syntax(file_path)
        result.errors.extend(syntax_result.errors)
        result.warnings.extend(syntax_result.warnings)
        if syntax_result.has_errors or level == "syntax":
            result.valid = not result.has_errors
            return result

        # Load JSON for further validation
        with open(file_path, "r") as f:
            json_data = json.load(f)

        # Level 2: Schema
        schema_result = self.validate_schema(file_path, json_data)
        result.errors.extend(schema_result.errors)
        result.warnings.extend(schema_result.warnings)
        result.config = schema_result.config
        if schema_result.has_errors or level == "schema":
            result.valid = not result.has_errors
            return result

        # Level 3: Semantic
        if level in ("semantic", "full") and result.config:
            semantic_result = self.validate_semantics(
                result.config, check_paths=check_paths, check_env=check_env
            )
            result.errors.extend(semantic_result.errors)
            result.warnings.extend(semantic_result.warnings)
            if level == "semantic":
                result.valid = not result.has_errors
                return result

        # Level 4: Cross-field (only in "full" mode)
        if level == "full" and result.config:
            cross_result = self.validate_cross_fields(result.config)
            result.errors.extend(cross_result.errors)
            result.warnings.extend(cross_result.warnings)

        result.valid = not result.has_errors
        return result

    def _suggest_field_name(
        self, unknown_field: str, valid_fields: List[str]
    ) -> Optional[str]:
        """Suggest a field name using fuzzy matching.

        Args:
            unknown_field: The unknown field name
            valid_fields: List of valid field names

        Returns:
            Suggested field name or None
        """
        matches = get_close_matches(unknown_field, valid_fields, n=1, cutoff=0.6)
        return matches[0] if matches else None

    def _get_valid_fields_for_path(
        self, json_data: Dict[str, Any], path: Tuple[Any, ...]
    ) -> List[str]:
        """Get valid field names for a given path in the JSON.

        Args:
            json_data: The JSON data
            path: Path to the object (tuple of keys)

        Returns:
            List of valid field names
        """
        # Navigate to the object at the path
        obj = json_data
        for key in path:
            if isinstance(obj, dict) and key in obj:
                obj = obj[key]
            else:
                return []

        # Get schema for this object
        # For now, return keys from the JSON object itself
        # TODO: Extract from Pydantic model schema
        if isinstance(obj, dict):
            return list(obj.keys())
        return []

    def _validate_uri(self, uri: str, expected_schemes: List[str]) -> bool:
        """Validate URI format.

        Args:
            uri: URI to validate
            expected_schemes: List of expected schemes (e.g., ["bolt", "neo4j"])

        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(uri)
            return parsed.scheme in expected_schemes
        except Exception:
            return False

    def _validate_extraction_template(
        self,
        config: GraphitiConfig,
        result: ValidationResult,
        check_paths: bool,
    ) -> None:
        """Validate extraction preprocessing template.

        Checks if specified template file exists in hierarchy.
        Only validates template files (.md), not inline prompts.

        Args:
            config: Graphiti configuration
            result: ValidationResult to add warnings to
            check_paths: Whether to check file paths exist
        """
        prompt = config.extraction.preprocessing_prompt

        # Skip if disabled
        if not prompt or prompt in (False, None):
            return

        # Check if it's a template file (not inline prompt)
        is_template = (
            prompt.endswith(".md") or "/" in prompt or "\\" in prompt
        )

        if not is_template:
            # Inline prompt - no validation needed
            return

        # Check template exists
        if check_paths:
            from pathlib import Path

            from graphiti_core.template_resolver import TemplateResolver

            # Use current working directory as project root for template resolution
            # In real usage, this would be the directory where graphiti.config.json is loaded from
            project_dir = Path.cwd()
            resolver = TemplateResolver(project_dir=project_dir)

            if not resolver.exists(prompt):
                search_paths = resolver._get_search_paths(prompt)
                search_paths_str = "\n  ".join(str(p) for p in search_paths)

                result.add_warning(
                    path="extraction.preprocessing_prompt",
                    message=f"Template file not found: {prompt}",
                    suggestion=f"Template searched in:\n  {search_paths_str}\n"
                    f"Create template file or use inline prompt instead.",
                )

    def _check_env_var(self, env_var_name: str) -> Tuple[bool, str]:
        """Check if environment variable is set.

        Args:
            env_var_name: Name of environment variable

        Returns:
            Tuple of (is_set, error_message)
        """
        value = os.environ.get(env_var_name)
        if value is None:
            return False, f"Environment variable {env_var_name} not set"
        if value == "":
            return False, f"Environment variable {env_var_name} is empty"
        return True, ""

    def _validate_project_overrides(
        self,
        config: GraphitiConfig,
        result: ValidationResult,
        check_paths: bool,
    ) -> None:
        """Validate project_overrides structure.

        Checks for:
        - Non-overridable sections in overrides (database, daemon, resilience, etc.)
        - Project paths are valid directory paths
        - Semantic validation of override contents

        Args:
            config: Graphiti configuration
            result: ValidationResult to add warnings/errors to
            check_paths: Whether to check project paths exist
        """
        # Non-overridable sections (must match unified_config.py:_validate_override)
        non_overridable = {
            "database", "daemon", "resilience", "mcp_server", "logging",
            "version", "project", "search", "performance"
        }

        for project_path, override in config.project_overrides.items():
            # Convert override to dict to check for non-overridable sections
            override_dict = override.model_dump(exclude_none=True)

            # Check for non-overridable sections
            for section in non_overridable:
                if section in override_dict and override_dict[section] is not None:
                    result.add_warning(
                        path=f"project_overrides.{project_path}.{section}",
                        message=f"Non-overridable section '{section}' in project override (will be ignored)",
                        suggestion=f"Remove '{section}' section from override. "
                        f"Overridable sections: llm, embedder, extraction, session_tracking"
                    )

            # Validate project path format (basic path validation)
            if check_paths:
                from pathlib import Path
                try:
                    # Attempt to create Path object (validates format)
                    path_obj = Path(project_path).expanduser()

                    # Check if path exists (warning only, not error)
                    if not path_obj.exists():
                        result.add_warning(
                            path=f"project_overrides.{project_path}",
                            message=f"Project path does not exist: {project_path}",
                            suggestion="Ensure this is a valid project directory path"
                        )
                except Exception as e:
                    result.add_error(
                        path=f"project_overrides.{project_path}",
                        message=f"Invalid project path format: {str(e)}",
                        suggestion="Use absolute or ~/ path format"
                    )


def format_result(result: ValidationResult, config_path: Path) -> str:
    """Format validation result as human-readable string.

    Args:
        result: Validation result
        config_path: Path to config file

    Returns:
        Formatted string
    """
    lines = []

    if result.valid:
        lines.append(f"[OK] Configuration valid: {config_path}\n")

        if result.config:
            lines.append(f"Schema: graphiti-config v{result.config.version}")
            lines.append(
                f"Database: {result.config.database.backend} "
                f"({result.config.database.neo4j.uri if result.config.database.neo4j else 'N/A'})"
            )
            lines.append(
                f"LLM: {result.config.llm.provider} "
                f"({result.config.llm.default_model})"
            )
            lines.append(
                f"Session Tracking: {'enabled' if result.config.session_tracking.enabled else 'disabled'}"
            )

        if result.has_warnings:
            lines.append(f"\nWarnings: {len(result.warnings)}")
            for warning in result.warnings:
                lines.append(f"\n[WARNING] {warning.path}: {warning.message}")
                if warning.suggestion:
                    lines.append(f"  → {warning.suggestion}")
        else:
            lines.append("\nNo issues found.")
    else:
        lines.append(f"[ERROR] Configuration invalid: {config_path}\n")
        lines.append("Issues found:\n")

        for error in result.errors:
            location = ""
            if error.line and error.column:
                location = f" (line {error.line}, column {error.column})"
            lines.append(f"[ERROR] {error.path}{location}: {error.message}")
            if error.suggestion:
                lines.append(f"  → {error.suggestion}")
            lines.append("")

        for warning in result.warnings:
            lines.append(f"[WARNING] {warning.path}: {warning.message}")
            if warning.suggestion:
                lines.append(f"  → {warning.suggestion}")
            lines.append("")

        lines.append(
            f"Summary: {len(result.errors)} error{'s' if len(result.errors) != 1 else ''}, "
            f"{len(result.warnings)} warning{'s' if len(result.warnings) != 1 else ''}"
        )

    return "\n".join(lines)


def format_result_json(result: ValidationResult) -> str:
    """Format validation result as JSON.

    Args:
        result: Validation result

    Returns:
        JSON string
    """
    data = {
        "valid": result.valid,
        "errors": [
            {
                "level": error.level,
                "path": error.path,
                "message": error.message,
                "suggestion": error.suggestion,
                "line": error.line,
                "column": error.column,
            }
            for error in result.errors
        ],
        "warnings": [
            {
                "level": warning.level,
                "path": warning.path,
                "message": warning.message,
                "suggestion": warning.suggestion,
            }
            for warning in result.warnings
        ],
        "summary": f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)",
    }
    return json.dumps(data, indent=2)


def main() -> int:
    """CLI entry point for config validator.

    Returns:
        Exit code: 0=valid, 1=errors, 2=warnings only, 3=validator error
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Graphiti configuration files"
    )
    parser.add_argument(
        "config_path",
        nargs="?",
        default="./graphiti.config.json",
        help="Path to config file (default: ./graphiti.config.json)",
    )
    parser.add_argument(
        "--level",
        choices=["syntax", "schema", "semantic", "full"],
        default="full",
        help="Validation level (default: full)",
    )
    parser.add_argument(
        "--no-path-check",
        action="store_true",
        help="Skip file path existence checks",
    )
    parser.add_argument(
        "--no-env-check",
        action="store_true",
        help="Skip environment variable checks",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON format (for CI/CD)"
    )

    args = parser.parse_args()

    config_path = Path(args.config_path)
    validator = ConfigValidator()

    try:
        result = validator.validate_all(
            config_path,
            level=args.level,
            check_paths=not args.no_path_check,
            check_env=not args.no_env_check,
        )

        if args.json:
            print(format_result_json(result))
        else:
            print(format_result(result, config_path))

        if result.valid and not result.has_warnings:
            return 0
        elif result.valid and result.has_warnings:
            return 2
        else:
            return 1

    except Exception as e:
        if args.json:
            print(
                json.dumps(
                    {"valid": False, "error": str(e), "summary": "Validator error"}
                )
            )
        else:
            print(f"[ERROR] Validator error: {str(e)}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
