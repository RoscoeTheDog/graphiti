#!/usr/bin/env python3
"""
Configuration CLI - Manage and inspect Graphiti configuration

Commands:
    graphiti-mcp-config effective         Show effective configuration for a project
    graphiti-mcp-config list-projects     List all projects with overrides
    graphiti-mcp-config set-override      Add/update override for project+key
    graphiti-mcp-config remove-override   Remove specific override or all for project
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from mcp_server.unified_config import GraphitiConfig, normalize_project_path


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output"""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def is_tty() -> bool:
    """Check if stdout is a TTY (for color support)"""
    return sys.stdout.isatty()


def colorize(text: str, color: str) -> str:
    """Apply color to text if TTY, otherwise return plain text"""
    if is_tty():
        return f"{color}{text}{Colors.RESET}"
    return text


def mask_sensitive(key: str, value: Any) -> Any:
    """Mask sensitive values (API keys, passwords, etc.)"""
    sensitive_patterns = ["api_key", "password", "secret", "token"]

    if isinstance(key, str):
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in sensitive_patterns):
            if isinstance(value, str) and value:
                return "***REDACTED***"

    return value


def find_config_file() -> Optional[Path]:
    """Find the Graphiti configuration file.

    Search order:
        1. ./graphiti.config.json (project root)
        2. Platform-specific config directory (v2.1 architecture):
           - Windows: %LOCALAPPDATA%\\Graphiti\\config\\graphiti.config.json
           - macOS: ~/Library/Preferences/Graphiti/graphiti.config.json
           - Linux: ~/.config/graphiti/graphiti.config.json

    Returns:
        Path to config file, or None if not found
    """
    from mcp_server.daemon.paths import get_config_file

    # Try project root first
    project_config = Path("graphiti.config.json")
    if project_config.exists():
        return project_config

    # Try platform-specific config (v2.1 architecture)
    platform_config = get_config_file()
    if platform_config.exists():
        return platform_config

    return None


def _get_nested_value(obj: Any, path: str) -> Any:
    """Get nested value from object using dot notation path"""
    parts = path.split(".")
    current = obj

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)

        if current is None:
            return None

    return current


def _compare_configs(effective_dict: Dict[str, Any], global_dict: Dict[str, Any], path: str = "") -> Dict[str, tuple[Any, Any]]:
    """Recursively compare two config dicts and return differences.

    Args:
        effective_dict: Effective config dictionary
        global_dict: Global config dictionary
        path: Current path in nested structure

    Returns:
        Dictionary mapping paths to (global_value, effective_value) tuples
    """
    differences = {}

    for key, effective_value in effective_dict.items():
        current_path = f"{path}.{key}" if path else key
        global_value = global_dict.get(key)

        # Skip project_overrides section (meta-config)
        if key == "project_overrides":
            continue

        # Recursively compare nested dicts
        if isinstance(effective_value, dict) and isinstance(global_value, dict):
            nested_diffs = _compare_configs(effective_value, global_value, current_path)
            differences.update(nested_diffs)
        # Compare values
        elif effective_value != global_value:
            differences[current_path] = (global_value, effective_value)

    return differences


def _format_value(key: str, value: Any, indent: int = 0) -> str:
    """Format a config value for display"""
    indent_str = "  " * indent

    # Mask sensitive values
    display_value = mask_sensitive(key, value)

    # Format based on type
    if isinstance(display_value, bool):
        display_value = str(display_value).lower()
    elif isinstance(display_value, (list, tuple)):
        if display_value:
            display_value = f"[{', '.join(str(v) for v in display_value)}]"
        else:
            display_value = "[]"
    elif display_value is None:
        display_value = "null"

    return f"{indent_str}{key}: {display_value}"


def _format_section(section_name: str, section_dict: Dict[str, Any], differences: Dict[str, tuple], path_prefix: str = "", indent: int = 0) -> str:
    """Format a configuration section with override highlighting"""
    lines = []
    indent_str = "  " * indent

    # Section header
    if indent == 0:
        lines.append(f"\n{colorize(section_name + ':', Colors.BOLD)}")
    else:
        lines.append(f"{indent_str}{section_name}:")

    for key, value in section_dict.items():
        current_path = f"{path_prefix}.{key}" if path_prefix else f"{section_name}.{key}"

        # Skip project_overrides section
        if key == "project_overrides":
            continue

        # Check if this value is overridden
        is_overridden = current_path in differences

        if isinstance(value, dict) and value:
            # Nested section
            nested_lines = _format_section(key, value, differences, current_path, indent + 1)
            lines.append(nested_lines)
        else:
            # Leaf value
            formatted = _format_value(key, value, indent + 1)

            if is_overridden:
                if is_tty():
                    formatted = colorize(formatted, Colors.GREEN)
                    formatted += colorize(" [OVERRIDE]", Colors.GREEN)
                else:
                    formatted += " [OVERRIDE]"

            lines.append(formatted)

    return "\n".join(lines)


