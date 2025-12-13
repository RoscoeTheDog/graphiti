# Story 5: Update CLI Tools

**Status**: unassigned
**Created**: 2025-12-12 17:46

## Description

Update `session_tracking_cli.py` and `manual_sync.py` to remove references to deprecated parameters. CLI output should no longer display inactivity_timeout, check_interval, or auto_summarize settings.

## Acceptance Criteria

- [ ] (P0) Remove display of `inactivity_timeout`, `check_interval`, `auto_summarize` in CLI status
- [ ] (P1) Update CLI help text to reflect new architecture
- [ ] (P2) Remove any deprecated CLI commands if present

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Remove Deprecated Config Parameters
