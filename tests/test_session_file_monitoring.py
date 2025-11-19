"""Integration tests for session file monitoring."""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from graphiti_core.session_tracking import (
    ActiveSession,
    ClaudePathResolver,
    ConversationContext,
    SessionFileWatcher,
    SessionManager,
)


@pytest.fixture
def temp_claude_dir(tmp_path: Path) -> Path:
    """Create temporary Claude directory structure.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        Path to temporary .claude directory
    """
    claude_dir = tmp_path / ".claude"
    projects_dir = claude_dir / "projects"
    projects_dir.mkdir(parents=True)
    return claude_dir


@pytest.fixture
def mock_session_file(temp_claude_dir: Path) -> Path:
    """Create a mock session JSONL file.

    Args:
        temp_claude_dir: Temporary Claude directory

    Returns:
        Path to mock session file
    """
    # Create project hash directory
    project_hash = "abc123de"
    sessions_dir = temp_claude_dir / "projects" / project_hash / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create session file
    session_id = "test-session-001"
    session_file = sessions_dir / f"{session_id}.jsonl"

    # Write some initial messages in Claude Code JSONL format
    messages = [
        {
            "uuid": "msg-001",
            "sessionId": session_id,
            "timestamp": "2025-11-13T10:00:00Z",
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello, Claude!"
                    }
                ]
            }
        },
        {
            "uuid": "msg-002",
            "sessionId": session_id,
            "timestamp": "2025-11-13T10:00:01Z",
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello! How can I help you today?"
                    }
                ]
            }
        }
    ]

    with open(session_file, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return session_file


def test_session_file_watcher_detects_new_files(temp_claude_dir: Path):
    """Test that file watcher detects new session files."""
    created_files: List[Path] = []

    def on_created(file_path: Path):
        created_files.append(file_path)

    projects_dir = temp_claude_dir / "projects"
    watcher = SessionFileWatcher(
        watch_path=projects_dir,
        on_session_created=on_created
    )

    with watcher:
        # Give watcher time to start
        time.sleep(0.5)

        # Create a new session file
        project_hash = "test123"
        sessions_dir = projects_dir / project_hash / "sessions"
        sessions_dir.mkdir(parents=True)

        session_file = sessions_dir / "new-session.jsonl"
        session_file.write_text('{"uuid": "msg-001", "sessionId": "new-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "test"}]}}\n')

        # Give watcher time to detect
        time.sleep(1.0)

    # Verify file was detected (watchdog can fire multiple events, so check >= 1)
    assert len(created_files) >= 1
    assert all(f.name == "new-session.jsonl" for f in created_files)


def test_session_file_watcher_detects_modifications(mock_session_file: Path, temp_claude_dir: Path):
    """Test that file watcher detects session file modifications."""
    modified_files: List[Path] = []

    def on_modified(file_path: Path):
        modified_files.append(file_path)

    projects_dir = temp_claude_dir / "projects"
    watcher = SessionFileWatcher(
        watch_path=projects_dir,
        on_session_modified=on_modified
    )

    with watcher:
        # Give watcher time to start
        time.sleep(0.5)

        # Modify the session file
        with open(mock_session_file, "a") as f:
            f.write('{"uuid": "msg-003", "sessionId": "test-session-001", "timestamp": "2025-11-13T10:00:02Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "more content"}]}}\n')

        # Give watcher time to detect
        time.sleep(1.0)

    # Verify file modification was detected
    assert len(modified_files) >= 1
    assert mock_session_file in modified_files


def test_session_manager_tracks_new_sessions(temp_claude_dir: Path, mock_session_file: Path):
    """Test that session manager tracks new sessions."""
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=10
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify session was discovered
        assert session_manager.get_active_session_count() == 1
        assert session_manager.is_session_active("test-session-001")

    finally:
        session_manager.stop()


def test_session_manager_reads_new_messages(temp_claude_dir: Path, mock_session_file: Path):
    """Test that session manager reads new messages from session files."""
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=10
    )

    session_manager.start()

    try:
        # Give time for discovery and initial read
        time.sleep(0.5)

        # Get initial message count
        session = session_manager.active_sessions.get("test-session-001")
        assert session is not None
        initial_count = session.message_count

        # Add more messages
        with open(mock_session_file, "a") as f:
            f.write('{"uuid": "msg-003", "sessionId": "test-session-001", "timestamp": "2025-11-13T10:00:02Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "new message"}]}}\n')

        # Give time for file modification detection
        time.sleep(1.5)

        # Verify new messages were read
        assert session.message_count > initial_count

    finally:
        session_manager.stop()


