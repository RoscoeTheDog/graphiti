# Graphiti MCP Server: Professional Per-User Daemon Architecture

> **Version**: 2.1.0
> **Status**: DESIGN COMPLETE - Ready for Implementation
> **Created**: 2025-12-25
> **Supersedes**: DAEMON_ARCHITECTURE_SPEC_v2.0.md
> **Design Pattern**: See `MCP_DAEMON_DESIGN_PATTERN.md`

---

## Executive Summary

This document specifies a **professional-grade, per-user daemon architecture** for the Graphiti MCP server that follows industry conventions (Ollama, VS Code, Discord pattern):

1. **Frozen installation** in platform-appropriate Programs directory
2. **Complete separation** of executables, config, and runtime data
3. **Repository-independent** - deleting source repo doesn't break daemon
4. **No admin privileges** required to install
5. **Version tracking** for upgrade detection
6. **Clean uninstall** by removing two directories

### Key Change from v2.0

| Aspect | v2.0 (Home Directory) | v2.1 (Professional Install) |
|--------|----------------------|------------------------------|
| Install location | `~/.graphiti/` | `%LOCALAPPDATA%\Programs\Graphiti\` |
| Package install | Editable (links to repo) | Frozen (copied, versioned) |
| Config location | `~/.graphiti/` | `%LOCALAPPDATA%\Graphiti\config\` |
| Repo dependency | Partial (imports from repo) | None (fully standalone) |
| Version tracking | None | `VERSION` file |
| Upgrade model | Manual | Detectable, scriptable |

### Why This Pattern?

Following the **Ollama/VS Code model**:

1. **Developer tool** - per-user, no admin required
2. **Frozen installs** - repo changes don't break runtime
3. **Clean separation** - Programs vs Config vs Logs
4. **Professional UX** - like installing any quality software

---

## Directory Structure

### Windows

```
%LOCALAPPDATA%\Programs\Graphiti\           # C:\Users\{user}\AppData\Local\Programs\Graphiti\
├── bin\
│   ├── python.exe                          # Python interpreter (from venv)
│   ├── pythonw.exe                         # No-console Python
│   ├── graphiti-mcp.exe                    # CLI wrapper
│   └── graphiti-bootstrap.exe              # Bootstrap entry point (optional)
├── lib\
│   ├── mcp_server\                         # Frozen mcp_server package
│   │   ├── __init__.py
│   │   ├── graphiti_mcp_server.py
│   │   ├── unified_config.py
│   │   ├── daemon\
│   │   │   ├── __init__.py
│   │   │   ├── bootstrap.py
│   │   │   ├── manager.py
│   │   │   └── ...
│   │   └── ...
│   ├── graphiti_core\                      # Frozen graphiti_core package
│   │   └── ...
│   └── site-packages\                      # All pip dependencies
│       └── ...
├── VERSION                                 # e.g., "2.1.0"
└── INSTALL_INFO                            # Install metadata JSON

%LOCALAPPDATA%\Graphiti\                    # C:\Users\{user}\AppData\Local\Graphiti\
├── config\
│   └── graphiti.config.json                # User configuration
├── logs\
│   ├── bootstrap.log                       # Bootstrap service logs
│   ├── mcp-server.log                      # MCP server logs
│   └── install.log                         # Installation logs
├── data\
│   ├── retry_queue.json                    # Failed episode queue
│   └── sessions\                           # Session tracking data
└── templates\                              # User-customizable templates
    └── ...
```

### macOS

```
~/Library/Application Support/Graphiti/     # Install location
├── bin/
├── lib/
├── VERSION
└── INSTALL_INFO

~/Library/Preferences/Graphiti/             # Config
└── graphiti.config.json

~/Library/Logs/Graphiti/                    # Logs
├── bootstrap.log
└── mcp-server.log

~/Library/Caches/Graphiti/                  # Runtime data
└── ...
```

### Linux (XDG Compliant)

```
~/.local/share/graphiti/                    # XDG_DATA_HOME - Install
├── bin/
├── lib/
├── VERSION
└── INSTALL_INFO

~/.config/graphiti/                         # XDG_CONFIG_HOME - Config
└── graphiti.config.json

