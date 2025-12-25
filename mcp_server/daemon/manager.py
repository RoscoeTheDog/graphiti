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
from .wrapper_generator import WrapperGenerator, WrapperGenerationError
from .path_integration import PathIntegration, PathIntegrationError
from .package_deployer import PackageDeployer, PackageDeploymentError
from .paths import get_config_file, get_install_dir, get_log_dir
from .v2_detection import detect_v2_0_installation


class UnsupportedPlatformError(Exception):
    """Raised when platform is not supported."""
    pass


class DaemonManager:
    """Platform-agnostic daemon service manager."""

    def __init__(self):
        """Initialize manager with platform-specific implementation."""
        self.platform = platform.system()
        self.venv_manager = VenvManager()  # Dedicated venv managed by paths.py
        self.package_deployer = PackageDeployer()  # Package deployment to platform-specific install directory
        self.service_manager = self._get_service_manager()
        self.config_path = get_config_file()  # Platform-specific config file from paths.py
        self.wrapper_generator = WrapperGenerator()  # Wrapper scripts in platform-specific bin directory
        self.path_integration = PathIntegration()  # PATH detection and instructions

    def _get_service_manager(self):
        """Get platform-specific service manager."""
        if self.platform == "Windows":
            return WindowsServiceManager(venv_manager=self.venv_manager)
        elif self.platform == "Darwin":
            return LaunchdServiceManager(venv_manager=self.venv_manager)
        elif self.platform == "Linux":
            return SystemdServiceManager(venv_manager=self.venv_manager)
        else:
            raise UnsupportedPlatformError(
                f"Platform '{self.platform}' is not supported. "
                "Graphiti daemon requires Windows, macOS, or Linux."
            )

    def _get_config_path(self) -> Path:
        """
        Get config path (platform-aware).

        NOTE: This method is deprecated. Use get_config_file() from paths.py instead.
        Kept for backward compatibility only.
        """
        return get_config_file()

    def _get_uninstall_script_path(self) -> Optional[Path]:
        """
        Get path to standalone uninstall script for current platform.

        Returns:
            Path to uninstall script if it exists, None otherwise.

        Note:
            Standalone scripts can run without Python or repository access.
            Useful as fallback when manager.py is unavailable.
        """
        script_dir = Path(__file__).parent

        if self.platform == "Windows":
            script_path = script_dir / "uninstall_windows.ps1"
        elif self.platform == "Darwin":
            script_path = script_dir / "uninstall_macos.sh"
        elif self.platform == "Linux":
            script_path = script_dir / "uninstall_linux.sh"
        else:
            return None

        return script_path if script_path.exists() else None

    def detect_v2_installation(self) -> dict:
        """
        Detect v2.0 installation artifacts.

        This method wraps the v2_detection.detect_v2_0_installation() function
        to provide a unified interface through DaemonManager.

        Returns:
            dict: Detection results with the following structure:
                {
                    "detected": bool,           # True if v2.0 installation found
                    "home_dir": Path or None,   # ~/.graphiti/ if exists
                    "config_file": Path or None,  # ~/.graphiti/graphiti.config.json if exists
                    "service_task": str or None   # Service/task name if found
                }

        Usage:
            >>> manager = DaemonManager()
            >>> result = manager.detect_v2_installation()
            >>> if result["detected"]:
            ...     print(f"v2.0 installation found: {result['home_dir']}")
            ...     # Proceed with migration (Story 12)

        See Also:
            - v2_detection.detect_v2_0_installation() for implementation details
            - Story 11: Implement v2.0 Installation Detection
            - Story 12: Implement Config Migration (uses this detection)
        """
        return detect_v2_0_installation()

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
            print(f"  - Ensure you have write permissions to {get_install_dir()}")
            print("  - Check available disk space")
            print("  - Try: python -m venv --help (verify venv module available)")
            return False

        # Step 2.4: Deploy mcp_server package to standalone location
        print()
        print(f"Deploying mcp_server package to {get_install_dir()}...")
        try:
            success, msg = self.package_deployer.deploy_package()
            if success:
                print(f"[OK] {msg}")
            else:
                print(f"[FAILED] Package deployment failed: {msg}")
                print()
                print("Troubleshooting:")
                print(f"  - Ensure write permissions to {get_install_dir()}")
                print("  - Check available disk space")
                print("  - Verify mcp_server/pyproject.toml exists in repository")
                return False
        except PackageDeploymentError as e:
            print(f"[FAILED] Package deployment failed: {e}")
            print()
            print("Troubleshooting:")
            print("  - Ensure you're running from the Graphiti repository directory")
            print("  - Verify mcp_server/ directory structure is intact")
            return False
        except Exception as e:
            print(f"[FAILED] Unexpected error during package deployment: {e}")
            return False

        # Step 2.5: Install mcp_server package into venv
        print()
        print("Installing mcp_server package...")
        try:
            success, msg = self.venv_manager.install_package()
            if success:
                print(f"[OK] {msg}")
            else:
                print(f"[FAILED] Package installation failed: {msg}")
                print()
                print("Troubleshooting:")
                print("  - Ensure you're running from the Graphiti repository directory")
                print("  - Check internet connection (needed for package dependencies)")
                print("  - Verify mcp_server/pyproject.toml exists in repository")
                return False
        except VenvCreationError as e:
            print(f"[FAILED] Package installation failed: {e}")
            return False
        except Exception as e:
            print(f"[FAILED] Unexpected error during package installation: {e}")
            return False

        # Step 2.6: Generate CLI wrapper scripts
        print()
        print("Generating CLI wrapper scripts...")
        try:
            success, msg = self.wrapper_generator.generate_wrappers()
            if success:
                print(f"[OK] {msg}")
            else:
                print(f"[FAILED] {msg}")
                print()
                print("Troubleshooting:")
                print(f"  - Ensure write permissions to {get_install_dir() / 'bin'}")
                print("  - Check available disk space")
                return False
        except WrapperGenerationError as e:
            print(f"[FAILED] Wrapper generation failed: {e}")
            return False
        except Exception as e:
            print(f"[FAILED] Unexpected error during wrapper generation: {e}")
            return False

        # Step 2.7: Display PATH configuration instructions
        try:
            self.path_integration.display_instructions()
        except PathIntegrationError as e:
            print(f"[WARNING] PATH integration error: {e}")
            print(f"  You may need to manually add {get_install_dir() / 'bin'} to your PATH")
        except Exception as e:
            print(f"[WARNING] Unexpected error during PATH integration: {e}")
            print(f"  You may need to manually add {get_install_dir() / 'bin'} to your PATH")

        # Step 3: Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 4: Initialize or update config
        if not self.config_path.exists():
            print()
            print(f"Creating default config: {self.config_path}")
            self._create_default_config()
        else:
            # Config exists, update if needed
            self._update_existing_config()

        # Step 5: Install service
        print()
        success = self.service_manager.install()

        if success:
            print()
            print("[SUCCESS] Bootstrap service installed successfully")
            print()
            print("Daemon is now running with auto-start enabled!")
            print()
            print("What's happening:")
            print("  - The MCP server will start automatically within 5 seconds")
            print("  - Config file created/updated with daemon.enabled = true")
            print()
            print("Next steps:")
            print("  1. Check status: graphiti-mcp daemon status")
            print(f"  2. View logs: graphiti-mcp daemon logs")
            print(f"  3. Edit config (optional): {self.config_path}")
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
            # Clean up wrapper scripts
            print()
            print("Cleaning up wrapper scripts...")
            try:
                cleanup_success, cleanup_msg = self.wrapper_generator.cleanup_wrappers()
                if cleanup_success:
                    print(f"[OK] {cleanup_msg}")
                else:
                    print(f"[WARNING] {cleanup_msg}")
            except Exception as e:
                print(f"[WARNING] Wrapper cleanup failed: {e}")

            print()
            print("[SUCCESS] Bootstrap service uninstalled successfully")
            print()
            print(f"Config file preserved: {self.config_path}")
            print(f"  (You can manually delete {get_install_dir()} if desired)")
            print()

            # Suggest standalone script for complete uninstall
            standalone_script = self._get_uninstall_script_path()
            if standalone_script:
                print("For complete uninstall (including venv and deployed package):")
                if self.platform == "Windows":
                    print(f"  Run: powershell -File {standalone_script}")
                else:
                    print(f"  Run: {standalone_script}")
                print()
                print("See docs/UNINSTALL.md for details")
            else:
                print("Note: Standalone uninstall script not found.")
                print(f"  Manual cleanup: Remove {get_install_dir()} directory if desired")

            return True
        else:
            print()
            print("[FAILED] Failed to uninstall bootstrap service")
            print("  See error messages above for details")
            print()

            # Suggest standalone script as fallback
            standalone_script = self._get_uninstall_script_path()
            if standalone_script:
                print("Alternative: Use standalone uninstall script")
                if self.platform == "Windows":
                    print(f"  Run: powershell -File {standalone_script}")
                else:
                    print(f"  Run: {standalone_script}")
                print()
                print("See docs/UNINSTALL.md for details")

            return False

    def status(self) -> dict:
        """
        Get daemon status (installed, enabled, running).

        Returns:
            Dict with status information:
            {
                'venv': {'exists': bool, 'path': str},
                'wrappers': {'all_exist': bool, 'bin_path': str, 'message': str},
                'service': {'installed': bool, 'running': bool, 'platform': str, 'manager': str},
                'config': {'enabled': bool, 'host': str, 'port': int, 'path': str}
            }
        """
        # Check venv status
        venv_exists = self.venv_manager.detect_venv()

        # Check wrapper scripts status
        wrappers_exist, wrapper_msg = self.wrapper_generator.validate_wrappers()

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
            'wrappers': {
                'all_exist': wrappers_exist,
                'bin_path': str(self.wrapper_generator.bin_path),
                'message': wrapper_msg
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

        # Print wrapper scripts status
        print(f"Wrappers Path:   {status['wrappers']['bin_path']}")
        print(f"Wrappers Status: {'[OK]' if status['wrappers']['all_exist'] else '[MISSING]'}")
        if not status['wrappers']['all_exist']:
            print(f"  {status['wrappers']['message']}")
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
                "enabled": True,
                "_enabled_help": "Master switch: false = MCP server stopped, true (default) = MCP server running",
                "host": "127.0.0.1",
                "_host_help": "Bind address for HTTP API. Use 127.0.0.1 (localhost-only, secure)",
                "port": 8321,
                "_port_help": "HTTP port for MCP API. 8321 is default, change if conflict",
                "config_poll_seconds": 5,
                "_config_poll_seconds_help": "How often bootstrap checks this file for changes",
                "pid_file": None,
                "_pid_file_help": f"null = {get_install_dir() / 'graphiti-mcp.pid'}",
                "log_file": None,
                "_log_file_help": f"null = {get_log_dir() / 'graphiti-mcp.log'}",
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

    def _update_existing_config(self) -> None:
        """Update existing config to enable daemon if needed.

        If config exists with daemon.enabled: false, prompts user before updating.
        If user confirms, updates config to set enabled: true.
        If daemon.enabled is already true, skips update.
        """
        try:
            # Read existing config
            config_text = self.config_path.read_text()
            config = json.loads(config_text)

            # Check if daemon.enabled is already true
            daemon_config = config.get("daemon", {})
            if daemon_config.get("enabled", False):
                # Already enabled, no update needed
                return

            # Daemon is disabled, prompt user for update
            print()
            print(f"Found existing config: {self.config_path}")
            print("  Current setting: daemon.enabled = false (MCP server will not auto-start)")
            print()
            print("The installer can update this to enabled = true for auto-start.")
            print()

            try:
                response = input("  Update config to enable daemon? (y/n): ").strip().lower()
                if response == 'y':
                    # Update config to enable daemon
                    daemon_config["enabled"] = True
                    config["daemon"] = daemon_config
                    self.config_path.write_text(json.dumps(config, indent=2))
                    print()
                    print("  [OK] Config updated: daemon.enabled = true")
                else:
                    print()
                    print("  [SKIPPED] Config not updated, daemon remains disabled")
                    print("  You can manually enable later by editing:")
                    print(f"    {self.config_path}")
            except (KeyboardInterrupt, EOFError):
                print()
                print("  [SKIPPED] Config update cancelled")

        except json.JSONDecodeError:
            print(f"[WARNING] Existing config has invalid JSON: {self.config_path}")
            print("  Creating backup and generating new config...")
            backup_path = self.config_path.with_suffix('.json.backup')
            self.config_path.rename(backup_path)
            print(f"  Backup saved to: {backup_path}")
            self._create_default_config()
        except Exception as e:
            print(f"[WARNING] Error reading existing config: {e}")
            print("  Proceeding with existing config unchanged")


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
            manager.print_status()
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