def test_session_manager_detects_inactivity(temp_claude_dir: Path, mock_session_file: Path):
    """Test that session manager detects inactive sessions."""
    closed_sessions: List[str] = []

    def on_closed(session_id: str, file_path: Path, context: ConversationContext):
        closed_sessions.append(session_id)

    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=2,  # 2 seconds for testing
        on_session_closed=on_closed
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify session is active
        assert session_manager.is_session_active("test-session-001")

        # Wait for inactivity timeout
        time.sleep(3.0)

        # Check for inactive sessions
        session_manager.check_inactive_sessions()

        # Verify session was closed
        assert "test-session-001" in closed_sessions
        assert not session_manager.is_session_active("test-session-001")

    finally:
        session_manager.stop()


def test_session_manager_callback_on_close(temp_claude_dir: Path, mock_session_file: Path):
    """Test that session manager triggers callback when session closes."""
    closed_sessions = []

    def on_closed(session_id: str, file_path: Path, context: ConversationContext):
        closed_sessions.append({
            "session_id": session_id,
            "file_path": file_path,
            "message_count": len(context.messages),
            "token_count": context.total_tokens.total_tokens
        })

    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=2,
        on_session_closed=on_closed
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Wait for inactivity
        time.sleep(3.0)
        session_manager.check_inactive_sessions()

        # Verify callback was triggered
        assert len(closed_sessions) == 1
        assert closed_sessions[0]["session_id"] == "test-session-001"
        assert closed_sessions[0]["message_count"] >= 2

    finally:
        session_manager.stop()


def test_session_manager_handles_deleted_files(temp_claude_dir: Path, mock_session_file: Path):
    """Test that session manager handles deleted session files."""
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=10
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify session is active
        assert session_manager.is_session_active("test-session-001")

        # Delete the file
        mock_session_file.unlink()

        # Give time for deletion detection
        time.sleep(1.5)

        # Verify session was closed
        assert not session_manager.is_session_active("test-session-001")

    finally:
        session_manager.stop()


def test_session_manager_context_manager(temp_claude_dir: Path):
    """Test that session manager works as context manager."""
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)

    with SessionManager(path_resolver=path_resolver) as manager:
        # Verify manager started
        assert manager._is_running
        assert manager.watcher.is_running()

    # Verify manager stopped
    assert not manager._is_running
    assert not manager.watcher.is_running()


def test_multiple_concurrent_sessions(temp_claude_dir: Path):
    """Test handling multiple concurrent sessions."""
    projects_dir = temp_claude_dir / "projects"

    # Create multiple session files
    for i in range(3):
        project_hash = f"project{i}"
        sessions_dir = projects_dir / project_hash / "sessions"
        sessions_dir.mkdir(parents=True)

        session_file = sessions_dir / f"session-{i}.jsonl"
        session_file.write_text(f'{{"uuid": "msg-001", "sessionId": "session-{i}", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {{"role": "user", "content": [{{"type": "text", "text": "test"}}]}}}}\n')

    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(path_resolver=path_resolver)

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify all sessions were discovered
        assert session_manager.get_active_session_count() == 3

    finally:
        session_manager.stop()


def test_rolling_period_filter_recent_sessions(temp_claude_dir: Path):
    """Test that rolling period filter discovers only recent sessions."""
    projects_dir = temp_claude_dir / "projects"
    project_hash = "test-project"
    sessions_dir = projects_dir / project_hash / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create old session (10 days ago)
    old_session = sessions_dir / "old-session.jsonl"
    old_session.write_text('{"uuid": "msg-001", "sessionId": "old-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "old"}]}}\n')
    old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
    os.utime(old_session, (old_time, old_time))

    # Create recent session (3 days ago)
    recent_session = sessions_dir / "recent-session.jsonl"
    recent_session.write_text('{"uuid": "msg-001", "sessionId": "recent-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "recent"}]}}\n')
    recent_time = time.time() - (3 * 24 * 60 * 60)  # 3 days ago
    os.utime(recent_session, (recent_time, recent_time))

    # Create very recent session (1 hour ago)
    very_recent_session = sessions_dir / "very-recent-session.jsonl"
    very_recent_session.write_text('{"uuid": "msg-001", "sessionId": "very-recent-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "very recent"}]}}\n')
    very_recent_time = time.time() - (1 * 60 * 60)  # 1 hour ago
    os.utime(very_recent_session, (very_recent_time, very_recent_time))

    # Create session manager with 7-day rolling window
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=10,
        keep_length_days=7  # Only discover sessions modified in last 7 days
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify only recent sessions were discovered (2 out of 3)
        assert session_manager.get_active_session_count() == 2
        assert session_manager.is_session_active("recent-session")
        assert session_manager.is_session_active("very-recent-session")
        assert not session_manager.is_session_active("old-session")

    finally:
        session_manager.stop()


