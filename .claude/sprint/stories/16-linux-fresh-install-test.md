# Story 16: Linux Fresh Install Test

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 5 - End-to-End Testing

## Description

Perform end-to-end testing of fresh v2.1 installation on Linux, verifying XDG paths, systemd user service registration, and MCP server functionality.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Define Linux test environment requirements
- [ ] Document test success criteria for XDG compliance
- [ ] Create test checklist for manual verification
- [ ] Identify potential Linux-specific issues (systemd user, etc.)

### (i) Implementation Phase
- [ ] (P0) Run full install on clean Linux environment
- [ ] Verify directories created in ~/.local/share/graphiti/
- [ ] Verify config directory created in ~/.config/graphiti/
- [ ] Verify systemd user service installed in ~/.config/systemd/user/
- [ ] Verify systemctl --user enable succeeds

### (t) Testing Phase
- [ ] (P0) Verify systemd --user service starts
- [ ] (P0) Verify MCP server health check passes
- [ ] Verify MCP server accessible on expected port
- [ ] Verify logs are written to ~/.local/state/graphiti/logs/
- [ ] Test service restart with systemctl --user

## Dependencies

- Story 9: Update SystemdServiceManager (Linux)
- Story 10: Fix Bootstrap Module Invocation

## Implementation Notes

Test on Ubuntu 22.04+ or similar with systemd and Python 3.10+.
Ensure `loginctl enable-linger $USER` is set for user services.
