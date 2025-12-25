# Story 7: Update WindowsTaskSchedulerManager

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 3 - Service Manager Updates

## Description

Update the WindowsTaskSchedulerManager to use the new v2.1 installation paths, ensuring the Task Scheduler task uses the frozen Python executable and correct working directory.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Review current Task Scheduler XML template
- [ ] Identify all path references that need updating
- [ ] Document current pythonw.exe location vs new location
- [ ] Review working directory implications

### (i) Implementation Phase
- [ ] (P0) Update Command to use `{INSTALL_DIR}\bin\pythonw.exe`
- [ ] (P0) Update WorkingDirectory to `{INSTALL_DIR}`
- [ ] Update Arguments to use `-m mcp_server.daemon.bootstrap`
- [ ] Import and use paths.py for path resolution
- [ ] Update task XML template generation
- [ ] Ensure LogonType uses InteractiveToken (not S4U)

### (t) Testing Phase
- [ ] (P0) Verify generated Task XML has correct paths
- [ ] Verify task can be created with new paths
- [ ] Verify task runs under current user context (not SYSTEM)

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module
- Story 2: Migrate Daemon Modules to New Path System

## Implementation Notes

Key XML changes:
```xml
<Command>{INSTALL_DIR}\bin\pythonw.exe</Command>
<Arguments>-m mcp_server.daemon.bootstrap</Arguments>
<WorkingDirectory>{INSTALL_DIR}</WorkingDirectory>
```
