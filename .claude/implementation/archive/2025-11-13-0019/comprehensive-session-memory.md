# Comprehensive Session Memory Architecture

## Vision

**Transform agent memory** from manual, sparse memories to **complete session understanding** by automatically indexing JSONL conversation logs into Graphiti's knowledge graph.

### The Power of Complete Context

**Current State**: Agents manually add memories (~5-10 per session)
- Sparse coverage
- Agents forget to document decisions
- No understanding of workflow patterns
- Limited cross-session learning

**Future State**: Complete session history in Graphiti
- Agents understand: "Last time this error occurred, we fixed it by X"
- Workflow patterns emerge: "Agent always tries approach A before B"
- Decision trees visible: "User prefers Y over Z because of serverless constraints"
- Tool usage patterns: "This bash command fails 80% of the time, try alternative first"

### Example Session Flow (Preserved in Graph)

```
User: "Fix the authentication bug"
  ↓
Agent: "I'll investigate the auth module"
  ↓
Tool: Read(src/auth.py)  [content omitted]
Tool: Grep(pattern="login")  [results omitted]
  ↓
Agent: "Found the issue - JWT expiry is set to 0. Let me fix it."
  ↓
Tool: Edit(src/auth.py)  [old/new strings omitted]
  ↓
Agent: "Fixed! JWT expiry now set to 3600 seconds."
  ↓
User: "Great, also make sure it works with Redis session store"
  ↓
Agent: "Ah, Redis session store requires different config. Let me adjust..."
```

**Graph Knowledge**:
- `JWT_BUG → CAUSED_BY → expiry=0`
- `JWT_FIX → REQUIRES → expiry=3600`
- `Redis_Session_Store → CONFLICTS_WITH → default_JWT_config`
- `Agent → WORKFLOW → Read_Then_Grep_Then_Edit`

## Three Core Challenges

### Challenge 1: JSONL Location Outside Project Boundaries

**Problem**: JSONL files are in `~/.claude/projects/{hash}/sessions/`, not project root.

**Solutions**:

**Option A: Global Tracking Configuration** (Recommended)
```json
// ~/.graphiti/tracking-config.json
{
  "global": {
    "track_session_logs": true,
    "session_log_sources": [
      {
        "type": "claude_code_jsonl",
        "base_path": "~/.claude/projects",
        "mapping": "auto"  // Auto-detect project from hash
      }
    ]
  },
  "projects": {
    "hostname__abc123": {
      "project_root": "/path/to/project",
      "session_tracking": {
        "enabled": true,
        "source": "claude_code_jsonl"
      }
    }
  }
}
```

**Option B: Symbolic Link Approach**
```bash
# Create symlink in project (gitignored)
ln -s ~/.claude/projects/{hash}/sessions .claude/sessions

# Track via normal filesystem watcher
# .gitignore: .claude/sessions/
```

**Option C: Explicit Permission Model**
```python
# User grants permission for cross-boundary access
graphiti configure-session-tracking \
  --project /path/to/project \
  --session-logs ~/.claude/projects/{hash}/sessions \
  --permission grant
```

**Recommendation**: Option A (global config with auto-mapping)
- Clean separation of concerns
- No project directory pollution
- Explicit user control

### Challenge 2: Token Cost Management

**Problem**: Full session JSONL = 200k+ tokens, Graphiti processes each episode with LLM (~5-15k tokens per episode).

**Solution: Smart Chunking + Filtering**

#### Token Optimization Strategy

**Raw JSONL**: ~200k tokens (full session with tool outputs)

**After Filtering**:
```
User message: ~200 tokens
Agent response: ~300 tokens
Tool calls (structure only): ~50 tokens
MCP calls (structure only): ~50 tokens
----------------------------------------
Per exchange: ~600 tokens
20 exchanges: ~12k tokens (94% reduction!)
```

**Chunking Strategy**:
- **Chunk by conversation turn** (user → agent exchange)
- **Each chunk = 1 episode** in Graphiti
- Average chunk: ~600-800 tokens
- Graphiti processing: ~5.5k tokens per chunk
- 20 chunks per session: ~110k tokens total

**Cost Analysis**:
- Per session: ~110k tokens
- GPT-4.1-mini: ~$0.17 per session
- GPT-4: ~$2.75 per session
- Claude Sonnet: ~$3.30 per session

**Incremental Indexing**:
```python
# Don't reindex entire session every time
# Track last indexed position
{
  "session_id": "abc123",
  "last_indexed_line": 547,
  "last_indexed_timestamp": "2025-11-12T15:30:00Z"
}

# Only index new lines since last position
new_lines = read_jsonl_from_line(548)
```

### Challenge 3: Content Filtering (Preserve Structure, Omit Details)

**Problem**: Tool outputs can be massive (10k+ lines of logs, full file contents, etc.)

**Solution: Structural Preservation**

#### JSONL Filtering Rules

**KEEP (Full Content)**:
- User messages
- Agent responses (text explanations)
- Agent reasoning (internal thoughts)