~/.local/state/graphiti/                    # XDG_STATE_HOME - Logs/State
├── logs/
└── data/

~/.cache/graphiti/                          # XDG_CACHE_HOME - Cache
└── ...
```

---

## Path Resolution

### Python Implementation

```python
import os
import sys
from pathlib import Path
from typing import NamedTuple

class GraphitiPaths(NamedTuple):
    """Platform-specific paths for Graphiti installation."""
    install_dir: Path      # Executables and libraries
    config_dir: Path       # User configuration
    state_dir: Path        # Logs, data, runtime state
    config_file: Path      # Main config file path

def get_paths() -> GraphitiPaths:
    """Get platform-appropriate Graphiti paths."""

    if sys.platform == "win32":
        local_app_data = Path(os.environ.get(
            "LOCALAPPDATA",
            Path.home() / "AppData" / "Local"
        ))
        install_dir = local_app_data / "Programs" / "Graphiti"
        config_dir = local_app_data / "Graphiti" / "config"
        state_dir = local_app_data / "Graphiti"

    elif sys.platform == "darwin":
        install_dir = Path.home() / "Library" / "Application Support" / "Graphiti"
        config_dir = Path.home() / "Library" / "Preferences" / "Graphiti"
        state_dir = Path.home() / "Library" / "Logs" / "Graphiti"

    else:  # Linux and others (XDG)
        xdg_data = Path(os.environ.get(
            "XDG_DATA_HOME",
            Path.home() / ".local" / "share"
        ))
        xdg_config = Path(os.environ.get(
            "XDG_CONFIG_HOME",
            Path.home() / ".config"
        ))
        xdg_state = Path(os.environ.get(
            "XDG_STATE_HOME",
            Path.home() / ".local" / "state"
        ))

        install_dir = xdg_data / "graphiti"
        config_dir = xdg_config / "graphiti"
        state_dir = xdg_state / "graphiti"

    return GraphitiPaths(
        install_dir=install_dir,
        config_dir=config_dir,
        state_dir=state_dir,
        config_file=config_dir / "graphiti.config.json"
    )

# Convenience accessors
def get_install_dir() -> Path:
    return get_paths().install_dir

def get_config_dir() -> Path:
    return get_paths().config_dir

def get_config_file() -> Path:
    return get_paths().config_file

def get_log_dir() -> Path:
    paths = get_paths()
    if sys.platform == "darwin":
        return paths.state_dir  # Already points to Logs
    return paths.state_dir / "logs"

def get_data_dir() -> Path:
    paths = get_paths()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "Graphiti"
    return paths.state_dir / "data"
```

---

## Installation Process

### Step-by-Step

```
1. VALIDATE ENVIRONMENT
   ├── Check Python version >= 3.10
   ├── Check available disk space (>500MB)
   ├── Check no conflicting installation (or offer upgrade)
   └── Check network connectivity (for pip)

2. CREATE DIRECTORY STRUCTURE
   ├── {INSTALL}/bin/
   ├── {INSTALL}/lib/
   ├── {CONFIG}/
   ├── {STATE}/logs/
   └── {STATE}/data/

3. CREATE VIRTUAL ENVIRONMENT
   ├── python -m venv {INSTALL}/.venv
   └── Activate for subsequent operations

4. INSTALL DEPENDENCIES
   ├── pip install -r requirements.txt
   └── Includes: graphiti-core, mcp, openai, neo4j, etc.

5. FREEZE PACKAGES TO lib/
   ├── Copy mcp_server/ package to {INSTALL}/lib/mcp_server/
   ├── Copy graphiti_core/ package to {INSTALL}/lib/graphiti_core/
   ├── Ensure all __init__.py files present
   └── Remove .pyc, __pycache__, .git if present

6. CREATE BIN WRAPPERS
   ├── graphiti-mcp.exe/.sh → invokes python -m mcp_server.cli
   └── Ensure wrappers use {INSTALL}/bin/python

7. WRITE VERSION INFO
   ├── VERSION file with semantic version
   └── INSTALL_INFO with metadata (date, source commit, Python version)

