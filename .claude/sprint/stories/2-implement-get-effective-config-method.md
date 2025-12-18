# Story 2: Implement get_effective_config() Method

**Status**: unassigned
**Created**: 2025-12-18 09:23

## Description

Add method to `GraphitiConfig` that resolves project-specific overrides and returns a merged configuration.

## Acceptance Criteria

- [ ] (P0) `get_effective_config(project_path)` method added to `GraphitiConfig`
- [ ] (P0) Method looks up normalized path in `project_overrides` dict
- [ ] (P0) If found, deep merges override with global config
- [ ] (P0) If not found, returns global config unchanged
- [ ] (P1) Updated `get_config()` function accepts optional `project_path` parameter
- [ ] (P1) Non-overridable sections (database, daemon) ignored in overrides with warning

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 1: Add ProjectOverride Schema and Deep Merge Logic](1-add-projectoverride-schema-and-deep-merge-logic.md)