def _format_config_human(effective_config: GraphitiConfig, global_config: GraphitiConfig, project_path: str) -> str:
    """Format configuration as human-readable output with override highlighting.

    Args:
        effective_config: Effective configuration for project
        global_config: Global configuration
        project_path: Project path being displayed

    Returns:
        Formatted string for display
    """
    lines = []

    # Header
    lines.append(colorize("\nEffective Configuration for Project:", Colors.BOLD))
    lines.append(colorize("=" * 60, Colors.BOLD))
    lines.append(f"Project Path: {project_path}")

    # Convert to dicts for comparison
    effective_dict = effective_config.model_dump()
    global_dict = global_config.model_dump()

    # Find differences
    differences = _compare_configs(effective_dict, global_dict)

    # Format each major section
    sections = [
        ("Database", effective_dict.get("database", {})),
        ("LLM", effective_dict.get("llm", {})),
        ("Embedder", effective_dict.get("embedder", {})),
        ("Extraction", effective_dict.get("extraction", {})),
        ("Session Tracking", effective_dict.get("session_tracking", {})),
        ("Search", effective_dict.get("search", {})),
        ("Logging", effective_dict.get("logging", {})),
        ("Performance", effective_dict.get("performance", {})),
        ("MCP Server", effective_dict.get("mcp_server", {})),
        ("Project", effective_dict.get("project", {})),
    ]

    for section_name, section_dict in sections:
        if section_dict:
            lines.append(_format_section(section_name, section_dict, differences, section_name.replace(" ", "_").lower()))

    lines.append("")
    return "\n".join(lines)


def _format_config_diff(effective_config: GraphitiConfig, global_config: GraphitiConfig, project_path: str) -> str:
    """Format configuration showing only overridden values (diff mode).

    Args:
        effective_config: Effective configuration for project
        global_config: Global configuration
        project_path: Project path being displayed

    Returns:
        Formatted diff string
    """
    lines = []

    # Header
    lines.append(colorize("\nConfiguration Overrides for Project:", Colors.BOLD))
    lines.append(colorize("=" * 60, Colors.BOLD))
    lines.append(f"Project Path: {project_path}")

    # Convert to dicts for comparison
    effective_dict = effective_config.model_dump()
    global_dict = global_config.model_dump()

    # Find differences
    differences = _compare_configs(effective_dict, global_dict)

    if not differences:
        lines.append("\n" + colorize("No overrides found. Using global configuration.", Colors.YELLOW))
        lines.append("")
        return "\n".join(lines)

    # Group differences by section
    sections: Dict[str, list] = {}
    for path, (global_val, effective_val) in differences.items():
        section = path.split(".")[0]
        if section not in sections:
            sections[section] = []
        sections[section].append((path, global_val, effective_val))

    # Format each section
    for section_name, items in sorted(sections.items()):
        lines.append(f"\n{colorize(section_name.replace('_', ' ').title() + ':', Colors.BOLD)}")

        for path, global_val, effective_val in items:
            # Get the leaf key name
            key = path.split(".")[-1]

            # Mask sensitive values
            global_display = mask_sensitive(key, global_val)
            effective_display = mask_sensitive(key, effective_val)

            # Format the diff line
            diff_line = f"  {key}: {global_display} → {effective_display}"

            if is_tty():
                diff_line = colorize(diff_line, Colors.GREEN)

            lines.append(diff_line)

    lines.append("")
    return "\n".join(lines)


def _format_config_json(effective_config: GraphitiConfig) -> str:
    """Format configuration as JSON.

    Args:
        effective_config: Effective configuration for project

    Returns:
        JSON string
    """
    config_dict = effective_config.model_dump()

    # Remove project_overrides from output (meta-config)
    config_dict.pop("project_overrides", None)

    return json.dumps(config_dict, indent=2)


