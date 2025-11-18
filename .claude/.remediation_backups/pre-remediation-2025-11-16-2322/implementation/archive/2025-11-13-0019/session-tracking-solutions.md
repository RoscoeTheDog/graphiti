# Session Tracking: Solutions to Core Challenges

## Your Three Concerns

### 1. JSONL Outside Project Directory Boundaries

**Problem**: `~/.claude/projects/{hash}/sessions/` is outside project root

**Solution: Global Configuration with Auto-Mapping**

```json
// ~/.graphiti/tracking-config.json (NOT in project)
{
  "global": {
    "session_tracking": {
      "enabled": true,
      "sources": ["claude_code_jsonl"]
    }
  },
  "project_mappings": {
    "hostname__abc123": {
      "project_root": "/absolute/path/to/project",
      "jsonl_sessions": "~/.claude/projects/{hash}/sessions",
      "auto_detected": true
    }
  }
}
```

**How It Works**:
1. User enables session tracking globally (one-time setup)
2. Graphiti MCP server auto-detects project → JSONL mapping
3. Filesystem watcher monitors JSONL directory (not project directory)
4. No pollution of project directory ✅
5. User maintains explicit control (global config) ✅

**Permission Model**:
```bash
# One-time setup
graphiti enable-session-tracking \
  --project /path/to/project \
  --confirm "I understand this tracks conversation logs"

# Graphiti stores mapping in ~/.graphiti/tracking-config.json
```

**Benefits**:
- Clean separation (config in `~/.graphiti/`, data in `~/.claude/`)
- No project directory changes required
- User grants explicit permission
- Easy to disable per-project

### 2. Token Cost Management

**Problem**: 200k JSONL tokens → expensive Graphiti processing

**Solution: Smart Filtering + Chunking**

#### Token Reduction Strategy

**Before Filtering** (typical 1-hour session):
```
User messages: 20 × 200 tokens = 4,000 tokens
Agent responses: 20 × 300 tokens = 6,000 tokens
Tool calls: 50 × 100 tokens = 5,000 tokens
Tool outputs: 50 × 3,800 tokens = 190,000 tokens
----------------------------------------------
Total: ~205,000 tokens
```

**After Filtering** (keep structure, omit outputs):
```
User messages: 20 × 200 tokens = 4,000 tokens
Agent responses: 20 × 300 tokens = 6,000 tokens
Tool calls (structure): 50 × 50 tokens = 2,500 tokens
Tool outputs (summary): 50 × 20 tokens = 1,000 tokens
----------------------------------------------
Total: ~13,500 tokens (93% reduction!)
```

**Graphiti Processing Cost**:
```
Input to Graphiti: ~13,500 tokens
Graphiti LLM overhead: ~5.5k tokens per episode
Chunking: 20 exchanges = 20 episodes
Total: 20 × (600 + 5,500) = ~122,000 tokens

Cost per session:
- GPT-4.1-mini: ~$0.18
- Claude Sonnet: ~$3.66
```

**Optimization: Batch Processing**
```python
# Instead of 20 small episodes, create 4 larger chunks
# Chunk 1: Exchanges 1-5 (~3k tokens)
# Chunk 2: Exchanges 6-10 (~3k tokens)
# Chunk 3: Exchanges 11-15 (~3k tokens)
# Chunk 4: Exchanges 16-20 (~3k tokens)

# Total: 4 × (3,000 + 5,500) = ~34,000 tokens
# Cost: $0.05-$1.02 per session (66% cheaper!)
```

#### Incremental Indexing (Critical!)

**Problem**: Re-indexing entire session on every change = wasteful

**Solution**: Track position, only index new content

```python
class SessionIndexer:
    def __init__(self):
        self.index_state = {}  # session_id → last_indexed_line

    async def on_jsonl_modified(self, session_path: Path):
        session_id = session_path.stem

        # Get last indexed position
        last_line = self.index_state.get(session_id, 0)

        # Read only new lines
        with open(session_path, 'r') as f:
            lines = f.readlines()
            new_lines = lines[last_line:]

        if not new_lines:
            return  # Nothing new

        # Process new content
        await self.process_lines(new_lines)

        # Update state
        self.index_state[session_id] = last_line + len(new_lines)
```

