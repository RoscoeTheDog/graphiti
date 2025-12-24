# Session 027: Fix graphiti-memory MCP Connection After Daemon Deployment

**Status**: ACTIVE
**Created**: 2025-12-23 22:57
**Objective**: Fix graphiti-memory MCP server connection failure after daemon deployment sprint

---

## Completed

- Diagnosed MCP connection failure: port mismatch (8000 vs 8321) + Windows service in PAUSED state
- Fixed `~/.claude.json` graphiti-memory URL from port 8000 to 8321
- Fixed `mcp_server/src/config/schema.py` default port from 8000 to 8321
- Created missing `_mcp_server.pth` file in `~/.graphiti/.venv/Lib/site-packages/`
- Verified `mcp_server.daemon.manager` imports correctly after .pth fix
- Confirmed `graphiti-mcp daemon status` command works

---

## Blocked

- Windows service reinstall requires Administrator privileges (user action pending)

---

## Next Steps

- User runs as Administrator: `C:\Users\Admin\.graphiti\.venv\Scripts\python.exe -m mcp_server.daemon.manager install`
- Verify daemon running: `curl http://localhost:8321/health`
- Create remediation story for sprint deployment to auto-create `_mcp_server.pth` file
- Update mcp_server/README.md documentation (still references old port 8000)

---

## Decisions Made

- Port 8321 is the correct daemon default (consistent with DAEMON_ARCHITECTURE_SPEC)
- Port 8000 was a legacy default from old schema.py that was not updated during daemon sprint
- Created `.pth` file pointing to `~/.graphiti/` directory to make `mcp_server` package importable from venv

---

## Errors Resolved

- **"Authenticate" button in Claude Code /mcp menu**: Caused by SSE endpoint unreachable (daemon not running + wrong port)
- **"ModuleNotFoundError: No module named 'mcp_server.daemon'"**: Fixed by creating `_mcp_server.pth` file in venv site-packages
- **Service disappeared from services.msc**: Windows service was corrupted when stopping from PAUSED state; requires reinstall
- **Port mismatch 8000 vs 8321**: Fixed in both `~/.claude.json` and source code `schema.py`

---

## Context

**Files Modified/Created**:
- `C:\Users\Admin\.claude.json` - Updated graphiti-memory URL to port 8321
- `mcp_server/src/config/schema.py` - Changed default port from 8000 to 8321
- `C:\Users\Admin\.graphiti\.venv\Lib\site-packages\_mcp_server.pth` - Created (contains path to ~/.graphiti/)

**Documentation Referenced**:
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md`
- `graphiti.config.json` (daemon.port = 8321)
- `CONFIGURATION.md` (confirms 8321 as documented default)

---

**Session Duration**: ~30 minutes
**Token Usage**: ~40k estimated
