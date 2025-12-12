# Story 4: Delete/Replace Logic in Indexer (ST-H4)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: High
**Estimate**: M

## Description

Implement the delete/replace strategy in the session indexer. When session content changes since last index, delete the old episode and create a new one.

## Acceptance Criteria

- [ ] (P0) Implement `replace_session_episode(session_id, old_episode_uuid, new_content, group_id)` function
- [ ] (P0) Function must delete old episode via `graphiti.delete_episode()`
- [ ] (P0) Function must index new content and return new episode UUID
- [ ] (P1) Update SessionStateManager with new episode_uuid and content_hash
- [ ] (P1) Handle case where old_episode_uuid is None (first index)
- [ ] (P2) Log deletion and replacement with episode UUIDs

## Dependencies

- Story 1: SessionStateManager (for episode_uuid tracking)
- Story 3: Content hash (for change detection)

## Implementation Notes

- Location: `graphiti_core/session_tracking/indexer.py` (modify existing)
- See Section 7.2 of spec for implementation details
- Graphiti handles cascade deletion of orphaned relationships

## Related Stories

- Depends on: Story 1, Story 3
- Used by: Story 2, Story 5
