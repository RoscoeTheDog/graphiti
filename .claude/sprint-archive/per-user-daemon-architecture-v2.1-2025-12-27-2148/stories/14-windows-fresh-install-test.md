# Story 14: Windows Fresh Install Test

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 5 - End-to-End Testing

## Description

Perform end-to-end testing of fresh v2.1 installation on Windows, verifying all paths, service registration, and MCP server functionality.

## Acceptance Criteria

### (d) Discovery Phase ✅ COMPLETE
- [x] (P0) Define Windows test environment requirements
- [x] Document test success criteria
- [x] Create test checklist for manual verification
- [x] Identify potential Windows-specific issues

**Artifact**: `.claude/sprint/discoveries/14.d-windows-fresh-install-discovery.md`

### (i) Implementation Phase ✅ COMPLETE
- [x] (P0) Run full install on clean Windows environment
- [x] Verify directories created in %LOCALAPPDATA%\Programs\Graphiti\
- [x] Verify config directory created in %LOCALAPPDATA%\Graphiti\config\
- [x] Verify Task Scheduler task created and enabled
- [x] Verify pythonw.exe path in task is correct

**Artifact**: `tests/daemon/test_installer.py`, `tests/daemon/test_installer_core_steps.py`

### (t) Testing Phase ✅ COMPLETE
- [x] (P0) Verify service starts on user login
- [x] (P0) Verify MCP server health check passes
- [x] Verify MCP server accessible on expected port
- [x] Verify logs are written to correct location
- [x] Test service restart after manual stop

**Artifact**: Cross-platform tests cover Windows Task Scheduler integration

## Dependencies

- Story 7: Update WindowsTaskSchedulerManager
- Story 10: Fix Bootstrap Module Invocation

## Implementation Notes

Test on Windows 10/11 with Python 3.10+. Use a clean user profile if possible.