**KEEP (Structure Only)**:
- Tool calls (name + parameters, omit results)
- MCP calls (tool name + arguments, omit outputs)
- Errors (error type + message, omit stack traces)

**OMIT (Too Verbose)**:
- Tool call results (file contents, command outputs)
- MCP tool outputs (search results, code snippets)
- Stack traces (keep first line only)

#### Example Filtering

**Raw JSONL Entry**:
```json
{
  "type": "tool_use",
  "tool": "Read",
  "input": {"file_path": "/project/src/auth.py"},
  "output": {
    "content": "import jwt\nimport redis\n... [2000 lines] ..."
  },
  "timestamp": "2025-11-12T15:30:00Z"
}
```

**Filtered for Graphiti**:
```json
{
  "type": "tool_use",
  "tool": "Read",
  "input": {"file_path": "/project/src/auth.py"},
  "output_summary": "File read successfully (2134 lines, 48KB)",
  "timestamp": "2025-11-12T15:30:00Z"
}
```

**Episode Body**:
```
Agent: I'll investigate the auth module
Action: Read(file_path="/project/src/auth.py") → Success (2134 lines)
Agent: Found the issue - JWT expiry is set to 0
```

## Implementation Architecture

### Component: JSONLSessionTracker

```python
class JSONLSessionTracker:
    def __init__(self, graphiti: Graphiti, config: TrackingConfig):
        self.graphiti = graphiti
        self.config = config
        self.session_states = {}  # Track indexing progress

    async def start_tracking(self, project_root: str):
        """Initialize session tracking for project"""
        # 1. Resolve JSONL path from project root
        jsonl_dir = self._resolve_jsonl_path(project_root)

        # 2. Find active session file
        active_session = self._get_active_session(jsonl_dir)

        # 3. Start watchdog on session file
        observer = Observer()
        handler = JSONLFileHandler(
            session_path=active_session,
            on_new_content=self.process_new_content
        )
        observer.schedule(handler, path=str(active_session.parent))
        observer.start()

    def _resolve_jsonl_path(self, project_root: str) -> Path:
        """Map project root to JSONL sessions directory"""
        # Compute project hash (Claude Code style)
        project_hash = self._compute_project_hash(project_root)

        # Return JSONL sessions path
        return Path.home() / ".claude" / "projects" / project_hash / "sessions"

    def _compute_project_hash(self, project_root: str) -> str:
        """Compute Claude Code project hash"""
        normalized = str(Path(project_root).resolve())
        # Claude Code normalizes paths to Unix format
        if sys.platform == "win32":
            normalized = normalized.replace("\\", "/")
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def process_new_content(self, new_lines: list[str]):
        """Process new JSONL lines incrementally"""
        # 1. Parse JSONL lines
        entries = [json.loads(line) for line in new_lines]

        # 2. Group into conversation chunks
        chunks = self._chunk_by_exchange(entries)

        # 3. Filter each chunk
        for chunk in chunks:
            filtered = self._filter_chunk(chunk)

            # 4. Create episode in Graphiti
            await self.graphiti.add_episode(
                name=f"session-{chunk['session_id']}-{chunk['chunk_id']}",
                episode_body=self._format_chunk(filtered),
                source="session_log",
                group_id=chunk['group_id']
            )

    def _chunk_by_exchange(self, entries: list[dict]) -> list[dict]:
        """Group entries into user→agent exchanges"""
        chunks = []
        current_chunk = []

        for entry in entries:
            current_chunk.append(entry)

            # Complete chunk on agent final response
            if entry.get("type") == "assistant" and not entry.get("tool_calls"):
                chunks.append({
                    "entries": current_chunk,
                    "chunk_id": len(chunks),
                    "timestamp": current_chunk[0].get("timestamp")
                })
                current_chunk = []

        return chunks

    def _filter_chunk(self, chunk: dict) -> dict:
        """Apply filtering rules to chunk"""
        filtered_entries = []

        for entry in chunk["entries"]:
            entry_type = entry.get("type")

            if entry_type in ["user", "assistant"]:
                # Keep full content
                filtered_entries.append(entry)

            elif entry_type == "tool_use":
                # Keep structure, summarize output
                filtered_entries.append({
                    "type": "tool_use",
                    "tool": entry["tool"],
                    "input": entry.get("input", {}),
                    "output_summary": self._summarize_output(entry.get("output")),
                    "status": "success" if "output" in entry else "error"
                })

            elif entry_type == "error":
                # Keep error message, omit stack trace
                filtered_entries.append({
                    "type": "error",
                    "message": entry.get("message", "")[:500],
                    "error_type": entry.get("error_type")
                })

        return {**chunk, "entries": filtered_entries}

    def _summarize_output(self, output: any) -> str:
        """Create concise summary of tool output"""
        if isinstance(output, dict):
            keys = list(output.keys())[:5]
            return f"Dict with keys: {keys}"
        elif isinstance(output, list):
            return f"List with {len(output)} items"
        elif isinstance(output, str):
            lines = output.count('\n') + 1
            chars = len(output)
            return f"Text ({lines} lines, {chars} chars)"
        else:
            return str(type(output).__name__)

    def _format_chunk(self, chunk: dict) -> str:
        """Format filtered chunk into episode body"""
        lines = []

        for entry in chunk["entries"]:
            if entry["type"] == "user":
                lines.append(f"User: {entry['content']}")

            elif entry["type"] == "assistant":
                lines.append(f"Agent: {entry['content']}")

            elif entry["type"] == "tool_use":
                tool_name = entry["tool"]
                inputs = entry["input"]
                summary = entry["output_summary"]
                lines.append(f"Action: {tool_name}({inputs}) → {summary}")

            elif entry["type"] == "error":
                lines.append(f"Error: {entry['message']}")

        return "\n".join(lines)
```

