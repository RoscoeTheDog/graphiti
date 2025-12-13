# Story 15 Documentation Remediation Plan

**Story**: Story 15 - Documentation Update - Comprehensive User Guide  
**Status**: Remediation plan created  
**Created**: 2025-11-19  
**Estimated Effort**: 3.5-4 hours (6 tasks)  
**Sprint**: v1.0.0 Session Tracking Integration  

---

## Issues Identified

### Issue 1: CONFIGURATION.md - Outdated Type System (Lines 468-532)
- **Problem**: Still uses enum-style strings (`"full"`, `"summary"`, `"omit"`)
- **Reality**: Implementation uses `Union[bool, str]` (bool for true/false, str for template paths)
- **Impact**: Users will configure incorrectly, causing validation errors
- **Lines to fix**: 468-471 (example JSON), 479-489 (table + content modes), 495-532 (all 4 preset examples)

### Issue 2: CONFIGURATION.md - Incorrect Default Value (Line 466)
- **Problem**: Shows `"enabled": true`
- **Reality**: `enabled: bool = Field(default=False, ...)` (opt-in model)
- **Impact**: Misleading users about default behavior

### Issue 3: SESSION_TRACKING_USER_GUIDE.md - Contradictory Messaging (Lines 34-36, 113, 231, 326)
- **Problem**: Multiple locations state "enabled by default"
- **Reality**: Opt-in model (disabled by default)
- **Specific errors**:
  - Line 36: "Session tracking is **enabled by default**"
  - Line 113: `enabled` default listed as `true`
  - Line 231: "opt-out anytime"
  - Line 326: "now **enabled by default** (was opt-in previously)" - backwards!

### Issue 4: SESSION_TRACKING_MIGRATION.md - Missing File
- **Problem**: File does not exist
- **Required**: v1.0.0 → v1.1.0 migration guide per Story 15 spec

---

## Remediation Tasks

### Task 1: Update CONFIGURATION.md - Filter Type System (~45 min)
**Status**: pending  
**File**: `CONFIGURATION.md`  
**Complexity**: Medium (multiple sections)

**Changes**:
1. Update filter table (lines 479-484):
   - Change `"full"/"summary"/"omit"` to `true | false | "template-file.md"`
   - Update descriptions to reflect bool|str semantics
2. Rewrite "Content Modes" section (lines 486-489):
   - Replace enum descriptions with type system explanation:
     - `true`: Preserve complete content
     - `false`: Omit content (structure only)
     - `"template.md"`: Custom template path
3. Update all 4 preset examples (lines 495-532):
   - Change `"summary"` → template path (e.g., `"default-tool-content.md"`)
   - Change `"full"` → `true`
   - Change `"omit"` → `false`
4. Update line 542-545 (ContentMode.SUMMARY note):
   - Remove ContentMode references
   - Update to reflect template-based system

**Validation**:
- [ ] All JSON examples valid: `python -m json.tool`
- [ ] No enum strings remain (`"full"`, `"summary"`, `"omit"`)
- [ ] All filter examples use bool|str syntax

---

### Task 2: Update CONFIGURATION.md - Default Value (~5 min)
**Status**: pending  
**File**: `CONFIGURATION.md`  
**Complexity**: Low (simple find-replace)

**Changes**:
1. Line 466: Change `"enabled": true` → `"enabled": false`
2. Line 426 table: Change default column for `enabled` field from `true` to `false`
3. Add note: "Opt-in model for security (disabled by default)"

**Validation**:
- [ ] Example config shows `"enabled": false`
- [ ] Table default column accurate
- [ ] Security rationale documented

---

### Task 3: Update SESSION_TRACKING_USER_GUIDE.md - Opt-in Model (~30 min)
**Status**: pending  
**File**: `docs/SESSION_TRACKING_USER_GUIDE.md`  
**Complexity**: Low-Medium (multiple locations)

**Changes**:
1. Line 34-36: Rewrite section header and intro:
   - FROM: "Default Behavior (Enabled by Default)" / "enabled by default"
   - TO: "Default Behavior (Opt-In)" / "disabled by default, enable explicitly"
