# Story 1: Auto-Enable Daemon on Install

**Status**: unassigned
**Created**: 2025-12-17 15:28

## Description

Modify `daemon install` to automatically set `daemon.enabled: true` in config after successful service installation, so the MCP server starts immediately without requiring manual config edits.

## Acceptance Criteria

- [ ] (P0) After successful `daemon install`, `daemon.enabled` is automatically set to `true` in graphiti.config.json
- [ ] (P0) The MCP server starts within 5 seconds of install completion (bootstrap detects config change)
- [ ] (P1) If config already exists with `daemon.enabled: false`, installer asks user before overwriting
- [ ] (P1) Success message updated to reflect that daemon is now running (no manual step needed)

## Dependencies

None

## Implementation Notes

**Key Files**:
- `mcp_server/daemon/manager.py` - `DaemonManager.install()` method
- `mcp_server/daemon/manager.py` - `DaemonManager._create_default_config()` method

**Implementation Approach**:
1. Modify `_create_default_config()` to set `enabled: true` by default
2. Add logic to `install()` to update existing config if present
3. Add user prompt if existing config has `enabled: false`
4. Update success message to indicate daemon is running

## Related Stories

- Story 2: Clear Error Feedback (dependent context)
- Story 3: Documentation Updates (will reference this change)
