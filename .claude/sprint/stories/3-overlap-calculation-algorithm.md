# Story 3: Overlap Calculation Algorithm

**Status**: unassigned
**Created**: 2025-12-19 19:58

## Description

Implement the test file overlap calculation algorithm that determines reconciliation mode (propagate vs retest).

## Acceptance Criteria

- [ ] (P0) `calculate_test_overlap()` function returns ratio of matching test files
- [ ] (P0) `same_test_parameters()` function compares threshold, command, etc.
- [ ] Overlap >= 0.95 qualifies for propagate mode
- [ ] Overlap >= 0.50 and < 0.95 triggers retest mode
- [ ] Overlap < 0.50 results in no_match (no reconciliation)
- [ ] Unit tests for edge cases (empty lists, identical lists, partial overlap)

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Metadata Schema Extension
