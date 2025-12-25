"""
v2.0 Installation Detection Module

Detects existing v2.0 installations to support migration to v2.1.

v2.0 artifacts:
- Directory: ~/.graphiti/
- Config: ~/.graphiti/graphiti.config.json
- Venv: ~/.graphiti/.venv/
- Logs: ~/.graphiti/logs/

v2.0 service/task names by platform:
- Windows: GraphitiBootstrap or GraphitiBootstrap_{username} (Task Scheduler)
- macOS: com.graphiti.bootstrap (LaunchAgent)
- Linux: graphiti-bootstrap (systemd user service)

See: .claude/sprint/plans/11-plan.yaml
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional


def detect_v2_0_installation() -> dict:
    """
    Detect v2.0 installation artifacts.

    Returns:
        dict: Detection results with the following structure:
            {
                "detected": bool,           # True if v2.0 installation found
                "home_dir": Path or None,   # ~/.graphiti/ if exists
                "config_file": Path or None,  # ~/.graphiti/graphiti.config.json if exists
                "service_task": str or None   # Service/task name if found
            }

    Platform-specific detection:
        Windows:
            - Directory: C:\\Users\\{username}\\.graphiti\\
            - Task: GraphitiBootstrap or GraphitiBootstrap_{username}
            - Query: Get-ScheduledTask -TaskName 'GraphitiBootstrap*'

        macOS:
            - Directory: /Users/{username}/.graphiti/
            - LaunchAgent: ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
            - Query: launchctl list | grep com.graphiti.bootstrap

        Linux:
            - Directory: /home/{username}/.graphiti/
            - Service: ~/.config/systemd/user/graphiti-bootstrap.service
            - Query: systemctl --user status graphiti-bootstrap

    Error Handling:
        - Gracefully handles permission denied errors when querying services
        - Returns partial results if directory exists but service query fails
        - Never raises exceptions - always returns dict with detected=False on errors
    """
    v2_home_dir = Path.home() / ".graphiti"
    v2_config_file = v2_home_dir / "graphiti.config.json"

    # Check for directory existence
    home_dir_exists = v2_home_dir.exists() and v2_home_dir.is_dir()
    config_file_exists = v2_config_file.exists() and v2_config_file.is_file()

    # Platform-specific service/task detection
    current_platform = platform.system()
    service_task_name = None

    if current_platform == "Windows":
        service_task_name = _detect_windows_task()
    elif current_platform == "Darwin":
        service_task_name = _detect_macos_launchagent()
    elif current_platform == "Linux":
        service_task_name = _detect_linux_service()

    # Detection is positive if EITHER home directory OR service exists
    detected = home_dir_exists or (service_task_name is not None)

    return {
        "detected": detected,
        "home_dir": v2_home_dir if home_dir_exists else None,
        "config_file": v2_config_file if config_file_exists else None,
        "service_task": service_task_name
    }


def _detect_windows_task() -> Optional[str]:
    """
    Detect Windows Task Scheduler task for v2.0 bootstrap.

    Task names:
        - GraphitiBootstrap
        - GraphitiBootstrap_{username}

    Query method:
        - PowerShell: Get-ScheduledTask -TaskName 'GraphitiBootstrap*'
        - Fallback: sc query (not applicable for Task Scheduler)

    Returns:
        str: Task name if found (e.g., "GraphitiBootstrap")
        None: If task not found or query failed

    Error Handling:
        - Returns None on permission denied
        - Returns None on PowerShell not available
        - Never raises exceptions
    """
    try:
        # Try PowerShell Get-ScheduledTask
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-ScheduledTask -TaskName 'GraphitiBootstrap*' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty TaskName"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode == 0 and result.stdout.strip():
            # Get first matching task name
            task_name = result.stdout.strip().split('\n')[0].strip()
            if task_name:
                return task_name

        return None

    except subprocess.TimeoutExpired:
        # Query took too long - treat as not found
        return None
    except FileNotFoundError:
        # PowerShell not available
        return None
    except Exception:
        # Any other error (permissions, etc.) - treat as not found
        return None


def _detect_macos_launchagent() -> Optional[str]:
    """
    Detect macOS LaunchAgent for v2.0 bootstrap.

    LaunchAgent details:
        - Plist path: ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
        - Service ID: com.graphiti.bootstrap

    Query method:
        - Check plist file existence
        - Verify with launchctl list (optional, more thorough)

    Returns:
        str: Service ID if found (e.g., "com.graphiti.bootstrap")
        None: If LaunchAgent not found or query failed

    Error Handling:
        - Returns None on permission denied
        - Returns None on launchctl not available
        - Never raises exceptions
    """
    service_id = "com.graphiti.bootstrap"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{service_id}.plist"

    # Primary check: plist file existence
    if plist_path.exists() and plist_path.is_file():
        return service_id

    # Secondary check: launchctl list (may be loaded even if plist is gone)
    try:
        cmd = ["launchctl", "list"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Check if service ID appears in output
            if service_id in result.stdout:
                return service_id

        return None

    except subprocess.TimeoutExpired:
        # Query took too long - treat as not found
        return None
    except FileNotFoundError:
        # launchctl not available (unlikely on macOS)
        return None
    except Exception:
        # Any other error (permissions, etc.) - treat as not found
        return None


def _detect_linux_service() -> Optional[str]:
    """
    Detect Linux systemd user service for v2.0 bootstrap.

    Service details:
        - Service file: ~/.config/systemd/user/graphiti-bootstrap.service
        - Service name: graphiti-bootstrap

    Query method:
        - Check service file existence
        - Verify with systemctl --user status (optional, more thorough)

    Returns:
        str: Service name if found (e.g., "graphiti-bootstrap")
        None: If service not found or query failed

    Error Handling:
        - Returns None on permission denied
        - Returns None on systemctl not available
        - Never raises exceptions
    """
    service_name = "graphiti-bootstrap"

    # Check for service file in XDG_CONFIG_HOME or default location
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        service_dir = Path(xdg_config) / "systemd" / "user"
    else:
        service_dir = Path.home() / ".config" / "systemd" / "user"

    service_file = service_dir / f"{service_name}.service"

    # Primary check: service file existence
    if service_file.exists() and service_file.is_file():
        return service_name

    # Secondary check: systemctl --user status (may be loaded even if file is gone)
    try:
        cmd = ["systemctl", "--user", "status", service_name]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )

        # systemctl status returns 0 (active), 3 (inactive), or 4 (not found)
        # We consider 0 or 3 as "service exists"
        if result.returncode in (0, 3):
            return service_name

        return None

    except subprocess.TimeoutExpired:
        # Query took too long - treat as not found
        return None
    except FileNotFoundError:
        # systemctl not available
        return None
    except Exception:
        # Any other error (permissions, etc.) - treat as not found
        return None
