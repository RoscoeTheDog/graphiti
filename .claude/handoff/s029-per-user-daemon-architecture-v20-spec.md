# Session 029: Per-User Daemon Architecture v2.0 Spec

**Status**: ACTIVE
**Created**: 2025-12-24 00:06
**Objective**: Create v2.0 daemon architecture spec replacing system services with per-user services

---

## Summary

Analyzed why GRAPHITI_HOME environment variable was being proposed (Windows service running as SYSTEM user causes `Path.home()` to resolve to wrong directory). Challenged whether env var was the right solution. Researched conventional patterns for multi-platform services. Discovered that per-user service instances (not system services) are the correct architecture for MCP servers since they're inherently user-scoped. Created comprehensive v2.0 specification.

---

## Completed

- Reviewed session s028 handoff (unified installer spec, Windows service Path.home() issue)
- Analyzed `windows_service.py` and `bootstrap.py` to understand the SYSTEM user path issue
- Identified 3 runtime `Path.home()` calls that break when running as SYSTEM user
- Researched conventional patterns for multi-platform system services (PostgreSQL, Redis, Docker, etc.)
- Discussed multi-user isolation concerns and collision risks with shared services
- Created `DAEMON_ARCHITECTURE_SPEC_v2.0.md` with per-user service architecture
- Marked `DAEMON_ARCHITECTURE_SPEC_v1.0.md` as SUPERSEDED with deprecation notice

---

## Blocked

None

---

## Next Steps

1. **Implement Phase 1**: Create `WindowsTaskSchedulerManager` to replace NSSM-based `WindowsServiceManager`
   - Generate Task XML programmatically
   - Use `schtasks.exe` for task management (no admin required)
   - Test install/uninstall/start/stop/status

2. **Update DaemonManager**: Replace `WindowsServiceManager` reference with new Task Scheduler implementation

3. **Add Migration Logic**: Detect existing NSSM service and offer migration to user task

4. **Cross-Platform Testing**: Verify launchd (macOS) and systemd --user (Linux) work correctly

5. **Multi-User Port Handling**: Implement deterministic port assignment based on username hash

---

## Decisions Made

- **Per-user services over system services**: System services (NSSM, system-level systemd/launchd) break `Path.home()` because they run as SYSTEM/root. Per-user services run in user context where `Path.home()` works correctly.

- **Task Scheduler over NSSM (Windows)**: Task Scheduler user tasks require no admin privileges, run at user login (not system boot), and properly isolate users. NSSM creates system services that run as SYSTEM.

- **No GRAPHITI_HOME env var needed**: With per-user services, `Path.home()` resolves correctly. Environment variable pollution avoided.

- **Multi-user isolation by design**: Each user gets their own `~/.graphiti/`, their own port (8321-8399 range based on username hash), and complete isolation. No shared state, no collision risk.

- **Convention research**: Studied PostgreSQL, Redis, Docker, Elasticsearch, MongoDB patterns. System services use `C:\ProgramData\` (Windows) / `/var/lib/` (Linux) / `/usr/local/var/` (macOS). But MCP servers are inherently per-user (Claude sessions are user-specific), so user-level services are more appropriate.

---

## Errors Resolved

- **Root cause of GRAPHITI_HOME proposal**: The v1.0 spec used NSSM system services on Windows. NSSM runs services as SYSTEM user, where `Path.home()` returns `C:\WINDOWS\system32\config\systemprofile\` instead of `C:\Users\{username}`. The "fix" was an env var override, but the correct solution is per-user services that run in user context.

---

## Context

**Files Created**:
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v2.0.md` - Complete per-user daemon architecture specification

**Files Modified**:
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` - Marked as SUPERSEDED with deprecation notice

**Files Analyzed**:
- `mcp_server/daemon/windows_service.py` - NSSM-based system service implementation
- `mcp_server/daemon/bootstrap.py` - Bootstrap service with `Path.home()` calls
- `mcp_server/daemon/venv_manager.py` - Venv manager with `Path.home()` calls

---

## Architecture Comparison

| Aspect | v1.0 (System Service) | v2.0 (Per-User) |
|--------|----------------------|-----------------|
| Windows | NSSM system service | Task Scheduler user task |
| macOS | System launchd | User LaunchAgent |
| Linux | System systemd | `systemctl --user` |
| Runs as | SYSTEM/root | Current user |
| Admin required | Yes | No |
| `Path.home()` | Broken | Works correctly |
| Multi-user | Collision risk | Complete isolation |
| Starts at | System boot | User login |

---

**Session Duration**: ~45 minutes
**Token Usage**: ~35k estimated
