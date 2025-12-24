# Session 027: Fix graphiti-memory MCP Connection After Daemon Deployment

**Status**: RESOLVED
**Created**: 2025-12-23 22:57
**Resolved**: 2025-12-23
**Objective**: Fix graphiti-memory MCP server connection failure after daemon deployment sprint

---

## Summary

All MCP connection issues resolved through direct debugging. No remediation stories needed.

---

## Completed

- Diagnosed MCP connection failure: port mismatch (8000 vs 8321) + Windows service in PAUSED state
- Fixed `~/.claude.json` graphiti-memory URL from port 8000 to 8321
- Fixed `mcp_server/src/config/schema.py` default port from 8000 to 8321
- Created missing `_mcp_server.pth` file in `~/.graphiti/.venv/Lib/site-packages/`
- Verified `mcp_server.daemon.manager` imports correctly after .pth fix
- Confirmed `graphiti-mcp daemon status` command works
- **Removed stale `mcp_server` package from site-packages** (root cause of final import error)
- **Successfully installed and started daemon service as Administrator**

---

## Root Cause Analysis

### Issue 1: Port Mismatch (8000 vs 8321)
- `schema.py` had legacy default port 8000
- `graphiti.config.json` and spec use port 8321
- **Fix**: Updated schema.py default to 8321

### Issue 2: Module Import Failure
- Initial symptom: `ModuleNotFoundError: No module named 'mcp_server.daemon'`
- Created `_mcp_server.pth` pointing to `~/.graphiti/` - didn't fully fix
- **Root cause**: Stale `mcp_server` package in `~/.graphiti/.venv/Lib/site-packages/`
  - This old package only had `__init__.py` and `server.py` (no `daemon/` submodule)
  - Python found this stale package before the `.pth` file paths
- **Fix**: `rm -rf ~/.graphiti/.venv/Lib/site-packages/mcp_server/`

### Issue 3: Windows Service Corruption
- Service disappeared from services.msc when stopping from PAUSED state
- **Fix**: Reinstalled via `python -m mcp_server.daemon.manager install` (as Administrator)

---

## Decisions Made

- Port 8321 is the correct daemon default (consistent with DAEMON_ARCHITECTURE_SPEC)
- Port 8000 was a legacy default from old schema.py that was not updated during daemon sprint
- `.pth` file approach is valid but must ensure no conflicting packages in site-packages
- Direct debugging preferred over remediation stories for deployment issues

---

## Errors Resolved

- **"Authenticate" button in Claude Code /mcp menu**: Caused by SSE endpoint unreachable (daemon not running + wrong port)
- **"ModuleNotFoundError: No module named 'mcp_server.daemon'"**: Fixed by removing stale mcp_server from site-packages
- **Service disappeared from services.msc**: Reinstalled via daemon manager
- **Port mismatch 8000 vs 8321**: Fixed in both `~/.claude.json` and source code `schema.py`

---

## Context

**Files Modified/Created**:
- `C:\Users\Admin\.claude.json` - Updated graphiti-memory URL to port 8321
- `mcp_server/src/config/schema.py` - Changed default port from 8000 to 8321
- `C:\Users\Admin\.graphiti\.venv\Lib\site-packages\_mcp_server.pth` - Created (contains path to ~/.graphiti/)

**Files Removed**:
- `C:\Users\Admin\.graphiti\.venv\Lib\site-packages\mcp_server\` - Stale package conflicting with .pth paths

**Documentation Referenced**:
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md`
- `graphiti.config.json` (daemon.port = 8321)
- `CONFIGURATION.md` (confirms 8321 as documented default)

---

## Documentation Notes

- **mcp_server/README.md uses port 8000**: This is correct for Docker/direct mode
- **Daemon mode uses port 8321**: Documented in DAEMON_ARCHITECTURE_SPEC, graphiti.config.json
- These are different deployment modes with different default ports (no doc update needed)

---

**Session Duration**: ~45 minutes
**Token Usage**: ~50k estimated
