# Session Tracking Configuration Overhaul - Summary

**Date**: 2025-11-18  
**Status**: Design Complete - Ready for Implementation  
**Priority**: HIGH (Security + Bug Fixes)

---

## Changes Overview

### 🔒 Security Improvements
1. **Opt-in model**: `enabled: false` by default (was `true`)
2. **No LLM costs**: `auto_summarize: false` by default (was `true`)
3. **Rolling window**: `keep_length_days: 7` prevents bulk indexing old sessions

### 🐛 Critical Bug Fixes
1. **Missing periodic checker**: `check_interval` configured but never used - sessions never close due to inactivity
2. **Implement async scheduler**: Call `check_inactive_sessions()` every `check_interval` seconds

### ⚡ Performance Improvements
1. **Realtime defaults**: `inactivity_timeout: 45s` (was 300s), `check_interval: 15s` (was 60s)
2. **Token reduction**: `tool_content: "default_tool_content.md"` (~35% reduction, paragraph summaries)

### 🎨 Configuration Simplification
1. **Removed enums**: `bool | str` instead of `"full" | "summary" | "omit"`
2. **Removed redundancy**: No `max_summary_chars` (templates control length)
3. **Direct templates**: `"default_tool_content.md"` instead of `"summary"` keyword
4. **Unified structure**: Same file hierarchy for global and project

---

## Final Configuration Schema

