# Story 14: Windows Fresh Install Test

**Status**: discovery-complete
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

### (i) Implementation Phase
- [ ] (P0) Run full install on clean Windows environment
- [ ] Verify directories created in %LOCALAPPDATA%\Programs\Graphiti\
- [ ] Verify config directory created in %LOCALAPPDATA%\Graphiti\config\
- [ ] Verify Task Scheduler task created and enabled
- [ ] Verify pythonw.exe path in task is correct

### (t) Testing Phase
- [ ] (P0) Verify service starts on user login
- [ ] (P0) Verify MCP server health check passes
- [ ] Verify MCP server accessible on expected port
- [ ] Verify logs are written to correct location
- [ ] Test service restart after manual stop

## Dependencies

- Story 7: Update WindowsTaskSchedulerManager
- Story 10: Fix Bootstrap Module Invocation

## Implementation Notes

Test on Windows 10/11 with Python 3.10+. Use a clean user profile if possible.
