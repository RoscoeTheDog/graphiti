# Story 12: Rolling Period Filter - Prevent Bulk Indexing

**Status**: unassigned
**Created**: 2025-11-18 23:01
**Priority**: HIGH
**Estimated Effort**: 4 hours
**Phase**: 4 (Week 2, Days 2-3)
**Depends on**: Story 10 (keep_length_days parameter)

## Description

Implement time-based filtering in session discovery to prevent bulk indexing of old sessions. When `keep_length_days` is set, only auto-discover sessions modified within the last N days. This prevents expensive bulk indexing on first run (e.g., 1000+ sessions costing $500+).

**Problem**:
- Current implementation discovers ALL sessions in watch directory
- If user has 100 projects with 1000+ sessions, auto-indexes everything
- Potential cost: $500+ without user consent
- No rolling window filter

**Solution**:
- Use `keep_length_days` to filter by modification time
- Default: 7 days (safe rolling window)
- null value: discover all (opt-in for historical sync)
- Log filtered session count for visibility

## Acceptance Criteria

- [ ] Update `_discover_existing_sessions()` method with time-based filtering
- [ ] Filter sessions by file modification time (`os.path.getmtime()`)
- [ ] Use `keep_length_days` from configuration
- [ ] null value discovers all sessions (backward compatible)
- [ ] Log filtered session count (e.g., "Filtered 847 sessions older than 7 days")
- [ ] Test: Sessions within window discovered
- [ ] Test: Sessions older than window filtered out
- [ ] Test: null value discovers all sessions
- [ ] Test: Filter works on first run with many old sessions

## Implementation Details

### Files to Modify

**`graphiti_core/session_tracking/session_manager.py`**:

Update `_discover_existing_sessions()` method:

```python
def _discover_existing_sessions(self) -> None:
    """Discover existing session files in watch directory with rolling period filter."""
    if not self.watch_path.exists():
        logger.warning(f"Watch directory does not exist: {self.watch_path}")
        return

    # Calculate cutoff time for rolling window
    cutoff_time: Optional[float] = None
    if self.keep_length_days is not None:
        cutoff_time = time.time() - (self.keep_length_days * 24 * 60 * 60)
        logger.info(
            f"Discovering sessions modified in last {self.keep_length_days} days "
            f"(cutoff: {datetime.fromtimestamp(cutoff_time)})"
        )
    else:
        logger.info("Discovering all sessions (no rolling window filter)")

    discovered_count = 0
    filtered_count = 0

    for session_file in self.watch_path.glob("session_*.jsonl"):
        # Check modification time
        if cutoff_time is not None:
            file_mtime = os.path.getmtime(session_file)
            if file_mtime < cutoff_time:
                filtered_count += 1
                continue  # Skip old sessions

        # Session is within window, discover it
        session_id = self._get_session_id_from_path(session_file)
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = SessionState(
                session_id=session_id,
                file_path=session_file,
                last_modified=datetime.now(),
                message_count=0,
            )
            discovered_count += 1

    # Log summary
    logger.info(
        f"Discovered {discovered_count} sessions "
        f"(filtered {filtered_count} old sessions)"
    )
```

Add `keep_length_days` to `__init__()`:

```python
def __init__(
    self,
    watch_path: Path,
    inactivity_timeout: int,
    keep_length_days: Optional[int] = 7,  # NEW parameter
    on_session_closed: Optional[Callable[[str, Path], None]] = None,
):
    self.watch_path = watch_path
    self.inactivity_timeout = inactivity_timeout
    self.keep_length_days = keep_length_days  # NEW field
    self.on_session_closed = on_session_closed
    # ... rest of __init__ ...
```

**`mcp_server/graphiti_mcp_server.py`**:

Update `initialize_session_tracking()` to pass `keep_length_days`:

```python
async def initialize_session_tracking():
    # ... existing code ...

    session_manager = SessionManager(
        watch_path=watch_path,
        inactivity_timeout=config.inactivity_timeout,
        keep_length_days=config.keep_length_days,  # NEW
        on_session_closed=on_session_closed_callback,
    )

    # ... rest of initialization ...
```

### Testing Requirements

**Update**: `tests/session_tracking/test_session_file_monitoring.py`

Add test cases:

1. **Rolling Window Filter**:
   - Create sessions with different modification times
   - Set `keep_length_days = 7`
   - Verify only recent sessions discovered
   - Verify old sessions filtered out

2. **Null Value Behavior**:
   - Set `keep_length_days = None`
   - Verify all sessions discovered
   - No filtering applied

3. **Logging**:
   - Verify filtered count logged
   - Verify cutoff timestamp logged

4. **Edge Cases**:
   - Empty watch directory
   - All sessions older than window
   - All sessions within window
   - Mixed old/new sessions

Example test:

```python
def test_rolling_period_filter():
    """Test that old sessions are filtered based on keep_length_days."""
    with tempfile.TemporaryDirectory() as tmpdir:
        watch_path = Path(tmpdir)

        # Create old session (10 days ago)
        old_session = watch_path / "session_old.jsonl"
        old_session.write_text('{"test": "old"}\n')
        old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
        os.utime(old_session, (old_time, old_time))

        # Create recent session (3 days ago)
        recent_session = watch_path / "session_recent.jsonl"
        recent_session.write_text('{"test": "recent"}\n')
        recent_time = time.time() - (3 * 24 * 60 * 60)  # 3 days ago
        os.utime(recent_session, (recent_time, recent_time))

        # Create session manager with 7-day window
        manager = SessionManager(
            watch_path=watch_path,
            inactivity_timeout=300,
            keep_length_days=7,
        )
        manager.start()

        # Verify only recent session discovered
        assert len(manager.active_sessions) == 1
        assert "recent" in manager.active_sessions

        manager.stop()
```

## Dependencies

- Story 10 (keep_length_days parameter added to config) - REQUIRED

## Related Documents

- `.claude/handoff/session-tracking-complete-overhaul-2025-11-18.md` (Section: Security & Privacy Concerns)
- `.claude/handoff/session-tracking-security-concerns-2025-11-18.md`

## Cross-Cutting Requirements

See parent sprint `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`:
- Platform-agnostic paths: Use pathlib.Path and os.path.getmtime()
- Error handling: Graceful handling of missing files, permission errors
- Type hints: Optional[int] for keep_length_days
- Testing: >80% coverage with time-based tests
- Performance: <5% overhead for filtering check
- Logging: Clear messages about filtered session count
