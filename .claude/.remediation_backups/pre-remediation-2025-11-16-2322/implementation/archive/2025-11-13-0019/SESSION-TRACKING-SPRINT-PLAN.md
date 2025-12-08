# Session Tracking Sprint Plan - Graphiti

## Executive Summary

**Goal**: Integrate automatic JSONL session tracking into Graphiti MCP server with CLI opt-in/out and runtime toggle capabilities.

**Source**: Extract and refactor modules from claude-window-watchdog project
**Priority**: Session tracking first (foundation infrastructure supports independent implementation)
**Cost**: ~$0.03-$0.50 per session (highly acceptable, likely overestimated)

## Extracted Modules Analysis

### From claude-window-watchdog:
1. **daemon/parser.py** (~243 lines)
   - JSONLParser class - parses JSONL entries
   - TokenCounts dataclass - tracks API token usage
   - MessageData dataclass - structured message representation
   - Incremental parsing with offset tracking

2. **daemon/watcher.py** (~335 lines)
   - ClaudeFileWatcher - watchdog-based file monitoring
   - JSONLFileHandler - event processing
   - Auto-discovery of new session files
   - Incremental offset management

**Refactoring Needed**:
- Remove SQLite database dependencies (use Graphiti graph instead)
- Extract JSONL path resolution logic
- Add LLM-based summarization (not in watchdog)
- Remove billing/token cost tracking (not needed for Graphiti)
- Add filtering logic per handoff docs (93% token reduction)

## Dependency Graph

```
Layer 1: Core Infrastructure (No dependencies)
├─ graphiti_core/session_tracking/__init__.py
├─ graphiti_core/session_tracking/types.py (dataclasses)
└─ graphiti_core/session_tracking/utils.py (path resolution)

Layer 2: JSONL Processing (depends on Layer 1)
├─ graphiti_core/session_tracking/parser.py (JSONLParser)
├─ graphiti_core/session_tracking/filter.py (Smart filtering, 93% reduction)
└─ graphiti_core/session_tracking/path_resolver.py (Claude Code path mapping)

Layer 3: Monitoring (depends on Layer 2)
├─ graphiti_core/session_tracking/watcher.py (File monitoring)
└─ graphiti_core/session_tracking/session_manager.py (Orchestration)

Layer 4: Summarization (depends on Layer 2)
├─ graphiti_core/session_tracking/summarizer.py (LLM summarization)
└─ graphiti_core/session_tracking/graphiti_storage.py (Graph persistence)

Layer 5: Integration (depends on Layers 3+4)
├─ mcp_server/session_tracking_service.py (MCP integration)
├─ mcp_server/cli_commands.py (CLI opt-in/out)
└─ Updated: mcp_server/graphiti_mcp_server.py (MCP tool registration)
```

## Implementation Order

### Phase 1: Foundation (Week 1, Days 1-2)
**Goal**: Core infrastructure + basic JSONL parsing

**Tasks**:
1. Create `graphiti_core/session_tracking/` module structure
2. Extract and refactor `types.py`:
   - SessionMessage dataclass (from MessageData)
   - ConversationContext dataclass (new)
   - SessionMetadata dataclass (new)
3. Extract and refactor `parser.py`:
   - Remove SQLite dependencies
   - Keep incremental parsing logic
   - Add tool call extraction (MCP-specific)
4. Implement `path_resolver.py`:
   - Resolve `~/.claude/projects/{hash}/sessions/`
   - Project root → hash mapping
   - Cross-platform path handling (Windows/Unix)
5. Unit tests for parser + path resolver

**Deliverable**: Can parse JSONL files and extract messages

### Phase 2: Smart Filtering (Week 1, Days 3-4)
**Goal**: 93% token reduction filtering per handoff design

**Tasks**:
1. Implement `filter.py`:
   - Keep: user/assistant messages (full)
   - Keep: tool call structure (name + params)
   - Omit: tool outputs (replace with summary)
   - Extract MCP tool interactions
2. Add filtering rules from `.claude/implementation/session-tracking-solutions.md`:
   - User messages: KEEP (full)
   - Agent responses: KEEP (full)
   - Tool use blocks: KEEP (structure only)
   - Tool results: OMIT (create 1-line summary)
3. Token counting (rough estimate for logging)
4. Unit tests for filtering

**Deliverable**: Filtered session reduces 205k → ~13.5k tokens

### Phase 3: File Monitoring (Week 1, Days 5-7)
**Goal**: Watchdog-based automatic session detection

**Tasks**:
1. Extract and refactor `watcher.py`:
   - Remove database storage (use callbacks)
   - Keep offset tracking logic
   - Add session lifecycle detection (start/close)