2. Line 113: Change `default: true` → `default: false`
3. Line 231: Change "opt-out anytime" → "opt-in (disabled by default)"
4. Line 324-328: **Delete entire section** (contradicts reality - never was opt-in before)
5. Add new "Enabling Session Tracking" section after line 38:
   ```markdown
   ## Enabling Session Tracking
   
   To enable session tracking, update your configuration:
   
   ```json
   {
     "session_tracking": {
       "enabled": true,
       ...
     }
   }
   ```
   ```

**Validation**:
- [ ] No "enabled by default" references remain
- [ ] All defaults show `false`
- [ ] Opt-in model clearly explained

---

### Task 4: Create SESSION_TRACKING_MIGRATION.md (~90 min)
**Status**: pending  
**File**: `docs/SESSION_TRACKING_MIGRATION.md` (new file)  
**Complexity**: Medium-High (new file, examples)

**Structure**:
```markdown
# Session Tracking Migration Guide: v1.0.0 → v1.1.0

## Breaking Changes

### 1. Opt-In Model (Security First)
**Changed**: `enabled` default changed from `true` → `false`
- **Impact**: Session tracking now disabled by default
- **Action**: Explicitly set `"enabled": true` if you want session tracking

### 2. Filter Configuration Type System
**Changed**: Filter fields changed from enum strings to `bool | str`
- **Before**: `"tool_content": "summary"`
- **After**: `"tool_content": "default-tool-content.md"` (template path)
- **Impact**: Old configs with `"full"/"summary"/"omit"` will fail validation
- **Action**: Update filter config per migration table below

### 3. Template System (New Feature)
**Added**: Pluggable summarization templates
- **Default**: Built-in templates (`default-tool-content.md`, etc.)
- **Customize**: Create templates in `.graphiti/auto-tracking/templates/`
- **Inline**: Use custom prompts directly

### 4. Rolling Period Filter (Cost Protection)
**Changed**: `keep_length_days` default changed from `None` → `7`
- **Impact**: Only last 7 days of sessions indexed by default
- **Action**: Set `null` to index all history (not recommended, expensive!)

### 5. Manual Sync Command (New Feature)
**Added**: `graphiti-mcp session-tracking sync` for historical data
- **Use**: Index sessions beyond rolling window
- **Flags**: `--days`, `--max-sessions`, `--dry-run`, `--confirm`

## Migration Examples

### Example 1: Minimal Config Update
**v1.0.0**:
```json
{
  "session_tracking": {
    "enabled": true
  }
}
```

**v1.1.0**:
```json
{
  "session_tracking": {
    "enabled": true,
    "filter": {
      "tool_content": "default-tool-content.md"
    }
  }
}
```

### Example 2: Custom Filtering Migration
**v1.0.0** (old enum system):
```json
{
  "filter": {
    "tool_content": "summary",
    "user_messages": "full",
    "agent_messages": "full"
  }
}
```

**v1.1.0** (new bool|str system):
```json
{
  "filter": {
    "tool_content": "default-tool-content.md",
    "user_messages": true,
    "agent_messages": true
  }
}
```

### Example 3: Maximum Privacy Migration
**v1.0.0**:
```json
{
  "filter": {
    "tool_content": "omit",
    "user_messages": "omit"
  }
}
```

**v1.1.0**:
```json
{
  "filter": {
    "tool_content": false,
    "user_messages": false
  }
}
```

## Checklist

- [ ] Update `enabled` field (explicit `true` if you want session tracking)
- [ ] Update filter config (enum strings → bool or template paths)
- [ ] Review `keep_length_days` (7 days default, change if needed)
- [ ] Test config: `python -m mcp_server.config_validator`
- [ ] Explore manual sync: `graphiti-mcp session-tracking sync --dry-run`
```

**Validation**:
- [ ] All migration examples tested
- [ ] Before/after configs clearly shown
- [ ] Breaking changes documented
- [ ] New features explained

---

