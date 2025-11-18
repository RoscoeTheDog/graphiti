# Graphiti Configuration Reference

Complete documentation for `graphiti.config.json` - the unified configuration system for Graphiti.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration File Structure](#configuration-file-structure)
4. [Database Configuration](#database-configuration)
5. [LLM Configuration](#llm-configuration)
6. [Embedder Configuration](#embedder-configuration)
7. [Memory Filter Configuration](#memory-filter-configuration)
8. [Project Configuration](#project-configuration)
9. [Search Configuration](#search-configuration)
10. [Resilience Configuration](#resilience-configuration)
11. [Session Tracking Configuration](#session-tracking-configuration) ⭐ New in v0.4.0
12. [Environment Variable Overrides](#environment-variable-overrides)
13. [Complete Examples](#complete-examples)
14. [Troubleshooting](#troubleshooting)

---

## Overview

Graphiti uses a **unified configuration system** where all structural settings are in `graphiti.config.json` and only secrets (passwords, API keys) are in `.env`.

### Benefits

- **Single source of truth** for configuration
- **Type-safe** with Pydantic validation
- **Version controlled** (graphiti.config.json is committed)
- **Environment overrides** for deployment flexibility
- **Backend switching** without code changes

### File Locations

Configuration files are searched in this order:
1. `./graphiti.config.json` (project directory)
2. `~/.graphiti/graphiti.config.json` (global)
3. Built-in defaults (in `mcp_server/unified_config.py`)

**Note**: If upgrading from v0.3.x or earlier, configurations from `~/.claude/graphiti.config.json` will be automatically migrated to `~/.graphiti/` on first use.

---

## Quick Start

### 1. Edit Configuration
```bash
# Edit the existing config file or copy it
cp graphiti.config.json graphiti.config.local.json  # Optional: for local customization
# Or edit graphiti.config.json directly
```

### 2. Create .env with Secrets
```bash
cat > .env << 'EOF'
NEO4J_PASSWORD=your_neo4j_password
OPENAI_API_KEY=sk-your-openai-key
EOF
```

### 3. Start Server
```bash
python -m mcp_server.graphiti_mcp_server
```

The server will:
1. Load `graphiti.config.json`
2. Apply environment overrides from `.env`
3. Validate configuration
4. Initialize components

---

## Configuration File Structure

```json
{
  "database": { /* Database backend settings */ },
  "llm": { /* LLM provider settings */ },
  "embedder": { /* Embedder settings */ },
  "project": { /* Project metadata */ },
  "search": { /* Search parameters */ },
  "logging": { /* Logging configuration */ }
}
```

---

## Database Configuration

### Overview

Graphiti supports multiple graph database backends:
- **Neo4j** (default) - Community or Enterprise Edition
- **FalkorDB** - Redis-based graph database

### Backend Selection

```json
{
  "database": {
    "backend": "neo4j",  // or "falkordb"
    "neo4j": { /* Neo4j config */ },
    "falkordb": { /* FalkorDB config */ }
  }
}
```

### Neo4j Configuration

```json
{
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password": "${NEO4J_PASSWORD}",  // From .env
      "database": "neo4j"
    }
  }
}
```

**Fields:**
- `uri` - Connection URI (bolt://, neo4j://, bolt+s://)
- `user` - Database username
- `password` - Use `${ENV_VAR}` syntax for secrets
- `database` - Database name (default: "neo4j")

**Environment Override:**
```bash
export NEO4J_URI=bolt://production-server:7687
export NEO4J_USER=admin
export NEO4J_PASSWORD=secure_password
```

### FalkorDB Configuration

```json
{
  "database": {
    "backend": "falkordb",
    "falkordb": {
      "uri": "redis://localhost:6379",
      "password": "${FALKORDB_PASSWORD}",
      "graph_name": "graphiti"
    }
  }
}
```

**Fields:**
- `uri` - Redis connection URI
- `password` - Use `${ENV_VAR}` syntax
- `graph_name` - Name of the graph (default: "graphiti")

---

## LLM Configuration

### Overview

Graphiti supports multiple LLM providers:
- **OpenAI** (default)
- **Azure OpenAI**
- **Anthropic**

### Provider Selection

```json
{
  "llm": {
    "provider": "openai",  // "openai" | "azure_openai" | "anthropic"
    "default_model": "gpt-4o-mini",
    "temperature": 0.0,
    "max_tokens": 8192,
    "semaphore_limit": 10,
    "openai": { /* OpenAI config */ },
    "azure_openai": { /* Azure config */ },
    "anthropic": { /* Anthropic config */ }
  }
}
```

### OpenAI Configuration

```json
{
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "openai": {
      "api_key": "${OPENAI_API_KEY}",
      "base_url": null,  // Optional: custom endpoint
      "organization": null  // Optional: org ID
    }
  }
}
```

**Environment Override:**
```bash
export OPENAI_API_KEY=sk-your-key
export MODEL_NAME=gpt-4o  # Override default_model
```

### Azure OpenAI Configuration

```json
{
  "llm": {
    "provider": "azure_openai",
    "default_model": "gpt-4",
    "azure_openai": {
      "api_key": "${AZURE_OPENAI_API_KEY}",
      "endpoint": "${AZURE_OPENAI_ENDPOINT}",
      "api_version": "2024-02-15-preview",
      "deployment_name": "gpt-4-deployment"
    }
  }
}
```

**Fields:**
- `endpoint` - Azure resource endpoint (e.g., https://your-resource.openai.azure.com)
- `deployment_name` - Name of your deployment
- `api_version` - API version (see Azure docs)

### Anthropic Configuration

```json
{
  "llm": {
    "provider": "anthropic",
    "default_model": "claude-3-5-sonnet-20241022",
    "anthropic": {
      "api_key": "${ANTHROPIC_API_KEY}",
      "base_url": null
    }
  }
}
```

---

## Embedder Configuration

### Overview

Embedders generate vector representations for semantic search.

### Supported Providers

- **OpenAI** (default) - text-embedding-3-small
- **Azure OpenAI** - Azure-hosted embeddings

### OpenAI Embedder

```json
{
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "embedding_dim": 1536,
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  }
}
```

**Fields:**
- `model` - Embedding model name
- `embedding_dim` - Dimension of embeddings (1536 for text-embedding-3-small)

### Azure OpenAI Embedder

```json
{
  "embedder": {
    "provider": "azure_openai",
    "model": "text-embedding-ada-002",
    "embedding_dim": 1536,
    "azure_openai": {
      "api_key": "${AZURE_OPENAI_API_KEY}",
      "endpoint": "${AZURE_OPENAI_ENDPOINT}",
      "api_version": "2024-02-15-preview",
      "deployment_name": "embedding-deployment"
    }
  }
}
```

---

## Project Configuration

```json
{
  "project": {
    "name": "my-project",
    "version": "1.0.0"
  }
}
```

---

## Search Configuration

```json
{
  "search": {
    "limit": 10,
    "num_episodes": 5,
    "num_results": 10
  }
}
```

**Fields:**
- `limit` - Default result limit
- `num_episodes` - Episodes to retrieve
- `num_results` - Search results to return

---

## Resilience Configuration

The resilience configuration controls automatic reconnection, health monitoring, and error recovery behavior for the MCP server.

### Configuration

```json
{
  "resilience": {
    "max_retries": 3,
    "retry_backoff_base": 2,
    "episode_timeout": 60,
    "health_check_interval": 300
  }
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_retries` | int | 3 | Maximum number of connection retry attempts on failure |
| `retry_backoff_base` | int | 2 | Base for exponential backoff calculation (seconds = base^retry_count) |
| `episode_timeout` | int | 60 | Timeout in seconds for episode processing operations |
| `health_check_interval` | int | 300 | Interval in seconds for logging connection health metrics |

### Retry Behavior

When a connection failure occurs, the MCP server will automatically attempt to reconnect using exponential backoff:

- **Retry 1**: Wait 2^0 = 1 second
- **Retry 2**: Wait 2^1 = 2 seconds
- **Retry 3**: Wait 2^2 = 4 seconds

After `max_retries` attempts, the server will stop the affected queue worker and log an error.

### Episode Timeout

The `episode_timeout` setting prevents indefinite hangs during episode processing:

- If an episode takes longer than `episode_timeout` seconds to process, it will be cancelled
- A timeout error will be logged with episode details
- The episode is removed from the queue
- Subsequent episodes continue processing normally
- The queue worker remains active and continues processing

### Health Monitoring

The MCP server automatically monitors connection health:

- Connection status is checked periodically
- Health metrics are logged every `health_check_interval` seconds
- Metrics include: connection status, episode success/failure rates, queue depths
- Use the `health_check` tool to check connection status on demand

### Environment Overrides

Resilience settings can be overridden with environment variables:

```bash
export GRAPHITI_MAX_RETRIES=5
export GRAPHITI_RETRY_BACKOFF_BASE=3
export GRAPHITI_EPISODE_TIMEOUT=120
export GRAPHITI_HEALTH_CHECK_INTERVAL=600
```

### Example Configuration

**Aggressive Retry (for unstable connections)**:
```json
{
  "resilience": {
    "max_retries": 5,
    "retry_backoff_base": 2,
    "episode_timeout": 120,
    "health_check_interval": 60
  }
}
```

**Conservative Retry (for stable production)**:
```json
{
  "resilience": {
    "max_retries": 2,
    "retry_backoff_base": 3,
    "episode_timeout": 30,
    "health_check_interval": 600
  }
}
```

---

## Session Tracking Configuration

**New in v0.4.0** - Automatic session tracking for Claude Code conversations.

Session tracking monitors Claude Code conversation files (`~/.claude/projects/{hash}/sessions/*.jsonl`) and automatically indexes them to the Graphiti knowledge graph, enabling cross-session memory and context continuity.

### Configuration

```json
{
  "session_tracking": {
    "enabled": false,
    "watch_path": null,
    "inactivity_timeout": 300,
    "check_interval": 60,
    "auto_summarize": true,
    "store_in_graph": true
  }
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Enable/disable automatic session tracking (opt-in model) |
| `watch_path` | str\|null | `null` | Path to directory containing Claude Code session files. If null, defaults to `~/.claude/projects/`. Must be an absolute path. |
| `inactivity_timeout` | int | 300 | **Seconds** of inactivity before session is considered closed and indexed (default: 5 minutes) |
| `check_interval` | int | 60 | **Seconds** between checks for inactive sessions (default: 1 minute) |
| `auto_summarize` | bool | `true` | Automatically summarize closed sessions using Graphiti's LLM |
| `store_in_graph` | bool | `true` | Store session summaries in the Graphiti knowledge graph |

### Behavior

**When enabled:**
1. File watcher monitors `watch_path` directory for new/modified `.jsonl` files
2. Sessions are tracked in-memory with incremental message parsing
3. After `inactivity_timeout` seconds of no activity, session is closed and indexed
4. Filtered session content (93% token reduction) is added as an episode to Graphiti
5. Graphiti automatically extracts entities, relationships, and enables semantic search

**Session lifecycle:**
```
New JSONL file detected
  → Parse messages incrementally
  → Track activity (updates extend timeout)
  → Inactivity timeout reached
  → Filter messages (93% token reduction)
  → Index to Graphiti as episode
  → Link to previous session (if exists)
```

### Default: Enabled (Opt-Out Model)

Session tracking is **enabled by default** starting in v0.4.0. This provides automatic cross-session memory out-of-the-box.

**To disable:**
```bash
# CLI command
graphiti-mcp session-tracking disable

# Or set in config
{
  "session_tracking": {
    "enabled": false
  }
}
```

### Runtime Control (MCP Tools)

Session tracking can be controlled at runtime via MCP tool calls:

```json
// Enable for current session (overrides global config)
{
  "tool": "session_tracking_start",
  "arguments": {
    "force": true
  }
}

// Disable for current session
{
  "tool": "session_tracking_stop"
}

// Check status
{
  "tool": "session_tracking_status"
}
```

### Cost Considerations

**Per session:** ~$0.17 (average)
- Token filtering: 93% reduction (free)
- Entity extraction: ~$0.17 (OpenAI gpt-4o-mini)

**Monthly estimates:**
- Light usage (10 sessions/month): ~$1.70/month
- Regular usage (50 sessions/month): ~$8.50/month
- Heavy usage (100 sessions/month): ~$17.00/month

### Environment Overrides

Session tracking settings can be overridden with environment variables:

```bash
export GRAPHITI_SESSION_TRACKING_ENABLED=false
export GRAPHITI_SESSION_TRACKING_WATCH_DIRECTORIES='["~/.claude/projects"]'
export GRAPHITI_SESSION_TRACKING_INACTIVITY_TIMEOUT_MINUTES=15
export GRAPHITI_SESSION_TRACKING_SCAN_INTERVAL_SECONDS=5
```

### Example Configurations

**Default (Recommended)**:
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": "~/.claude/projects",
    "inactivity_timeout": 300,
    "check_interval": 60
  }
}
```

**High-Volume Environment** (faster session closure, more frequent checks):
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": "~/.claude/projects/active",
    "inactivity_timeout": 180,
    "check_interval": 30
  }
}
```

**Low-Resource System** (longer timeout, less frequent checks):
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": "~/.claude/projects",
    "inactivity_timeout": 600,
    "check_interval": 120
  }
}
```

**Disabled** (opt-out):
```json
{
  "session_tracking": {
    "enabled": false
  }
}
```

### Documentation

For detailed session tracking documentation:
- **User Guide**: [docs/SESSION_TRACKING_USER_GUIDE.md](docs/SESSION_TRACKING_USER_GUIDE.md)
- **Developer Guide**: [docs/SESSION_TRACKING_DEV_GUIDE.md](docs/SESSION_TRACKING_DEV_GUIDE.md)
- **Troubleshooting**: [docs/SESSION_TRACKING_TROUBLESHOOTING.md](docs/SESSION_TRACKING_TROUBLESHOOTING.md)

---

## Environment Variable Overrides

### Override Priority

1. Environment variables (highest)
2. `graphiti.config.json` file
3. Built-in defaults (lowest)

### Supported Overrides

| Environment Variable | Config Path | Type | Example |
|---------------------|-------------|------|---------|
| `GRAPHITI_DB_BACKEND` | `database.backend` | string | `neo4j` |
| `NEO4J_URI` | `database.neo4j.uri` | string | `bolt://localhost:7687` |
| `NEO4J_USER` | `database.neo4j.user` | string | `neo4j` |
| `NEO4J_PASSWORD` | `database.neo4j.password` | string | `password` |
| `NEO4J_DATABASE` | `database.neo4j.database` | string | `neo4j` |
| `MODEL_NAME` | `llm.default_model` | string | `gpt-4o` |
| `OPENAI_API_KEY` | `llm.openai.api_key` | string | `sk-...` |
| `ANTHROPIC_API_KEY` | `llm.anthropic.api_key` | string | `sk-ant-...` |
| `AZURE_OPENAI_ENDPOINT` | `llm.azure_openai.endpoint` | string | `https://...` |
| `AZURE_OPENAI_API_KEY` | `llm.azure_openai.api_key` | string | `...` |
| `EMBEDDER_MODEL_NAME` | `embedder.model` | string | `text-embedding-3-small` |
| `SEMAPHORE_LIMIT` | `llm.semaphore_limit` | int | `10` |
| `GRAPHITI_MAX_RETRIES` | `resilience.max_retries` | int | `3` |
| `GRAPHITI_RETRY_BACKOFF_BASE` | `resilience.retry_backoff_base` | int | `2` |
| `GRAPHITI_EPISODE_TIMEOUT` | `resilience.episode_timeout` | int | `60` |
| `GRAPHITI_HEALTH_CHECK_INTERVAL` | `resilience.health_check_interval` | int | `300` |

### Usage

```bash
# Override in environment
export MODEL_NAME=gpt-4o
export SEMAPHORE_LIMIT=20

# Or inline
MODEL_NAME=gpt-4o python -m mcp_server.graphiti_mcp_server
```

---

## Complete Examples

### Example 1: Neo4j + OpenAI (Default)

```json
{
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password": "${NEO4J_PASSWORD}",
      "database": "neo4j"
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "temperature": 0.0,
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "embedding_dim": 1536,
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  }
}
```

**.env:**
```bash
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=sk-your-key
```

### Example 2: FalkorDB + Azure OpenAI

```json
{
  "database": {
    "backend": "falkordb",
    "falkordb": {
      "uri": "redis://localhost:6379",
      "password": "${FALKORDB_PASSWORD}",
      "graph_name": "graphiti"
    }
  },
  "llm": {
    "provider": "azure_openai",
    "default_model": "gpt-4",
    "azure_openai": {
      "api_key": "${AZURE_OPENAI_API_KEY}",
      "endpoint": "${AZURE_OPENAI_ENDPOINT}",
      "api_version": "2024-02-15-preview",
      "deployment_name": "gpt-4-deployment"
    }
  },
  "embedder": {
    "provider": "azure_openai",
    "model": "text-embedding-ada-002",
    "embedding_dim": 1536,
    "azure_openai": {
      "api_key": "${AZURE_OPENAI_API_KEY}",
      "endpoint": "${AZURE_OPENAI_ENDPOINT}",
      "api_version": "2024-02-15-preview",
      "deployment_name": "embedding-deployment"
    }
  }
}
```

**.env:**
```bash
FALKORDB_PASSWORD=your_password
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_azure_key
```

### Example 3: Neo4j + Anthropic (Filter Only)

```json
{
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password": "${NEO4J_PASSWORD}",
      "database": "neo4j"
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "embedding_dim": 1536,
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  }
}
```

**.env:**
```bash
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=sk-your-openai-key
```

---

## Troubleshooting

### Config Not Loading

**Symptom:** Server uses defaults despite config file existing

**Debug:**
```bash
# Check file exists
ls -la graphiti.config.json

# Validate JSON
python -c "import json; json.load(open('graphiti.config.json'))"

# Check loading
python -c "from mcp_server.unified_config import get_config; print(get_config())"
```

**Solution:** Ensure config file is in project root or `~/.claude/`

### Environment Variables Not Working

**Symptom:** API keys not found

**Debug:**
```bash
# Check .env exists
ls -la .env

# Check variables set
grep OPENAI_API_KEY .env

# Verify in Python
python -c "import os; print(os.environ.get('OPENAI_API_KEY', 'NOT SET'))"
```

**Solution:** Export variables or load .env before starting server

### Database Connection Fails

**Symptom:** Cannot connect to database

**Debug:**
```bash
# Check database running
docker ps | grep neo4j

# Test connection manually (Neo4j)
cypher-shell -a bolt://localhost:7687 -u neo4j -p your_password

# Check config
python -c "
from mcp_server.unified_config import get_config
db = get_config().database.get_active_config()
print(f'URI: {db.uri}')
print(f'User: {db.user}')
"
```

**Solution:** Start database, verify URI/credentials in config

### Invalid Configuration

**Symptom:** Pydantic validation errors

**Common Issues:**
- Invalid backend: Use "neo4j" or "falkordb" (lowercase)
- Invalid provider: Use "openai", "azure_openai", or "anthropic"
- Missing required fields: Check error message
- Type mismatch: Ensure ints are ints, not strings

**Fix:**
```bash
# Validate against schema
python -c "
from mcp_server.unified_config import GraphitiConfig
import json

with open('graphiti.config.json') as f:
    config_data = json.load(f)

try:
    GraphitiConfig(**config_data)
    print('✅ Config valid')
except Exception as e:
    print(f'❌ Validation error: {e}')
"
```

### Migration Issues

**Symptom:** Migration script fails

**Solution:**
```bash
# Run in dry-run mode first
python implementation/scripts/migrate-to-unified-config.py --dry-run

# Check for backup files
ls -la .env.backup*

# Restore from backup if needed
cp .env.backup.20241103_120000 .env
```

### Connection Failures and Recovery

**Symptom:** MCP server loses connection to database

**Automatic Recovery:**
- The MCP server automatically attempts reconnection using exponential backoff
- Default: 3 retries with 1s, 2s, 4s delays
- Queue workers restart after successful reconnection
- Episodes continue processing after recovery

**Manual Troubleshooting:**
```bash
# 1. Check database is running
docker ps | grep neo4j

# 2. Test connection manually
cypher-shell -a bolt://localhost:7687 -u neo4j -p your_password

# 3. Check health status using MCP tool
# Use the health_check tool from your MCP client

# 4. Review logs for connection errors
tail -f logs/graphiti_mcp.log | grep -i "connection\|error"
```

**Tuning Resilience Settings:**

For unstable networks:
```json
{
  "resilience": {
    "max_retries": 5,
    "retry_backoff_base": 2,
    "episode_timeout": 120
  }
}
```

For production environments with stable connections:
```json
{
  "resilience": {
    "max_retries": 2,
    "retry_backoff_base": 3,
    "episode_timeout": 30
  }
}
```

### Episode Processing Timeouts

**Symptom:** Episodes hang indefinitely during processing

**Automatic Handling:**
- Default timeout: 60 seconds per episode
- Timed-out episodes are logged and skipped
- Queue worker continues with next episode
- No manual intervention needed

**Configuration:**
```json
{
  "resilience": {
    "episode_timeout": 120  // Increase for large/complex episodes
  }
}
```

**Debug Timeout Issues:**
```bash
# Check logs for timeout patterns
grep "TimeoutError" logs/graphiti_mcp.log

# Review episode that timed out
grep "episode_name" logs/graphiti_mcp.log
```

---

## Additional Resources

- [Unified Config Implementation Plan](implementation/plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md)
- [Memory Filter Implementation Plan](implementation/plans/IMPLEMENTATION_PLAN_LLM_FILTER.md)
- [Migration Guide](implementation/guides/MIGRATION_GUIDE.md)
- [Quick Reference](implementation/guides/UNIFIED_CONFIG_SUMMARY.md)

---

**Last Updated:** 2025-11-03
**Version:** 2.0 (Unified Configuration)
