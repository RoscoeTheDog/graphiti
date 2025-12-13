# Story 6: Clean Up Test Files

**Status**: unassigned
**Created**: 2025-12-12 17:46

## Description

Remove or update test files that test deprecated functionality. Tests for time-based session detection, periodic checking, and file watching are no longer needed.

## Acceptance Criteria

- [ ] (P0) Identify tests in `tests/` referencing deprecated params
- [ ] (P0) Remove tests for `check_inactive_sessions_periodically`
- [ ] (P1) Remove tests for file watcher time-based behavior
- [ ] (P1) Update `test_config_validator.py` to remove deprecated param validation tests

## Dependencies

Stories 1-5

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Remove Deprecated Config Parameters
- Story 2: Remove Session Manager Time-Based Logic
- Story 3: Remove File Watcher Module
- Story 4: Clean Up MCP Server Session Initialization
- Story 5: Update CLI Tools
