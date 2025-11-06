# Graphiti MCP Tools Reference

This document describes the MCP (Model Context Protocol) tools available when using Graphiti as an MCP server with Claude Code.

**Related Documentation**:
- [CONFIGURATION.md](../CONFIGURATION.md) - Configuration reference
- [README.md](../README.md) - Quick start guide

---

## Overview

Graphiti provides an MCP server that exposes memory operations as tools for AI assistants. These tools allow you to build and query a temporal knowledge graph for agent memory.

**MCP Server Location**: `mcp_server/graphiti_mcp_server.py`

---

## Available Tools

### Memory Operations

#### `add_memory`
Add episodes to the knowledge graph.

**Description**: Store information as an episode in the knowledge graph. Episodes can be plain text, messages, or structured JSON data.

**Parameters**:
- `name` (string, required): Name/title of the episode
- `episode_body` (string, required): Content to store
- `group_id` (string, optional): Group ID for organizing episodes
- `source` (string, optional): Source type - `text`, `json`, or `message`
- `source_description` (string, optional): Description of the source
- `uuid` (string, optional): Custom UUID for the episode

**Example Usage**:
```python
# Add plain text
add_memory(
    name="User Preference",
    episode_body="User prefers dark mode and compact layouts",
    source="text"
)

# Add structured data
add_memory(
    name="Feature Request",
    episode_body='{"feature": "export", "priority": "high", "requested_by": "user123"}',
    source="json"
)
```

---

### Search Operations

#### `search_memory_nodes`
Search for entities (nodes) in the knowledge graph.

**Description**: Find entities/concepts stored in the graph using semantic search.

**Parameters**:
- `query` (string, required): Search query
- `group_ids` (list, optional): Filter by group IDs
- `max_nodes` (int, optional): Maximum nodes to return (default: 10)
- `center_node_uuid` (string, optional): Center search around a specific node
- `entity` (string, optional): Filter by entity type (`Preference`, `Procedure`)

**Example Usage**:
```python
# Search for user preferences
search_memory_nodes(
    query="user interface preferences",
    entity="Preference",
    max_nodes=5
)
```

---

#### `search_memory_facts`
Search for relationships (facts) between entities.

**Description**: Find connections and relationships between entities in the graph.

**Parameters**:
- `query` (string, required): Search query
- `group_ids` (list, optional): Filter by group IDs
- `max_facts` (int, optional): Maximum facts to return (default: 10)
- `center_node_uuid` (string, optional): Center search around a specific node

**Example Usage**:
```python
# Search for relationships
search_memory_facts(
    query="user preferences related to UI",
    max_facts=10
)
```

---

### Retrieval Operations

#### `get_episodes`
Retrieve recent memory episodes.

**Description**: Get the most recent episodes for a specific group.

**Parameters**:
- `group_id` (string, optional): Group ID to filter episodes
- `last_n` (int, optional): Number of recent episodes to retrieve (default: 10)

**Example Usage**:
```python
# Get last 5 episodes
get_episodes(last_n=5)
```

---

### Deletion Operations

#### `delete_episode`
Remove an episode from the knowledge graph.

**Description**: Delete a specific episode by its UUID.

**Parameters**:
- `uuid` (string, required): UUID of the episode to delete

**Example Usage**:
```python
delete_episode(uuid="episode-uuid-here")
```

---

#### `delete_entity_edge`
Remove a relationship edge from the graph.

**Description**: Delete a specific relationship between entities.

**Parameters**:
- `uuid` (string, required): UUID of the entity edge to delete

**Example Usage**:
```python
delete_entity_edge(uuid="edge-uuid-here")
```

---

### Utility Operations

#### `clear_graph`
Clear all data from the knowledge graph.

**Description**: Remove all episodes, entities, and relationships. **Use with caution** - this is irreversible.

**Parameters**: None

**Example Usage**:
```python
clear_graph()
```

---

#### `health_check`
Check server and database health.

**Description**: Verify MCP server connectivity, database connection status, and view metrics.

**Parameters**: None

**Returns**:
- Connection status (healthy/unhealthy)
- Database connectivity (connected/disconnected)
- Connection metrics (last successful connection, consecutive failures)
- Error details (if unhealthy)