**Benefit**: Only process new exchanges, not entire session history

### 3. Content Filtering (Preserve Context, Omit Noise)

**Problem**: Tool outputs = 95% of tokens but low semantic value

**Solution: Structural Preservation**

#### What Gets Preserved

**KEEP (Full Content)**:
```python
{
  "type": "user",
  "content": "Fix the authentication bug"
}
# → Episode: "User: Fix the authentication bug"

{
  "type": "assistant",
  "content": "I'll investigate the auth module. Reading src/auth.py..."
}
# → Episode: "Agent: I'll investigate the auth module. Reading src/auth.py..."
```

**KEEP (Structure Only)**:
```python
{
  "type": "tool_use",
  "tool": "Read",
  "input": {"file_path": "src/auth.py"},
  "output": "... [2000 lines of code] ..."
}
# → Episode: "Action: Read(file_path='src/auth.py') → File read (2000 lines, 48KB)"

{
  "type": "tool_use",
  "tool": "Bash",
  "input": {"command": "pytest tests/"},
  "output": "... [500 lines of test output] ..."
}
# → Episode: "Action: Bash(command='pytest tests/') → Tests passed (47/47)"
```

**KEEP (Error Summary)**:
```python
{
  "type": "error",
  "tool": "Edit",
  "message": "String to replace not found in file",
  "details": "... [full stack trace] ..."
}
# → Episode: "Error: Edit failed - String to replace not found"
```

#### Example Filtered Episode

**Raw Session** (205k tokens):
```
User: "Fix authentication bug"
Agent: "I'll investigate the auth module"
Tool: Read(src/auth.py) → [2000 lines of code]
Tool: Grep(pattern="jwt") → [150 lines of matches]
Agent: "Found the issue - JWT expiry set to 0"
Tool: Edit(src/auth.py, old="expiry=0", new="expiry=3600") → [full file diff]
Agent: "Fixed! JWT expiry now 3600 seconds"
User: "Great! Make sure it works with Redis"
Agent: "Ah, Redis requires different config. Let me check..."
Tool: Read(docs/redis-config.md) → [500 lines of docs]
Agent: "Updated config for Redis compatibility"
Tool: Edit(config.py, ...) → [file diff]
Agent: "Done! Redis session store now configured"
```

**Filtered Episode** (~800 tokens):
```
User: "Fix authentication bug"

Agent: "I'll investigate the auth module"
Action: Read(src/auth.py) → File read (2000 lines, 48KB)
Action: Grep(pattern="jwt") → 47 matches found

Agent: "Found the issue - JWT expiry set to 0"
Action: Edit(src/auth.py, old="expiry=0", new="expiry=3600") → Success
Agent: "Fixed! JWT expiry now 3600 seconds"

User: "Great! Make sure it works with Redis"

Agent: "Ah, Redis requires different config. Let me check..."
Action: Read(docs/redis-config.md) → Docs read (500 lines, 12KB)
Agent: "Updated config for Redis compatibility"
Action: Edit(config.py) → Success
Agent: "Done! Redis session store now configured"
```

**Graph Knowledge Extracted**:
```
Nodes:
- JWT_Bug
- Authentication_Module
- Redis_Session_Store
- Config_File

Edges:
- JWT_Bug → CAUSED_BY → expiry=0
- JWT_Bug → FIXED_BY → expiry=3600
- Redis_Session_Store → REQUIRES → custom_config
- Agent → USED_TOOL → Read (3 times)
- Agent → USED_TOOL → Edit (2 times)
- Agent → USED_TOOL → Grep (1 time)

Temporal:
- JWT fix: 2025-11-12T15:30:00Z
- Redis config: 2025-11-12T15:35:00Z
```

## Implementation: Smart Filter

