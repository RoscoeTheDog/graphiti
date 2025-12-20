# Discovery Findings: Story 2 - Implement get_effective_config() Method

**Date**: 2025-12-18
**Story**: 2 - Implement get_effective_config() Method
**Phase**: Discovery (2.d)

## Executive Summary

Story 2 builds on Story 1's foundation (ProjectOverride schema, normalize_project_path, deep_merge) to add the `get_effective_config()` method that resolves project-specific configuration overrides. The implementation is straightforward: normalize the project path, look it up in the `project_overrides` dictionary, deep merge if found, and return a new GraphitiConfig instance.

**Estimated Complexity**: Medium
**Estimated Lines of Code**: ~230 (80 implementation + 150 tests)
**Estimated Tokens**: ~5000
**Risk Level**: Low-Medium (Pydantic model merging, backward compatibility)

## Key Files to Modify

### 1. mcp_server/unified_config.py

**Location**: Lines ~1040-1120 (new methods in GraphitiConfig class)

**Changes Required**:

1. **Add `get_effective_config(project_path: str) -> GraphitiConfig` method** (~40 lines)
   - Normalize project_path using `normalize_project_path()`
   - Look up normalized path in `self.project_overrides` dict
   - If not found: return self (global config)
   - If found: deep merge override with global config, return new instance

2. **Add `_validate_override(override_dict, project_path)` helper** (~20 lines)
   - Check for non-overridable sections (database, daemon, resilience, etc.)
   - Log warnings for each non-overridable section found
   - Do not raise exceptions (permissive validation)

3. **Update `get_config(reload, force_reload, project_path=None)` function** (~20 lines)
   - Add optional `project_path` parameter
   - After loading config, if project_path provided: call `config.get_effective_config(project_path)`
   - Return effective config instead of base config
   - Maintain backward compatibility (existing calls without project_path work unchanged)

### 2. tests/test_project_overrides.py

**Location**: New test class `TestGetEffectiveConfig` (~150 lines)

**Tests to Add**:

1. **Basic functionality**:
   - `test_get_effective_config_no_override`: Path not in overrides → returns self
   - `test_get_effective_config_with_override`: Path in overrides → returns merged config

2. **Merge behavior**:
   - `test_get_effective_config_merge_llm`: Override llm.provider → merged config has new provider
   - `test_get_effective_config_merge_nested`: Override session_tracking.enabled → nested merge works
   - `test_get_effective_config_none_inherits`: Override with None values → inherits from global

3. **Path normalization**:
   - `test_get_effective_config_normalizes_path`: Windows path C:\\ → normalizes to /c/ for lookup

4. **get_config() integration**:
   - `test_get_config_with_project_path`: Call get_config(project_path='/path') → returns effective config
   - `test_get_config_without_project_path`: Call get_config() → returns global config (backward compat)

5. **Validation**:
   - `test_validate_override_warns_database`: Override contains database section → logs warning
   - `test_validate_override_warns_daemon`: Override contains daemon section → logs warning
   - `test_validate_override_warns_multiple`: Override with multiple non-overridable → logs all warnings

6. **End-to-end**:
   - `test_get_effective_config_end_to_end`: Full workflow with override, verify merged values

## Implementation Approach

### Algorithm: get_effective_config()

```python
def get_effective_config(self, project_path: str) -> GraphitiConfig:
    """Get effective config for a specific project (global + project override).

    Args:
        project_path: Absolute path to project directory

    Returns:
        GraphitiConfig instance with project overrides applied
    """
    # 1. Normalize path for consistent lookup
    normalized_path = normalize_project_path(project_path)

    # 2. Look up override
    override = self.project_overrides.get(normalized_path)
    if override is None:
        return self  # No override, return global config

    # 3. Convert to dicts for merging
    base_dict = self.model_dump()
    override_dict = override.model_dump(exclude_none=True)

    # 4. Validate override (log warnings for non-overridable sections)
    self._validate_override(override_dict, normalized_path)

    # 5. Deep merge
    merged_dict = deep_merge(base_dict, override_dict)

    # 6. Reconstruct and return
    return GraphitiConfig(**merged_dict)
```

### Algorithm: _validate_override()

