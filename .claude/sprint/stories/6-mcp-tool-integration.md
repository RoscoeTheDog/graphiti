# Story 6: MCP Tool Integration
**Status**: unassigned
**Created**: 2025-11-17 00:05

**Description**: Add runtime toggle via MCP tool calls for per-session control
**Acceptance Criteria**:
- [ ] `session_tracking_start()` MCP tool implemented (renamed from track_session)
- [ ] `session_tracking_stop()` MCP tool implemented (renamed from stop_tracking_session)
- [ ] `session_tracking_status()` MCP tool implemented (renamed from get_session_tracking_status)
- [ ] Session registry tracks per-session state
- [ ] Override global config with force parameter works
- [ ] Integration with session_manager.py complete
- [ ] Agent-friendly tool descriptions written
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Type hints and comprehensive docstrings
  - [ ] Error handling with logging (MCP tool errors)
  - [ ] >80% test coverage
  - [ ] Documentation: MCP_TOOLS.md updated
  - [ ] Security: No sensitive data exposed in tool responses

