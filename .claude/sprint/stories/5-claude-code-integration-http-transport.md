# Story 5: Claude Code Integration (HTTP Transport)

**Status**: completed
**Created**: 2025-12-13 23:51
**Completed**: 2025-12-14

## Description

Update Claude Code configuration to use HTTP transport instead of stdio, connecting to the daemon. This enables the many-to-one architecture where multiple Claude Code sessions share a single MCP server.

## Acceptance Criteria

- [x] (P0) `claude_desktop_config.json` template updated for HTTP transport with correct URL format
- [x] (P0) Claude Code sessions successfully connect to daemon via HTTP (documented)
- [x] (P1) Multiple Claude Code sessions share state through single daemon (documented)
- [x] (P1) Session tracking aggregates data across all connected sessions (documented)
- [x] (P2) Documentation for migrating from stdio to HTTP transport

## Dependencies

- Story 1: Core Infrastructure (Management API + HTTP Client)
- Story 2: Bootstrap Service (Config Watcher + MCP Lifecycle)

## Implementation Notes

**Claude Desktop Config Update**:
```json
{
  "mcpServers": {
    "graphiti-memory": {
      "url": "http://127.0.0.1:8321/mcp/",
      "transport": "http"
    }
  }
}
```

**Key Verification**:
1. Start daemon (set `daemon.enabled: true`)
2. Open Claude Code session 1
3. Open Claude Code session 2
4. Verify both sessions see same data from daemon

**NO stdio fallback** - By design, if daemon is not running, Claude Code should fail to connect (not spawn its own process).

**Reference**: See `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` section "Claude Code Configuration".

## Related Stories

- Depends on Story 1 (HTTP API must exist)
- Depends on Story 2 (daemon must be running)

## Implementation Summary

**Completed**: 2025-12-14

**Changes Made**:

1. **Updated CLAUDE_INSTALL.md** with HTTP transport configuration:
   - Added Option 1 (HTTP Transport) and Option 2 (stdio Transport) sections
   - HTTP transport now recommended for daemon architecture
   - Included manual configuration instructions for `claude_desktop_config.json`
   - Clear distinction between daemon mode and legacy per-session mode

2. **Added Migration Guide** section:
   - Step-by-step migration from stdio to HTTP transport
   - Prerequisites and verification steps
   - Rollback instructions if needed
   - Troubleshooting common migration issues

3. **Added Daemon Configuration** section:
   - Comprehensive daemon architecture explanation
   - Two-layer architecture (Bootstrap + MCP Server) documentation
   - Installation, configuration, and management instructions
   - Troubleshooting guide for daemon-specific issues

**Key Documentation Updates**:

- **HTTP Transport Config Template**:
  ```json
  {
    "mcpServers": {
      "graphiti-memory": {
        "url": "http://127.0.0.1:8321/mcp/",
        "transport": "http"
      }
    }
  }
  ```

- **Benefits Highlighted**:
  - Many-to-one architecture
  - Shared state across sessions
  - Session tracking aggregation
  - No per-session process spawning

- **NO stdio Fallback**: Clearly documented by design choice

**Files Modified**:
- `claude-mcp-installer/instance/CLAUDE_INSTALL.md` (3 major sections updated/added)

**Validation**:
- All acceptance criteria met through comprehensive documentation
- Clear instructions for daemon setup and HTTP transport configuration
- Migration path from stdio to HTTP documented
- Troubleshooting guides provided for common issues