```python
def _validate_override(self, override_dict: Dict[str, Any], project_path: str) -> None:
    """Validate project override and log warnings for non-overridable sections.

    Args:
        override_dict: Override configuration as dict
        project_path: Project path (for warning messages)
    """
    non_overridable = {
        'database', 'daemon', 'resilience', 'mcp_server',
        'logging', 'version', 'project', 'search', 'performance'
    }

    for section in non_overridable:
        if section in override_dict:
            logger.warning(
                f"Project override for '{project_path}' contains non-overridable "
                f"section '{section}', ignoring"
            )
```

### Algorithm: get_config() update

```python
def get_config(
    reload: bool = False,
    force_reload: bool = False,
    project_path: str | None = None
) -> GraphitiConfig:
    """Get the global configuration instance.

    Args:
        reload: Force reload from file (deprecated, use force_reload)
        force_reload: Force reload from file
        project_path: Optional project path for project-specific overrides

    Returns:
        GraphitiConfig instance (with project overrides if project_path provided)
    """
    global _config_instance

    should_reload = reload or force_reload

    if _config_instance is None or should_reload:
        _config_instance = GraphitiConfig.from_file()
        _config_instance.apply_env_overrides()

    # NEW: Apply project-specific overrides if requested
    if project_path is not None:
        return _config_instance.get_effective_config(project_path)

    return _config_instance
```

## Key Design Decisions

### 1. Return New Instance vs Modify In-Place

**Decision**: `get_effective_config()` returns a NEW GraphitiConfig instance

**Rationale**:
- Immutability: Preserves global config unchanged
- Thread safety: Multiple calls with different project_paths don't interfere
- Testability: Clear input/output, no side effects

### 2. Non-Overridable Section Validation

**Decision**: Log warnings but don't raise exceptions

**Rationale**:
- ProjectOverride schema already rejects non-overridable sections via `extra='forbid'`
- This validation is defense-in-depth (if schema is bypassed)
- Warnings are visible in logs but don't break functionality
- Permissive approach allows for future schema evolution

### 3. Pydantic Model Merging

**Decision**: Convert to dict → merge → reconstruct

**Rationale**:
- Pydantic models don't support direct merging
- `model_dump()` + `deep_merge()` + `GraphitiConfig(**merged)` is clean pattern
- `exclude_none=True` on override preserves deep_merge None semantics
- Reconstructed model validates merged config automatically

### 4. Backward Compatibility in get_config()

**Decision**: Add optional `project_path` parameter (default None)

**Rationale**:
- Existing calls `get_config()` continue to work without changes
- New calls `get_config(project_path='/path')` opt into override behavior
- No breaking changes to existing codebase
- Future Story 3 can gradually migrate MCP tools to pass project_path

## Integration with Story 1

Story 1 provided the building blocks:

1. **ProjectOverride schema** (lines 837-850): Defines overridable sections
2. **normalize_project_path()** (lines 1103-1145): Cross-platform path normalization
3. **deep_merge()** (lines 1148-1195): Recursive dict merging with None inheritance

Story 2 uses all three:

- `normalize_project_path()`: For consistent project_overrides dict lookups
- `deep_merge()`: For merging base config with override
- `ProjectOverride`: Schema for project_overrides dict values

## Edge Cases to Handle

### 1. Empty Override (All Fields None)

**Scenario**: Override exists but all fields are None
```python
project_overrides = {
    "/c/Users/Admin/project": ProjectOverride(llm=None, embedder=None, extraction=None, session_tracking=None)
}
```

**Handling**: `deep_merge()` with all None values inherits everything from global config (correct behavior)

### 2. Partial Override

**Scenario**: Only one field in one section specified
```python
project_overrides = {
    "/c/Users/Admin/project": ProjectOverride(
        llm=LLMConfig(provider="anthropic"),  # Only provider changed
        embedder=None,
        extraction=None,
        session_tracking=None
    )
}
```

**Handling**: `deep_merge()` merges `llm.provider`, inherits all other fields from global config (correct behavior)

### 3. Path Normalization Edge Cases

**Scenarios**:
- Windows path: `C:\Users\Admin\project` → `/c/Users/Admin/project`
- Forward slash Windows: `C:/Users/Admin/project` → `/c/Users/Admin/project`
- Unix path: `/home/user/project` → `/home/user/project`
- MSYS path: `/c/Users/Admin/project` → `/c/Users/Admin/project`
- Relative path: `./project` → Resolves to absolute, then normalizes
- Tilde: `~/project` → Expands to home dir, then normalizes

**Handling**: `normalize_project_path()` (from Story 1) handles all cases via `Path.resolve()` + `as_posix()` + Windows drive conversion

