# Story 2: session_tracking_close() MCP Tool (ST-H2)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: High
**Estimate**: S

## Description

Implement the `session_tracking_close()` MCP tool that allows agents/users to explicitly signal session completion and trigger immediate indexing.

## Acceptance Criteria

- [ ] (P0) Implement `session_tracking_close(session_id: str | None, reason: str | None)` MCP tool
- [ ] (P0) Tool must identify current active session if session_id not provided
- [ ] (P0) Tool must trigger immediate indexing (not queued)
- [ ] (P1) Return JSON with status, session_id, episode_uuid, message
- [ ] (P1) Integrate with content hash dedup (skip if unchanged, replace if changed)
- [ ] (P2) Log close reason in session metadata

## Dependencies

- Story 1: SessionStateManager (for state tracking)
- Story 3: Content hash (for deduplication)

## Implementation Notes

- Location: `mcp_server/graphiti_mcp_server.py` (add new tool)
- See Section 2.2 of spec for full tool signature
- Must work standalone without external dependencies (per Section 2.3)

## Related Stories

- Depends on: Story 1, Story 3
- Used by: Story 11 (hook integration)
