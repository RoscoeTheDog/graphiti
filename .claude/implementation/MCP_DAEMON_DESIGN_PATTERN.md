# MCP Daemon Design Pattern v1.0

**Status**: ACTIVE
**Created**: 2025-12-25
**Scope**: Reusable architecture pattern for MCP servers requiring persistent daemon services

---

## Overview

This document defines a standardized design pattern for deploying MCP (Model Context Protocol) servers as persistent, per-user daemon services. The pattern is designed for:

- **Developer tools** that integrate with AI assistants (Claude, etc.)
- **Localhost servers** that need to persist across sessions
- **Per-user isolation** without requiring admin privileges
- **Professional-grade deployment** separate from source repositories

### Target Use Cases

1. Knowledge graph servers (Graphiti)
2. Code indexing servers (Claude-Context)
3. Research/retrieval servers (GPT-Researcher MCP)
4. Any MCP server requiring persistent state or background processing

---

## Design Principles

### 1. Repository Independence

The installed daemon MUST be completely independent of the source repository:

- **No symlinks** to repo directories
- **No editable installs** (`pip install -e`)
- **Frozen packages** copied to install location
- **Version tracking** via VERSION file

**Rationale**: Users should be able to delete, move, or modify the source repo without affecting the running daemon.

### 2. No Admin Privileges Required

Installation MUST NOT require elevated privileges:

- Use per-user installation locations
- Use per-user service managers (Task Scheduler user tasks, launchd LaunchAgents, systemd --user)
- No writes to `C:\Program Files\`, `/usr/local/`, or system directories

**Rationale**: Developers should install without IT approval or UAC prompts.

### 3. Separation of Concerns

Three distinct directory trees with different lifecycles:

| Category | Contents | Lifecycle | User Editable |
|----------|----------|-----------|---------------|
| **Programs** | Executables, libraries, VERSION | Install-time, replaced on upgrade | No |
| **Config** | User configuration files | Persistent across upgrades | Yes |
| **State** | Logs, caches, runtime data | Machine-generated, purgeable | No |

### 4. Per-User Isolation

Each user on a multi-user system gets:

- Their own installation
- Their own configuration
- Their own service instance
- Their own port assignment (if applicable)

**Rationale**: Prevents conflicts, enables different versions per user, maintains privacy.

### 5. Two-Layer Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    OS Service Manager                    │
│         (Task Scheduler / launchd / systemd)            │
└─────────────────────────┬───────────────────────────────┘
                          │ starts/monitors
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Bootstrap Service                      │
│              (lightweight, always running)               │
│                                                         │
│  • Watches config file for changes                      │
│  • Starts/stops MCP server based on daemon.enabled      │
│  • Restarts MCP server on crash                         │
│  • Handles graceful shutdown                            │
└─────────────────────────┬───────────────────────────────┘
                          │ manages
                          ▼
┌─────────────────────────────────────────────────────────┐
│                     MCP Server                           │
│              (the actual functionality)                  │
│                                                         │
│  • HTTP/SSE transport on localhost                      │
│  • Implements MCP tools                                 │
│  • Connects to databases, APIs, etc.                    │
└─────────────────────────────────────────────────────────┘
```

**Rationale**:
- Bootstrap is simple and unlikely to crash
- MCP server can be restarted without service reinstall
- Config changes take effect without service restart
- Single control point (config file) for state management

---

## Directory Structure

### Windows

```
%LOCALAPPDATA%\Programs\{AppName}\          # Install location
├── bin\
│   ├── python.exe                          # Python interpreter (or wrapper)
│   ├── {appname}.exe                       # CLI entry point
│   └── {appname}-bootstrap.exe             # Bootstrap service
├── lib\
│   ├── {package_name}\                     # Main package (frozen)
│   ├── {dependency}\                       # Dependencies (frozen)
│   └── site-packages\                      # All pip packages
├── VERSION                                 # Semantic version (e.g., "2.1.0")
└── INSTALL_INFO                            # Install metadata (date, source, etc.)

%LOCALAPPDATA%\{AppName}\                   # Runtime location
├── config\
│   └── {appname}.config.json               # User configuration
├── logs\
│   ├── bootstrap.log                       # Bootstrap service logs
│   └── server.log                          # MCP server logs
├── data\
│   └── {runtime_files}                     # Queues, caches, state
└── templates\                              # User-customizable templates
```

### macOS

```
~/Library/Application Support/{AppName}/    # Install location
├── bin/
├── lib/
├── VERSION
└── INSTALL_INFO

~/Library/Preferences/{AppName}/            # Config
└── {appname}.config.json

~/Library/Logs/{AppName}/                   # Logs
├── bootstrap.log
└── server.log

~/Library/Caches/{AppName}/                 # Cache/State
└── {runtime_files}
```

### Linux (XDG Compliant)

