# Conversation Buffer Implementation Analysis

## Problem Statement

**Tier 2 Context Capture**: Need to preserve conversation context (WHY decisions were made) for git operations and file deletions.

**Challenge**: Capturing conversation history is token-heavy if done naively.

## Implementation Approaches

### Approach 1: JSONL Log Parsing (Recommended for Claude Code)

**Mechanism**: Read `~/.claude/projects/{project_hash}/sessions/{session_id}.jsonl` directly from MCP server.

**Pros**:
- ✅ Zero token overhead during conversation (no agent tool calls needed)
- ✅ Complete conversation history available
- ✅ No client modification required
- ✅ Works with Claude Code's existing architecture

**Cons**:
- ❌ Tightly coupled to Claude Code JSONL format
- ❌ Won't work with other MCP clients (VS Code, etc.)
- ❌ Requires filesystem access from MCP server

**Implementation**:
```python
class ConversationBuffer:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.claude_dir = Path.home() / ".claude"

    def get_project_hash(self) -> str:
        """Compute project hash for JSONL path lookup"""
        # Claude Code uses normalized project path hash
        normalized = str(Path(self.project_root).resolve())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def get_active_session_path(self) -> Path:
        """Find most recent session JSONL file"""
        project_hash = self.get_project_hash()
        sessions_dir = self.claude_dir / "projects" / project_hash / "sessions"

        if not sessions_dir.exists():
            return None

        # Find most recent session file
        session_files = list(sessions_dir.glob("*.jsonl"))
        if not session_files:
            return None

        return max(session_files, key=lambda p: p.stat().st_mtime)

    def get_last_n_messages(self, n: int = 5) -> list[dict]:
        """Extract last N user/assistant messages (exclude tool calls)"""
        session_path = self.get_active_session_path()
        if not session_path:
            return []

        messages = []
        with open(session_path, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)

                # Only include user and assistant messages
                if entry.get("type") in ["user", "assistant"]:
                    # Exclude tool use blocks
                    content = entry.get("content", "")
                    if not self._is_tool_call(content):
                        messages.append({
                            "role": entry["type"],
                            "content": content[:500],  # Truncate for safety
                            "timestamp": entry.get("timestamp")
                        })

        # Return last N messages
        return messages[-n:]

    def _is_tool_call(self, content: str) -> bool:
        """Check if message is a tool call (heuristic)"""
        # Tool calls typically contain XML tags or specific patterns
        tool_indicators = [
            "<function_calls>",
            "mcp__",
            "Bash(",
            "Read(",
            "Edit("
        ]
        return any(indicator in content for indicator in tool_indicators)
```

### Approach 2: MCP Tool-Based Tracking (Client-Agnostic)

**Mechanism**: Agent calls `track_message(role, content)` MCP tool after each user/agent exchange.

**Pros**:
- ✅ Client-agnostic (works with any MCP client)
- ✅ Explicit control over what gets tracked
- ✅ No filesystem assumptions

**Cons**:
- ❌ Token overhead (~100-200 tokens per message pair)
- ❌ Doubles token usage if tracking full conversations
- ❌ Requires agent discipline (must call tool consistently)
- ❌ Risk of agents forgetting to call tool

**Implementation**:
```python
# MCP Server
class GraphitiMCPServer:
    def __init__(self):
        self.conversation_buffers = {}  # group_id -> deque

    @mcp_tool
    async def track_message(
        self,
        group_id: str,
        role: str,  # "user" or "assistant"
        content: str
    ):
        """Track conversation message for context capture"""
        if group_id not in self.conversation_buffers:
            self.conversation_buffers[group_id] = deque(maxlen=10)

        self.conversation_buffers[group_id].append({
            "role": role,
            "content": content[:500],  # Truncate
            "timestamp": datetime.utcnow().isoformat()
        })

        return {"status": "tracked", "buffer_size": len(self.conversation_buffers[group_id])}

# Agent usage (adds token overhead)
track_message(
    group_id="hostname__abc123",
    role="user",
    content="Wait, this won't work with serverless"
)
```

## Token Cost Analysis

### Graphiti LLM Usage During `add_episode`

**Based on Context7 docs**:

Graphiti uses LLM for:
1. **Entity Extraction** - Identifies entities in episode text
2. **Relationship Extraction** - Identifies relationships between entities
3. **Temporal Extraction** - Extracts valid_at/invalid_at dates
4. **Edge Deduplication** - Determines if edges are duplicates
5. **Community Updates** (optional) - Updates graph communities

**LLM Calls per `add_episode`**:
- Entity extraction: 1 LLM call (~1000 input tokens + episode content)
- Edge extraction: 1 LLM call (~1000 input tokens + episode content)
- Temporal extraction: 1 LLM call per edge (~500 input tokens per edge)
- Deduplication: 1 LLM call (~300 input tokens)

**Total LLM Token Cost** (rough estimate):
- Simple episode (200 tokens): ~5k input + ~500 output = ~5.5k tokens
- Complex episode (2000 tokens): ~12k input + ~2k output = ~14k tokens

**Important**: `add_memory` MCP tool **adds** episodes to graph (uses LLM), `search_memory_nodes` **queries** graph (uses embeddings, minimal LLM).

### Conversation Buffer Token Costs

**Approach 1 (JSONL Parsing)**:
- Filesystem read: 0 tokens (direct file I/O)
- Parsing JSONL: 0 tokens (local processing)
- Extracting last 5 messages: 0 tokens
- **Total overhead per session: 0 tokens** ✅

