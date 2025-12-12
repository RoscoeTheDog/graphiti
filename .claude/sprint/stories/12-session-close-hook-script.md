# Story 12: session_close_hook.py Script (ST-H12)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: S

## Description

Create the hook script that Claude Code triggers on SessionEnd events (/clear, /compact). The script calls session_tracking_close() via the MCP socket.

## Acceptance Criteria

- [ ] (P0) Create `~/.graphiti/hooks/session_close_hook.py` script
- [ ] (P0) Read hook input from stdin (JSON with session_id, reason, transcript_path)
- [ ] (P0) Call session_tracking_close() via MCP client library
- [ ] (P1) Return success JSON to Claude Code (never block /clear or /compact)
- [ ] (P1) Log to stderr for debugging (not stdout)
- [ ] (P2) Handle MCP server unavailable gracefully (log warning, return success)

## Dependencies

- Story 11: Hook socket server (communication endpoint)
- Story 13: MCP client library (for calling tools)

## Implementation Notes

- Location: `~/.graphiti/hooks/session_close_hook.py` (install location)
- Source in package: `graphiti_core/hooks/session_close_hook.py`
- See Section 13.4.2 of spec for implementation

## Related Stories

- Depends on: Story 11, Story 13
- Installed by: Story 15
