# Story 10: Configuration Schema Changes - Safe Defaults & Simplification

**Status**: unassigned
**Created**: 2025-11-18 23:01
**Priority**: HIGH
**Estimated Effort**: 6 hours
**Phase**: 2 (Week 1, Days 3-4)
**Depends on**: Story 9 (not blocking, but recommended first)

## Description

Implement comprehensive configuration schema changes to address security concerns and simplify the user experience:

1. **Safe Defaults**: Change to opt-in model (enabled: false, auto_summarize: false)
2. **Simplification**: Remove enum-based system, use `bool | str` types
3. **Better Timing**: Increase `inactivity_timeout` to 900s (15 minutes) for long-running operations
4. **Rolling Window**: Add `keep_length_days` parameter to prevent bulk indexing

## Acceptance Criteria

### FilterConfig Changes
- [ ] Change type: `ContentMode` enum → `bool | str`
- [ ] Remove `max_summary_chars` parameter (redundant with templates)
- [ ] Update field descriptions to reflect new type system
- [ ] Update validation logic for `bool | str` values
- [ ] Test: `true` resolves to full content
- [ ] Test: `false` resolves to omit
- [ ] Test: `"template.md"` resolves to template path
- [ ] Test: `"inline prompt..."` resolves to inline prompt

### SessionTrackingConfig Defaults
- [ ] Change `enabled: true` → `false` (opt-in security)
- [ ] Change `inactivity_timeout: 300` → `900` (15 min for long operations)
- [ ] Change `auto_summarize: true` → `false` (no LLM costs by default)
- [ ] Change `filter.tool_content: ContentMode.SUMMARY` → `"default-tool-content.md"`
- [ ] Test: Default config loads without errors
- [ ] Test: Default config requires explicit enable
- [ ] Test: Default config has no LLM costs

### New Parameter: keep_length_days
- [ ] Add `keep_length_days` field to `SessionTrackingConfig`
- [ ] Type: `Optional[int]` (null = all, N = last N days)
- [ ] Default: `7` (safe rolling window)
- [ ] Validation: Must be > 0 or null
- [ ] Update field description
- [ ] Test: null value accepted
- [ ] Test: positive integers accepted
- [ ] Test: zero/negative rejected with clear error

## Implementation Details

### Files to Modify

**`graphiti_core/session_tracking/filter_config.py`**:

1. Remove ContentMode enum entirely
2. Update FilterConfig class:
```python
class FilterConfig(BaseModel):
    """Configuration for message filtering during session tracking.

    Filter values use bool | str type system:
    - true: Preserve full content (no filtering)
    - false: Omit content entirely
    - "template.md": Load template from hierarchy (project > global > built-in)
    - "inline prompt...": Use string as direct LLM prompt
    """

    tool_calls: bool = True
    tool_content: bool | str = "default-tool-content.md"
    user_messages: bool | str = True
    agent_messages: bool | str = True

    # max_summary_chars REMOVED (templates self-describe length)
```

**`mcp_server/unified_config.py`**:

1. Update SessionTrackingConfig defaults:
```python
class SessionTrackingConfig(BaseModel):
    """Session tracking configuration."""

    enabled: bool = False  # Changed from True (opt-in security)
    watch_path: Optional[Path] = None
    inactivity_timeout: int = 900  # Changed from 300 (15 min for long ops)
    check_interval: int = 60
    auto_summarize: bool = False  # Changed from True (no LLM costs)
    store_in_graph: bool = True
    keep_length_days: Optional[int] = 7  # NEW: Rolling window filter
    filter: FilterConfig = Field(default_factory=FilterConfig)

    @field_validator('keep_length_days')
    def validate_keep_length_days(cls, v):
        if v is not None and v <= 0:
            raise ValueError("keep_length_days must be > 0 or null")
        return v
```

**`graphiti.config.json`**:

Update example configuration with new defaults:
```json
{
  "session_tracking": {
    "enabled": false,
    "watch_path": null,
    "inactivity_timeout": 900,
    "check_interval": 60,
    "auto_summarize": false,
    "store_in_graph": true,
    "keep_length_days": 7,
    "filter": {
      "tool_calls": true,
      "tool_content": "default-tool-content.md",
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

### Testing Requirements

**Update**: `tests/session_tracking/test_filter_config.py`

1. Add tests for `bool | str` type resolution
2. Remove tests for ContentMode enum
3. Remove tests for max_summary_chars

**Update**: `tests/test_unified_config.py`

1. Test new defaults load correctly
2. Test keep_length_days validation
3. Test backward compatibility (old configs still load)

## Migration Notes

**Breaking Changes**:
1. `FilterConfig.tool_content` type changed from `ContentMode` to `bool | str`
2. `max_summary_chars` removed (use templates to control length)
3. Default `enabled` changed from `true` to `false`
4. Default `auto_summarize` changed from `true` to `false`
5. Default `inactivity_timeout` changed from `300` to `900`

**Migration Strategy**:
- Users upgrading will need to explicitly set `enabled: true` to re-enable tracking
- Old `ContentMode.SUMMARY` configs map to `"default-tool-content.md"`
- Old `ContentMode.FULL` configs map to `true`
- Old `ContentMode.OMIT` configs map to `false`

## Dependencies

- Story 9 recommended first (but not blocking)

## Related Documents

- `.claude/handoff/session-tracking-complete-overhaul-2025-11-18.md` (Section: Design Evolution, Final Configuration Schema)
- `.claude/handoff/session-tracking-security-concerns-2025-11-18.md` (Security analysis)

## Cross-Cutting Requirements

See parent sprint `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`:
- Type hints: All fields properly typed
- Validation: Pydantic validators for new fields
- Testing: >80% coverage with migration tests
- Documentation: Updated config examples
