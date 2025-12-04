"""Tests for manual sync resilience integration (Story 13.3).

These tests verify that manual_sync.py integrates correctly with
the resilience layer from Story 19 (ResilientSessionIndexer).
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from enum import Enum

import pytest

from graphiti_core.session_tracking.session_manager import ActiveSession
from mcp_server.manual_sync import (
    index_session_sync,
    session_tracking_sync_history,
)


class MockDegradationLevel(int, Enum):
    """Mock enum matching DegradationLevel for testing."""

    FULL = 0
    PARTIAL = 1
    RAW_ONLY = 2


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager."""
    manager = Mock()
    manager.path_resolver = Mock()
    manager.path_resolver.list_all_projects.return_value = {}
    manager.path_resolver.get_project_hash.return_value = "test_hash"
    manager.path_resolver.get_sessions_dir.return_value = Path("/fake/sessions")

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
def mock_resilient_indexer():
    """Create a mock ResilientSessionIndexer."""
    indexer = AsyncMock()

    # Default behavior: successful full processing
    indexer.index_session = AsyncMock(
        return_value={
            "success": True,
            "degraded": False,
            "queued_for_retry": False,
            "error": None,
        }
    )
    indexer.get_degradation_level = Mock(return_value=MockDegradationLevel.FULL)

    return indexer


@pytest.fixture
def sample_session(tmp_path):
    """Create a sample session for testing."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_file = sessions_dir / "test_session.jsonl"
    session_file.write_text('[{"role": "user", "content": "test message"}]\n')

    return ActiveSession(
        session_id="test_session",
        file_path=session_file,
        project_hash="test_hash",
        offset=0,
        last_modified=0.0,
        last_activity=0.0,
        message_count=1,
    )


@pytest.fixture
def sample_sessions(tmp_path):
    """Create multiple sample sessions for testing."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    sessions = []
    for i in range(3):
        session_file = sessions_dir / f"session_{i}.jsonl"
        session_file.write_text('[{"role": "user", "content": "test message"}]\n')
        sessions.append(
            ActiveSession(
                session_id=f"session_{i}",
                file_path=session_file,
                project_hash="test_hash",
                offset=0,
                last_modified=float(i),
                last_activity=float(i),
                message_count=1,
            )
        )

    return sessions, sessions_dir