**Example Usage**:
```python
health_check()
# Returns: {"status": "healthy", "database_connected": true, ...}
```

---

## Resilience Features

The MCP server includes automatic recovery and monitoring:

- **Automatic Reconnection**: Reconnects to database on connection failure with exponential backoff
- **Episode Timeouts**: Prevents indefinite hangs (default: 60 seconds per episode)
- **Health Monitoring**: Tracks connection status and processing metrics
- **Queue Recovery**: Queue workers restart automatically after successful reconnection
- **Error Classification**: Distinguishes recoverable errors (retries) from fatal errors (stops)

**Configuration**: Managed through `graphiti.config.json` in the `resilience` section.

See [CONFIGURATION.md](../CONFIGURATION.md#resilience-configuration) for resilience configuration details.

---

## Configuration

### MCP Server Setup

To use these tools, configure the Graphiti MCP server in your Claude Code CLI configuration:

**Location**: `~/.claude.json` or project-local MCP config

**Example Configuration**:
```json
{
  "mcpServers": {
    "graphiti-memory": {
      "type": "stdio",
      "command": "/path/to/python",
      "args": ["/path/to/graphiti/mcp_server/graphiti_mcp_server.py"],
      "env": {
        "NEO4J_URI": "neo4j+ssc://xxxxx.databases.neo4j.io",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password",
        "OPENAI_API_KEY": "sk-your-key"
      }
    }
  }
}
```

**See Also**: `claude-mcp-installer/instance/CLAUDE_INSTALL.md` for complete MCP server installation guide.

---

## Database Configuration

Graphiti requires a Neo4j database. Configuration is in `graphiti.config.json`:

**Recommended Setup**:
- **Neo4j Community Edition** (Windows Service): $0 cost, requires one-time setup
- **Neo4j Aura** (Cloud): $65/month, quick setup but ongoing cost
- **Neo4j Docker**: Containerized, easy cleanup

See [CONFIGURATION.md](../CONFIGURATION.md#database-configuration) for database configuration details.

---

## Best Practices

### Memory Organization

1. **Use Group IDs**: Organize episodes by conversation, user, or project
2. **Descriptive Names**: Make episode names searchable and meaningful
3. **Structured Data**: Use JSON source type for complex data
4. **Temporal Context**: Episodes automatically track creation time

### Search Optimization

1. **Specific Queries**: More specific queries yield better results
2. **Entity Filtering**: Use entity type filters when searching for specific concepts
3. **Limit Results**: Use `max_nodes`/`max_facts` to control result size
4. **Center Node**: Use `center_node_uuid` for contextual searches

### Health Monitoring

1. **Regular Checks**: Use `health_check` before bulk operations
2. **Monitor Metrics**: Track consecutive failures for reliability
3. **Connection Issues**: Check database connectivity if tools fail

---

## Troubleshooting

### Tool Failures

**Symptom**: MCP tools return errors or timeout

**Diagnosis**:
1. Run `health_check` to verify database connectivity
2. Check MCP server logs in Claude Code debug output
3. Verify database is running (`sc query Neo4j` on Windows, `docker ps` for Docker)

**Solutions**:
- **Database disconnected**: Restart database service
- **Authentication failed**: Verify credentials in MCP config
- **Timeout errors**: Check resilience configuration in `graphiti.config.json`

### Connection Issues

**Symptom**: "Unable to retrieve routing information" (VMs)

**Solution**: Use `neo4j+ssc://` URI scheme instead of `neo4j+s://`

See [claude-mcp-installer/instance/CLAUDE_INSTALL.md](../claude-mcp-installer/instance/CLAUDE_INSTALL.md#vm-specific-troubleshooting) for VM-specific troubleshooting.

---

## Related Documentation

- **[CONFIGURATION.md](../CONFIGURATION.md)** - Complete configuration reference
- **[README.md](../README.md)** - Project overview and quick start
- **[claude-mcp-installer/instance/CLAUDE_INSTALL.md](../claude-mcp-installer/instance/CLAUDE_INSTALL.md)** - MCP server installation
- **[Implementation Guides](./.claude/implementation/guides/)** - Migration and upgrade guides

---

**Last Updated:** 2025-11-06
**Version:** 1.0