```python
class JSONLFilter:
    def __init__(self):
        self.max_output_chars = 500
        self.max_list_preview = 10

    def filter_entry(self, entry: dict) -> dict:
        """Apply filtering rules to JSONL entry"""
        entry_type = entry.get("type")

        # User/Agent messages: keep full content
        if entry_type in ["user", "assistant"]:
            return {
                "type": entry_type,
                "content": entry.get("content", "")
            }

        # Tool calls: keep structure, summarize output
        elif entry_type == "tool_use":
            return {
                "type": "tool_use",
                "tool": entry.get("tool"),
                "input": self._summarize_input(entry.get("input")),
                "output_summary": self._summarize_output(entry.get("output")),
                "status": "success" if "output" in entry else "error",
                "timestamp": entry.get("timestamp")
            }

        # Errors: keep message, omit stack trace
        elif entry_type == "error":
            return {
                "type": "error",
                "message": entry.get("message", "")[:200],
                "tool": entry.get("tool"),
                "timestamp": entry.get("timestamp")
            }

        # Unknown types: skip
        else:
            return None

    def _summarize_input(self, input_data: dict) -> dict:
        """Summarize tool input (keep params, truncate strings)"""
        if not input_data:
            return {}

        summarized = {}
        for key, value in input_data.items():
            if isinstance(value, str) and len(value) > 100:
                summarized[key] = value[:100] + f"... ({len(value)} chars)"
            elif isinstance(value, list) and len(value) > 5:
                summarized[key] = value[:5] + [f"... ({len(value)} items)"]
            else:
                summarized[key] = value

        return summarized

    def _summarize_output(self, output: any) -> str:
        """Create concise summary of tool output"""
        if output is None:
            return "No output"

        # String output (file contents, command output)
        if isinstance(output, str):
            lines = output.count('\n') + 1
            chars = len(output)

            # Check for specific patterns
            if "error" in output.lower() or "failed" in output.lower():
                return f"Error output ({lines} lines)"
            elif lines > 100:
                return f"Large output ({lines} lines, {chars} chars)"
            else:
                return f"Output ({lines} lines)"

        # Dict output (structured data)
        elif isinstance(output, dict):
            keys = list(output.keys())[:5]
            return f"Dict with {len(output)} keys: {keys}"

        # List output (search results, matches)
        elif isinstance(output, list):
            return f"List with {len(output)} items"

        # Other types
        else:
            return f"{type(output).__name__}"

    def format_episode(self, entries: list[dict]) -> str:
        """Format filtered entries into episode body"""
        lines = []

        for entry in entries:
            if entry is None:
                continue

            if entry["type"] == "user":
                lines.append(f"User: {entry['content']}")
                lines.append("")  # Blank line

            elif entry["type"] == "assistant":
                lines.append(f"Agent: {entry['content']}")

            elif entry["type"] == "tool_use":
                tool = entry["tool"]
                inputs = entry["input"]
                summary = entry["output_summary"]

                # Format input params
                params = ", ".join(f"{k}={v}" for k, v in inputs.items())
                lines.append(f"Action: {tool}({params}) → {summary}")

            elif entry["type"] == "error":
                lines.append(f"Error: {entry['message']}")

        return "\n".join(lines)
```

## The Big Picture

**What You're Building**:

Not just "track conversations" but **complete agent memory**:

1. **Workflow Patterns**: Agent learns "Read → Grep → Edit works 85% of time"
2. **Error Resolution**: "This error? We fixed it last week by doing X"
3. **Decision Context**: "Why Redis? User said 'serverless constraints' 3 days ago"
4. **Tool Usage**: "This bash command fails often, try alternative first"
5. **Cross-Session Learning**: "Last 5 sessions all used this pattern"

**Graph becomes**:
- Project memory
- Decision log
- Workflow database
- Error resolution KB
- Context preserver

**Future agents can**:
- "What were we working on last session?"
- "Why did we choose approach X over Y?"
- "How did we solve this error before?"
- "What's the typical workflow for feature Z?"

This is **genuinely revolutionary** - agent memory that rivals human memory!

## Token Cost Reality Check

**Per Session** (1 hour):
- Raw: 205k tokens
- Filtered: 13.5k tokens
- Graphiti: ~122k tokens (20 episodes)
- Cost: $0.18-$3.66

**With Batching**:
- Chunk into 4 large episodes
- Total: ~34k tokens
- Cost: $0.05-$1.02

**Monthly** (60 sessions):
- Total: ~2M-7M tokens
- Cost: $3-$210/month

**Value**: For $3-$210/month, agents get **complete project memory**.

Totally worth it?