class TestIndexSessionSyncResilience:
    """Tests for index_session_sync resilience integration."""

    @pytest.mark.asyncio
    async def test_sync_uses_resilient_indexer_when_provided(
        self,
        mock_graphiti_client,
        mock_unified_config,
        mock_resilient_indexer,
        sample_session,
    ):
        """Test that resilient indexer is used when provided.

        AC1: Use resilient_indexer.py instead of direct SessionIndexer
        """
        with patch("mcp_server.manual_sync.JSONLParser") as mock_parser_class, patch(
            "mcp_server.manual_sync.SessionFilter"
        ) as mock_filter_class:
            # Configure parser mock
            mock_parser = mock_parser_class.return_value
            mock_parser.parse_file.return_value = (
                [Mock(role="user", content="test")],
                100,
            )

            # Configure filter mock
            mock_filter = mock_filter_class.return_value
            mock_filter.filter_conversation = AsyncMock(
                return_value=[Mock(role="user", content="test")]
            )

            # Call with resilient indexer
            result = await index_session_sync(
                session=sample_session,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                resilient_indexer=mock_resilient_indexer,
            )

            # Verify resilient indexer was called
            mock_resilient_indexer.index_session.assert_called_once()
            call_kwargs = mock_resilient_indexer.index_session.call_args[1]
            assert call_kwargs["session_id"] == "test_session"
            assert call_kwargs["group_id"] == "test_hash"

            # Verify result structure
            assert result["success"] is True
            assert result["degraded"] is False
            assert result["degradation_level"] == "full"

    @pytest.mark.asyncio
    async def test_sync_queues_failed_sessions(
        self,
        mock_graphiti_client,
        mock_unified_config,
        sample_session,
    ):
        """Test that failed sessions are queued for retry.

        AC2: Failed sessions are added to retry_queue
        """
        # Create mock with failed indexing (queued for retry)
        mock_indexer = AsyncMock()
        mock_indexer.index_session = AsyncMock(
            return_value={
                "success": False,
                "degraded": True,
                "queued_for_retry": True,  # Key: queued for retry
                "error": "LLM unavailable, queued for retry",
            }
        )
        mock_indexer.get_degradation_level = Mock(return_value=MockDegradationLevel.PARTIAL)

        with patch("mcp_server.manual_sync.JSONLParser") as mock_parser_class, patch(
            "mcp_server.manual_sync.SessionFilter"
        ) as mock_filter_class:
            mock_parser = mock_parser_class.return_value
            mock_parser.parse_file.return_value = ([Mock(role="user", content="test")], 100)
            mock_filter = mock_filter_class.return_value
            mock_filter.filter_conversation = AsyncMock(
                return_value=[Mock(role="user", content="test")]
            )

            result = await index_session_sync(
                session=sample_session,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                resilient_indexer=mock_indexer,
            )

            # Verify queued for retry is passed through
            assert result["success"] is False
            assert result["degraded"] is True
            assert result["queued_for_retry"] is True
            assert result["degradation_level"] == "partial"
            assert "queued for retry" in result["error"]

    @pytest.mark.asyncio
    async def test_sync_respects_circuit_breaker(
        self,
        mock_graphiti_client,
        mock_unified_config,
        sample_session,
    ):
        """Test that circuit breaker state is respected.

        AC3: Respect circuit breaker state (skip indexing if LLM unavailable)
        """
        # Create mock with circuit breaker open (LLM unavailable)
        mock_indexer = AsyncMock()
        mock_indexer.index_session = AsyncMock(
            return_value={
                "success": False,
                "degraded": True,
                "queued_for_retry": True,
                "error": "Circuit breaker open - LLM unavailable",
            }
        )
        mock_indexer.get_degradation_level = Mock(return_value=MockDegradationLevel.RAW_ONLY)

        with patch("mcp_server.manual_sync.JSONLParser") as mock_parser_class, patch(
            "mcp_server.manual_sync.SessionFilter"
        ) as mock_filter_class:
            mock_parser = mock_parser_class.return_value
            mock_parser.parse_file.return_value = ([Mock(role="user", content="test")], 100)
            mock_filter = mock_filter_class.return_value
            mock_filter.filter_conversation = AsyncMock(
                return_value=[Mock(role="user", content="test")]
            )

            result = await index_session_sync(
                session=sample_session,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                resilient_indexer=mock_indexer,
            )

            # Verify circuit breaker state is reflected
            assert result["degraded"] is True
            assert result["degradation_level"] == "raw_only"

    @pytest.mark.asyncio
    async def test_sync_returns_degradation_level(
        self,
        mock_graphiti_client,
        mock_unified_config,
        sample_session,
    ):
        """Test that degradation level is returned in response.

        AC4: Return degradation status in response (full/partial/raw_only)
        """
        # Test all three degradation levels
        for level in [
            MockDegradationLevel.FULL,
            MockDegradationLevel.PARTIAL,
            MockDegradationLevel.RAW_ONLY,
        ]:
            mock_indexer = AsyncMock()
            mock_indexer.index_session = AsyncMock(
                return_value={
                    "success": level == MockDegradationLevel.FULL,
                    "degraded": level != MockDegradationLevel.FULL,
                    "queued_for_retry": level != MockDegradationLevel.FULL,
                    "error": None if level == MockDegradationLevel.FULL else "degraded",
                }
            )
            mock_indexer.get_degradation_level = Mock(return_value=level)

            with patch("mcp_server.manual_sync.JSONLParser") as mock_parser_class, patch(
                "mcp_server.manual_sync.SessionFilter"
            ) as mock_filter_class:
                mock_parser = mock_parser_class.return_value
                mock_parser.parse_file.return_value = ([Mock(role="user", content="test")], 100)
                mock_filter = mock_filter_class.return_value
                mock_filter.filter_conversation = AsyncMock(
                    return_value=[Mock(role="user", content="test")]
                )

                result = await index_session_sync(
                    session=sample_session,
                    graphiti_client=mock_graphiti_client,
                    unified_config=mock_unified_config,
                    resilient_indexer=mock_indexer,
                )

                # Verify degradation level is in response
                expected_level = level.name.lower()
                assert result["degradation_level"] == expected_level

    @pytest.mark.asyncio
    async def test_sync_fallback_to_session_indexer(
        self,
        mock_graphiti_client,
        mock_unified_config,
        sample_session,
    ):
        """Test fallback to direct SessionIndexer when no resilient indexer.

        This ensures backward compatibility - when resilient_indexer is not
        provided, the function falls back to direct SessionIndexer usage.
        """
        with patch("mcp_server.manual_sync.JSONLParser") as mock_parser_class, patch(
            "mcp_server.manual_sync.SessionFilter"
        ) as mock_filter_class, patch(
            "mcp_server.manual_sync.SessionIndexer"
        ) as mock_indexer_class:
            # Configure mocks
            mock_parser = mock_parser_class.return_value
            mock_parser.parse_file.return_value = ([Mock(role="user", content="test")], 100)
            mock_filter = mock_filter_class.return_value
            mock_filter.filter_conversation = AsyncMock(
                return_value=[Mock(role="user", content="test")]
            )
            mock_indexer = mock_indexer_class.return_value
            mock_indexer.index_session = AsyncMock()

            # Call WITHOUT resilient indexer
            result = await index_session_sync(
                session=sample_session,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                resilient_indexer=None,  # No resilient indexer
            )

            # Verify SessionIndexer was used
            mock_indexer_class.assert_called_once_with(mock_graphiti_client)
            mock_indexer.index_session.assert_called_once()

            # Verify basic result structure
            assert result["success"] is True
            assert result["degradation_level"] == "full"


