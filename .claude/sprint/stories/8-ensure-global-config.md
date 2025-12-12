# Story 8: Update ensure_global_config_exists() (ST-H8)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: S

## Description

Update the `ensure_global_config_exists()` function to include new hybrid close configuration fields when creating default config.

## Acceptance Criteria

- [ ] (P0) Add close_strategy section to default config template
- [ ] (P0) Add state_persistence section to default config template
- [ ] (P1) Preserve existing config values when upgrading (merge, don't overwrite)
- [ ] (P1) Add hooks section for future hook integration (Story 11+)
- [ ] (P2) Log when new config sections are added to existing config

## Dependencies

- Story 7: Configuration schema (defines the schema)

## Implementation Notes

- Location: `mcp_server/unified_config.py` (modify ensure_global_config_exists)
- Must handle config migration from old format
- Test with both fresh install and upgrade scenarios

## Related Stories

- Depends on: Story 7