2. Implement `session_manager.py`:
   - Track active sessions (in-memory registry)
   - Detect session close (no activity for N seconds)
   - Trigger summarization on close
   - Handle auto-compaction (new JSONL file = continuation)
3. Add configuration:
   - `session_tracking.enabled` (global default)
   - `session_tracking.auto_summarize_on_close` (boolean)
   - `session_tracking.inactivity_timeout` (seconds)
4. Integration tests with mock JSONL files

**Deliverable**: Auto-detects and monitors session JSONL files

### Phase 4: LLM Summarization (Week 2, Days 1-3)
**Goal**: LLM-based session summarization → Graphiti storage

**Tasks**:
1. Implement `summarizer.py`:
   - Use existing Graphiti LLM client
   - Prompt template from handoff docs
   - Extract:
     * Session objective
     * Work completed (files, functions, bugs)
     * External research (tools, findings)
     * Knowledge stored (Graphiti entities)
     * Decisions made
     * Unresolved issues
     * Next steps
     * Continuation context
2. Implement `graphiti_storage.py`:
   - Store session as EpisodicNode
   - Metadata: token_count, mcp_tools_used, files_modified
   - Relations: preceded_by, continued_by, spawned_agent
   - Content: LLM-generated summary
3. Cost tracking (log actual LLM costs)
4. Integration test with real Graphiti instance

**Deliverable**: Closed sessions automatically summarized and stored in graph

### Phase 5: CLI Integration (Week 2, Days 4-5)
**Goal**: Global opt-in/out commands

**Tasks**:
1. Add CLI commands (integrate with existing MCP server CLI):
   ```bash
   graphiti-mcp session-tracking enable
   graphiti-mcp session-tracking disable
   graphiti-mcp session-tracking status
   ```
2. Persistent configuration storage:
   - Use `graphiti.config.json` (unified config)
   - Section: `session_tracking.enabled` (boolean)
   - Apply on MCP server startup
3. Update `mcp_server/unified_config.py`:
   - Add `SessionTrackingConfig` schema
   - Validation logic
4. Documentation:
   - Update CONFIGURATION.md
   - Add session tracking section
   - Cost estimates and opt-out instructions

**Deliverable**: Users can globally enable/disable session tracking

### Phase 6: MCP Tool Integration (Week 2, Days 6-7)
**Goal**: Runtime toggle via MCP tool call

**Tasks**:
1. Add MCP tools to `mcp_server/graphiti_mcp_server.py`:
   ```python
   @mcp.tool()
   def track_session(group_id: str, force: bool = False):
       \"\"\"
       Enable session tracking for current session.
       
       Args:
           group_id: Graphiti group ID for session storage
           force: Force tracking even if globally disabled
       \"\"\"
   
   @mcp.tool()
   def stop_tracking_session(session_id: str):
       \"\"\"Stop tracking for specific session.\"\"\"
   
   @mcp.tool()
   def get_session_tracking_status() -> dict:
       \"\"\"Get current tracking status.\"\"\"
   ```
2. Session registry (in-memory):
   - Track active sessions being monitored
   - Per-session enable/disable state
   - Override global config if `force=True`
3. Integration with `session_manager.py`:
   - Start monitoring on `track_session()` call
   - Stop monitoring on `stop_tracking_session()` call
   - Respect global config vs per-session override
4. Agent-friendly tool descriptions

**Deliverable**: Agent can enable tracking mid-session

### Phase 7: Testing & Validation (Week 3, Days 1-3)
**Goal**: Comprehensive testing and cost validation

**Tasks**:
1. End-to-end integration tests:
   - Full workflow: detect → parse → filter → summarize → store
   - Multiple sessions (sequential and parallel)
   - Auto-compaction detection
   - Agent spawning (parent-child linkage)
2. Cost measurement:
   - Real session data from test conversations
   - Actual OpenAI API costs
   - Validate against projections ($0.03-$0.50/session)
3. Performance testing:
   - Large sessions (100+ exchanges)
   - Multiple concurrent sessions
   - File watcher overhead
4. Documentation:
   - User guide: How to use session tracking
   - Developer guide: Architecture and extension points
   - Troubleshooting guide

**Deliverable**: Production-ready, validated implementation

### Phase 8: Refinement & Launch (Week 3, Days 4-5)
**Goal**: Polish and release

**Tasks**:
1. Code review and refactoring
2. Add logging and debugging aids
3. Error handling improvements
4. Update README.md with session tracking features
5. Create migration guide (for existing users)
6. Release notes

**Deliverable**: Released to production