### Task 5: Add Manual Sync Documentation (~15 min)
**Status**: pending  
**File**: `docs/SESSION_TRACKING_USER_GUIDE.md`  
**Complexity**: Low (straightforward)

**Location**: New section after line 150

**Content**:
```markdown
## Manual Sync - Indexing Historical Sessions

By default, Graphiti only indexes sessions from the last 7 days (`keep_length_days: 7`). To index older sessions:

### Dry-Run Mode (Preview)
```bash
graphiti-mcp session-tracking sync --dry-run
```

Outputs:
- Sessions found (within time range)
- Estimated cost ($0.17/session average)
- Sample sessions (first 10)

### Actual Sync
```bash
graphiti-mcp session-tracking sync --no-dry-run --days 30
```

**Flags**:
- `--days N` - Look back N days (default: 7)
- `--max-sessions N` - Safety limit (default: 100)
- `--project <path>` - Specific project (default: all)
- `--confirm` - Required for `--days 0` (all history)

**Cost Warning**: `--days 0` discovers ALL sessions. Could cost $100+ in LLM fees!
```

**Validation**:
- [ ] Command syntax correct
- [ ] Cost warnings prominent
- [ ] All flags documented

---

### Task 6: Document keep_length_days Parameter (~10 min)
**Status**: pending  
**File**: `CONFIGURATION.md`  
**Complexity**: Low (table + explanation)

**Changes**:
1. Add row to line 426 table:
   ```markdown
   | `keep_length_days` | int \| null | `7` | Rolling window for session discovery (days). `null` = discover all (expensive!) |
   ```

2. Add explanation after line 440:
   ```markdown
   **Rolling Window (`keep_length_days`)**:
   - **Default**: `7` days (last week only)
   - **Purpose**: Prevents expensive bulk indexing on first run
   - **Cost Impact**: 7 days ≈ 10-20 sessions ≈ $2-$4 | All history ≈ 1000+ sessions ≈ $170+
   - **Override**: Set to `null` to discover all sessions (not recommended unless you know the cost!)
   - **Manual Sync**: Use `graphiti-mcp session-tracking sync` for controlled historical indexing
   ```

**Validation**:
- [ ] Table entry complete
- [ ] Cost comparison clear
- [ ] Cross-reference to manual sync

---

## Effort Summary

| Task | Estimated Time | Complexity | Status |
|------|----------------|------------|--------|
| 1. CONFIGURATION.md filter type system | 45 min | Medium | pending |
| 2. CONFIGURATION.md default value | 5 min | Low | pending |
| 3. USER_GUIDE opt-in model | 30 min | Low-Medium | pending |
| 4. Create MIGRATION.md | 90 min | Medium-High | pending |
| 5. Add manual sync docs | 15 min | Low | pending |
| 6. Document keep_length_days | 10 min | Low | pending |
| **Total** | **195 min (3.25 hours)** | **Medium** | **0/6 complete** |

Add 15-30 min for JSON validation and final review → **3.5-4 hours total**

---

## Validation Checklist (Final)

After all tasks complete:
- [ ] All JSON examples validate: `python -m json.tool <file>`
- [ ] No references to ContentMode enum remain
- [ ] All filter examples use bool|str syntax
- [ ] Default values match implementation (enabled: false)
- [ ] Migration guide has before/after examples
- [ ] Manual sync command documented with cost warnings
- [ ] keep_length_days parameter fully documented
- [ ] Story 15 marked complete in sprint index

---

## Execution Notes

- **Session Boundaries**: This is a multi-session plan (3.5-4 hours total)
- **Task Independence**: Tasks 1-2 (CONFIGURATION.md), Task 3 (USER_GUIDE), Tasks 4-5 (new docs) are independent
- **Recommended Order**: Follow task sequence 1→6 for logical flow
- **Checkpoints**: Commit after each major task (1, 3, 4, 6)
- **Testing**: Run `python -m mcp_server.config_validator` after Task 1-2

---

**Plan Status**: Ready for execution  
**Next**: Begin Task 1 (CONFIGURATION.md filter type system)