# Unified Installer Specification v1.0

**Status**: DRAFT
**Created**: 2025-12-23
**Author**: Claude Code (from user requirements)

---

## Executive Summary

Create a single, platform-agnostic Python installer script that serves as the primary entry point for Graphiti MCP server deployment. The installer dynamically detects the platform and deploys to `~/.graphiti/`, supporting multiple transport configurations (SSE, HTTP, stdio, Docker).

---

## Problem Statement

### Current Issues Identified (Session s027/s028)

1. **Stale Global Installs**: `pip install --user` creates global entry points that conflict with deployed venv
2. **Windows Service User Context**: Service runs as SYSTEM, `Path.home()` resolves to wrong directory
3. **Multiple Entry Points**: No single installer script; requires navigating repo and running Python modules
4. **No Transport Selection**: User must manually configure transport type
5. **Platform Detection Gaps**: Code uses `Path.home()` without `GRAPHITI_HOME` environment override

### Root Causes

- `Path.home()` used in 17 places without environment variable override
- Windows services run as SYSTEM user by default
- No unified installer entry point
- Transport configuration spread across multiple files

---

## Proposed Architecture

### 1. Single Entry Point: `install.py`

```
graphiti/
├── install.py              # <-- PRIMARY ENTRY POINT (platform-agnostic)
├── mcp_server/
│   ├── daemon/
│   │   ├── installer.py    # Core installer logic (called by install.py)
│   │   └── ...
│   └── ...
└── ...
```

### 2. Usage Examples

```bash
# Default installation (SSE transport, recommended)
python install.py

# Specific transport
python install.py --transport sse      # SSE (default, recommended)
python install.py --transport http     # HTTP/REST
python install.py --transport stdio    # stdio for Claude Desktop
python install.py --transport docker   # Docker Compose setup

# With options
python install.py --transport sse --port 8321
python install.py --transport http --port 8000
python install.py --uninstall
python install.py --status
```

### 3. Transport Comparison

| Transport | Client Relationship | Use Case | Complexity |
|-----------|---------------------|----------|------------|
| **SSE** (default) | Many-to-one | Multiple Claude instances | Simple, secure |
| HTTP | Many-to-one | REST API clients | Moderate |
| stdio | One-to-one | Claude Desktop direct | Simple |
| Docker | Containerized | Production deployment | Complex |

**Recommendation**: SSE as default because:
- Supports multiple Claude Code instances connecting to one server
- Simple and secure (no authentication complexity)
- Works across platforms
- Better resource utilization (single server process)

---

## Implementation Plan

### Phase 1: GRAPHITI_HOME Environment Support (Hotfix)

**Files to Modify** (add GRAPHITI_HOME support):

```python
# Pattern to apply everywhere Path.home() is used:

def get_graphiti_home() -> Path:
    """Get Graphiti home directory with environment override support."""
    if env_home := os.environ.get("GRAPHITI_HOME"):
        return Path(env_home)
    return Path.home() / ".graphiti"
```

**Files needing changes**:
1. `mcp_server/daemon/venv_manager.py` (line 54)
2. `mcp_server/daemon/bootstrap.py` (lines 103, 109, 236)
3. `mcp_server/daemon/manager.py` (lines 70, 77)
4. `mcp_server/daemon/windows_service.py` (lines 148, 153, 229)
5. `mcp_server/daemon/package_deployer.py` (line 58)
6. `mcp_server/daemon/wrapper_generator.py` (lines 53, 55)
7. `mcp_server/daemon/path_integration.py` (line 45)
8. `mcp_server/daemon/generate_requirements.py` (line 281)
9. `mcp_server/daemon/launchd_service.py` (lines 40, 41)
10. `mcp_server/daemon/systemd_service.py` (lines 45, 48)

**Windows Service Fix**:
Update `windows_service.py` install() to set GRAPHITI_HOME:

```python
# After installing service, set environment
self._run_nssm("set", self.service_name, "AppEnvironmentExtra",
               f"GRAPHITI_HOME={Path.home() / '.graphiti'}")
```

### Phase 2: Unified Installer Script

**Location**: `graphiti/install.py`

**Features**:
1. Platform detection (Windows/macOS/Linux)
2. Python version validation (>=3.10)
3. Transport selection with sensible defaults
4. Venv creation in `~/.graphiti/.venv/`
5. Package deployment to `~/.graphiti/mcp_server/`
6. Service installation (daemon mode)
7. Claude Desktop/Cursor configuration generation
8. Health check verification

**Implementation Outline**:

