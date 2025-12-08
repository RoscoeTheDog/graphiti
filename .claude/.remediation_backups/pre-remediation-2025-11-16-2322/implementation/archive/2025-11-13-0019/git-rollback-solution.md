# Git Rollback Context Preservation - Solution Summary

## Problem Statement

When agents work with projects using filesystem tracking, git rollbacks create a **context preservation dilemma**:

### Scenario
1. Agent implements feature (creates 15+ files)
2. User realizes architecture is flawed
3. User runs `git reset --hard HEAD~5`
4. **Question**: What should agent know in next session?

### Dilemma
- **Option A**: Show all file changes → Agent sees "47 files changed" (no context WHY)
- **Option B**: Hide file changes → Agent thinks old work still exists (confusion)
- **Lost Context**: The reasoning about WHY rollback happened is valuable

## Solution: Three-Tier Git Operation Tracking

### Architecture

**Tier 1: Git Metadata** (lightweight, ALWAYS in lazy-load)
- WHAT: Operation type, commits, file count
- Token cost: ~50 tokens
- Purpose: Agent knows git operation occurred

**Tier 2: Conversation Context** (WHY it happened, ALWAYS in lazy-load)
- Captures last 5 messages before git operation
- Token cost: ~200-500 tokens
- Purpose: Agent understands reasoning

**Tier 3: File State Changes** (bulk updates, EXCLUDED from lazy-load)
- Individual file contents (47 episodes)
- Token cost: ~50k tokens (if all loaded)
- Purpose: Queryable for specific file history
- **Excluded by default** to prevent context pollution

### Implementation

```python
# When .git/HEAD changes:
1. Create Tier 1: Git metadata episode
   - "Git reset --hard: 47 files, abc123 → def456"
   - operation="git_metadata" (included in lazy-load)

2. Create Tier 2: Conversation snapshot
   - Last 5 messages from conversation buffer
   - "User: Won't work with serverless, Agent: Should rollback"
   - operation="git_context" (included in lazy-load)

3. Queue Tier 3: File updates (47 episodes)
   - Individual file contents
   - operation="update" (excluded from lazy-load)
   - Linked via git_batch_id
```

### Lazy-Load Query

```python
# Agent INIT R8
search_memory_nodes(
    query="recent project context",
    group_ids=[GRAPHITI_GROUP_ID],
    exclude_operations=["update", "delete", "move", "rename"],  # Tier 3
    max_nodes=20
)

# Returns:
# - Tier 1: Git metadata ✅
# - Tier 2: Conversation context ✅
# - User memories ✅
# - NOT: 47 file updates ❌
```

## Example: Redis Cache Rollback

**Session 1**: Implementation attempt
```
User: "Implement Redis caching layer"
Agent: [Creates 15 files]
User: "Wait, won't work with serverless"
Agent: "Right, should rollback"
User: git reset --hard HEAD~5
```

**Graphiti stores**:
1. Tier 1: "Git rollback: 47 files, 15:30 on 2025-11-12"
2. Tier 2: "Conversation: Serverless incompatibility with Redis"
3. Tier 3: 47 file update episodes (marked with git_batch_id)

**Session 2**: Next day
```
Agent lazy-load sees:
✅ "Git rollback occurred (47 files)"
✅ "Reason: Serverless + Redis incompatible"
✅ Current filesystem state (no Redis code)

Agent understands:
- Work was intentionally abandoned
- Why it was abandoned
- What to avoid (Redis in serverless)
```

## Benefits

✅ **Context Preservation**: Agent knows WHAT happened (rollback) and WHY (architecture mismatch)

✅ **No Pollution**: Lazy-load stays clean (50 tokens vs 50k tokens)

✅ **Queryable History**: File updates available if needed ("show me Redis implementation")

✅ **Decision Learning**: Agent remembers "avoid Redis in serverless" for future

✅ **Temporal Integrity**: All data preserved in graph, just filtered intelligently

## Technical Requirements

### MCP Server Changes
1. Add conversation buffer (last 10 messages)
2. Intercept tool calls to populate buffer
3. Pass buffer to FilesystemTrackingManager

### GitDetector Enhancement
1. Capture git operation metadata (commit hashes, branch, timestamp)
2. Create Tier 1 + Tier 2 episodes on .git/HEAD change
3. Mark Tier 3 file updates with git_batch_id

### Query Enhancement
1. Add `exclude_operations` parameter to search_memory_nodes
2. Filter episodes by operation metadata
3. Default exclude: ["update", "delete", "move", "rename"]

## Conversation Buffer Implementation

```python
class GraphitiMCPServer:
    def __init__(self):
        self.conversation_buffer = deque(maxlen=10)

    async def handle_tool_call(self, tool, args):
        # Track user messages
        if tool == "add_memory":
            self.conversation_buffer.append({
                "timestamp": datetime.utcnow(),
                "content": args["episode_body"][:500]
            })

        return await super().handle_tool_call(tool, args)
```

## Configuration

No new user-facing config needed. This is automatic behavior when:
- Filesystem tracking enabled
- Git repository detected
- Conversation buffer available

## Next Steps

See [filesystem-tracking-design.md](filesystem-tracking-design.md) for complete implementation details.

Priority:
1. Implement conversation buffer in MCP server
2. Enhance GitDetector with Tier 1/2 episode creation
3. Add `exclude_operations` to search_memory_nodes
4. Test with real git workflows (checkout, reset, rebase)