8. CREATE DEFAULT CONFIG
   ├── Only if {CONFIG}/graphiti.config.json doesn't exist
   └── Preserve existing config on upgrade

9. REGISTER OS SERVICE
   ├── Windows: schtasks /create with Task XML
   ├── macOS: cp plist to ~/Library/LaunchAgents/ + launchctl load
   └── Linux: cp unit to ~/.config/systemd/user/ + systemctl --user enable

10. START SERVICE
    ├── Start immediately (don't wait for next login)
    └── Verify health check passes

11. DISPLAY SUCCESS
    ├── Show installed version
    ├── Show config location
    ├── Show how to check status
    └── Show PATH instructions if needed
```

### Installer Code Structure

```python
# mcp_server/daemon/installer.py

class GraphitiInstaller:
    """Professional-grade Graphiti MCP server installer."""

    def __init__(self):
        self.paths = get_paths()
        self.service_manager = get_service_manager()

    def install(self, source_dir: Path = None) -> bool:
        """
        Install Graphiti MCP server.

        Args:
            source_dir: Path to source repo (default: auto-detect)

        Returns:
            True if installation successful
        """
        try:
            self._validate_environment()
            self._create_directories()
            self._create_venv()
            self._install_dependencies()
            self._freeze_packages(source_dir)
            self._create_wrappers()
            self._write_version_info(source_dir)
            self._create_default_config()
            self._register_service()
            self._start_service()
            self._verify_installation()
            return True
        except InstallationError as e:
            self._cleanup_on_failure()
            raise

    def upgrade(self, source_dir: Path = None) -> bool:
        """Upgrade existing installation."""
        # Stop service
        # Backup lib/
        # Freeze new packages
        # Update VERSION
        # Start service
        # Verify health
        # Remove backup (or rollback)
        pass

    def uninstall(self, keep_config: bool = True) -> bool:
        """Uninstall Graphiti MCP server."""
        # Stop service
        # Unregister service
        # Remove install dir
        # Optionally remove config/state dirs
        pass
```

---

## Service Configuration

### Task Scheduler (Windows)

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Graphiti MCP Bootstrap Service</Description>
    <Author>Graphiti</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{CURRENT_USER}</UserId>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{CURRENT_USER}</UserId>
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
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions>
    <Exec>
      <Command>{INSTALL_DIR}\bin\pythonw.exe</Command>
      <Arguments>-m mcp_server.daemon.bootstrap</Arguments>
      <WorkingDirectory>{INSTALL_DIR}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

**Key Points:**
- Uses `{INSTALL_DIR}\bin\pythonw.exe` (frozen Python, no console)
- Working directory is install dir (not repo)
- `-m mcp_server.daemon.bootstrap` uses frozen package in lib/

### launchd (macOS)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.graphiti.bootstrap</string>

    <key>ProgramArguments</key>
    <array>
        <string>{INSTALL_DIR}/bin/python</string>
        <string>-m</string>
        <string>mcp_server.daemon.bootstrap</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{INSTALL_DIR}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>{INSTALL_DIR}/lib</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>{LOG_DIR}/bootstrap.log</string>

    <key>StandardErrorPath</key>
    <string>{LOG_DIR}/bootstrap.log</string>
</dict>
</plist>
```

### systemd (Linux)

```ini
[Unit]
Description=Graphiti MCP Bootstrap Service
After=default.target

[Service]
Type=simple
ExecStart={INSTALL_DIR}/bin/python -m mcp_server.daemon.bootstrap
WorkingDirectory={INSTALL_DIR}
Environment="PYTHONPATH={INSTALL_DIR}/lib"
Restart=on-failure
RestartSec=5

StandardOutput=append:{LOG_DIR}/bootstrap.log
StandardError=append:{LOG_DIR}/bootstrap.log

[Install]
WantedBy=default.target
```

---

## Bootstrap Module Updates

### Updated Path Resolution

```python
# mcp_server/daemon/bootstrap.py

import sys
from pathlib import Path

# Add frozen lib to path BEFORE any imports
def _setup_frozen_path():
    """Ensure frozen packages in lib/ are importable."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base = Path(sys.executable).parent.parent
    else:
        # Running as script - find install dir
        # bootstrap.py is in {INSTALL}/lib/mcp_server/daemon/
        base = Path(__file__).parent.parent.parent.parent

    lib_path = base / "lib"
    if lib_path.exists() and str(lib_path) not in sys.path:
        sys.path.insert(0, str(lib_path))

_setup_frozen_path()

# Now safe to import from frozen packages
from mcp_server.daemon.paths import get_paths, get_config_file, get_log_dir

class BootstrapService:
    def __init__(self):
        self.paths = get_paths()
        self.config_path = get_config_file()
        self.log_dir = get_log_dir()
        # ... rest of init

    def _get_mcp_server_path(self) -> Path:
        """Get path to MCP server module."""
        # In v2.1, always use frozen package
        return self.paths.install_dir / "lib" / "mcp_server" / "graphiti_mcp_server.py"
```

---

## Version Tracking

### VERSION File

Plain text file with semantic version:

```
2.1.0
```

### INSTALL_INFO File

JSON with installation metadata:

```json
{
  "version": "2.1.0",
  "installed_at": "2025-12-25T10:30:00Z",
  "installed_from": "C:\\Users\\Admin\\Documents\\GitHub\\graphiti",
  "source_commit": "abc123def456",
  "python_version": "3.10.18",
  "platform": "Windows-10-10.0.26100-SP0",
  "installer_version": "1.0.0"
}
```

### Upgrade Detection

```python
def check_for_upgrade(source_dir: Path) -> tuple[bool, str, str]:
    """
    Check if upgrade is available.

    Returns:
        (upgrade_available, installed_version, available_version)
    """
    installed = get_installed_version()
    available = get_source_version(source_dir)

    if installed is None:
        return (True, "not installed", available)

    from packaging import version
    return (
        version.parse(available) > version.parse(installed),
        installed,
        available
    )
```

---

## Migration from v2.0

### Migration Path

```
1. DETECT v2.0 INSTALLATION
   ├── Check ~/.graphiti/ exists
   ├── Check for Task Scheduler task "GraphitiBootstrap_*"
   └── Read ~/.graphiti/graphiti.config.json

2. BACKUP v2.0 CONFIG
   └── Copy ~/.graphiti/graphiti.config.json to temp

3. STOP v2.0 SERVICE
   ├── Stop Task Scheduler task
   └── Kill any running graphiti processes

4. INSTALL v2.1
   └── Follow normal installation process

5. MIGRATE CONFIG
   ├── Copy backed-up config to {CONFIG}/graphiti.config.json
   └── Merge any v2.1-specific defaults

6. CLEANUP v2.0
   ├── Unregister old Task Scheduler task
   └── Prompt: Remove ~/.graphiti/? (preserve logs/data option)

7. VERIFY
   └── Run health check on new installation
```

### Migration Script

```python
def migrate_from_v2_0() -> bool:
    """Migrate from v2.0 (~/.graphiti) to v2.1 (LOCALAPPDATA)."""

    old_home = Path.home() / ".graphiti"
    if not old_home.exists():
        return False  # Nothing to migrate

    print("Detected v2.0 installation at ~/.graphiti/")
    print("Migrating to v2.1 architecture...")

    # Backup config
    old_config = old_home / "graphiti.config.json"
    if old_config.exists():
        config_backup = old_config.read_text()

    # Stop old service
    old_task_name = f"GraphitiBootstrap_{getpass.getuser()}"
    subprocess.run(["schtasks", "/End", "/TN", old_task_name],
                   capture_output=True)
    subprocess.run(["schtasks", "/Delete", "/TN", old_task_name, "/F"],
                   capture_output=True)

    # Install v2.1 (normal process)
    installer = GraphitiInstaller()
    installer.install()

    # Restore config
    if config_backup:
        new_config = get_config_file()
        new_config.write_text(config_backup)

    # Prompt for cleanup
    response = input("Remove old ~/.graphiti/ directory? (y/n): ")
    if response.lower() == 'y':
        shutil.rmtree(old_home)
        print("Old installation removed.")
    else:
        print(f"Old installation preserved at {old_home}")

    return True
```

---

## CLI Updates

### Commands

```bash
# Install (includes migration detection)
graphiti-mcp daemon install

# Upgrade (from repo)
graphiti-mcp daemon upgrade

# Uninstall
graphiti-mcp daemon uninstall [--keep-config] [--keep-data]

# Status
graphiti-mcp daemon status

# Logs
graphiti-mcp daemon logs [-f] [-n 50]

# Version info
graphiti-mcp daemon version
```

### Status Output (v2.1)

```
$ graphiti-mcp daemon status

Graphiti MCP Server Status
==========================

Installation:
  Version:     2.1.0
  Location:    C:\Users\Admin\AppData\Local\Programs\Graphiti
  Installed:   2025-12-25 10:30:00

Service:
  Platform:    Windows (Task Scheduler)
  Task Name:   GraphitiBootstrap_Admin
  Status:      Running

Bootstrap:
  PID:         12345
  Uptime:      2h 34m

MCP Server:
  Status:      Running (daemon.enabled: true)
  URL:         http://127.0.0.1:8321
  Health:      OK

Paths:
  Config:      C:\Users\Admin\AppData\Local\Graphiti\config\graphiti.config.json
  Logs:        C:\Users\Admin\AppData\Local\Graphiti\logs\
  Data:        C:\Users\Admin\AppData\Local\Graphiti\data\
```

---

## Implementation Phases

### Phase 1: Path Infrastructure

- [ ] Create `mcp_server/daemon/paths.py` with platform-aware path resolution
- [ ] Update all modules to use new path functions
- [ ] Add unit tests for path resolution on all platforms

### Phase 2: Installer Overhaul

- [ ] Create `mcp_server/daemon/installer.py` with `GraphitiInstaller` class
- [ ] Implement frozen package deployment (copy, not editable install)
- [ ] Implement VERSION and INSTALL_INFO generation
- [ ] Add upgrade detection and handling

### Phase 3: Service Manager Updates

- [ ] Update `WindowsTaskSchedulerManager` to use new paths
- [ ] Update `LaunchdServiceManager` to use new paths
- [ ] Update `SystemdServiceManager` to use new paths
- [ ] Fix bootstrap invocation (`-m mcp_server.daemon.bootstrap`)

### Phase 4: Migration

- [ ] Implement v2.0 detection
- [ ] Implement config migration
- [ ] Implement old installation cleanup
- [ ] Test migration on Windows

### Phase 5: Testing

- [ ] Fresh install on clean Windows system
- [ ] Upgrade from v2.0 to v2.1
- [ ] Service auto-start on login
- [ ] MCP server health check
- [ ] Uninstall (with and without keep-config)

### Phase 6: Documentation

- [ ] Update installation guide
- [ ] Document migration process
- [ ] Update troubleshooting guide
- [ ] Update CONFIGURATION.md with new paths

---

## Appendix: Comparison with v2.0

| Component | v2.0 Location | v2.1 Location |
|-----------|---------------|---------------|
| Python venv | `~/.graphiti/.venv/` | `%LOCALAPPDATA%\Programs\Graphiti\bin\` |
| mcp_server package | `~/.graphiti/mcp_server/` (copied) | `%LOCALAPPDATA%\Programs\Graphiti\lib\mcp_server\` |
| graphiti_core | Imported from repo | `%LOCALAPPDATA%\Programs\Graphiti\lib\graphiti_core\` |
| Config file | `~/.graphiti/graphiti.config.json` | `%LOCALAPPDATA%\Graphiti\config\graphiti.config.json` |
| Logs | `~/.graphiti/logs/` | `%LOCALAPPDATA%\Graphiti\logs\` |
| Runtime data | `~/.graphiti/` | `%LOCALAPPDATA%\Graphiti\data\` |
| VERSION file | None | `%LOCALAPPDATA%\Programs\Graphiti\VERSION` |

---

## References

- **Design Pattern**: `MCP_DAEMON_DESIGN_PATTERN.md` (this repo)
- **Previous Version**: `DAEMON_ARCHITECTURE_SPEC_v2.0.md`
- **Ollama Installation**: https://github.com/ollama/ollama
- **VS Code User Install**: https://code.visualstudio.com/docs/setup/windows
- **XDG Base Directory Spec**: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
