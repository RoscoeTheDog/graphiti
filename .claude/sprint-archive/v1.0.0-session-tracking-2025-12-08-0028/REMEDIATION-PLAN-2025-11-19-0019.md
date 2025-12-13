# Sprint Remediation Plan

**Generated**: 2025-11-19 00:19
**Type**: critical
**Impact**: 44 → 44 stories (no deletions/creations)
**Health**: 65 → 85 (projected)

## Modification Manifest

### Story 10: Complete filter.py Refactoring

**File**: `graphiti_core/session_tracking/filter.py`

**Problem**: Uses removed `ContentMode` enum (22 references)

**Changes Required**:

#### 1. Update Import Statement (Line 26)

**Current**:
```python
from graphiti_core.session_tracking.filter_config import ContentMode, FilterConfig
```

**New**:
```python
from graphiti_core.session_tracking.filter_config import FilterConfig
```

#### 2. Update __init__ Method (Lines 62-76)

**Current**:
```python
"""
...
Use FilterConfig(tool_content=ContentMode.FULL) instead.
"""
summarizer: Optional MessageSummarizer for ContentMode.SUMMARY support.
...
if preserve_tool_results is not None:
    warnings.warn(
        "preserve_tool_results is deprecated. "
        "Use FilterConfig(tool_content=ContentMode.FULL) instead."
    )
    self.config = FilterConfig(
        tool_content=ContentMode.FULL,
        user_messages=ContentMode.FULL,
        agent_messages=ContentMode.FULL
    )
```

**New**:
```python
"""
...
Use FilterConfig(tool_content=True) instead.
"""
summarizer: Optional MessageSummarizer for template/inline prompt support.
...
if preserve_tool_results is not None:
    warnings.warn(
        "preserve_tool_results is deprecated. "
        "Use FilterConfig(tool_content=True) instead."
    )
    self.config = FilterConfig(
        tool_content=True,
        user_messages=True,
        agent_messages=True
    )
```

#### 3. Update _filter_message Method (Lines 174-219)

**Current** (user_messages logic):
```python
if self.config.user_messages == ContentMode.FULL:
    filtered_content.append(content)
elif self.config.user_messages == ContentMode.OMIT:
    return None  # Skip this message entirely
...
elif self.config.user_messages == ContentMode.SUMMARY:
    if self.summarizer:
        summary = await self.summarizer.summarize_message(content)
        filtered_content.append(summary)
    else:
        logger.warning(
            "ContentMode.SUMMARY requested but no summarizer provided, "
            "falling back to FULL mode"
        )
        filtered_content.append(content)
else:  # ContentMode.FULL
    filtered_content.append(content)
```

**New** (bool | str type-based logic):
```python
# user_messages: True (full), False (omit), str (template/inline prompt)
if self.config.user_messages is True:
    filtered_content.append(content)
elif self.config.user_messages is False:
    return None  # Skip this message entirely
elif isinstance(self.config.user_messages, str):
    # Template or inline prompt (requires summarizer)
    if self.summarizer:
        summary = await self.summarizer.summarize_message(
            content,
            template_or_prompt=self.config.user_messages
        )
        filtered_content.append(summary)
    else:
        logger.warning(
            "Template/prompt requested for user_messages but no summarizer provided, "
            "falling back to full content"
        )
        filtered_content.append(content)
```

#### 4. Update _filter_message Method (Lines 226-247)

**Current** (agent_messages logic):
```python
if self.config.agent_messages == ContentMode.OMIT:
    continue  # Skip agent content entirely
elif self.config.agent_messages == ContentMode.SUMMARY:
    if self.summarizer:
        summary = await self.summarizer.summarize_message(
            content_block.get("text", "")
        )
        filtered_content.append({
            "type": "text",
            "text": summary
        })
    else:
        logger.warning(
            "ContentMode.SUMMARY requested but no summarizer provided, "
            "falling back to FULL mode"
        )
        filtered_content.append(content_block)
```

**New** (bool | str logic):
```python
if self.config.agent_messages is False:
    continue  # Skip agent content entirely
elif isinstance(self.config.agent_messages, str):
    # Template or inline prompt
    if self.summarizer:
        summary = await self.summarizer.summarize_message(
            content_block.get("text", ""),
            template_or_prompt=self.config.agent_messages
        )
        filtered_content.append({
            "type": "text",
            "text": summary
        })
    else:
        logger.warning(
            "Template/prompt requested for agent_messages but no summarizer provided, "
            "falling back to full content"
        )
        filtered_content.append(content_block)
else:  # True (preserve full content)
    filtered_content.append(content_block)
```

