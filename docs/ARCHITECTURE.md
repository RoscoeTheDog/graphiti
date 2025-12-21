# Graphiti Architecture: Session Tracking System

Comprehensive architectural overview of Graphiti's session tracking and memory management system.

**Version**: v2.0.0
**Last Updated**: 2025-12-20

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Module Descriptions](#module-descriptions)
5. [Integration Points](#integration-points)
6. [Performance & Scalability](#performance--scalability)
7. [Security](#security)

---

## System Overview

### Purpose

Graphiti's session tracking system automatically captures Claude Code sessions, filters content for optimal token efficiency, and indexes them into a knowledge graph for cross-session memory and context retrieval.

### Key Features

- **Turn-Based Indexing**: Automatically indexes conversation turns when role transitions occur (user→assistant)
- **Smart Filtering**: Reduces token usage by 35-70% through intelligent content filtering
- **Knowledge Graph Integration**: Indexes sessions as episodes in Neo4j for semantic search
- **Global Session Tracking**: Single global knowledge graph with namespace tagging for cross-project learning
- **Platform-Agnostic**: Handles Windows, Unix, and WSL path formats
- **Configuration-Driven Control**: Enable/disable tracking via graphiti.config.json
- **Opt-Out Model**: Enabled by default for seamless out-of-box experience

### Architecture Principles

1. **Separation of Concerns**: Parse, filter, index as distinct stages
2. **Async-First**: All I/O operations are asynchronous
3. **Graceful Degradation**: Failures in one component don't break others
4. **Configuration-Driven**: All behavior configurable via graphiti.config.json
5. **Cost-Conscious**: Token reduction and LLM usage optimization built-in

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Graphiti MCP Server                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Session Tracking Subsystem                   │  │
│  │                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │Turn Detector │  │    Parser    │  │    Filter    │   │  │
│  │  │              │  │              │  │              │   │  │
│  │  │ Detects:     │→ │ Parses:      │→ │ Reduces:     │   │  │
│  │  │ Role         │  │ JSONL to     │  │ Tokens by    │   │  │
│  │  │ Transitions  │  │ Messages     │  │ 35-70%       │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  │         │                  │                  │          │  │
│  │         └──────────────────┴──────────────────┘          │  │
│  │                            │                             │  │
│  │                   ┌────────▼────────┐                    │  │
│  │                   │ Preprocessor    │                    │  │
│  │                   │                 │                    │  │
│  │                   │ Builds Context  │                    │  │
│  │                   │ Single-Pass LLM │                    │  │
│  │                   └────────┬────────┘                    │  │
│  │                            │                             │  │
│  │                   ┌────────▼────────┐                    │  │
│  │                   │    Indexer      │                    │  │
│  │                   │                 │                    │  │
│  │                   │ Graphiti        │                    │  │
│  │                   │ add_episode()   │                    │  │
│  │                   └────────┬────────┘                    │  │
│  └────────────────────────────┼──────────────────────────────┘  │
│                                │                                │
│  ┌─────────────────────────────▼──────────────────────────┐    │
│  │              Graphiti Core                             │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │    Global Knowledge Graph (Neo4j)                │  │    │
│  │  │                                                  │  │    │
│  │  │  group_id: hostname__global                     │  │    │
│  │  │  metadata: project_namespace                    │  │    │
│  │  │                                                  │  │    │
│  │  │  Episodes → Entities → Relationships → Facts    │  │    │
│  │  │                                                  │  │    │
│  │  │  LLM-powered entity extraction (single-pass)    │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

                              ▲
                              │
                    ┌─────────┴─────────┐
                    │   MCP Tools       │
                    │                   │
                    │ session_tracking_ │
                    │ status/health     │
                    └───────────────────┘
```

---

## Data Flow

### 1. Turn Detection Flow

```
User sends message to Claude Code
        │
        ▼
Claude Code writes to ~/.claude-code/sessions/{uuid}.jsonl
        │
        ▼
Turn Detector monitors role transitions (user→assistant)
        │
        ▼
When assistant turn completes, trigger indexing
        │
        ▼
Parser reads turn-pair from JSONL (user + assistant messages)
        │
        ▼
ConversationContext built for this turn
```

### 2. Filtering Flow

```
ConversationContext (raw)
        │
        ▼
Filter.filter_conversation() [async]
        │
        ├─→ User messages: Keep FULL (default)
        ├─→ Agent messages: Keep FULL (default)
        ├─→ Tool calls: SUMMARY (1-line)
        └─→ Tool results: SUMMARY (1-line)
        │
        ▼
Optional: MessageSummarizer for LLM-based summarization
        │
        ▼
ConversationContext (filtered, 35-70% smaller)
```

### 3. Indexing Flow (Single-Pass)

```
ConversationContext (filtered)
        │
        ▼
Preprocessor builds context with custom_prompt
        │
        ├─→ Format as episode text
        ├─→ Add metadata (session_id, timestamp, files_modified, project_namespace)
        ├─→ Inject preprocessing prompt into custom_prompt field
        └─→ Generate global group_id (hostname__global)
        │
        ▼
Graphiti.add_episode() with custom_prompt
        │
        ├─→ Single LLM pass: preprocessing + entity extraction
        ├─→ Extract entities (User, Agent, MCP Tools, Files)
        ├─→ Identify relationships (used, modified, created)
        └─→ Store in Neo4j global knowledge graph
        │
        ▼
Episode indexed with namespace tag, searchable via search_memory_nodes/facts
```

### 4. Turn Completion Flow

```
Assistant completes response
        │
        ▼
Turn-pair complete (user + assistant messages)
        │
        ▼
Trigger indexing pipeline
        │
        ├─→ Filter turn content
        ├─→ Build preprocessed context
        └─→ Index to Graphiti (single-pass LLM)
        │
        ▼
Turn indexed and available in global knowledge graph
```

---

## Module Descriptions

### Core Modules

#### `graphiti_core/session_tracking/`

**types.py** - Type definitions
- `MessageRole` (enum): USER, ASSISTANT, SYSTEM
- `SessionMessage` (dataclass): Individual message with content, role, tool calls
- `ConversationContext` (dataclass): Full session context with messages and metadata
- `SessionMetadata` (dataclass): Session info (ID, timestamps, tokens, project path)

**parser.py** - JSONL session file parsing
- `JSONLParser`: Reads Claude Code session files
- Incremental parsing with offset tracking (resume from last byte)
- Handles malformed JSON lines gracefully
- Extracts MCP tool calls and file modifications

**path_resolver.py** - Cross-platform path handling
- `PathResolver`: Normalizes Windows/Unix/WSL paths
- Generates stable project hashes for group_id
- Discovers session files in Claude Code directory
- **Critical**: All paths normalized to UNIX format for hashing, returned in native OS format

**filter.py** - Token reduction filtering
- `SessionFilter`: Filters messages based on configuration
- Preserves user/agent messages (default)
- Summarizes tool results (1-line format)
- Async support for LLM-based summarization

**filter_config.py** - Filtering configuration
- `ContentMode` (enum): FULL, SUMMARY, OMIT
- `FilterConfig` (dataclass): Per-message-type filtering rules
- Presets: default, conservative, maximum, aggressive

**message_summarizer.py** - LLM-based summarization (opt-in)
- `MessageSummarizer`: Summarizes user/agent messages via LLM
- In-memory cache (SHA256 content hashing)
- Graceful fallback to FULL mode on errors
- Cache statistics tracking

**watcher.py** - File system monitoring (DEPRECATED in v2.0)
- `SessionWatcher`: Previously watched session directory for changes
- **Note**: File watching replaced by turn-based detection in v2.0
- Legacy code maintained for backward compatibility
- New implementations should use turn detection instead

**session_manager.py** - Session lifecycle management
- `SessionManager`: Coordinates watcher, parser, filter, indexer
- Tracks active sessions (dict of session_id → Session)
- Inactivity detection (configurable timeout)
- on_session_closed callback for indexing

**indexer.py** - Knowledge graph integration
- `SessionIndexer`: Adds sessions to Graphiti knowledge graph
- Direct episode indexing (no intermediate summarization)
- Generates group_id from project path hash
- Formats messages with metadata

---

### MCP Server Integration

#### `mcp_server/graphiti_mcp_server.py`

**Session Tracking Initialization**:
```python
async def initialize_session_tracking(config: GraphitiConfig, graphiti: Graphiti):
    """Initialize session tracking subsystem"""
    # Create components
    path_resolver = PathResolver()
    indexer = SessionIndexer(graphiti)
    filter = SessionFilter(config.session_tracking.filter)

    # Start session manager
    manager = SessionManager(
        watch_path=config.session_tracking.watch_path,
        graphiti_client=graphiti,
        on_session_closed=lambda sid, ctx: index_session(sid, ctx)
    )
    await manager.start()
    return manager
```

**MCP Tools** (read-only monitoring):
- `session_tracking_status()`: Get comprehensive status (config, sessions)
- `session_tracking_health()`: Health diagnostics and metrics
- `get_failed_episodes()`: View retry queue status

**Configuration-Based Control**:
- Session tracking is enabled/disabled via `graphiti.config.json`
- No runtime override capability (consistent behavior)
- Changes require MCP server restart

---

### Configuration System

#### `mcp_server/unified_config.py`

**Configuration Hierarchy**:
1. Explicit path (--config argument)
2. Project-level: `./graphiti.config.json`
3. Global: `~/.graphiti/graphiti.config.json`

**SessionTrackingConfig**:
```python
@dataclass
class SessionTrackingConfig:
    enabled: bool = True  # Opt-out model (default enabled)
    watch_path: str = "~/.claude-code/sessions"
    check_interval: int = 5  # seconds
    inactivity_timeout: int = 300  # seconds
    filter: FilterConfig = field(default_factory=FilterConfig.default)
```

**Validation**:
- Pydantic models for type safety
- `ConfigValidator` for multi-level validation (syntax, schema, semantic, cross-field)
- Field name typo detection with suggestions

---

## Integration Points

### Claude Code Integration

**Session File Location**: `~/.claude-code/sessions/{uuid}.jsonl`

**Session File Format**:
```jsonl
{"type":"input","input":{"type":"command","command":"User message"}}
{"type":"output","output":{"type":"text","text":"Agent response"}}
{"type":"output","output":{"type":"tool_use","name":"Read","input":{"file_path":"..."}}}
{"type":"output","output":{"type":"tool_result","tool_use_id":"...","content":"..."}}
```

**Incremental Parsing**:
- Session manager tracks last offset for each session
- Only new lines parsed on file updates
- Efficient handling of long-running sessions

---

### Neo4j Knowledge Graph

**Episode Structure** (Global Scope with Namespace Tagging):
```cypher
(:Episode {
  uuid: "...",
  name: "Session 2025-11-18",
  content: "User: ...\nAgent: ...\nTools used: ...",
  source: "session_tracking",
  group_id: "hostname__global",
  project_namespace: "/path/to/project",
  created_at: "2025-11-18T12:34:56Z"
})
```

**Key Design**:
- **group_id**: Single global identifier per machine (`hostname__global`)
- **project_namespace**: Metadata field for provenance and optional filtering
- **Cross-project learning**: All episodes share global graph for knowledge sharing
- **Filterable context**: Search can be scoped to specific namespaces if needed

**Entity Extraction** (automatic via Graphiti LLM):
- User actions
- Agent responses
- MCP tools used
- Files modified
- Concepts discussed

**Relationships**:
- `(User)-[:REQUESTED]->(Feature)`
- `(Agent)-[:USED]->(MCP_Tool)`
- `(Session)-[:MODIFIED]->(File)`

---

### MCP Protocol

**Tool Registration**:
```python
@mcp.tool()
async def session_tracking_status(session_id: str | None = None) -> str:
    """Get session tracking status and configuration"""
    # Implementation
    return json.dumps({"status": "success", "enabled": True, ...})
```

**Tool Response Format**:
```json
{
  "status": "success|error",
  "enabled": true,
  "global_config": {...},  // Configuration details
  "session_manager": {...}  // Runtime status
}
```

---

## Performance & Scalability

### Token Reduction

**Default Configuration** (~35% reduction):
- User messages: FULL (no filtering)
- Agent messages: FULL (no filtering)
- Tool calls: SUMMARY (1-line: "Read(file.py)")
- Tool results: SUMMARY (1-line: "Read 150 lines from file.py")

**Aggressive Configuration** (~70% reduction):
- User messages: SUMMARY (LLM summarization)
- Agent messages: SUMMARY (LLM summarization)
- Tool calls: SUMMARY (1-line)
- Tool results: OMIT (remove entirely)

### Memory Usage

**Session Manager**:
- Active sessions: ~1-5 KB per session in memory
- Completed sessions: Removed from memory after indexing
- Incremental parsing: Only new lines loaded

**Parser**:
- Offset tracking: 8 bytes per session (int64)
- Message buffer: ~10-100 KB per active session
- No full-file loading (streaming parser)

### CPU Overhead

**File Watcher**:
- <1% CPU (watchdog library uses OS-level notifications)
- Debouncing reduces unnecessary processing

**Parsing**:
- ~10ms per 100 lines of JSONL
- Async I/O prevents blocking

**Filtering**:
- ~5ms per 1000 messages (summary mode)
- LLM summarization: ~500ms per message (opt-in only)

### Cost Optimization

**Default Configuration** ($0.17/session):
- Filtering: $0 (no LLM calls)
- Graphiti indexing: ~$0.17 (gpt-4o-mini entity extraction)

**With LLM Summarization** ($0.27-0.67/session):
- Message summarization: ~$0.10-0.50 (depends on message count)
- Graphiti indexing: ~$0.17

**Cost Control**:
- Caching prevents re-summarization (95% hit rate in practice)
- Configurable max_length reduces LLM tokens
- Opt-in model (disabled by default)

---

## Security

### Credential Detection

**Session Filter**:
- Scans for API keys, passwords, tokens
- Regex patterns: `api[_-]?key`, `secret`, `password`, `bearer`, `sk-`
- Warns on detection (logs to stderr)

**File Export**:
- Validates export paths (no path traversal)
- Checks for credentials before writing
- Obfuscates detected credentials: `sk-***REDACTED***`

### Path Validation

**PathResolver**:
- Blocks `..` patterns (path traversal)
- Validates absolute paths only
- Rejects system directories (/etc, /sys, /proc)

### Configuration Security

**Sensitive Fields**:
- `neo4j_password`: Loaded from environment variable
- `llm_api_key`: Loaded from environment variable
- Never logged or exposed in MCP tool responses

**File Permissions**:
- Config files: 644 (rw-r--r--)
- Session files: 644 (readable by user)

---

## Deployment Architectures

### Single-User (Default)

```
User's Machine
├── Claude Code (writes sessions)
├── Graphiti MCP Server (indexes sessions)
└── Neo4j Database (local or cloud)
    └── Global Knowledge Graph
        ├── group_id: hostname__global
        └── Episodes tagged with project_namespace
```

**Characteristics**:
- Session tracking enabled by default
- Global knowledge graph with namespace tagging
- Cross-project learning enabled
- Single user, multiple projects share knowledge

### Multi-User (Enterprise)

```
Shared Neo4j Database (Cloud)
        ▲
        │
   ┌────┴────┐
   │         │
User A      User B
├── Claude Code           ├── Claude Code
├── Graphiti MCP          ├── Graphiti MCP
└── group_id=hostA__global └── group_id=hostB__global
    ├── namespace=projectA1   ├── namespace=projectB1
    └── namespace=projectA2   └── namespace=projectB2
```

**Characteristics**:
- Shared knowledge graph (all episodes)
- Per-machine global group_id (hostA__global, hostB__global)
- Project namespace tagging for provenance
- Cross-project learning within each user's machine
- Optional namespace filtering for focused search

---

## Daemon Architecture

### Overview

Graphiti MCP Server supports a **platform-agnostic daemon architecture** for persistent background operation with unified HTTP/JSON communication.

### Architecture Models

#### Current: Per-Session Architecture (stdio)

```
┌─────────────────┐     stdio      ┌──────────────────────┐
│ Claude Code #1  │ ──────────────►│ graphiti_mcp (pid 1) │
└─────────────────┘                └──────────────────────┘

┌─────────────────┐     stdio      ┌──────────────────────┐
│ Claude Code #2  │ ──────────────►│ graphiti_mcp (pid 2) │
└─────────────────┘                └──────────────────────┘
```

**Characteristics**:
- Each client spawns separate MCP server process
- stdio-based communication
- No shared state between sessions
- Resource overhead (multiple Neo4j connections)

#### Future: Daemon Architecture (HTTP)

```
┌─────────────────┐
│ Claude Code #1  │─────┐
└─────────────────┘     │
                        │  HTTP/JSON
┌─────────────────┐     │  :8321
│ Claude Code #2  │─────┼─────────►┌──────────────────────┐
└─────────────────┘     │          │                      │
                        │          │  Graphiti MCP Server │
┌─────────────────┐     │          │  (Daemon Service)    │
│ CLI commands    │─────┤          │                      │
└─────────────────┘     │          │  - Single Neo4j conn │
                        │          │  - Shared state      │
┌─────────────────┐     │          │  - Session tracking  │
│ Other tools     │─────┘          │                      │
└─────────────────┘                └──────────────────────┘
```

**Characteristics**:
- Single persistent daemon process
- HTTP/JSON communication (platform-agnostic)
- Many-to-one client relationships
- Shared state across all clients
- Config-driven control (`daemon.enabled`)

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Platform-Agnostic** | Single protocol works on Windows, macOS, Linux |
| **Config-Primary** | `daemon.enabled` in graphiti.config.json is THE runtime control |
| **Auto-Monitoring** | Config changes detected automatically within 5 seconds |
| **Single Daemon** | One daemon per machine to avoid state conflicts |
| **No Fallback** | No per-process spawning; daemon-only when enabled |

### Control Model

**Installation** (one-time):
```bash
graphiti-mcp daemon install
```

**Runtime Control** (config-driven):
```json
{
  "daemon": {
    "enabled": true,
    "port": 8321,
    "host": "127.0.0.1"
  }
}
```

Changes take effect automatically within 5 seconds via file polling.

### Reference

For complete daemon architecture specification, see:
- **[docs/DAEMON_ARCHITECTURE.md](DAEMON_ARCHITECTURE.md)** - Detailed design specification

---

## Related Documentation

- [API Reference](API_REFERENCE.md) - Python API
- [CLI Reference](CLI_REFERENCE.md) - Command-line interface
- [Configuration](../CONFIGURATION.md) - Config schema
- [MCP Tools](MCP_TOOLS.md) - MCP tool reference
- [Migration Guide](../claude-mcp-installer/instance/SESSION_TRACKING_MIGRATION.md)
