# Story 9: Integration Tests for Hybrid Flow (ST-H9)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: High
**Estimate**: L

## Description

Write comprehensive integration tests covering the full hybrid close flow including explicit close, lazy indexing, content deduplication, and timeout fallback.

## Acceptance Criteria

- [ ] (P0) Test `test_explicit_close_indexes`: session_tracking_close() triggers indexing
- [ ] (P0) Test `test_explicit_close_skips_unchanged`: Skip if hash matches
- [ ] (P0) Test `test_explicit_close_replaces_changed`: Delete + index if hash differs
- [ ] (P0) Test `test_lazy_index_on_search`: Unindexed sessions indexed before search
- [ ] (P1) Test `test_content_hash_stability`: Same content produces same hash
- [ ] (P1) Test `test_state_persistence`: States survive restart
- [ ] (P1) Test `test_full_hybrid_flow`: Explicit close -> query -> lazy index fallback
- [ ] (P2) Test `test_parallel_sessions`: Multiple active sessions handled independently
- [ ] (P2) Test `test_timeout_fallback`: Timeout triggers close after inactivity

## Dependencies

- Story 1-5: Core implementation complete

## Implementation Notes

- Location: `tests/session_tracking/test_hybrid_close.py` (NEW)
- See Section 12 of spec for full test requirements
- Use pytest fixtures for session setup/teardown

## Related Stories

- Depends on: Stories 1-5
- Validates: Entire hybrid close feature
