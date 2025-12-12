# Story 7: Wire Preprocessing in MCP Server Initialization

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Update `initialize_graphiti()` in MCP server to resolve preprocessing config and pass to Graphiti client.

## Acceptance Criteria

- [ ] (P0) MCP server reads extraction config from unified config
- [ ] (P0) Resolved preprocessing_prompt passed to Graphiti constructor
- [ ] (P1) Config reload triggers preprocessing prompt re-resolution
- [ ] (P2) Startup logs indicate preprocessing status (enabled/disabled, template name)

## Dependencies

Story 2, Story 6

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 2: Extend GraphitiClients with Preprocessing Fields](2-extend-graphiticlients-preprocessing.md)
- [Story 6: Add Extraction Config to unified_config.py](6-add-extraction-config-unified.md)
