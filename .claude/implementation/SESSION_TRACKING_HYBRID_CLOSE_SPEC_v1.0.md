# Session Tracking Hybrid Close Architecture - Specification v1.0

**Version**: 1.0.0
**Status**: Design Specification
**Authors**: Human + Claude Agent
**Date**: 2025-12-11
**Related**: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md, INTELLIGENT_SESSION_SUMMARIZATION_SPEC_v1.0.md

---

## Executive Summary

This specification defines a hybrid approach to session close detection that eliminates wasted LLM calls while ensuring timely context handoff between agents. The architecture combines explicit signals, lazy indexing, content-based deduplication, and inactivity timeout as a layered fallback system.

### Problem Statement

The current inactivity-based timeout approach creates a fundamental tension:

| Fast Timeout (2 min) | Slow Timeout (15 min) |
|---------------------|----------------------|
| ✅ Quick handoff to next agent | ❌ Slow handoff (stale context) |
| ❌ Wasted LLM calls on pauses | ✅ Fewer wasted LLM calls |
| ❌ Many delete/replace cycles | ✅ Fewer replacements needed |
| ❌ Higher cost | ❌ Next agent lacks recent context |

**Root Cause**: We're inferring user intent from file system events, which is inherently lossy.

**Additional Complication**:
- `/compact` has no reliable markers in JSONL
- `/clear` creates new JSONL but could be parallel agent
- Same PWD doesn't indicate same workflow
- No way to distinguish concurrent agents from sequential sessions

### Solution Overview

A four-layer hybrid approach:

