"""Tests for manual session sync functionality."""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from graphiti_core.session_tracking.session_manager import ActiveSession
from mcp_server.manual_sync import (
    discover_sessions_for_sync,
    index_session_sync,
    session_tracking_sync_history,
)


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager."""
    manager = Mock()
    manager.path_resolver = Mock()
    manager.path_resolver.list_all_projects.return_value = {}
    manager.path_resolver.get_project_hash.return_value = "test_hash"
    manager.path_resolver.get_sessions_dir.return_value = Path("/fake/sessions")

    # Make extract_session_id_from_path return the session ID from the filename
    def extract_session_id(path):
        return path.stem
    manager.path_resolver.extract_session_id_from_path.side_effect = extract_session_id

    return manager


@pytest.fixture
def mock_graphiti_client():
    """Create a mock Graphiti client."""
    return AsyncMock()


@pytest.fixture
def mock_unified_config():
    """Create a mock unified config."""
    config = Mock()
    config.session_tracking.filter = None
    return config


@pytest.fixture
def sample_sessions(tmp_path):
    """Create sample session files for testing."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    # Create 3 test session files with different modification times
    sessions = []
    for i in range(3):
        session_file = sessions_dir / f"session_{i}.jsonl"
        session_file.write_text('[{"role": "user", "content": "test"}]\n')

        # Set modification time (older to newer)
        # Add small offset to avoid boundary issues with time comparisons
        mtime = time.time() - ((3 - i) * 86400) + 3600  # 3, 2, 1 days ago + 1 hour
        os.utime(session_file, (mtime, mtime))

        sessions.append(ActiveSession(
            session_id=f"session_{i}",
            file_path=session_file,
            project_hash="test_hash",
            offset=0,
            last_modified=mtime,
            last_activity=mtime,
            message_count=0,
        ))

    return sessions, sessions_dir


