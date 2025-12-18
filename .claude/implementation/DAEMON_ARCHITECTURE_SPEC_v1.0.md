# Graphiti MCP Server: Platform-Agnostic Daemon Architecture

> **Version**: 1.0.0
> **Status**: DESIGN COMPLETE - Ready for Sprint Creation
> **Created**: 2024-12-13
> **Updated**: 2024-12-13
> **Author**: Claude + Human collaboration
> **Next Step**: Create implementation sprint (6 phases)

---

## Executive Summary

This document specifies a platform-agnostic daemon architecture for the Graphiti MCP server that:
1. Runs as a **persistent background service** on Windows, macOS, and Linux
2. Provides a **unified HTTP API** for all clients (Claude Code, CLI, other tools)
3. Supports **many-to-one** client relationships (multiple sessions, one server)
4. Uses a **single communication protocol** across all platforms
5. Is **config-primary** with `daemon.enabled` as the ONLY runtime control
6. **Auto-monitors** config changes via file polling (changes take effect in ~5s)

### UX Design Principle

**Config-primary control**: Users edit the config file to enable/disable the daemon. CLI commands are for installation lifecycle only (install/uninstall), not runtime control (no start/stop).

```
# One-time setup
graphiti-mcp daemon install

# Runtime control (config only)
Edit ~/.graphiti/graphiti.config.json → "daemon": { "enabled": true }
# Changes take effect automatically within 5 seconds
```

---

## Problem Statement

### Current Architecture (Per-Session)

```
┌─────────────────┐     stdio      ┌──────────────────────┐
│ Claude Code #1  │ ──────────────►│ graphiti_mcp (pid 1) │
└─────────────────┘                └──────────────────────┘

┌─────────────────┐     stdio      ┌──────────────────────┐
│ Claude Code #2  │ ──────────────►│ graphiti_mcp (pid 2) │
└─────────────────┘                └──────────────────────┘

┌─────────────────┐                ┌──────────────────────┐
│ CLI command     │ ──── X ────────│ (no connection)      │
└─────────────────┘                └──────────────────────┘
```

**Problems:**
1. Each Claude Code session spawns its own MCP server process
2. No shared state between sessions
3. CLI cannot connect to any running server (imports module globals)
4. Resource waste (multiple Neo4j connections, multiple Python processes)
5. Session tracking cannot aggregate across sessions in real-time

### Desired Architecture (Daemon)

```
┌─────────────────┐
│ Claude Code #1  │─────┐
└─────────────────┘     │
                        │  HTTP/JSON
┌─────────────────┐     │  :8321
│ Claude Code #2  │─────┼─────────►┌──────────────────────┐
└─────────────────┘     │          │                      │
                        │          │  Graphiti MCP Server │
┌─────────────────┐     │          │  (Daemon Service)    │
│ CLI commands    │─────┤          │                      │
└─────────────────┘     │          │  - Single Neo4j conn │
                        │          │  - Shared state      │
┌─────────────────┐     │          │  - Session tracking  │
│ Other tools     │─────┘          │                      │
└─────────────────┘                └──────────────────────┘
```

---

## Design Goals

| Goal | Priority | Rationale |
|------|----------|-----------|
| Platform-agnostic | P0 | Must work on Windows, macOS, Linux |
| Single protocol | P0 | HTTP/JSON - universally supported |
| Config-driven state | P0 | `daemon.enabled` is THE runtime control |
| Many-to-one only | P0 | NO fallback to per-process spawning |
| One daemon per machine | P0 | Avoid duplication, state conflicts |
| Simple setup | P1 | One command to install (`daemon install`) |
| Auto-start on boot | P1 | Bootstrap service survives reboots |
| Zero-config clients | P1 | Clients auto-discover running server |
| Config file watching | P1 | Changes take effect within 5 seconds |

### Non-Goals (Explicitly Out of Scope)

- **NO stdio fallback**: Clients do NOT spawn their own MCP server processes
- **NO multiple daemons**: Only one daemon instance per machine
- **NO lazy initialization**: HTTP requests do NOT start the server
- **NO start/stop CLI commands**: Runtime control is config-only (`daemon.enabled`)

