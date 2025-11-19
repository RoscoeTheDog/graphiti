# Story 10: Configuration Schema Changes - Safe Defaults & Simplification

**Status**: error
**Created**: 2025-11-18 23:01
**Claimed**: 2025-11-18 23:55
**Error**: 2025-11-19 00:04
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

## Implementation Progress

### Completed
- [x] FilterConfig: Removed ContentMode enum, updated to `bool | str` type system
- [x] SessionTrackingConfig: Changed defaults to opt-in model (enabled: false, auto_summarize: false)
- [x] SessionTrackingConfig: Increased inactivity_timeout from 300 to 900 seconds
- [x] SessionTrackingConfig: Added `keep_length_days` parameter with validation
- [x] graphiti.config.json: Updated with new defaults

### Remaining Work
- [ ] **CRITICAL**: Update filter.py to work with `bool | str` instead of ContentMode enum
  - Lines 26, 62-63, 70, 73-76, 100, 168, 174-304 reference ContentMode
  - Need to refactor comparison logic: `== ContentMode.FULL` → `is True`
  - Need to handle string values (templates/prompts) - requires new logic
  - Estimated: 2-3 hours
- [ ] Update test_filter_config.py to work with new type system
  - Remove ContentMode imports
  - Update all test assertions to use `True`, `False`, or string values
  - Estimated: 1-2 hours
- [ ] Update test_unified_config.py for keep_length_days validation
  - Test null value accepted
  - Test positive integers accepted
  - Test zero/negative rejected
  - Estimated: 30 minutes

## Blockers

**Cannot complete story until filter.py is refactored** - The existing filtering logic is tightly coupled to ContentMode enum. Needs careful refactoring to:
1. Interpret `True` as "preserve full content"
2. Interpret `False` as "omit content"  
3. Interpret strings as either template paths or inline prompts
4. Maintain backward compatibility with existing behavior

**Risk**: Breaking existing functionality if not done carefully.

## Next Steps

1. Refactor filter.py content mode handling
2. Update all tests
3. Run full test suite
4. Verify backward compatibility
5. Update documentation


## Remediation Plan

**Root Cause**: Schema changes (FilterConfig using `bool | str`) are complete, but runtime logic (filter.py) still uses ContentMode enum comparisons. This creates an import error that blocks all session tracking tests.

**Fix Required**:

1. **Refactor filter.py** (CRITICAL - 2-3 hours):
   - Remove `from graphiti_core.session_tracking.filter_config import ContentMode`
   - Replace all enum comparisons with type-based logic:
     ```python
     # OLD
     if self.config.user_messages == ContentMode.FULL:
         return message
     elif self.config.user_messages == ContentMode.OMIT:
         return omitted_message
     elif self.config.user_messages == ContentMode.SUMMARY:
         return summarized_message
     
     # NEW
     if self.config.user_messages is True:  # bool True = FULL
         return message
     elif self.config.user_messages is False:  # bool False = OMIT
         return omitted_message
     elif isinstance(self.config.user_messages, str):  # str = SUMMARY (template or inline prompt)
         return await self._apply_template_or_prompt(self.config.user_messages, message)
     ```
   - Implement template/inline prompt handling (NEW functionality)
   - Update backward compatibility logic (preserve_tool_results parameter)

2. **Update test_filter_config.py** (HIGH - 1-2 hours):
   - Remove `ContentMode` imports
   - Replace enum values with bool/str: `ContentMode.FULL` → `True`, `ContentMode.OMIT` → `False`, `ContentMode.SUMMARY` → `"default-tool-content.md"`
   - Update all assertions to match new types

3. **Add keep_length_days tests** (MEDIUM - 30 min):
   - test_unified_config.py: Add validation tests for new parameter

4. **Integration testing** (MEDIUM - 1 hour):
   - Run full test suite
   - Verify backward compatibility
   - Test all filter config combinations

**Action**: Story cannot be completed without filter.py refactoring. Split into substory or continue in next session.

**Dependencies**: None (this work is blocking Story 9, 11, 12)

**Estimated Completion**: 4-6 hours additional work
