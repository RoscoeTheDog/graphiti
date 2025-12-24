# Session 028: Unified Installer Spec and Deployment Architecture Gap Analysis

**Status**: ACTIVE
**Created**: 2025-12-23 23:36
**Objective**: Unified installer spec and deployment architecture gap analysis

---

## Summary

Continued from s027. Fixed remaining MCP import issues, analyzed deployment architecture gaps, and created specification for unified platform-agnostic installer. Windows daemon not yet functional due to SYSTEM user context issue.

---

## Completed

- Diagnosed and fixed MCP module import error (stale `mcp_server` package in site-packages conflicting with .pth paths)
- Removed stale global `graphiti-mcp.exe` from `%APPDATA%/Python/Python313/Scripts/`
- Updated session s027 handoff with complete root cause analysis (marked RESOLVED)
- Identified Windows service user context issue: service runs as SYSTEM, so `Path.home()` returns wrong directory
- Created `UNIFIED_INSTALLER_SPEC_v1.0.md` documenting vision for single-command installer
- Committed schema.py port fix (8000→8321) and handoff updates
- Committed unified installer specification

---

## Blocked

- Windows service not running: Needs `GRAPHITI_HOME` environment variable support in code
- Service configuration requires Administrator privileges to modify

---

## Next Steps

1. **Immediate workaround**: Run MCP server directly (not as service):
   ```powershell
   C:\Users\Admin\.graphiti\.venv\Scripts\python.exe -m mcp_server.graphiti_mcp_server
   ```

2. **Phase 1 (Hotfix)**: Implement `GRAPHITI_HOME` env var support:
   - Add `get_graphiti_home()` helper function
   - Update 17 files using `Path.home()`
   - Update `windows_service.py` to set env var when installing

3. **Phase 2**: Create `install.py` unified installer:
   - Single entry point: `python install.py`
   - Transport selection: `--transport {sse,http,stdio,docker}`
   - Platform detection and config generation

4. **Phase 3**: Entry point cleanup:
   - Remove stale global installs during installation
   - Proper entry points in deployed venv

---

## Decisions Made

- **SSE as default transport**: Simple, secure, supports many-to-one client relationships
- **Port clarification**: 8000 for Docker mode, 8321 for daemon mode (both correct in their context)
- **GRAPHITI_HOME approach**: Environment variable override preferred over running service as user
- **Direct debugging over remediation stories**: Fixed issues directly rather than creating sprint stories

---

## Errors Resolved

- **ModuleNotFoundError for mcp_server.daemon**: Root cause was stale `mcp_server` package in `~/.graphiti/.venv/Lib/site-packages/` taking precedence over .pth file paths. Fix: `rm -rf` the stale package.
- **Stale graphiti-mcp.exe**: Leftover from `pip install --user` causing wrong Python path. Fix: Removed from Python313 user scripts.
- **Windows service wrong directory**: Service runs as SYSTEM, `Path.home()` returns `C:\WINDOWS\system32\config\systemprofile\` instead of user directory. Fix pending: GRAPHITI_HOME env var support.

---

## Context

**Files Modified/Created**:
- `mcp_server/src/config/schema.py` - Changed default port 8000→8321
- `.claude/handoff/s027-fix-graphiti-memory-mcp-connection.md` - Updated to RESOLVED status
- `.claude/handoff/INDEX.md` - Updated s027 status
- `.claude/implementation/UNIFIED_INSTALLER_SPEC_v1.0.md` - NEW: Unified installer specification

**Files Removed**:
- `C:\Users\Admin\.graphiti\.venv\Lib\site-packages\mcp_server\` - Stale package
- `C:\Users\Admin\AppData\Roaming\Python\Python313\Scripts\graphiti-mcp.exe` - Stale global

**Documentation Referenced**:
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md`
- `mcp_server/daemon/bootstrap.py` - Config path logic
- `mcp_server/daemon/windows_service.py` - NSSM service installation
- `mcp_server/daemon/venv_manager.py` - Path.home() usage

---

## Architecture Issues Identified

1. **17 files use `Path.home()` without env override** - Breaks Windows services
2. **No unified installer entry point** - Users must navigate repo structure
3. **Stale global installs** - `pip install --user` creates conflicting entry points
4. **Transport selection manual** - No CLI option for transport type

---

**Session Duration**: ~60 minutes
**Token Usage**: ~70k estimated
