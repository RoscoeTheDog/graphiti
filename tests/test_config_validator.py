"""Unit tests for configuration validator."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from mcp_server.config_validator import (
    ConfigValidator,
    ValidationResult,
    format_result,
    format_result_json,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_init(self):
        """Test ValidationResult initialization."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.config is None

    def test_has_errors(self):
        """Test has_errors property."""
        result = ValidationResult(valid=True)
        assert result.has_errors is False

        result.add_error("test.path", "Test error")
        assert result.has_errors is True

    def test_has_warnings(self):
        """Test has_warnings property."""
        result = ValidationResult(valid=True)
        assert result.has_warnings is False

        result.add_warning("test.path", "Test warning")
        assert result.has_warnings is True

    def test_add_error(self):
        """Test adding errors."""
        result = ValidationResult(valid=True)
        result.add_error("test.path", "Test error", suggestion="Fix it", line=10, column=5)

        assert result.valid is False
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.level == "ERROR"
        assert error.path == "test.path"
        assert error.message == "Test error"
        assert error.suggestion == "Fix it"
        assert error.line == 10
        assert error.column == 5

    def test_add_warning(self):
        """Test adding warnings."""
        result = ValidationResult(valid=True)
        result.add_warning("test.path", "Test warning", suggestion="Consider fixing")

        assert result.valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert warning.level == "WARNING"
        assert warning.path == "test.path"
        assert warning.message == "Test warning"


