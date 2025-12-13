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
    print("Session tracking now uses a turn-based architecture for efficient indexing.")
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
    print("Note: Turn-based indexing will no longer process new sessions.")


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




def cmd_sync(args: argparse.Namespace) -> None:
    """Execute sync command.

    Uses resilient_indexer if available from MCP server for graceful degradation.
    Failed sessions are queued for retry instead of being lost.
    """
    import asyncio
    from mcp_server.manual_sync import session_tracking_sync_history
    from mcp_server.graphiti_mcp_server import (
        session_manager,
        graphiti_client,
        unified_config,
        resilient_indexer,  # Story 13.3: Resilience integration
    )

    # Validate dangerous operations
    if args.days == 0 and not args.confirm:
        print("❌ Error: --days 0 (all history) requires --confirm flag")
        print("   This could index thousands of sessions and cost hundreds of dollars!")
        sys.exit(1)

    # Progress callback for CLI
    def progress_callback(current: int, total: int) -> None:
        """Display progress during sync."""
        if not args.quiet:
            print(f"\r  Progress: {current}/{total} sessions", end="", flush=True)

    # Call MCP tool
    try:
        result_json = asyncio.run(
            session_tracking_sync_history(
                session_manager=session_manager,
                graphiti_client=graphiti_client,
                unified_config=unified_config,
                project=args.project,
                days=args.days,
                max_sessions=args.max_sessions,
                dry_run=args.dry_run,
                resilient_indexer=resilient_indexer,  # Story 13.3
                progress_callback=progress_callback if not args.dry_run else None,
            )
        )

        # Clear progress line if shown
        if not args.dry_run and not args.quiet:
            print()  # New line after progress

        # Parse and display results
        data = json.loads(result_json)

        if data.get("status") == "error":
            print(f"❌ Error: {data['error']}")
            sys.exit(1)

        # Display table
        print("""
📊 Session Sync Summary
""")
        print(f"  Mode:             {'DRY RUN (preview)' if data['dry_run'] else 'ACTUAL SYNC'}")
        print(f"  Sessions found:   {data['sessions_found']}")
        print(f"  Estimated cost:   {data['estimated_cost']}")
        if not data['dry_run']:
            print(f"  Sessions indexed: {data['sessions_indexed']}")
            print(f"  Sessions failed:  {data.get('sessions_failed', 0)}")
            print(f"  Actual cost:      {data['actual_cost']}")

            # Display resilience status (Story 13.3)
            if data.get('resilience_enabled'):
                print(f"\n  Resilience:")
                print(f"    Enabled:        ✅")
                print(f"    LLM available:  {'✅' if data.get('llm_available') else '⚠️ No'}")
                print(f"    Degradation:    {data.get('degradation_level', 'unknown')}")
                queued = data.get('sessions_queued_for_retry', 0)
                if queued > 0:
                    print(f"    Queued retry:   {queued} sessions (will retry when LLM available)")
            else:
                print(f"\n  Resilience:       ❌ Not available (run from MCP server)")

        if data['dry_run']:
            print("\n💡 Tip: Run with --no-dry-run to perform actual sync")

        # Show sample sessions
        if "sessions" in data and data["sessions"]:
            print("\n📄 Sample Sessions (first 10):\n")
            for session in data["sessions"]:
                print(f"  {session['path']}")
                print(f"    Modified: {session['modified']}, Messages: {session['messages']}")

        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

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


    # Sync command
    sync_parser = subparsers.add_parser(
        "sync",
        help="Manually sync historical sessions to Graphiti"
    )
    sync_parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Specific project path (default: all projects)"
    )
    sync_parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days to look back (0 = all history, requires --confirm)"
    )
    sync_parser.add_argument(
        "--max-sessions",
        type=int,
        default=100,
        help="Maximum sessions to sync (safety limit)"
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview mode (default)"
    )
    sync_parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Perform actual sync (not preview)"
    )
    sync_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for --days 0 (all history)"
    )
    sync_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output"
    )
    sync_parser.set_defaults(func=cmd_sync)

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
