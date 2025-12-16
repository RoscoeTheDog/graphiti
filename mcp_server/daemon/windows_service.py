"""
Windows Service Manager for Graphiti Bootstrap Service

Uses NSSM (Non-Sucking Service Manager) to install/manage the service on Windows.
NSSM is the recommended approach as it's simple, reliable, and widely used.

Requirements:
- NSSM must be installed (downloadable from https://nssm.cc/)
- Automatic download/install of NSSM is NOT implemented (requires admin rights)

See: .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .venv_manager import VenvManager, VenvCreationError


class WindowsServiceManager:
    """Manages Graphiti bootstrap service on Windows via NSSM."""

    name = "NSSM (Windows Service Manager)"
    service_name = "GraphitiBootstrap"
    display_name = "Graphiti MCP Bootstrap Service"

    def __init__(self, venv_manager: Optional[VenvManager] = None):
        """Initialize Windows service manager.

        Args:
            venv_manager: Optional VenvManager instance. If None, creates default instance.

        Raises:
            VenvCreationError: If venv doesn't exist at ~/.graphiti/.venv
        """
        self.nssm_path = self._find_nssm()
        self.venv_manager = venv_manager or VenvManager()
        # Get venv Python executable - raise VenvCreationError if venv doesn't exist
        # (DaemonManager.install() ensures venv exists before instantiating service managers)
        self.python_exe = self.venv_manager.get_python_executable()
        self.bootstrap_script = self._get_bootstrap_path()

    def _find_nssm(self) -> Optional[Path]:
        """Find NSSM executable in PATH or common locations."""
        # Check PATH first
        nssm_in_path = shutil.which("nssm")
        if nssm_in_path:
            return Path(nssm_in_path)

        # Check common installation locations
        common_locations = [
            Path(r"C:\Program Files\NSSM\nssm.exe"),
            Path(r"C:\Program Files (x86)\NSSM\nssm.exe"),
            Path.home() / "scoop" / "shims" / "nssm.exe",  # Scoop
            Path(os.environ.get("PROGRAMFILES", "")) / "NSSM" / "nssm.exe",
        ]

        for location in common_locations:
            if location.exists():
                return location

        return None

    def _get_bootstrap_path(self) -> Path:
        """Get path to bootstrap.py script."""
        # bootstrap.py is in mcp_server/daemon/
        return Path(__file__).parent / "bootstrap.py"

    def _run_nssm(self, *args) -> tuple[bool, str]:
        """Run NSSM command and return (success, output)."""
        if not self.nssm_path:
            return False, "NSSM not found. Please install NSSM from https://nssm.cc/"

        try:
            cmd = [str(self.nssm_path)] + list(args)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # NSSM returns 0 for success
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output.strip()

        except Exception as e:
            return False, f"Error running NSSM: {e}"

    def install(self) -> bool:
        """Install bootstrap service using NSSM."""
        if not self.nssm_path:
            print("✗ NSSM not found")
            print()
            print("NSSM is required to install services on Windows.")
            print("Please install NSSM:")
            print()
            print("  Option 1: Download from https://nssm.cc/download")
            print("  Option 2: Install via Chocolatey: choco install nssm")
            print("  Option 3: Install via Scoop: scoop install nssm")
            print()
            return False

        # Check if already installed
        if self.is_installed():
            print("✓ Service already installed")
            return True

        print(f"Using NSSM: {self.nssm_path}")
        print(f"Python: {self.python_exe}")
        print(f"Bootstrap script: {self.bootstrap_script}")
        print()

        # Install service
        print("Installing service...")
        success, output = self._run_nssm(
            "install",
            self.service_name,
            str(self.python_exe),
            str(self.bootstrap_script),
        )

        if not success:
            print(f"✗ Failed to install service: {output}")
            return False

        # Set display name
        self._run_nssm("set", self.service_name, "DisplayName", self.display_name)

        # Set description
        self._run_nssm(
            "set",
            self.service_name,
            "Description",
            "Watches graphiti.config.json and manages MCP server lifecycle",
        )

        # Set startup type to automatic
        self._run_nssm("set", self.service_name, "Start", "SERVICE_AUTO_START")

        # Set working directory to mcp_server/daemon/
        working_dir = self.bootstrap_script.parent
        self._run_nssm("set", self.service_name, "AppDirectory", str(working_dir))

        # Configure stdout/stderr logging
        log_dir = Path.home() / ".graphiti" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        stdout_log = log_dir / "bootstrap-stdout.log"
        stderr_log = log_dir / "bootstrap-stderr.log"

        self._run_nssm("set", self.service_name, "AppStdout", str(stdout_log))
        self._run_nssm("set", self.service_name, "AppStderr", str(stderr_log))

        # Rotate logs (10MB max, keep 5 files)
        self._run_nssm("set", self.service_name, "AppStdoutCreationDisposition", "4")  # APPEND
        self._run_nssm("set", self.service_name, "AppStderrCreationDisposition", "4")  # APPEND
        self._run_nssm("set", self.service_name, "AppRotateFiles", "1")  # Enable rotation
        self._run_nssm("set", self.service_name, "AppRotateBytes", str(10 * 1024 * 1024))  # 10MB

        # Start service
        print("Starting service...")
        success, output = self._run_nssm("start", self.service_name)

        if not success:
            print(f"✗ Failed to start service: {output}")
            print("  You can start it manually later via Services app or:")
            print(f"  nssm start {self.service_name}")
            return True  # Service installed, just not started

        print(f"✓ Service '{self.service_name}' started")
        return True

    def uninstall(self) -> bool:
        """Uninstall bootstrap service using NSSM."""
        if not self.nssm_path:
            print("✗ NSSM not found")
            return False

        if not self.is_installed():
            print("Service not installed (nothing to uninstall)")
            return True

        # Stop service first
        print("Stopping service...")
        self._run_nssm("stop", self.service_name)

        # Remove service
        print("Removing service...")
        success, output = self._run_nssm("remove", self.service_name, "confirm")

        if not success:
            print(f"✗ Failed to remove service: {output}")
            return False

        print(f"✓ Service '{self.service_name}' removed")
        return True

    def is_installed(self) -> bool:
        """Check if service is installed."""
        if not self.nssm_path:
            return False

        # Query service status (returns error if not installed)
        success, _ = self._run_nssm("status", self.service_name)
        return success

    def is_running(self) -> bool:
        """Check if service is running."""
        if not self.is_installed():
            return False

        success, output = self._run_nssm("status", self.service_name)
        if not success:
            return False

        # NSSM status returns: SERVICE_RUNNING, SERVICE_STOPPED, etc.
        return "SERVICE_RUNNING" in output

    def show_logs(self, follow: bool = False, lines: int = 50) -> None:
        """Show service logs (stdout and stderr)."""
        log_dir = Path.home() / ".graphiti" / "logs"
        stdout_log = log_dir / "bootstrap-stdout.log"
        stderr_log = log_dir / "bootstrap-stderr.log"

        if not stdout_log.exists() and not stderr_log.exists():
            print(f"No logs found in: {log_dir}")
            print()
            print("Service may not have started yet.")
            print(f"Check service status: graphiti-mcp daemon status")
            return

        print(f"Logs directory: {log_dir}")
        print()

        # Show stdout
        if stdout_log.exists():
            print("=== STDOUT ===")
            try:
                with open(stdout_log, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                    display_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    for line in display_lines:
                        print(line.rstrip())
            except Exception as e:
                print(f"Error reading stdout log: {e}")
            print()

        # Show stderr
        if stderr_log.exists():
            print("=== STDERR ===")
            try:
                with open(stderr_log, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                    display_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    for line in display_lines:
                        print(line.rstrip())
            except Exception as e:
                print(f"Error reading stderr log: {e}")
            print()

        if follow:
            print("Live log following not supported on Windows.")
            print("Use 'tail -f' equivalent or view in real-time via:")
            print(f"  Get-Content -Path '{stdout_log}' -Wait")

    @property
    def start_hint(self) -> str:
        """Hint for starting the service manually."""
        return f"nssm start {self.service_name}"