### Watchdog Integration

```python
class JSONLFileHandler(FileSystemEventHandler):
    def __init__(self, session_path: Path, on_new_content: callable):
        self.session_path = session_path
        self.on_new_content = on_new_content
        self.last_position = 0

    def on_modified(self, event):
        """Triggered when JSONL file is appended"""
        if event.src_path != str(self.session_path):
            return

        # Read new lines since last position
        with open(self.session_path, 'r') as f:
            f.seek(self.last_position)
            new_lines = f.readlines()
            self.last_position = f.tell()

        # Process new content
        asyncio.create_task(self.on_new_content(new_lines))
```

## Configuration Schema

```json
{
  "version": "2.0",
  "session_tracking": {
    "enabled": true,
    "mode": "claude_code_jsonl",
    "incremental": true,
    "chunking": {
      "strategy": "exchange",  // user→agent turn
      "max_chunk_tokens": 1000
    },
    "filtering": {
      "keep_user_messages": true,
      "keep_agent_responses": true,
      "keep_tool_structure": true,
      "omit_tool_outputs": true,
      "omit_file_contents": true,
      "max_output_summary_chars": 200
    },
    "indexing": {
      "frequency": "realtime",  // or "batch"
      "batch_interval_minutes": 5
    }
  },
  "projects": {
    "hostname__abc123": {
      "project_root": "/path/to/project",
      "jsonl_path": "~/.claude/projects/{hash}/sessions",
      "session_tracking_enabled": true
    }
  }
}
```

## Benefits & Implications

### 1. Agent Workflow Learning

**Graph captures**:
```
Pattern: Read → Grep → Edit (successful 85% of time)
Pattern: Bash → Error → Read docs → Bash (retry pattern)
```

**Future agents can**:
- See what approaches worked before
- Avoid known failure paths
- Learn project-specific workflows

### 2. Decision Preservation

**Graph captures**:
```
User: "Why did we avoid Redis here?"
  → Context: "Serverless constraints" (from session 3 days ago)

Agent: "Should I use library X?"
  → Context: "User prefers library Y" (from session last week)
```

### 3. Error Resolution Memory

**Graph captures**:
```
Error: "Connection timeout to database"
  → Resolution: "Increased timeout from 5s to 30s"
  → When: "2025-11-10"
  → Who: "User explicitly requested"
```

**Future agents see**:
- This error happened before
- How it was resolved
- Why that solution was chosen

### 4. Cross-Session Continuity

**Agent can query**:
```
"What were we working on in the last session?"
  → "Implementing authentication with JWT"

"Why did we rollback the Redis changes?"
  → "Serverless deployment incompatibility"

"How did we fix the database timeout issue?"
  → "Increased connection pool size to 20"
```

## Token Cost Projection

**Typical Session** (1 hour, ~20 user/agent exchanges):
- Raw JSONL: ~200k tokens
- After filtering: ~12k tokens
- Graphiti processing: ~110k tokens
- Cost: $0.17-$3.30 per session

**Daily Usage** (3 sessions):
- Total tokens: ~330k
- Cost: $0.50-$10/day

**Monthly Cost** (60 sessions):
- Total tokens: ~6.6M
- Cost: $10-$200/month

**Value Proposition**: For $10-$200/month, agents gain **complete project memory** and **cross-session learning**.

## Phased Rollout

### Phase 1: Proof of Concept
- Implement JSONL parsing
- Basic filtering (keep user/agent, omit tool outputs)
- Manual testing with 1 session

### Phase 2: Incremental Indexing
- Watchdog integration
- Track last indexed position
- Real-time processing

### Phase 3: Smart Filtering
- Advanced output summarization
- Chunk optimization
- Token cost monitoring

### Phase 4: Query Interface
- Search across sessions
- Pattern recognition
- Workflow visualization

## Next Steps

1. Validate JSONL path resolution algorithm
2. Implement basic filter (user/agent only)
3. Test with single session end-to-end
4. Measure actual token costs
5. Iterate on filtering rules

This is **genuinely transformative** - we're building agent memory that rivals human memory!