class TestDiscoverSessionsForSync:
    """Tests for discover_sessions_for_sync function."""

    def test_discover_all_sessions_no_filter(self, mock_session_manager, sample_sessions):
        """Test discovering all sessions without time filter."""
        sessions, sessions_dir = sample_sessions

        # Configure mock to return test sessions
        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        # Discover with days=0 (no filter)
        result = discover_sessions_for_sync(
            session_manager=mock_session_manager,
            project=None,
            days=0,
            max_sessions=100,
        )

        assert len(result) == 3
        # Should be sorted by modification time (newest first)
        assert result[0].session_id == "session_2"
        assert result[1].session_id == "session_1"
        assert result[2].session_id == "session_0"

    def test_discover_sessions_with_days_filter(self, mock_session_manager, sample_sessions):
        """Test discovering sessions within last N days."""
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        # Discover only sessions from last 1.5 days
        # (session_2 is 1 day old, session_1 is 2 days old - use 1.5 to avoid boundary issues)
        result = discover_sessions_for_sync(
            session_manager=mock_session_manager,
            project=None,
            days=1,  # Last 1 day should only include session_2
            max_sessions=100,
        )

        # Should only get sessions from last 1 day (session_2 only)
        assert len(result) == 1
        assert result[0].session_id == "session_2"

    def test_discover_sessions_with_max_limit(self, mock_session_manager, sample_sessions):
        """Test max_sessions limit is enforced."""
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        # Limit to 2 sessions
        result = discover_sessions_for_sync(
            session_manager=mock_session_manager,
            project=None,
            days=0,
            max_sessions=2,
        )

        assert len(result) == 2
        # Should get the 2 newest sessions
        assert result[0].session_id == "session_2"
        assert result[1].session_id == "session_1"

    def test_discover_specific_project(self, mock_session_manager, sample_sessions):
        """Test discovering sessions for specific project."""
        sessions, sessions_dir = sample_sessions

        # Configure mocks
        mock_session_manager.path_resolver.get_project_hash.return_value = "specific_hash"
        mock_session_manager.path_resolver.get_sessions_dir.return_value = sessions_dir

        # Discover for specific project
        result = discover_sessions_for_sync(
            session_manager=mock_session_manager,
            project="/path/to/project",
            days=0,
            max_sessions=100,
        )

        assert len(result) == 3
        mock_session_manager.path_resolver.get_project_hash.assert_called_once()

    def test_discover_empty_directory(self, mock_session_manager, tmp_path):
        """Test discovering from empty directory returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": empty_dir
        }

        result = discover_sessions_for_sync(
            session_manager=mock_session_manager,
            project=None,
            days=0,
            max_sessions=100,
        )

        assert len(result) == 0


class TestIndexSessionSync:
    """Tests for index_session_sync function."""

    @pytest.mark.asyncio
    async def test_index_session_success(
        self,
        mock_graphiti_client,
        mock_unified_config,
        sample_sessions,
    ):
        """Test successful session indexing."""
        sessions, _ = sample_sessions
        session = sessions[0]

        with patch('mcp_server.manual_sync.JSONLParser') as mock_parser_class, \
             patch('mcp_server.manual_sync.SessionFilter') as mock_filter_class, \
             patch('mcp_server.manual_sync.SessionIndexer') as mock_indexer_class:

            # Configure mocks
            mock_parser = mock_parser_class.return_value
            mock_parser.parse_file.return_value = (
                [{"role": "user", "content": "test"}],
                100
            )

            mock_filter = mock_filter_class.return_value
            # Return Mock objects with .content attribute (not dicts)
            mock_msg = Mock()
            mock_msg.role = "user"
            mock_msg.content = "test"
            mock_filter.filter_conversation = AsyncMock(return_value=[mock_msg])

            mock_indexer = mock_indexer_class.return_value
            mock_indexer.index_session = AsyncMock()

            # Index session
            await index_session_sync(
                session=session,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
            )

            # Verify calls
            mock_parser.parse_file.assert_called_once()
            mock_filter.filter_conversation.assert_called_once()
            mock_indexer.index_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_session_empty_messages(
        self,
        mock_graphiti_client,
        mock_unified_config,
        sample_sessions,
    ):
        """Test indexing session with no messages."""
        sessions, _ = sample_sessions
        session = sessions[0]

        with patch('mcp_server.manual_sync.JSONLParser') as mock_parser_class:
            mock_parser = mock_parser_class.return_value
            mock_parser.parse_file.return_value = ([], 0)

            # Should return without indexing
            await index_session_sync(
                session=session,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
            )

            # Parser called but no further processing
            mock_parser.parse_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_session_no_client(self, sample_sessions, mock_unified_config):
        """Test indexing fails when neither Graphiti client nor resilient indexer is provided."""
        sessions, _ = sample_sessions
        session = sessions[0]

        # Updated error message after Story 13.3 resilience integration
        with pytest.raises(RuntimeError, match="Either graphiti_client or resilient_indexer must be provided"):
            await index_session_sync(
                session=session,
                graphiti_client=None,
                unified_config=mock_unified_config,
                resilient_indexer=None,  # Explicitly pass None for both
            )


class TestSessionTrackingSyncHistory:
    """Tests for session_tracking_sync_history function."""

    @pytest.mark.asyncio
    async def test_sync_history_dry_run(
        self,
        mock_session_manager,
        mock_graphiti_client,
        mock_unified_config,
        sample_sessions,
    ):
        """Test dry-run mode returns preview without indexing."""
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        result_json = await session_tracking_sync_history(
            session_manager=mock_session_manager,
            graphiti_client=mock_graphiti_client,
            unified_config=mock_unified_config,
            project=None,
            days=7,
            max_sessions=100,
            dry_run=True,
        )

        data = json.loads(result_json)
        assert data["status"] == "success"
        assert data["dry_run"] is True
        assert data["sessions_found"] == 3
        assert "$" in data["estimated_cost"]
        assert data["estimated_tokens"] > 0
        assert len(data["sessions"]) == 3  # All 3 in preview
        assert "message" in data

    @pytest.mark.asyncio
    async def test_sync_history_actual_sync(
        self,
        mock_session_manager,
        mock_graphiti_client,
        mock_unified_config,
        sample_sessions,
    ):
        """Test actual sync mode indexes sessions."""
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        with patch('mcp_server.manual_sync.index_session_sync', new_callable=AsyncMock) as mock_index:
            result_json = await session_tracking_sync_history(
                session_manager=mock_session_manager,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                project=None,
                days=7,
                max_sessions=100,
                dry_run=False,
            )

            data = json.loads(result_json)
            assert data["status"] == "success"
            assert data["dry_run"] is False
            assert data["sessions_found"] == 3
            assert data["sessions_indexed"] == 3
            assert "$" in data["actual_cost"]

            # Verify indexing was called for each session
            assert mock_index.call_count == 3

    @pytest.mark.asyncio
    async def test_sync_history_partial_failure(
        self,
        mock_session_manager,
        mock_graphiti_client,
        mock_unified_config,
        sample_sessions,
    ):
        """Test sync continues even if some sessions fail."""
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        # Make second session fail by returning error result (not raising exception)
        # The resilience integration means index_session_sync returns a dict with success=False
        call_count = 0

        async def mock_index_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # Return failure result (simulating what happens with resilience)
                return {
                    "success": False,
                    "degraded": False,
                    "queued_for_retry": False,
                    "degradation_level": "full",
                    "error": "Test failure",
                }
            # Return success for other calls
            return {
                "success": True,
                "degraded": False,
                "queued_for_retry": False,
                "degradation_level": "full",
                "error": None,
            }

        with patch('mcp_server.manual_sync.index_session_sync', side_effect=mock_index_with_failure):
            result_json = await session_tracking_sync_history(
                session_manager=mock_session_manager,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                project=None,
                days=7,
                max_sessions=100,
                dry_run=False,
            )

            data = json.loads(result_json)
            assert data["status"] == "success"
            assert data["sessions_found"] == 3
            assert data["sessions_indexed"] == 2  # Only 2 succeeded

    @pytest.mark.asyncio
    async def test_sync_history_no_session_manager(
        self,
        mock_graphiti_client,
        mock_unified_config,
    ):
        """Test sync fails gracefully when session manager not initialized."""
        result_json = await session_tracking_sync_history(
            session_manager=None,
            graphiti_client=mock_graphiti_client,
            unified_config=mock_unified_config,
            project=None,
            days=7,
            max_sessions=100,
            dry_run=True,
        )

        data = json.loads(result_json)
        assert data["status"] == "error"
        assert "not initialized" in data["error"]

    @pytest.mark.asyncio
    async def test_sync_history_cost_calculation(
        self,
        mock_session_manager,
        mock_graphiti_client,
        mock_unified_config,
        sample_sessions,
    ):
        """Test cost estimation is accurate."""
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        # Dry-run to check estimates
        result_json = await session_tracking_sync_history(
            session_manager=mock_session_manager,
            graphiti_client=mock_graphiti_client,
            unified_config=mock_unified_config,
            project=None,
            days=7,
            max_sessions=100,
            dry_run=True,
        )

        data = json.loads(result_json)

        # Verify cost calculation (3 sessions * $0.17)
        expected_cost = 3 * 0.17
        assert data["estimated_cost"] == f"${expected_cost:.2f}"

        # Verify token estimation (3 sessions * 3500 tokens)
        expected_tokens = 3 * 3500
        assert data["estimated_tokens"] == expected_tokens
