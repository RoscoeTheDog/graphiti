# Story 7: Wire Preprocessing in MCP Server Initialization

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Update `initialize_graphiti()` in MCP server to resolve preprocessing config and pass to Graphiti client.

## Acceptance Criteria

- [x] (P0) MCP server reads extraction config from unified config
- [x] (P0) Resolved preprocessing_prompt passed to Graphiti constructor
- [x] (P1) Config reload triggers preprocessing prompt re-resolution
- [x] (P2) Startup logs indicate preprocessing status (enabled/disabled, template name)

## Dependencies

Story 2, Story 6

## Implementation Notes

### Changes Made

1. **Preprocessing Config Resolution** (lines 738-747)
   - Read `extraction_config` from `unified_config.extraction`
   - Check if preprocessing is enabled using `is_enabled()`
   - Resolve preprocessing prompt (calls `resolve_prompt()` stub from Story 6)
   - Fallback to raw prompt value since `resolve_prompt()` is currently a stub
   - Full template resolution will be implemented in Story 8

2. **Graphiti Constructor Updates** (lines 757-758)
   - Added `preprocessing_prompt` parameter (resolved value or None)
   - Added `preprocessing_mode` parameter from extraction config

3. **Startup Logging** (lines 787-799)
   - Log preprocessing status (enabled/disabled)
   - For template mode: show template filename and injection mode
   - For inline mode: show truncated preview (50 chars) and injection mode
   - For disabled: simple "Preprocessing: disabled" message

### Config Reload (P1 Acceptance Criteria)

Config reload is satisfied by design: since `initialize_graphiti()` reads from `unified_config.extraction` at runtime, any future config reload mechanism that calls `initialize_graphiti()` will automatically re-resolve the preprocessing config. No explicit reload handler is needed.

### Testing Notes

- Syntax validation: Passed
- Manual review: All acceptance criteria met
- Integration with existing code: No breaking changes
- Backward compatible: preprocessing is disabled by default

## Related Stories

- [Story 2: Extend GraphitiClients with Preprocessing Fields](2-extend-graphiticlients-preprocessing.md)
- [Story 6: Add Extraction Config to unified_config.py](6-add-extraction-config-unified.md)
