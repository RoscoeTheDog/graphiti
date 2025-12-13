# Story 1: Remove Deprecated Config Parameters

**Status**: unassigned
**Created**: 2025-12-12 17:46

## Description

Remove `inactivity_timeout`, `check_interval`, and `auto_summarize` from config schema, unified_config.py, config validator, AND the global user config file. These parameters are obsolete after the turn-based indexing architecture replaced time-based session detection.

## Acceptance Criteria

- [ ] (P0) Remove 3 deprecated fields from `SessionTrackingConfig` in `unified_config.py`
- [ ] (P0) Remove validation logic for these fields in `config_validator.py`
- [ ] (P0) Remove deprecated params from `~/.graphiti/graphiti.config.json` (global config)
- [ ] (P1) Update `graphiti.config.schema.json` to remove deprecated fields
- [ ] (P1) Remove help text comments from config generation in `graphiti_mcp_server.py`

## Dependencies

None

## Implementation Notes

*To be added during implementation*

## Related Stories

None
