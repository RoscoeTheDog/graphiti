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
- `health_check` - Check server health and database connectivity (returns connection status, metrics, and error details if unhealthy)

---

## Resilience Features

The MCP server includes automatic recovery and monitoring features:

- **Automatic Reconnection**: Reconnects to database on connection failure with exponential backoff
- **Episode Timeouts**: Prevents indefinite hangs (default: 60 seconds per episode)
- **Health Monitoring**: Tracks connection status and processing metrics
- **Queue Recovery**: Queue workers restart automatically after successful reconnection
- **Error Classification**: Distinguishes recoverable errors (retries) from fatal errors (stops)

Configuration is managed through `graphiti.config.json` in the `resilience` section. See [CONFIGURATION.md](CONFIGURATION.md#resilience-configuration) for details.

---

## Documentation

For detailed information:
- **[CONFIGURATION.md](CONFIGURATION.md)** - Complete configuration reference
- **[README.md](README.md)** - Quick start and overview
- **[Migration Guide](implementation/guides/MIGRATION_GUIDE.md)** - Upgrade from old .env system

---

**Last Updated:** 2025-11-03
**Version:** 2.0 (Unified Configuration)
