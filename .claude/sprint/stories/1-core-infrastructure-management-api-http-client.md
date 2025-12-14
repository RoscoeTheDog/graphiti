# Story 1: Core Infrastructure (Management API + HTTP Client)

**Status**: unassigned
**Created**: 2025-12-13 23:51

## Description

Add Management API endpoints and create HTTP client library for CLI/tools to communicate with daemon. This is the foundation layer that all other components will use to interact with the MCP server.

## Acceptance Criteria

- [ ] (P0) Management API endpoints implemented: `/api/v1/status`, `/api/v1/session/sync`, `/api/v1/session/history`, `/api/v1/config`, `/api/v1/config/reload`
- [ ] (P0) `GraphitiClient` HTTP client class created with methods for all API operations
- [ ] (P1) Daemon config schema added to `unified_config.py` with Pydantic validation
- [ ] (P1) Auto-discovery logic implemented (env var → config file → default URL)
- [ ] (P2) Client includes proper timeout handling and connection error detection

## Dependencies

None

## Implementation Notes

**Key Files to Create/Modify**:
- `mcp_server/api/management.py` - Management API endpoints
- `mcp_server/api/client.py` - GraphitiClient HTTP client
- `mcp_server/unified_config.py` - Add daemon config schema
- `mcp_server/graphiti_mcp_server.py` - Mount management API routes

**Reference**: See `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` for full specification.

## Related Stories

- Story 2 depends on this (Bootstrap Service)
- Story 3 depends on this (CLI Refactoring)
- Story 5 depends on this (Claude Code Integration)
