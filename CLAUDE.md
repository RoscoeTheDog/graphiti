# Graphiti - Claude Integration Guide

This document provides guidance for AI assistants (particularly Claude) when working with Graphiti.

## Quick Reference

Graphiti uses a **unified configuration system**:
- **graphiti.config.json** - All structural settings (version controlled)
- **.env** - Secrets only (passwords, API keys)

For complete configuration documentation, see [CONFIGURATION.md](CONFIGURATION.md).

---

## MCP Tools Available

When working with Graphiti MCP server:

- `add_memory` - Add episodes to the knowledge graph
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
**Version:** 2.0 (Unified Configuration)
