# Story 16: Testing & Validation - Comprehensive Coverage

**Status**: unassigned
**Created**: 2025-11-18 23:01
**Priority**: CRITICAL
**Estimated Effort**: 16 hours
**Phase**: 8 (Week 3, Day 5 - Week 4, Days 1-2)
**Depends on**: Stories 9-15 (all implementation complete)

## Description

Comprehensive testing and validation of all session tracking overhaul features. This includes unit tests, integration tests, performance tests, and security tests to ensure >80% coverage and verify all requirements are met.

**Scope**:
- Unit tests for all new features
- Integration tests for full workflows
- Performance benchmarks
- Security validation
- Regression tests

## Acceptance Criteria

### Unit Tests
- [ ] Test periodic checker lifecycle (start, run, cancel)
- [ ] Test template resolution hierarchy (project > global > built-in > inline)
- [ ] Test filter value resolution (`bool | str` type system)
- [ ] Test `keep_length_days` filtering (time-based)
- [ ] Test config auto-generation (create, no overwrite)
- [ ] Test manual sync (discovery, filtering, cost estimation)
- [ ] All unit tests pass (>95% pass rate)
- [ ] Test coverage >80%

### Integration Tests
- [ ] Test full session lifecycle with periodic checker
- [ ] Test manual sync command (dry-run + actual)
- [ ] Test custom templates override defaults
- [ ] Test project templates override global
- [ ] Test MCP server startup with auto-generation
- [ ] All integration tests pass

### Performance Tests
- [ ] Benchmark periodic checker overhead (<5%)
- [ ] Test file watcher with 1000+ sessions (no degradation)
- [ ] Test template resolution caching (avoid re-reads)
- [ ] Test session discovery performance (large directories)
- [ ] All performance tests meet requirements

### Security Tests
- [ ] Verify tracking disabled by default
- [ ] Verify no auto-summarization by default
- [ ] Verify rolling window prevents bulk indexing
- [ ] Verify confirmation required for dangerous operations
- [ ] All security requirements met

### Regression Tests
- [ ] Verify existing features still work
- [ ] Verify backward compatibility (old configs load)
- [ ] Verify no breaking changes for existing users
- [ ] All regression tests pass

## Implementation Details

### Files to Create

**`tests/session_tracking/test_periodic_checker.py`**:

```python
"""Tests for periodic session inactivity checker."""

import asyncio
import pytest
from graphiti_core.session_tracking.session_manager import SessionManager


@pytest.mark.asyncio
async def test_periodic_checker_lifecycle():
    """Test that periodic checker starts, runs, and cancels correctly."""
    # Create session manager
    manager = SessionManager(watch_path=Path("/tmp"), inactivity_timeout=300)

    # Start periodic checker
    task = asyncio.create_task(
        check_inactive_sessions_periodically(manager, interval_seconds=1)
    )

    # Wait for at least one check
    await asyncio.sleep(1.5)

    # Cancel task
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_session_closes_after_timeout():
    """Test that session closes after inactivity_timeout + check latency."""
    with tempfile.TemporaryDirectory() as tmpdir:
        watch_path = Path(tmpdir)

        # Create session file
        session_file = watch_path / "session_test.jsonl"
        session_file.write_text('{"test": "data"}\n')

        # Track closed sessions
        closed_sessions = []

        def on_closed(session_id, file_path):
            closed_sessions.append(session_id)

        # Create manager with short timeout
        manager = SessionManager(
            watch_path=watch_path,
            inactivity_timeout=2,  # 2 seconds
            on_session_closed=on_closed,
        )
        manager.start()

        # Start periodic checker (1 second interval)
        task = asyncio.create_task(
            check_inactive_sessions_periodically(manager, interval_seconds=1)
        )

        # Wait for timeout + check latency
        await asyncio.sleep(3.5)

        # Verify session closed
        assert len(closed_sessions) == 1
        assert "test" in closed_sessions[0]

        # Cleanup
        task.cancel()
        manager.stop()
```

**`tests/session_tracking/test_template_system.py`**:

```python
"""Tests for pluggable template system."""

import pytest
from pathlib import Path
from graphiti_core.session_tracking.message_summarizer import resolve_template_path


def test_template_resolution_hierarchy(tmp_path):
    """Test that templates resolve in correct order: project > global > built-in > inline."""
    # Setup directories
    project_dir = tmp_path / "project"
    project_templates = project_dir / ".graphiti" / "auto-tracking" / "templates"
    project_templates.mkdir(parents=True)

    global_dir = Path.home() / ".graphiti" / "auto-tracking" / "templates"
    global_dir.mkdir(parents=True, exist_ok=True)

    # Create templates
    project_template = project_templates / "test.md"
    project_template.write_text("PROJECT TEMPLATE")

    global_template = global_dir / "test.md"
    global_template.write_text("GLOBAL TEMPLATE")

    # Test project override
    content, is_inline = resolve_template_path("test.md", project_root=project_dir)
    assert content == "PROJECT TEMPLATE"
    assert not is_inline

    # Test global fallback (no project)
    content, is_inline = resolve_template_path("test.md", project_root=None)
    assert content == "GLOBAL TEMPLATE"
    assert not is_inline

    # Test inline prompt
    content, is_inline = resolve_template_path("Summarize in 1 sentence", project_root=None)
    assert content == "Summarize in 1 sentence"
    assert is_inline
```

**`tests/session_tracking/test_rolling_filter.py`**:

```python
"""Tests for rolling period filter."""

import time
import os
from pathlib import Path
from graphiti_core.session_tracking.session_manager import SessionManager


def test_keep_length_days_filter():
    """Test that sessions older than keep_length_days are filtered."""
    with tempfile.TemporaryDirectory() as tmpdir:
        watch_path = Path(tmpdir)

        # Create old session (10 days ago)
        old_session = watch_path / "session_old.jsonl"
        old_session.write_text('{"test": "old"}\n')
        old_time = time.time() - (10 * 24 * 60 * 60)
        os.utime(old_session, (old_time, old_time))

        # Create recent session (3 days ago)
        recent_session = watch_path / "session_recent.jsonl"
        recent_session.write_text('{"test": "recent"}\n')
        recent_time = time.time() - (3 * 24 * 60 * 60)
        os.utime(recent_session, (recent_time, recent_time))

        # Create manager with 7-day window
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


def test_null_keep_length_days():
    """Test that null keep_length_days discovers all sessions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        watch_path = Path(tmpdir)

        # Create old session (100 days ago)
        old_session = watch_path / "session_old.jsonl"
        old_session.write_text('{"test": "old"}\n')
        old_time = time.time() - (100 * 24 * 60 * 60)
        os.utime(old_session, (old_time, old_time))

        # Create manager with null window (all sessions)
        manager = SessionManager(
            watch_path=watch_path,
            inactivity_timeout=300,
            keep_length_days=None,
        )
        manager.start()

        # Verify old session discovered
        assert len(manager.active_sessions) == 1

        manager.stop()
```

**`tests/session_tracking/test_manual_sync.py`**:

```python
"""Tests for manual sync command."""

import pytest
from mcp_server.graphiti_mcp_server import session_tracking_sync_history


@pytest.mark.asyncio
async def test_dry_run_mode():
    """Test that dry-run mode returns preview without indexing."""
    result = await session_tracking_sync_history(
        project=None,
        days=7,
        max_sessions=100,
        dry_run=True,
    )

    data = json.loads(result)

    # Verify dry-run response
    assert data["dry_run"] is True
    assert "sessions_found" in data
    assert "estimated_cost" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_cost_estimation():
    """Test that cost estimation is accurate."""
    # Create test sessions
    # ... setup code ...

    result = await session_tracking_sync_history(
        project=test_project,
        days=7,
        max_sessions=10,
        dry_run=True,
    )

    data = json.loads(result)

    # Verify cost calculation
    expected_cost = data["sessions_found"] * 0.17
    actual_cost = float(data["estimated_cost"].replace("$", ""))
    assert abs(expected_cost - actual_cost) < 0.01
```

**`tests/test_config_generation.py`**:

```python
"""Tests for configuration auto-generation."""

import json
from pathlib import Path
from mcp_server.graphiti_mcp_server import ensure_global_config_exists


def test_config_auto_generation(tmp_path, monkeypatch):
    """Test that config is auto-generated on first run."""
    # Override home directory
    monkeypatch.setenv("HOME", str(tmp_path))

    config_path = tmp_path / ".graphiti" / "graphiti.config.json"

    # Ensure config doesn't exist
    assert not config_path.exists()

    # Call generation
    result_path = ensure_global_config_exists()

    # Verify config created
    assert config_path.exists()
    assert result_path == config_path

    # Verify valid JSON
    with open(config_path) as f:
        config = json.load(f)

    # Verify structure
    assert "database" in config
    assert "llm" in config
    assert "session_tracking" in config

    # Verify defaults
    assert config["session_tracking"]["enabled"] is False
    assert config["session_tracking"]["auto_summarize"] is False
    assert config["session_tracking"]["keep_length_days"] == 7


def test_no_overwrite(tmp_path, monkeypatch):
    """Test that existing config is not overwritten."""
    monkeypatch.setenv("HOME", str(tmp_path))

    config_path = tmp_path / ".graphiti" / "graphiti.config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Create existing config
    original_content = '{"custom": "config"}'
    config_path.write_text(original_content)

    # Call generation
    ensure_global_config_exists()

    # Verify no overwrite
    assert config_path.read_text() == original_content
```

### Performance Benchmarks

**Create**: `tests/session_tracking/test_performance.py`

```python
"""Performance benchmarks for session tracking."""

import time
import pytest


def test_periodic_checker_overhead():
    """Verify periodic checker adds <5% overhead."""
    # Baseline: session manager without checker
    start = time.time()
    # ... run session manager for 60 seconds ...
    baseline_time = time.time() - start

    # With checker
    start = time.time()
    # ... run session manager + periodic checker for 60 seconds ...
    checker_time = time.time() - start

    # Calculate overhead
    overhead = (checker_time - baseline_time) / baseline_time
    assert overhead < 0.05  # <5%


def test_large_directory_performance():
    """Verify file watcher handles 1000+ sessions without degradation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        watch_path = Path(tmpdir)

        # Create 1000 sessions
        for i in range(1000):
            session = watch_path / f"session_{i}.jsonl"
            session.write_text('{"test": "data"}\n')

        # Measure discovery time
        start = time.time()
        manager = SessionManager(watch_path=watch_path, inactivity_timeout=300)
        manager.start()
        discovery_time = time.time() - start

        # Verify performance
        assert discovery_time < 5.0  # <5 seconds for 1000 sessions
        assert len(manager.active_sessions) <= 1000

        manager.stop()
```

### Security Tests

**Update**: `tests/session_tracking/test_security.py`

```python
"""Security validation tests."""

import pytest
from mcp_server.unified_config import SessionTrackingConfig


def test_disabled_by_default():
    """Verify session tracking is disabled by default."""
    config = SessionTrackingConfig()
    assert config.enabled is False


def test_no_llm_costs_by_default():
    """Verify auto_summarize is disabled by default."""
    config = SessionTrackingConfig()
    assert config.auto_summarize is False


def test_rolling_window_default():
    """Verify rolling window prevents bulk indexing by default."""
    config = SessionTrackingConfig()
    assert config.keep_length_days == 7


def test_confirmation_required_for_all_history():
    """Verify CLI requires confirmation for --days 0."""
    # Test CLI command
    result = subprocess.run(
        ["graphiti-mcp", "session-tracking", "sync", "--days", "0"],
        capture_output=True,
        text=True,
    )

    # Verify error
    assert result.returncode != 0
    assert "--confirm" in result.stdout
```

## Testing Requirements Summary

**Total Test Files**: 7 new + updates to existing
**Total Test Cases**: ~50 new tests
**Coverage Target**: >80% for all new code
**Performance Target**: <5% overhead
**Security Target**: 100% (all requirements met)

## Dependencies

- Stories 9-15 (all implementation complete) - REQUIRED

## Related Documents

- `.claude/handoff/session-tracking-complete-overhaul-2025-11-18.md` (Section: Testing Requirements)

## Cross-Cutting Requirements

See parent sprint `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`:
- Testing: >80% coverage (target: 90%+)
- Platform-specific tests: Windows + Unix
- Performance: <5% overhead verified
- Security: All requirements validated