```python
#!/usr/bin/env python3
"""
Graphiti MCP Server Installer

Usage:
    python install.py [OPTIONS]

Options:
    --transport {sse,http,stdio,docker}  Transport type (default: sse)
    --port PORT                          Server port (default: 8321)
    --uninstall                          Remove installation
    --status                             Show installation status
    --configure-claude                   Generate Claude Desktop config
    --configure-cursor                   Generate Cursor config
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    args = parse_args()

    # Validate environment
    validate_python_version()

    if args.uninstall:
        return uninstall()

    if args.status:
        return show_status()

    # Install
    return install(
        transport=args.transport,
        port=args.port,
        configure_claude=args.configure_claude,
        configure_cursor=args.configure_cursor,
    )


def install(transport: str, port: int, **kwargs) -> int:
    """Main installation flow."""
    print(f"Installing Graphiti MCP Server ({transport} transport)")

    # 1. Detect platform
    plat = detect_platform()
    print(f"Platform: {plat}")

    # 2. Set GRAPHITI_HOME
    graphiti_home = get_graphiti_home()
    print(f"Installation directory: {graphiti_home}")

    # 3. Create venv
    create_venv(graphiti_home / ".venv")

    # 4. Install dependencies
    install_dependencies(graphiti_home / ".venv")

    # 5. Deploy package
    deploy_package(graphiti_home / "mcp_server")

    # 6. Create config
    create_config(graphiti_home / "graphiti.config.json", transport, port)

    # 7. Install service (if not stdio)
    if transport != "stdio":
        install_service(plat, graphiti_home)

    # 8. Generate client config
    if kwargs.get("configure_claude"):
        generate_claude_config(transport, port)

    if kwargs.get("configure_cursor"):
        generate_cursor_config(transport, port)

    # 9. Verify
    verify_installation(transport, port)

    print("\n✓ Installation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Phase 3: Entry Point Cleanup

1. **Remove stale global installs**:
   - Add cleanup step to installer
   - Check for and remove `~/.local/bin/graphiti-*` (Unix)
   - Check for and remove `%APPDATA%/Python/*/Scripts/graphiti-*` (Windows)

2. **Create proper entry points in deployed venv**:
   - Install package in editable mode with entry points
   - Or create wrapper scripts in `~/.graphiti/bin/`

3. **PATH integration** (optional):
   - Prompt user to add `~/.graphiti/bin` to PATH
   - Or provide activation script

---

## Configuration Schema Updates

### Transport-Specific Defaults

```json
{
  "server": {
    "transport": "sse",  // NEW: Transport type selection
    "host": "127.0.0.1",
    "port": 8321
  },
  "daemon": {
    "enabled": true,
    "auto_start": true
  }
}
```

### Transport Port Defaults

| Transport | Default Port | Rationale |
|-----------|-------------|-----------|
| SSE | 8321 | Daemon default (non-conflicting) |
| HTTP | 8321 | Same as SSE (same server, different endpoint) |
| stdio | N/A | No port (direct process communication) |
| Docker | 8000 (internal) | Container port mapping |

---

## Migration Path

### For Existing Users

1. Run `python install.py --uninstall` to clean up old installation
2. Run `python install.py --transport sse` to reinstall with new architecture
3. Update Claude Desktop config if needed

### For New Users

1. Clone repo
2. Run `python install.py`
3. Follow prompts

---

## Testing Requirements

1. **Platform Matrix**:
   - Windows 10/11
   - macOS (Intel and Apple Silicon)
   - Linux (Ubuntu, Fedora)

2. **Transport Matrix**:
   - SSE: Health check, multi-client connection
   - HTTP: REST API endpoints
   - stdio: Claude Desktop integration
   - Docker: Container lifecycle

3. **Edge Cases**:
   - Stale installation cleanup
   - Permission errors
   - Port conflicts
   - Network isolation

---

## Success Criteria

1. Single command installation: `python install.py`
2. Works on Windows, macOS, Linux without modification
3. SSE transport as secure, simple default
4. Clean uninstall with no residual files
5. Claude Desktop/Cursor config generation
6. Health check passes post-installation

---

## Appendix: Current vs Proposed Flow

### Current (Complex)
```
1. Clone repo
2. cd mcp_server
3. Find correct Python
4. Create venv manually (maybe)
5. pip install dependencies
6. Run daemon manager
7. Debug SYSTEM user issues
8. Manually configure Claude Desktop
```

### Proposed (Simple)
```
1. Clone repo (or download install.py)
2. python install.py
3. Done (config generated, service running)
```

---

## References

- Session s027: MCP connection debugging
- Session s028: Architecture gap analysis
- DAEMON_ARCHITECTURE_SPEC_v1.0.md
- CONFIGURATION.md
