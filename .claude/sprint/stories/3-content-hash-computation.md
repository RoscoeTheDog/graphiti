# Story 3: Content Hash Computation and Comparison (ST-H3)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: High
**Estimate**: S

## Description

Implement content hash utilities for session deduplication. Hash is computed on filtered content (not raw JSONL) to ensure stability across non-semantic changes.

## Acceptance Criteria

- [ ] (P0) Implement `compute_session_hash(file_path: Path) -> str` function
- [ ] (P0) Hash must be computed on filtered content (after session_filter.filter_conversation)
- [ ] (P0) Use SHA-256 truncated to 16 characters for hash
- [ ] (P1) Implement deterministic serialization for hash stability
- [ ] (P1) Add hash comparison helper: `content_changed(old_hash: str, new_hash: str) -> bool`
- [ ] (P2) Add logging when hash matches (skip) vs differs (replace)

## Dependencies

- Story 1: SessionStateManager (stores content_hash)

## Implementation Notes

- Location: `graphiti_core/session_tracking/content_hasher.py` (NEW)
- See Section 4.2 of spec for hash algorithm details
- Serialization format: `"[{role}]: {content}"` joined by newlines

## Related Stories

- Depends on: Story 1
- Used by: Story 2, Story 4
