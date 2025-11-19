# Graphiti Architecture: Session Tracking System

Comprehensive architectural overview of Graphiti's session tracking and memory management system.

**Version**: v1.0.0
**Last Updated**: 2025-11-18

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

- **Automatic Session Detection**: Watches Claude Code session directory for new/updated files
- **Smart Filtering**: Reduces token usage by 35-70% through intelligent content filtering
- **Knowledge Graph Integration**: Indexes sessions as episodes in Neo4j for semantic search
- **Platform-Agnostic**: Handles Windows, Unix, and WSL path formats
- **Runtime Control**: Enable/disable tracking via MCP tools or CLI
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
│  │  │   Watcher    │  │    Parser    │  │    Filter    │   │  │
│  │  │              │  │              │  │              │   │  │
│  │  │ Monitors:    │→ │ Parses:      │→ │ Reduces:     │   │  │
│  │  │ .jsonl files │  │ JSONL to     │  │ Tokens by    │   │  │
│  │  │              │  │ Messages     │  │ 35-70%       │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  │         │                  │                  │          │  │
│  │         └──────────────────┴──────────────────┘          │  │
│  │                            │                             │  │
│  │                   ┌────────▼────────┐                    │  │
│  │                   │ Session Manager │                    │  │
│  │                   │                 │                    │  │
│  │                   │ Lifecycle Mgmt  │                    │  │
│  │                   │ Inactivity      │                    │  │
│  │                   │ Detection       │                    │  │
│  │                   └────────┬────────┘                    │  │
│  │                            │                             │  │
│  │                   ┌────────▼────────┐                    │  │
│  │                   │    Indexer      │                    │  │
│  │                   │                 │                    │  │
│  │                   │ Add Episode to  │                    │  │
│  │                   │ Knowledge Graph │                    │  │
│  │                   └────────┬────────┘                    │  │
│  └────────────────────────────┼──────────────────────────────┘  │
│                                │                                │
│  ┌─────────────────────────────▼──────────────────────────┐    │
│  │              Graphiti Core                             │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │           Knowledge Graph (Neo4j)                │  │    │
│  │  │                                                  │  │    │
│  │  │  Episodes → Entities → Relationships → Facts    │  │    │
│  │  │                                                  │  │    │
│  │  │  LLM-powered entity extraction & summarization  │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

                              ▲
                              │
                    ┌─────────┴─────────┐
                    │   MCP Tools       │
                    │                   │
                    │ session_tracking_ │
                    │ start/stop/status │
                    └───────────────────┘
```

---

## Data Flow

### 1. Session Detection Flow

```
User creates Claude Code session
        │
        ▼
Claude Code writes to ~/.claude-code/sessions/{uuid}.jsonl
        │
        ▼
SessionWatcher detects file change (watchdog library)
        │
        ▼
SessionManager creates/updates Session object
        │
        ▼
Parser incrementally reads new lines (from last offset)
        │
        ▼
ConversationContext updated with new messages
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

### 3. Indexing Flow

```
ConversationContext (filtered)
        │
        ▼
SessionIndexer.index_session() [async]
        │
        ├─→ Format as episode text
        ├─→ Add metadata (session_id, timestamp, files_modified)
        └─→ Generate group_id (project-based)
        │
        ▼
Graphiti.add_episode()
        │
        ├─→ LLM extracts entities (User, Agent, MCP Tools, Files)
        ├─→ LLM identifies relationships (used, modified, created)
        └─→ Store in Neo4j knowledge graph
        │
        ▼
Episode indexed, searchable via search_memory_nodes/facts
```

### 4. Inactivity Detection Flow

```
Session file: No changes for 5 minutes
        │
        ▼
SessionManager.check_inactivity()
        │
        ▼
Session marked as inactive
        │
        ▼
on_session_closed callback triggered
        │
        ├─→ Filter conversation
        ├─→ Index to Graphiti
        └─→ Remove from active sessions
        │
        ▼
Session complete (available in knowledge graph)
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

**watcher.py** - File system monitoring
- `SessionWatcher`: Watches session directory for changes
- Uses `watchdog` library for efficient file monitoring
- Debounces rapid changes (5-second window)
- Cross-platform (Windows, macOS, Linux)

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

**MCP Tools**:
- `session_tracking_start()`: Enable tracking (force override or respect config)
- `session_tracking_stop()`: Disable tracking for current client
- `session_tracking_status()`: Get comprehensive status (config, runtime, sessions)

**Runtime State Management**:
- `runtime_session_tracking_state` (dict): Per-client enable/disable state
- Overrides global configuration when set
- Cleared on client disconnect

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

**Episode Structure**:
```cypher
(:Episode {
  uuid: "...",
  name: "Session 2025-11-18",
  content: "User: ...\nAgent: ...\nTools used: ...",
  source: "session_tracking",
  group_id: "hostname__project_hash",
  created_at: "2025-11-18T12:34:56Z"
})
```

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
async def session_tracking_start(force: bool = False) -> str:
    """Enable session tracking"""
    # Implementation
    return json.dumps({"status": "enabled", ...})
```

**Tool Response Format**:
```json
{
  "status": "enabled|disabled",
  "message": "Human-readable message",
  "config": {...},  // Optional configuration details
  "active_sessions": 2  // Optional session count
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
```

**Characteristics**:
- Session tracking enabled by default
- Project-level group_id isolation
- Single user, multiple projects

### Multi-User (Enterprise)

```
Shared Neo4j Database (Cloud)
        ▲
        │
   ┌────┴────┐
   │         │
User A      User B
├── Claude Code    ├── Claude Code
├── Graphiti MCP   ├── Graphiti MCP
└── group_id=A     └── group_id=B
```

**Characteristics**:
- Shared knowledge graph (all episodes)
- group_id isolation per user/project
- Search can span groups (optional)

---

## Related Documentation

- [API Reference](API_REFERENCE.md) - Python API
- [CLI Reference](CLI_REFERENCE.md) - Command-line interface
- [Configuration](../CONFIGURATION.md) - Config schema
- [MCP Tools](MCP_TOOLS.md) - MCP tool reference
- [Migration Guide](../claude-mcp-installer/instance/SESSION_TRACKING_MIGRATION.md)