def cmd_effective(args: argparse.Namespace) -> None:
    """Show effective configuration for a project.

    Args:
        args: Parsed command-line arguments
    """
    # Determine project path
    if args.project:
        project_path = args.project
    else:
        project_path = os.getcwd()

    # Resolve to absolute path
    project_path = str(Path(project_path).resolve())

    # Find config file
    config_path = find_config_file()

    if config_path is None:
        from mcp_server.daemon.paths import get_config_file
        print("[ERROR] No configuration file found.")
        print("\nSearched locations:")
        print("  1. ./graphiti.config.json (project root)")
        print(f"  2. {get_config_file()} (platform-specific)")
        print("\nTo create a config file, see documentation:")
        print("  https://github.com/getzep/graphiti/blob/main/CONFIGURATION.md")
        sys.exit(1)

    # Load global config
    try:
        global_config = GraphitiConfig.from_file(str(config_path))
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        sys.exit(1)

    # Get effective config for project
    try:
        effective_config = global_config.get_effective_config(project_path)
    except Exception as e:
        print(f"[ERROR] Failed to compute effective configuration: {e}")
        sys.exit(1)

    # Format and display output
    try:
        if args.json:
            output = _format_config_json(effective_config)
        elif args.diff:
            output = _format_config_diff(effective_config, global_config, project_path)
        else:
            output = _format_config_human(effective_config, global_config, project_path)

        print(output)
    except Exception as e:
        print(f"[ERROR] Failed to format output: {e}")
        sys.exit(1)


def cmd_list_projects(args: argparse.Namespace) -> None:
    """List all projects with overrides."""
    config_path = find_config_file()

    if config_path is None:
        print("No config file found.")
        print("\nNo project overrides configured.")
        print("Use 'graphiti-mcp-config set-override' to add overrides.")
        return

    try:
        config_dict = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error reading config file: {e}")
        sys.exit(1)

    # Get project_overrides dict
    project_overrides = config_dict.get("project_overrides", {})

    if not project_overrides:
        print(f"Config file: {config_path}")
        print("\nNo project overrides configured.")
        print("Use 'graphiti-mcp-config set-override' to add overrides.")
        return

    # Print each project with its overrides
    print(f"Config file: {config_path}")
    print(f"\nProjects with overrides: {len(project_overrides)}\n")

    for project_path, override in sorted(project_overrides.items()):
        print(f"Project: {project_path}")
        _print_nested_values(override, prefix="  ")
        print()  # Blank line between projects


def _print_nested_values(obj: Any, prefix: str = "") -> None:
    """Recursively print nested dict values with dot notation.

    Args:
        obj: Object to print (dict or value)
        prefix: Current indentation prefix
    """
    if isinstance(obj, dict):
        for key, value in sorted(obj.items()):
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                _print_nested_values(value, prefix + "  ")
            else:
                print(f"{prefix}{key}: {value}")
    else:
        print(f"{prefix}{obj}")


# Valid overridable sections
VALID_SECTIONS = {"llm", "embedder", "extraction", "session_tracking"}

# Non-overridable sections
INVALID_SECTIONS = {
    "database", "daemon", "resilience", "mcp_server",
    "logging", "version", "project", "search", "performance"
}


def _validate_key_path(key: str) -> tuple[bool, str]:
    """Validate key path is valid and overridable.

    Args:
        key: Dot-notation key path (e.g., 'llm.default_model')

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    if not key:
        return False, "[ERROR] Key path cannot be empty"

    # Split key by dots
    parts = key.split(".")
    root_section = parts[0]

    # Check if root section is overridable
    if root_section not in VALID_SECTIONS:
        error_msg = f"""[ERROR] Invalid key path: '{key}'
Section '{root_section}' is not overridable.

Overridable sections:
  - llm (e.g., llm.provider, llm.default_model)
  - embedder (e.g., embedder.provider, embedder.model)
  - extraction (e.g., extraction.max_reflexion_iterations)
  - session_tracking (e.g., session_tracking.enabled)

