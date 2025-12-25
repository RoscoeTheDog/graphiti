# Story 15: macOS Fresh Install Test

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 5 - End-to-End Testing

## Description

Perform end-to-end testing of fresh v2.1 installation on macOS, verifying all paths, LaunchAgent registration, and MCP server functionality.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Define macOS test environment requirements
- [ ] Document test success criteria
- [ ] Create test checklist for manual verification
- [ ] Identify potential macOS-specific issues (permissions, etc.)

### (i) Implementation Phase
- [ ] (P0) Run full install on clean macOS environment
- [ ] Verify directories created in ~/Library/Application Support/Graphiti/
- [ ] Verify config directory created in ~/Library/Preferences/Graphiti/
- [ ] Verify LaunchAgent plist created in ~/Library/LaunchAgents/
- [ ] Verify launchctl load succeeds

### (t) Testing Phase
- [ ] (P0) Verify LaunchAgent loads on login
- [ ] (P0) Verify MCP server health check passes
- [ ] Verify MCP server accessible on expected port
- [ ] Verify logs are written to ~/Library/Logs/Graphiti/
- [ ] Test service restart with launchctl

## Dependencies

- Story 8: Update LaunchdServiceManager (macOS)
- Story 10: Fix Bootstrap Module Invocation

## Implementation Notes

Test on macOS 12+ (Monterey or newer) with Python 3.10+.
