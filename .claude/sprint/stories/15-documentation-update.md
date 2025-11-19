# Story 15: Documentation Update - Comprehensive User Guide

**Status**: completed
**Created**: 2025-11-18 23:01
**Updated**: 2025-11-19 12:12 (Marked complete per handoff s004)
**Claimed**: 2025-11-19 12:04 (Session 004)
**Completed**: 2025-11-19 (6/6 tasks complete per handoff s004)
**Priority**: HIGH
**Estimated Effort**: 12 hours (Actual: ~2.5 hours per handoff)
**Phase**: 7 (Week 3, Days 3-5)
**Depends on**: Stories 9-14 (all implementation complete)

## Description

Update all documentation to reflect the session tracking overhaul. This includes configuration reference, user guide, and migration guide. Documentation must be comprehensive, clear, and include examples for all new features.

**Scope**:
- Update CONFIGURATION.md with all 10 parameters
- Update SESSION_TRACKING_USER_GUIDE.md with new features
- Create SESSION_TRACKING_MIGRATION.md for users upgrading
- Add examples, troubleshooting, and FAQs

## Acceptance Criteria

### CONFIGURATION.md Updates
- [ ] Document all 10 session_tracking parameters
- [ ] Explain `bool | str` type system
- [ ] Document template system with hierarchy
- [ ] Document file structure (`.graphiti/auto-tracking/templates/`)
- [ ] Add configuration examples for common scenarios
- [ ] Add migration guide section
- [ ] Test: All examples are valid JSON
- [ ] Test: All parameter descriptions are accurate

### SESSION_TRACKING_USER_GUIDE.md Updates
- [ ] Update quick start to reflect opt-in model
- [ ] Add template customization section
- [ ] Add manual sync documentation
- [ ] Add troubleshooting section
- [ ] Add cost analysis section
- [ ] Add security best practices
- [ ] Test: All examples work as documented
- [ ] Test: Quick start guide successful on fresh install

### SESSION_TRACKING_MIGRATION.md Creation
- [ ] Document breaking changes from v1.0.0 to v1.1.0
- [ ] Provide before/after migration examples
- [ ] Add FAQ section for common migration issues
- [ ] Add version compatibility table
- [ ] Test: Migration examples accurate

## Implementation Details

### Files to Update

**`CONFIGURATION.md`**:

Add comprehensive session_tracking section:

```markdown
## Session Tracking Configuration

Session tracking enables automatic indexing of Claude Code sessions into Graphiti's knowledge graph for cross-session continuity.

### Parameters

#### enabled

**Type**: `bool`
**Default**: `false` (opt-in security model)

Enable or disable session tracking. Must be explicitly set to `true` to start tracking.

**Example**:
```json
{
  "session_tracking": {
    "enabled": true
  }
}
```

#### watch_path

**Type**: `str | null`
**Default**: `null` (watches `~/.claude/projects/`)

Path to directory containing session JSONL files. When `null`, defaults to `~/.claude/projects/`.

**Examples**:
```json
// Watch all projects (default)
"watch_path": null

// Watch specific project
"watch_path": "/home/user/my-project"
```

#### inactivity_timeout

**Type**: `int`
**Default**: `900` (15 minutes)

Seconds of inactivity before a session is considered closed. Set higher for long-running operations.

**Recommended values**:
- Realtime: `300` (5 min)
- Balanced: `900` (15 min) - DEFAULT
- Conservative: `1800` (30 min)

#### check_interval

**Type**: `int`
**Default**: `60` (1 minute)

Seconds between inactivity checks. Lower values = more responsive, higher overhead.

**Recommended values**:
- Realtime: `30` (30 sec)
- Balanced: `60` (1 min) - DEFAULT
- Conservative: `120` (2 min)

#### auto_summarize

**Type**: `bool`
**Default**: `false` (no LLM costs by default)

Enable LLM-based summarization of sessions. Costs ~$0.17 per session.

**Example**:
```json
{
  "session_tracking": {
    "auto_summarize": true  // Opt-in to LLM costs
  }
}
```

#### store_in_graph

**Type**: `bool`
**Default**: `true`

Store sessions in Neo4j graph. Required for cross-session memory.

#### keep_length_days

**Type**: `int | null`
**Default**: `7` (rolling 7-day window)

Only auto-discover sessions modified in last N days. Prevents bulk indexing on first run.

**Examples**:
```json
// Safe default (last 7 days)
"keep_length_days": 7

// Last 30 days
"keep_length_days": 30

