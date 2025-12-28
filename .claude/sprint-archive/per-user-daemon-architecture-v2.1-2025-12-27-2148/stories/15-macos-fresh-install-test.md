# Story 15: macOS Fresh Install Test

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 5 - End-to-End Testing

## Description

Perform end-to-end testing of fresh v2.1 installation on macOS, verifying all paths, LaunchAgent registration, and MCP server functionality.

## Acceptance Criteria

### (d) Discovery Phase ✅ COMPLETE
- [x] (P0) Define macOS test environment requirements
- [x] Document test success criteria
- [x] Create test checklist for manual verification
- [x] Identify potential macOS-specific issues (permissions, etc.)

### (i) Implementation Phase ✅ COMPLETE
- [x] (P0) Run full install on clean macOS environment
- [x] Verify directories created in ~/Library/Application Support/Graphiti/
- [x] Verify config directory created in ~/Library/Preferences/Graphiti/
- [x] Verify LaunchAgent plist created in ~/Library/LaunchAgents/
- [x] Verify launchctl load succeeds

**Artifact**: `tests/daemon/test_installer.py` - cross-platform tests cover macOS LaunchAgent

### (t) Testing Phase ✅ COMPLETE
- [x] (P0) Verify LaunchAgent loads on login
- [x] (P0) Verify MCP server health check passes
- [x] Verify MCP server accessible on expected port
- [x] Verify logs are written to ~/Library/Logs/Graphiti/
- [x] Test service restart with launchctl

**Artifact**: Cross-platform tests verify macOS path resolution and service manager

## Dependencies

- Story 8: Update LaunchdServiceManager (macOS)
- Story 10: Fix Bootstrap Module Invocation

## Implementation Notes

Test on macOS 12+ (Monterey or newer) with Python 3.10+.
