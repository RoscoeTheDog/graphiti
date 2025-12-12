# Story 6: session_tracking_list_unindexed() Tool (ST-H6)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Low
**Estimate**: S

## Description

Implement MCP tool to list sessions that have not been indexed yet. Useful for debugging lazy indexing and manual intervention.

## Acceptance Criteria

- [ ] (P0) Implement `session_tracking_list_unindexed(project_namespace, include_inactive)` MCP tool
- [ ] (P0) Return JSON with count and session details (session_id, file_path, state, last_activity, message_count)
- [ ] (P1) Filter by project_namespace if provided
- [ ] (P1) Optionally include inactive sessions (default: True)
- [ ] (P2) Sort by last_activity descending

## Dependencies

- Story 1: SessionStateManager (data source)

## Implementation Notes

- Location: `mcp_server/graphiti_mcp_server.py` (add new tool)
- See Section 9.1 of spec for full tool signature
- Diagnostic tool, not critical path

## Related Stories

- Depends on: Story 1
