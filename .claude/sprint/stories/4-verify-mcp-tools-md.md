# Story 4: Verify/Update MCP_TOOLS.md

**Priority**: P1
**Estimated Tokens**: ~8K read + ~3K write
**Status**: pending

---

## Objective

Verify `docs/MCP_TOOLS.md` accurately documents all current MCP tools and their signatures.

---

## Source Documents

1. `mcp_server/graphiti_mcp_server.py` - Actual tool implementations
2. `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` - Daemon-related tools

---

## Target Document

`docs/MCP_TOOLS.md`

---

## Key Changes Required

### 1. Transport Options Section
- **Current**: Documents both HTTP and stdio
- **Verify**: stdio still supported? Or deprecated?

### 2. Core Memory Tools
Verify these tools and their signatures:
- `add_memory`
- `search_memory_nodes`
- `search_memory_facts`
- `get_episodes`
- `delete_episode`
- `delete_entity_edge`
- `clear_graph`

### 3. Session Tracking Tools
Verify current state:
- `session_tracking_status` - should exist (read-only)
- `session_tracking_start` - removed in v1.0.0?
- `session_tracking_stop` - removed in v1.0.0?

### 4. Daemon Tools
Add if not documented:
- `daemon_status` (if exists)
- Any other daemon management tools

### 5. Health/Diagnostics Tools
Verify:
- `health_check`
- Any new diagnostic tools

---

## Acceptance Criteria

- [ ] All tools in code are documented
- [ ] All documented tools exist in code
- [ ] Tool signatures (parameters, return types) match implementation
- [ ] Examples are accurate and working
- [ ] Deprecated tools marked or removed
- [ ] Last Updated date set to current date
