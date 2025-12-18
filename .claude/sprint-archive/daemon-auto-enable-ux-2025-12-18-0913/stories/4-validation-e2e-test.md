# Story 4: Validation - End-to-End UX Test

**Status**: unassigned
**Created**: 2025-12-17 15:28

## Description

Validate the complete user flow from fresh install to working MCP connection in Claude Code.

## Acceptance Criteria

- [ ] (P0) Fresh install flow works: `daemon install` → MCP server running → Claude Code connects
- [ ] (P0) Error messages appear correctly when daemon not installed
- [ ] (P1) Reinstall scenario works (daemon already installed, run install again)
- [ ] (P1) Cross-platform validation (Windows focus, document Linux/macOS status)

## Dependencies

- Story 1: Auto-Enable Daemon on Install
- Story 2: Clear Error Feedback for Connection Failures
- Story 3: Update Installation Documentation

## Implementation Notes

**Test Scenarios**:

1. **Fresh Install (P0)**:
   - Uninstall existing daemon: `graphiti-mcp daemon uninstall`
   - Remove config: `rm ~/.graphiti/graphiti.config.json`
   - Run fresh install: `graphiti-mcp daemon install`
   - Verify: `graphiti-mcp daemon status` shows running
   - Verify: `curl http://127.0.0.1:8321/health` returns 200
   - Verify: Claude Code MCP tools work

2. **Error Messages (P0)**:
   - Stop daemon (set `enabled: false`)
   - Attempt MCP tool call
   - Verify error message is actionable

3. **Reinstall Scenario (P1)**:
   - With daemon running, run `daemon install` again
   - Verify no errors, daemon continues running
   - Verify config preserved

4. **Cross-Platform (P1)**:
   - Windows: Full validation (primary platform)
   - Linux/macOS: Document known status or test if available

**Validation Checklist**:
```
[ ] Fresh install creates config with enabled: true
[ ] MCP server starts within 5 seconds of install
[ ] Health check endpoint accessible
[ ] Claude Code can call MCP tools
[ ] Error messages guide user to fix issues
[ ] Reinstall is idempotent
```

## Related Stories

- Stories 1, 2, 3: All must be complete before validation
