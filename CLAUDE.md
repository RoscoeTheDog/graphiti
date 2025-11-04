# Graphiti - Claude Integration Guide

This document provides guidance for AI assistants (particularly Claude) when working with Graphiti.

## Quick Reference

Graphiti uses a **unified configuration system**:
- **graphiti.config.json** - All structural settings (version controlled)
- **.env** - Secrets only (passwords, API keys)

For complete configuration documentation, see [CONFIGURATION.md](CONFIGURATION.md).

---

## Memory Filter Tool

Graphiti includes an **intelligent memory filter** that automatically decides what should be stored in long-term memory.

### Usage

Simply call the `should_store` MCP tool before storing to memory:

```python
# The filter handles the decision logic
result = should_store(
    content="Description of what happened",
    context="Additional context (files changed, errors, etc.)"
)

# Follow the filter's decision
if result["should_store"]:
    add_memory(
        name="Descriptive name",
        episode_body=content,
        source="text",
        group_id="session-id"
    )
```

The filter uses LLM-based intelligence to determine:
- What's valuable to remember (env quirks, user preferences, architectural decisions)
- What's already captured elsewhere (bug fixes in git, config in repo, docs added)

**That's it!** The filter handles all the complexity. No need to memorize categories or rules.

---

## Configuration

Enable/disable filtering in `graphiti.config.json`:

```json
{
  "memory_filter": {
    "enabled": true  // Set to false to disable filtering
  }
}
```

---

## MCP Tools Available

When working with Graphiti MCP server:

- `add_memory` - Add episodes to the knowledge graph
- `should_store` - Check if content should be stored (intelligent filter)
- `search_memory_nodes` - Search for entities
- `search_memory_facts` - Search for relationships
- `get_episodes` - Retrieve recent episodes
- `delete_episode` - Remove episodes
- `delete_entity_edge` - Remove relationships
- `clear_graph` - Clear all data

---

## Documentation

For detailed information:
- **[CONFIGURATION.md](CONFIGURATION.md)** - Complete configuration reference
- **[README.md](README.md)** - Quick start and overview
- **[Migration Guide](implementation/guides/MIGRATION_GUIDE.md)** - Upgrade from old .env system

---

**Last Updated:** 2025-11-03
**Version:** 2.0 (Unified Configuration + Intelligent Filter)
