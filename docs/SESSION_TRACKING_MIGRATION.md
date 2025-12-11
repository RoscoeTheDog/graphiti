# Session Tracking Migration Guide

## Overview

This guide covers migrating session tracking configuration across major versions:
- **v1.0.0 → v1.1.0**: Opt-in security model, flexible filtering, rolling retention
- **v1.1.0 → v2.0.0**: Global knowledge graph with cross-project learning (NEW)

The v2.0.0 release introduces a fundamental architectural change: migrating from project-scoped isolation to global indexing with namespace tagging. This enables cross-project knowledge sharing while preserving provenance tracking.

**v1.1.0 Migration Timeline**: ~15-30 minutes
**v2.0.0 Migration Timeline**: ~5-15 minutes (fresh start recommended)
**Breaking Changes**: Yes
**Backward Compatibility**: v1.x data preserved, not searched by default in v2.0

---

## What's Changed in v1.1.0

### 1. Opt-In Security Model (Breaking Change)

**v1.0.0 Behavior:**
- Session tracking **enabled by default**
- Users had to opt-out if privacy was a concern
- Risk of unintentional data collection

**v1.1.0 Behavior:**
- Session tracking **disabled by default**
- Users must explicitly opt-in
- Enhanced privacy and security posture

**Migration Required:** Yes - must explicitly enable if upgrading

---

### 2. Filter Type System (Breaking Change)

**v1.0.0 System:**
```json
{
  "filter": {
    "user_messages": "full",      // Enum: "full" | "summary" | "omit"
    "agent_messages": "full",
    "tool_calls": "summary",
    "tool_content": "omit"
  }
}
```

**v1.1.0 System:**
```json
{
  "filter": {
    "user_messages": true,                    // bool | string (template path)
    "agent_messages": true,
    "tool_calls": "templates/tool_summary",
    "tool_content": false
  }
}
```

**Key Changes:**
- Enum strings (`"full"`, `"summary"`, `"omit"`) replaced with `bool | str`
- `true` = include full content (replaces `"full"`)
- `false` = exclude content (replaces `"omit"`)
- Template paths for custom filtering (replaces `"summary"`)

**Migration Required:** Yes - update filter configuration syntax

---

### 3. Template-Based Filtering (New Feature)

**v1.0.0:** Fixed summarization logic in code

**v1.1.0:** Configurable Markdown templates

```json
{
  "filter": {
    "tool_calls": "default-tool-content.md",
    "tool_content": "templates/custom_filter.md"
  }
}
```

**Benefits:**
- Custom summarization rules without code changes
- Project-specific filtering strategies
- A/B testing different filter approaches

**Migration Required:** No - backward compatible (can continue using `true`/`false`)

---

### 4. Rolling Retention Period (New Feature)

**v1.0.0:** Sessions indexed indefinitely (all history)

**v1.1.0:** Configurable retention with rolling window

```json
{
  "session_tracking": {
    "keep_length_days": 90  // Index last 90 days only
  }
}
```

**Benefits:**
- Reduced Neo4j storage costs
- Faster query performance
- GDPR/privacy compliance (automatic data cleanup)

**Cost Impact:**
- 30 days retention: ~$5/month (50 sessions)
- 90 days retention: ~$15/month (150 sessions)
- Unlimited retention: ~$50+/month (500+ sessions)

**Migration Required:** No - defaults to unlimited (v1.0.0 behavior)

---

### 5. Manual Sync Command (New Feature)

**v1.0.0:** No way to manually trigger indexing

**v1.1.0:** CLI command for on-demand sync

```bash
# Sync last 7 days (default)
graphiti-mcp-session-tracking sync

# Sync specific date range
graphiti-mcp-session-tracking sync --days 30

# Sync all unindexed sessions (expensive!)
graphiti-mcp-session-tracking sync --days 0
```

**Use Cases:**
- Migrate pre-existing sessions from v1.0.0
- Re-index after configuration changes
- Recover from indexing failures

**Cost Warning:** `--days 0` can be very expensive ($10-$50+ for large backlogs)

**Migration Required:** No - optional feature

---

## Migration Paths

### Path 1: Minimal Migration (Keep v1.0.0 Behavior)

**Goal:** Enable session tracking with defaults similar to v1.0.0

**Steps:**
1. Enable session tracking:
   ```bash
   graphiti-mcp-session-tracking enable
   ```

