# Story 3: CLI Refactoring (HTTP Client + Error Messages)

**Status**: unassigned
**Created**: 2025-12-13 23:51

## Description

Refactor CLI to use HTTP client instead of module imports, with actionable error messages when daemon is disabled/unreachable. This fixes the current issue where CLI commands fail with "Session tracking not initialized" because they try to import in-process globals.

## Acceptance Criteria

- [ ] (P0) `session_tracking_cli.py` refactored to use `GraphitiClient` HTTP client
- [ ] (P0) Actionable error message when daemon is disabled: shows config path and how to enable
- [ ] (P0) Actionable error message when daemon unreachable: shows troubleshooting steps
- [ ] (P1) `graphiti-mcp daemon status` command shows installed/enabled/running state
- [ ] (P1) `graphiti-mcp daemon logs` command tails daemon log file
- [ ] (P2) All existing CLI commands work through HTTP API

## Dependencies

- Story 1: Core Infrastructure (Management API + HTTP Client)
- Story 2: Bootstrap Service (Config Watcher + MCP Lifecycle)

## Implementation Notes

**Key Files to Modify**:
- `mcp_server/session_tracking_cli.py` - Refactor to use HTTP client

**Error Message Examples**:
```
❌ Error: Graphiti daemon is disabled.

   To enable, edit: C:\Users\Admin\.graphiti\graphiti.config.json
   Set: "daemon": { "enabled": true }

   The daemon will start automatically within 5 seconds.
```

**Design Principle**: NO start/stop CLI commands. Runtime control is config-only.

**Reference**: See `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` section "CLI Error Handling".

## Related Stories

- Depends on Story 1 (uses GraphitiClient)
- Depends on Story 2 (needs running daemon to connect to)