1. **Explicit Close (Primary)** - Agent/user signals session complete
2. **Lazy Indexing (Fallback)** - Index on-demand when next agent queries
3. **Content-Hash Dedup (Safety)** - Skip unchanged, replace changed
4. **Inactivity Timeout (Last Resort)** - Catches abandoned sessions

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Layer 1: Explicit Close Signal](#2-layer-1-explicit-close-signal)
3. [Layer 2: Lazy Indexing on Query](#3-layer-2-lazy-indexing-on-query)
4. [Layer 3: Content-Hash Deduplication](#4-layer-3-content-hash-deduplication)
5. [Layer 4: Inactivity Timeout Fallback](#5-layer-4-inactivity-timeout-fallback)
6. [Session State Machine](#6-session-state-machine)
7. [Delete/Replace Strategy](#7-deletereplace-strategy)
8. [Configuration Schema](#8-configuration-schema)
9. [MCP Tool Interface](#9-mcp-tool-interface)
10. [Integration Points](#10-integration-points)
11. [Implementation Requirements](#11-implementation-requirements)
12. [Testing Requirements](#12-testing-requirements)

---

## 1. Architecture Overview

### 1.1 Current Architecture (Timeout-Only)

```
Session Active
      ↓
Inactivity detected (15 min)
      ↓
_close_session() → Index to graph
      ↓
Session removed from active_sessions
      ↓
File modified again? → Treated as NEW session → DUPLICATE indexed
```

**Problems**:
- No deduplication
- No explicit close signal
- Timeout too slow for handoff, too fast for pauses
- Wasted LLM calls on session resume

### 1.2 Proposed Architecture (Hybrid)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SESSION LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────┐                                                        │
│   │ ACTIVE  │ ←──────────────────────────────────────┐              │
│   └────┬────┘                                        │              │
│        │                                             │              │
│        ├──── Layer 1: Explicit Close ────┐          │              │
│        │     (session_tracking_close())  │          │              │
│        │                                 ▼          │              │
│        │                          ┌──────────┐      │              │
│        │                          │ INDEXING │──────┤              │
│        │                          └──────────┘      │              │
│        │                                 │          │              │
│        ├──── Layer 4: Timeout ───────────┤          │              │
│        │     (30-60 min fallback)        │          │              │
│        │                                 ▼          │              │
│        │                          ┌──────────┐      │              │
│        │                          │ INDEXED  │      │              │
│        │                          └────┬─────┘      │              │
│        │                               │            │              │
│        │         File modified?        │            │              │
│        │              │                │            │              │
│        │              ▼                │            │              │
│        │     ┌─────────────────┐       │            │              │
│        │     │ Layer 3: Hash   │       │            │              │
│        │     │ Compare Content │       │            │              │
│        │     └────────┬────────┘       │            │              │
│        │              │                │            │              │
│        │    ┌─────────┴─────────┐      │            │              │
│        │    ▼                   ▼      │            │              │
│        │ Unchanged           Changed   │            │              │
│        │ (skip)              (replace) │            │              │
│        │                        │      │            │              │
│        │                        └──────┘            │              │
│        │                                            │              │
│   ┌────┴────┐                                       │              │
│   │UNINDEXED│ ←── Session closed without indexing   │              │
│   └────┬────┘     (timeout disabled, abandoned)     │              │
│        │                                            │              │
│        └──── Layer 2: Lazy Index ───────────────────┘              │
│              (next agent queries graph)                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer 1: Explicit Close Signal

### 2.1 Purpose

Provide a reliable, explicit mechanism for agents/users to signal "this session is complete, index it now."

### 2.2 MCP Tool: `session_tracking_close`

```python
@mcp.tool()
async def session_tracking_close(
    session_id: str | None = None,
    reason: str | None = None,
) -> str:
    """
    Explicitly close and index the current or specified session.

    This is the PREFERRED method for session handoff. Call this tool when:
    - Completing a story/task before starting the next
    - Before running /clear to start fresh context
    - When handing off to another agent
    - Before ending a work session

    Args:
        session_id: Specific session to close (default: current active session)
        reason: Optional reason for closing (logged, included in metadata)

    Returns:
        JSON with indexing result:
        {
            "status": "success" | "error",
            "session_id": str,
            "episode_uuid": str | null,
            "message": str
        }

    Examples:
        # Close current session (most common)
        session_tracking_close()

        # Close with reason (for logging/debugging)
        session_tracking_close(reason="story_complete")

        # Close specific session
        session_tracking_close(session_id="abc123-def456")

    Note:
        - If session is already indexed and unchanged, returns existing episode UUID
        - If session content changed since last index, replaces the episode
        - Triggers immediate LLM processing (not queued)
    """
```

### 2.3 Integration Pattern

**IMPORTANT**: The session tracking module MUST NOT depend on external command modules (e.g., `/sprint:*` namespace). Instead, external modules should integrate with session tracking.

```
┌──────────────────────────────────────────────────────────────────┐
│                     INTEGRATION BOUNDARY                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Session Tracking Module              External Modules            │
│  ════════════════════                 ════════════════            │
│                                                                   │
│  ┌─────────────────────┐              ┌─────────────────────┐    │
│  │ session_tracking_   │◄─────────────│ /sprint:NEXT        │    │
│  │ close()             │   calls      │ /sprint:FINISH      │    │
│  │                     │              │ /context:HANDOFF    │    │
│  │ (standalone MCP     │              │ etc.                │    │
│  │  tool, no deps)     │              │                     │    │
│  └─────────────────────┘              └─────────────────────┘    │
│                                                                   │
│  Session tracking provides the tool.                              │
│  External modules choose to call it.                              │
│  NO circular dependencies.                                        │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.4 Recommended Integration Points for External Modules

The following namespace commands SHOULD call `session_tracking_close()` as part of their workflow. **These modifications should be made by the dedicated namespace command agent, not this module.**

| Command | When to Call | Reason |
|---------|--------------|--------|
| `/sprint:NEXT` | Before loading next story | Previous story context available |
| `/sprint:FINISH` | Before merge operations | Sprint context preserved |
| `/context:HANDOFF` | As part of handoff creation | Ensures session indexed for handoff |
| `/clear` (if hooked) | Before clearing context | Preserves session before wipe |

**Example integration in slash command**:
```markdown
<!-- In /sprint:NEXT.md -->
## Pre-Execution Steps
1. Call `session_tracking_close(reason="sprint_next_transition")` to index current session
2. Load next story from queue
3. Begin execution...
```

---

## 3. Layer 2: Lazy Indexing on Query

### 3.1 Purpose

Eliminate wasted LLM calls by only indexing sessions that are actually queried by subsequent agents. This aligns cost with value.

### 3.2 Mechanism

```python
# When agent queries graph (search_memory_nodes, get_episodes, etc.)
async def search_memory_nodes(query: str, group_ids: list[str], ...):
    # Step 1: Check for unindexed sessions in queried groups
    unindexed = await find_unindexed_sessions(group_ids)

    if unindexed:
        # Step 2: Index them on-demand (blocking)
        for session in unindexed:
            await index_session_on_demand(session)

    # Step 3: Perform actual search (now includes fresh content)
    return await graphiti.search(query, group_ids, ...)
```

### 3.3 Session State Tracking

Requires persistent tracking of session states:

```python
@dataclass
class SessionState:
    session_id: str
    file_path: Path
    project_namespace: str
    state: Literal["active", "inactive", "indexed", "unindexed"]
    content_hash: str | None  # For dedup
    last_indexed_at: datetime | None
    episode_uuid: str | None
    last_activity: datetime
    message_count: int
```

**Storage**: `~/.graphiti/session_states.json` (persisted across restarts)

### 3.4 Trigger Points

Lazy indexing triggered on these MCP tool calls:

- `search_memory_nodes()`
- `search_memory_facts()`
- `get_episodes()`
- `session_tracking_sync_history()` (preview mode)

### 3.5 Performance Considerations

**First Query Latency**: If unindexed sessions exist, first query will be slower (indexing is synchronous).

**Mitigation Options**:
1. Show progress: `"Indexing 2 recent sessions before search..."`
2. Parallel indexing: Index multiple sessions concurrently
3. Timeout: Skip indexing if it would exceed query timeout

---

## 4. Layer 3: Content-Hash Deduplication

### 4.1 Purpose

Enable aggressive timeouts without wasting LLM calls on unchanged content. Also enables clean delete/replace when content changes.

### 4.2 Hash Computation

```python
def compute_session_hash(file_path: Path) -> str:
    """
    Compute content hash for session file.

    Uses SHA-256 of filtered content (not raw JSONL) to ensure
    hash stability across non-semantic changes.
    """
    # Parse and filter session
    messages, _ = parser.parse_file(str(file_path))
    filtered = session_filter.filter_conversation(messages)

    # Serialize deterministically
    content = "\n".join(f"[{m.role}]: {m.content}" for m in filtered)

    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

### 4.3 Decision Flow

```
Session close triggered (any layer)
              │
              ▼
    ┌─────────────────────┐
    │ Compute content_hash│
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ Check session_state │
    │ for previous hash   │
    └──────────┬──────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
   No previous     Has previous
   (first index)   episode
       │               │
       │               ▼
       │      ┌─────────────────┐
       │      │ Hash matches?   │
       │      └────────┬────────┘
       │               │
       │       ┌───────┴───────┐
       │       ▼               ▼
       │    Matches         Different
       │    (unchanged)     (changed)
       │       │               │
       │       ▼               ▼
       │    SKIP           DELETE old
       │    (return        episode
       │    existing       │
       │    UUID)          ▼
       │               INDEX new
       │               content
       │                   │
       └───────────────────┴───────────▶ Update session_state
```

### 4.4 Skip Logging

When skipping unchanged sessions:
```
INFO: Session abc123 unchanged (hash: a1b2c3d4), skipping index
```

---

## 5. Layer 4: Inactivity Timeout Fallback

### 5.1 Purpose

Catch abandoned sessions that were never explicitly closed and never queried. This is the last resort, not the primary mechanism.

### 5.2 Configuration

```json
{
  "session_tracking": {
    "inactivity_timeout": 1800,  // 30 minutes (increased from 15)
    "_inactivity_timeout_help": "Fallback timeout for abandoned sessions. Primary close should be explicit."
  }
}
```

### 5.3 Behavior

- Timeout triggers `_close_session()` as before
- Goes through Layer 3 (hash dedup) before indexing
- Marked as `close_reason: "inactivity_timeout"` in metadata

### 5.4 Recommended Timeout Values

| Use Case | Timeout | Rationale |
|----------|---------|-----------|
| Development (active) | 1800s (30 min) | Long enough to not interrupt deep work |
| CI/Automation | 300s (5 min) | Agents complete quickly |
| Overnight/Away | 3600s (1 hr) | Catch end-of-day abandonment |

---

## 6. Session State Machine

### 6.1 States

```
┌─────────────────────────────────────────────────────────────────┐
│                     SESSION STATES                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ACTIVE ──────┬────────────────────────────────────▶ INACTIVE   │
│    │          │ (file not modified for check_interval)    │     │
│    │          │                                           │     │
│    │          │ explicit_close()                          │     │
│    │          │ or timeout                                │     │
│    │          ▼                                           │     │
│    │     INDEXING ─────────────────────────────────▶ INDEXED    │
│    │          │                                           │     │
│    │          │ error                                     │     │
│    │          ▼                                           │     │
│    │       FAILED ──────────────────────────────────▶ (retry)   │
│    │                                                      │     │
│    │  ◄───────────────────────────────────────────────────┘     │
│    │  file modified (session resumed)                           │
│    │                                                             │
│    │  Hash comparison on re-index:                               │
│    │  - Unchanged → SKIP (stay INDEXED)                          │
│    │  - Changed → DELETE + re-INDEX                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 State Transitions

| From | To | Trigger |
|------|-----|---------|
| (new) | ACTIVE | File created/detected |
| ACTIVE | ACTIVE | File modified (activity) |
| ACTIVE | INACTIVE | No modification for `check_interval` |
| INACTIVE | ACTIVE | File modified |
| ACTIVE/INACTIVE | INDEXING | explicit_close() or timeout |
| INDEXING | INDEXED | Success |
| INDEXING | FAILED | Error (queued for retry) |
| INDEXED | ACTIVE | File modified (session resumed) |
| INDEXED | INDEXED | Re-index triggered, hash unchanged (skip) |
| INDEXED | INDEXING | Re-index triggered, hash changed (replace) |

---

## 7. Delete/Replace Strategy

### 7.1 Rationale

Incremental indexing is not feasible because:
1. LLM summarization output changes based on full context
2. Graphiti entity extraction builds relationships from complete content
3. Updating a node would require rebuilding all relationships

**Therefore**: Delete old episode, index new complete content.

### 7.2 Implementation

```python
async def replace_session_episode(
    session_id: str,
    old_episode_uuid: str,
    new_content: str,
    group_id: str,
    **kwargs
) -> str:
    """
    Replace an existing session episode with updated content.

    1. Delete old episode (and its relationships)
    2. Index new content as fresh episode
    3. Update session state with new UUID
    """
    # Delete old
    await graphiti.delete_episode(old_episode_uuid)
    logger.info(f"Deleted old episode {old_episode_uuid} for session {session_id}")

    # Index new
    new_uuid = await index_session(
        session_id=session_id,
        filtered_content=new_content,
        group_id=group_id,
        **kwargs
    )
    logger.info(f"Replaced with new episode {new_uuid}")

    return new_uuid
```

### 7.3 Relationship Handling

When episode is deleted:
- Graphiti handles cascade deletion of orphaned relationships
- Entity nodes may persist if referenced by other episodes
- This is the expected Graphiti behavior

---

## 8. Architecture Note (Non-Configurable)

The hybrid close strategy is the **architecture**, not a configurable option. The four-layer approach (explicit close → lazy indexing → hash dedup → timeout fallback) represents the design of the system.

**Rationale for non-configurability**:
1. The layers are interdependent - disabling one would break the fallback chain
2. Configuration toggles add complexity without meaningful user value
3. Users who need different behavior would require code changes anyway
4. The hybrid approach is the optimal balance of cost, latency, and reliability

**What remains configurable** (existing fields):
- `session_tracking.enabled` - Enable/disable session tracking entirely
- `session_tracking.inactivity_timeout` - Fallback timeout duration (default: 1800s)
- `session_tracking.watch_directories` - Directories to monitor

No new configuration fields are added by this feature.

---

## 9. MCP Tool Interface

### 9.1 New Tools

#### `session_tracking_close`
```python
async def session_tracking_close(
    session_id: str | None = None,
    reason: str | None = None,
) -> str
```
See Section 2.2 for full specification.

#### `session_tracking_list_unindexed`
```python
async def session_tracking_list_unindexed(
    project_namespace: str | None = None,
    include_inactive: bool = True,
) -> str:
    """
    List sessions that have not been indexed yet.

    Useful for:
    - Debugging lazy indexing
    - Seeing what will be indexed on next query
    - Manual intervention before queries

    Returns:
        JSON with unindexed sessions:
        {
            "status": "success",
            "count": int,
            "sessions": [
                {
                    "session_id": str,
                    "file_path": str,
                    "project_namespace": str,
                    "state": "active" | "inactive",
                    "last_activity": str,
                    "message_count": int
                }
            ]
        }
    """
```

### 9.2 Modified Tools

#### `search_memory_nodes` / `search_memory_facts` / `get_episodes`

Add lazy indexing pre-check (transparent to caller):

```python
async def search_memory_nodes(query: str, ...):
    # NEW: Lazy index check (always enabled as part of hybrid architecture)
    await _ensure_sessions_indexed(group_ids)

    # Existing search logic
    return await graphiti.search(...)
```

---

## 10. Integration Points

### 10.1 Session Tracking Module Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `session_tracking_close()` | MCP tool for explicit close |
| `SessionStateManager` | Track session states, persistence |
| `ContentHasher` | Compute/compare content hashes |
| `LazyIndexer` | On-demand indexing on query |
| `SessionManager` | File watching, timeout fallback |

### 10.2 External Module Integration (NOT in scope)

The following integrations should be implemented by their respective module owners:

| Module | Integration |
|--------|-------------|
| `/sprint:*` commands | Call `session_tracking_close()` on story transitions |
| `/context:HANDOFF` | Call `session_tracking_close()` before handoff creation |
| Claude Code hooks | Optional hook on `/clear` to trigger close |

**Note**: Session tracking MUST NOT have dependencies on these modules. The integration is one-way (external → session tracking).

### 10.3 CLAUDE.md Recommendations

Add to agent instructions:
```markdown
## Session Handoff Best Practice

Before transitioning to a new task or context:
1. Call `session_tracking_close(reason="task_complete")` to ensure current session is indexed
2. This enables the next agent to query your work immediately
3. Skipped automatically if session unchanged (no wasted calls)
```

---

## 11. Implementation Requirements

### 11.1 Story Breakdown

| Story | Description | Priority | Estimate |
|-------|-------------|----------|----------|
| ST-H1 | Implement `SessionStateManager` with persistence | High | M |
| ST-H2 | Implement `session_tracking_close()` MCP tool | High | S |
| ST-H3 | Implement content hash computation and comparison | High | S |
| ST-H4 | Implement delete/replace logic in indexer | High | M |
| ST-H5 | Implement lazy indexing in search tools | Medium | M |
| ST-H6 | Implement `session_tracking_list_unindexed()` tool | Low | S |
| ST-H7 | Write integration tests for hybrid flow | High | L |
| ST-H8 | Update documentation (user guide, dev guide) | Medium | M |

**Note**: Configuration schema stories (ST-H7, ST-H8 in earlier drafts) were removed. The hybrid close strategy is architectural, not configurable. See Section 8.

### 11.2 File Changes

| File | Changes |
|------|---------|
| `graphiti_core/session_tracking/state_manager.py` | NEW: SessionStateManager class |
| `graphiti_core/session_tracking/content_hasher.py` | NEW: Content hash utilities |
| `graphiti_core/session_tracking/session_manager.py` | Integrate state manager, hash dedup |
| `graphiti_core/session_tracking/indexer.py` | Add delete/replace logic |
| `mcp_server/graphiti_mcp_server.py` | Add new MCP tools, lazy indexing |

### 11.3 Dependencies

- No new external dependencies required
- Uses existing: hashlib (stdlib), pathlib (stdlib)

---

## 12. Testing Requirements

### 12.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_content_hash_stability` | Same content → same hash |
| `test_content_hash_changes` | Different content → different hash |
| `test_state_persistence` | States survive restart |
| `test_explicit_close_indexes` | `session_tracking_close()` triggers indexing |
| `test_explicit_close_skips_unchanged` | Skip if hash matches |
| `test_explicit_close_replaces_changed` | Delete + index if hash differs |
| `test_lazy_index_on_search` | Unindexed sessions indexed before search |
| `test_timeout_fallback` | Timeout triggers close after inactivity |

### 12.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_full_hybrid_flow` | Explicit close → query → lazy index fallback |
| `test_session_resume_replace` | Session resumes after index → content replaced |
| `test_parallel_sessions` | Multiple active sessions handled independently |
| `test_cross_restart_state` | Session states persist across MCP server restart |

### 12.3 Manual Testing Checklist

- [ ] Enable session tracking, start session
- [ ] Call `session_tracking_close()` → verify immediate index
- [ ] Modify session, call close again → verify replace (not duplicate)
- [ ] Start new session, query graph → verify lazy index of previous
- [ ] Let session timeout → verify fallback works
- [ ] Check `~/.graphiti/session_states.json` for state persistence

---

## Appendix A: Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Delete/replace vs incremental | Delete/replace | LLM output changes with full context; incremental not feasible |
| Lazy indexing blocking vs async | Blocking | Ensures fresh results; async would complicate UX |
| Hash of filtered vs raw content | Filtered | Stability across non-semantic JSONL changes |
| State persistence location | `~/.graphiti/` | Consistent with other Graphiti state files |
| Default timeout increase | 30 min (from 15) | Primary close is explicit; timeout is fallback |

---

## Appendix B: Migration Notes

### From v1.x (Timeout-Only)

1. Existing indexed sessions remain valid
2. New `session_states.json` created on first run
3. Existing active sessions tracked with state "active"
4. No data migration required
5. No configuration changes required - hybrid close is the new default architecture

---

## 13. Claude Code Hook Integration

### 13.1 Overview

Claude Code provides native hooks that trigger on session lifecycle events. We can leverage `SessionEnd` hooks with `clear` and `compact` matchers to automatically call `session_tracking_close()` when users run `/clear` or `/compact`.

This provides **automatic session indexing** without requiring agents to explicitly call the MCP tool.

### 13.2 Available Hook Events

Claude Code supports these relevant hook events:

| Event | Matchers | Description |
|-------|----------|-------------|
| `SessionEnd` | `clear`, `compact` | Triggered when session ends via /clear or /compact |
| `SessionStart` | `clear`, `compact` | Triggered when new session starts after /clear or /compact |

For session tracking, we use `SessionEnd` to index **before** the session context is cleared.

### 13.3 Hook Configuration

Add to `~/.claude/settings.json` (or project `.claude/settings.json`):

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "clear",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.graphiti/hooks/session_close_hook.py",
            "timeout": 30000
          }
        ]
      },
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.graphiti/hooks/session_close_hook.py",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

### 13.4 Hook Script Design

The hook script must communicate with the running Graphiti MCP server to trigger `session_tracking_close()`.

#### 13.4.1 Architecture Options

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| **A. MCP Client** | Script acts as MCP client, calls tool directly | Clean, uses existing protocol | Requires MCP client library |
| **B. HTTP Endpoint** | MCP server exposes REST endpoint for close | Simple HTTP call | Requires adding HTTP server |
| **C. Signal File** | Script writes marker file, MCP server watches | No network, simple | Polling delay, race conditions |
| **D. Unix Socket/Named Pipe** | Direct IPC to MCP server | Fast, reliable | Platform-specific complexity |

**Recommended: Option A (MCP Client)** - Cleanest integration using the existing MCP protocol.

#### 13.4.2 Hook Script Implementation

```python
#!/usr/bin/env python3
"""
Claude Code SessionEnd Hook for Graphiti Session Tracking

This script is triggered by Claude Code's SessionEnd hook when /clear or /compact
is executed. It calls the Graphiti MCP server's session_tracking_close() tool
to index the session before context is cleared.

Location: ~/.graphiti/hooks/session_close_hook.py
"""

import json
import sys
import asyncio
from pathlib import Path

# Hook receives JSON input via stdin
def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}

async def call_session_tracking_close(session_id: str | None, reason: str) -> dict:
    """
    Call Graphiti MCP server's session_tracking_close() tool.

    Uses lightweight MCP client to communicate with running server.
    """
    try:
        # Option A: MCP Client approach
        from graphiti_mcp_client import GraphitiMCPClient

        async with GraphitiMCPClient() as client:
            result = await client.call_tool(
                "session_tracking_close",
                {
                    "session_id": session_id,
                    "reason": reason
                }
            )
            return json.loads(result)

    except ImportError:
        # Fallback: Direct function call if running in same process
        # This won't work for hook scripts, but useful for testing
        return {"status": "error", "message": "MCP client not available"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    """Main hook entry point."""
    # Read hook input
    hook_input = get_hook_input()

    # Extract relevant info
    session_id = hook_input.get("session_id")
    reason = hook_input.get("reason", "session_end_hook")  # "clear" or "compact"
    transcript_path = hook_input.get("transcript_path")

    # Log for debugging (stderr doesn't interfere with hook protocol)
    print(f"[graphiti-hook] SessionEnd triggered: reason={reason}, session={session_id}",
          file=sys.stderr)

    # Call session tracking close
    try:
        result = asyncio.run(call_session_tracking_close(
            session_id=session_id,
            reason=f"hook_{reason}"  # e.g., "hook_clear", "hook_compact"
        ))

        if result.get("status") == "success":
            print(f"[graphiti-hook] Session indexed: {result.get('episode_uuid')}",
                  file=sys.stderr)
        else:
            print(f"[graphiti-hook] Warning: {result.get('message')}",
                  file=sys.stderr)

    except Exception as e:
        print(f"[graphiti-hook] Error: {e}", file=sys.stderr)
        # Don't fail the hook - session should still clear

    # Return success to Claude Code (don't block /clear or /compact)
    print(json.dumps({"status": "ok"}))
    sys.exit(0)

if __name__ == "__main__":
    main()
```

#### 13.4.3 MCP Client Library

A lightweight MCP client is needed for the hook script to communicate with the running Graphiti MCP server.

```python
# ~/.graphiti/hooks/graphiti_mcp_client.py
"""
Lightweight MCP client for Graphiti hook scripts.

Connects to the running Graphiti MCP server via stdio transport
and calls tools directly.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

class GraphitiMCPClient:
    """Simple MCP client for calling Graphiti tools from hooks."""

    def __init__(self, server_command: str | None = None):
        """
        Initialize MCP client.

        Args:
            server_command: Command to start MCP server (if not already running)
                          Default: Uses existing server via socket/pipe
        """
        self.server_command = server_command
        self._process = None
        self._reader = None
        self._writer = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()

    async def connect(self):
        """Connect to MCP server."""
        # Implementation depends on how MCP server is exposed
        # Option 1: Unix socket at ~/.graphiti/mcp.sock
        # Option 2: Named pipe on Windows
        # Option 3: Start subprocess with stdio transport

        socket_path = Path.home() / ".graphiti" / "mcp.sock"
        if socket_path.exists():
            self._reader, self._writer = await asyncio.open_unix_connection(
                str(socket_path)
            )
        else:
            raise ConnectionError("Graphiti MCP server not running")

    async def disconnect(self):
        """Disconnect from MCP server."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """
        Call an MCP tool and return result.

        Args:
            tool_name: Name of MCP tool (e.g., "session_tracking_close")
            arguments: Tool arguments

        Returns:
            JSON string result from tool
        """
        # Send JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        self._writer.write(json.dumps(request).encode() + b"\n")
        await self._writer.drain()

        # Read response
        response_line = await self._reader.readline()
        response = json.loads(response_line.decode())

        if "error" in response:
            raise Exception(response["error"]["message"])

        return response["result"]["content"][0]["text"]
```

### 13.5 MCP Server Socket Exposure

For the hook script to communicate with the MCP server, the server needs to expose a socket endpoint.

#### 13.5.1 Server-Side Changes

Add to `graphiti_mcp_server.py`:

```python
import asyncio
from pathlib import Path

# Socket path for hook communication
HOOK_SOCKET_PATH = Path.home() / ".graphiti" / "mcp.sock"

async def start_hook_socket_server():
    """
    Start a Unix socket server for hook script communication.

    This allows external scripts (like Claude Code hooks) to call
    MCP tools without going through the full MCP protocol.
    """
    async def handle_hook_client(reader, writer):
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                request = json.loads(line.decode())

                # Route to appropriate tool
                tool_name = request["params"]["name"]
                arguments = request["params"]["arguments"]

                # Call the tool
                if tool_name == "session_tracking_close":
                    result = await session_tracking_close(**arguments)
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                # Send response
                response = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                }
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()

        except Exception as e:
            logger.error(f"Hook client error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    # Remove stale socket
    if HOOK_SOCKET_PATH.exists():
        HOOK_SOCKET_PATH.unlink()

    # Start server
    server = await asyncio.start_unix_server(
        handle_hook_client,
        str(HOOK_SOCKET_PATH)
    )

    logger.info(f"Hook socket server started: {HOOK_SOCKET_PATH}")
    return server
```

#### 13.5.2 Windows Compatibility

On Windows, use named pipes instead of Unix sockets:

```python
import sys

if sys.platform == "win32":
    HOOK_PIPE_NAME = r"\\.\pipe\graphiti_mcp_hook"
    # Use asyncio.start_server with named pipe
else:
    HOOK_SOCKET_PATH = Path.home() / ".graphiti" / "mcp.sock"
    # Use asyncio.start_unix_server
```

### 13.6 Installation and Setup

#### 13.6.1 Automatic Setup

Add to Graphiti installation/setup:

```python
def setup_claude_code_hooks():
    """
    Set up Claude Code hooks for automatic session tracking.

    Creates:
    - ~/.graphiti/hooks/session_close_hook.py
    - ~/.graphiti/hooks/graphiti_mcp_client.py
    - Adds hook config to Claude Code settings (with user confirmation)
    """
    hooks_dir = Path.home() / ".graphiti" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Copy hook scripts
    # ... (copy from package resources)

    # Optionally update Claude Code settings
    claude_settings = Path.home() / ".claude" / "settings.json"
    # ... (merge hook config with existing settings)
```

#### 13.6.2 Manual Setup Instructions

For users who prefer manual setup:

```markdown
## Manual Hook Setup

1. Create hook directory:
   ```bash
   mkdir -p ~/.graphiti/hooks
   ```

2. Copy hook scripts from Graphiti package:
   ```bash
   cp $(python -c "import graphiti_core; print(graphiti_core.__path__[0])")/hooks/* ~/.graphiti/hooks/
   ```

3. Add to `~/.claude/settings.json`:
   ```json
   {
     "hooks": {
       "SessionEnd": [
         {
           "matcher": "clear",
           "hooks": [{"type": "command", "command": "python ~/.graphiti/hooks/session_close_hook.py"}]
         },
         {
           "matcher": "compact",
           "hooks": [{"type": "command", "command": "python ~/.graphiti/hooks/session_close_hook.py"}]
         }
       ]
     }
   }
   ```

4. Restart Claude Code to pick up hook changes.
```

### 13.7 Hook Behavior

#### 13.7.1 Success Flow

```
User runs /clear
        ↓
Claude Code triggers SessionEnd hook (matcher: "clear")
        ↓
session_close_hook.py executes
        ↓
Hook script calls session_tracking_close() via MCP socket
        ↓
Graphiti indexes session (with hash dedup)
        ↓
Hook returns success
        ↓
Claude Code clears context
        ↓
New session starts with indexed context available
```

#### 13.7.2 Failure Handling

The hook script should **never block** `/clear` or `/compact`:

```python
try:
    result = await call_session_tracking_close(...)
except Exception as e:
    # Log error but don't fail
    print(f"[graphiti-hook] Warning: {e}", file=sys.stderr)

# Always return success to Claude Code
print(json.dumps({"status": "ok"}))
sys.exit(0)
```

#### 13.7.3 Timeout Handling

Hook timeout is set to 30 seconds (configurable). If indexing takes longer:

1. Hook times out
2. Claude Code proceeds with /clear
3. Session may not be indexed (falls back to lazy indexing)

For large sessions, consider:
- Async indexing (hook triggers, doesn't wait)
- Increased timeout for heavy users

### 13.8 Configuration Options

Add to `graphiti.config.json`:

```json
{
  "session_tracking": {
    "hooks": {
      "enabled": true,
      "_enabled_help": "Enable Claude Code hook integration",

      "socket_enabled": true,
      "_socket_enabled_help": "Expose socket for hook communication",

      "socket_path": null,
      "_socket_path_help": "null = ~/.graphiti/mcp.sock (Unix) or named pipe (Windows)",

      "hook_timeout": 30000,
      "_hook_timeout_help": "Timeout for hook execution in milliseconds",

      "async_indexing": false,
      "_async_indexing_help": "Return immediately from hook, index in background"
    }
  }
}
```

### 13.9 Story Additions

Add to Section 11.1 (Story Breakdown):

| Story | Description | Priority | Estimate |
|-------|-------------|----------|----------|
| ST-H9 | Implement hook socket server in MCP server | Medium | M |
| ST-H10 | Create session_close_hook.py script | Low | S |
| ST-H11 | Create graphiti_mcp_client.py library | Medium | M |
| ST-H12 | Add Windows named pipe support | Medium | M |
| ST-H13 | Create hook setup/installation utilities | Low | S |
| ST-H14 | Write hook integration tests | Medium | M |
| ST-H15 | Document hook setup in user guide | Low | S |

### 13.10 File Additions

Add to Section 11.2 (File Changes):

| File | Changes |
|------|---------|
| `mcp_server/graphiti_mcp_server.py` | Add hook socket server |
| `~/.graphiti/hooks/session_close_hook.py` | NEW: Hook script |
| `~/.graphiti/hooks/graphiti_mcp_client.py` | NEW: MCP client library |
| `graphiti_core/hooks/__init__.py` | NEW: Hook utilities package |
| `graphiti_core/hooks/setup.py` | NEW: Hook installation utilities |
| `~/.claude/settings.json` | Hook configuration (user file) |

---

**End of Specification**
