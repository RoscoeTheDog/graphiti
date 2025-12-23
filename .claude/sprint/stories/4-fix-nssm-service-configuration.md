# Story 4: Fix NSSM service configuration

**Status**: unassigned
**Created**: 2025-12-23 14:49

## Description

Update the Windows service configuration to use module invocation (`-m mcp_server.daemon.bootstrap`) instead of direct script execution, and set `AppDirectory` to `~/.graphiti/`.

## Acceptance Criteria

- [ ] (P0) NSSM `AppParameters` uses `-m mcp_server.daemon.bootstrap`
- [ ] (P0) NSSM `AppDirectory` is set to `~/.graphiti/`
- [ ] (P0) Service starts successfully without relative import errors
- [ ] (P1) Service survives system reboot and auto-starts
- [ ] (P2) Service logs are written to `~/.graphiti/logs/`

## Dependencies

Story 2, Story 3

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 2: Deploy standalone package](2-deploy-standalone-package.md)
- [Story 3: Update venv_manager](3-update-venv-manager.md)