```
~/.local/share/{appname}/                   # XDG_DATA_HOME - Install
├── bin/
├── lib/
├── VERSION
└── INSTALL_INFO

~/.config/{appname}/                        # XDG_CONFIG_HOME - Config
└── {appname}.config.json

~/.local/state/{appname}/                   # XDG_STATE_HOME - Logs/State
├── logs/
└── data/

~/.cache/{appname}/                         # XDG_CACHE_HOME - Cache
└── {cache_files}
```

---

## Configuration Schema

### Minimum Required Configuration

```json
{
  "daemon": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8321,
    "log_level": "INFO"
  }
}
```

### Full Configuration Template

```json
{
  "$schema": "https://example.com/schemas/{appname}.config.schema.json",
  "_version": "1.0",

  "daemon": {
    "_comment": "Daemon service configuration",
    "enabled": true,
    "_enabled_help": "Master switch: false = server stopped, true = server running",

    "host": "127.0.0.1",
    "_host_help": "Bind address. Use 127.0.0.1 for localhost-only (secure default)",

    "port": 8321,
    "_port_help": "HTTP port. null = auto-assign based on username hash",

    "transport": "sse",
    "_transport_help": "MCP transport: 'sse' (recommended) or 'stdio'",

    "log_level": "INFO",
    "_log_level_help": "DEBUG | INFO | WARNING | ERROR | CRITICAL",

    "config_poll_seconds": 5,
    "_config_poll_seconds_help": "How often bootstrap checks this file for changes",

    "health_check_interval": 30,
    "_health_check_interval_help": "Seconds between MCP server health checks"
  },

  "server": {
    "_comment": "MCP server-specific configuration",
    "// additional fields specific to each MCP server": null
  }
}
```

### Configuration Discovery Order

1. `--config` CLI argument (explicit path)
2. `{CONFIG_DIR}/{appname}.config.json` (platform default)
3. Environment variable `{APPNAME}_CONFIG`
4. Built-in defaults

---

## Service Management

### Platform-Specific Service Managers

| Platform | Service Manager | Install Method | User Context |
|----------|----------------|----------------|--------------|
| Windows | Task Scheduler | `schtasks.exe` | LogonTrigger, InteractiveToken |
| macOS | launchd | LaunchAgent plist | ~/Library/LaunchAgents/ |
| Linux | systemd | `systemctl --user` | User unit in ~/.config/systemd/user/ |

### Service Lifecycle Commands

```bash
# Install (registers service + starts it)
{appname} daemon install

# Uninstall (stops service + removes registration)
{appname} daemon uninstall

# Status (shows install state, running state, config)
{appname} daemon status

# Logs (tail daemon logs)
{appname} daemon logs [-f] [-n 50]
```

### Runtime Control via Config (NOT via CLI)

**Important**: After installation, runtime control is via config file only:

```bash
# To stop the MCP server:
# Edit config: daemon.enabled = false
# (Bootstrap detects change within poll interval, stops server)

# To restart the MCP server:
# Edit config: daemon.enabled = false, wait, set true
# (Or just save the file - change detection triggers restart)
```

**Rationale**: Single source of truth. No state mismatch between CLI and config.

---

## Port Assignment Strategy

### Static Ports (Simple)

```json
{
  "daemon": {
    "port": 8321
  }
}
```

### Dynamic Per-User Ports (Multi-User Systems)

For systems with multiple users, assign ports deterministically by username:

```python
import hashlib

def get_user_port(username: str, base_port: int = 8321, range_size: int = 100) -> int:
    """
    Generate deterministic port from username.

    Args:
        username: OS username
        base_port: Start of port range (default 8321)
        range_size: Size of port range (default 100, so 8321-8420)

    Returns:
        Port number in range [base_port, base_port + range_size)
    """
    hash_bytes = hashlib.sha256(username.encode()).digest()
    offset = int.from_bytes(hash_bytes[:2], 'big') % range_size
    return base_port + offset
```

**Config**:
```json
{
  "daemon": {
    "port": null,
    "_port_help": "null = auto-assign 8321-8420 based on username"
  }
}
```

---

## Installer Implementation

### Installation Steps

```
1. Validate environment
   ├── Check Python version (>= 3.10)
   ├── Check available disk space
   └── Check no conflicting installation

2. Create directory structure
   ├── {PROGRAMS}/{AppName}/bin/
   ├── {PROGRAMS}/{AppName}/lib/
   ├── {RUNTIME}/config/
   ├── {RUNTIME}/logs/
   └── {RUNTIME}/data/

3. Create/update virtual environment
   ├── Create venv in {PROGRAMS}/{AppName}/
   ├── Install dependencies from requirements.txt
   └── Install main package (non-editable)

4. Deploy frozen packages
   ├── Copy package source to lib/
   ├── Write VERSION file
   └── Write INSTALL_INFO metadata

5. Generate CLI wrappers
   ├── Create {appname}.exe/.sh in bin/
   └── Display PATH instructions

6. Create default config (if not exists)
   └── Write {appname}.config.json with defaults

7. Register OS service
   ├── Generate service definition (XML/plist/unit)
   ├── Register with service manager
   └── Start service immediately

8. Verify installation
   ├── Check service is running
   ├── Health check MCP server
   └── Display success message
```

