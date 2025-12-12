# Story 16: Hook Integration Tests (ST-H16)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: M

## Description

Write integration tests for the Claude Code hook integration, covering socket communication, hook script execution, and end-to-end flow.

## Acceptance Criteria

- [ ] (P0) Test `test_socket_server_starts`: Socket server starts with MCP server
- [ ] (P0) Test `test_mcp_client_connects`: GraphitiMCPClient connects to socket
- [ ] (P0) Test `test_hook_calls_close`: Hook script successfully calls session_tracking_close
- [ ] (P1) Test `test_hook_handles_server_unavailable`: Hook returns success when server down
- [ ] (P1) Test `test_hook_timeout`: Hook respects timeout setting
- [ ] (P2) Test `test_windows_named_pipe`: Named pipe works on Windows (skip on Unix)

## Dependencies

- Story 11-13: Hook infrastructure complete

## Implementation Notes

- Location: `tests/session_tracking/test_hooks.py` (NEW)
- Use subprocess to test hook script execution
- Mock Claude Code hook input format

## Related Stories

- Depends on: Stories 11-13
- Validates: Hook integration feature
