# Story 5: Claude Code Integration (HTTP Transport)

**Status**: unassigned
**Created**: 2025-12-13 23:51

## Description

Update Claude Code configuration to use HTTP transport instead of stdio, connecting to the daemon. This enables the many-to-one architecture where multiple Claude Code sessions share a single MCP server.

## Acceptance Criteria

- [ ] (P0) `claude_desktop_config.json` template updated for HTTP transport with correct URL format
- [ ] (P0) Claude Code sessions successfully connect to daemon via HTTP
- [ ] (P1) Multiple Claude Code sessions share state through single daemon
- [ ] (P1) Session tracking aggregates data across all connected sessions
- [ ] (P2) Documentation for migrating from stdio to HTTP transport

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