### Upgrade Handling

```
1. Stop MCP server (via config: enabled = false)
2. Backup current lib/ to lib.backup/
3. Deploy new packages to lib/
4. Update VERSION
5. Restart MCP server (via config: enabled = true)
6. Verify health
7. Remove backup (or rollback on failure)
```

### Uninstallation

```
1. Stop service
2. Unregister from service manager
3. Remove {PROGRAMS}/{AppName}/ entirely
4. Prompt: Keep config/logs/data? (default: yes)
5. If no: Remove {RUNTIME}/{AppName}/ entirely
```

---

## Claude Desktop Integration

### MCP Configuration Entry

```json
{
  "mcpServers": {
    "{appname}": {
      "type": "sse",
      "url": "http://localhost:8321/sse"
    }
  }
}
```

### Auto-Discovery (Future Enhancement)

Daemons could register themselves in a well-known location:

```
%LOCALAPPDATA%\Claude\mcp-daemons\
└── {appname}.json
    {
      "name": "{AppName}",
      "transport": "sse",
      "url": "http://localhost:8321/sse",
      "health": "http://localhost:8321/health",
      "version": "2.1.0"
    }
```

---

## Security Considerations

### Localhost Binding

- **ALWAYS** default to `127.0.0.1` (IPv4 localhost)
- **NEVER** default to `0.0.0.0` (all interfaces)
- Log security warning if user configures non-localhost binding

### Config File Permissions

- Config files should be readable/writable by owner only
- Windows: Default ACLs for user profile are sufficient
- Unix: `chmod 600 {appname}.config.json`

### Secrets Management

- **NEVER** store secrets in config file directly
- Use environment variable references: `"password_env": "NEO4J_PASSWORD"`
- Or use OS keychain integration

### No Elevation

- Daemon runs as current user, not SYSTEM/root
- No access to other users' data
- Cannot bind to privileged ports (<1024)

---

## Error Handling

### Bootstrap Failure Modes

| Failure | Bootstrap Behavior | User Action |
|---------|-------------------|-------------|
| Config file missing | Create default, continue | None (auto-recovery) |
| Config JSON invalid | Log error, use defaults | Fix JSON syntax |
| MCP server crash | Restart after 30s | Check server logs |
| MCP server won't start | Log error, keep trying | Check dependencies/config |
| Port in use | Log error, keep trying | Change port in config |

### Health Check Endpoints

MCP server SHOULD expose:

```
GET /health
Response: {"status": "healthy", "version": "2.1.0", "uptime_seconds": 3600}

GET /metrics (optional)
Response: {"connections": 5, "requests": 1000, "errors": 2}
```

---

## Logging Standards

### Log Format

```
{timestamp} - {logger_name} - {level} - {message}
2025-12-25 10:30:00,123 - graphiti.bootstrap - INFO - MCP server started (PID: 1234)
```

### Log Rotation

```json
{
  "daemon": {
    "log_rotation": {
      "max_bytes": 10485760,
      "backup_count": 5
    }
  }
}
```

### Log Levels by Component

| Component | Default Level | When to Use DEBUG |
|-----------|--------------|-------------------|
| Bootstrap | INFO | Service startup issues |
| MCP Server | INFO | Request/response tracing |
| Database | WARNING | Connection debugging |

---

## Testing Checklist

### Installation Tests

- [ ] Fresh install on clean system
- [ ] Install with existing config (preserves config)
- [ ] Install with incompatible Python version (fails gracefully)
- [ ] Install with insufficient disk space (fails gracefully)

### Upgrade Tests

- [ ] Upgrade preserves config
- [ ] Upgrade preserves logs
- [ ] Rollback on failed upgrade

### Runtime Tests

- [ ] Service starts on user login
- [ ] MCP server restarts on crash
- [ ] Config change detected and applied
- [ ] Graceful shutdown on service stop

### Multi-User Tests

- [ ] Two users on same machine, independent instances
- [ ] Port conflicts avoided (dynamic assignment)
- [ ] No file permission conflicts

---

## Reference Implementations

- **Graphiti MCP Server**: First implementation of this pattern
- **See**: `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v2.1.md`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-25 | Initial pattern definition |

---

## Appendix: Platform Path Resolution

### Python Implementation

```python
import os
import sys
from pathlib import Path

def get_install_dir(app_name: str) -> Path:
    """Get platform-appropriate installation directory."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        return Path(local_app_data) / "Programs" / app_name
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    else:  # Linux and others
        xdg_data = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        return Path(xdg_data) / app_name.lower()

def get_config_dir(app_name: str) -> Path:
    """Get platform-appropriate configuration directory."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        return Path(local_app_data) / app_name / "config"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Preferences" / app_name
    else:  # Linux and others
        xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        return Path(xdg_config) / app_name.lower()

def get_state_dir(app_name: str) -> Path:
    """Get platform-appropriate state/logs directory."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        return Path(local_app_data) / app_name
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / app_name
    else:  # Linux and others
        xdg_state = os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")
        return Path(xdg_state) / app_name.lower()
```
