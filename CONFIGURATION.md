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
11. [LLM Resilience Configuration](#llm-resilience-configuration) ⭐ New in v1.0.0
12. [MCP Tools Configuration](#mcp-tools-configuration) ⭐ New in v1.0.0
13. [Session Tracking Configuration](#session-tracking-configuration)
14. [Environment Variable Overrides](#environment-variable-overrides)
15. [Complete Examples](#complete-examples)
16. [Troubleshooting](#troubleshooting)

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

## LLM Resilience Configuration

**New in v1.0.0** - Comprehensive LLM operation resilience with health checks, retry policies, and circuit breaker patterns.

The LLM resilience system provides robust handling of LLM API failures, rate limits, and timeouts, ensuring graceful degradation and automatic recovery.

### Configuration

```json
{
  "llm_resilience": {
    "health_check": {
      "enabled": true,
      "interval_seconds": 60,
      "on_startup": true,
      "timeout_seconds": 10
    },
    "retry": {
      "max_attempts": 4,
      "initial_delay_seconds": 5,
      "max_delay_seconds": 120,
      "exponential_base": 2,
      "retry_on_rate_limit": true,
      "retry_on_timeout": true
    },
    "circuit_breaker": {
      "enabled": true,
      "failure_threshold": 5,
      "recovery_timeout_seconds": 300,
      "half_open_max_calls": 3
    }
  }
}
```

### Health Check Configuration

Periodic health checks verify LLM provider availability before operations.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Enable periodic health checks |
| `interval_seconds` | int | `60` | Seconds between health check probes |
| `on_startup` | bool | `true` | Run health check on MCP server startup |
| `timeout_seconds` | int | `10` | Timeout for individual health check requests |

### Retry Policy Configuration

Exponential backoff retry for transient LLM failures.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_attempts` | int | `4` | Maximum retry attempts before failure |
| `initial_delay_seconds` | float | `5` | Initial delay before first retry |
| `max_delay_seconds` | float | `120` | Maximum delay cap for exponential backoff |
| `exponential_base` | float | `2` | Base for exponential backoff calculation |
| `retry_on_rate_limit` | bool | `true` | Retry on HTTP 429 rate limit errors |
| `retry_on_timeout` | bool | `true` | Retry on timeout errors |

**Retry Delay Calculation**: `min(initial_delay * (exponential_base ^ attempt), max_delay)`

### Circuit Breaker Configuration

Prevents cascading failures by temporarily disabling LLM calls after repeated failures.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Enable circuit breaker pattern |
| `failure_threshold` | int | `5` | Consecutive failures before circuit opens |
| `recovery_timeout_seconds` | int | `300` | Seconds before attempting recovery (half-open state) |
| `half_open_max_calls` | int | `3` | Test calls allowed in half-open state |

**Circuit States**:
- **CLOSED**: Normal operation, all calls pass through
- **OPEN**: Circuit tripped, all calls fail immediately (fast-fail)
- **HALF-OPEN**: Recovery testing, limited calls allowed

**Restart Behavior**:

The circuit breaker state is held **in-memory only** and is reset when the MCP server restarts:

- On server start/restart, circuit initializes to **CLOSED** state with `failure_count=0`
- All previous failure history is cleared
- This behavior can be used as a manual recovery technique when the circuit is stuck OPEN
- There is no persistence to disk or database - state is ephemeral

**Important Notes**:
- State is not persisted across MCP server restarts
- To manually reset the circuit without restarting, wait for the `recovery_timeout_seconds` period
- Use the `llm_health_check` MCP tool to monitor circuit state and LLM availability
- Future versions may add optional state persistence (e.g., Redis/database backing)

### Example Configurations

**High Availability (aggressive retry)**:
```json
{
  "llm_resilience": {
    "health_check": {
      "enabled": true,
      "interval_seconds": 30,
      "on_startup": true
    },
    "retry": {
      "max_attempts": 6,
      "initial_delay_seconds": 2,
      "max_delay_seconds": 60
    },
    "circuit_breaker": {
      "enabled": true,
      "failure_threshold": 10,
      "recovery_timeout_seconds": 120
    }
  }
}
```

**Cost-Sensitive (conservative retry)**:
```json
{
  "llm_resilience": {
    "health_check": {
      "enabled": true,
      "interval_seconds": 300,
      "on_startup": false
    },
    "retry": {
      "max_attempts": 2,
      "initial_delay_seconds": 10,
      "max_delay_seconds": 60
    },
    "circuit_breaker": {
      "enabled": false
    }
  }
}
```

---

## MCP Tools Configuration

**New in v1.0.0** - Control MCP tool behavior during LLM unavailability.

Defines how MCP tools respond when the LLM backend is unavailable (circuit breaker open, health check failed, etc.).

### Configuration

```json
{
  "mcp_tools": {
    "on_llm_unavailable": "FAIL",
    "wait_for_completion_default": true,
    "timeout_seconds": 60
  }
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `on_llm_unavailable` | str | `"FAIL"` | Behavior when LLM is unavailable (see modes below) |
| `wait_for_completion_default` | bool | `true` | Default for `add_memory` wait_for_completion parameter |
| `timeout_seconds` | int | `60` | Default timeout for MCP tool operations |

### LLM Unavailable Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `FAIL` | Return error immediately | Production systems requiring explicit error handling |
| `STORE_RAW` | Store raw episode without LLM processing | Data preservation priority |
| `QUEUE_RETRY` | Queue for later processing when LLM recovers | Best-effort processing |

**Note**: `STORE_RAW` and `QUEUE_RETRY` require session tracking resilience configuration for proper queue management.

### Response Types (Story 18)

MCP tools return structured responses with explicit status indicators:

| Status | Description | When Used |
|--------|-------------|-----------|
| `success` | Full processing completed | Normal operation with LLM available |
| `degraded` | Partial success with limitations | LLM unavailable, `STORE_RAW` mode |
| `queued` | Operation queued for later | LLM unavailable, `QUEUE_RETRY` mode |
| `error` | Operation failed | Any error condition |

**Error Responses** include:
- `category`: Error type (e.g., `llm_unavailable`, `database_connection`, `validation`)
- `recoverable`: Boolean indicating if retry may succeed
- `suggestion`: Actionable recovery suggestion
- `retry_after_seconds`: Optional wait time before retry

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
    "inactivity_timeout": 900,
    "check_interval": 60,
    "auto_summarize": false,
    "store_in_graph": true,
    "keep_length_days": 7,
    "filter": {
      "tool_calls": true,
      "tool_content": "default-tool-content.md",
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Enable/disable automatic session tracking (opt-in model for security, **disabled by default**) |
| `watch_path` | str\|null | `null` | Path to directory containing Claude Code session files. If null, defaults to `~/.claude/projects/`. Must be an absolute path. |
| `inactivity_timeout` | int | 900 | **Seconds** of inactivity before session is considered closed and indexed (default: 15 minutes) |
| `check_interval` | int | 60 | **Seconds** between checks for inactive sessions (default: 1 minute) |
| `auto_summarize` | bool | `false` | Automatically summarize closed sessions using Graphiti's LLM (disabled by default to avoid LLM costs) |
| `store_in_graph` | bool | `true` | Store session summaries in the Graphiti knowledge graph |
| `filter` | object | See below | Filtering configuration for session content (controls token reduction) |
| `keep_length_days` | int\|null | 7 | **Days** to retain sessions in rolling window (default: 7 days). If null, discovers all sessions (use with caution - may cause bulk LLM costs). **New in v1.1.0** |

### Filtering Configuration

Control how different message types are filtered during session tracking. Enables fine-grained control over token reduction vs information preservation.

```json
{
  "session_tracking": {
    "enabled": false,
    "filter": {
      "tool_calls": true,
      "tool_content": "default-tool-content.md",
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

**Filter Fields:**

| Field | Type | Options | Default | Description |
|-------|------|---------|---------|-------------|
| `tool_calls` | bool | true/false | `true` | Preserve tool call structure (names, parameters) |
| `tool_content` | bool \| str | true/false/"template.md" | `"default-tool-content.md"` | Tool result content: `true` (full), `false` (omit), or template path for summarization |
| `user_messages` | bool \| str | true/false/"template.md" | `true` | User message content: `true` (full), `false` (omit), or template path for summarization |
| `agent_messages` | bool \| str | true/false/"template.md" | `true` | Agent message content: `true` (full), `false` (omit), or template path for summarization |

**Filter Value Types:**
- **`true`**: Preserve complete content (no filtering)
- **`false`**: Omit content completely, keep structure only (~95% reduction)
- **`"template-file.md"`**: Use custom template for LLM-based summarization (~70% reduction, adds LLM cost)

**Filtering Presets:**

```json
// Default: Balanced (50%+ token reduction, preserves user/agent messages)
{
  "filter": {
    "tool_calls": true,
    "tool_content": "default-tool-content.md",
    "user_messages": true,
    "agent_messages": true
  }
}

// Maximum reduction: Omit all tool results (~60% reduction)
{
  "filter": {
    "tool_calls": true,
    "tool_content": false,
    "user_messages": true,
    "agent_messages": true
  }
}

// Conservative: Preserve everything (no filtering, highest memory accuracy)
{
  "filter": {
    "tool_calls": true,
    "tool_content": true,
    "user_messages": true,
    "agent_messages": true
  }
}

// Aggressive: Summarize everything (~70% reduction, requires LLM cost)
{
  "filter": {
    "tool_calls": true,
    "tool_content": "default-tool-content.md",
    "user_messages": "default-user-messages.md",
    "agent_messages": "default-agent-messages.md"
  }
}
```

**Token Reduction Estimates:**
- Default config: ~35% reduction (summarize tool results only)
- Maximum config: ~60% reduction (omit all tool results)
- Aggressive config: ~70% reduction (summarize everything with LLM)
- Conservative config: 0% reduction (no filtering)

**Note on Template-Based Summarization:**
- **Template paths** (e.g., `"default-tool-content.md"`) trigger LLM-based summarization
- **Cost**: ~$0.01-0.05 per message when using templates for user/agent messages
- **Default configuration** (`true` for user/agent messages) avoids LLM costs
- **Built-in templates**: `default-tool-content.md`, `default-user-messages.md`, `default-agent-messages.md`
- **Custom templates**: Place in `.graphiti/auto-tracking/templates/` (see Template System section below)

### Customizable Summarization Templates

**New in v0.4.0** (Story 11) - Pluggable template system for LLM summarization prompts.

When using LLM summarization (`ContentMode.SUMMARY` for user/agent messages), you can customize the prompts used by providing template files or inline prompts.

**Template Resolution Hierarchy:**
1. **Project templates** - `<project>/.graphiti/auto-tracking/templates/{template}.md`
2. **Global templates** - `~/.graphiti/auto-tracking/templates/{template}.md`
3. **Built-in templates** - Packaged with Graphiti (default prompts)
4. **Inline prompts** - Pass prompt string directly (no .md extension)

**Default Templates:**

Three built-in templates are provided and automatically created in `~/.graphiti/auto-tracking/templates/` on first run:
- `default-tool-content.md` - For tool result summarization
- `default-user-messages.md` - For user message summarization
- `default-agent-messages.md` - For agent response summarization

**Template Variables:**
- `{content}` - The message content to summarize
- `{context}` - Optional context (e.g., "user message", "tool name")

**Example Custom Template:**

Create `~/.graphiti/auto-tracking/templates/custom-user-summary.md`:
```markdown
Summarize this user request concisely, focusing on intent and key requirements.

**User request:**
{content}

**Context:** {context}

**Summary (1-2 sentences):**
```

**Using Templates:**

```python
from graphiti_core.session_tracking.message_summarizer import MessageSummarizer

# Use built-in template (by filename)
summarizer = MessageSummarizer(llm_client)
summary = await summarizer.summarize(
    content="Long message here...",
    template="default-user-messages.md"
)

# Use custom template (from ~/.graphiti/auto-tracking/templates/)
summary = await summarizer.summarize(
    content="Long message here...",
    template="custom-user-summary.md"
)

# Use inline prompt (no .md extension)
summary = await summarizer.summarize(
    content="Long message here...",
    template="Summarize concisely: {content}"
)

# Use absolute path
summary = await summarizer.summarize(
    content="Long message here...",
    template="/path/to/custom-template.md"
)
```

**Template Caching:**
- Templates are resolved once and cached for the session
- Reduces disk I/O for repeated summarizations
- Cache is cleared when session changes

**Benefits:**
- **Customizable**: Tailor summarization style to your needs
- **Hierarchical**: Override built-in templates without modifying code
- **Flexible**: Use file-based templates or inline prompts
- **Efficient**: Template resolution is cached to minimize overhead

### Rolling Retention (keep_length_days)

**New in v1.1.0** - Control how long sessions are retained in the knowledge graph.

**Configuration:**
```json
{
  "session_tracking": {
    "keep_length_days": 90  // Retain last 90 days only
  }
}
```

**Behavior:**
- `null` (default): Keep all sessions indefinitely
- `90`: Retain only sessions from last 90 days
- Older sessions are automatically pruned during indexing

**Cost Comparison (50 sessions/month):**

| Retention Period | Total Sessions Stored | Neo4j Storage | Monthly API Cost | Total Monthly Cost |
|------------------|----------------------|---------------|------------------|--------------------|
| 30 days | ~50 | ~100 MB | ~$8.50 | ~$8.50 |
| 90 days | ~150 | ~300 MB | ~$8.50 | ~$8.50 |
| 180 days | ~300 | ~600 MB | ~$8.50 | ~$8.50 |
| Unlimited (null) | 500+ | 1+ GB | ~$8.50 | ~$8.50+ |

**Notes:**
- API costs are for indexing NEW sessions (constant per month)
- Storage costs increase with unlimited retention
- Query performance degrades with large graphs (1000+ episodes)
- Recommended: 90-180 days for optimal cost/performance balance

**Use Cases:**
- **30 days**: Short-term projects, privacy-focused
- **90 days**: Standard development work (recommended)
- **180 days**: Long-running projects with historical context needs
- **Unlimited**: Archive/research purposes (monitor storage costs)

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

### CLI Commands

Manage session tracking configuration via the command line:

**Enable session tracking:**
```bash
graphiti-mcp-session-tracking enable
```

**Disable session tracking:**
```bash
graphiti-mcp-session-tracking disable
```

**Check status:**
```bash
graphiti-mcp-session-tracking status
```

The CLI commands automatically update your `graphiti.config.json` file (project or global). Changes take effect on the next MCP server restart.

**Manual configuration:**
```json
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
    "inactivity_timeout": 900,
    "check_interval": 60,
    "auto_summarize": false,
    "keep_length_days": 7
  }
}
```

**High-Volume Environment** (faster session closure, more frequent checks):
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": "~/.claude/projects/active",
    "inactivity_timeout": 300,
    "check_interval": 30,
    "keep_length_days": 7
  }
}
```

**Low-Resource System** (longer timeout, less frequent checks):
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": "~/.claude/projects",
    "inactivity_timeout": 1800,
    "check_interval": 120,
    "keep_length_days": 7
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

### Session Tracking Resilience

**New in v1.0.0** - Handles LLM unavailability during session summarization.

When LLM services are unavailable (rate limits, outages), session tracking can gracefully degrade and retry later.

```json
{
  "session_tracking": {
    "resilience": {
      "on_llm_unavailable": "STORE_RAW_AND_RETRY",
      "retry_queue": {
        "max_retries": 5,
        "retry_delays_seconds": [300, 900, 2700, 7200, 21600],
        "max_queue_size": 1000,
        "persist_to_disk": true
      },
      "notifications": {
        "on_permanent_failure": true,
        "notification_method": "log",
        "webhook_url": null
      }
    }
  }
}
```

**Resilience Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `on_llm_unavailable` | str | `"STORE_RAW_AND_RETRY"` | Action when LLM unavailable (see modes below) |
| `retry_queue` | object | See below | Retry queue configuration |
| `notifications` | object | See below | Failure notification settings |

**LLM Unavailable Modes:**

| Mode | Behavior |
|------|----------|
| `STORE_RAW_AND_RETRY` | Store raw session, queue for LLM processing later (default, recommended) |
| `STORE_RAW_ONLY` | Store raw session without queueing for retry |
| `FAIL` | Fail immediately, do not store |

**Retry Queue Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_retries` | int | `5` | Maximum retry attempts per session |
| `retry_delays_seconds` | list | `[300, 900, ...]` | Delay between retries (exponential backoff) |
| `max_queue_size` | int | `1000` | Maximum sessions in retry queue |
| `persist_to_disk` | bool | `true` | Persist queue across server restarts |

**Notification Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `on_permanent_failure` | bool | `true` | Notify on permanent failures |
| `notification_method` | str | `"log"` | Notification method: "log" or "webhook" |
| `webhook_url` | str\|null | `null` | Webhook URL for notifications (if method is "webhook") |

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

## Validating Configuration

### Configuration Validator

Graphiti includes a configuration validator tool to catch errors before runtime:

```bash
# Validate default config file
python -m mcp_server.config_validator

# Validate specific file
python -m mcp_server.config_validator ~/.graphiti/graphiti.config.json

# Validation levels
python -m mcp_server.config_validator --level syntax   # Fast: JSON syntax only
python -m mcp_server.config_validator --level schema   # Moderate: Field names and types
python -m mcp_server.config_validator --level semantic # Thorough: URI format, paths exist
python -m mcp_server.config_validator --level full     # Complete: All checks (default)

# Skip specific checks
python -m mcp_server.config_validator --no-path-check  # Don't verify paths exist
python -m mcp_server.config_validator --no-env-check   # Don't verify env vars set

# JSON output (for CI/CD)
python -m mcp_server.config_validator --json
```

### Validation Checks

The validator performs four levels of validation:

1. **Syntax**: Valid JSON format, no trailing commas
2. **Schema**: Field names match Pydantic models, correct types
3. **Semantic**: URIs well-formed, paths exist (optional), env vars set (optional)
4. **Cross-field**: Database backend matches config, LLM provider has API key

### Example Output

**Valid config:**
```
[OK] Configuration valid: graphiti.config.json

Schema: graphiti-config v1.0.0
Database: neo4j (bolt://localhost:7687)
LLM: openai (gpt-4.1-mini)
Session Tracking: disabled

No issues found.
```

**Invalid config:**
```
[ERROR] Configuration invalid: graphiti.config.json

Issues found:

[ERROR] session_tracking.watch_directories: Extra inputs are not permitted
  → Did you mean 'watch_path'?

[WARNING] database.neo4j.password_env: Environment variable NEO4J_PASSWORD not set
  → Set environment variable: export NEO4J_PASSWORD='your-password'

Summary: 1 error, 1 warning
```

### IDE Support

The `graphiti.config.schema.json` file enables autocomplete and validation in IDEs:

```json
{
  "$schema": "./graphiti.config.schema.json",
  "version": "1.0.0",
  ...
}
```

---

## Additional Resources

- [Unified Config Implementation Plan](implementation/plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md)
- [Memory Filter Implementation Plan](implementation/plans/IMPLEMENTATION_PLAN_LLM_FILTER.md)
- [Migration Guide](implementation/guides/MIGRATION_GUIDE.md)
- [Quick Reference](implementation/guides/UNIFIED_CONFIG_SUMMARY.md)

---

**Last Updated:** 2025-11-27
**Version:** 3.0 (Added LLM Resilience Configuration, MCP Tools Configuration)