Non-overridable sections: {', '.join(sorted(INVALID_SECTIONS))}"""
        return False, error_msg

    return True, ""


def _set_nested_value(obj: dict, key_path: str, value: Any) -> None:
    """Set value in nested dict using dot notation.

    Args:
        obj: Dictionary to modify
        key_path: Dot-notation key path (e.g., 'llm.default_model')
        value: Value to set
    """
    parts = key_path.split(".")
    current = obj

    # Navigate to parent of final key, creating dicts as needed
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set final key
    current[parts[-1]] = value


def _delete_nested_value(obj: dict, key_path: str) -> None:
    """Delete value from nested dict using dot notation.

    Args:
        obj: Dictionary to modify
        key_path: Dot-notation key path (e.g., 'llm.default_model')

    Raises:
        KeyError: If key path doesn't exist
    """
    parts = key_path.split(".")
    current = obj

    # Navigate to parent of final key
    for part in parts[:-1]:
        if part not in current:
            raise KeyError(f"Key path '{key_path}' not found")
        current = current[part]

    # Delete final key
    if parts[-1] not in current:
        raise KeyError(f"Key path '{key_path}' not found")

    del current[parts[-1]]


def _is_empty_nested_dict(obj: dict) -> bool:
    """Check if nested dict is empty (no leaf values).

    Args:
        obj: Dictionary to check

    Returns:
        True if dict has no leaf values (only empty dicts)
    """
    if not obj:
        return True

    for value in obj.values():
        if isinstance(value, dict):
            if not _is_empty_nested_dict(value):
                return False
        else:
            return False

    return True


def _parse_value(value_str: str) -> Any:
    """Parse value string to appropriate type.

    Type detection order:
        1. Boolean: 'true'/'false' (case-insensitive) → bool
        2. Integer: numeric string without decimal → int
        3. Float: numeric string with decimal → float
        4. Otherwise: string

    Args:
        value_str: String value to parse

    Returns:
        Parsed value with appropriate type
    """
    # Handle booleans
    if value_str.lower() in ("true", "false"):
        return value_str.lower() == "true"

    # Try integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass

    # Default to string
    return value_str


def _load_config_dict(config_path: Path) -> dict:
    """Load configuration from JSON file as dict.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    try:
        return json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error reading config file: {e}")
        sys.exit(1)


def _save_config_dict(config_path: Path, config: dict) -> None:
    """Save configuration to JSON file.

    Args:
        config_path: Path to config file
        config: Configuration dictionary
    """
    try:
        config_path.write_text(json.dumps(config, indent=2))
    except Exception as e:
        print(f"[ERROR] Error saving config file: {e}")
        sys.exit(1)


def _ensure_global_config() -> Path:
    """Ensure global config directory and file exist.

    Uses v2.1 platform-specific paths:
        - Windows: %LOCALAPPDATA%\\Graphiti\\config\\graphiti.config.json
        - macOS: ~/Library/Preferences/Graphiti/graphiti.config.json
        - Linux: ~/.config/graphiti/graphiti.config.json

    Returns:
        Path to global config file
    """
    from mcp_server.daemon.paths import get_config_file, get_config_dir

    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = get_config_file()

    if not config_path.exists():
        # Create minimal config with defaults
        minimal_config = {
            "version": "1.0.0",
            "project_overrides": {}
        }
        config_path.write_text(json.dumps(minimal_config, indent=2))
        print(f"Created new global config at {config_path}")

    return config_path


def cmd_set_override(args: argparse.Namespace) -> None:
    """Add/update override for project+key."""
    # Normalize project path
    try:
        normalized_path = normalize_project_path(args.project)
    except Exception as e:
        print(f"[ERROR] Invalid project path: {e}")
        sys.exit(1)

    # Validate key path
    is_valid, error_msg = _validate_key_path(args.key)
    if not is_valid:
        print(error_msg)
        sys.exit(1)

    # Parse value to appropriate type
    value = _parse_value(args.value)

    # Load or create config
    config_path = find_config_file()
    if config_path is None:
        config_path = _ensure_global_config()
        print(f"No existing config found, using global: {config_path}\n")

    config = _load_config_dict(config_path)

    # Ensure project_overrides exists
    if "project_overrides" not in config:
        config["project_overrides"] = {}

    # Ensure project entry exists
    if normalized_path not in config["project_overrides"]:
        config["project_overrides"][normalized_path] = {}

    # Set nested value
    _set_nested_value(config["project_overrides"][normalized_path], args.key, value)

    # Save config
    _save_config_dict(config_path, config)

    # Print success message
    print(f"[OK] Set {args.key} = {value!r} for project {normalized_path}")
    print(f"   Config location: {config_path}")


