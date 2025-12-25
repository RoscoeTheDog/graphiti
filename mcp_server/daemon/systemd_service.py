"""
Linux Systemd Service Manager for Graphiti Bootstrap Service

Uses systemd user services to install/manage the service on Linux.
Runs as a user service (not system-wide) for security and convenience.

See: .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .venv_manager import VenvManager, VenvCreationError
from .paths import get_log_dir


class SystemdServiceManager:
    """Manages Graphiti bootstrap service on Linux via systemd."""

    name = "systemd (Linux Service Manager)"
    service_name = "graphiti-bootstrap"

    def __init__(self, venv_manager: Optional[VenvManager] = None):
        """Initialize systemd service manager.

        Args:
            venv_manager: Optional VenvManager instance. If None, creates default instance.

        Raises:
            VenvCreationError: If venv doesn't exist (platform-specific location from paths.py)
        """
        self.venv_manager = venv_manager or VenvManager()
        # Get venv Python executable - raise VenvCreationError if venv doesn't exist
        # (DaemonManager.install() ensures venv exists before instantiating service managers)
        self.python_exe = self.venv_manager.get_python_executable()
        self.bootstrap_script = self._get_bootstrap_path()

        # User service directory
        xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
        if xdg_config:
            self.service_dir = Path(xdg_config) / "systemd" / "user"
        else:
            self.service_dir = Path.home() / ".config" / "systemd" / "user"

        self.service_file = self.service_dir / f"{self.service_name}.service"
        self.log_dir = get_log_dir()

    def _get_bootstrap_path(self) -> Path:
        """Get path to bootstrap.py script."""
        # bootstrap.py is in mcp_server/daemon/
        return Path(__file__).parent / "bootstrap.py"

    def _create_service_unit(self) -> str:
        """Create systemd service unit file content."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

        unit_content = f"""[Unit]
Description=Graphiti MCP Bootstrap Service
Documentation=https://github.com/getzep/graphiti
After=network.target

[Service]
Type=simple
ExecStart={self.python_exe} {self.bootstrap_script}
Restart=always
RestartSec=5
WorkingDirectory={self.bootstrap_script.parent}
Environment="PATH={os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')}"
StandardOutput=append:{self.log_dir / 'bootstrap-stdout.log'}
StandardError=append:{self.log_dir / 'bootstrap-stderr.log'}

[Install]
WantedBy=default.target
"""
        return unit_content

    def _run_systemctl(self, *args) -> tuple[bool, str]:
        """Run systemctl command and return (success, output)."""
        try:
            cmd = ["systemctl", "--user"] + list(args)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # systemctl returns 0 for success
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output.strip()

        except Exception as e:
            return False, f"Error running systemctl: {e}"

    def install(self) -> bool:
        """Install bootstrap service using systemd."""
        # Check if already installed
        if self.is_installed():
            print("✓ Service already installed")
            return True

        print(f"Python: {self.python_exe}")
        print(f"Bootstrap script: {self.bootstrap_script}")
        print(f"Service file: {self.service_file}")
        print()

        # Ensure service directory exists
        self.service_dir.mkdir(parents=True, exist_ok=True)

        # Create service file
        print("Creating systemd service unit...")
        try:
            unit_content = self._create_service_unit()
            self.service_file.write_text(unit_content)
            print(f"✓ Service file created: {self.service_file}")
        except Exception as e:
            print(f"✗ Failed to create service file: {e}")
            return False

        # Reload systemd daemon
        print("Reloading systemd daemon...")
        success, output = self._run_systemctl("daemon-reload")
        if not success:
            print(f"⚠ Warning: Failed to reload daemon: {output}")

        # Enable service (auto-start on boot)
        print("Enabling service...")
        success, output = self._run_systemctl("enable", self.service_name)
        if not success:
            print(f"✗ Failed to enable service: {output}")
            return False

        # Start service
        print("Starting service...")
        success, output = self._run_systemctl("start", self.service_name)
        if not success:
            print(f"✗ Failed to start service: {output}")
            print("  You can start it manually later via:")
            print(f"  systemctl --user start {self.service_name}")
            return True  # Service installed, just not started

        print(f"✓ Service '{self.service_name}' started and enabled")
        return True

    def uninstall(self) -> bool:
        """Uninstall bootstrap service using systemd."""
        if not self.is_installed():
            print("Service not installed (nothing to uninstall)")
            return True

        # Stop service
        print("Stopping service...")
        success, output = self._run_systemctl("stop", self.service_name)
        if not success:
            print(f"⚠ Warning: Failed to stop service: {output}")

        # Disable service
        print("Disabling service...")
        success, output = self._run_systemctl("disable", self.service_name)
        if not success:
            print(f"⚠ Warning: Failed to disable service: {output}")

        # Remove service file
        print("Removing service file...")
        try:
            if self.service_file.exists():
                self.service_file.unlink()
                print(f"✓ Service file removed: {self.service_file}")
        except Exception as e:
            print(f"✗ Failed to remove service file: {e}")
            return False

        # Reload systemd daemon
        print("Reloading systemd daemon...")
        self._run_systemctl("daemon-reload")

        print(f"✓ Service '{self.service_name}' removed")
        return True

    def is_installed(self) -> bool:
        """Check if service is installed (service file exists)."""
        return self.service_file.exists()

    def is_running(self) -> bool:
        """Check if service is running."""
        if not self.is_installed():
            return False

        # Check service status
        success, output = self._run_systemctl("is-active", self.service_name)

        # systemctl is-active returns "active" if running
        return success and "active" in output

    def show_logs(self, follow: bool = False, lines: int = 50) -> None:
        """Show service logs using journalctl."""
        if not self.is_installed():
            print("Service not installed")
            return

        print(f"Fetching logs from journalctl...")
        print()

        # Use journalctl to show logs
        cmd = [
            "journalctl",
            "--user",
            "-u", self.service_name,
            "-n", str(lines),
        ]

        if follow:
            cmd.append("-f")

        try:
            if follow:
                print("Press Ctrl+C to stop following logs")
                print()
                # Stream output continuously
                subprocess.run(cmd)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
                print(result.stdout)
                if result.stderr:
                    print("Errors:")
                    print(result.stderr)
        except FileNotFoundError:
            # journalctl not available, fall back to log files
            print("journalctl not available, showing log files instead:")
            print()
            self._show_log_files(follow, lines)
        except Exception as e:
            print(f"Error reading logs: {e}")

    def _show_log_files(self, follow: bool = False, lines: int = 50) -> None:
        """Fallback: Show log files directly (when journalctl unavailable)."""
        stdout_log = self.log_dir / "bootstrap-stdout.log"
        stderr_log = self.log_dir / "bootstrap-stderr.log"

        if not stdout_log.exists() and not stderr_log.exists():
            print(f"No logs found in: {self.log_dir}")
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

    @property
    def start_hint(self) -> str:
        """Hint for starting the service manually."""
        return f"systemctl --user start {self.service_name}"
