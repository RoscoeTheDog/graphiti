# Story 5: Lazy Indexing in Search Tools (ST-H5)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: M

## Description

Implement lazy indexing that triggers on-demand when agents query the graph. This ensures unindexed sessions are indexed before search results are returned.

## Acceptance Criteria

- [ ] (P0) Add `find_unindexed_sessions(group_ids: list[str])` helper function
- [ ] (P0) Add `_ensure_sessions_indexed(group_ids)` pre-check to search_memory_nodes
- [ ] (P0) Add same pre-check to search_memory_facts and get_episodes
- [ ] (P1) Lazy indexing must be blocking (ensures fresh results)
- [ ] (P1) Support parallel indexing of multiple unindexed sessions
- [ ] (P2) Add progress indicator: "Indexing N recent sessions before search..."

## Dependencies

- Story 1: SessionStateManager (for tracking unindexed sessions)
- Story 4: Delete/replace indexer (for actual indexing)

## Implementation Notes

- Location: `mcp_server/graphiti_mcp_server.py` (modify search tools)
- See Section 3.2 and 3.3 of spec for mechanism details
- Respect close_strategy.lazy_indexing_enabled config flag

## Related Stories

- Depends on: Story 1, Story 4
- Triggered by: Story 6 (list unindexed tool)
