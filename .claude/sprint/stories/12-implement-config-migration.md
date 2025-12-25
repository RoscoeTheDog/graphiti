# Story 12: Implement Config Migration

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 4 - Migration

## Description

Implement configuration file migration from v2.0 (`~/.graphiti/graphiti.config.json`) to the new v2.1 location.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Design config migration strategy (copy vs merge)
- [x] Identify any config schema changes between v2.0 and v2.1
- [x] Document backup strategy before migration
- [x] Design conflict resolution for existing v2.1 config

**Discovery Complete**: See `.claude/sprint/plans/12-plan.yaml` for full design

### (i) Implementation Phase
- [x] (P0) Implement `migrate_config()` function
- [x] Backup existing v2.0 config before migration
- [x] Copy config to new location (preserving content)
- [x] Handle case where v2.1 config already exists (prompt user)
- [x] Merge any v2.1-specific defaults if needed
- [x] Log migration actions

**Implementation Complete**: See `mcp_server/daemon/installer_migration.py` for full implementation

### (t) Testing Phase
- [ ] (P0) Verify config is copied to correct new location
- [ ] Verify original config is preserved as backup
- [ ] Verify config content is unchanged after migration

## Dependencies

- Story 11: Implement v2.0 Installation Detection

## Implementation Notes

New config locations:
- Windows: `%LOCALAPPDATA%\Graphiti\config\graphiti.config.json`
- macOS: `~/Library/Preferences/Graphiti/graphiti.config.json`
- Linux: `~/.config/graphiti/graphiti.config.json`
