# Story 11: Hook Socket Server in MCP Server (ST-H11)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: M

## Description

Implement a Unix socket server (or Windows named pipe) in the MCP server that allows external scripts (like Claude Code hooks) to call MCP tools directly.

## Acceptance Criteria

- [ ] (P0) Implement `start_hook_socket_server()` async function
- [ ] (P0) Create socket at `~/.graphiti/mcp.sock` (Unix) or named pipe (Windows)
- [ ] (P0) Handle JSON-RPC requests for session_tracking_close tool
- [ ] (P1) Clean up stale socket on startup
- [ ] (P1) Graceful shutdown when MCP server stops
- [ ] (P2) Support configurable socket path via config

## Dependencies

- Story 2: session_tracking_close() tool (to route requests)
- Story 7: Configuration (for hooks.socket_path config)

## Implementation Notes

- Location: `mcp_server/graphiti_mcp_server.py` (add socket server)
- See Section 13.5 of spec for implementation details
- Start socket server alongside MCP server in main()

## Related Stories

- Depends on: Story 2, Story 7
- Used by: Story 12 (hook script), Story 13 (MCP client)
