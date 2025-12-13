# Story 4: Clean Up MCP Server Session Initialization

**Status**: unassigned
**Created**: 2025-12-12 17:46

## Description

Remove session tracking initialization code in MCP server that uses deprecated time-based patterns. The server should no longer start background tasks for periodic session checking or file watching.

## Acceptance Criteria

- [ ] (P0) Remove `check_inactive_sessions_periodically` call from server startup
- [ ] (P0) Remove `check_interval` usage from session tracking initialization
- [ ] (P1) Simplify `initialize_session_tracking` function
- [ ] (P1) Remove related logging statements referencing deprecated params

## Dependencies

Stories 1-3

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Remove Deprecated Config Parameters
- Story 2: Remove Session Manager Time-Based Logic
- Story 3: Remove File Watcher Module
