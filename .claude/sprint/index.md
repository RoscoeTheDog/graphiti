# Implementation Sprint: Session Tracking Hybrid Close

**Version**: v3.1.0
**Created**: 2025-12-11 22:28
**Base Branch**: dev
**Status**: Active
**Spec**: [SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md](../implementation/SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md)

## Sprint Goal

Implement a hybrid approach to session close detection that eliminates wasted LLM calls while ensuring timely context handoff between agents. The architecture combines explicit signals, lazy indexing, content-based deduplication, and inactivity timeout as a layered fallback system.

## Key Decisions

- **Delete/replace over incremental indexing**: LLM summarization output changes based on full context
- **Lazy indexing is blocking**: Ensures fresh results when next agent queries
- **Hash on filtered content**: Stability across non-semantic JSONL changes
- **30-minute default timeout**: Primary close is explicit; timeout is fallback
- **Socket/pipe communication**: Hook scripts communicate with MCP server via IPC

---

## Stories

### Core Implementation (High Priority)

### Story 1: SessionStateManager with Persistence
**Status**: unassigned | **Priority**: High | **Size**: M
**See**: [stories/1-session-state-manager.md](stories/1-session-state-manager.md)

### Story 2: session_tracking_close() MCP Tool
**Status**: unassigned | **Priority**: High | **Size**: S
**See**: [stories/2-session-tracking-close-tool.md](stories/2-session-tracking-close-tool.md)

### Story 3: Content Hash Computation
**Status**: unassigned | **Priority**: High | **Size**: S
**See**: [stories/3-content-hash-computation.md](stories/3-content-hash-computation.md)

### Story 4: Delete/Replace Logic in Indexer
**Status**: unassigned | **Priority**: High | **Size**: M
**See**: [stories/4-delete-replace-indexer.md](stories/4-delete-replace-indexer.md)

### Story 5: Lazy Indexing in Search Tools
**Status**: unassigned | **Priority**: Medium | **Size**: M
**See**: [stories/5-lazy-indexing-search.md](stories/5-lazy-indexing-search.md)

### Story 6: session_tracking_list_unindexed() Tool
**Status**: unassigned | **Priority**: Low | **Size**: S
**See**: [stories/6-list-unindexed-tool.md](stories/6-list-unindexed-tool.md)

### Story 7: Configuration Schema Updates
**Status**: unassigned | **Priority**: Medium | **Size**: S
**See**: [stories/7-configuration-schema.md](stories/7-configuration-schema.md)

### Story 8: Update ensure_global_config_exists()
**Status**: unassigned | **Priority**: Medium | **Size**: S
**See**: [stories/8-ensure-global-config.md](stories/8-ensure-global-config.md)

### Story 9: Integration Tests for Hybrid Flow
**Status**: unassigned | **Priority**: High | **Size**: L
**See**: [stories/9-integration-tests.md](stories/9-integration-tests.md)

### Story 10: Documentation Updates
**Status**: unassigned | **Priority**: Medium | **Size**: M
**See**: [stories/10-documentation.md](stories/10-documentation.md)

---

### Hook Integration (Medium Priority)

### Story 11: Hook Socket Server in MCP Server
**Status**: unassigned | **Priority**: Medium | **Size**: M
**See**: [stories/11-hook-socket-server.md](stories/11-hook-socket-server.md)

### Story 12: session_close_hook.py Script
**Status**: unassigned | **Priority**: Medium | **Size**: S
**See**: [stories/12-session-close-hook-script.md](stories/12-session-close-hook-script.md)

### Story 13: graphiti_mcp_client.py Library
**Status**: unassigned | **Priority**: Medium | **Size**: M
**See**: [stories/13-mcp-client-library.md](stories/13-mcp-client-library.md)

### Story 14: Windows Named Pipe Support
**Status**: unassigned | **Priority**: Low | **Size**: M
**See**: [stories/14-windows-named-pipe.md](stories/14-windows-named-pipe.md)

### Story 15: Hook Setup/Installation Utilities
**Status**: unassigned | **Priority**: Medium | **Size**: S
**See**: [stories/15-hook-setup-utilities.md](stories/15-hook-setup-utilities.md)

### Story 16: Hook Integration Tests
**Status**: unassigned | **Priority**: Medium | **Size**: M
**See**: [stories/16-hook-integration-tests.md](stories/16-hook-integration-tests.md)

### Story 17: Document Hook Setup in User Guide
**Status**: unassigned | **Priority**: Medium | **Size**: S
**See**: [stories/17-hook-documentation.md](stories/17-hook-documentation.md)

---

## Dependency Graph

```
         ┌─────┐
         │  1  │ SessionStateManager
         └──┬──┘
      ┌─────┼─────┬─────┐
      ▼     ▼     ▼     ▼
   ┌───┐ ┌───┐ ┌───┐ ┌───┐
   │ 2 │ │ 3 │ │ 5 │ │ 6 │
   └─┬─┘ └─┬─┘ └───┘ └───┘
     │     │
     └──┬──┘
        ▼
     ┌───┐
     │ 4 │ Delete/Replace
     └─┬─┘
       │
       ▼
     ┌───┐
     │ 9 │ Integration Tests
     └───┘

   ┌───┐     ┌───┐
   │ 7 │────▶│ 8 │ Config
   └─┬─┘     └───┘
     │
     ▼
   ┌────┐    ┌────┐    ┌────┐
   │ 11 │───▶│ 12 │───▶│ 15 │
   └──┬─┘    └─┬──┘    └──┬─┘
      │        │          │
      ▼        ▼          ▼
   ┌────┐   ┌────┐     ┌────┐
   │ 13 │   │ 14 │     │ 16 │
   └────┘   └────┘     └────┘
                          │
                          ▼
                       ┌────┐
                       │ 17 │ Docs
                       └────┘

   ┌────┐
   │ 10 │ Core Docs (parallel)
   └────┘
```

---

## Recommended Execution Order

**Phase 1: Foundation** (Stories 1, 3, 7)
- Can be done in parallel
- No external dependencies

**Phase 2: Core Tools** (Stories 2, 4, 8)
- Depend on Phase 1
- Implement explicit close and delete/replace

**Phase 3: Lazy Indexing** (Stories 5, 6)
- Depend on Phase 1-2
- Complete core hybrid close

**Phase 4: Testing & Docs** (Stories 9, 10)
- Integration tests after core complete
- Documentation in parallel

**Phase 5: Hook Integration** (Stories 11-17)
- Can start after Phase 2
- Independent feature track

---

*Generated by /sprint:CREATE_SPRINT v3.1.0*