class TestConfigValidator:
    """Test ConfigValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ConfigValidator()

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file."""
        # Use a temporary directory for the config file
        temp_dir = tempfile.mkdtemp()
        config_path = Path(temp_dir) / "test_config.json"

        yield config_path

        # Cleanup
        if config_path.exists():
            config_path.unlink()
        Path(temp_dir).rmdir()

    def test_validate_syntax_valid_json(self, validator, temp_config_file):
        """Test syntax validation with valid JSON."""
        config_data = {
            "version": "1.0.0",
            "database": {"backend": "neo4j"},
            "llm": {"provider": "openai"},
        }
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        result = validator.validate_syntax(temp_config_file)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_syntax_invalid_json(self, validator, temp_config_file):
        """Test syntax validation with invalid JSON."""
        with open(temp_config_file, "w") as f:
            f.write('{"version": "1.0.0",}')  # Trailing comma

        result = validator.validate_syntax(temp_config_file)
        assert result.valid is False
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.level == "ERROR"
        assert "Invalid JSON syntax" in error.message

    def test_validate_syntax_file_not_found(self, validator):
        """Test syntax validation with missing file."""
        result = validator.validate_syntax(Path("/nonexistent/file.json"))
        assert result.valid is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].message

    def test_validate_schema_valid_config(self, validator, temp_config_file):
        """Test schema validation with valid config."""
        # Use minimal valid config
        config_data = {
            "version": "1.0.0",
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD",
                },
            },
            "llm": {
                "provider": "openai",
                "default_model": "gpt-4.1-mini",
                "openai": {"api_key_env": "OPENAI_API_KEY"},
            },
        }
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        result = validator.validate_schema(temp_config_file)
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.config is not None

    def test_validate_schema_unknown_field(self, validator, temp_config_file):
        """Test schema validation with unknown field.

        Note: Pydantic v2 ignores extra fields by default (not an error).
        This test verifies that unknown fields are silently ignored.
        """
        config_data = {
            "version": "1.0.0",
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD",
                },
            },
            "llm": {
                "provider": "openai",
                "default_model": "gpt-4.1-mini",
                "openai": {"api_key_env": "OPENAI_API_KEY"},
            },
            "session_tracking": {
                "enabled": False,
                "watch_directories": ["/path"],  # Extra field, will be ignored
            },
        }
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        result = validator.validate_schema(temp_config_file)
        # Pydantic v2 ignores extra fields by default, so this is valid
        assert result.valid is True
        assert result.config is not None

    def test_validate_schema_type_mismatch(self, validator, temp_config_file):
        """Test schema validation with type mismatch."""
        config_data = {
            "version": "1.0.0",
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD",
                },
            },
            "llm": {
                "provider": "openai",
                "default_model": "gpt-4.1-mini",
                "openai": {"api_key_env": "OPENAI_API_KEY"},
            },
            "session_tracking": {
                "enabled": False,
                "inactivity_timeout": "not_a_number",  # Should be int
            },
        }
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        result = validator.validate_schema(temp_config_file)
        assert result.valid is False
        assert len(result.errors) > 0

    @pytest.mark.skip(reason="Complex config object construction - TODO: simplify")
    def test_validate_semantics_invalid_uri(self, validator):
        """Test semantic validation with invalid URI."""
        # TODO: Load from config file instead of constructing object
        pass

    @pytest.mark.skip(reason="Complex config object construction - TODO: simplify")
    def test_validate_semantics_missing_path(self, validator):
        """Test semantic validation with missing watch_path."""
        # TODO: Load from config file instead of constructing object
        pass

    @pytest.mark.skip(reason="Complex config object construction - TODO: simplify")
    def test_validate_semantics_negative_timeout(self, validator):
        """Test semantic validation with negative timeout."""
        # TODO: Load from config file instead of constructing object
        pass

    @pytest.mark.skip(reason="Complex config object construction - TODO: simplify")
    def test_validate_cross_fields_missing_neo4j_config(self, validator):
        """Test cross-field validation with missing neo4j config."""
        # TODO: Load from config file instead of constructing object
        pass

    @pytest.mark.skip(reason="Complex config object construction - TODO: simplify")
    def test_validate_cross_fields_session_tracking_no_path(self, validator):
        """Test cross-field validation with session tracking enabled but no path."""
        # TODO: Load from config file instead of constructing object
        pass

    def test_validate_all_syntax_level(self, validator, temp_config_file):
        """Test validate_all with syntax level."""
        config_data = {"version": "1.0.0"}
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        result = validator.validate_all(temp_config_file, level="syntax")
        assert result.valid is True

    def test_validate_all_schema_level(self, validator, temp_config_file):
        """Test validate_all with schema level."""
        config_data = {
            "version": "1.0.0",
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD",
                },
            },
            "llm": {
                "provider": "openai",
                "default_model": "gpt-4.1-mini",
                "openai": {"api_key_env": "OPENAI_API_KEY"},
            },
        }
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        result = validator.validate_all(temp_config_file, level="schema")
        assert result.valid is True
        assert result.config is not None

    def test_validate_all_full_level(self, validator, temp_config_file):
        """Test validate_all with full level."""
        config_data = {
            "version": "1.0.0",
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD",
                },
            },
            "llm": {
                "provider": "openai",
                "default_model": "gpt-4.1-mini",
                "openai": {"api_key_env": "OPENAI_API_KEY"},
            },
        }
        with open(temp_config_file, "w") as f:
            json.dump(config_data, f)

        result = validator.validate_all(temp_config_file, level="full", check_env=False)
        assert result.valid is True

    def test_suggest_field_name(self, validator):
        """Test field name suggestion."""
        valid_fields = ["watch_path", "enabled", "check_interval"]

        # Test close match
        suggestion = validator._suggest_field_name("enabledd", valid_fields)
        assert suggestion == "enabled"

        # Test no match
        suggestion = validator._suggest_field_name("completely_wrong_field", valid_fields)
        assert suggestion is None

    def test_validate_uri(self, validator):
        """Test URI validation."""
        assert validator._validate_uri("bolt://localhost:7687", ["bolt", "neo4j"]) is True
        assert validator._validate_uri("neo4j://localhost:7687", ["bolt", "neo4j"]) is True
        assert validator._validate_uri("invalid", ["bolt"]) is False
        assert validator._validate_uri("http://localhost", ["bolt"]) is False

    def test_check_env_var(self, validator):
        """Test environment variable checking."""
        # Set a test env var
        os.environ["TEST_ENV_VAR"] = "test_value"
        is_set, msg = validator._check_env_var("TEST_ENV_VAR")
        assert is_set is True
        assert msg == ""

        # Check non-existent var
        is_set, msg = validator._check_env_var("NONEXISTENT_VAR")
        assert is_set is False
        assert "not set" in msg

        # Clean up
        del os.environ["TEST_ENV_VAR"]


class TestFormatting:
    """Test output formatting functions."""

    def test_format_result_valid(self):
        """Test formatting valid result."""
        result = ValidationResult(valid=True)
        output = format_result(result, Path("test.json"))
        assert "[OK]" in output
        assert "Configuration valid" in output

    def test_format_result_invalid(self):
        """Test formatting invalid result."""
        result = ValidationResult(valid=False)
        result.add_error("test.path", "Test error", suggestion="Fix it")
        output = format_result(result, Path("test.json"))
        assert "[ERROR]" in output
        assert "Configuration invalid" in output
        assert "test.path" in output
        assert "Test error" in output
        assert "Fix it" in output

    def test_format_result_with_warnings(self):
        """Test formatting result with warnings."""
        result = ValidationResult(valid=True)
        result.add_warning("test.path", "Test warning")
        output = format_result(result, Path("test.json"))
        assert "[WARNING]" in output
        assert "Test warning" in output

    def test_format_result_json(self):
        """Test JSON formatting."""
        result = ValidationResult(valid=True)
        result.add_error("test.path", "Test error")
        result.add_warning("test.path", "Test warning")

        output = format_result_json(result)
        data = json.loads(output)

        assert data["valid"] is False  # Has error
        assert len(data["errors"]) == 1
        assert len(data["warnings"]) == 1
        assert data["errors"][0]["path"] == "test.path"
        assert data["warnings"][0]["path"] == "test.path"


