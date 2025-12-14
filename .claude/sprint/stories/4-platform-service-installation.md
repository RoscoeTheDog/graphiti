# Story 4: Platform Service Installation (Windows/macOS/Linux)

**Status**: unassigned
**Created**: 2025-12-13 23:51

## Description

Implement platform-specific service managers for installing bootstrap as a native OS service. This enables the bootstrap service to run at system startup and survive reboots.

## Acceptance Criteria

- [ ] (P0) `daemon_manager.py` with platform abstraction layer implemented
- [ ] (P0) Windows service manager using NSSM (Non-Sucking Service Manager)
- [ ] (P0) macOS launchd service manager with plist template
- [ ] (P0) Linux systemd service manager with unit file template
- [ ] (P1) `graphiti-mcp daemon install` works on all three platforms
- [ ] (P1) `graphiti-mcp daemon uninstall` cleanly removes service on all platforms
- [ ] (P2) Service survives reboot on all platforms

## Dependencies

- Story 2: Bootstrap Service (Config Watcher + MCP Lifecycle)

## Implementation Notes

**Key Files to Create**:
- `mcp_server/daemon/manager.py` - Platform abstraction
- `mcp_server/daemon/windows_service.py` - NSSM wrapper
- `mcp_server/daemon/launchd_service.py` - macOS launchd
- `mcp_server/daemon/systemd_service.py` - Linux systemd
- `mcp_server/daemon/templates/graphiti-bootstrap.service` - systemd unit
- `mcp_server/daemon/templates/com.graphiti.bootstrap.plist` - launchd plist
- `mcp_server/daemon/templates/nssm_bootstrap.ps1` - Windows NSSM script

**CLI Commands** (installation lifecycle only):
```bash
graphiti-mcp daemon install    # Install bootstrap service
graphiti-mcp daemon uninstall  # Remove bootstrap service
graphiti-mcp daemon status     # Show current state
graphiti-mcp daemon logs       # Tail daemon logs
```

**NOT supported** (by design): `start`, `stop` commands

**Reference**: See `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` section "Platform-Specific Service Installation".

## Related Stories

- Depends on Story 2 (installs the bootstrap service)
