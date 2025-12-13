# Story 5: Modify edge_operations.py for Preprocessing Injection

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Update `extract_edges()` with same preprocessing injection pattern as node_operations.

## Acceptance Criteria

- [x] (P0) `extract_edges()` reads `clients.preprocessing_prompt` for initial custom_prompt
- [x] (P0) Preprocessing concatenates with reflexion hints (not replaces)
- [x] (P0) Mode handling matches node_operations (prepend/append)
- [x] (P1) Empty/None preprocessing_prompt preserves existing behavior

## Dependencies

Story 2, Story 4

## Implementation Notes

### Changes Made

Modified `graphiti_core/utils/maintenance/edge_operations.py`:

1. **Initialization (line 113)**: Added initialization of `custom_prompt` with `clients.preprocessing_prompt` if available, otherwise empty string
   ```python
   custom_prompt = clients.preprocessing_prompt if clients.preprocessing_prompt else ''
   ```

2. **Context Setup (line 144)**: Updated initial context to use `custom_prompt` instead of hardcoded empty string
   ```python
   'custom_prompt': custom_prompt,
   ```

3. **Reflexion Loop (lines 176-191)**: Modified reflexion hint handling to concatenate with preprocessing_prompt based on mode:
   - Build reflexion hint from missing facts
   - If `preprocessing_prompt` exists:
     - Prepend mode: `preprocessing_prompt + reflexion_hint`
     - Append mode: `reflexion_hint + preprocessing_prompt`
   - If no `preprocessing_prompt`: use reflexion hint only (preserves existing behavior)

### Pattern Alignment

This implementation exactly mirrors the pattern used in `node_operations.py` (Story 4):
- Same initialization approach (line 108 in node_operations)
- Same mode handling logic (lines 189-199 in node_operations)
- Same preservation of existing behavior when preprocessing is not used

### Testing

- All existing tests pass (7 passed)
- No regression in edge extraction functionality
- Syntax validated successfully

## Related Stories

- [Story 2: Extend GraphitiClients with Preprocessing Fields](2-extend-graphiticlients-preprocessing.md)
- [Story 4: Modify node_operations.py for Preprocessing Injection](4-modify-node-operations-preprocessing.md)
