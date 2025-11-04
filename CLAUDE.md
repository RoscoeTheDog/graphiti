# Graphiti - Claude Integration Guide

This document provides guidance for AI assistants (particularly Claude) when working with Graphiti.

## Overview

Graphiti is a knowledge graph framework with MCP (Model Context Protocol) server integration. This guide covers the unified configuration system and memory filter integration.

---

## Configuration System

Graphiti uses a **unified configuration system**:
- **graphiti.config.json** - All structural settings (version controlled)
- **.env** - Secrets only (passwords, API keys)

### Quick Reference

```bash
# Copy config template
cp implementation/config/graphiti.config.json graphiti.config.json

# Set secrets
cat > .env << 'EOF'
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=sk-your-key
EOF

# Start MCP server
python -m mcp_server.graphiti_mcp_server
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete documentation.

---

## Memory Filter Integration

### Overview

Graphiti includes an LLM-based memory filter to intelligently decide what should be stored in long-term memory.

**Before storing to memory, use the filter tool:**

```python
# Check if content should be stored
result = should_store(
    content="Description of what happened",
    context="Additional context (files changed, errors encountered, etc.)"
)

# Result structure:
{
    "should_store": true/false,
    "category": "user-pref|env-quirk|project-decision|skip",
    "confidence": 0.0-1.0,
    "reason": "Explanation of the decision"
}

# If should_store=true, proceed with storage
if result["should_store"]:
    add_memory(
        name="Descriptive name",
        episode_body=content,
        source="text",
        group_id="session-id"
    )
```

### Filter Categories

✅ **STORE** (non-redundant insights):
- `user-pref` - User preferences (dark mode, editor settings, etc.)
- `env-quirk` - Machine/OS-specific issues (can't fix in code)
- `external-api` - Third-party API quirks or undocumented behavior
- `project-decision` - Architectural decisions, conventions
- `workaround` - Non-obvious workarounds for limitations

❌ **SKIP** (already captured elsewhere):
- `bug-in-code` - Fixed bugs (now in version control)
- `config-in-repo` - Configuration now committed
- `docs-added` - Information now in README/docs
- `ephemeral` - Temporary issues, one-time events

### Configuration

- **Config file**: `graphiti.config.json` (memory_filter section)
- **Enable/disable**: `memory_filter.enabled: true/false`
- **Providers**: Hierarchical fallback (OpenAI → Anthropic)

---

## Workflow: Memory Storage with Filter

**Scenario:** User expresses a preference or you discover an environment quirk

### Step 1: Capture the Event
```
Event: "User prefers 2-space indentation for Python"
Context: "Discussion about code formatting"
```

### Step 2: Check if it Should be Stored
```python
result = should_store(
    content="User prefers 2-space indentation for Python files",
    context="Code formatting discussion, user explicitly stated preference"
)
```

### Step 3: Evaluate Result
```python
if result["should_store"]:
    category = result["category"]  # Expected: "user-pref"
    reason = result["reason"]
```

### Step 4: Store to Memory
```python
add_memory(
    name="Python Indentation Preference",
    episode_body="User prefers 2-space indentation for Python files",
    source="message",
    source_description="user preference",
    group_id="user-preferences"
)
```

---

## Anti-Patterns

### ❌ Don't Blindly Store Everything

**BAD:**
```python
# No filtering
add_memory("Fixed bug in parser.py", ...)  # Already in git!
```

**GOOD:**
```python
# Use filter first
result = should_store("Fixed bug in parser.py", "Committed to git")
if result["should_store"]:  # Will be False (bug-in-code)
    add_memory(...)  # Won't execute
```

---

## MCP Tools Available

When working with Graphiti MCP server, these tools are available:

- `add_memory` - Add episodes to the knowledge graph
- `should_store` - Check if content should be stored (filter)
- `search_memory_nodes` - Search for entities
- `search_memory_facts` - Search for relationships
- `get_episodes` - Retrieve recent episodes
- `delete_episode` - Remove episodes
- `delete_entity_edge` - Remove relationships
- `clear_graph` - Clear all data

---

## Implementation Notes

### Database Backends

Graphiti supports multiple backends (configured in `graphiti.config.json`):
- **Neo4j** (default) - `"backend": "neo4j"`
- **FalkorDB** - `"backend": "falkordb"`

Switch backends by editing config file and restarting server.

### LLM Providers

Supported providers (configured in `graphiti.config.json`):
- **OpenAI** (default) - `"provider": "openai"`
- **Azure OpenAI** - `"provider": "azure_openai"`
- **Anthropic** - `"provider": "anthropic"`

### Environment Variable Overrides

Common overrides:
- `NEO4J_PASSWORD` - Database password
- `OPENAI_API_KEY` - LLM API key
- `ANTHROPIC_API_KEY` - Alternative LLM (for filter fallback)
- `MODEL_NAME` - Override default model
- `SEMAPHORE_LIMIT` - Concurrency limit (default: 10)

---

## Troubleshooting

### Config Not Loading
- Ensure `graphiti.config.json` in project root
- Validate JSON syntax: `python -c "import json; json.load(open('graphiti.config.json'))"`

### Filter Not Working
- Check `memory_filter.enabled: true` in config
- Verify API keys set in `.env`
- Check logs for filter initialization

### Database Connection Issues
- Verify database is running: `docker ps | grep neo4j`
- Check credentials in config
- Test connection manually

---

## Additional Resources

- [Configuration Reference](CONFIGURATION.md) - Complete config documentation
- [Migration Guide](implementation/guides/MIGRATION_GUIDE.md) - Migrating from old .env system
- [Unified Config Summary](implementation/guides/UNIFIED_CONFIG_SUMMARY.md) - Quick reference
- [Implementation Plans](implementation/plans/) - Detailed implementation docs

---

**Last Updated:** 2025-11-03
**Version:** 2.0 (Unified Configuration)
