# Story 4: CLI Commands - list-projects, set-override, remove-override

**Status**: completed
**Created**: 2025-12-18 09:23
**Completed**: 2025-12-18 10:50

## Description

Implement convenience CLI commands for managing project overrides without manually editing JSON.

## Acceptance Criteria

- [x] (P0) `graphiti-mcp config list-projects` lists all projects with overrides
- [x] (P0) `graphiti-mcp config set-override --project PATH --key KEY --value VALUE` adds/updates override
- [x] (P0) `graphiti-mcp config remove-override --project PATH --key KEY` removes specific override
- [x] (P1) `--all` flag for remove-override deletes all overrides for a project
- [x] (P1) Commands validate key paths (e.g., `llm.default_model` is valid)
- [x] (P1) Commands reject non-overridable sections with helpful error

## Dependencies

Story 2 ✅ (completed)

## Implementation Notes

### Implementation Summary

All three CLI commands have been successfully implemented in `mcp_server/config_cli.py`:

1. **list-projects**: Lists all configured project overrides with their settings
2. **set-override**: Adds or updates project-specific configuration overrides
3. **remove-override**: Removes specific keys or all overrides for a project

### Key Features

- **Path Normalization**: All project paths are normalized to Unix format for consistency
- **Type Detection**: Values are automatically parsed to appropriate types (bool, int, float, string)
- **Key Validation**: Only overridable sections (llm, embedder, extraction, session_tracking) are allowed
- **Helpful Errors**: Clear error messages with examples when invalid sections are specified
- **Config Management**: Automatically creates global config if it doesn't exist

### Files Modified

1. `mcp_server/config_cli.py` - CLI implementation (already existed, includes all commands)
2. `mcp_server/pyproject.toml` - Added entry point `graphiti-mcp-config`
3. `tests/test_config_cli.py` - Comprehensive test coverage (64 tests, all passing)

### Test Results

All 64 tests passed successfully:
- Unit tests for key validation, value parsing, nested operations
- Integration tests for all three commands
- Edge case testing for error conditions

### Usage Examples

```bash
# List all projects with overrides
graphiti-mcp-config list-projects

# Set an override for a project
graphiti-mcp-config set-override --project ~/myproject --key llm.default_model --value gpt-4o

# Remove a specific override
graphiti-mcp-config remove-override --project ~/myproject --key llm.default_model

# Remove all overrides for a project
graphiti-mcp-config remove-override --project ~/myproject --all
```

## Related Stories

- [Story 2: Implement get_effective_config() Method](2-implement-get-effective-config-method.md)