```json
{
  "session_tracking": {
    "enabled": false,
    "watch_path": null,
    "inactivity_timeout": 45,
    "check_interval": 15,
    "auto_summarize": false,
    "store_in_graph": true,
    "keep_length_days": 7,
    
    "filter": {
      "tool_calls": true,
      "tool_content": "default_tool_content.md",
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

**Total parameters**: 10 (down from 11, removed `max_summary_chars`)

---

## Filter Value Types

Each filter field accepts:
- `true` → Full content (no filtering)
- `false` → Omit entirely
- `"template.md"` → Template file (resolved via hierarchy)
- `"inline prompt..."` → Direct prompt string

---

## File Structure

### Global: `~/.graphiti/`
```
~/.graphiti/
├── auto_tracking/
│   └── templates/
│       ├── default_tool_content.md
│       ├── default_user_messages.md
│       └── default_agent_messages.md
└── graphiti.config.json
```

### Project: `<project_root>/.graphiti/`
```
<project_root>/.graphiti/
├── auto_tracking/
│   └── templates/
│       └── *.md (project overrides)
└── (optional config overrides)
```

### Resolution Order
1. **Project**: `<project_root>/.graphiti/auto_tracking/templates/{name}`
2. **Global**: `~/.graphiti/auto_tracking/templates/{name}`
3. **Built-in**: Packaged with Graphiti (hardcoded sources)
4. **Inline**: Treat string as prompt

---

## New Features

### Manual Sync Command
**Purpose**: Index historical sessions when tracking was disabled

**MCP Tool**:
```python
session_tracking_sync_history(
    project_path=None,       # Null = all projects
    keep_length_days=7,      # Rolling window
    dry_run=True,            # Preview first
    max_sessions=100         # Safety limit
)
```

**CLI**:
```bash
graphiti-mcp session-tracking sync --dry-run
graphiti-mcp session-tracking sync --days 30
```

**Returns**:
```json
{
  "sessions_found": 168,
  "sessions_filtered": 123,
  "sessions_to_sync": 45,
  "estimated_cost": 2.25
}
```

---

## Breaking Changes

### Configuration Changes
| Old | New | Migration |
|-----|-----|-----------|
| `"tool_content": "summary"` | `"tool_content": "default_tool_content.md"` | Auto-migrate |
| `"tool_content": "full"` | `"tool_content": true` | Auto-migrate |
| `"tool_content": "omit"` | `"tool_content": false` | Auto-migrate |
| `max_summary_chars: 500` | (removed) | Templates control length |

### Behavior Changes
| Before | After | Impact |
|--------|-------|--------|
| `enabled: true` | `enabled: false` | Opt-in security model |
| `auto_summarize: true` | `auto_summarize: false` | No LLM costs by default |
| `check_interval: 60` (unused) | `check_interval: 15` (working) | Bug fix - sessions actually close |
| No rolling window | `keep_length_days: 7` | Prevents bulk indexing |

---

## Implementation Priority

### Week 1 (Critical Path)
1. Update `FilterConfig` schema (`bool | str` types)
2. Remove `max_summary_chars` parameter
3. Implement periodic checker task (bug fix)
4. Change defaults in `unified_config.py`
5. Create default template files
6. Implement template resolution hierarchy
7. Update auto-generated config

### Week 2 (Features)
8. Implement `keep_length_days` filtering
9. Implement `session_tracking_sync_history` MCP tool
10. Add CLI command `graphiti-mcp session-tracking sync`
11. Update configuration documentation

### Week 3 (Polish)
12. Write migration logic for old configs
13. Write comprehensive tests
14. Update user guides and examples

---

## Design Documents

All detailed designs in `.claude/implementation/`:
1. `session-tracking-security-concerns-2025-11-18.md` (handoff, security analysis)
2. `session-tracking-safe-defaults-design.md` (bug fix, defaults)
3. `complete-session-tracking-config-template.md` (all parameters documented)
4. `pluggable-summary-prompts-design.md` (template system v1)
5. `simplified-config-schema-v2.md` (simplified bool|str design)
6. `final-config-schema-and-structure.md` (final unified structure)

---

## Testing Requirements

### Critical Tests
- [ ] Periodic checker runs every `check_interval` seconds
- [ ] Sessions close after `inactivity_timeout` + check latency
- [ ] Template resolution hierarchy (project → global → built-in)
- [ ] Filter value resolution (`bool` vs `str`)
- [ ] Auto-generation creates templates on first run

### Integration Tests
- [ ] Manual sync command with `keep_length_days` filter
- [ ] Project-specific templates override global
- [ ] Inline prompts work without file lookup
- [ ] Migration from old enum-based configs

### Security Tests
- [ ] Default config has tracking disabled
- [ ] No auto-summarization without explicit enablement
- [ ] Rolling window prevents bulk indexing

---

## Estimated Impact

### Token Reduction
- **Current default**: ~35% (tool results summarized via `"summary"`)
- **New default**: ~35% (tool results summarized via `"default_tool_content.md"`)
- **Max reduction**: ~85% (all omitted except user messages)

### Cost Impact
- **Current**: Auto-enabled, auto-summarize = $10-50/month potential surprise
- **New**: Opt-in, no auto-summarize = $0/month until user enables

### Performance
- **Current**: Sessions never close (bug), 5-minute timeout (too slow)
- **New**: Sessions close in ~45-60 seconds (realtime-like)

---

## User Experience

### First-Time Setup
1. User installs Graphiti MCP
2. MCP server starts → auto-generates `~/.graphiti/graphiti.config.json`
3. Auto-generates default templates in `~/.graphiti/auto_tracking/templates/`
4. User sees file with safe defaults, clear comments
5. User explicitly sets `enabled: true` to opt-in

### Customization Workflow
1. User edits global template: `~/.graphiti/auto_tracking/templates/default_tool_content.md`
2. Changes apply to all projects immediately
3. For project-specific needs: Copy to `<project>/.graphiti/auto_tracking/templates/`
4. Project override takes precedence

### Historical Sync
1. User had tracking disabled for 6 months
2. Enables tracking: `"enabled": true`
3. Previews sync: `graphiti-mcp session-tracking sync --dry-run`
4. Reviews cost estimate: "$4.35 for 87 sessions"
5. Decides and syncs: `--days 30` or `--days 7`
6. File watcher handles new sessions automatically

---

## Open Questions (Resolved)

1. ✅ Should `max_summary_chars` exist? **NO** - Templates control length
2. ✅ Enum vs bool|str? **bool|str** - Simpler, more intuitive
3. ✅ Separate prompts config? **NO** - Direct template references
4. ✅ Template locations? **Unified** - Same structure global/project
5. ✅ Manual sync needed? **YES** - Historical indexing when tracking was disabled

---

**Status**: All design complete, ready for implementation
**Next Step**: Begin implementation (Week 1 critical path)
