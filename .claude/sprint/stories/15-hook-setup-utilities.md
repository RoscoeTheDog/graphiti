# Story 15: Hook Setup/Installation Utilities (ST-H15)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: S

## Description

Create utilities for installing and configuring Claude Code hooks for automatic session tracking.

## Acceptance Criteria

- [ ] (P0) Create `setup_claude_code_hooks()` function
- [ ] (P0) Copy hook scripts to `~/.graphiti/hooks/`
- [ ] (P1) Optionally update `~/.claude/settings.json` with hook config (with user confirmation)
- [ ] (P1) Validate existing Claude Code settings before modifying
- [ ] (P2) Provide dry-run mode to preview changes
- [ ] (P2) Support uninstall/removal of hooks

## Dependencies

- Story 12: Hook script (to install)
- Story 13: MCP client library (to install)

## Implementation Notes

- Location: `graphiti_core/hooks/setup.py` (NEW)
- See Section 13.6 of spec for setup details
- Must not overwrite user's existing hook configurations

## Related Stories

- Depends on: Story 12, Story 13
- Documented by: Story 17