---

## Architecture Decision: HTTP over Alternatives

### Options Considered

| Protocol | Pros | Cons |
|----------|------|------|
| **HTTP/JSON** | Universal, debuggable, firewall-friendly, existing FastMCP support | Slightly more overhead than sockets |
| Unix sockets | Fast, secure | Windows uses named pipes (different API) |
| Named pipes | Windows-native | Unix uses sockets (different API) |
| gRPC | Fast, typed | Complex setup, not MCP-native |
| stdio | Simple | Can't share across processes |

### Decision: HTTP/JSON on localhost

**Rationale:**
1. **Already implemented**: `src/graphiti_mcp_server.py` supports `--transport http`
2. **Universal**: Same API on all platforms
3. **Debuggable**: Can test with curl, browser, Postman
4. **MCP-compatible**: FastMCP supports HTTP streaming natively
5. **Firewall-safe**: localhost-only by default (127.0.0.1)

---

## Two-Layer Architecture: Bootstrap Service + MCP Server

The daemon architecture consists of two layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    OS Service Layer                              │
│  (systemd / launchd / Windows Service)                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            Bootstrap Service (always running)            │    │
│  │                                                          │    │
│  │  - Watches ~/.graphiti/graphiti.config.json              │    │
│  │  - Reads daemon.enabled flag                             │    │
│  │  - Starts/stops MCP server based on config               │    │
│  │  - Lightweight (~5MB RAM)                                │    │
│  │                                                          │    │
│  │         ┌──────────────────────────────────┐             │    │
│  │         │  MCP Server (conditional)        │             │    │
│  │         │                                  │             │    │
│  │         │  - Only runs if enabled=true     │             │    │
│  │         │  - HTTP API on :8321             │             │    │
│  │         │  - Neo4j connection              │             │    │
│  │         │  - Session tracking              │             │    │
│  │         │  - ~100MB RAM when active        │             │    │
│  │         └──────────────────────────────────┘             │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Why Two Layers?

1. **Bootstrap always runs** - Installed as OS service, survives reboots
2. **MCP server is conditional** - Only runs when `daemon.enabled: true`
3. **Config changes take effect immediately** - No manual restart needed
4. **Minimal overhead when disabled** - Bootstrap uses ~5MB, watches one file

### State Transitions

```
                    ┌─────────────────┐
                    │  Config File    │
                    │  daemon.enabled │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Bootstrap reads │
                    │ config (poll)   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       enabled: false                enabled: true
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │ MCP Server OFF  │           │ MCP Server ON   │
    │                 │           │                 │
    │ Clients get:    │           │ Clients get:    │
    │ "Connection     │           │ Normal API      │
    │  refused"       │           │ responses       │
    └─────────────────┘           └─────────────────┘
```

---

## Server Specification

### Default Configuration

```json
{
  "daemon": {
    "_comment": "Daemon service configuration",
    "enabled": true,
    "_enabled_help": "Auto-enabled after install. Set to false to stop MCP server.",
    "host": "127.0.0.1",
    "port": 8321,
    "config_poll_seconds": 5,
    "_config_poll_help": "How often bootstrap checks config for changes (seconds)",
    "pid_file": null,
    "_pid_file_help": "null = ~/.graphiti/graphiti-mcp.pid",
    "log_file": null,
    "_log_file_help": "null = ~/.graphiti/logs/graphiti-mcp.log"
  }
}
```

**Key Points:**
- `enabled: true` by default **after install** (auto-enable UX improvement - Story 1)
- **Breaking Change**: Previous behavior required manual `enabled: true` edit
- Bootstrap service always runs (watches config)
- MCP server starts automatically within 5 seconds of install

### Port Selection: 8321

- Mnemonic: "8" (graphi**ti**) + "321" (countdown/launch)
- Not in common use (checked against IANA registry)
- Configurable via `GRAPHITI_PORT` env var or config

### Endpoints

The server exposes two endpoint categories:

#### 1. MCP Protocol Endpoints (existing)

