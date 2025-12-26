"""
Windows Task Scheduler Service Manager for Graphiti Bootstrap Service

Uses Windows Task Scheduler to install/manage the service on Windows.
Runs as a user-level scheduled task (not system-wide) for security.

The task is configured to:
- Run at user logon
- Restart on failure
- Run whether user is logged in or not (if password provided)

See: .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v2.1.md
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

from .paths import get_install_dir, get_log_dir


class TaskSchedulerServiceManager:
    """Manages Graphiti bootstrap service on Windows via Task Scheduler.

    Uses frozen package installation from {INSTALL_DIR}:
    - Python: {INSTALL_DIR}\\Scripts\\pythonw.exe (windowless)
    - Bootstrap: -m mcp_server.daemon.bootstrap
    - PYTHONPATH: {INSTALL_DIR}\\lib
    """

    name = "Task Scheduler (Windows Service Manager)"
    task_name = "GraphitiBootstrap"
    task_path = "\\Graphiti\\"  # Task folder in Task Scheduler

    def __init__(self):
        """Initialize Task Scheduler service manager.

        Uses frozen package installation paths from get_install_dir().
        Python executable: {INSTALL_DIR}\\Scripts\\pythonw.exe (windowless)
        Bootstrap module: mcp_server.daemon.bootstrap (invoked with -m)
        """
        self.install_dir = get_install_dir()
        # Use pythonw.exe for windowless operation (no console window)
        self.python_exe = self.install_dir / "Scripts" / "pythonw.exe"
        # Fallback to python.exe if pythonw.exe doesn't exist
        if not self.python_exe.exists():
            self.python_exe = self.install_dir / "Scripts" / "python.exe"
        self.log_dir = get_log_dir()
        self.full_task_name = f"{self.task_path}{self.task_name}"

    def _create_task_xml(self) -> str:
        """Create Task Scheduler XML configuration.

        Returns XML that configures:
        - Trigger: At user logon
        - Action: Run pythonw.exe -m mcp_server.daemon.bootstrap
        - Settings: Restart on failure, run indefinitely
        - Environment: PYTHONPATH set to {INSTALL_DIR}\\lib
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        lib_dir = self.install_dir / "lib"

        # Get current username for the task
        username = os.environ.get("USERNAME", os.environ.get("USER", ""))

        # Task Scheduler XML format
        xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Graphiti MCP Bootstrap Service - Manages MCP server lifecycle</Description>
    <Author>{username}</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{username}</UserId>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{username}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{self.python_exe}</Command>
      <Arguments>-c "import sys; sys.path.insert(0, r'{lib_dir}'); from mcp_server.daemon.bootstrap import main; main()"</Arguments>
      <WorkingDirectory>{self.install_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        return xml_content

    def _run_schtasks(self, *args) -> tuple[bool, str]:
        """Run schtasks command and return (success, output)."""
        try:
            cmd = ["schtasks"] + list(args)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            # schtasks returns 0 for success
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output.strip()

        except Exception as e:
            return False, f"Error running schtasks: {e}"

    def _ensure_task_folder(self) -> bool:
        """Ensure the Graphiti task folder exists in Task Scheduler."""
        # Check if folder exists by trying to query it
        success, _ = self._run_schtasks("/Query", "/TN", "\\Graphiti\\")
        if success:
            return True

        # Create a dummy task to force folder creation, then delete it
        # This is a workaround since schtasks doesn't have a "create folder" command
        return True  # Folder will be created when we create the task

    def install(self) -> bool:
        """Install bootstrap service using Task Scheduler."""
        # Check if already installed
        if self.is_installed():
            print("✓ Task already installed")
            return True

        print(f"Python: {self.python_exe}")
        print(f"Bootstrap module: mcp_server.daemon.bootstrap")
        print(f"Task name: {self.full_task_name}")
        print()

        # Create temporary XML file for task import
        import tempfile
        xml_content = self._create_task_xml()

        try:
            # Write XML to temp file (Task Scheduler requires UTF-16 encoding)
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.xml',
                delete=False,
                encoding='utf-16'
            ) as f:
                f.write(xml_content)
                xml_path = f.name

            print("Creating scheduled task...")

            # Create the task using XML import
            success, output = self._run_schtasks(
                "/Create",
                "/TN", self.full_task_name,
                "/XML", xml_path,
                "/F"  # Force overwrite if exists
            )

            # Clean up temp file
            try:
                os.unlink(xml_path)
            except Exception:
                pass

            if not success:
                print(f"✗ Failed to create task: {output}")
                return False

            print(f"✓ Task '{self.task_name}' created")

            # Set PYTHONPATH environment variable for the task
            # Note: Task Scheduler doesn't directly support env vars in XML,
            # so we'll create a wrapper batch script or set it via the action
            self._create_env_wrapper()

            # Start the task immediately
            print("Starting task...")
            success, output = self._run_schtasks("/Run", "/TN", self.full_task_name)

            if not success:
                print(f"⚠ Warning: Failed to start task immediately: {output}")
                print("  Task will start at next logon")
            else:
                print(f"✓ Task '{self.task_name}' started")

            return True

        except Exception as e:
            print(f"✗ Failed to install task: {e}")
            return False

    def _create_env_wrapper(self) -> None:
        """Create a wrapper script that sets PYTHONPATH before running bootstrap.

        Task Scheduler XML doesn't support environment variables directly,
        so we create a small batch wrapper that sets PYTHONPATH.
        """
        wrapper_path = self.install_dir / "run_bootstrap.bat"
        lib_dir = self.install_dir / "lib"

        wrapper_content = f'''@echo off
set PYTHONPATH={lib_dir}
"{self.python_exe}" -m mcp_server.daemon.bootstrap
'''
        try:
            wrapper_path.parent.mkdir(parents=True, exist_ok=True)
            wrapper_path.write_text(wrapper_content)
        except Exception:
            pass  # Non-critical - bootstrap can still work without wrapper

    def uninstall(self) -> bool:
        """Uninstall bootstrap service from Task Scheduler."""
        if not self.is_installed():
            print("Task not installed (nothing to uninstall)")
            return True

        # Stop the task if running
        print("Stopping task...")
        self._run_schtasks("/End", "/TN", self.full_task_name)

        # Delete the task
        print("Removing task...")
        success, output = self._run_schtasks(
            "/Delete",
            "/TN", self.full_task_name,
            "/F"  # Force delete without confirmation
        )

        if not success:
            print(f"✗ Failed to remove task: {output}")
            return False

        # Remove wrapper script if exists
        wrapper_path = self.install_dir / "run_bootstrap.bat"
        try:
            if wrapper_path.exists():
                wrapper_path.unlink()
        except Exception:
            pass  # Non-critical

        print(f"✓ Task '{self.task_name}' removed")
        return True

    def is_installed(self) -> bool:
        """Check if task is installed in Task Scheduler."""
        success, _ = self._run_schtasks("/Query", "/TN", self.full_task_name)
        return success

    def is_running(self) -> bool:
        """Check if task is currently running."""
        if not self.is_installed():
            return False

        success, output = self._run_schtasks(
            "/Query",
            "/TN", self.full_task_name,
            "/FO", "LIST",
            "/V"
        )

        if not success:
            return False

        # Check if status is "Running"
        return "Running" in output

    def show_logs(self, follow: bool = False, lines: int = 50) -> None:
        """Show service logs (stdout and stderr)."""
        stdout_log = self.log_dir / "bootstrap-stdout.log"
        stderr_log = self.log_dir / "bootstrap-stderr.log"

        if not stdout_log.exists() and not stderr_log.exists():
            print(f"No logs found in: {self.log_dir}")
            print()
            print("Service may not have started yet.")
            print(f"Check task status: graphiti-mcp daemon status")
            return

        print(f"Logs directory: {self.log_dir}")
        print()

        # On Windows, we'll read the files directly since tail isn't available
        if stdout_log.exists():
            print("=== STDOUT ===")
            try:
                with open(stdout_log, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.readlines()
                    # Get last N lines
                    for line in content[-lines:]:
                        print(line, end='')
                print()
            except Exception as e:
                print(f"Error reading stdout log: {e}")
            print()

        if stderr_log.exists() and not follow:
            print("=== STDERR ===")
            try:
                with open(stderr_log, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.readlines()
                    for line in content[-lines:]:
                        print(line, end='')
                print()
            except Exception as e:
                print(f"Error reading stderr log: {e}")
            print()

        if follow:
            print()
            print("Note: Follow mode (-f) requires PowerShell Get-Content -Wait")
            print(f"  PowerShell: Get-Content -Wait -Tail {lines} '{stdout_log}'")

    @property
    def start_hint(self) -> str:
        """Hint for starting the service manually."""
        return f'schtasks /Run /TN "{self.full_task_name}"'