## Architecture Decisions

### CLI + MCP Integration Pattern

**Three-tier control system**:

1. **Global Config** (CLI-managed, persistent):
   ```json
   {
     "session_tracking": {
       "enabled": false,  // Default: opt-in required
       "auto_summarize_on_close": true,
       "inactivity_timeout": 300  // 5 minutes
     }
   }
   ```

2. **MCP Server State** (runtime, non-persistent):
   - Reads global config on startup
   - Applies to all sessions by default
   - Can be overridden per-session

3. **Per-Session Override** (MCP tool, runtime):
   - `track_session(force=True)` → Enable for this session only
   - Stored in session registry (in-memory)
   - Lost on server restart (intentional)

**Decision Flow**:
```
New session detected
  ├─ Check global config: enabled?
  │  ├─ YES → Start tracking
  │  └─ NO → Skip tracking
  │
  └─ Agent calls track_session(force=True)?
     └─ YES → Override, start tracking
```

**Use Cases**:
- **User wants all sessions tracked**: `graphiti-mcp session-tracking enable`
- **User wants opt-out by default, manual opt-in**: Keep `enabled: false`, use `track_session()` tool
- **User wants to disable mid-session**: `stop_tracking_session(session_id)`

### Storage Architecture

**Session as EpisodicNode**:
```python
episode = EpisodicNode(
    name=f"session_{session_id}",
    content=llm_summary,  // LLM-generated structured summary
    source="claude_code_jsonl",
    source_description="Claude Code conversation session",
    created_at=session_start,
    valid_at=session_end,
    group_ids=[group_id],
    metadata={
        "session_id": session_id,
        "project_root": project_root,
        "message_count": 42,
        "token_count": 15234,
        "mcp_tools_used": ["serena", "graphiti"],
        "files_modified": ["auth.py", "config.py"],
        "unresolved_issues": ["Test JWT timeout"],
        "next_steps": ["Implement Phase 2"]
    }
)
```

**Relations**:
- `preceded_by`: Link to previous session (auto-compaction)
- `continued_by`: Link to next session (auto-compaction)
- `spawned_agent`: Link to child agent sessions
- `modified_file`: Link to file entities (if filesystem tracking exists)

### Cost Projections (Revised)

Based on handoff docs + user experience with gptr-mcp:

**Per Session** (1 hour, 20 exchanges):
- Filtering: 205k → 13.5k tokens (93% reduction)
- Graphiti processing: ~34k tokens (with batching)
- LLM cost (gpt-4.1-mini): ~$0.03-$0.10
- **Total**: ~$0.03-$0.50/session (likely closer to $0.03)

**Monthly** (60 sessions):
- $1.80-$30/month
- **Expected**: ~$2-$5/month (conservative estimate)

**Highly acceptable** per user feedback.

## Risk Mitigation

1. **Risk**: Token costs exceed $0.50/session
   - **Mitigation**: More aggressive filtering, configurable batch size

2. **Risk**: JSONL format changes (Claude Code updates)
   - **Mitigation**: Version detection, graceful degradation, parser tests

3. **Risk**: File watcher performance issues
   - **Mitigation**: Debouncing, async processing, configurable polling

4. **Risk**: Privacy concerns (conversation tracking)
   - **Mitigation**: Opt-in by default, clear documentation, user control

5. **Risk**: Cross-platform path resolution failures
   - **Mitigation**: Extensive path testing (Windows/Unix/WSL), fallback logic

## Success Criteria

**Must Have**:
- ✅ JSONL parsing works reliably (cross-platform)
- ✅ 90%+ token reduction from filtering
- ✅ LLM summarization preserves context
- ✅ CLI opt-in/out works correctly
- ✅ MCP tool runtime toggle works
- ✅ Costs remain under $0.50/session

**Should Have**:
- ✅ Auto-detects session close (inactivity timeout)
- ✅ Handles auto-compaction (session continuation)
- ✅ Agent spawning detection (parent-child linkage)
- ✅ No performance degradation for MCP server

**Nice to Have**:
- ⭐ Query interface for session history
- ⭐ Workflow pattern recognition
- ⭐ Cross-session decision tracking

## Next Steps

1. Review this plan with user
2. Create GitHub issues/milestones (optional)
3. Begin Phase 1 implementation
4. Daily standups to track progress (via handoff docs)

## Timeline

- **Week 1**: Foundation + Filtering + Monitoring (Phases 1-3)
- **Week 2**: Summarization + CLI + MCP Integration (Phases 4-6)
- **Week 3**: Testing + Refinement + Launch (Phases 7-8)

**Total**: ~15-18 days for full implementation