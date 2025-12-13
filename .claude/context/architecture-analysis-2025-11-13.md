# Sprint Architecture Analysis - Session Tracking Integration

## Original Design Intent (from comprehensive-session-memory.md)

**Core Flow:**
```
1. JSONL Detection (watchdog)
   └─→ Parse session file incrementally
       └─→ Filter content (93% token reduction)
           └─→ Add episodes directly to Graphiti
               └─→ Let Graphiti's LLM extract entities/relationships
                   └─→ Query graph for session insights
```

**Key Philosophy:**
- **Graphiti does the heavy lifting** - Entity extraction, summarization, relationship building
- **Minimal preprocessing** - Just filter to reduce tokens
- **Direct episode addition** - No intermediate summarization
- **Let the graph learn** - Natural knowledge emergence

**Token Cost Model (Original):**
- Raw JSONL: ~200k tokens/session
- After filtering: ~12k tokens/session (93% reduction)
- Graphiti processing: ~110k tokens total (chunked episodes)
- **Cost: $0.17/session with gpt-4.1-mini**

---

## Current Sprint Implementation (index.md)

**Story Breakdown:**
1. ✅ Foundation (parser, types, path resolver)
2. ✅ Smart Filtering (93% token reduction)
3. ✅ File Monitoring (watchdog, session manager)
4. ✅ **LLM Summarization** (SessionSummarizer + SessionStorage) ← **REDUNDANT**
5. ⏳ CLI Integration
6. ⏳ MCP Tool Integration
7. ⏳ Testing & Validation
8. ⏳ Refinement & Launch

**Current Flow:**
```
1. JSONL Detection (watchdog) ✅
   └─→ Parse session file ✅
       └─→ Filter content ✅
           └─→ **Summarize with LLM** ❌ REDUNDANT
               └─→ **Create markdown handoff file** ❌ REDUNDANT
                   └─→ Store summary in Graphiti ❌ WRONG APPROACH
```

---

## Identified Redundancies

### 🔴 MAJOR: Story 4 - LLM Summarization (REDUNDANT)

**Problem:**
- We're running our own LLM to create summaries
- Graphiti already does this automatically via `add_episode()`
- We're pre-summarizing what the graph should learn from raw data

**Evidence:**
- `SessionSummarizer` uses Graphiti's LLM client to extract structured summaries
- Creates intermediate markdown files (filesystem duplication)
- Then stores summaries in Graphiti (when we should store filtered raw content)

**Impact:**
- ❌ Doubled LLM costs (summarize + Graphiti's entity extraction)
- ❌ Loss of granularity (graph learns from summaries, not original content)
- ❌ Filesystem bloat (handoff markdown files duplicate graph data)
- ❌ Maintenance burden (two storage systems to sync)

**Solution:**
```python
# Current (wrong):
summary = await summarizer.summarize_session(context, filtered_content)
markdown = summary.to_markdown()
write_file(handoff_path, markdown)  # Filesystem copy
await storage.store_session(summary)  # Graph copy

# Should be (right):
await graphiti.add_episode(
    name=f"Session {seq_num}",
    episode_body=filtered_content,  # Direct from SessionFilter
    source=EpisodeType.text,
    group_id=group_id
)
# Graphiti handles: entity extraction, summarization, relationships
```

---

### 🟡 MODERATE: Markdown Handoff Files (OPTIONAL, not required)

**Problem:**
- Original design mentions handoff files as **user-facing convenience**, not core infrastructure
- Sprint treats them as mandatory storage layer alongside Graphiti

**Evidence from design:**
> "Future agents query: 'What were we working on last session?'"
> → Query the **graph**, not handoff files

**Recommendation:**
- **Keep handoff files as opt-in CLI feature** (`graphiti session export-handoff`)
- **Remove from core flow** (don't auto-generate)
- **Use graph as source of truth** for queries

---

### 🟢 MINOR: ConversationContext dataclass (MAY BE OVERKILL)

**Current:** Comprehensive `ConversationContext` with 10+ fields
```python
@dataclass
class ConversationContext:
    messages: List[SessionMessage]
    session_id: str
    project_root: Path
    created_at: datetime
    updated_at: datetime
    total_tokens: int
    mcp_tools_used: Set[str]
    files_modified: Set[str]
    # ... etc
```

**Question:** Do we need all this structure, or can we pass simpler data?
- Graphiti extracts most metadata automatically from episode content
- May be simpler to pass `(session_id, filtered_content)` directly

**Not urgent** - current implementation works, just more complex than needed.

---

## Architectural Recommendations

### Immediate Changes (Story 4 Simplification)

**1. Remove SessionSummarizer class**
- Delete `summarizer.py` and tests
- Graphiti's `add_episode()` handles summarization

**2. Simplify SessionStorage**
- Rename to `SessionIndexer` (more accurate)
- Single method: `index_session(session_id, filtered_content, group_id)`
- Calls `graphiti.add_episode()` directly
- No markdown generation in core flow

**3. Make handoff files optional**
- Move to separate module `handoff_exporter.py`
- CLI command: `graphiti session export-handoff --session-id X`
- Not part of automatic flow

### Simplified Architecture

**Core Flow (Correct):**
```
SessionFileWatcher (Story 3)
  └─→ Detects new .jsonl files
      └─→ JSONLParser (Story 1)
          └─→ Parse messages incrementally
              └─→ SessionFilter (Story 2)
                  └─→ Filter to 93% reduction
                      └─→ SessionIndexer (Story 4 - simplified)
                          └─→ graphiti.add_episode(filtered_content)
                              └─→ Graphiti extracts entities/relationships
```

**CLI Tools (Story 5):**
```
graphiti session enable         # Enable automatic session tracking
graphiti session disable        # Disable tracking
graphiti session status         # Show tracking status
graphiti session export-handoff # Optional: Create markdown handoff file
```

**MCP Tools (Story 6):**
```
track_session()              # Enable for current session
stop_tracking_session()      # Disable for current session  
get_session_tracking_status() # Check status
query_session_history()       # NEW: Search past sessions in graph
```

---

## Cost Analysis Correction

**Original Design Target:** $0.17/session
**Current Implementation:** ~$0.46/session (doubled due to extra LLM call)

**After Simplification:** $0.17/session (matches original design)

---

## Next Steps

1. ✅ Identify redundancies (this document)
2. ⏳ Propose simplified Story 4 implementation
3. ⏳ Update sprint index with architectural changes
4. ⏳ Refactor Story 4 code (remove summarizer, simplify storage)
5. ⏳ Continue with Stories 5-8 using corrected architecture