### 4. Multiple Calls to get_effective_config()

**Scenario**: Call `get_effective_config("/path/A")` then `get_effective_config("/path/B")`

**Handling**: Each call returns a new independent instance (idempotent, no side effects)

## Testing Strategy

### Test Coverage Goals

- **Unit tests**: >90% coverage of new methods
- **Integration tests**: End-to-end workflow with overrides
- **Edge case tests**: Empty overrides, partial overrides, path normalization
- **Backward compatibility tests**: get_config() without project_path still works

### Test Organization

All tests in `tests/test_project_overrides.py`:

```python
class TestGetEffectiveConfig:
    """Test get_effective_config() method"""
    # Basic functionality tests
    # Merge behavior tests
    # Path normalization tests
    # Validation tests
    # Integration tests
```

### Key Test Assertions

1. **No override**: `assert config.get_effective_config('/path') is config`
2. **With override**: `assert merged.llm.provider == 'anthropic'` (override), `assert merged.llm.temperature == 0.0` (inherited)
3. **Path normalization**: `assert config.get_effective_config('C:\\path') == config.get_effective_config('/c/path')`
4. **Warnings**: `assert "non-overridable section 'database'" in caplog.text`

## Dependencies

### Story 1 (Completed)

Story 1 must be completed and merged before implementing Story 2:

- ✅ ProjectOverride schema defined
- ✅ normalize_project_path() implemented
- ✅ deep_merge() implemented
- ✅ Tests passing

### External Dependencies

- Python typing: `Dict`, `Any`, `Optional`
- Pydantic: `BaseModel`, `model_dump()`
- logging: `logger.warning()`
- pathlib: `Path` (already imported)

## Future Integration (Story 3)

Story 3 will update MCP tools to use project-specific configs:

```python
# Before (Story 2):
config = get_config()

# After (Story 3):
project_path = extract_project_path_from_context()  # From filepath or group_id
config = get_config(project_path=project_path)
```

MCP tools to update in Story 3:
- `add_memory()`: Extract project_path from filepath parameter
- `search_memory_nodes()`: Extract project_path from group_ids
- `search_memory_facts()`: Extract project_path from group_ids

## Risk Assessment

### Low Risk

- Implementation is straightforward (method calls Story 1 functions)
- Pydantic model reconstruction is well-tested pattern
- Backward compatibility preserved via optional parameter

### Medium Risk

1. **Pydantic model merging**:
   - Risk: `model_dump()` → `deep_merge()` → `GraphitiConfig(**merged)` could fail validation
   - Mitigation: Unit tests verify reconstruction, integration tests verify end-to-end

2. **Non-overridable section detection**:
   - Risk: Hardcoded list of non-overridable sections could drift from schema
   - Mitigation: Use set-based check, document clearly, add test to verify list is complete

### Mitigation Strategies

1. **Comprehensive testing**: Unit + integration + edge case tests
2. **Type safety**: Use type hints, mypy validation
3. **Documentation**: Clear docstrings, inline comments
4. **Validation**: _validate_override() provides defense-in-depth

## Success Criteria

1. ✅ All P0 acceptance criteria met and tested
2. ✅ All P1 acceptance criteria met and tested
3. ✅ Test coverage >80% for new code
4. ✅ Type checking passes (mypy)
5. ✅ Linting passes (ruff)
6. ✅ No breaking changes to existing API
7. ✅ Documentation complete (docstrings + plan)

## Open Questions

None - Story 1 provided clear foundation, implementation approach is straightforward.

## Estimated Timeline

- Implementation: 2-3 hours
- Testing: 2-3 hours
- Documentation: 1 hour
- **Total**: 5-7 hours

## Notes for Implementation Phase

1. **Start with tests**: Write tests first (TDD approach) to clarify expected behavior
2. **Incremental approach**: Implement get_effective_config() first, then _validate_override(), then get_config() update
3. **Verify Story 1 works**: Run Story 1 tests to ensure foundation is solid before building on it
4. **Use existing patterns**: Follow GraphitiConfig method patterns (instance methods, return new instances)
5. **Check logs**: Verify warning messages are clear and helpful

## References

- Story 1 implementation: `mcp_server/unified_config.py` lines 837-1195
- Story 1 tests: `tests/test_project_overrides.py`
- GraphitiConfig class: `mcp_server/unified_config.py` lines 858-1095
- get_config() function: `mcp_server/unified_config.py` lines 1206-1225