// All sessions (use with caution!)
"keep_length_days": null
```

#### filter

**Type**: `object`
**Default**: See FilterConfig below

Message filtering configuration for token reduction.

### FilterConfig - Message Filtering

#### Type System: bool | str

Filter values use a flexible `bool | str` type system:

- `true`: Preserve full content (no filtering)
- `false`: Omit content entirely
- `"template.md"`: Load template from hierarchy (project > global > built-in)
- `"inline prompt..."`: Use string as direct LLM prompt

**Examples**:
```json
{
  "filter": {
    "tool_calls": true,                        // Preserve full structure
    "tool_content": "default-tool-content.md", // Use template
    "user_messages": false,                    // Omit entirely
    "agent_messages": "Summarize in 1 sentence" // Inline prompt
  }
}
```

#### Template Resolution Hierarchy

1. **Project template**: `<project>/.graphiti/auto-tracking/templates/{name}.md`
2. **Global template**: `~/.graphiti/auto-tracking/templates/{name}.md`
3. **Built-in template**: Packaged with Graphiti
4. **Inline prompt**: Use string directly if not .md file

#### Built-in Templates

- `default-tool-content.md`: Summarize tool results in 1 paragraph
- `default-user-messages.md`: Summarize user messages in 1-2 sentences
- `default-agent-messages.md`: Summarize agent responses in 1 paragraph

### Configuration Examples

#### Example 1: Minimal (Opt-in, Safe Defaults)

```json
{
  "session_tracking": {
    "enabled": true
  }
}
```

This enables tracking with safe defaults:
- Watches `~/.claude/projects/`
- No LLM costs (auto_summarize: false)
- 7-day rolling window
- 15-minute inactivity timeout

#### Example 2: Single Project with Aggressive Summarization

```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": "/home/user/my-project",
    "auto_summarize": true,
    "filter": {
      "tool_content": "default-tool-content.md",
      "user_messages": "default-user-messages.md",
      "agent_messages": "default-agent-messages.md"
    }
  }
}
```

This enables:
- Single project tracking
- LLM-based summarization (~70% token reduction)
- Cost: ~$0.17 per session

#### Example 3: Conservative (No Filtering, Long Timeout)

```json
{
  "session_tracking": {
    "enabled": true,
    "inactivity_timeout": 1800,
    "check_interval": 120,
    "keep_length_days": 30,
    "filter": {
      "tool_calls": true,
      "tool_content": true,
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

This enables:
- Full content preservation (no summarization)
- 30-minute inactivity timeout
- 30-day rolling window
- Maximum memory accuracy

### Migration from v1.0.0

**Breaking Changes**:
1. `enabled` default changed from `true` to `false`
2. `auto_summarize` default changed from `true` to `false`
3. `inactivity_timeout` default changed from `300` to `900`
4. FilterConfig type changed from enum to `bool | str`
5. `max_summary_chars` removed (use templates)

**Migration Examples**:

```json
// OLD (v1.0.0)
{
  "session_tracking": {
    "enabled": true,  // Implicit
    "filter": {
      "tool_content": "summary"  // Enum
    },
    "summary_prompts": {
      "max_summary_chars": 500
    }
  }
}

// NEW (v1.1.0)
{
  "session_tracking": {
    "enabled": true,  // Explicit required
    "filter": {
      "tool_content": "default-tool-content.md"  // Template
    }
    // max_summary_chars removed
  }
}
```

See `docs/SESSION_TRACKING_MIGRATION.md` for detailed migration guide.
```

**`docs/SESSION_TRACKING_USER_GUIDE.md`**:

Update sections:
1. Quick start (reflect opt-in model)
2. Template customization examples
3. Manual sync documentation
4. Cost analysis section
5. Troubleshooting section

**Create `docs/SESSION_TRACKING_MIGRATION.md`**:

```markdown
# Session Tracking Migration Guide

This guide helps you migrate from Graphiti v1.0.0 to v1.1.0 session tracking.

## Breaking Changes

### 1. Opt-in Security Model

**Change**: Default `enabled: true` → `enabled: false`

**Impact**: Session tracking is now disabled by default. You must explicitly enable it.

**Migration**:
```json
{
  "session_tracking": {
    "enabled": true  // Add this line to re-enable
  }
}
```

### 2. No LLM Costs by Default

**Change**: Default `auto_summarize: true` → `auto_summarize: false`

**Impact**: No LLM costs by default. Opt-in to enable summarization.

**Migration**:
```json
{
  "session_tracking": {
    "auto_summarize": true  // Add this line to re-enable
  }
}
```

### 3. Longer Inactivity Timeout

**Change**: Default `inactivity_timeout: 300` → `inactivity_timeout: 900`

**Impact**: Sessions stay active longer (15 min vs 5 min).

**Migration**: No action needed if default is acceptable. Set explicitly if needed:
```json
{
  "session_tracking": {
    "inactivity_timeout": 300  // Restore old behavior
  }
}
```

### 4. Template-Based Filtering

**Change**: `ContentMode` enum → `bool | str` type system

**Impact**: Filter values are now flexible (bool, template, or inline prompt).

**Migration**:
```json
// OLD
{
  "filter": {
    "tool_content": "summary"
  }
}

// NEW
{
  "filter": {
    "tool_content": "default-tool-content.md"
  }
}
```

**Enum Mapping**:
- `ContentMode.FULL` → `true`
- `ContentMode.SUMMARY` → `"default-tool-content.md"`
- `ContentMode.OMIT` → `false`

### 5. Removed max_summary_chars

**Change**: `max_summary_chars` parameter removed

**Impact**: Templates self-describe length (e.g., "Summarize in 1 paragraph").

**Migration**: No direct replacement. Edit templates to control length.

## New Features

### 1. Rolling Period Filter

**Feature**: `keep_length_days` parameter

**Purpose**: Prevent bulk indexing of old sessions on first run.

**Default**: `7` (last 7 days)

**Example**:
```json
{
  "session_tracking": {
    "keep_length_days": 30  // Last 30 days
  }
}
```

### 2. Manual Sync Command

**Feature**: `graphiti-mcp session-tracking sync`

**Purpose**: Manually sync historical sessions beyond rolling window.

**Example**:
```bash
# Preview last 30 days
graphiti-mcp session-tracking sync --days 30 --dry-run

# Actually sync
graphiti-mcp session-tracking sync --days 30 --no-dry-run
```

### 3. Pluggable Templates

**Feature**: Custom template files in `.graphiti/auto-tracking/templates/`

**Purpose**: Customize summarization behavior without code changes.

**Example**:
```bash
# Create custom template
mkdir -p ~/.graphiti/auto-tracking/templates
cat > ~/.graphiti/auto-tracking/templates/my-custom.md << 'EOF'
Summarize in 2-3 sentences focusing on key decisions.

{content}
EOF

# Use in config
{
  "filter": {
    "user_messages": "my-custom.md"
  }
}
```

## FAQ

### Q: Will my existing sessions still work?

**A**: Yes, existing sessions remain in the graph. Only new sessions use v1.1.0 configuration.

### Q: Do I need to re-index old sessions?

**A**: No, unless you want to. Use `graphiti-mcp session-tracking sync` to manually index historical sessions.

### Q: What if I don't update my config?

**A**: Session tracking will be disabled by default. You must explicitly enable it.

### Q: How do I restore v1.0.0 behavior?

**A**:
```json
{
  "session_tracking": {
    "enabled": true,
    "auto_summarize": true,
    "inactivity_timeout": 300,
    "keep_length_days": null
  }
}
```

### Q: What's the cost difference?

**A**:
- v1.0.0 default: ~$0.17/session (LLM enabled)
- v1.1.0 default: $0/session (LLM disabled)
- v1.1.0 opt-in: ~$0.17/session (same as v1.0.0)

## Version Compatibility

| Version | Config Format | Auto-Migration | Notes |
|---------|---------------|----------------|-------|
| v1.0.0  | Enum-based    | N/A            | Original |
| v1.1.0  | bool \| str   | Yes (recommended) | Opt-in model |

Auto-migration recommended: Update config to new format for clarity and to avoid deprecation warnings.
```

### Testing Requirements

1. **Documentation Accuracy**:
   - All examples are valid JSON
   - All parameter descriptions match implementation
   - All code examples run successfully

2. **Quick Start Guide**:
   - Fresh install follows quick start
   - Configuration examples work
   - Troubleshooting steps resolve issues

3. **Migration Guide**:
   - Migration examples accurate
   - Breaking changes documented
   - FAQ answers common questions

## Dependencies

- Stories 9-14 (all implementation complete) - REQUIRED

## Related Documents

- `.claude/handoff/session-tracking-complete-overhaul-2025-11-18.md` (Source material)
- `CONFIGURATION.md` (existing)
- `docs/SESSION_TRACKING_USER_GUIDE.md` (existing)

## Cross-Cutting Requirements

See parent sprint `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`:
- Documentation: Complete user and developer docs
- Examples: All examples tested and working
- Migration guide: Clear upgrade path
