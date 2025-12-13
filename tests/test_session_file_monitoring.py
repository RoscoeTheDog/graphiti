"""Integration tests for session management.

Note: File watcher tests removed as part of Session Tracking Deprecation Cleanup v1.0.
Turn-based processing eliminates the need for filesystem monitoring.
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from graphiti_core.session_tracking import (
    ActiveSession,
    ClaudePathResolver,
    ConversationContext,
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


def test_session_manager_context_manager(temp_claude_dir: Path):
    """Test that session manager works as context manager."""
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)

    with SessionManager(path_resolver=path_resolver) as manager:
        # Verify manager started
        assert manager._is_running

    # Verify manager stopped
    assert not manager._is_running


def test_session_manager_basic_operations(temp_claude_dir: Path, mock_session_file: Path):
    """Test basic session manager operations without file watcher."""
    path_resolver = ClaudePathResolver(claude_dir=temp_claude_dir)
    session_manager = SessionManager(path_resolver=path_resolver)

    # Test start/stop
    session_manager.start()
    assert session_manager._is_running

    # Test manual session tracking
    project_hash = "abc123de"
    session_manager._start_tracking_session(mock_session_file, project_hash)

    assert session_manager.get_active_session_count() == 1
    assert session_manager.is_session_active("test-session-001")

    session_manager.stop()
    assert not session_manager._is_running