```
POST /mcp/              # MCP JSON-RPC endpoint (tools, resources)
GET  /mcp/sse           # Server-Sent Events for notifications
GET  /health            # Health check
```

#### 2. Management API (new)

```
GET  /api/v1/status              # Server status + session tracking status
POST /api/v1/session/sync        # Trigger manual session sync
GET  /api/v1/session/history     # Get session tracking history
GET  /api/v1/config              # Get current config (non-sensitive)
POST /api/v1/config/reload       # Hot-reload configuration
GET  /api/v1/metrics             # Prometheus-format metrics (optional)
```

---

## Client Specification

### Claude Code Configuration

Update `claude_desktop_config.json` to use HTTP transport:

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "url": "http://127.0.0.1:8321/mcp/",
      "transport": "http"
    }
  }
}
```

**Note**: The MCP SDK supports HTTP transport natively. No custom client code needed.

### CLI Client Refactoring

Current (broken):
```python
# Imports module globals (only works in-process)
from mcp_server.graphiti_mcp_server import session_manager
```

Refactored:
```python
import httpx

class GraphitiClient:
    """HTTP client for Graphiti MCP daemon."""

    def __init__(self, base_url: str = "http://127.0.0.1:8321"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def sync_sessions(self, days: int = 7, dry_run: bool = True) -> dict:
        """Trigger session sync via HTTP API."""
        response = self.client.post(
            f"{self.base_url}/api/v1/session/sync",
            json={"days": days, "dry_run": dry_run}
        )
        return response.json()

    def get_status(self) -> dict:
        """Get server and session tracking status."""
        response = self.client.get(f"{self.base_url}/api/v1/status")
        return response.json()

    def health_check(self) -> bool:
        """Check if daemon is running."""
        try:
            response = self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except httpx.ConnectError:
            return False
```

### Auto-Discovery

Clients should auto-discover the daemon:

```python
def get_graphiti_url() -> str:
    """Get Graphiti daemon URL with fallback chain."""
    # 1. Environment variable
    if url := os.environ.get("GRAPHITI_URL"):
        return url

    # 2. Config file
    config_path = Path.home() / ".graphiti" / "graphiti.config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        if url := config.get("daemon", {}).get("url"):
            return url

    # 3. Default
    return "http://127.0.0.1:8321"
```

### CLI Error Handling

When daemon is disabled or unreachable, CLI provides actionable errors:

```python
class GraphitiClient:
    """HTTP client for Graphiti MCP daemon."""

    def __init__(self, base_url: str = None):
        self.config_path = Path.home() / ".graphiti" / "graphiti.config.json"
        self.base_url = base_url or self._get_url_from_config()
        self.client = httpx.Client(timeout=30.0)

    def _get_url_from_config(self) -> str:
        """Read daemon URL from config."""
        if self.config_path.exists():
            config = json.loads(self.config_path.read_text())
            host = config.get("daemon", {}).get("host", "127.0.0.1")
            port = config.get("daemon", {}).get("port", 8321)
            return f"http://{host}:{port}"
        return "http://127.0.0.1:8321"

    def _check_daemon_enabled(self) -> bool:
        """Check if daemon is enabled in config."""
        if self.config_path.exists():
            config = json.loads(self.config_path.read_text())
            return config.get("daemon", {}).get("enabled", False)
        return False

    def _handle_connection_error(self, operation: str) -> None:
        """Provide actionable error message when daemon unreachable."""
        if not self._check_daemon_enabled():
            # Daemon is disabled in config
            print(f"❌ Error: Graphiti daemon is disabled.")
            print(f"")
            print(f"   To enable, edit: {self.config_path}")
            print(f"   Set: \"daemon\": {{ \"enabled\": true }}")
            print(f"")
            print(f"   The daemon will start automatically within 5 seconds.")
        else:
            # Daemon enabled but not responding
            print(f"❌ Error: Cannot connect to Graphiti daemon at {self.base_url}")
            print(f"")
            print(f"   Config shows daemon.enabled: true")
            print(f"   But server is not responding.")
            print(f"")
            print(f"   Check if bootstrap service is running:")
            print(f"     graphiti-mcp daemon status")
            print(f"")
            print(f"   View logs:")
            print(f"     graphiti-mcp daemon logs")
        sys.exit(1)

    def sync_sessions(self, days: int = 7, dry_run: bool = True) -> dict:
        """Trigger session sync via HTTP API."""
        try:
            response = self.client.post(
                f"{self.base_url}/api/v1/session/sync",
                json={"days": days, "dry_run": dry_run}
            )
            return response.json()
        except httpx.ConnectError:
            self._handle_connection_error("sync sessions")
```

### Example CLI Session

```bash
# Daemon disabled (default state after install)
$ graphiti-mcp-session-tracking sync --days 2
❌ Error: Graphiti daemon is disabled.

   To enable, edit: C:\Users\Admin\.graphiti\graphiti.config.json
   Set: "daemon": { "enabled": true }

   The daemon will start automatically within 5 seconds.

# User edits config, sets enabled: true
# ... waits 5 seconds for bootstrap to detect change ...

$ graphiti-mcp-session-tracking sync --days 2
📊 Session Sync Summary

  Mode:             DRY RUN (preview)
  Sessions found:   15
  Estimated cost:   $2.55
  ...
```

---

## Bootstrap Service Implementation

The bootstrap service is the core of the daemon architecture. It:
1. Runs as an OS-level service (always on)
2. Polls the config file for changes
3. Starts/stops the MCP server based on `daemon.enabled`

### Bootstrap Service Code

```python
#!/usr/bin/env python3
"""
Graphiti Bootstrap Service

Lightweight service that watches graphiti.config.json and manages
the MCP server lifecycle based on the daemon.enabled flag.

This is installed as an OS service (systemd/launchd/Windows Service)
and runs continuously, even when daemon.enabled is false.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("graphiti.bootstrap")


class BootstrapService:
    """Watches config and manages MCP server lifecycle."""

    def __init__(self):
        self.config_path = self._get_config_path()
        self.mcp_process: Optional[subprocess.Popen] = None
        self.last_config_mtime: float = 0
        self.last_enabled_state: Optional[bool] = None
        self.poll_interval: int = 5  # seconds
        self.running: bool = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _get_config_path(self) -> Path:
        """Get config path (platform-aware)."""
        # Check environment override first
        if env_path := os.environ.get("GRAPHITI_CONFIG"):
            return Path(env_path)

        # Default locations
        if sys.platform == "win32":
            return Path.home() / ".graphiti" / "graphiti.config.json"
        else:
            # Unix: ~/.graphiti/ or XDG_CONFIG_HOME
            xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
            if xdg_config:
                return Path(xdg_config) / "graphiti" / "graphiti.config.json"
            return Path.home() / ".graphiti" / "graphiti.config.json"

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self._stop_mcp_server()

    def _read_config(self) -> dict:
        """Read and parse config file."""
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text())
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {e}")
        except Exception as e:
            logger.error(f"Error reading config: {e}")
        return {}

    def _config_changed(self) -> bool:
        """Check if config file was modified."""
        try:
            if self.config_path.exists():
                mtime = self.config_path.stat().st_mtime
                if mtime != self.last_config_mtime:
                    self.last_config_mtime = mtime
                    return True
        except Exception as e:
            logger.warning(f"Error checking config mtime: {e}")
        return False

    def _start_mcp_server(self, config: dict) -> None:
        """Start the MCP server subprocess."""
        if self.mcp_process and self.mcp_process.poll() is None:
            logger.debug("MCP server already running")
            return

        daemon_config = config.get("daemon", {})
        host = daemon_config.get("host", "127.0.0.1")
        port = daemon_config.get("port", 8321)

        # Determine the MCP server script path
        mcp_server_path = self._get_mcp_server_path()

        cmd = [
            sys.executable,
            str(mcp_server_path),
            "--transport", "http",
            "--host", host,
            "--port", str(port),
        ]

        logger.info(f"Starting MCP server on {host}:{port}")
        try:
            self.mcp_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Don't create new console window on Windows
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            logger.info(f"MCP server started (PID: {self.mcp_process.pid})")
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")

    def _stop_mcp_server(self) -> None:
        """Stop the MCP server subprocess."""
        if self.mcp_process is None:
            return

        if self.mcp_process.poll() is None:
            logger.info("Stopping MCP server...")
            self.mcp_process.terminate()

            # Wait for graceful shutdown
            try:
                self.mcp_process.wait(timeout=10)
                logger.info("MCP server stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("MCP server didn't stop, killing...")
                self.mcp_process.kill()
                self.mcp_process.wait()

        self.mcp_process = None

    def _get_mcp_server_path(self) -> Path:
        """Get path to MCP server script."""
        # Check environment override
        if env_path := os.environ.get("GRAPHITI_MCP_SERVER"):
            return Path(env_path)

        # Default: relative to this script
        bootstrap_dir = Path(__file__).parent
        return bootstrap_dir / "src" / "graphiti_mcp_server.py"

    def run(self) -> None:
        """Main loop: watch config and manage MCP server."""
        logger.info(f"Bootstrap service starting, watching: {self.config_path}")
        logger.info(f"Poll interval: {self.poll_interval}s")

        while self.running:
            try:
                # Check for config changes
                if self._config_changed() or self.last_enabled_state is None:
                    config = self._read_config()
                    daemon_config = config.get("daemon", {})
                    enabled = daemon_config.get("enabled", False)

                    # Update poll interval from config
                    self.poll_interval = daemon_config.get("config_poll_seconds", 5)

                    # State change detected
                    if enabled != self.last_enabled_state:
                        if enabled:
                            logger.info("daemon.enabled changed to true, starting MCP server")
                            self._start_mcp_server(config)
                        else:
                            logger.info("daemon.enabled changed to false, stopping MCP server")
                            self._stop_mcp_server()

                        self.last_enabled_state = enabled

                # Check if MCP server crashed (restart if enabled)
                if self.last_enabled_state and self.mcp_process:
                    if self.mcp_process.poll() is not None:
                        logger.warning("MCP server crashed, restarting...")
                        config = self._read_config()
                        self._start_mcp_server(config)

                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in bootstrap loop: {e}")
                time.sleep(self.poll_interval)

        logger.info("Bootstrap service stopped")


def main():
    """Entry point for bootstrap service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    service = BootstrapService()
    service.run()


if __name__ == "__main__":
    main()
```

### File Watching: Polling vs Event-Based

| Approach | Pros | Cons |
|----------|------|------|
| **Polling (chosen)** | Simple, cross-platform, reliable | Slight delay (5s default) |
| watchdog library | Instant detection | Platform-specific quirks, extra dependency |
| inotify/FSEvents | Native, efficient | Different API per platform |

**Decision**: Use polling with configurable interval.
- Default 5 seconds is fast enough for config changes
- No platform-specific code for file watching
- No additional dependencies
- Reliable on network drives and all filesystems

---

## Daemon Management

### Platform-Specific Service Installation

#### Windows (NSSM or native service)

```powershell
# Option 1: NSSM (Non-Sucking Service Manager) - Recommended
nssm install GraphitiMCP "C:\python313\python.exe" "C:\path\to\graphiti_mcp_server.py --transport http"
nssm set GraphitiMCP AppDirectory "C:\path\to\graphiti\mcp_server"
nssm set GraphitiMCP DisplayName "Graphiti MCP Server"
nssm set GraphitiMCP Start SERVICE_AUTO_START
nssm start GraphitiMCP

# Option 2: Native Windows Service (requires pywin32)
# See implementation section
```

#### macOS (launchd)

```xml
<!-- ~/Library/LaunchAgents/com.graphiti.mcp.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.graphiti.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/graphiti_mcp_server.py</string>
        <string>--transport</string>
        <string>http</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/graphiti-mcp.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/graphiti-mcp.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.graphiti.mcp.plist
```

#### Linux (systemd)

```ini
# /etc/systemd/user/graphiti-mcp.service
[Unit]
Description=Graphiti MCP Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /path/to/graphiti_mcp_server.py --transport http
Restart=always
RestartSec=5
Environment="GRAPHITI_CONFIG=/home/user/.graphiti/graphiti.config.json"

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable graphiti-mcp
systemctl --user start graphiti-mcp
```

### Unified CLI for Daemon Management

**Design Principle**: Config-primary control. Service commands are for **installation lifecycle only**, not runtime control.

```bash
# Installation lifecycle (one-time setup)
graphiti-mcp daemon install    # Install bootstrap service (runs on boot)
graphiti-mcp daemon uninstall  # Remove bootstrap service

# Observability (read-only)
graphiti-mcp daemon status     # Show current state (installed? enabled? running?)
graphiti-mcp daemon logs       # Tail daemon logs

# NOT SUPPORTED (by design):
# graphiti-mcp daemon start    # ❌ Use config: daemon.enabled: true
# graphiti-mcp daemon stop     # ❌ Use config: daemon.enabled: false
```

**Why no start/stop commands?**
- Single source of truth: `daemon.enabled` in config
- Avoids confusion: "did I start it or enable it?"
- Config-driven: automation tools can manage state via config files
- Consistent: bootstrap watches config, user edits config

**User workflow (Auto-Enable UX - Story 1):**
```bash
# 1. One-time install (daemon auto-enabled)
graphiti-mcp daemon install
# MCP server starts automatically within 5 seconds!

# 2. Verify daemon is running (should be active immediately)
graphiti-mcp daemon status

# 3. Optional: Disable via config if needed
# Edit ~/.graphiti/graphiti.config.json:
#   "daemon": { "enabled": false }
```

**Previous workflow (manual enable required):**
```bash
# OLD (before Story 1):
# 1. graphiti-mcp daemon install
# 2. Edit config: set daemon.enabled: true ← Manual step removed!
# 3. Wait 5 seconds for server to start
```

Implementation uses platform detection:

```python
import platform

def get_service_manager():
    system = platform.system()
    if system == "Windows":
        return WindowsServiceManager()  # NSSM or pywin32
    elif system == "Darwin":
        return LaunchdServiceManager()  # launchctl
    elif system == "Linux":
        return SystemdServiceManager()  # systemctl
    else:
        raise UnsupportedPlatformError(f"Unknown platform: {system}")
```

---

## Configuration Schema Updates

### graphiti.config.json additions

```json
{
  "daemon": {
    "_comment": "Daemon service configuration (Two-Layer Architecture)",
    "_docs": "See .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md",

    "enabled": false,
    "_enabled_help": "Master switch: false (default) = MCP server stopped, true = MCP server running",

    "host": "127.0.0.1",
    "_host_help": "Bind address for HTTP API. Use 127.0.0.1 (localhost-only, secure)",

    "port": 8321,
    "_port_help": "HTTP port for MCP API. 8321 is default, change if conflict",

    "config_poll_seconds": 5,
    "_config_poll_seconds_help": "How often bootstrap checks this file for changes",

    "pid_file": null,
    "_pid_file_help": "null = ~/.graphiti/graphiti-mcp.pid",

    "log_file": null,
    "_log_file_help": "null = ~/.graphiti/logs/graphiti-mcp.log",

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
  },
  "session_tracking": {
    "enabled": true,
    "...": "existing config (unchanged)"
  }
}
```

### Key Configuration Behaviors

| Setting | Default | Behavior |
|---------|---------|----------|
| `daemon.enabled` | `false` | **Single source of truth**. Bootstrap watches this and starts/stops MCP server. |
| `daemon.config_poll_seconds` | `5` | Bootstrap polls config file every N seconds for changes. |
| `daemon.health_check_interval` | `30` | Bootstrap checks if MCP server crashed every N seconds (restarts if needed). |

### Minimal Config (Defaults)

To enable the daemon with all defaults:

```json
{
  "daemon": {
    "enabled": true
  }
}
```

This alone is sufficient - all other settings have sensible defaults.

---

## Migration Path

### Phase 1: Core Infrastructure

**Goal**: Add Management API and HTTP client foundation

- [x] `graphiti_mcp_server.py` supports `--transport http`
- [x] Health endpoint exists (`/health`)
- [ ] Add Management API endpoints (`/api/v1/*`)
- [ ] Create `GraphitiClient` HTTP client class
- [ ] Add daemon config schema to `unified_config.py`

**Deliverables**: Management API, HTTP client library

### Phase 2: Bootstrap Service

**Goal**: Create the config-watching bootstrap layer

- [ ] Implement `bootstrap.py` (config watcher + MCP lifecycle)
- [ ] Config file polling (5s default, configurable)
- [ ] MCP server start/stop based on `daemon.enabled`
- [ ] Crash detection and auto-restart
- [ ] Graceful shutdown handling

**Deliverables**: Working bootstrap service, can be run manually

### Phase 3: CLI Refactoring

**Goal**: CLI uses HTTP client instead of module imports

- [ ] Refactor `session_tracking_cli.py` to use `GraphitiClient`
- [ ] Add actionable error messages (daemon disabled/unreachable)
- [ ] Add `graphiti-mcp daemon` management commands
- [ ] Test CLI against running daemon

**Deliverables**: CLI works with daemon, clear error messages

### Phase 4: Platform Service Installation

**Goal**: Bootstrap runs as native OS service

- [ ] Create `daemon_manager.py` with platform abstraction
- [ ] Implement Windows service manager (NSSM)
- [ ] Implement macOS launchd manager
- [ ] Implement Linux systemd manager
- [ ] Create service config templates
- [ ] `graphiti-mcp daemon install/start/stop/status/logs`

**Deliverables**: One-command service installation on all platforms

### Phase 5: Claude Code Integration

**Goal**: Claude Code connects to daemon via HTTP

- [ ] Update `claude_desktop_config.json` template for HTTP transport
- [ ] Document migration from stdio to HTTP
- [ ] Test multi-session scenario (shared state verification)
- [ ] **NO stdio fallback** (by design)

**Deliverables**: Claude Code works with daemon, shared state

### Phase 6: Testing & Documentation

**Goal**: Production-ready across all platforms

- [ ] Cross-platform testing (Windows 11, macOS, Ubuntu/Debian)
- [ ] Integration tests (CLI + Claude Code + daemon)
- [ ] Update installation documentation
- [ ] Update troubleshooting guide
- [ ] Add daemon architecture to user docs

**Deliverables**: Tested, documented, release-ready

---

## Security Considerations

### Localhost-Only Binding

```python
# SECURITY: Always bind to localhost by default
host = config.daemon.host or "127.0.0.1"
if host not in ("127.0.0.1", "localhost", "::1"):
    logger.warning(
        f"SECURITY WARNING: Binding to {host} exposes the server to network. "
        "Set daemon.host to '127.0.0.1' for local-only access."
    )
```

### No Authentication (localhost)

Since the server binds to localhost only:
- No authentication required (same machine = trusted)
- No TLS required (localhost traffic is local)
- Firewall not needed (no external exposure)

### Future: Network Mode (Optional)

If users want to expose the server to the network:
- Add API key authentication
- Add TLS support
- Document security implications

---

## Implementation Files

### New Files to Create

```
mcp_server/
├── daemon/
│   ├── __init__.py
│   ├── bootstrap.py         # Bootstrap service (config watcher + MCP lifecycle)
│   ├── manager.py           # Platform-agnostic daemon manager
│   ├── windows_service.py   # Windows-specific (NSSM/pywin32)
│   ├── launchd_service.py   # macOS-specific
│   ├── systemd_service.py   # Linux-specific
│   └── templates/           # Service config templates
│       ├── graphiti-bootstrap.service    # systemd (bootstrap service)
│       ├── com.graphiti.bootstrap.plist  # launchd (bootstrap service)
│       └── nssm_bootstrap.ps1            # Windows NSSM (bootstrap service)
├── api/
│   ├── __init__.py
│   ├── management.py        # Management API endpoints
│   └── client.py            # HTTP client for CLI
└── session_tracking_cli.py  # Refactored to use HTTP client
```

### Modified Files

```
mcp_server/
├── graphiti_mcp_server.py   # Add management API routes
└── unified_config.py        # Add daemon config section
```

### Entry Points (setup.py / pyproject.toml)

```python
entry_points={
    "console_scripts": [
        "graphiti-mcp=mcp_server.graphiti_mcp_server:main",          # MCP server
        "graphiti-bootstrap=mcp_server.daemon.bootstrap:main",        # Bootstrap service
        "graphiti-mcp-daemon=mcp_server.daemon.manager:main",         # Daemon CLI
        "graphiti-mcp-session-tracking=mcp_server.session_tracking_cli:main",  # Session CLI
    ],
}
```

---

## Success Criteria

1. **Single command install**: `graphiti-mcp daemon install` works on Win/Mac/Linux
2. **Auto-start**: Daemon survives reboot
3. **CLI works**: `graphiti-mcp-session-tracking sync --days 2` connects to daemon
4. **Claude Code works**: Sessions connect to daemon via HTTP
5. **Shared state**: Session tracking aggregates across all connected clients
6. **Logs accessible**: `graphiti-mcp daemon logs` shows unified logs

---

## Resolved Design Decisions

The following questions were resolved during design review:

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Port selection** | 8321 (fixed) | Unique enough, not in common use, memorable |
| **Default state** | `daemon.enabled: false` | Opt-in model, single source of truth |
| **Fallback behavior** | **NO stdio fallback** | Always many-to-one; avoids duplication, overhead, state conflicts |
| **Daemon instances** | One per machine | Use `group_id` for project isolation, not separate processes |
| **Config watching** | Polling (5s default) | Cross-platform simplicity, reliable on all filesystems |
| **Service architecture** | Two-layer (Bootstrap + MCP) | Bootstrap always runs, MCP conditional on config |
| **Runtime control** | **Config-only** | No `start/stop` CLI commands; `daemon.enabled` is THE control |
| **CLI commands** | Install/uninstall/status/logs | Service lifecycle + observability only, no runtime control |

### Port Conflict Handling

If port 8321 is in use:
1. Bootstrap logs clear error message
2. User must either:
   - Stop conflicting service
   - Change `daemon.port` in config
3. **NO auto-increment** - explicit port configuration preferred

### Docker Deployment

Docker containers use the same architecture:
- Bootstrap service runs in container
- Exposes HTTP on configurable port
- Host binding via Docker port mapping
- Same config format, same API

---

## Appendix: Port 8321 Availability Check

```python
import socket

def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False

# Check common ports to avoid
AVOID_PORTS = {
    3000,  # React dev server
    5000,  # Flask default
    8000,  # Django/uvicorn default
    8080,  # Common HTTP alt
    8888,  # Jupyter
}

# 8321 is uncommon and memorable
assert 8321 not in AVOID_PORTS
```

---

## Next Steps

### For Human Review

1. ✅ **Review this spec** - Confirm design decisions align with requirements
2. **Approve for sprint creation** - Confirm ready to proceed

### For Sprint Creation Agent

When creating the implementation sprint, use these 6 phases as sprint stories:

| Phase | Story Title | Est. Complexity |
|-------|-------------|-----------------|
| 1 | Core Infrastructure (Management API + HTTP Client) | Medium |
| 2 | Bootstrap Service (Config Watcher + MCP Lifecycle) | Medium |
| 3 | CLI Refactoring (HTTP Client + Error Messages) | Medium |
| 4 | Platform Service Installation (Win/Mac/Linux) | High |
| 5 | Claude Code Integration (HTTP Transport) | Low |
| 6 | Testing & Documentation | Medium |

### Sprint Naming Suggestion

`daemon-architecture-v1.0` or `mcp-http-daemon`

---

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [NSSM - Non-Sucking Service Manager](https://nssm.cc/)
- [systemd User Services](https://wiki.archlinux.org/title/Systemd/User)
- [launchd Documentation](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
