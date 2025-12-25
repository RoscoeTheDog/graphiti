# Session 031: MCP Daemon v2.1 Professional Installation Architecture

**Status**: ACTIVE
**Created**: 2025-12-25 01:17
**Objective**: Design professional-grade MCP daemon installation architecture following industry conventions

---

## Summary

Investigated Graphiti MCP server connection failure. Discovered multiple root causes: missing PyYAML dependency causing server crashes, Task Scheduler running with wrong user context (Path.home() resolving to SYSTEM profile), and bootstrap import issues. User requested moving from `~/.graphiti/` to a professional installation pattern. Researched industry conventions (Ollama, VS Code, PostgreSQL, Docker) and designed v2.1 architecture using `%LOCALAPPDATA%\Programs\` pattern (no admin required, per-user, frozen packages).

---

## Completed

- Investigated MCP server connection failure - identified 3 root causes
- Analyzed logs showing `Path.home()` resolving to `C:\WINDOWS\system32\config\systemprofile\`
- Discovered missing PyYAML dependency causing MCP server crashes every 30 seconds
- Identified bootstrap.py relative import issue when run directly vs as module
- Researched professional software installation patterns (Ollama, VS Code, Docker, PostgreSQL, Neo4j)
- Identified Ollama pattern as best fit: `%LOCALAPPDATA%\Programs\` (per-user, no admin)
- Created `MCP_DAEMON_DESIGN_PATTERN.md` - reusable template for any MCP daemon server
- Created `DAEMON_ARCHITECTURE_SPEC_v2.1.md` - Graphiti-specific implementation
- Marked `DAEMON_ARCHITECTURE_SPEC_v2.0.md` as SUPERSEDED

---

## Blocked

None - specs complete, ready for implementation

---

## Next Steps

1. Implement `mcp_server/daemon/paths.py` with platform-aware path resolution
2. Update all daemon modules to use new path functions (VenvManager, DaemonManager, PackageDeployer, etc.)
3. Create `GraphitiInstaller` class for frozen package deployment
4. Update service managers (Windows Task Scheduler, launchd, systemd) to use new paths
5. Implement v2.0 to v2.1 migration logic
6. Fix immediate issues: install PyYAML, fix bootstrap import method
7. Test complete install/uninstall cycle with new architecture

---

## Decisions Made

- **Ollama pattern over Program Files pattern**: `%LOCALAPPDATA%\Programs\` requires no admin privileges, ideal for developer tools. Program Files requires UAC/admin and is for IT-deployed system software.

- **Frozen packages over editable installs**: Copying packages to install location (not symlinks/editable) ensures repo independence. User can delete/move repo without breaking daemon.

- **Separation of concerns**: Three distinct directories with different lifecycles:
  - Programs (executables, frozen) - replaced on upgrade
  - Config (user settings) - preserved across upgrades
  - State (logs, data) - machine-generated, purgeable

- **VERSION file for upgrade detection**: Enables programmatic upgrade detection and rollback capability.

- **Created reusable design pattern**: `MCP_DAEMON_DESIGN_PATTERN.md` as template for other MCP servers requiring persistent daemons.

---

## Errors Resolved

- **Root cause of connection failure identified**:
  1. PyYAML not installed in `~/.graphiti/.venv/` despite being in requirements.txt
  2. Bootstrap script uses relative imports but Task Scheduler runs it directly (should use `-m mcp_server.daemon.bootstrap`)
  3. Historical runs with SYSTEM context caused Path.home() to resolve incorrectly

- **Why v2.0 architecture had issues**:
  - Editable install of mcp_server linked to repo
  - graphiti_core imported from repo (not deployed)
  - Mixed sys.path caused dependency confusion
  - No version tracking for upgrades

---

## Context

**Files Created**:
- `.claude/implementation/MCP_DAEMON_DESIGN_PATTERN.md` - Reusable daemon architecture template
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v2.1.md` - Graphiti v2.1 implementation spec

**Files Modified**:
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v2.0.md` - Marked as SUPERSEDED

**Files Analyzed**:
- `mcp_server/daemon/manager.py` - Current daemon manager
- `mcp_server/daemon/bootstrap.py` - Bootstrap service with Path.home() calls
- `mcp_server/daemon/windows_task_scheduler.py` - Task Scheduler implementation
- `~/.graphiti/logs/bootstrap-stderr.log` - Revealed SYSTEM path resolution
- `~/.graphiti/graphiti.config.json` - Current config structure

**Documentation Referenced**:
- Ollama installation pattern (developer tool, no admin)
- VS Code user installation pattern
- XDG Base Directory specification (Linux)
- Windows LOCALAPPDATA conventions

---

## Architecture Summary

### v2.1 Directory Structure (Windows)

```
%LOCALAPPDATA%\Programs\Graphiti\     <- Executables + frozen libs
├── bin\
├── lib\mcp_server\, lib\graphiti_core\
├── VERSION
└── INSTALL_INFO

%LOCALAPPDATA%\Graphiti\              <- Config + runtime
├── config\graphiti.config.json
├── logs\
└── data\
```

### Key Benefits
- No admin required (unlike Program Files)
- Repo-independent (frozen packages)
- Version-tracked (upgradeable)
- Clean uninstall (remove 2 directories)
- Professional UX (like Ollama, VS Code)

---

**Session Duration**: ~2 hours
**Token Usage**: ~50k estimated
