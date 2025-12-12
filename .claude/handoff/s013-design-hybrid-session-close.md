# Session 013: Design Hybrid Session Close Architecture

**Status**: ACTIVE
**Created**: 2025-12-11 22:15
**Objective**: Design hybrid session close architecture with Claude Code hook integration

---

## Completed

- Explored session tracking behavior when enabled globally (file watcher, inactivity timeout, indexing flow)
- Identified duplicate indexing problem when sessions resume after timeout (no deduplication, offset resets to 0)
- Analyzed fundamental tension between fast timeouts (quick handoff but wasted LLM calls) vs slow timeouts (efficient but stale context)
- Designed 4-layer hybrid close architecture:
  1. Explicit close via `session_tracking_close()` MCP tool (primary)
  2. Lazy indexing on query (fallback - only index when next agent searches)
  3. Content-hash deduplication (skip unchanged, replace changed)
  4. Inactivity timeout (last resort for abandoned sessions)
- Created comprehensive spec document: `SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md` with 17 implementation stories
- Added Claude Code hook integration section (SessionEnd hooks for /clear and /compact)
- Designed hook socket server architecture for MCP tool communication from hooks
- Updated global config at `~/.graphiti/graphiti.config.json` with v2.0 namespace fields
- Removed project-local `graphiti.config.json` to enforce singleton configuration pattern

---

## Blocked

None

---

## Next Steps

- Create sprint stories from spec (17 stories: ST-H1 through ST-H17)
- Implement `SessionStateManager` with persistence (ST-H1)
- Implement `session_tracking_close()` MCP tool (ST-H2)
- Implement content hash computation and comparison (ST-H3)
- Implement delete/replace logic in indexer (ST-H4)
- Implement hook socket server in MCP server (ST-H11)
- Create session_close_hook.py script (ST-H12)
- Create graphiti_mcp_client.py library (ST-H13)

---

## Decisions Made

- **Delete/replace over incremental indexing**: LLM summarization output changes based on full context; incremental indexing not feasible because Graphiti entity extraction builds relationships from complete content
- **Singleton global config only**: Removed project-local `graphiti.config.json` to avoid confusion and enforce single source of truth at `~/.graphiti/graphiti.config.json`
- **SessionEnd hooks with socket communication**: Hook scripts can't directly call MCP tools, so MCP server exposes Unix socket (or Windows named pipe) for hook-to-server communication
- **Content hash on filtered content**: Hash computed on filtered content (not raw JSONL) for stability across non-semantic changes
- **30-minute default timeout**: Increased from 15 minutes since primary close mechanism is now explicit; timeout is fallback only
- **Lazy indexing is blocking**: Ensures fresh results when next agent queries; async would complicate UX

---

## Errors Resolved

None - this was a design/specification session

---

## Context

**Files Modified/Created**:
- `.claude/implementation/SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md` (NEW - comprehensive spec)
- `~/.graphiti/graphiti.config.json` (UPDATED - added v2.0 namespace fields, set tool_content: false)
- `graphiti.config.json` (DELETED - removed project-local config)

**Documentation Referenced**:
- `.claude/implementation/GLOBAL_SESSION_TRACKING_SPEC_v2.0.md`
- `docs/SESSION_TRACKING_USER_GUIDE.md`
- `graphiti_core/session_tracking/session_manager.py`
- `graphiti_core/session_tracking/indexer.py`
- `mcp_server/graphiti_mcp_server.py`

---

**Session Duration**: ~1.5 hours
**Token Usage**: ~60k estimated