class TestSessionTrackingSyncHistoryResilience:
    """Tests for session_tracking_sync_history resilience integration."""

    @pytest.mark.asyncio
    async def test_sync_progress_callback_invoked(
        self,
        mock_session_manager,
        mock_graphiti_client,
        mock_unified_config,
        mock_resilient_indexer,
        sample_sessions,
    ):
        """Test that progress callback is invoked during sync.

        AC5: Add progress tracking (sessions processed / total)
        """
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        # Track progress callback invocations
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        with patch(
            "mcp_server.manual_sync.index_session_sync", new_callable=AsyncMock
        ) as mock_index:
            # Configure mock to return success
            mock_index.return_value = {
                "success": True,
                "degraded": False,
                "queued_for_retry": False,
                "degradation_level": "full",
                "error": None,
            }

            result_json = await session_tracking_sync_history(
                session_manager=mock_session_manager,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                project=None,
                days=7,
                max_sessions=100,
                dry_run=False,
                resilient_indexer=mock_resilient_indexer,
                progress_callback=progress_callback,
            )

            data = json.loads(result_json)
            assert data["status"] == "success"

            # Verify progress callback was invoked for each session
            assert len(progress_calls) == 3
            assert progress_calls[0] == (1, 3)  # 1 of 3
            assert progress_calls[1] == (2, 3)  # 2 of 3
            assert progress_calls[2] == (3, 3)  # 3 of 3

    @pytest.mark.asyncio
    async def test_sync_with_resilient_indexer_returns_degradation_in_response(
        self,
        mock_session_manager,
        mock_graphiti_client,
        mock_unified_config,
        mock_resilient_indexer,
        sample_sessions,
    ):
        """Test that sync response includes degradation information.

        AC4: Return degradation status in response
        """
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        # Configure mock to return partial degradation
        mock_resilient_indexer.get_degradation_level.return_value = MockDegradationLevel.PARTIAL

        with patch(
            "mcp_server.manual_sync.index_session_sync", new_callable=AsyncMock
        ) as mock_index:
            mock_index.return_value = {
                "success": True,
                "degraded": True,
                "queued_for_retry": False,
                "degradation_level": "partial",
                "error": None,
            }

            result_json = await session_tracking_sync_history(
                session_manager=mock_session_manager,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                project=None,
                days=7,
                max_sessions=100,
                dry_run=False,
                resilient_indexer=mock_resilient_indexer,
            )

            data = json.loads(result_json)
            assert data["status"] == "success"

            # Verify degradation info is in response
            assert "degradation_level" in data
            assert data["degradation_level"] == "partial"

    @pytest.mark.asyncio
    async def test_sync_counts_queued_for_retry_sessions(
        self,
        mock_session_manager,
        mock_graphiti_client,
        mock_unified_config,
        mock_resilient_indexer,
        sample_sessions,
    ):
        """Test that queued-for-retry count is included in response.

        AC2: Failed sessions are added to retry_queue
        """
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        call_count = 0

        async def mock_index_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First 2 sessions succeed, third is queued for retry
            if call_count == 3:
                return {
                    "success": False,
                    "degraded": True,
                    "queued_for_retry": True,
                    "degradation_level": "partial",
                    "error": "LLM unavailable",
                }
            return {
                "success": True,
                "degraded": False,
                "queued_for_retry": False,
                "degradation_level": "full",
                "error": None,
            }

        with patch(
            "mcp_server.manual_sync.index_session_sync", side_effect=mock_index_with_failures
        ):
            result_json = await session_tracking_sync_history(
                session_manager=mock_session_manager,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                project=None,
                days=7,
                max_sessions=100,
                dry_run=False,
                resilient_indexer=mock_resilient_indexer,
            )

            data = json.loads(result_json)
            assert data["status"] == "success"

            # Verify queued count is tracked
            assert "sessions_queued_for_retry" in data
            assert data["sessions_queued_for_retry"] == 1
            assert data["sessions_indexed"] == 2  # Only 2 succeeded

    @pytest.mark.asyncio
    async def test_sync_without_resilient_indexer_backward_compatible(
        self,
        mock_session_manager,
        mock_graphiti_client,
        mock_unified_config,
        sample_sessions,
    ):
        """Test sync works without resilient indexer (backward compatibility)."""
        sessions, sessions_dir = sample_sessions

        mock_session_manager.path_resolver.list_all_projects.return_value = {
            "test_hash": sessions_dir
        }

        with patch(
            "mcp_server.manual_sync.index_session_sync", new_callable=AsyncMock
        ) as mock_index:
            # Simulate old-style response (no resilience fields)
            mock_index.return_value = {
                "success": True,
                "degraded": False,
                "queued_for_retry": False,
                "degradation_level": "full",
                "error": None,
            }

            result_json = await session_tracking_sync_history(
                session_manager=mock_session_manager,
                graphiti_client=mock_graphiti_client,
                unified_config=mock_unified_config,
                project=None,
                days=7,
                max_sessions=100,
                dry_run=False,
                resilient_indexer=None,  # No resilient indexer
            )

            data = json.loads(result_json)
            assert data["status"] == "success"
            assert data["sessions_indexed"] == 3

            # Verify index_session_sync was called without resilient_indexer
            for call in mock_index.call_args_list:
                _, kwargs = call
                assert kwargs.get("resilient_indexer") is None
