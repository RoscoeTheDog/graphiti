#!/usr/bin/env python3
"""
Graphiti Daemon Manager

Platform-agnostic interface for managing the bootstrap service as an OS service.
Supports Windows (NSSM), macOS (launchd), and Linux (systemd).

This module provides the unified CLI interface:
- graphiti-mcp daemon install
- graphiti-mcp daemon uninstall
- graphiti-mcp daemon status
- graphiti-mcp daemon logs

Design Principle: Installation lifecycle only. Runtime control is via config file.

See: .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md
"""

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Optional

from .windows_service import WindowsServiceManager
from .launchd_service import LaunchdServiceManager
from .systemd_service import SystemdServiceManager
from .venv_manager import VenvManager, VenvCreationError, IncompatiblePythonVersionError


class UnsupportedPlatformError(Exception):
    """Raised when platform is not supported."""
    pass


class DaemonManager:
    """Platform-agnostic daemon service manager."""

    def __init__(self):
        """Initialize manager with platform-specific implementation."""
        self.platform = platform.system()
        self.service_manager = self._get_service_manager()
        self.config_path = self._get_config_path()
        self.venv_manager = VenvManager()  # Dedicated venv at ~/.graphiti/.venv/

    def _get_service_manager(self):
        """Get platform-specific service manager."""
        if self.platform == "Windows":
            return WindowsServiceManager()
        elif self.platform == "Darwin":
            return LaunchdServiceManager()
        elif self.platform == "Linux":
            return SystemdServiceManager()
        else:
            raise UnsupportedPlatformError(
                f"Platform '{self.platform}' is not supported. "
                "Graphiti daemon requires Windows, macOS, or Linux."
            )

    def _get_config_path(self) -> Path:
        """Get config path (platform-aware)."""
        if self.platform == "Windows":
            return Path.home() / ".graphiti" / "graphiti.config.json"
        else:
            # Unix: check XDG_CONFIG_HOME
            import os
            xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
            if xdg_config:
                return Path(xdg_config) / "graphiti" / "graphiti.config.json"
            return Path.home() / ".graphiti" / "graphiti.config.json"

    def install(self) -> bool:
        """Install bootstrap service (auto-start on boot)."""
        print(f"Installing Graphiti bootstrap service on {self.platform}...")
        print()

        # Step 1: Validate Python version
        try:
            self.venv_manager.validate_python_version()
            print("[OK] Python version check passed")
        except IncompatiblePythonVersionError as e:
            print(f"[FAILED] {e}")
            print()
            print("Please upgrade to Python 3.10 or higher:")
            print("  https://www.python.org/downloads/")
            return False

        # Step 2: Create dedicated venv
        print()
        print("Creating dedicated virtual environment...")
        try:
            success, msg = self.venv_manager.create_venv()
            if success:
                print(f"[OK] {msg}")
            else:
                print(f"[FAILED] {msg}")
                return False
        except VenvCreationError as e:
            print(f"[FAILED] Venv creation failed: {e}")
            print()
            print("Troubleshooting:")
            print("  - Ensure you have write permissions to ~/.graphiti/")
            print("  - Check available disk space")
            print("  - Try: python -m venv --help (verify venv module available)")
            return False

        # Step 3: Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 4: Initialize config if needed
        if not self.config_path.exists():
            print()
            print(f"Creating default config: {self.config_path}")
            self._create_default_config()

        # Step 5: Install service
        print()
        success = self.service_manager.install()

        if success:
            print()
            print("[SUCCESS] Bootstrap service installed successfully")
            print()
            print("Next steps:")
            print(f"  1. Edit config: {self.config_path}")
            print('     Set: "daemon": { "enabled": true }')
            print()
            print("  2. The MCP server will start automatically within 5 seconds")
            print()
            print("  3. Check status: graphiti-mcp daemon status")
            return True
        else:
            print()
            print("[FAILED] Failed to install bootstrap service")
            print("  See error messages above for details")
            return False

    def uninstall(self) -> bool:
        """Uninstall bootstrap service."""
        print(f"Uninstalling Graphiti bootstrap service on {self.platform}...")
        print()

        success = self.service_manager.uninstall()

        if success:
            print()
            print("[SUCCESS] Bootstrap service uninstalled successfully")
            print()
            print(f"Config file preserved: {self.config_path}")
            print("  (You can manually delete ~/.graphiti/ if desired)")
            return True
        else:
            print()
            print("[FAILED] Failed to uninstall bootstrap service")
            print("  See error messages above for details")
            return False

    def status(self) -> dict:
        """
        Get daemon status (installed, enabled, running).

        Returns:
            Dict with status information:
            {
                'venv': {'exists': bool, 'path': str},
                'service': {'installed': bool, 'running': bool, 'platform': str, 'manager': str},
                'config': {'enabled': bool, 'host': str, 'port': int, 'path': str}
            }
        """
        # Check venv status
        venv_exists = self.venv_manager.detect_venv()

        # Check if service is installed
        is_installed = self.service_manager.is_installed()

        # Check if service is running
        is_running = self.service_manager.is_running() if is_installed else False

        # Build status dict
        status_dict = {
            'venv': {
                'exists': venv_exists,
                'path': str(self.venv_manager.venv_path)
            },
            'service': {
                'installed': is_installed,
                'running': is_running,
                'platform': self.platform,
                'manager': self.service_manager.name
            }
        }

        # Check config state
        if self.config_path.exists():
            try:
                config = json.loads(self.config_path.read_text())
                daemon_config = config.get("daemon", {})
                status_dict['config'] = {
                    'path': str(self.config_path),
                    'enabled': daemon_config.get("enabled", False),
                    'host': daemon_config.get("host", "127.0.0.1"),
                    'port': daemon_config.get("port", 8321)
                }
            except json.JSONDecodeError:
                status_dict['config'] = {
                    'path': str(self.config_path),
                    'error': 'Invalid JSON'
                }
            except Exception as e:
                status_dict['config'] = {
                    'path': str(self.config_path),
                    'error': str(e)
                }
        else:
            status_dict['config'] = {
                'path': str(self.config_path),
                'exists': False
            }

        return status_dict

    def print_status(self) -> None:
        """Print daemon status to stdout (CLI-friendly version)."""
        status = self.status()

        print("Graphiti Daemon Status")
        print("=" * 60)
        print()

        # Print venv status
        print(f"Venv Path:       {status['venv']['path']}")
        print(f"Venv Status:     {'[EXISTS]' if status['venv']['exists'] else '[MISSING]'}")
        print()

        # Print service status
        print(f"Platform:        {status['service']['platform']}")
        print(f"Service Manager: {status['service']['manager']}")
        print(f"Installed:       {'[YES]' if status['service']['installed'] else '[NO]'}")
        print()

        if not status['service']['installed']:
            print("Service not installed. Run: graphiti-mcp daemon install")
            return

        print(f"Bootstrap:       {'[RUNNING]' if status['service']['running'] else '[STOPPED]'}")
        print()

        if not status['service']['running']:
            print("Bootstrap service not running.")
            print("  Check logs: graphiti-mcp daemon logs")
            return

        # Print config status
        if 'error' in status['config']:
            print(f"Config:          {status['config']['path']} ({status['config']['error']})")
        elif not status['config'].get('exists', True):
            print(f"Config:          NOT FOUND ({status['config']['path']})")
            print("  Run: graphiti-mcp daemon install (to create default config)")
        else:
            print(f"Config:          {status['config']['path']}")
            print(f"Daemon Enabled:  {'[YES]' if status['config']['enabled'] else '[NO]'}")
            print(f"MCP Server:      http://{status['config']['host']}:{status['config']['port']}")
            print()

            if not status['config']['enabled']:
                print("MCP server is disabled in config.")
                print(f"  To enable, edit: {status['config']['path']}")
                print('  Set: "daemon": { "enabled": true }')
            else:
                print("MCP server should be running on:")
                print(f"  http://{status['config']['host']}:{status['config']['port']}/health")
                print()
                print("Test with: curl http://127.0.0.1:8321/health")

    def logs(self, follow: bool = False, lines: int = 50) -> None:
        """Tail daemon logs."""
        print(f"Fetching last {lines} lines of daemon logs...")
        print()

        self.service_manager.show_logs(follow=follow, lines=lines)

    def _create_default_config(self) -> None:
        """Create default graphiti.config.json."""
        default_config = {
            "daemon": {
                "_comment": "Daemon service configuration (Two-Layer Architecture)",
                "_docs": "See .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md",
                "enabled": False,
                "_enabled_help": "Master switch: false (default) = MCP server stopped, true = MCP server running",
                "host": "127.0.0.1",
                "_host_help": "Bind address for HTTP API. Use 127.0.0.1 (localhost-only, secure)",
                "port": 8321,
                "_port_help": "HTTP port for MCP API. 8321 is default, change if conflict",
                "config_poll_seconds": 5,
                "_config_poll_seconds_help": "How often bootstrap checks this file for changes",
                "pid_file": None,
                "_pid_file_help": "null = ~/.graphiti/graphiti-mcp.pid",
                "log_file": None,
                "_log_file_help": "null = ~/.graphiti/logs/graphiti-mcp.log",
                "log_level": "INFO",
                "_log_level_help": "DEBUG | INFO | WARNING | ERROR | CRITICAL",
                "log_rotation": {
                    "max_bytes": 10485760,
                    "_max_bytes_help": "10MB default, rotate when exceeded",
                    "backup_count": 5,
                    "_backup_count_help": "Keep 5 rotated log files"
                },
                "health_check_interval": 30,
                "_health_check_interval_help": "Seconds between MCP server health checks by bootstrap"
            }
        }

        self.config_path.write_text(json.dumps(default_config, indent=2))


