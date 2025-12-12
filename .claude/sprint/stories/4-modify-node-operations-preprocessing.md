# Story 4: Modify node_operations.py for Preprocessing Injection

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Update `extract_nodes()` to inject preprocessing_prompt via clients.preprocessing_prompt, concatenating with reflexion hints based on preprocessing_mode.

## Acceptance Criteria

- [ ] (P0) `extract_nodes()` reads `clients.preprocessing_prompt` for initial custom_prompt
- [ ] (P0) Preprocessing concatenates with reflexion hints (not replaces)
- [ ] (P0) Prepend mode: preprocessing + reflexion | Append mode: reflexion + preprocessing
- [ ] (P1) Empty/None preprocessing_prompt preserves existing behavior
- [ ] (P2) No performance regression when preprocessing disabled

## Dependencies

Story 2

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 2: Extend GraphitiClients with Preprocessing Fields](2-extend-graphiticlients-preprocessing.md)