**Approach 2 (MCP Tool Tracking)**:
- Per message tracked: ~100-150 tokens (tool call overhead)
- 10 messages per session: ~1,000-1,500 tokens
- 50 messages per session: ~5,000-7,500 tokens
- **Total overhead per session: 1k-7.5k tokens** ❌

## Conversation Context Snapshot Token Usage

**When Git Operation Detected**:

1. **Extract Last 5 Messages**: ~500-1000 tokens (5 messages × 100-200 tokens each)
2. **Create Tier 2 Episode**: `add_memory` call with snapshot
   - Episode body: ~500-1000 tokens
   - Graphiti processing: ~5k tokens (entity/edge extraction)
   - **Total: ~5.5k-6k tokens**

**Frequency**: Only on git operations (rare events, maybe 1-5 per day)

**Cost Analysis**:
- GPT-4.1-mini: $0.150/1M input tokens = ~$0.0009 per git operation
- GPT-4: $2.50/1M input tokens = ~$0.015 per git operation
- Claude Sonnet 4: $3.00/1M input tokens = ~$0.018 per git operation

**Conclusion**: Conversation context snapshots are very cheap (~$0.001-$0.02 per git operation).

## Regular File Operations vs Git Operations

**Regular File Update** (source="filesystem_watch"):
```python
add_memory(
    name="src/database.py",
    episode_body=read_file("src/database.py"),  # Full file content (~2k tokens)
    source="filesystem_watch"
)
# Graphiti LLM cost: ~12k tokens
# Cost: ~$0.002-$0.04 per file update
```

**Git Bulk Operation** (source="git_bulk_update"):
```python
# 47 files × ~12k tokens = ~564k tokens
# Cost: ~$0.08-$1.69 per git operation (if we indexed all files)
# But we DON'T index these (excluded from add_memory for bulk ops)
```

**Solution**: Don't call `add_memory` for git bulk operations (Tier 3). Only create Tier 1 (metadata) and Tier 2 (conversation context).

## Recommendation: Hybrid Approach

### Primary: JSONL Parsing (Zero Token Overhead)

Use JSONL parsing for Claude Code users (majority case):

```python
class GitAwareWatcher:
    def __init__(self, project_root: str):
        self.conversation_buffer = ConversationBuffer(project_root)

    def on_git_head_change(self, event):
        # Capture git metadata (Tier 1)
        git_info = self.get_git_operation_info()
        add_memory(
            name=f"git-metadata-{batch_id}",
            episode_body=format_git_summary(git_info),
            source="git_metadata"
        )
        # Cost: ~5k tokens

        # Capture conversation context (Tier 2)
        recent_messages = self.conversation_buffer.get_last_n_messages(5)
        if recent_messages:
            add_memory(
                name=f"git-context-{batch_id}",
                episode_body=format_conversation(recent_messages),
                source="git_context"
            )
            # Cost: ~5.5k tokens

        # DO NOT call add_memory for 47 files (Tier 3)
        # Just track in pending_git_hashes for classification
```

### Fallback: Optional MCP Tool (Client-Agnostic)

Provide `track_message` tool for non-Claude Code clients, but make it optional:

```python
@mcp_tool
async def track_message(group_id: str, role: str, content: str):
    """Optional: Track conversation for context capture (non-Claude Code clients)"""
    # Implementation from Approach 2
    pass
```

**Configuration**:
```json
{
  "conversation_tracking": {
    "mode": "auto",  // "auto", "jsonl", "mcp_tool", "disabled"
    "jsonl_path": "~/.claude/projects/",
    "buffer_size": 10
  }
}
```

## Implementation Strategy

1. **Phase 1**: Implement JSONL parsing (zero token overhead)
   - Works for Claude Code users immediately
   - No agent changes needed

2. **Phase 2**: Add optional `track_message` MCP tool
   - Fallback for other clients
   - Document token costs clearly

3. **Phase 3**: Smart mode detection
   - Auto-detect Claude Code JSONL availability
   - Fall back to MCP tool if unavailable
   - Warn user about token costs

## Answer to User's Question

**Q**: Which approach is practical for token costs?

**A**: **JSONL parsing (#1) is strongly recommended**:

- Zero token overhead during conversation ✅
- Only costs ~5.5k tokens per git operation (Tier 2 snapshot) ✅
- Git operations are rare (1-5 per day) ✅
- Total cost: ~$0.001-$0.02 per git operation ✅

**MCP tool tracking (#2) costs**:
- 1k-7.5k tokens per session (tracking overhead) ❌
- Plus ~5.5k tokens per git operation ❌
- Total cost: ~$0.01-$0.30 per session ❌

**Q**: Does adding data to Graphiti consume tokens?

**A**: **Yes**, `add_memory` uses LLM for entity/edge extraction:
- Simple episode: ~5.5k tokens
- Complex episode: ~14k tokens
- **Querying** (`search_memory_nodes`) uses embeddings (minimal LLM, ~100 tokens)

**Q**: What about file tracking?

**A**: Track individual file updates normally:
- Regular file update: ~12k tokens (reasonable for 5-10 files/session)
- Git bulk operations: DON'T call `add_memory` for Tier 3 (47 files)
- Only create Tier 1 (metadata) + Tier 2 (conversation context)

## Final Recommendation

**Use JSONL parsing approach**:
1. Zero overhead for conversation tracking
2. Cheap Tier 2 snapshots (~5.5k tokens per git operation)
3. Don't index Tier 3 bulk file operations
4. Total cost: ~$0.01-$0.10 per day for typical usage

This is **99% cheaper** than MCP tool tracking while preserving all the context we need.
