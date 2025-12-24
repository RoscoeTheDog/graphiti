# Story 5: End-to-end installation test

**Status**: unassigned
**Created**: 2025-12-23 14:49

## Description

Create integration test that validates the complete daemon installation flow works on a clean system (simulated by removing `~/.graphiti/`).

## Acceptance Criteria

- [ ] (P0) Test can install daemon from scratch (no existing `~/.graphiti/`)
- [ ] (P0) Test verifies service starts and responds on health endpoint
- [ ] (P1) Test verifies daemon runs independently of project directory
- [ ] (P1) Test documents any manual steps required (e.g., admin privileges)

## Dependencies

Story 4

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 4: Fix NSSM service configuration](4-fix-nssm-service-configuration.md)