#### 5. Update _filter_message Method (Line 252)

**Current**:
```python
if self.config.tool_content == ContentMode.FULL:
    filtered_content.append(content_block)
```

**New**:
```python
if self.config.tool_content is True:
    filtered_content.append(content_block)
```

#### 6. Update _filter_message Method (Line 268)

**Current**:
```python
if tokens_modified or self.config.agent_messages != ContentMode.FULL:
    message.content = filtered_content
```

**New**:
```python
if tokens_modified or self.config.agent_messages is not True:
    message.content = filtered_content
```

#### 7. Update _summarize_tool_result Method (Line 298)

**Current**:
```python
if self.config.tool_content == ContentMode.FULL:
    return result
```

**New**:
```python
if self.config.tool_content is True:
    return result
elif self.config.tool_content is False:
    return "[Tool result omitted]"
elif isinstance(self.config.tool_content, str):
    # Template or inline prompt (future enhancement)
    # For now, fall back to built-in summarization
    logger.info(f"Template-based tool summarization not yet implemented, using built-in")
    # Continue to built-in summarization logic below
```

#### 8. Update Docstrings (Lines 100, 168)

**Current**:
```python
"""...ContentMode.SUMMARY is configured for user/agent messages."""
```

**New**:
```python
"""...template or inline prompt is configured for user/agent messages."""
```

---

### Test File Updates

#### test_filter_config.py

**File**: `tests/session_tracking/test_filter_config.py`

**Changes**:
1. Remove `ContentMode` import
2. Update all test assertions to use `bool | str` values:
   - `ContentMode.FULL` → `True`
   - `ContentMode.OMIT` → `False`
   - `ContentMode.SUMMARY` → `"template.md"` or `"inline prompt"`

**Example**:
```python
# OLD
def test_default_config():
    config = FilterConfig()
    assert config.tool_content == ContentMode.SUMMARY
    assert config.user_messages == ContentMode.FULL

# NEW
def test_default_config():
    config = FilterConfig()
    assert config.tool_content == "default-tool-content.md"
    assert config.user_messages is True
```

#### test_unified_config.py

**File**: `tests/test_unified_config.py`

**Changes**:
1. Add test for `keep_length_days` parameter:

```python
def test_session_tracking_keep_length_days():
    """Test keep_length_days parameter validation."""
    config_dict = {
        "session_tracking": {
            "enabled": True,
            "keep_length_days": 7
        }
    }
    config = GraphitiConfig(**config_dict)
    assert config.session_tracking.keep_length_days == 7

def test_session_tracking_keep_length_days_validation():
    """Test keep_length_days must be positive."""
    with pytest.raises(ValidationError):
        GraphitiConfig(
            session_tracking=SessionTrackingConfig(keep_length_days=-1)
        )
```

---

## Dependency Updates

### Story 9: Critical Bug Fix - Periodic Checker

**Current Status**: unassigned
**Dependencies**: Story 10 (BLOCKED)
**Action**: Unblock after Story 10 completion

**Validation**:
- Verify `keep_length_days` parameter available in `SessionTrackingConfig`
- Verify `enabled: false` default prevents unintended LLM costs
- Check rolling window filter implementation in Story 12 aligns with new schema

### Story 11: Template System Implementation

**Current Status**: unassigned
**Dependencies**: Story 10 (BLOCKED)
**Action**: Unblock after Story 10 completion

**Validation**:
- Verify `bool | str` pattern supports template filenames (e.g., `"custom-template.md"`)
- Check template hierarchy (project > global > built-in) aligns with FilterConfig design
- Validate backward compatibility with existing filter behavior

### Story 12: Rolling Period Filter

**Current Status**: unassigned
**Dependencies**: Story 10 (BLOCKED)
**Action**: Unblock after Story 10 completion

**Validation**:
- Verify `keep_length_days` parameter integration
- Check time-based filtering logic compatible with new schema

### Stories 13-16

**Current Status**: unassigned (all depend transitively on Story 10)
**Action**: Unblock cascade after Story 10 completion

---

## Index.md Rebuild

**No changes required** - index.md is accurate, all stories properly referenced.

---

## Breaking Change Mitigation

### User Migration Guide

**Add to CONFIGURATION.md**:

