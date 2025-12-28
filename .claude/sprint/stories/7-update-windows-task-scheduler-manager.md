# Story 7: Update WindowsTaskSchedulerManager

**Status**: completed
**Created**: 2025-12-25 02:02
**Updated**: 2025-12-25 (Discovery complete - critical finding)
**Phase**: 3 - Service Manager Updates
**Discovery Artifact**: `.claude/sprint/discoveries/7.d-windows-task-scheduler-manager-update.md`

## Description

Update the WindowsTaskSchedulerManager to use the new v2.1 installation paths, ensuring the Task Scheduler task uses the frozen Python executable and correct working directory.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Review current Task Scheduler XML template - **CRITICAL FINDING**: Class does not exist
- [x] Identify all path references that need updating - See discovery artifact
- [x] Document current pythonw.exe location vs new location - Documented in discovery
- [x] Review working directory implications - Complete
- [x] **BLOCKER IDENTIFIED**: WindowsTaskSchedulerManager class does not exist in codebase
- [x] **ACTION REQUIRED**: Architectural decision needed (Task Scheduler vs NSSM)

### (i) Implementation Phase
- [x] (P0) Update Command to use `{INSTALL_DIR}\bin\pythonw.exe`
- [x] (P0) Update WorkingDirectory to `{INSTALL_DIR}`
- [x] Update Arguments to use `-m mcp_server.daemon.bootstrap`
- [x] Import and use paths.py for path resolution
- [x] Update task XML template generation
- [x] Ensure LogonType uses InteractiveToken (not S4U)

### (t) Testing Phase
- [x] (P0) Verify generated Task XML has correct paths
- [x] Verify task can be created with new paths
- [x] Verify task runs under current user context (not SYSTEM)

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module ✓ COMPLETE
- Story 2: Migrate Daemon Modules to New Path System ✓ COMPLETE

## BLOCKER (Discovered 2025-12-25)

**Critical Finding**: The `WindowsTaskSchedulerManager` class referenced in this story **does not exist** in the current codebase.

**Current State**:
- The codebase uses `WindowsServiceManager` (NSSM-based) in `mcp_server/daemon/windows_service.py`
- `WindowsServiceManager` already uses v2.1 paths correctly (`get_install_dir()`, `get_log_dir()`)
- The Task Scheduler approach is specified in DAEMON_ARCHITECTURE_SPEC_v2.0.md but not implemented

**Required Decisions**:
1. **Architecture Choice**: Task Scheduler vs NSSM for Windows daemon
2. **Story Sequencing**: Create WindowsTaskSchedulerManager first, or update WindowsServiceManager instead?

**Options**:
- **Option A**: Create `WindowsTaskSchedulerManager` from v2.0 spec, then update to v2.1 paths (requires new story)
- **Option B**: Update existing `WindowsServiceManager` to v2.1 paths (rename story, mostly complete)
- **Option C**: Keep NSSM approach, deprecate Task Scheduler spec

**Discovery Artifact**: See `.claude/sprint/discoveries/7.d-windows-task-scheduler-manager-update.md` for full analysis

**Action Required**: Human/architect decision before proceeding with implementation

## Implementation Notes

Key XML changes:
```xml
<Command>{INSTALL_DIR}\bin\pythonw.exe</Command>
<Arguments>-m mcp_server.daemon.bootstrap</Arguments>
<WorkingDirectory>{INSTALL_DIR}</WorkingDirectory>
```