2. Update `graphiti.config.json`:
   ```json
   {
     "session_tracking": {
       "enabled": true,
       "filter": {
         "user_messages": true,
         "agent_messages": true,
         "tool_calls": true,
         "tool_content": false
       }
     }
   }
   ```

3. (Optional) Sync old sessions:
   ```bash
   # Be cautious with --days value (costs $$)
   graphiti-mcp-session-tracking sync --days 7
   ```

**Before:**
```json
{
  "session_tracking": {
    "enabled": true,  // Auto-enabled in v1.0.0
    "filter": {
      "user_messages": "full",
      "agent_messages": "full",
      "tool_calls": "summary",
      "tool_content": "omit"
    }
  }
}
```

**After:**
```json
{
  "session_tracking": {
    "enabled": true,  // Must explicitly enable in v1.1.0
    "filter": {
      "user_messages": true,      // "full" → true
      "agent_messages": true,
      "tool_calls": true,          // "summary" → true (or template path)
      "tool_content": false        // "omit" → false
    }
  }
}
```

**Estimated Time:** 5 minutes  
**Cost Impact:** Same as v1.0.0 (~$0.17/session)

---

### Path 2: Enhanced Security Migration (Recommended)

**Goal:** Leverage new security and cost optimization features

**Steps:**
1. Enable session tracking:
   ```bash
   graphiti-mcp-session-tracking enable
   ```

2. Update `graphiti.config.json` with optimizations:
   ```json
   {
     "session_tracking": {
       "enabled": true,
       "keep_length_days": 90,  // 3-month rolling window
       "filter": {
         "user_messages": true,
         "agent_messages": true,
         "tool_calls": "default-tool-content.md",
         "tool_content": false
       }
     }
   }
   ```

3. Create custom template (optional):
   ```bash
   mkdir -p templates
   cat > default-tool-content.md << 'EOF'
   Summarize this tool result: {content}
   EOF
   ```

4. Sync recent sessions only:
   ```bash
   graphiti-mcp-session-tracking sync --days 30
   ```

**Before:**
```json
{
  "session_tracking": {
    "enabled": true,
    "filter": {
      "user_messages": "full",
      "agent_messages": "full",
      "tool_calls": "summary",
      "tool_content": "omit"
    }
  }
}
```

**After:**
```json
{
  "session_tracking": {
    "enabled": true,
    "keep_length_days": 90,
    "filter": {
      "user_messages": true,
      "agent_messages": true,
      "tool_calls": "default-tool-content.md",
      "tool_content": false
    }
  }
}
```

**Estimated Time:** 15 minutes  
**Cost Impact:** -40% reduction (rolling retention + templates)

---

### Path 3: Privacy-First Migration

**Goal:** Maximum privacy with minimal data collection

**Steps:**
1. Keep session tracking disabled (default):
   ```bash
   # Do nothing - tracking is disabled by default
   ```

2. Enable via configuration when needed:
   ```json
   // graphiti.config.json
   {
     "session_tracking": {
       "enabled": true
     }
   }
   ```

3. Configure minimal filtering:
   ```json
   {
     "session_tracking": {
       "enabled": false,  // Disabled by default
       "keep_length_days": 30,
       "filter": {
         "user_messages": false,              // Exclude user messages
         "agent_messages": "templates/minimal.md",
         "tool_calls": "default-tool-content.md",
         "tool_content": false
       }
     }
   }
   ```

4. Custom minimal template:
   ```bash
   cat > templates/minimal.md << 'EOF'
   Summary: Task completed successfully
   EOF
   ```

**Before:**
```json
{
  "session_tracking": {
    "enabled": true,
    "filter": {
      "user_messages": "full",
      "agent_messages": "full",
      "tool_calls": "summary",
      "tool_content": "omit"
    }
  }
}
```

**After:**
```json
{
  "session_tracking": {
    "enabled": false,  // Opt-in only when needed
    "keep_length_days": 30,
    "filter": {
      "user_messages": false,              // Maximum privacy
      "agent_messages": "templates/minimal.md",
      "tool_calls": "default-tool-content.md",
      "tool_content": false
    }
  }
}
```

**Estimated Time:** 20 minutes  
**Cost Impact:** -70% reduction (disabled by default + minimal filtering)

---

## Configuration Reference

### Filter Value Types

