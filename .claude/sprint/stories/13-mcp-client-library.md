# Story 13: graphiti_mcp_client.py Library (ST-H13)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: M

## Description

Create a lightweight MCP client library that hook scripts can use to communicate with the running Graphiti MCP server via socket.

## Acceptance Criteria

- [ ] (P0) Create `GraphitiMCPClient` class with async context manager
- [ ] (P0) Implement `connect()` to open socket connection
- [ ] (P0) Implement `call_tool(tool_name, arguments)` to send JSON-RPC requests
- [ ] (P1) Implement `disconnect()` with proper cleanup
- [ ] (P1) Handle connection errors gracefully (raise ConnectionError)
- [ ] (P2) Support both Unix socket and Windows named pipe

## Dependencies

- Story 11: Hook socket server (provides socket endpoint)

## Implementation Notes

- Location: `~/.graphiti/hooks/graphiti_mcp_client.py` (install location)
- Source in package: `graphiti_core/hooks/graphiti_mcp_client.py`
- See Section 13.4.3 of spec for implementation
- Lightweight, minimal dependencies (stdlib only)

## Related Stories

- Depends on: Story 11
- Used by: Story 12
