# Story 3: CLI Command - config effective

**Status**: unassigned
**Created**: 2025-12-18 09:23

## Description

Implement `graphiti-mcp config effective` CLI command to display computed configuration for a project.

## Acceptance Criteria

- [ ] (P0) `graphiti-mcp config effective` shows merged config for current directory
- [ ] (P0) `--project PATH` option specifies target project
- [ ] (P1) `--diff` flag shows only overridden values with before/after
- [ ] (P1) `--json` flag outputs machine-readable JSON
- [ ] (P1) Output highlights which values are overridden vs inherited
- [ ] (P2) Colored terminal output for better readability

## Dependencies

Story 2

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 2: Implement get_effective_config() Method](2-implement-get-effective-config-method.md)
