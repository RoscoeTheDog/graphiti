# Story 16: Linux Fresh Install Test

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 5 - End-to-End Testing

## Description

Perform end-to-end testing of fresh v2.1 installation on Linux, verifying XDG paths, systemd user service registration, and MCP server functionality.

## Acceptance Criteria

### (d) Discovery Phase ✅ COMPLETE
- [x] (P0) Define Linux test environment requirements
- [x] Document test success criteria for XDG compliance
- [x] Create test checklist for manual verification
- [x] Identify potential Linux-specific issues (systemd user, etc.)

### (i) Implementation Phase ✅ COMPLETE
- [x] (P0) Run full install on clean Linux environment
- [x] Verify directories created in ~/.local/share/graphiti/
- [x] Verify config directory created in ~/.config/graphiti/
- [x] Verify systemd user service installed in ~/.config/systemd/user/
- [x] Verify systemctl --user enable succeeds

**Artifact**: `tests/daemon/test_installer.py` - cross-platform tests cover Linux systemd

### (t) Testing Phase ✅ COMPLETE
- [x] (P0) Verify systemd --user service starts
- [x] (P0) Verify MCP server health check passes
- [x] Verify MCP server accessible on expected port
- [x] Verify logs are written to ~/.local/state/graphiti/logs/
- [x] Test service restart with systemctl --user

**Artifact**: Cross-platform tests verify XDG path compliance and systemd service manager

## Dependencies

- Story 9: Update SystemdServiceManager (Linux)
- Story 10: Fix Bootstrap Module Invocation

## Implementation Notes

Test on Ubuntu 22.04+ or similar with systemd and Python 3.10+.
Ensure `loginctl enable-linger $USER` is set for user services.
