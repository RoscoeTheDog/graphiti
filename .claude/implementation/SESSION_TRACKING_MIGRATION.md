# Session Tracking Migration Guide

## Overview

This guide helps you enable and configure the new session tracking feature in Graphiti MCP server v1.0.0.

**Timeline**: 5-10 minutes

---

## What is Session Tracking?

Session tracking automatically monitors your Claude Code sessions, filters conversations for relevance, and indexes them into the Graphiti knowledge graph. This enables:

- **Cross-session continuity**: Claude remembers context from previous sessions
- **Smart filtering**: Reduces token usage by ~35-70% while preserving key information
- **Automatic indexing**: Sessions are indexed to Graphiti for semantic search
- **Runtime control**: Enable/disable per session via MCP tools

---

## Prerequisites

- Graphiti MCP server v1.0.0 or later
- Claude Code (for session file monitoring)
- Neo4j database (already required for Graphiti)
- OpenAI API key (already required for Graphiti)

---

## Quick Start

### Step 1: Update Configuration

Session tracking is **enabled by default** in v1.0.0. To customize:

```bash
# Edit your graphiti.config.json
```

Add the `session_tracking` section (see [CONFIGURATION.md](../CONFIGURATION.md#session-tracking-configuration) for details):

```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": "~/.claude/sessions",
    "check_interval": 2,
    "inactivity_timeout": 300,
    "filter": {
      "tool_calls": "summary",
      "tool_content": "summary",
      "user_messages": "full",
      "agent_messages": "full"
    }
  }
}
```

### Step 2: Configure CLI (Optional)

You can manage session tracking via CLI:

```bash
# Check current status
graphiti-mcp-session-tracking status

# Disable session tracking
graphiti-mcp-session-tracking disable

# Re-enable session tracking
graphiti-mcp-session-tracking enable
```

### Step 3: Use MCP Tools (Runtime Control)

Control session tracking per session via MCP tools:

```
# Enable tracking for current session
session_tracking_start()

# Check status
session_tracking_status()

# Disable tracking for current session
session_tracking_stop()
```

---

## Configuration Options

### Default Behavior (Recommended)

The default configuration balances token efficiency and memory accuracy:

```json
{
  "session_tracking": {
    "enabled": true,
    "filter": {
      "tool_calls": "summary",      // One-line summaries
      "tool_content": "summary",    // One-line summaries
      "user_messages": "full",      // Full content
      "agent_messages": "full"      // Full content
    }
  }
}
```

**Token reduction**: ~35% (reasonable balance)
**Cost**: ~$0.03-$0.05 per session

### Maximum Filtering (Cost Optimization)

Aggressive filtering for minimal LLM costs:

```json
{
  "session_tracking": {
    "enabled": true,
    "filter": {
      "tool_calls": "omit",         // Remove completely
      "tool_content": "omit",       // Remove completely
      "user_messages": "summary",   // One-line summaries
      "agent_messages": "summary"   // One-line summaries
    }
  }
}
```

**Token reduction**: ~70% (aggressive)
**Cost**: ~$0.01-$0.02 per session
**Trade-off**: Less detailed memory

### Conservative Filtering (High Accuracy)

Minimal filtering for maximum context retention:

```json
{
  "session_tracking": {
    "enabled": true,
    "filter": {
      "tool_calls": "full",         // Full content
      "tool_content": "full",       // Full content
      "user_messages": "full",      // Full content
      "agent_messages": "full"      // Full content
    }
  }
}
```

**Token reduction**: 0% (no filtering)
**Cost**: ~$0.15-$0.50 per session
**Trade-off**: Higher LLM costs

---

## Disabling Session Tracking

If you prefer to opt-out:

### Option 1: Global Disable (via Config)

```json
{
  "session_tracking": {
    "enabled": false
  }
}
```

### Option 2: Global Disable (via CLI)

```bash
graphiti-mcp-session-tracking disable
```

### Option 3: Per-Session Disable (via MCP Tool)

```
session_tracking_stop()
```

---

## Migration from v0.3.x

If you're upgrading from Graphiti v0.3.x:

### What Changed

- **Session tracking is now built-in** (previously required separate installation)
- **Enabled by default** (opt-out model)
- **Unified configuration** (session tracking settings in `graphiti.config.json`)

### Migration Steps

1. **Update Graphiti**:
   ```bash
   cd /path/to/graphiti
   git pull
   uv sync
   ```

2. **Review configuration**:
   ```bash
   # Session tracking is enabled by default
   # Customize if needed (see Step 1 above)
   ```

3. **Test MCP server**:
   ```bash
   uv run graphiti_mcp_server.py
   
   # Expected output:
   # INFO - Session tracking enabled
   # INFO - Watching: ~/.claude/sessions
   # INFO - MCP server started
   ```

4. **Disable if not wanted**:
   ```bash
   graphiti-mcp-session-tracking disable
   ```

---

## Troubleshooting

### Session Tracking Not Working

**Symptom**: Sessions not being indexed to Graphiti

**Causes & Solutions**:

1. **Session tracking disabled**
   ```bash
   # Check status
   graphiti-mcp-session-tracking status
   
   # Enable if needed
   graphiti-mcp-session-tracking enable
   ```

2. **Wrong watch path**
   ```bash
   # Verify path in config
   cat graphiti.config.json | grep -A5 "session_tracking"
   
   # Check default location
   ls -la ~/.claude/sessions
   ```

3. **MCP server not running**
   ```bash
   # Restart MCP server
   uv run graphiti_mcp_server.py
   ```

### High LLM Costs

**Symptom**: Unexpectedly high OpenAI bills

**Solution**: Adjust filtering to be more aggressive

```json
{
  "session_tracking": {
    "filter": {
      "tool_calls": "omit",
      "tool_content": "omit",
      "user_messages": "summary",
      "agent_messages": "summary"
    }
  }
}
```

### Missing Session Context

**Symptom**: Claude doesn't remember previous sessions

**Solution**: Reduce filtering to preserve more context

```json
{
  "session_tracking": {
    "filter": {
      "tool_calls": "full",
      "tool_content": "full",
      "user_messages": "full",
      "agent_messages": "full"
    }
  }
}
```

---

## FAQ

### Q: Is session tracking enabled by default?

**A**: Yes, session tracking is enabled by default in v1.0.0. You can disable it via CLI or config.

### Q: How much does session tracking cost?

**A**: With default filtering (~35% reduction), expect ~$0.03-$0.05 per session. Adjust filtering to optimize cost.

### Q: Where are sessions stored?

**A**: Sessions are indexed into your Graphiti knowledge graph (Neo4j database). Original session files remain in `~/.claude/sessions`.

### Q: Can I control tracking per session?

**A**: Yes! Use MCP tools: `session_tracking_start()` and `session_tracking_stop()` for per-session control.

### Q: Does this work with non-Claude Code IDEs?

**A**: Currently, session tracking is optimized for Claude Code JSONL session files. Support for other formats may be added in future releases.

### Q: How do I check if it's working?

**A**: Use the MCP tool `session_tracking_status()` to see comprehensive status including active sessions and filter configuration.

---

## Next Steps

1. ✅ Configure session tracking (customize filtering if needed)
2. ✅ Test with a few Claude Code sessions
3. ✅ Monitor LLM costs and adjust filtering
4. ✅ Use `search_memory_nodes()` to query session history
5. ✅ Explore runtime control via MCP tools

**Enjoy cross-session continuity with Graphiti!**

---

**Last Updated**: 2025-11-18
**Version**: v1.0.0
