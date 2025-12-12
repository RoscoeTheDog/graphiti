# Story 5: Modify edge_operations.py for Preprocessing Injection

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Update `extract_edges()` with same preprocessing injection pattern as node_operations.

## Acceptance Criteria

- [ ] (P0) `extract_edges()` reads `clients.preprocessing_prompt` for initial custom_prompt
- [ ] (P0) Preprocessing concatenates with reflexion hints (not replaces)
- [ ] (P0) Mode handling matches node_operations (prepend/append)
- [ ] (P1) Empty/None preprocessing_prompt preserves existing behavior

## Dependencies

Story 2, Story 4

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 2: Extend GraphitiClients with Preprocessing Fields](2-extend-graphiticlients-preprocessing.md)
- [Story 4: Modify node_operations.py for Preprocessing Injection](4-modify-node-operations-preprocessing.md)
