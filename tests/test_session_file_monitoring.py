"""Integration tests for session file monitoring."""

import json
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
