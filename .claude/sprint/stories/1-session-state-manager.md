# Story 1: SessionStateManager with Persistence (ST-H1)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: High
**Estimate**: M

## Description

Implement the `SessionStateManager` class that tracks session lifecycle states with persistence to `~/.graphiti/session_states.json`. This is the foundation for all hybrid close features.

## Acceptance Criteria

- [ ] (P0) Create `SessionState` dataclass with fields: session_id, file_path, project_namespace, state (active/inactive/indexed/unindexed), content_hash, last_indexed_at, episode_uuid, last_activity, message_count
- [ ] (P0) Implement `SessionStateManager` class with CRUD operations for session states
- [ ] (P0) Implement persistence to `~/.graphiti/session_states.json` with atomic writes
- [ ] (P1) Implement state transitions per Section 6.2 of spec (ACTIVE -> INACTIVE -> INDEXING -> INDEXED)
- [ ] (P1) Load existing states on startup, handle missing/corrupt file gracefully
- [ ] (P2) Add logging for state transitions

## Dependencies

None (foundation story)

## Implementation Notes

- Location: `graphiti_core/session_tracking/state_manager.py` (NEW)
- Must be thread-safe for concurrent session updates
- Use file locking for atomic persistence writes

## Related Stories

- Blocks: Story 2, Story 3, Story 4, Story 5
