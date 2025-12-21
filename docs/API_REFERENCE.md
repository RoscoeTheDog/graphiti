# Graphiti API Reference

Complete API reference for Graphiti's session tracking and memory management system.

**Version**: v1.1.0
**Last Updated**: 2025-12-20

---

## Table of Contents

1. [Session Tracking API](#session-tracking-api)
2. [Turn-Based Processing API](#turn-based-processing-api)
3. [Filtering API](#filtering-api)
4. [Path Resolution API](#path-resolution-api)
5. [Configuration API](#configuration-api)
6. [MCP Tools API](#mcp-tools-api)

---

## Session Tracking API

### Core Modules

#### `graphiti_core.session_tracking.parser`

**JSONLParser** - Parse Claude Code session JSONL files

```python
from graphiti_core.session_tracking import JSONLParser

parser = JSONLParser()

# Parse entire session file
context = parser.parse_session_file("/path/to/session.jsonl")

# Incremental parsing with offset tracking
context, new_offset = parser.parse_session_file(
    "/path/to/session.jsonl",
    start_offset=1000  # Resume from byte 1000
)
```

**Methods**:
- `parse_session_file(filepath: str, start_offset: int = 0) -> Tuple[ConversationContext, int]`
  - Parses JSONL session file from given offset
  - Returns conversation context and new offset for incremental parsing
  - Automatically handles malformed JSON lines

**Returns**: `ConversationContext`
```python
@dataclass
class ConversationContext:
    messages: List[SessionMessage]      # All messages in session
    metadata: SessionMetadata           # Session metadata
    mcp_tools_used: List[str]          # MCP tools invoked
    files_modified: List[str]          # Files changed (Write/Edit)
```

---

#### `graphiti_core.session_tracking.filter`

**SessionFilter** - Filter and summarize session content

```python
from graphiti_core.session_tracking import SessionFilter, FilterConfig, ContentMode

# Create filter with default config
filter = SessionFilter()

# Create filter with custom config
config = FilterConfig(
    tool_calls=ContentMode.SUMMARY,      # Summarize tool calls
    tool_content=ContentMode.SUMMARY,    # Summarize tool results
    user_messages=ContentMode.FULL,      # Keep full user messages
    agent_messages=ContentMode.FULL      # Keep full agent messages
)
filter = SessionFilter(config=config)

# Filter conversation (async)
filtered = await filter.filter_conversation(context)
```

**Methods**:
- `filter_conversation(context: ConversationContext) -> ConversationContext` (async)
  - Filters messages based on configuration
  - Preserves user/agent messages
  - Summarizes or omits tool results
  - Returns new ConversationContext with filtered messages

**Token Reduction**: 35% (default) to 70% (aggressive)

---

#### `graphiti_core.session_tracking.indexer`

**SessionIndexer** - Index sessions to Graphiti knowledge graph

```python
from graphiti_core.session_tracking import SessionIndexer
from graphiti import Graphiti

graphiti = Graphiti(uri, user, password)
indexer = SessionIndexer(graphiti)

# Index filtered session
await indexer.index_session(
    context=filtered_context,
    group_id="my-project",
    name="Session 2025-11-18"
)
```

**Methods**:
- `index_session(context: ConversationContext, group_id: str, name: str) -> str` (async)
  - Adds session as episode to knowledge graph
  - Returns episode UUID
  - Graphiti automatically extracts entities and relationships

---

#### `graphiti_core.session_tracking.session_manager`

**SessionManager** - Lifecycle management for session tracking

```python
from graphiti_core.session_tracking import SessionManager

manager = SessionManager(
    watch_path="/path/to/.claude-code/sessions",
    graphiti_client=graphiti,
    check_interval=5,           # Check for new sessions every 5s
    inactivity_timeout=300      # Close sessions after 5min idle
)

# Start monitoring
await manager.start()

# Stop monitoring
await manager.stop()
```

**Methods**:
- `start() -> None` (async)
  - Starts file watcher and session processing
- `stop() -> None` (async)
  - Gracefully stops all sessions and watcher
- `get_active_sessions() -> List[str]`
  - Returns list of currently active session IDs

**Callbacks**:
```python
def on_session_closed(session_id: str, context: ConversationContext):
    # Called when session becomes inactive
    pass

manager = SessionManager(..., on_session_closed=on_session_closed)
```

---

## Turn-Based Processing API

### Activity Detection

#### `graphiti_core.session_tracking.activity_detector`

**ActivityDetector** - Detect turn boundaries in conversation streams

```python
from graphiti_core.session_tracking import ActivityDetector

detector = ActivityDetector()

# Detect if turn is complete (user->assistant pair)
is_turn_complete = detector.detect_turn_boundary(messages)

# Get activity metrics
activity = detector.calculate_activity_vector(context)
```

**Methods**:
- `detect_turn_boundary(messages: List[SessionMessage]) -> bool`
  - Returns True when user->assistant turn pair is complete
  - Looks for role transitions (USER -> ASSISTANT)
- `calculate_activity_vector(context: ConversationContext) -> ActivityVector`
  - Returns metrics like tool_call_count, file_modifications, bash_commands

---

### Tool Classification

#### `graphiti_core.session_tracking.tool_classifier`

**ToolClassifier** - Classify tool calls by extraction priority

```python
from graphiti_core.session_tracking import ToolClassifier, ExtractionPriority

classifier = ToolClassifier()

# Classify tool call
priority = classifier.classify_tool(tool_name, tool_args)

# Priority levels: CRITICAL, HIGH, MEDIUM, LOW
if priority == ExtractionPriority.CRITICAL:
    # File modifications, git commits
    pass
elif priority == ExtractionPriority.HIGH:
    # Code edits, test runs
    pass
```

**ExtractionPriority Enum**:
```python
class ExtractionPriority(str, Enum):
    CRITICAL = "critical"  # File Write, Edit, Git commit
    HIGH = "high"          # Code changes, test execution
    MEDIUM = "medium"      # Read operations, searches
    LOW = "low"            # Navigation, trivial operations
```

---

### Bash Analysis

#### `graphiti_core.session_tracking.bash_analyzer`

**BashAnalyzer** - Extract semantic meaning from bash commands

```python
from graphiti_core.session_tracking import BashAnalyzer

analyzer = BashAnalyzer()

# Analyze bash command
result = analyzer.analyze_command(
    command="git commit -m 'feat: add new feature'",
    output="[main abc123] feat: add new feature"
)

# Result includes:
# - command_type: git_commit
# - semantic_summary: "Committed code changes"
# - extracted_entities: ["main", "abc123"]
```

**Detected Command Types**:
- Git operations (commit, push, pull, merge)
- Package management (npm, pip, cargo)
- File operations (mkdir, rm, cp, mv)
- Build/test commands (pytest, npm test)

---

### Unified Classification

#### `graphiti_core.session_tracking.unified_classifier`

**UnifiedClassifier** - Combine tool and bash classification

```python
from graphiti_core.session_tracking import UnifiedClassifier

classifier = UnifiedClassifier()

# Classify mixed content
classification = classifier.classify_activity(
    tool_calls=tool_calls,
    bash_commands=bash_commands
)

# Returns unified priority and semantic summary
```

---

## Filtering API

### ContentMode Enum

```python
from graphiti_core.session_tracking import ContentMode

ContentMode.FULL     # Keep full content (no filtering)
ContentMode.SUMMARY  # 1-line summary (tool results or LLM summarization)
ContentMode.OMIT     # Remove entirely
```

### FilterConfig

```python
from graphiti_core.session_tracking import FilterConfig

config = FilterConfig(
    tool_calls=ContentMode.SUMMARY,      # How to handle tool calls
    tool_content=ContentMode.SUMMARY,    # How to handle tool results
    user_messages=ContentMode.FULL,      # How to handle user messages
    agent_messages=ContentMode.FULL      # How to handle agent messages
)
```

**Presets**:

```python
# Default (35% reduction)
FilterConfig.default()

# Conservative (20% reduction)
FilterConfig.conservative()

# Maximum (15% reduction)
FilterConfig.maximum()

# Aggressive (70% reduction - requires LLM)
FilterConfig.aggressive()
```

### MessageSummarizer

**LLM-based summarization** for user/agent messages (opt-in)

```python
from graphiti_core.session_tracking import MessageSummarizer

summarizer = MessageSummarizer(llm_client)

# Summarize message (async, with caching)
summary = await summarizer.summarize_message(
    content="Long message content...",
    role="user",
    max_length=100
)

# Get cache statistics
stats = summarizer.get_cache_stats()
# Returns: {"hits": 15, "misses": 5, "hit_rate": 0.75}
```

**Features**:
- In-memory cache (SHA256 content hashing)
- Graceful fallback to FULL mode on LLM errors
- Configurable max_length with truncation

---

## Path Resolution API

### PathResolver

**Platform-agnostic path normalization** (Windows/Unix/WSL)

```python
from graphiti_core.session_tracking import PathResolver

resolver = PathResolver()

# Normalize path for cross-platform consistency
unix_path = resolver.normalize_path("C:\\Users\\Admin\\project")
# Returns: "/c/Users/Admin/project"

# Calculate project hash for grouping
project_hash = resolver.get_project_hash("/c/Users/Admin/project")
# Returns: "a1b2c3d4" (8-char hash)

# Find session files
session_files = resolver.find_session_files(
    "/path/to/.claude-code/sessions"
)
# Returns: List[Path] of .jsonl files, sorted by modification time
```

**Methods**:
- `normalize_path(path: Union[str, Path]) -> str`
  - Converts to UNIX format for hashing/internal use
  - Returns native OS format for display
- `get_project_hash(project_path: str) -> str`
  - Generates stable 8-character hash for project
  - Used for group_id generation
- `find_session_files(directory: Union[str, Path]) -> List[Path]`
  - Finds all .jsonl session files in directory
  - Sorted by modification time (oldest first)

---

## Configuration API

### Unified Configuration System

**Load configuration**:

```python
from mcp_server.unified_config import load_graphiti_config

# Auto-discovery: project > global (~/.graphiti/)
config = load_graphiti_config()

# Explicit path
config = load_graphiti_config("/path/to/graphiti.config.json")
```

**Configuration Schema**:

```python
from mcp_server.unified_config import GraphitiConfig, SessionTrackingConfig
from graphiti_core.extraction_config import ExtractionConfig

config = GraphitiConfig(
    neo4j_uri="neo4j+ssc://your-aura-instance.databases.neo4j.io",
    neo4j_user="neo4j",
    neo4j_password="${NEO4J_PASSWORD}",  # From environment

    llm_provider="openai",
    llm_api_key="${OPENAI_API_KEY}",
    llm_model="gpt-4o-mini",

    session_tracking=SessionTrackingConfig(
        enabled=True,  # Default: opt-out model
        watch_path="~/.claude-code/sessions",
        check_interval=5,
        inactivity_timeout=300,
        filter=FilterConfig(
            tool_calls=ContentMode.SUMMARY,
            tool_content=ContentMode.SUMMARY,
            user_messages=ContentMode.FULL,
            agent_messages=ContentMode.FULL
        )
    ),

    extraction=ExtractionConfig(
        preprocessing_prompt="default-session-turn.md",  # Built-in template
        preprocessing_mode="prepend"  # Before reflexion hints
    )
)
```

**ExtractionConfig** - Control LLM extraction preprocessing:

```python
from graphiti_core.extraction_config import ExtractionConfig

# Default: Use built-in session turn template
config = ExtractionConfig()

# Custom template file
config = ExtractionConfig(
    preprocessing_prompt="my-custom-template.md"
)

# Inline preprocessing instructions
config = ExtractionConfig(
    preprocessing_prompt="Focus on code changes and error patterns"
)

# Disable preprocessing
config = ExtractionConfig(preprocessing_prompt=None)
```

**Fields**:
- `preprocessing_prompt: str | bool | None` - Template filename, inline prompt, or None to disable
- `preprocessing_mode: "prepend" | "append"` - Position relative to reflexion hints

**Validation**:

```python
from mcp_server.config_validator import ConfigValidator

validator = ConfigValidator()

# Validate configuration file
result = validator.validate_file(
    "graphiti.config.json",
    level="full"  # syntax, schema, semantic, cross-field
)

if result.is_valid:
    print("✅ Configuration valid")
else:
    for error in result.errors:
        print(f"❌ {error}")
```

---

## MCP Tools API

### Core Memory Tools

#### `add_memory`

**Add episodes to knowledge graph**

```python
result = await mcp_client.call_tool("add_memory", {
    "name": "Session 2025-12-20",
    "content": "Conversation content...",
    "group_id": "my-project",
    "source_type": "message"  # message, text, or json
})
```

**Parameters**:
- `name: str` - Episode name/identifier
- `content: str | dict` - Episode content (text or JSON)
- `group_id: str` - Project/group identifier for isolation
- `source_type: "message" | "text" | "json"` - Content format

---

#### `search_memory_nodes`

**Search for entities in knowledge graph**

```python
results = await mcp_client.call_tool("search_memory_nodes", {
    "query": "authentication bug fixes",
    "group_ids": ["my-project"],
    "max_nodes": 20
})
```

**Parameters**:
- `query: str` - Semantic search query
- `group_ids: List[str]` - Filter by project groups
- `max_nodes: int` - Maximum results (default: 10)

---

#### `search_memory_facts`

**Search for relationships in knowledge graph**

```python
results = await mcp_client.call_tool("search_memory_facts", {
    "query": "code review relationships",
    "group_ids": ["my-project"],
    "max_facts": 20
})
```

---

#### `get_episodes`

**Retrieve recent episodes**

```python
episodes = await mcp_client.call_tool("get_episodes", {
    "group_id": "my-project",
    "limit": 10
})
```

---

#### `delete_episode`

**Remove episode from graph**

```python
result = await mcp_client.call_tool("delete_episode", {
    "uuid": "episode-uuid-here"
})
```

---

#### `delete_entity_edge`

**Remove entity or relationship**

```python
result = await mcp_client.call_tool("delete_entity_edge", {
    "uuid": "entity-or-edge-uuid"
})
```

---

#### `clear_graph`

**Clear all data (use with caution)**

```python
result = await mcp_client.call_tool("clear_graph")
```

---

### Health Check Tools

#### `health_check`

**Check server and database connectivity**

```python
health = await mcp_client.call_tool("health_check")
```

**Response**:
```json
{
  "status": "healthy",
  "database_connected": true,
  "llm_configured": true,
  "session_tracking_enabled": true,
  "uptime_seconds": 3600
}
```

---

#### `llm_health_check`

**Check LLM provider connectivity**

```python
llm_health = await mcp_client.call_tool("llm_health_check")
```

**Response**:
```json
{
  "status": "healthy",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "response_time_ms": 250
}
```

---

### Session Tracking Tools

Exposed via MCP server for monitoring (read-only):

> **Note**: Session tracking is controlled via configuration (`graphiti.config.json`).
> MCP tools provide monitoring and diagnostics only. The `session_tracking_start` and
> `session_tracking_stop` tools were removed in v1.0.0.

#### `session_tracking_status`

**Get comprehensive status**

```python
result = await mcp_client.call_tool("session_tracking_status")
```

**Response**:
```json
{
  "global_config_enabled": true,
  "runtime_state": "enabled",
  "effective_state": "enabled",
  "active_sessions": 2,
  "session_manager": {
    "watch_path": "~/.claude-code/sessions",
    "check_interval": 5,
    "inactivity_timeout": 300
  },
  "filter_config": {
    "tool_calls": "SUMMARY",
    "tool_content": "SUMMARY",
    "user_messages": "FULL",
    "agent_messages": "FULL"
  }
}
```

---

#### `session_tracking_health`

**Get session tracking health metrics**

```python
health = await mcp_client.call_tool("session_tracking_health")
```

**Response**:
```json
{
  "status": "healthy",
  "active_sessions": 2,
  "sessions_indexed": 45,
  "last_activity": "2025-12-20T10:30:00Z"
}
```

---

#### `get_failed_episodes`

**Retrieve episodes that failed to index**

```python
failed = await mcp_client.call_tool("get_failed_episodes", {
    "group_id": "my-project",
    "limit": 10
})
```

**Response**:
```json
{
  "failed_episodes": [
    {
      "name": "Session-abc123",
      "error": "LLM timeout",
      "timestamp": "2025-12-20T09:15:00Z",
      "retry_count": 3
    }
  ],
  "total_failed": 1
}
```

---

#### `session_tracking_sync_history`

**View synchronization history**

```python
history = await mcp_client.call_tool("session_tracking_sync_history", {
    "limit": 20
})
```

**Response**:
```json
{
  "sync_events": [
    {
      "timestamp": "2025-12-20T10:00:00Z",
      "session_id": "abc123",
      "status": "success",
      "duration_ms": 2500
    }
  ]
}
```

---

## Type Reference

### SessionMessage

```python
@dataclass
class SessionMessage:
    role: MessageRole  # USER, ASSISTANT, SYSTEM
    content: str
    timestamp: Optional[datetime] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    token_usage: Optional[TokenUsage] = None
```

### ConversationContext

```python
@dataclass
class ConversationContext:
    messages: List[SessionMessage]
    metadata: SessionMetadata
    mcp_tools_used: List[str]
    files_modified: List[str]
```

### SessionMetadata

```python
@dataclass
class SessionMetadata:
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_tokens: int
    project_path: Optional[str]
```

---

## Error Handling

All session tracking functions use comprehensive error handling:

```python
import logging

logger = logging.getLogger(__name__)

try:
    context = parser.parse_session_file(filepath)
except FileNotFoundError:
    logger.error(f"Session file not found: {filepath}")
except json.JSONDecodeError as e:
    logger.warning(f"Malformed JSON line {e.lineno}: {e.msg}")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
```

**Graceful Degradation**:
- Malformed JSON lines are skipped with warnings
- Missing fields use defaults
- LLM summarization falls back to FULL mode on errors

---

## Performance

**Token Reduction** (filtering):
- Default config: ~35% reduction
- Conservative: ~20% reduction
- Maximum: ~15% reduction
- Aggressive (with LLM): ~70% reduction

**Cost** (per session):
- Filtering: $0 (no LLM calls)
- LLM summarization (opt-in): ~$0.10-0.50
- Graphiti indexing: ~$0.17 (entity extraction)
- **Total (default)**: ~$0.17/session

**Overhead**:
- Session tracking: <5% CPU/memory impact
- Incremental parsing: Resume from last offset (no re-parsing)

---

## Related Documentation

- [CLI Reference](CLI_REFERENCE.md) - Command-line interface
- [Architecture](ARCHITECTURE.md) - System design
- [MCP Tools](MCP_TOOLS.md) - MCP tool reference
- [Configuration](../CONFIGURATION.md) - Config schema
- [Migration Guide](../claude-mcp-installer/instance/SESSION_TRACKING_MIGRATION.md)
