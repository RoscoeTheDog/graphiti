# Story 2: Bootstrap Service (Config Watcher + MCP Lifecycle)

**Status**: completed
**Created**: 2025-12-13 23:51

## Description

Create the config-watching bootstrap layer that manages MCP server lifecycle based on `daemon.enabled` flag. The bootstrap service runs as an OS-level service and polls the config file to detect state changes.

## Acceptance Criteria

- [x] (P0) `bootstrap.py` implemented with config file polling (5s default, configurable)
- [x] (P0) MCP server starts when `daemon.enabled` changes to `true`
- [x] (P0) MCP server stops when `daemon.enabled` changes to `false`
- [x] (P1) Crash detection and automatic restart of MCP server
- [x] (P1) Graceful shutdown handling (SIGTERM/SIGINT)
- [x] (P2) Health check interval configurable for MCP server monitoring

## Dependencies

- Story 1: Core Infrastructure (Management API + HTTP Client)

## Implementation Notes

**Key Files to Create**:
- `mcp_server/daemon/__init__.py`
- `mcp_server/daemon/bootstrap.py` - Main bootstrap service

**Design Principle**: Config-primary control. The bootstrap service is the only thing that starts/stops the MCP server. Users control state via `daemon.enabled` in config, not via CLI commands.

**Reference**: See `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` section "Bootstrap Service Implementation".

## Related Stories

- Depends on Story 1 (needs config schema)
- Story 3 depends on this (CLI needs running daemon)
- Story 4 depends on this (service installation wraps bootstrap)