def main():
    """Entry point for graphiti-mcp daemon CLI."""
    parser = argparse.ArgumentParser(
        prog="graphiti-mcp daemon",
        description="Manage Graphiti MCP daemon service (installation lifecycle only)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Daemon command")

    # Install command
    subparsers.add_parser(
        "install",
        help="Install bootstrap service (auto-start on boot)",
    )

    # Uninstall command
    subparsers.add_parser(
        "uninstall",
        help="Uninstall bootstrap service",
    )

    # Status command
    subparsers.add_parser(
        "status",
        help="Show daemon status (installed, enabled, running)",
    )

    # Logs command
    logs_parser = subparsers.add_parser(
        "logs",
        help="Tail daemon logs",
    )
    logs_parser.add_argument(
        "-f", "--follow",
        action="store_true",
        help="Follow log output (like tail -f)",
    )
    logs_parser.add_argument(
        "-n", "--lines",
        type=int,
        default=50,
        help="Number of lines to show (default: 50)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print()
        print("Examples:")
        print("  graphiti-mcp daemon install    # Install service")
        print("  graphiti-mcp daemon status     # Check status")
        print("  graphiti-mcp daemon logs       # View logs")
        print("  graphiti-mcp daemon uninstall  # Remove service")
        sys.exit(1)

    try:
        manager = DaemonManager()

        if args.command == "install":
            success = manager.install()
            sys.exit(0 if success else 1)

        elif args.command == "uninstall":
            success = manager.uninstall()
            sys.exit(0 if success else 1)

        elif args.command == "status":
            manager.status()
            sys.exit(0)

        elif args.command == "logs":
            manager.logs(follow=args.follow, lines=args.lines)
            sys.exit(0)

    except UnsupportedPlatformError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
