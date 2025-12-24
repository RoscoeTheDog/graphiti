# Graphiti MCP Server: Per-User Daemon Architecture

> **Version**: 2.0.0
> **Status**: DESIGN COMPLETE - Ready for Implementation
> **Created**: 2024-12-24
> **Updated**: 2024-12-24
> **Supersedes**: DAEMON_ARCHITECTURE_SPEC_v1.0.md
> **Author**: Claude + Human collaboration

---

## Executive Summary

This document specifies a **per-user daemon architecture** for the Graphiti MCP server that:

1. Runs as a **user-level background process** (not a system service)
2. Uses **user home directory** (`~/.graphiti/`) for all data and config
3. Starts automatically at **user login** (not system boot)
4. Provides **complete isolation** between users on multi-user systems
5. Requires **no administrator privileges** to install
6. Works identically on **Windows, macOS, and Linux**

### Key Change from v1.0

| Aspect | v1.0 (System Service) | v2.0 (Per-User) |
|--------|----------------------|-----------------|
| Scope | Machine-wide | Per-user |
| Install requires | Admin rights | User rights only |
| Runs as | SYSTEM/root | Current user |
| Data location | System paths | `~/.graphiti/` |
| Starts at | System boot | User login |
| Multi-user | Collision risk | Complete isolation |
| `Path.home()` | Broken (SYSTEM user) | Works correctly |

### Why Per-User?

1. **MCP is inherently per-user** - Claude sessions are user-specific
2. **Memory graphs are personal** - Users shouldn't share memory
3. **No privilege escalation** - Users manage their own installation
4. **Simpler architecture** - No SYSTEM user path issues
5. **Better security** - Isolation by design

---

## Architecture Overview

### Per-User Model

```
User A (logged in):
┌─────────────────────────────────────────────────────────────┐
│  C:\Users\A\.graphiti\                                       │
│  ├── graphiti.config.json                                    │
│  ├── .venv/                                                  │
│  ├── mcp_server/                                             │
│  └── logs/                                                   │
│                                                              │
│  Graphiti Bootstrap (user process)                          │
│  └── MCP Server on localhost:8321                           │
│                                                              │
│  Claude Code ─────► http://127.0.0.1:8321                   │
└─────────────────────────────────────────────────────────────┘

User B (logged in simultaneously):
┌─────────────────────────────────────────────────────────────┐
│  C:\Users\B\.graphiti\                                       │
│  ├── graphiti.config.json                                    │
│  ├── .venv/                                                  │
│  ├── mcp_server/                                             │
│  └── logs/                                                   │
│                                                              │
│  Graphiti Bootstrap (user process)                          │
│  └── MCP Server on localhost:8322  ← Different port!        │
│                                                              │
│  Claude Code ─────► http://127.0.0.1:8322                   │
└─────────────────────────────────────────────────────────────┘
```

### Complete Isolation

- Each user has their own `~/.graphiti/` directory
- Each user has their own config, venv, and logs
- Each user has their own Neo4j database (or namespace)
- Port conflicts avoided via per-user port configuration
- No shared state, no collision risk

---

## Platform Implementation

### Windows: Task Scheduler (User Level)

**Why Task Scheduler instead of NSSM?**

| Aspect | NSSM (System Service) | Task Scheduler (User Task) |
|--------|----------------------|---------------------------|
| Runs as | SYSTEM | Current user |
| `Path.home()` | `C:\Windows\system32\...` (wrong!) | `C:\Users\{user}` (correct) |
| Admin required | Yes | No |
| Starts at | System boot | User login |
| Multi-user | Collision | Isolated |

**Task Scheduler Configuration:**

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Graphiti MCP Bootstrap Service - manages MCP server lifecycle</Description>
    <Author>Graphiti</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
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
      <Command>%USERPROFILE%\.graphiti\.venv\Scripts\pythonw.exe</Command>
      <Arguments>-m mcp_server.daemon.bootstrap</Arguments>
      <WorkingDirectory>%USERPROFILE%\.graphiti</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

