#!/usr/bin/env python3
"""
Session Tracking CLI - Manage session tracking configuration for Graphiti MCP server

Commands:
    graphiti-mcp session-tracking enable    Enable automatic session tracking
    graphiti-mcp session-tracking disable   Disable automatic session tracking
    graphiti-mcp session-tracking status    Show session tracking status
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from mcp_server.unified_config import GraphitiConfig


def find_config_file() -> Optional[Path]:
    """Find the Graphiti configuration file.

    Search order:
        1. ./graphiti.config.json (project root)
        2. ~/.graphiti/graphiti.config.json (global)

    Returns:
        Path to config file, or None if not found
    """
    # Try project root first
    project_config = Path("graphiti.config.json")
    if project_config.exists():
        return project_config

    # Try global config
    global_config = Path.home() / ".graphiti" / "graphiti.config.json"
    if global_config.exists():
        return global_config

    return None


def ensure_global_config() -> Path:
    """Ensure global config directory and file exist.

    Returns:
        Path to global config file
    """
    global_config_dir = Path.home() / ".graphiti"
    global_config_dir.mkdir(parents=True, exist_ok=True)

    global_config_path = global_config_dir / "graphiti.config.json"

    if not global_config_path.exists():
        # Create minimal config with defaults
        minimal_config = {
            "version": "1.0.0",
            "session_tracking": {
                "enabled": False
            }
        }
        global_config_path.write_text(json.dumps(minimal_config, indent=2))
        print(f"Created new global config at {global_config_path}")

    return global_config_path


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    try:
        return json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading config file: {e}")
        sys.exit(1)


def save_config(config_path: Path, config: dict) -> None:
    """Save configuration to JSON file.

    Args:
        config_path: Path to config file
        config: Configuration dictionary
    """
    try:
        config_path.write_text(json.dumps(config, indent=2))
        print(f"✅ Configuration saved to {config_path}")
    except Exception as e:
        print(f"❌ Error saving config file: {e}")
        sys.exit(1)


def cmd_enable(args: argparse.Namespace) -> None:
    """Enable session tracking."""
    config_path = find_config_file()

    if config_path is None:
        # No existing config, create global one
        config_path = ensure_global_config()
        print(f"No existing config found, using global: {config_path}")

    config = load_config(config_path)

    # Ensure session_tracking section exists
    if "session_tracking" not in config:
        config["session_tracking"] = {}

    # Enable tracking
    config["session_tracking"]["enabled"] = True

    # Save updated config
    save_config(config_path, config)

    print("\n✅ Session tracking enabled")
    print(f"   Config location: {config_path}")
    print("\nSession tracking will start on next MCP server startup.")
    print("To customize settings, edit the config file or see documentation:")
    print("  https://github.com/getzep/graphiti/blob/main/CONFIGURATION.md#session-tracking")


def cmd_disable(args: argparse.Namespace) -> None:
    """Disable session tracking."""
    config_path = find_config_file()

    if config_path is None:
        print("⚠️  No config file found. Session tracking is already disabled (default).")
        return

    config = load_config(config_path)

    # Ensure session_tracking section exists
    if "session_tracking" not in config:
        config["session_tracking"] = {}

    # Disable tracking
    config["session_tracking"]["enabled"] = False

    # Save updated config
    save_config(config_path, config)

    print("\n✅ Session tracking disabled")
    print(f"   Config location: {config_path}")
    print("\nSession tracking will stop on next MCP server startup.")


def cmd_status(args: argparse.Namespace) -> None:
    """Show session tracking status."""
    config_path = find_config_file()

    if config_path is None:
        print("Session Tracking Status")
        print("=" * 50)
        print("Config file:  Not found")
        print("Status:       ❌ Disabled (default)")
        print("\nNo configuration file found. Session tracking is disabled.")
        print(f"Run 'graphiti-mcp session-tracking enable' to enable.")
        return

    config = load_config(config_path)

    # Get session tracking config
    session_config = config.get("session_tracking", {})
    enabled = session_config.get("enabled", False)
    watch_path = session_config.get("watch_path", None)
    inactivity_timeout = session_config.get("inactivity_timeout", 300)
    check_interval = session_config.get("check_interval", 60)
    auto_summarize = session_config.get("auto_summarize", True)
    store_in_graph = session_config.get("store_in_graph", True)

    # Get filter config
    filter_config = session_config.get("filter", {})

    # Display status
    print("\nSession Tracking Status")
    print("=" * 50)
    print(f"Config file:        {config_path}")
    print(f"Status:             {'✅ Enabled' if enabled else '❌ Disabled'}")

    if enabled:
        print(f"\nConfiguration:")
        print(f"  Watch path:       {watch_path or '~/.claude/projects/ (default)'}")
        print(f"  Inactivity:       {inactivity_timeout}s")
        print(f"  Check interval:   {check_interval}s")
        print(f"  Auto summarize:   {auto_summarize}")
        print(f"  Store in graph:   {store_in_graph}")

        if filter_config:
            print(f"\n  Filtering:")
            print(f"    Tool calls:     {filter_config.get('tool_calls', True)}")
            print(f"    Tool content:   {filter_config.get('tool_content', 'summary')}")
            print(f"    User messages:  {filter_config.get('user_messages', 'full')}")
            print(f"    Agent messages: {filter_config.get('agent_messages', 'full')}")
    else:
        print("\nTo enable session tracking, run:")
        print("  graphiti-mcp session-tracking enable")

    print()


def main() -> None:
    """Main entry point for session tracking CLI."""
    parser = argparse.ArgumentParser(
        prog="graphiti-mcp session-tracking",
        description="Manage session tracking for Graphiti MCP server"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Enable command
    enable_parser = subparsers.add_parser(
        "enable",
        help="Enable automatic session tracking"
    )
    enable_parser.set_defaults(func=cmd_enable)

    # Disable command
    disable_parser = subparsers.add_parser(
        "disable",
        help="Disable automatic session tracking"
    )
    disable_parser.set_defaults(func=cmd_disable)

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show session tracking status"
    )
    status_parser.set_defaults(func=cmd_status)

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