| Value | Type | Behavior | Use Case |
|-------|------|----------|----------|
| `true` | bool | Include full content | High-fidelity indexing |
| `false` | bool | Exclude entirely | Privacy, cost reduction |
| `"template.md"` | str | Custom Markdown template with `{content}` placeholder | Flexible summarization |

### Retention Configuration

| Days | Storage | Query Speed | Monthly Cost (50 sessions/month) |
|------|---------|-------------|----------------------------------|
| 30 | ~100 MB | Very fast | ~$5 |
| 90 | ~300 MB | Fast | ~$15 |
| 180 | ~600 MB | Medium | ~$30 |
| Unlimited | 1+ GB | Slow | ~$50+ |

---

## Troubleshooting

### Issue 1: "Session tracking not working after upgrade"

**Cause:** v1.1.0 defaults to disabled (v1.0.0 was enabled by default)

**Solution:**
```bash
graphiti-mcp-session-tracking enable
graphiti-mcp-session-tracking status  # Verify enabled
```

---

### Issue 2: "Invalid filter configuration error"

**Cause:** v1.0.0 enum strings (`"full"`, `"summary"`, `"omit"`) not supported in v1.1.0

**Solution:** Update to new syntax:
```json
// Old (v1.0.0)
"user_messages": "full"

// New (v1.1.0)
"user_messages": true
```

**Mapping:**
- `"full"` → `true`
- `"omit"` → `false`
- `"summary"` → `true` or `"templates/custom.md"`

---

### Issue 3: "High costs after migration"

**Cause:** Syncing large backlog with `--days 0`

**Solution:**
1. Check what was synced:
   ```bash
   # View recent episodes
   graphiti-mcp episodes list --limit 50
   ```

2. Configure retention to prevent future costs:
   ```json
   {
     "session_tracking": {
       "keep_length_days": 90
     }
   }
   ```

3. Clean up old episodes:
   ```bash
   # Delete episodes older than 90 days
   graphiti-mcp episodes cleanup --older-than 90
   ```

---

### Issue 4: "Template not found error"

**Cause:** Template path specified but file doesn't exist

**Solution:**
1. Create template directory:
   ```bash
   mkdir -p templates
   ```

2. Use built-in templates or create custom:
   ```bash
   # Use boolean instead of template
   "tool_calls": true

   # Or create template
   cat > default-tool-content.md << 'EOF'
   Summarize this tool result: {content}
   EOF
   ```

---

## Rollback Procedure

If migration causes issues, you can rollback to v1.0.0 behavior:

**Step 1: Downgrade package**
```bash
pip install graphiti-mcp==1.0.0
```

**Step 2: Restore v1.0.0 config**
```json
{
  "session_tracking": {
    "enabled": true,
    "filter": {
      "user_messages": "full",
      "agent_messages": "full",
      "tool_calls": "summary",
      "tool_content": "omit"
    }
  }
}
```

**Step 3: Restart MCP server**
```bash
# Restart to apply downgrade
pkill -f graphiti-mcp
# MCP server will auto-restart via Claude Code
```

---

## Testing Your Migration

After migrating, verify everything works:

**Test 1: Verify tracking is enabled**
```bash
graphiti-mcp-session-tracking status
# Expected: "enabled": true
```

**Test 2: Create test session**
```bash
# Start Claude Code session and perform simple task
# Wait 5 minutes (inactivity timeout)
```

**Test 3: Verify session was indexed**
```bash
graphiti-mcp episodes list --limit 5
# Expected: See recent test session
```

**Test 4: Query indexed content**
```python
# Use search_memory_nodes MCP tool
{
  "tool": "search_memory_nodes",
  "arguments": {
    "query": "test session task",
    "max_nodes": 5
  }
}
# Expected: Find nodes related to test session
```

---

## Support

**Migration Issues:**
- GitHub: https://github.com/getzep/graphiti/issues
- Label: `migration`, `session-tracking`

**Documentation:**
- User Guide: `docs/SESSION_TRACKING_USER_GUIDE.md`
- Configuration Reference: `CONFIGURATION.md`

**Community:**
- Discord: https://discord.com/invite/W8Kw6bsgXQ
- Channel: #session-tracking

---

## v1.1.0 → v2.0.0 Migration (Global Scope)

**New in v2.0.0** - Fundamental architectural change from project-scoped isolation to global indexing with namespace tagging.

