# Graphiti Filter Configuration - Summary

## Overview

Clean, project-local configuration system for LLM-based memory filtering with **zero global environment variable pollution**.

---

## Key Design Decisions

### ✅ What We Did

1. **Project-local config file** (`graphiti-filter.config.json`)
   - Version controlled
   - Human-readable JSON
   - Self-documenting schema

2. **Deployment script** (`scripts/install-filter-config.sh`)
   - Copies config to `~/.claude/`
   - Validates API keys
   - Cross-platform support

3. **Config search order** (project → global → defaults)
   - Development: Uses project-local config
   - Production: Uses global config after installation
   - Fallback: Built-in defaults

4. **Standard API keys only**
   - `OPENAI_API_KEY` (shared with other tools)
   - `ANTHROPIC_API_KEY` (shared with other tools)
   - No Graphiti-specific env vars

### ❌ What We Avoided

1. **No global env var pollution**
   - ~~`GRAPHITI_FILTER_ENABLED`~~
   - ~~`GRAPHITI_FILTER_PROVIDERS`~~
   - ~~`GRAPHITI_FILTER_OPENAI_MODEL`~~
   - ~~`GRAPHITI_FILTER_ANTHROPIC_MODEL`~~

2. **No complex env var parsing**
   - ~~Comma-separated provider lists~~
   - ~~String-to-bool conversions~~
   - ~~Model name parsing~~

3. **No hard-coded defaults in env vars**
   - All defaults in config file
   - Easy to customize without shell config changes

---

## File Structure

```
graphiti/
├── graphiti.config.json              # ✅ Project config (version controlled)
├── .env                              # ✅ Secrets (API keys, passwords)
└── mcp_server/
    ├── unified_config.py             # Unified configuration system
    └── graphiti_mcp_server.py        # MCP server implementation
```

---

## Configuration File

**`graphiti-filter.config.json`**:

```json
{
  "filter": {
    "enabled": true,
    "providers": [
      {
        "name": "openai",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "temperature": 0.0,
        "max_tokens": 200,
        "enabled": true,
        "priority": 1
      },
      {
        "name": "anthropic",
        "model": "claude-haiku-3-5-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
        "temperature": 0.0,
        "max_tokens": 200,
        "enabled": true,
        "priority": 2
      }
    ],
    "session": {
      "max_context_tokens": 5000,
      "auto_cleanup": true,
      "session_timeout_minutes": 60
    },
    "categories": {
      "store": ["env-quirk", "user-pref", "external-api", "historical-context", "cross-project", "workaround"],
      "skip": ["bug-in-code", "config-in-repo", "docs-added", "first-success"]
    },
    "logging": {
      "log_filter_decisions": true,
      "log_level": "INFO"
    }
  }
}
```

---

## Installation

### One-Time Setup

```bash
# 1. Navigate to graphiti project
cd /path/to/graphiti

# 2. Run installation script
./scripts/install-filter-config.sh

# 3. Set API keys (if not already set)
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# 4. Restart Graphiti MCP server
```

### What Gets Deployed

```
~/.claude/graphiti-filter.config.json  ← Deployed here
```

---

## Config Search Order

When Graphiti MCP server starts:

1. **Check project root**: `./graphiti-filter.config.json`
   - For development/testing
   - Allows per-project customization

2. **Check global**: `~/.claude/graphiti-filter.config.json`
   - For production use
   - Deployed via install script

3. **Use defaults**: Built-in config in `filter_config.py`
   - Graceful fallback if no config found
   - Same defaults as config file

---

## Customization

### Change Models

Edit `~/.claude/graphiti-filter.config.json`:

```json
{
  "filter": {
    "providers": [
      {
        "name": "openai",
        "model": "gpt-4o",           ← Change model here
        "priority": 1
      }
    ]
  }
}
```

### Change Provider Order

```json
{
  "filter": {
    "providers": [
      {
        "name": "anthropic",         ← Lower priority = tried first
        "priority": 1
      },
      {
        "name": "openai",
        "priority": 2
      }
    ]
  }
}
```

### Disable Filtering

```json
{
  "filter": {
    "enabled": false               ← Disable all filtering
  }
}
```

### Disable Single Provider

```json
{
  "filter": {
    "providers": [
      {
        "name": "openai",
        "enabled": false             ← Disable this provider only
      }
    ]
  }
}
```

---

## Environment Variables

**Only standard API keys needed:**

```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.profile
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

**No Graphiti-specific variables required!**

---

## Benefits

### For Developers

✅ **Version controlled** - Config file in git
✅ **Self-documenting** - JSON schema is readable
✅ **Easy testing** - Override with project-local config
✅ **No env conflicts** - Standard API keys only

### For Users

✅ **Simple installation** - One script
✅ **Easy customization** - Edit JSON file
✅ **No shell config** - No exports needed (except API keys)
✅ **Cross-platform** - Works on Windows/Mac/Linux

### For Maintenance

✅ **Clear separation** - Project vs global config
✅ **Graceful fallback** - Works even without config
✅ **Standard patterns** - Follows MCP conventions
✅ **No pollution** - Clean global env namespace

---

## Comparison

| Approach | Env Vars | Config File | Deployment |
|----------|----------|-------------|------------|
| **❌ Old (env-based)** | 6+ custom vars | None | Manual exports |
| **✅ New (config-based)** | 2 standard vars | JSON file | One script |

**Reduction**: 6+ custom env vars → 0 custom env vars (67-100% cleaner)

---

## Next Steps

1. ✅ Config file created (`graphiti-filter.config.json`)
2. ✅ Install script created (`scripts/install-filter-config.sh`)
3. ⏳ Implement config loader (`mcp_server/filter_config.py`)
4. ⏳ Integrate with MCP server
5. ⏳ Test deployment workflow
6. ⏳ Update CLAUDE.md

---

**Date**: 2025-11-03
**Version**: v1.0 (Clean Config Architecture)