```markdown
## Migration from v0.4.x to v1.0.0

### ContentMode Enum Removed

**Old Configuration** (v0.4.x):
```json
{
  "session_tracking": {
    "filter": {
      "tool_content": "SUMMARY",
      "user_messages": "FULL",
      "agent_messages": "FULL"
    }
  }
}
```

**New Configuration** (v1.0.0):
```json
{
  "session_tracking": {
    "filter": {
      "tool_content": "default-tool-content.md",
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

**Migration Table**:
| Old Value | New Value | Behavior |
|-----------|-----------|----------|
| `ContentMode.FULL` / `"FULL"` | `true` | Preserve full content |
| `ContentMode.OMIT` / `"OMIT"` | `false` | Omit content entirely |
| `ContentMode.SUMMARY` / `"SUMMARY"` | `"template.md"` or `"inline prompt"` | Use template/LLM summarization |

### Default Changes

- `enabled: true` → `enabled: false` (opt-in security model)
- `tool_content: "SUMMARY"` → `tool_content: "default-tool-content.md"` (template-based)
- Added `keep_length_days: 7` (rolling window, prevents bulk indexing)

**Action Required**: Users upgrading from v0.3.x-v0.4.x must:
1. Set `enabled: true` explicitly if using session tracking
2. Update filter values from enum strings to bool/str
3. Review `keep_length_days` setting (default 7 days)
```

---

## Test Strategy

### Integration Testing Plan

1. **filter.py Refactoring** (Unit Tests):
   - Run `pytest tests/session_tracking/test_filter.py -v`
   - Expected: All 27 tests pass (may need updates for bool/str logic)

2. **FilterConfig Changes** (Schema Tests):
   - Run `pytest tests/session_tracking/test_filter_config.py -v`
   - Expected: 16 tests pass (update assertions for new type system)

3. **Unified Config** (Integration Tests):
   - Run `pytest tests/test_unified_config.py -v`
   - Expected: All tests + 2 new `keep_length_days` tests pass

4. **End-to-End** (Session Tracking):
   - Run `pytest tests/session_tracking/ -v`
   - Expected: 95/99 tests pass (3 existing failures unrelated to Story 10)

### Acceptance Criteria Validation

Story 10 AC verification:
- ✅ AC-10.1: FilterConfig uses bool | str (schema change complete)
- ✅ AC-10.2: SessionTrackingConfig defaults changed (enabled: false, etc.)
- ⏸️ AC-10.3: Migration guide created (pending in this plan)
- ⏸️ AC-10.4: Tests updated for new schema (pending execution)
- ⏸️ AC-10.5: Backward compatibility verified (pending testing)

---

## Estimated Impact

### Story Count

- **Before**: 44 stories (27 completed, 11 unassigned, 6 deprecated)
- **After**: 44 stories (28 completed, 10 unassigned, 6 deprecated)
- **Change**: +1 completed (Story 10)

### Health Score

- **Before**: 65/100 (Fair - significant gaps)
- **After**: 85/100 (Good - minor improvements recommended)
- **Improvement**: +20 points

**Calculation**:
- Remove 1 critical issue (Story 10 blocker): +20 points
- Remove 1 warning (uncommitted changes committed): +10 points
- Remove 1 warning (dependency chain unblocked): +10 points
- New total: 65 + 40 = 105 → capped at 100, realistic estimate 85

### Timeline Impact

**Blocked Work Unblocked**:
- Story 9: Critical Bug Fix (Phase 3, Week 1 Day 5)
- Story 11: Template System (Phase 4, Week 2 Days 1-2)
- Story 12: Rolling Period Filter (Phase 2, Week 1 Days 3-4)
- Story 13: Manual Sync Command (Phase 5, Week 2 Days 3-4)
- Story 14: Config Auto-Gen (Phase 6, Week 2 Day 5 - Week 3 Day 1)
- Story 15: Documentation Update (Phase 7, Week 3 Days 2-4)
- Story 16.1-16.4: Testing substories (Phase 8, Week 3 Days 4-5 - Week 4 Days 1-2)

**Total**: 8 stories unblocked (55% of remaining sprint work)

---

## Next Steps

1. **Review this plan carefully**
2. **Run**: `/sprint:REMEDIATE --validate` (dry-run simulation)
3. **After validation passes**:
   - Run `/sprint:REMEDIATE --apply` (execute on remediation branch)
   - Run `/sprint:REMEDIATE --merge` (merge back to sprint)
4. **Continue sprint**: `/sprint:NEXT` (will claim Story 9)

---

**Plan Complete**: Ready for validation phase.
