# Story 9: Critical Bug Fix - Periodic Checker Implementation

**Status**: unassigned
**Created**: 2025-11-18 23:01
**Priority**: CRITICAL
**Estimated Effort**: 4 hours
**Phase**: 1 (Week 1, Days 1-2)

## Description

**CRITICAL BUG**: The `check_interval` parameter exists in configuration but there is NO periodic scheduler calling `SessionManager.check_inactive_sessions()`. This means sessions NEVER close due to inactivity - they remain "active" indefinitely until the file is deleted or the MCP server shuts down.

**Evidence**:
- `SessionManager.check_inactive_sessions()` method exists (line 134-152 in session_manager.py)
- Method is NEVER called automatically - only manually in tests
- No `asyncio.create_task()` or periodic loop found in codebase

**Impact**:
- Sessions remain "active" indefinitely
- Users think sessions close after `inactivity_timeout` but they never do
- Memory leak potential (sessions accumulate in `active_sessions` dict)

## Acceptance Criteria

- [ ] Implement `check_inactive_sessions_periodically()` async function
- [ ] Add global `_inactivity_checker_task` variable to track task
- [ ] Update `initialize_session_tracking()` to start periodic checker task
- [ ] Update `shutdown_session_tracking()` to cancel task gracefully
- [ ] Test: Session closes after `inactivity_timeout` + check latency
- [ ] Test: Multiple sessions close independently
- [ ] Test: Task cancels cleanly on shutdown
- [ ] Test: No exceptions if session manager stops first

## Implementation Details

### Files to Modify

**`mcp_server/graphiti_mcp_server.py`**:

1. Add periodic checker function:
```python
async def check_inactive_sessions_periodically(
    session_manager: SessionManager,
    interval_seconds: int
):
    """Periodically check for inactive sessions and close them."""
    logger.info(f"Started periodic session inactivity checker (interval: {interval_seconds}s)")

    try:
        while True:
            await asyncio.sleep(interval_seconds)

            try:
                closed_count = session_manager.check_inactive_sessions()
                if closed_count > 0:
                    logger.info(f"Closed {closed_count} inactive sessions")
            except Exception as e:
                logger.error(f"Error checking inactive sessions: {e}", exc_info=True)

    except asyncio.CancelledError:
        logger.info("Session inactivity checker stopped")
        raise
```

2. Add global task handle:
```python
_inactivity_checker_task: Optional[asyncio.Task] = None
```

3. Update `initialize_session_tracking()`:
```python
async def initialize_session_tracking():
    global _session_manager, _inactivity_checker_task

    # ... existing code to create session_manager ...

    _session_manager = session_manager
    session_manager.start()

    # Start periodic checker (NEW)
    check_interval = unified_config.session_tracking.check_interval
    _inactivity_checker_task = asyncio.create_task(
        check_inactive_sessions_periodically(session_manager, check_interval)
    )
    logger.info(f"Session tracking initialized (check_interval: {check_interval}s)")
```

4. Update `shutdown_session_tracking()`:
```python
async def shutdown_session_tracking():
    global _session_manager, _inactivity_checker_task

    # Cancel checker task (NEW)
    if _inactivity_checker_task:
        _inactivity_checker_task.cancel()
        try:
            await _inactivity_checker_task
        except asyncio.CancelledError:
            pass

    # Stop session manager
    if _session_manager:
        _session_manager.stop()
```

### Testing Requirements

**Create**: `tests/session_tracking/test_periodic_checker.py`

Test cases:
1. **Task Lifecycle**:
   - Task starts when session tracking initialized
   - Task runs every `check_interval` seconds
   - Task cancels cleanly on shutdown

2. **Session Closure Timing**:
   - Session closes after `inactivity_timeout` + check latency
   - Multiple sessions close independently
   - Session doesn't close if file modified during timeout period
   - Closed session triggers callback

3. **Error Handling**:
   - No exceptions if session manager stops first
   - Exceptions in check don't crash task
   - Task continues after exception

## Dependencies

- None (critical bug fix, should be done first)

## Related Documents

- `.claude/handoff/session-tracking-complete-overhaul-2025-11-18.md` (Section: Critical Bug Discovery)
- `graphiti_core/session_tracking/session_manager.py` (existing code)
- `mcp_server/graphiti_mcp_server.py` (existing code)

## Cross-Cutting Requirements

See parent sprint `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`:
- Type hints: All async functions properly typed
- Error handling: Comprehensive logging for task lifecycle
- Testing: >80% coverage with lifecycle tests
- Performance: <5% overhead for periodic checks
