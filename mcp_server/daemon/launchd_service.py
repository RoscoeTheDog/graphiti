"""
macOS Launchd Service Manager for Graphiti Bootstrap Service

Uses macOS's native launchd system to install/manage the service.
Service runs as a user agent (not system-wide) for security.

See: .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md
"""

import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .paths import get_install_dir, get_log_dir


class LaunchdServiceManager:
    """Manages Graphiti bootstrap service on macOS via launchd.

    Uses frozen package installation from {INSTALL_DIR}:
    - Python: {INSTALL_DIR}/bin/python
    - Bootstrap: -m mcp_server.daemon.bootstrap
    - PYTHONPATH: {INSTALL_DIR}/lib
    """

    name = "launchd (macOS Service Manager)"
    service_id = "com.graphiti.bootstrap"

    def __init__(self):
        """Initialize launchd service manager.

        Uses frozen package installation paths from get_install_dir().
        Python executable: {INSTALL_DIR}/bin/python
        Bootstrap module: mcp_server.daemon.bootstrap (invoked with -m)
        """
        self.install_dir = get_install_dir()
        self.python_exe = self.install_dir / "bin" / "python"
        self.plist_path = Path.home() / "Library" / "LaunchAgents" / f"{self.service_id}.plist"
        self.log_dir = get_log_dir()

    def _create_plist(self) -> dict:
        """Create launchd plist configuration.

        Plist uses frozen package paths:
        - ProgramArguments: {INSTALL_DIR}/bin/python -m mcp_server.daemon.bootstrap
        - WorkingDirectory: {INSTALL_DIR}
        - PYTHONPATH: {INSTALL_DIR}/lib (for frozen package imports)
        - Logs: {STATE_DIR}/logs/ (via get_log_dir())
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)

        plist = {
            "Label": self.service_id,
            "ProgramArguments": [
                str(self.python_exe),
                "-m",
                "mcp_server.daemon.bootstrap",
            ],
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": str(self.log_dir / "bootstrap-stdout.log"),
            "StandardErrorPath": str(self.log_dir / "bootstrap-stderr.log"),
            "WorkingDirectory": str(self.install_dir),
            "EnvironmentVariables": {
                "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                "PYTHONPATH": str(self.install_dir / "lib"),
            },
        }

        return plist

    def _run_launchctl(self, *args) -> tuple[bool, str]:
        """Run launchctl command and return (success, output)."""
        try:
            cmd = ["launchctl"] + list(args)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # launchctl returns 0 for success
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output.strip()

        except Exception as e:
            return False, f"Error running launchctl: {e}"

    def install(self) -> bool:
        """Install bootstrap service using launchd."""
        # Check if already installed
        if self.is_installed():
            print("✓ Service already installed")
            return True

        print(f"Python: {self.python_exe}")
        print(f"Bootstrap module: mcp_server.daemon.bootstrap")
        print(f"Plist: {self.plist_path}")
        print()

        # Ensure LaunchAgents directory exists
        self.plist_path.parent.mkdir(parents=True, exist_ok=True)

        # Create plist file
        print("Creating launchd plist...")
        try:
            plist_data = self._create_plist()
            with open(self.plist_path, "wb") as f:
                plistlib.dump(plist_data, f)
            print(f"✓ Plist created: {self.plist_path}")
        except Exception as e:
            print(f"✗ Failed to create plist: {e}")
            return False

        # Load service
        print("Loading service...")
        success, output = self._run_launchctl("load", str(self.plist_path))

        if not success:
            print(f"✗ Failed to load service: {output}")
            return False

        print(f"✓ Service '{self.service_id}' loaded and started")
        return True

    def uninstall(self) -> bool:
        """Uninstall bootstrap service using launchd."""
        if not self.is_installed():
            print("Service not installed (nothing to uninstall)")
            return True

        # Unload service
        print("Unloading service...")
        success, output = self._run_launchctl("unload", str(self.plist_path))

        if not success:
            print(f"⚠ Warning: Failed to unload service: {output}")
            # Continue anyway to delete plist

        # Remove plist file
        print("Removing plist file...")
        try:
            if self.plist_path.exists():
                self.plist_path.unlink()
                print(f"✓ Plist removed: {self.plist_path}")
        except Exception as e:
            print(f"✗ Failed to remove plist: {e}")
            return False

        print(f"✓ Service '{self.service_id}' removed")
        return True

    def is_installed(self) -> bool:
        """Check if service is installed (plist exists)."""
        return self.plist_path.exists()

    def is_running(self) -> bool:
        """Check if service is running."""
        if not self.is_installed():
            return False

        # List loaded services and check for our service
        success, output = self._run_launchctl("list")
        if not success:
            return False

        # Check if our service ID appears in the list
        return self.service_id in output

    def show_logs(self, follow: bool = False, lines: int = 50) -> None:
        """Show service logs (stdout and stderr)."""
        stdout_log = self.log_dir / "bootstrap-stdout.log"
        stderr_log = self.log_dir / "bootstrap-stderr.log"

        if not stdout_log.exists() and not stderr_log.exists():
            print(f"No logs found in: {self.log_dir}")
            print()
            print("Service may not have started yet.")
            print(f"Check service status: graphiti-mcp daemon status")
            return

        print(f"Logs directory: {self.log_dir}")
        print()

        # Show stdout
        if stdout_log.exists():
            print("=== STDOUT ===")
            try:
                cmd = ["tail", f"-n{lines}", str(stdout_log)]
                if follow:
                    cmd = ["tail", "-f", f"-n{lines}", str(stdout_log)]

                if follow:
                    # Stream output continuously
                    subprocess.run(cmd)
                else:
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    print(result.stdout)
            except Exception as e:
                print(f"Error reading stdout log: {e}")
            print()

        # Show stderr (only if not following stdout)
        if stderr_log.exists() and not follow:
            print("=== STDERR ===")
            try:
                result = subprocess.run(
                    ["tail", f"-n{lines}", str(stderr_log)],
                    capture_output=True,
                    text=True,
                )
                print(result.stdout)
            except Exception as e:
                print(f"Error reading stderr log: {e}")
            print()

        if follow:
            print()
            print("Press Ctrl+C to stop following logs")

    @property
    def start_hint(self) -> str:
        """Hint for starting the service manually."""
        return f"launchctl start {self.service_id}"