### What Changed

| Aspect | v1.1.0 (Project Scope) | v2.0.0 (Global Scope) |
|--------|------------------------|----------------------|
| **Group ID** | Per-project (`{hostname}__{project_hash}`) | Single global (`{hostname}__global`) |
| **Cross-Project Learning** | None (isolated) | Enabled by default |
| **Episode Metadata** | Minimal | YAML frontmatter with namespace/path |
| **Configuration** | Project or global | Global only (recommended) |

### Migration Path: Fresh Start (Recommended)

Since v1.x was never publicly released, we recommend a clean start with v2.0:

**Step 1: Update configuration**
```json
{
  "session_tracking": {
    "enabled": true,
    "group_id": null,
    "cross_project_search": true,
    "trusted_namespaces": null,
    "include_project_path": true
  }
}
```

**Step 2: Start using v2.0**
- New sessions will be indexed with namespace metadata
- Old v1.x data in project-specific group_ids remains but won't be searched

**Before (v1.1.0)**:
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": null,
    "keep_length_days": 90,
    "filter": {
      "user_messages": true,
      "agent_messages": true,
      "tool_calls": true,
      "tool_content": false
    }
  }
}
```

**After (v2.0.0)**:
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": null,
    "keep_length_days": 90,
    "group_id": null,
    "cross_project_search": true,
    "trusted_namespaces": null,
    "include_project_path": true,
    "filter": {
      "user_messages": true,
      "agent_messages": true,
      "tool_calls": true,
      "tool_content": false
    }
  }
}
```

**Estimated Time:** 5 minutes
**Cost Impact:** None (new sessions only)

### Migration Path: Keep Old Data

If you have valuable v1.x data you want to preserve access to:

**Option A: Keep Old Data (Separate)**
- Old data remains in project-specific group_ids
- New data goes to global group_id
- Query both group_ids when needed:
  ```json
  {
    "tool": "search_memory_nodes",
    "arguments": {
      "query": "authentication",
      "group_ids": ["myhost__global", "myhost__a1b2c3d4"]
    }
  }
  ```

**Option B: Re-index Sessions**
- Use CLI to re-index existing sessions with new global group_id
- Sessions get namespace metadata added automatically
- Old project-specific data can be cleared

```bash
# Re-index last 90 days
graphiti-mcp session-tracking sync --days 90 --no-dry-run

# Clear old project-specific data (optional, irreversible)
# graphiti-mcp episodes cleanup --group-id "myhost__a1b2c3d4"
```

**Option C: Manual Migration Script**
For advanced users who need fine-grained control:

```python
# Example: Migrate episodes to global group_id with namespace metadata
from graphiti_core import Graphiti

async def migrate_episode(graphiti, old_episode, new_group_id, namespace):
    """Re-index episode with namespace metadata."""
    metadata_header = f"""---
graphiti_session_metadata:
  version: "2.0"
  project_namespace: "{namespace}"
  migrated_from: "{old_episode.group_id}"
---

"""
    await graphiti.add_episode(
        name=old_episode.name,
        episode_body=metadata_header + old_episode.content,
        source_description=f"[{namespace[:8]}] {old_episode.source_description}",
        group_id=new_group_id,
    )
```

### New Configuration Fields

| Field | Default | Description |
|-------|---------|-------------|
| `group_id` | `null` | Global group ID (default: `{hostname}__global`) |
| `cross_project_search` | `true` | Search across all project namespaces |
| `trusted_namespaces` | `null` | Restrict search to specific namespaces |
| `include_project_path` | `true` | Include paths in episode metadata |

### Breaking Changes

1. **Group ID Format**: Changed from `{hostname}__{project_hash}` to `{hostname}__global`
2. **Episode Content**: Now includes YAML frontmatter with namespace metadata
3. **Search Behavior**: Cross-project search enabled by default

### Backward Compatibility Notes

- Existing v1.x data in old group_ids is preserved but not searched by default
- New configuration fields have sensible defaults (no config changes required)
- v1.x filter syntax (`true`/`false`) continues to work
- v1.0 was never publicly released, simplifying migration

---

**Version:** 2.0 (2025-12-10)
**Covers:** v1.0.0 → v1.1.0 migration, v1.1.0 → v2.0.0 migration
**Next Review:** 2026-01-10
