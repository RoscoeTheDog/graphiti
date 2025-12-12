# Story 7: Configuration Schema Updates (ST-H7)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: S

## Description

Update the configuration schema to add the new `close_strategy` section with all hybrid close options.

## Acceptance Criteria

- [ ] (P0) Add `close_strategy` section to session_tracking config schema
- [ ] (P0) Include fields: explicit_close_enabled, lazy_indexing_enabled, content_hash_dedup, inactivity_timeout
- [ ] (P0) Add `state_persistence` section with enabled and path fields
- [ ] (P1) Add Pydantic validation for new config fields
- [ ] (P1) Provide sensible defaults per Section 8.2 of spec
- [ ] (P2) Add _help fields with documentation strings

## Dependencies

None (can be done in parallel with Stories 1-4)

## Implementation Notes

- Location: `mcp_server/unified_config.py` (modify)
- See Section 8.1 of spec for full schema
- Backward compatible: missing close_strategy uses defaults

## Related Stories

- Used by: Story 8 (ensure_global_config_exists)
