# Session 020: MCP Daemon Fallback Architecture Analysis

**Status**: ACTIVE
**Created**: 2025-12-17 15:17
**Objective**: MCP daemon fallback architecture analysis and hybrid transport design

---

## Completed

- Initialized session with MCP tools (graphiti-memory unavailable, claude-context indexed)
- Reviewed sprint state: excluded-paths-v1.0 sprint completed and archived (100%)
- Confirmed last handoff s019 (Temporal BMAD orchestration design - COMPLETE)
- Analyzed unified config schema (`mcp_server/unified_config.py`) - all parameters exposed with safe defaults
- Diagnosed MCP server connection failure: HTTP transport requires daemon running, no stdio fallback by design
- Researched MCP Python SDK documentation on transport behavior (confirmed no built-in fallback)
- Designed hybrid fallback architecture proposal with wrapper script approach

---

## Blocked

None - design analysis complete, awaiting user decision on implementation approach

---

## Next Steps

1. **Short-term (immediate)**: Revert to stdio transport in `claude_desktop_config.json` for immediate MCP connectivity
2. **Long-term (sprint)**: Implement hybrid fallback wrapper script (`graphiti-mcp-connect`) that:
   - Checks daemon health on startup via HTTP
   - Uses stdio-to-HTTP bridge proxy when daemon available
   - Falls back to direct stdio MCP server when daemon unavailable
3. Create sprint story for hybrid fallback implementation if user decides to proceed

---

## Decisions Made

1. **MCP SDK does NOT support automatic transport fallback** - Transport is bound at session initialization, client cannot auto-switch
2. **Fallback logic must live in CLIENT side** - Server cannot control this, Claude Code decides how to connect
3. **Three architecture options identified**:
   - Option A: Client-side fallback (requires Claude Code changes - not feasible)
   - Option B: Hybrid config (manual user config of both transports - poor UX)
   - Option C: Wrapper script (`graphiti-mcp-connect`) - recommended approach
4. **If daemon goes down mid-session**: Connection fails, user must restart Claude Code (no auto-reconnect)
5. **Wrapper script trade-off**: Shared state only when daemon running; per-session isolation when stdio fallback active

---

## Errors Resolved

None - this was an analysis/design session

---

## Context

**Files Analyzed**:
- `mcp_server/unified_config.py` - Full config schema with all parameters exposed
- `mcp_server/daemon/bootstrap.py` - Bootstrap service implementation
- `mcp_server/graphiti_mcp_server.py` - MCP server entry point
- `claude-mcp-installer/instance/CLAUDE_INSTALL.md` - Installation guide with HTTP/stdio instructions
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` - Daemon architecture spec

**Documentation Referenced**:
- MCP Python SDK docs (Context7) - transport, client session, stdio/HTTP patterns
- `.claude/handoff/s019-temporal-bmad-orchestration-design.md` - Previous session context
- `.claude/sprint-archive/excluded-paths-v1.0-2025-12-16-0842/` - Completed sprint

---

## Technical Details

### Current Architecture Problem

```
Claude Code -> HTTP :8321 -> Daemon (NOT RUNNING) -> Connection Refused
```

### Proposed Hybrid Architecture

```
Claude Code -> stdio -> graphiti-mcp-connect (wrapper)
                          |
                          +-- Daemon healthy? -> Proxy stdio <-> HTTP :8321
                          |
                          +-- Daemon down? -> Spawn MCP server directly (stdio)
```

### Key MCP SDK Finding

From SDK docs: Transport is configured at initialization via `stdio_client()` or `streamablehttp_client()`. ClientSession wraps specific transport streams. No automatic fallback mechanism exists.

---

**Session Duration**: ~45 minutes
**Token Usage**: ~35k/200k estimated
**Graphiti Status**: MCP server unavailable (daemon not running - the very issue being analyzed)

---

**NOTE**: This handoff was created with filesystem-only storage (Graphiti MCP unavailable).
Re-index to Graphiti when daemon is running for cross-session semantic search.