def cmd_remove_override(args: argparse.Namespace) -> None:
    """Remove specific override or all overrides for project."""
    # Validate arguments: exactly one of --key or --all
    if args.key and args.all:
        print("[ERROR] Cannot use both --key and --all flags")
        print("   Use --key KEY to remove a specific override")
        print("   Use --all to remove all overrides for the project")
        sys.exit(1)

    if not args.key and not args.all:
        print("[ERROR] Must specify either --key KEY or --all")
        print("   Use --key KEY to remove a specific override")
        print("   Use --all to remove all overrides for the project")
        sys.exit(1)

    # Normalize project path
    try:
        normalized_path = normalize_project_path(args.project)
    except Exception as e:
        print(f"[ERROR] Invalid project path: {e}")
        sys.exit(1)

    # Load config
    config_path = find_config_file()
    if config_path is None:
        print("[ERROR] No config file found")
        print("   No project overrides exist to remove")
        sys.exit(1)

    config = _load_config_dict(config_path)

    # Check project_overrides exists
    if "project_overrides" not in config:
        print(f"[ERROR] Project not found: {normalized_path}")
        print("   No project overrides configured")
        sys.exit(1)

    # Check project exists
    if normalized_path not in config["project_overrides"]:
        print(f"[ERROR] Project not found: {normalized_path}")
        print("   Project has no overrides configured")
        sys.exit(1)

    # Handle --all flag
    if args.all:
        del config["project_overrides"][normalized_path]
        _save_config_dict(config_path, config)
        print(f"[OK] Removed all overrides for project {normalized_path}")
        print(f"   Config location: {config_path}")
        return

    # Handle --key flag
    # Validate key path
    is_valid, error_msg = _validate_key_path(args.key)
    if not is_valid:
        print(error_msg)
        sys.exit(1)

    # Try to delete the key
    try:
        _delete_nested_value(config["project_overrides"][normalized_path], args.key)
    except KeyError:
        print(f"[ERROR] Key not found: {args.key}")
        print(f"   Key does not exist in overrides for {normalized_path}")
        sys.exit(1)

    # If project override is now empty, remove the project entry
    if _is_empty_nested_dict(config["project_overrides"][normalized_path]):
        del config["project_overrides"][normalized_path]

    # Save config
    _save_config_dict(config_path, config)

    print(f"[OK] Removed {args.key} override for project {normalized_path}")
    print(f"   Config location: {config_path}")


def main() -> None:
    """Main entry point for config CLI."""
    parser = argparse.ArgumentParser(
        prog="graphiti-mcp-config",
        description="Manage and inspect Graphiti configuration"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Effective command
    effective_parser = subparsers.add_parser(
        "effective",
        help="Show effective configuration for a project"
    )
    effective_parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Project path (default: current directory)"
    )
    effective_parser.add_argument(
        "--diff",
        action="store_true",
        help="Show only overridden values with before/after"
    )
    effective_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    effective_parser.set_defaults(func=cmd_effective)

    # list-projects command
    list_parser = subparsers.add_parser(
        "list-projects",
        help="List all projects with overrides"
    )
    list_parser.set_defaults(func=cmd_list_projects)

    # set-override command
    set_parser = subparsers.add_parser(
        "set-override",
        help="Add/update override for project+key"
    )
    set_parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="Project path (any format, will be normalized)"
    )
    set_parser.add_argument(
        "--key",
        type=str,
        required=True,
        help="Dot-notation key (e.g., llm.default_model)"
    )
    set_parser.add_argument(
        "--value",
        type=str,
        required=True,
        help="Value to set (auto-detect type: string, int, float, bool)"
    )
    set_parser.set_defaults(func=cmd_set_override)

    # remove-override command
    remove_parser = subparsers.add_parser(
        "remove-override",
        help="Remove specific override or all overrides for project"
    )
    remove_parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="Project path"
    )
    remove_parser.add_argument(
        "--key",
        type=str,
        help="Specific key to remove (dot notation)"
    )
    remove_parser.add_argument(
        "--all",
        action="store_true",
        help="Remove all overrides for project"
    )
    remove_parser.set_defaults(func=cmd_remove_override)

    # Parse arguments
    args = parser.parse_args()

    # Execute command
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