**Key Points:**
- `<LogonTrigger>` - Starts when user logs in
- `<LogonType>InteractiveToken</LogonType>` - Runs as logged-in user
- `<RunLevel>LeastPrivilege</RunLevel>` - No admin elevation
- `pythonw.exe` - No console window
- `%USERPROFILE%` - Expands to correct user directory

**Installation via Python:**

```python
import subprocess
import sys
from pathlib import Path

class WindowsTaskSchedulerManager:
    """Manages Graphiti bootstrap as a Windows Task Scheduler task."""

    task_name = "GraphitiBootstrap"

    def __init__(self):
        self.graphiti_home = Path.home() / ".graphiti"
        self.venv_python = self.graphiti_home / ".venv" / "Scripts" / "pythonw.exe"
        self.task_xml_path = self.graphiti_home / "graphiti-bootstrap-task.xml"

    def install(self) -> bool:
        """Install bootstrap as scheduled task (runs at user login)."""
        # Generate task XML
        self._generate_task_xml()

        # Register task (no admin required for user-level tasks)
        result = subprocess.run(
            [
                "schtasks", "/create",
                "/tn", self.task_name,
                "/xml", str(self.task_xml_path),
                "/f"  # Force overwrite if exists
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Failed to create task: {result.stderr}")
            return False

        print(f"Task '{self.task_name}' created successfully")

        # Start task immediately
        return self.start()

    def uninstall(self) -> bool:
        """Remove scheduled task."""
        # Stop task first
        self.stop()

        result = subprocess.run(
            ["schtasks", "/delete", "/tn", self.task_name, "/f"],
            capture_output=True,
            text=True
        )

        return result.returncode == 0

    def start(self) -> bool:
        """Start the task immediately."""
        result = subprocess.run(
            ["schtasks", "/run", "/tn", self.task_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def stop(self) -> bool:
        """Stop the running task."""
        result = subprocess.run(
            ["schtasks", "/end", "/tn", self.task_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def is_installed(self) -> bool:
        """Check if task is registered."""
        result = subprocess.run(
            ["schtasks", "/query", "/tn", self.task_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def is_running(self) -> bool:
        """Check if task is currently running."""
        result = subprocess.run(
            ["schtasks", "/query", "/tn", self.task_name, "/fo", "CSV", "/v"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False
        return "Running" in result.stdout

    def _generate_task_xml(self):
        """Generate task XML file."""
        xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Graphiti MCP Bootstrap Service - manages MCP server lifecycle</Description>
    <Author>Graphiti</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
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
      <Command>{self.venv_python}</Command>
      <Arguments>-m mcp_server.daemon.bootstrap</Arguments>
      <WorkingDirectory>{self.graphiti_home}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''

        self.task_xml_path.parent.mkdir(parents=True, exist_ok=True)
        self.task_xml_path.write_text(xml_content, encoding="utf-16")
```

---

### macOS: launchd User Agent

**Location:** `~/Library/LaunchAgents/com.graphiti.bootstrap.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.graphiti.bootstrap</string>

    <key>ProgramArguments</key>
    <array>
        <string>${HOME}/.graphiti/.venv/bin/python</string>
        <string>-m</string>
        <string>mcp_server.daemon.bootstrap</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${HOME}/.graphiti</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>${HOME}/.graphiti/logs/bootstrap-stdout.log</string>

    <key>StandardErrorPath</key>
    <string>${HOME}/.graphiti/logs/bootstrap-stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

**Key Points:**
- Located in `~/Library/LaunchAgents/` (user-level, not system)
- `RunAtLoad` - Starts when user logs in
- `KeepAlive` with `SuccessfulExit: false` - Restart on crash
- No admin privileges required

**Installation:**

```bash
# Copy plist to LaunchAgents
cp com.graphiti.bootstrap.plist ~/Library/LaunchAgents/

# Load (start) the agent
launchctl load ~/Library/LaunchAgents/com.graphiti.bootstrap.plist

