# Story 8: Validation Engine Skip Logic

**Status**: unassigned
**Created**: 2025-12-19 19:58

## Description

Update validation_engine.py to skip Check D if reconciliation already applied.

## Acceptance Criteria

- [ ] (P0) Check D skipped when validation has `reconciliation.status = propagated`
- [ ] Check D runs when `needs_retest = true`
- [ ] Check D skipped when validation has `reconciliation.status = superseded`
- [ ] Skip reason logged for audit trail
- [ ] Token savings achieved (96% reduction for propagate/supersede modes)

## Dependencies

Story 6

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 6: Remediation Testing Trigger
