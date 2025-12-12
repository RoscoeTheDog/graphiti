# Story 14: Windows Named Pipe Support (ST-H14)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Low
**Estimate**: M

## Description

Add Windows named pipe support for hook-to-server communication, since Unix sockets are not available on Windows.

## Acceptance Criteria

- [ ] (P0) Detect platform and use named pipe on Windows (`\\.\pipe\graphiti_mcp_hook`)
- [ ] (P0) Update `start_hook_socket_server()` for Windows pipe support
- [ ] (P0) Update `GraphitiMCPClient.connect()` for Windows pipe support
- [ ] (P1) Test hook communication on Windows
- [ ] (P2) Document platform differences in user guide

## Dependencies

- Story 11: Hook socket server (base implementation)
- Story 13: MCP client library (client-side)

## Implementation Notes

- See Section 13.5.2 of spec for Windows pipe path
- Use asyncio pipe support on Windows
- Consider using `asyncio.open_connection()` with named pipe path

## Related Stories

- Extends: Story 11, Story 13
- Critical for Windows users
