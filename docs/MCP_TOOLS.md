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
Add episodes to the knowledge graph and optionally export to file.

**Description**: Store information as an episode in the knowledge graph. Episodes can be plain text, messages, or structured JSON data. Optionally save the episode content to a file on the filesystem.

**Parameters**:
- `name` (string, required): Name/title of the episode
- `episode_body` (string, required): Content to store
- `group_id` (string, optional): Group ID for organizing episodes
- `source` (string, optional): Source type - `text`, `json`, or `message`
- `source_description` (string, optional): Description of the source
- `uuid` (string, optional): Custom UUID for the episode
- `filepath` (string, optional): File path to export episode. Supports path variables:
  - `{date}` - Current date (YYYY-MM-DD)
  - `{timestamp}` - Date and time (YYYY-MM-DD-HHMM)
  - `{time}` - Time only (HHMM)
  - `{hash}` - MD5 hash of episode name (8 chars)

**Example Usage**:
```python
# Add to graph only (backward compatible)
add_memory(
    name="User Preference",
    episode_body="User prefers dark mode and compact layouts",
    source="text"
)

# Add to graph AND save to file
add_memory(
    name="Bug Report",
    episode_body="Login timeout after 5 minutes",
    filepath="bugs/{date}-auth.md"
)

# Add structured data with dynamic filepath
add_memory(
    name="Feature Request",
    episode_body='{"feature": "export", "priority": "high", "requested_by": "user123"}',
    source="json",
    filepath="data/{timestamp}-feature-request.json"
)

# Organize files by date with hash for uniqueness
add_memory(
    name="Support Conversation",
    episode_body="user: How do I reset password?\nassistant: Click 'Forgot Password'",
    source="message",
    filepath="chats/{date}/{timestamp}-{hash}.txt"
)
```

**Filesystem Export Features**:
- Automatic directory creation (parent directories created as needed)
- Path variable substitution for dynamic filenames
- Security scanning (warns if credentials detected in content)
- Path traversal protection (blocks `..` patterns)

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

### Session Tracking Operations

#### `session_tracking_start`
Enable session tracking for the current or specified Claude Code session.

**Description**: Start automatic JSONL session tracking for Claude Code sessions. When enabled, the system monitors session files, filters messages, and indexes them into the Graphiti knowledge graph for cross-session memory and continuity.

**Parameters**:
- `session_id` (string, optional): Session ID to enable tracking for. If None, uses current session.
  - Format: UUID string (extracted from JSONL filename)
- `force` (bool, optional): Force enable even if globally disabled (default: False)

**Runtime Behavior**:
- Without `force`: Respects global configuration (`session_tracking.enabled`)
- With `force=True`: Overrides global config and always enables tracking

**Returns**: JSON string with status and configuration details

**Example Usage**:
```python
# Enable for current session (respects global config)
session_tracking_start()

# Enable for specific session
session_tracking_start(session_id="abc123-def456")

# Force enable (override global config)
session_tracking_start(force=True)
```

**Response Format**:
```json
{
  "status": "success",
  "message": "Session tracking enabled for session abc123-def456",
  "session_id": "abc123-def456",
  "enabled": true,
  "forced": false,
  "global_config": true
}
```

**Notes**:
- Requires Neo4j database connection
- Filtered sessions reduce token usage by 35-70% (configurable)
- Sessions are indexed when they become inactive (default: 5 minutes)
- Use `session_tracking_status()` to check current state

---

#### `session_tracking_stop`
Disable session tracking for the current or specified Claude Code session.

**Description**: Stop automatic JSONL session tracking for a specific session. The session will no longer be monitored or indexed into Graphiti, even if globally enabled.

**Parameters**:
- `session_id` (string, optional): Session ID to disable tracking for. If None, uses current session.
  - Format: UUID string (extracted from JSONL filename)

**Runtime Behavior**:
- Adds session ID to exclusion list
- Does not affect other active sessions
- Does not modify global configuration

**Returns**: JSON string with status

**Example Usage**:
```python
# Disable for current session
session_tracking_stop()

# Disable for specific session
session_tracking_stop(session_id="abc123-def456")
```

**Response Format**:
```json
{
  "status": "success",
  "message": "Session tracking disabled for session abc123-def456",
  "session_id": "abc123-def456",
  "enabled": false
}
```

**Notes**:
- Stopping tracking does NOT delete already-indexed data
- To re-enable, use `session_tracking_start()`
- To check status, use `session_tracking_status()`

---

#### `session_tracking_status`
Get session tracking status and configuration details.

**Description**: Returns comprehensive information about session tracking state, including global configuration, per-session runtime state, session manager status, active session count, and filtering configuration.

**Parameters**:
- `session_id` (string, optional): Session ID to check status for. If None, returns global status.
  - Format: UUID string (extracted from JSONL filename)

**Returns**: JSON string with detailed status information

**Example Usage**:
```python
# Check global status
session_tracking_status()

# Check specific session status
session_tracking_status(session_id="abc123-def456")
```

**Response Format**:
```json
{
  "status": "success",
  "session_id": "abc123-def456",
  "enabled": true,
  "global_config": {
    "enabled": true,
    "watch_path": "/home/user/.claude/projects",
    "inactivity_timeout": 300,
    "check_interval": 60
  },
  "runtime_override": null,
  "session_manager": {
    "running": true,
    "active_sessions": 3
  },
  "filter_config": {
    "tool_calls": "SUMMARY",
    "tool_content": "SUMMARY",
    "user_messages": "FULL",
    "agent_messages": "FULL"
  }
}
```