def test_rolling_period_filter_null_discovers_all(temp_claude_dir: Path):
    """Test that null keep_length_days discovers all sessions (no filter)."""
    projects_dir = temp_claude_dir / "projects"
    project_hash = "test-project"
    sessions_dir = projects_dir / project_hash / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create old session (30 days ago)
    old_session = sessions_dir / "old-session.jsonl"
    old_session.write_text('{"uuid": "msg-001", "sessionId": "old-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "old"}]}}\n')
    old_time = time.time() - (30 * 24 * 60 * 60)  # 30 days ago
    os.utime(old_session, (old_time, old_time))

    # Create recent session (1 day ago)
    recent_session = sessions_dir / "recent-session.jsonl"
    recent_session.write_text('{"uuid": "msg-001", "sessionId": "recent-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "recent"}]}}\n')
    recent_time = time.time() - (1 * 24 * 60 * 60)  # 1 day ago
    os.utime(recent_session, (recent_time, recent_time))

    # Create session manager with null keep_length_days (discover all)
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=10,
        keep_length_days=None  # Discover all sessions, no filter
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify both sessions were discovered (all sessions)
        assert session_manager.get_active_session_count() == 2
        assert session_manager.is_session_active("old-session")
        assert session_manager.is_session_active("recent-session")

    finally:
        session_manager.stop()


def test_rolling_period_filter_all_old_sessions(temp_claude_dir: Path):
    """Test rolling period filter when all sessions are older than window."""
    projects_dir = temp_claude_dir / "projects"
    project_hash = "test-project"
    sessions_dir = projects_dir / project_hash / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create multiple old sessions (all > 7 days)
    for i in range(3):
        old_session = sessions_dir / f"old-session-{i}.jsonl"
        old_session.write_text(f'{{"uuid": "msg-001", "sessionId": "old-session-{i}", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {{"role": "user", "content": [{{"type": "text", "text": "old"}}]}}}}\n')
        old_time = time.time() - ((10 + i) * 24 * 60 * 60)  # 10-12 days ago
        os.utime(old_session, (old_time, old_time))

    # Create session manager with 7-day window
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=10,
        keep_length_days=7
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify no sessions were discovered (all filtered out)
        assert session_manager.get_active_session_count() == 0

    finally:
        session_manager.stop()


def test_rolling_period_filter_edge_case_exact_cutoff(temp_claude_dir: Path):
    """Test rolling period filter with session exactly at cutoff time."""
    projects_dir = temp_claude_dir / "projects"
    project_hash = "test-project"
    sessions_dir = projects_dir / project_hash / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create session exactly 7 days ago (should be included, cutoff is <, not <=)
    cutoff_time = time.time() - (7 * 24 * 60 * 60)
    edge_session = sessions_dir / "edge-session.jsonl"
    edge_session.write_text('{"uuid": "msg-001", "sessionId": "edge-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "edge"}]}}\n')
    os.utime(edge_session, (cutoff_time + 1, cutoff_time + 1))  # 1 second after cutoff

    # Create session exactly 1 second before cutoff (should be filtered)
    old_edge_session = sessions_dir / "old-edge-session.jsonl"
    old_edge_session.write_text('{"uuid": "msg-001", "sessionId": "old-edge-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "old edge"}]}}\n')
    os.utime(old_edge_session, (cutoff_time - 1, cutoff_time - 1))  # 1 second before cutoff

    # Create session manager with 7-day window
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=10,
        keep_length_days=7
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify only edge_session was discovered (within window)
        assert session_manager.get_active_session_count() == 1
        assert session_manager.is_session_active("edge-session")
        assert not session_manager.is_session_active("old-edge-session")

    finally:
        session_manager.stop()


def test_rolling_period_filter_default_7_days(temp_claude_dir: Path):
    """Test that default keep_length_days is 7 days."""
    projects_dir = temp_claude_dir / "projects"
    project_hash = "test-project"
    sessions_dir = projects_dir / project_hash / "sessions"
    sessions_dir.mkdir(parents=True)

    # Create old session (10 days ago)
    old_session = sessions_dir / "old-session.jsonl"
    old_session.write_text('{"uuid": "msg-001", "sessionId": "old-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "old"}]}}\n')
    old_time = time.time() - (10 * 24 * 60 * 60)
    os.utime(old_session, (old_time, old_time))

    # Create recent session (3 days ago)
    recent_session = sessions_dir / "recent-session.jsonl"
    recent_session.write_text('{"uuid": "msg-001", "sessionId": "recent-session", "timestamp": "2025-11-13T10:00:00Z", "type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "recent"}]}}\n')
    recent_time = time.time() - (3 * 24 * 60 * 60)
    os.utime(recent_session, (recent_time, recent_time))

    # Create session manager without keep_length_days (should default to 7)
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(
        path_resolver=path_resolver,
        inactivity_timeout=10
        # keep_length_days not specified, should default to 7
    )

    session_manager.start()

    try:
        # Give time for discovery
        time.sleep(0.5)

        # Verify default filtering applied (only recent session discovered)
        assert session_manager.get_active_session_count() == 1
        assert session_manager.is_session_active("recent-session")
        assert not session_manager.is_session_active("old-session")

    finally:
        session_manager.stop()
