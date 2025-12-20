# Story 2: Test Identity Capture in REMEDIATE

**Status**: unassigned
**Created**: 2025-12-19 19:58

## Description

Update `/sprint:REMEDIATE` command to capture test identity (files, command, threshold, original failure details) when creating remediation for Check D failures.

## Acceptance Criteria

- [ ] (P0) REMEDIATE.md updated to populate `test_reconciliation` metadata block
- [ ] (P0) Test files extracted from failure details and stored in metadata
- [ ] `--supersedes-tests` flag supported with required `--supersession-reason`
- [ ] `--retest-mode` flag supported to force retest instead of propagate
- [ ] Manual reconciliation still required (automation not yet implemented)

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Metadata Schema Extension
