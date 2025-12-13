# Story 2: Remove Session Manager Time-Based Logic

**Status**: unassigned
**Created**: 2025-12-12 17:46

## Description

Remove or refactor `session_manager.py` to eliminate time-based session tracking (inactivity detection, periodic checking). The turn-based architecture processes each user→assistant turn immediately, eliminating the need for time-based session boundaries.

## Acceptance Criteria

- [ ] (P0) Remove `inactivity_timeout` usage from `SessionManager.__init__`
- [ ] (P0) Remove `check_inactive_sessions_periodically` function
- [ ] (P1) Remove `_check_session_inactivity` method if present
- [ ] (P2) Evaluate if `SessionManager` class is still needed or can be simplified

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Remove Deprecated Config Parameters