# Unload (stop) the agent
launchctl unload ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
```

---

### Linux: systemd User Service

**Location:** `~/.config/systemd/user/graphiti-bootstrap.service`

```ini
[Unit]
Description=Graphiti MCP Bootstrap Service
After=default.target

[Service]
Type=simple
ExecStart=%h/.graphiti/.venv/bin/python -m mcp_server.daemon.bootstrap
WorkingDirectory=%h/.graphiti
Restart=on-failure
RestartSec=5

# Logging (journald)
StandardOutput=journal
StandardError=journal
SyslogIdentifier=graphiti-bootstrap

[Install]
WantedBy=default.target
```

**Key Points:**
- Located in `~/.config/systemd/user/` (user-level)
- `%h` expands to user's home directory
- `WantedBy=default.target` - Starts at user login
- No sudo required

**Installation:**

```bash
# Create systemd user directory
mkdir -p ~/.config/systemd/user

# Copy service file
cp graphiti-bootstrap.service ~/.config/systemd/user/

# Reload systemd user daemon
systemctl --user daemon-reload

# Enable (auto-start at login)
systemctl --user enable graphiti-bootstrap

# Start now
systemctl --user start graphiti-bootstrap

# Check status
systemctl --user status graphiti-bootstrap

# View logs
journalctl --user -u graphiti-bootstrap -f
```

---

## Multi-User Port Management

### Problem

If two users are logged in simultaneously on the same machine, both try to bind to port 8321 → conflict.

### Solution: Dynamic Port Assignment

```python
def get_user_port() -> int:
    """
    Get a deterministic port for the current user.

    Uses a hash of the username to generate a port in the range 8321-8399.
    This ensures:
    - Same user always gets same port
    - Different users get different ports (with high probability)
    - Ports are in a reserved range for Graphiti
    """
    import hashlib
    import getpass

    username = getpass.getuser()
    hash_value = int(hashlib.sha256(username.encode()).hexdigest()[:8], 16)

    # Port range: 8321-8399 (79 ports)
    base_port = 8321
    port_range = 79

    return base_port + (hash_value % port_range)
```

**Alternative: User-Configured Port**

Users can explicitly set their port in config:

```json
{
  "daemon": {
    "port": 8325
  }
}
```

**Port Conflict Detection:**

```python
def find_available_port(preferred: int = 8321, max_attempts: int = 10) -> int:
    """Find an available port, starting from preferred."""
    import socket

    for offset in range(max_attempts):
        port = preferred + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue

    raise RuntimeError(f"No available port found in range {preferred}-{preferred + max_attempts}")
```

---

## Directory Structure

### Per-User Layout

```
~/.graphiti/                          # User's Graphiti home
├── graphiti.config.json              # User's configuration
├── .venv/                            # Dedicated Python venv
│   ├── Scripts/ (Windows)            # or bin/ (Unix)
│   │   ├── python.exe
│   │   └── pythonw.exe               # No-console Python (Windows)
│   └── Lib/site-packages/
├── mcp_server/                       # Deployed MCP server code
│   ├── graphiti_mcp_server.py
│   └── daemon/
│       └── bootstrap.py
├── logs/                             # Log files
│   ├── bootstrap-stdout.log
│   ├── bootstrap-stderr.log
│   └── mcp-server.log
├── graphiti-bootstrap-task.xml       # Windows Task Scheduler XML
└── graphiti-mcp.pid                  # PID file (optional)
```

### No System Paths

Unlike v1.0, this architecture does **not** use:
- `C:\ProgramData\Graphiti\` (Windows)
- `/var/lib/graphiti/` (Linux)
- `/usr/local/var/graphiti/` (macOS)

All data is in user home directory.

---

## Code Changes Required

### 1. Replace WindowsServiceManager with WindowsTaskSchedulerManager

**File:** `mcp_server/daemon/windows_service.py` → rename to `windows_task.py`

Remove NSSM dependency entirely. Use Task Scheduler via `schtasks.exe`.

### 2. Update DaemonManager Platform Detection

```python
# mcp_server/daemon/manager.py