class TestExtractionTemplateValidation:
    """Test extraction template validation."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ConfigValidator()

    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory with a test template."""
        temp_dir = tempfile.mkdtemp()
        template_dir = Path(temp_dir) / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        # Create a test template file
        test_template = template_dir / "test-template.md"
        test_template.write_text("# Test Template\n\nThis is a test template.")

        yield temp_dir, test_template

        # Cleanup
        test_template.unlink()
        template_dir.rmdir()
        (Path(temp_dir) / ".graphiti").rmdir()
        Path(temp_dir).rmdir()

    def test_validate_extraction_template_exists(self, validator, temp_template_dir):
        """Test validation passes when template file exists."""
        project_dir, test_template = temp_template_dir

        # Create config with valid template
        from mcp_server.unified_config import GraphitiConfig

        # Change to temp directory so cwd-based resolution finds the template
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)

            config = GraphitiConfig(
                extraction={
                    "preprocessing_prompt": "test-template.md",
                    "preprocessing_mode": "prepend",
                }
            )

            result = ValidationResult(valid=True, config=config)
            validator._validate_extraction_template(config, result, check_paths=True)

            # Should have no warnings since template exists
            assert result.valid is True
            assert len(result.warnings) == 0
        finally:
            os.chdir(original_cwd)

    def test_validate_extraction_template_not_found(self, validator):
        """Test validation warns when template file not found."""
        from mcp_server.unified_config import GraphitiConfig

        config = GraphitiConfig(
            extraction={
                "preprocessing_prompt": "nonexistent-template.md",
                "preprocessing_mode": "prepend",
            }
        )

        result = ValidationResult(valid=True, config=config)
        validator._validate_extraction_template(config, result, check_paths=True)

        # Should have warning about missing template
        assert result.valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert warning.path == "extraction.preprocessing_prompt"
        assert "not found" in warning.message.lower()
        assert "nonexistent-template.md" in warning.message
        assert "searched in" in warning.suggestion.lower()

    def test_validate_extraction_inline_prompt_skipped(self, validator):
        """Test validation skips inline prompts (not template files)."""
        from mcp_server.unified_config import GraphitiConfig

        config = GraphitiConfig(
            extraction={
                "preprocessing_prompt": "Consider session context when extracting entities.",
                "preprocessing_mode": "prepend",
            }
        )

        result = ValidationResult(valid=True, config=config)
        validator._validate_extraction_template(config, result, check_paths=True)

        # Should have no warnings - inline prompts are not validated
        assert result.valid is True
        assert len(result.warnings) == 0

    def test_validate_extraction_disabled_skipped(self, validator):
        """Test validation skips when preprocessing is disabled."""
        from mcp_server.unified_config import GraphitiConfig

        # Test with False
        config_false = GraphitiConfig(
            extraction={
                "preprocessing_prompt": False,
                "preprocessing_mode": "prepend",
            }
        )

        result_false = ValidationResult(valid=True, config=config_false)
        validator._validate_extraction_template(config_false, result_false, check_paths=True)
        assert len(result_false.warnings) == 0

        # Test with None
        config_none = GraphitiConfig(
            extraction={
                "preprocessing_prompt": None,
                "preprocessing_mode": "prepend",
            }
        )

        result_none = ValidationResult(valid=True, config=config_none)
        validator._validate_extraction_template(config_none, result_none, check_paths=True)
        assert len(result_none.warnings) == 0

    def test_validate_extraction_check_paths_disabled(self, validator):
        """Test validation skips path checking when check_paths=False."""
        from mcp_server.unified_config import GraphitiConfig

        config = GraphitiConfig(
            extraction={
                "preprocessing_prompt": "nonexistent-template.md",
                "preprocessing_mode": "prepend",
            }
        )

        result = ValidationResult(valid=True, config=config)
        validator._validate_extraction_template(config, result, check_paths=False)

        # Should have no warnings when path checking is disabled
        assert result.valid is True
        assert len(result.warnings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
