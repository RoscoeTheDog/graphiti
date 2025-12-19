# Graphiti Daemon Architecture

Complete architectural overview of Graphiti's daemon system, including virtual environment organization, bootstrap service, and multi-session support.

**Version**: v1.0.0
**Last Updated**: 2025-12-18

---

## Table of Contents

1. [Overview](#overview)
2. [Virtual Environment Architecture](#virtual-environment-architecture)
3. [Directory Structure](#directory-structure)
4. [Bootstrap Service](#bootstrap-service)
5. [Installation Flow](#installation-flow)
6. [Multi-Session Support](#multi-session-support)
7. [Platform-Specific Details](#platform-specific-details)

---

## Overview

The Graphiti daemon provides a persistent MCP server that runs as a background service. This architecture enables:

- **Always-on MCP Server**: No need to start the server manually for each Claude Code session
- **Multi-session Support**: Multiple Claude Code windows share one daemon instance
- **Configuration Watching**: Daemon responds to config changes without restart
- **Isolated Dependencies**: Daemon has its own virtual environment, separate from your projects

### Key Design Decisions

1. **User-global daemon**: One daemon per user (not per-project)
2. **Isolated venv**: Daemon dependencies don't conflict with project dependencies
3. **Decoupled from repository**: Daemon works even if you delete/move the graphiti repo
4. **Bootstrap service**: Lightweight watcher that manages MCP server lifecycle

---

## Virtual Environment Architecture

### Two Separate Virtual Environments

Graphiti uses **two separate venvs** for different purposes:

| venv Location | Purpose | Created By | Lifetime |
|--------------|---------|------------|----------|
| `~/.graphiti/.venv/` | **Daemon venv** - Runs MCP server as background service | `graphiti-mcp daemon install` | Persistent (survives repo deletion) |
| `{project}/.venv/` | **Project venv** - For development/direct library usage | Manual setup | Per-project |

### Why Two Separate Environments?

```
~/.graphiti/                    # User-global daemon installation
├── .venv/                      # Daemon's isolated virtual environment
│   ├── bin/ or Scripts/        # Python executable + installed scripts
│   └── lib/site-packages/      # Daemon dependencies (mcp_server, etc.)
├── bin/                        # CLI wrapper scripts (graphiti-mcp)
├── graphiti.config.json        # Global configuration
└── logs/                       # Daemon log files

~/Documents/GitHub/graphiti/    # Cloned repository (example)
├── .venv/                      # Development venv (optional)
├── mcp_server/                 # Source code
└── tests/                      # Tests
```

### Rationale for Daemon venv at `~/.graphiti/`

**1. Decoupling from Repository**
- The daemon runs independently of where (or if) graphiti is cloned
- You can delete/move the repo without breaking the daemon
- Different machines can have different clone locations

**2. Single Daemon per User**
- Prevents multiple MCP server instances competing
- All Claude Code sessions share one daemon
- Consistent state across all projects

**3. Dependency Isolation**
- Daemon dependencies don't conflict with project dev dependencies
- Can run different versions (daemon uses stable release, project uses dev branch)
- Clean separation of concerns

**4. Bootstrap Resilience**
- Bootstrap service always knows where to find the daemon
- Fixed location simplifies service configuration
- Survives Python version upgrades in project venv

### What This Is NOT

This is **not** a shared venv across multiple MCP servers. The architecture is:

```
User Machine:
├── ~/.graphiti/.venv/          # ONE daemon venv (Graphiti MCP only)
├── ~/.other-mcp/.venv/         # Different MCP server (separate)
├── ~/project-1/.venv/          # Project 1 dev environment
└── ~/project-2/.venv/          # Project 2 dev environment
```

Each MCP server (Graphiti, Context7, etc.) has its own isolated installation. They don't share a venv.

---

## Directory Structure

### `~/.graphiti/` (User Home)

```
~/.graphiti/
├── .venv/                      # Daemon virtual environment
│   ├── bin/                    # Unix: python, pip, etc.
│   ├── Scripts/                # Windows: python.exe, pip.exe, etc.
│   ├── lib/                    # Installed packages
│   └── pyvenv.cfg              # Venv configuration
├── bin/                        # CLI wrapper scripts
│   ├── graphiti-mcp            # Unix wrapper script
│   └── graphiti-mcp.bat        # Windows wrapper script
├── graphiti.config.json        # Main configuration file
├── logs/                       # Service log files
│   ├── bootstrap.log           # Bootstrap service logs
│   └── mcp-server.log          # MCP server logs
└── daemon/                     # Platform service files
    ├── graphiti-bootstrap.plist    # macOS launchd
    ├── graphiti-bootstrap.service  # Linux systemd
    └── nssm.exe                    # Windows service manager
```

### Project Directory (Optional)

```
~/Documents/GitHub/graphiti/    # Or wherever you clone
├── .venv/                      # Development venv (optional)
│   └── ...                     # For running tests, development
├── graphiti.config.json        # Project-level config (overrides global)
├── mcp_server/                 # Source code
├── graphiti_core/              # Core library
└── tests/                      # Test suite
```

---

## Bootstrap Service

The bootstrap service is a lightweight process that:

1. **Watches configuration**: Monitors `~/.graphiti/graphiti.config.json` for changes
2. **Manages MCP server**: Starts/stops MCP server based on `daemon.enabled` flag
3. **Auto-recovery**: Restarts MCP server if it crashes
4. **Runs at boot**: Installed as a system service

### Bootstrap vs MCP Server

```
┌─────────────────────────────────────────────────────────────┐
│                    Bootstrap Service                         │
│                  (Always running, ~5MB RAM)                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Config Watcher                                       │    │
│  │ - Polls ~/.graphiti/graphiti.config.json every 5s   │    │
│  │ - Detects daemon.enabled changes                    │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │ MCP Server Manager                                   │    │
│  │ - Starts MCP server when daemon.enabled = true      │    │
│  │ - Stops MCP server when daemon.enabled = false      │    │
│  │ - Restarts on crash (with backoff)                  │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
           ┌──────────────▼──────────────┐
           │       MCP Server            │
           │   (When enabled, ~100MB)    │
           │                             │
           │  - HTTP transport           │
           │  - Neo4j connection         │
           │  - Session tracking         │
           │  - Memory operations        │
           └─────────────────────────────┘
```

### Configuration Flow

```
User edits graphiti.config.json
           │
           ▼
Bootstrap detects change (5s polling)
           │
           ▼
daemon.enabled = true? ───No───► Stop MCP server (if running)
           │
          Yes
           │
           ▼
Start MCP server (if not running)
           │
           ▼
MCP server listens on http://127.0.0.1:8321
           │
           ▼
Claude Code connects via HTTP/SSE transport
```

---

## Installation Flow

### What Happens During `graphiti-mcp daemon install`

```
Step 1: VenvManager.create_venv()
        │
        ├─► Check Python version (>=3.10 required)
        ├─► Create ~/.graphiti/.venv/ (uses uv if available, else python -m venv)
        └─► Validate venv creation succeeded

Step 2: VenvManager.install_package()
        │
        ├─► Install mcp_server package into ~/.graphiti/.venv/
        └─► Uses pip or uv depending on availability

Step 3: WrapperGenerator.generate_wrappers()
        │
        ├─► Create ~/.graphiti/bin/graphiti-mcp (Unix) or .bat (Windows)
        └─► Wrappers invoke ~/.graphiti/.venv/bin/python directly

Step 4: Platform Service Installation
        │
        ├─► Windows: Install NSSM service (GraphitiBootstrap)
        ├─► macOS: Install launchd plist (~~/Library/LaunchAgents/)
        └─► Linux: Install systemd unit (~/.config/systemd/user/)

Step 5: Start Bootstrap Service
        │
        └─► Service starts watching config, ready to manage MCP server
```

### Post-Installation State

After successful installation:

- `~/.graphiti/.venv/` exists with mcp_server installed
- `~/.graphiti/bin/graphiti-mcp` wrapper works without venv activation
- Bootstrap service runs at boot and watches configuration
- `graphiti-mcp daemon status` shows service state

---

## Multi-Session Support

### Architecture

```
                    ┌─────────────────────────┐
                    │   Bootstrap Service     │
                    │   (System service)      │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │      MCP Server         │
                    │  http://127.0.0.1:8321  │
                    │   (Single instance)     │
                    └───────────┬─────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
│  Claude Code    │   │  Claude Code    │   │  Claude Code    │
│  Session 1      │   │  Session 2      │   │  Session 3      │
│  (Window 1)     │   │  (Window 2)     │   │  (Window 3)     │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### Benefits

1. **Shared State**: All sessions see the same knowledge graph
2. **Resource Efficiency**: One Neo4j connection pool, one LLM client
3. **Consistent Behavior**: Configuration changes affect all sessions
4. **No Conflicts**: Single MCP server prevents race conditions

### How Clients Connect

Each Claude Code session configures HTTP transport in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "graphiti": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-proxy", "http://127.0.0.1:8321/sse"],
      "transport": "sse"
    }
  }
}
```

All sessions connect to the same `http://127.0.0.1:8321` endpoint.

---

## Platform-Specific Details

### Windows

**Service Manager**: NSSM (Non-Sucking Service Manager)
**Service Name**: `GraphitiBootstrap`
**venv Python**: `~/.graphiti/.venv/Scripts/python.exe`

```powershell
# Check service status
sc query GraphitiBootstrap

# View service configuration
nssm dump GraphitiBootstrap

# Restart service
sc stop GraphitiBootstrap
sc start GraphitiBootstrap
```

### macOS

**Service Manager**: launchd
**Plist Location**: `~/Library/LaunchAgents/com.graphiti.bootstrap.plist`
**venv Python**: `~/.graphiti/.venv/bin/python`

```bash
# Check service status
launchctl list | grep graphiti

# View plist
cat ~/Library/LaunchAgents/com.graphiti.bootstrap.plist

# Restart service
launchctl stop com.graphiti.bootstrap
launchctl start com.graphiti.bootstrap
```

### Linux

**Service Manager**: systemd (user service)
**Unit Location**: `~/.config/systemd/user/graphiti-bootstrap.service`
**venv Python**: `~/.graphiti/.venv/bin/python`

```bash
# Check service status
systemctl --user status graphiti-bootstrap

# View unit file
cat ~/.config/systemd/user/graphiti-bootstrap.service

# Restart service
systemctl --user restart graphiti-bootstrap
```

---

## Comparison: With vs Without Daemon

| Aspect | Stdio Transport (No Daemon) | HTTP Transport (With Daemon) |
|--------|----------------------------|------------------------------|
| **Startup** | MCP server starts per-session | Bootstrap starts at boot |
| **Sessions** | One server per Claude window | One server for all windows |
| **Memory** | ~100MB per window | ~105MB total |
| **State** | Isolated per session | Shared across sessions |
| **Config Changes** | Requires restart | Auto-detected (5s) |
| **venv Required** | System Python or project venv | Daemon venv at ~/.graphiti/ |

---

## FAQ

### Q: Why not put the daemon venv in the cloned repo?

The daemon needs to run independently of any specific clone. If you:
- Delete the repo: Daemon keeps working
- Clone to different location: Daemon keeps working
- Have multiple clones: One daemon serves all

### Q: Can I use the project venv for the daemon?

Not recommended. The daemon venv at `~/.graphiti/.venv/` is:
- Managed by `daemon install` command
- Has specific dependencies for background operation
- Isolated from your development environment

### Q: What if I upgrade Python in my project?

The daemon uses its own Python in `~/.graphiti/.venv/`. Project Python upgrades don't affect it.

### Q: How do I completely uninstall the daemon?

```bash
# Uninstall service
graphiti-mcp daemon uninstall

# Remove daemon directory (optional)
rm -rf ~/.graphiti/
```

---

## Related Documentation

- [TROUBLESHOOTING_DAEMON.md](TROUBLESHOOTING_DAEMON.md) - Common issues and solutions
- [CONFIGURATION.md](../CONFIGURATION.md) - Configuration reference
- [MCP_TOOLS.md](MCP_TOOLS.md) - MCP tools reference
- [claude-mcp-installer/instance/CLAUDE_INSTALL.md](../claude-mcp-installer/instance/CLAUDE_INSTALL.md) - Installation guide