def get_service_manager():
    """Get platform-appropriate service manager."""
    import platform

    system = platform.system()
    if system == "Windows":
        from .windows_task import WindowsTaskSchedulerManager
        return WindowsTaskSchedulerManager()
    elif system == "Darwin":
        from .launchd_service import LaunchdServiceManager
        return LaunchdServiceManager()
    elif system == "Linux":
        from .systemd_service import SystemdServiceManager
        return SystemdServiceManager()
    else:
        raise UnsupportedPlatformError(f"Unsupported platform: {system}")
```

### 3. Simplify Path Resolution

Since we're always running as the user, `Path.home()` works correctly:

```python
# No more GRAPHITI_HOME env var needed for path override
# (though we can keep it for testing/development)

def get_graphiti_home() -> Path:
    """Get Graphiti home directory."""
    if home := os.environ.get("GRAPHITI_HOME"):
        return Path(home)
    return Path.home() / ".graphiti"
```

### 4. Remove NSSM Dependency

Remove from installation requirements:
- No NSSM download/detection
- No NSSM instructions in error messages
- No `nssm.exe` path handling

---

## CLI Changes

### Updated Commands

```bash
# Installation (unchanged semantics, different implementation)
graphiti-mcp daemon install    # Register user task/agent/service
graphiti-mcp daemon uninstall  # Remove user task/agent/service

# Observability (unchanged)
graphiti-mcp daemon status     # Show current state
graphiti-mcp daemon logs       # Tail daemon logs

# Manual control (optional, for debugging)
graphiti-mcp daemon start      # Start task/agent now
graphiti-mcp daemon stop       # Stop task/agent now
```

### Status Output

```
$ graphiti-mcp daemon status

Graphiti Daemon Status
======================
Platform:     Windows (Task Scheduler)
Task Name:    GraphitiBootstrap
Status:       Running
User:         Admin
Port:         8321

Bootstrap Process:
  PID:        12345
  Uptime:     2h 34m
  Memory:     45 MB

MCP Server:
  Status:     Running (daemon.enabled: true)
  PID:        12346
  Port:       8321
  Uptime:     2h 34m

Config:       C:\Users\Admin\.graphiti\graphiti.config.json
Logs:         C:\Users\Admin\.graphiti\logs\
```

---

## Migration from v1.0

### For Existing NSSM Installations

```bash
# 1. Stop and remove NSSM service
nssm stop GraphitiBootstrap
nssm remove GraphitiBootstrap confirm

# 2. Install new user-level task
graphiti-mcp daemon install

# 3. Verify
graphiti-mcp daemon status
```

### Automatic Migration

The installer can detect and migrate:

```python
def migrate_from_nssm():
    """Migrate from NSSM system service to Task Scheduler user task."""
    import shutil

    nssm = shutil.which("nssm")
    if not nssm:
        return  # NSSM not installed, nothing to migrate

    # Check if old service exists
    result = subprocess.run(
        [nssm, "status", "GraphitiBootstrap"],
        capture_output=True
    )

    if result.returncode == 0:
        print("Migrating from NSSM system service to user task...")

        # Stop old service
        subprocess.run([nssm, "stop", "GraphitiBootstrap"])

        # Remove old service
        subprocess.run([nssm, "remove", "GraphitiBootstrap", "confirm"])

        print("Old NSSM service removed.")
