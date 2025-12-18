# Story 4: CLI Commands - list-projects, set-override, remove-override

**Status**: unassigned
**Created**: 2025-12-18 09:23

## Description

Implement convenience CLI commands for managing project overrides without manually editing JSON.

## Acceptance Criteria

- [ ] (P0) `graphiti-mcp config list-projects` lists all projects with overrides
- [ ] (P0) `graphiti-mcp config set-override --project PATH --key KEY --value VALUE` adds/updates override
- [ ] (P0) `graphiti-mcp config remove-override --project PATH --key KEY` removes specific override
- [ ] (P1) `--all` flag for remove-override deletes all overrides for a project
- [ ] (P1) Commands validate key paths (e.g., `llm.default_model` is valid)
- [ ] (P1) Commands reject non-overridable sections with helpful error

## Dependencies

Story 2

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 2: Implement get_effective_config() Method](2-implement-get-effective-config-method.md)
