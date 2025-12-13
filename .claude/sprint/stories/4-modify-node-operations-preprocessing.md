# Story 4: Modify node_operations.py for Preprocessing Injection

**Status**: completed
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

### Changes Made

Modified `graphiti_core/utils/maintenance/node_operations.py` in the `extract_nodes()` function:

1. **Line 107-108**: Initialize `custom_prompt` with `clients.preprocessing_prompt` if available, otherwise empty string (AC-4.1)
   ```python
   custom_prompt = clients.preprocessing_prompt if clients.preprocessing_prompt else ''
   ```

2. **Line 134-144**: Moved context dict creation inside the while loop to ensure updated `custom_prompt` is used in each reflexion iteration (AC-4.5)

3. **Line 183-198**: Modified reflexion hint concatenation to respect `preprocessing_mode`:
   - Build reflexion hint separately
   - If `preprocessing_prompt` exists:
     - Prepend mode: `preprocessing + reflexion` (AC-4.3)
     - Append mode: `reflexion + preprocessing` (AC-4.3)
   - If no `preprocessing_prompt`: use reflexion hint only (AC-4.4)

### Acceptance Criteria Status

- [x] (P0) `extract_nodes()` reads `clients.preprocessing_prompt` for initial custom_prompt
- [x] (P0) Preprocessing concatenates with reflexion hints (not replaces)
- [x] (P0) Prepend mode: preprocessing + reflexion | Append mode: reflexion + preprocessing
- [x] (P1) Empty/None preprocessing_prompt preserves existing behavior
- [x] (P2) No performance regression when preprocessing disabled

### Testing

- All existing node_operations tests pass (23 tests)
- All preprocessing field tests pass (18 tests)
- Manual verification tests confirm all acceptance criteria
- Backward compatibility maintained

## Related Stories

- [Story 2: Extend GraphitiClients with Preprocessing Fields](2-extend-graphiticlients-preprocessing.md)