```

---

## Security Considerations

### Isolation Benefits

1. **No privilege escalation** - User can only affect their own installation
2. **No shared state** - Users cannot access each other's memory graphs
3. **No system-wide impact** - Misconfiguration only affects one user
4. **Clear ownership** - All files owned by the user

### Port Binding

- Binds to `127.0.0.1` only (localhost)
- No network exposure
- Each user has isolated port

### File Permissions

```bash
# Unix: Ensure proper permissions
chmod 700 ~/.graphiti
chmod 600 ~/.graphiti/graphiti.config.json
chmod 600 ~/.graphiti/.env  # If exists
```

---

## Testing

### Test Matrix

| Scenario | Windows | macOS | Linux |
|----------|---------|-------|-------|
| Fresh install | schtasks /create | launchctl load | systemctl --user enable |
| User login auto-start | LogonTrigger | RunAtLoad | WantedBy=default.target |
| Manual start | schtasks /run | launchctl start | systemctl --user start |
| Manual stop | schtasks /end | launchctl stop | systemctl --user stop |
| Uninstall | schtasks /delete | launchctl unload + rm plist | systemctl --user disable |
| Process crash restart | RestartOnFailure | KeepAlive | Restart=on-failure |
| Path.home() correct | Yes (user context) | Yes | Yes |

### Multi-User Test

1. Log in as User A
2. Install daemon, verify running on port 8321
3. Switch to User B (fast user switching)
4. Install daemon, verify running on port 8322 (different)
5. Both users can access their respective MCP servers
6. No collision, no shared state

---

## Appendix: Platform Commands Reference

### Windows Task Scheduler

```powershell
# List tasks
schtasks /query /tn GraphitiBootstrap

# Create task from XML
schtasks /create /tn GraphitiBootstrap /xml task.xml /f

# Run task now
schtasks /run /tn GraphitiBootstrap

# Stop running task
schtasks /end /tn GraphitiBootstrap

# Delete task
schtasks /delete /tn GraphitiBootstrap /f

# Query with full details
schtasks /query /tn GraphitiBootstrap /fo LIST /v
```

### macOS launchctl

```bash
# Load (register and start)
launchctl load ~/Library/LaunchAgents/com.graphiti.bootstrap.plist

# Unload (stop and unregister)
launchctl unload ~/Library/LaunchAgents/com.graphiti.bootstrap.plist

# Start (if loaded but not running)
launchctl start com.graphiti.bootstrap

# Stop (if running)
launchctl stop com.graphiti.bootstrap

# List all user agents
launchctl list | grep graphiti

# Check status
launchctl print gui/$(id -u)/com.graphiti.bootstrap
```

### Linux systemd --user

```bash
# Reload after editing service file
systemctl --user daemon-reload

# Enable (auto-start at login)
systemctl --user enable graphiti-bootstrap

# Disable (no auto-start)
systemctl --user disable graphiti-bootstrap

# Start now
systemctl --user start graphiti-bootstrap

# Stop
systemctl --user stop graphiti-bootstrap

# Status
systemctl --user status graphiti-bootstrap

# Logs
journalctl --user -u graphiti-bootstrap -f

# Enable lingering (run even when not logged in)
loginctl enable-linger $USER
```

---

## Implementation Phases

### Phase 1: Windows Task Scheduler Manager

- [ ] Create `windows_task.py` with `WindowsTaskSchedulerManager`
- [ ] Generate Task XML programmatically
- [ ] Test install/uninstall/start/stop/status
- [ ] Test auto-start at login
- [ ] Test crash recovery (RestartOnFailure)

### Phase 2: Update DaemonManager

- [ ] Replace `WindowsServiceManager` reference with `WindowsTaskSchedulerManager`
- [ ] Remove NSSM detection and error messages
- [ ] Update CLI commands to use new manager

### Phase 3: Migration Logic

- [ ] Detect existing NSSM service
- [ ] Offer migration to user task
- [ ] Clean up old NSSM installation

### Phase 4: Testing

- [ ] Test on Windows 10/11
- [ ] Test on macOS (verify launchd changes if any)
- [ ] Test on Linux (verify systemd --user changes if any)
- [ ] Multi-user isolation test

### Phase 5: Documentation

- [ ] Update installation guide
- [ ] Update troubleshooting guide
- [ ] Document migration from v1.0

---

## References

- [Windows Task Scheduler XML Schema](https://docs.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-schema)
- [schtasks.exe Documentation](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks)
- [launchd.plist Manual](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
- [systemd User Services](https://wiki.archlinux.org/title/Systemd/User)
- [loginctl enable-linger](https://www.freedesktop.org/software/systemd/man/loginctl.html)
