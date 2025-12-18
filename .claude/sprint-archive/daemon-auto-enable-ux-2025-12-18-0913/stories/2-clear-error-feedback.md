# Story 2: Clear Error Feedback for Connection Failures

**Status**: unassigned
**Created**: 2025-12-17 15:28

## Description

Add actionable error messages when MCP server connection fails, guiding users to install the daemon or check its status.

## Acceptance Criteria

- [ ] (P0) When HTTP connection to :8321 fails, error message includes: "Daemon not running. Run: graphiti-mcp daemon install"
- [ ] (P0) When daemon is installed but not enabled, error message includes path to config file
- [ ] (P1) Error messages are visible in Claude Code logs (stderr output)
- [ ] (P2) Add health check endpoint response that indicates daemon state for debugging

## Dependencies

None

## Implementation Notes

**Key Files**:
- `mcp_server/graphiti_mcp_server.py` - Server startup and error handling
- `mcp_server/daemon/bootstrap.py` - Bootstrap service logging

**Implementation Approach**:
1. Add startup banner with connection info to stderr
2. Enhance health check response with daemon state information
3. Add connection failure handler with actionable error messages
4. Ensure errors propagate to Claude Code's MCP server logs

**Error Message Templates**:
```
❌ Graphiti MCP Server: Connection failed on port 8321

Possible causes:
  1. Daemon not installed: Run 'graphiti-mcp daemon install'
  2. Daemon not enabled: Edit ~/.graphiti/graphiti.config.json
     Set: "daemon": { "enabled": true }
  3. Port conflict: Check if another service is using port 8321

Check status: graphiti-mcp daemon status
View logs: graphiti-mcp daemon logs
```

## Related Stories

- Story 1: Auto-Enable (reduces need for error case 2)