**Response Fields**:
- `enabled`: Effective state for this session (runtime override OR global config)
- `global_config`: Global configuration from `graphiti.config.json`
- `runtime_override`: Per-session override (true/false if set, null if not)
- `session_manager`: Session manager runtime status
- `filter_config`: Content filtering strategy (see CONFIGURATION.md)

**Notes**:
- Use this tool to verify configuration before starting tracking
- Effective state = runtime override OR global config
- Filter config shows token reduction strategy

---

#### `session_tracking_sync_history`
Manually sync historical sessions to Graphiti beyond the automatic rolling window.

**Description**: This tool allows users to index historical sessions that fall outside the automatic rolling window discovery. Useful for one-time imports, catching up on missed sessions, or backfilling historical data.

**Parameters**:
- `project` (string, optional): Project path to sync. If None, syncs all projects in watch_path
- `days` (int, optional): Number of days to look back (default: 7). Set to 0 for all history (requires `--confirm` in CLI)
- `max_sessions` (int, optional): Maximum sessions to sync (safety limit, default: 100)
- `dry_run` (bool, optional): Preview mode without actual indexing (default: True)

**Runtime Behavior**:
- **Dry-run mode** (default): Returns preview with session list and cost estimate
- **Actual sync mode**: Parses, filters, and indexes sessions to Graphiti

**Returns**: JSON string with sync results

**Example Usage**:
```python
# Preview last 7 days (default)
session_tracking_sync_history()

# Preview last 30 days
session_tracking_sync_history(days=30)

# Actually sync last 7 days
session_tracking_sync_history(dry_run=False)

# Sync specific project
session_tracking_sync_history(project="/path/to/project", dry_run=False)
```

**Dry-Run Response Format**:
```json
{
  "status": "success",
  "dry_run": true,
  "sessions_found": 15,
  "estimated_cost": "$2.55",
  "estimated_tokens": 52500,
  "sessions": [
    {
      "path": "/home/user/.claude/projects/abc123/sessions/def456.jsonl",
      "modified": "2025-11-18T14:30:00",
      "messages": 42
    }
  ],
  "message": "Run with dry_run=False to perform actual sync"
}
```

**Actual Sync Response Format**:
```json
{
  "status": "success",
  "dry_run": false,
  "sessions_found": 15,
  "sessions_indexed": 15,
  "estimated_cost": "$2.55",
  "actual_cost": "$2.55"
}
```

**Notes**:
- Cost estimation: ~$0.17 per session, ~3500 tokens average
- Safety limit prevents accidentally indexing thousands of sessions
- Dry-run mode enabled by default for safety
- Sessions are sorted by modification time (newest first)
- Max sessions limit (default 100) prevents runaway costs
- Time filter uses file modification time
- Uses same filtering and indexing pipeline as automatic tracking

**CLI Alternative**:
```bash
# Preview sync (dry-run by default)
graphiti-mcp session-tracking sync --days 30

# Actually sync
graphiti-mcp session-tracking sync --days 30 --no-dry-run

# Sync all history (requires confirmation)
graphiti-mcp session-tracking sync --days 0 --no-dry-run --confirm
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

---

## Filepath Parameter - Path Resolution

The `filepath` parameter in `add_memory` supports both relative and absolute paths with dynamic variable substitution.

### Path Resolution Behavior

**Relative Paths** (recommended):
- Resolved relative to the **client's working directory** (where you run Claude Code)
- Example: `.claude/handoff/snapshots/session.md` → `{project_root}/.claude/handoff/snapshots/session.md`

**Absolute Paths**:
- Used as-is without modification
- Example: `/tmp/output.md` → `/tmp/output.md`

### Path Variables

Dynamic variables are substituted before path resolution:

| Variable | Description | Example |
|----------|-------------|---------|
| `{date}` | Current date (YYYY-MM-DD) | `2025-11-09` |
| `{timestamp}` | Date and time (YYYY-MM-DD-HHMM) | `2025-11-09-1430` |
| `{time}` | Time only (HHMM) | `1430` |
| `{hash}` | MD5 hash of episode name (8 chars) | `a3f5c9d2` |

### Examples

**Basic Relative Path**:
```python
add_memory(
    name="Session Notes",
    episode_body="Today's progress...",
    filepath=".claude/handoff/current.md"
)
# Creates: {project_root}/.claude/handoff/current.md
```

**With Date Variables**:
```python
add_memory(
    name="Daily Report",
    episode_body="Summary of work...",
    filepath=".claude/handoff/{date}-report.md"
)
# Creates: {project_root}/.claude/handoff/2025-11-09-report.md
```

**With Multiple Variables**:
```python
add_memory(
    name="Bug Report",
    episode_body="Login timeout issue...",
    filepath="bugs/{date}/{time}-{hash}.md"
)
# Creates: {project_root}/bugs/2025-11-09/1430-a3f5c9d2.md
```

**Absolute Path**:
```python
add_memory(
    name="Temp Output",
    episode_body="Temporary data...",
    filepath="/tmp/scratch.md"
)
# Creates: /tmp/scratch.md
```

### Notes

- Directories are created automatically if they don't exist
- Path traversal (`..`) is blocked for security
- Success messages show paths relative to project root for clarity
- Files are written with UTF-8 encoding

### Technical Details

**Implementation**: The MCP server uses the `PWD` environment variable to detect the client's working directory. This is a workaround for Claude Code's roots capability bug ([GitHub issue #3315](https://github.com/anthropics/claude-code/issues/3315)).

**Cross-Platform**: Works on Windows, macOS, and Linux.

For more details, see `.claude/context/claude-code-roots-issue.md` in the repository.
