"""Tests for session tracking health MCP tools (Story 19).

This module tests the session tracking resilience MCP tools:
- session_tracking_health()
- get_failed_episodes()
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the MCP server module
import mcp_server.graphiti_mcp_server as mcp_server
from graphiti_core.session_tracking.status import (
    DegradationLevel,
    LLMStatus,
    QueueStatus,
    RetryQueueStatus,
    ServiceStatus,
    SessionTrackingHealth,
    SessionTrackingStatusAggregator,
)
from graphiti_core.session_tracking.retry_queue import FailedEpisode, RetryQueue


class TestSessionTrackingHealth:
    """Tests for session_tracking_health() MCP tool."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Save and restore global state."""
        original_session_manager = mcp_server.session_manager
        original_resilient_indexer = mcp_server.resilient_indexer
        original_status_aggregator = mcp_server.status_aggregator

        yield

        mcp_server.session_manager = original_session_manager
        mcp_server.resilient_indexer = original_resilient_indexer
        mcp_server.status_aggregator = original_status_aggregator

    @pytest.mark.asyncio
    async def test_health_without_resilient_indexer(self):
        """Test health check when resilient indexer is not initialized."""
        mcp_server.session_manager = None
        mcp_server.resilient_indexer = None
        mcp_server.status_aggregator = None

        result = await mcp_server.session_tracking_health()
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        assert "health" in result_dict
        health = result_dict["health"]
        assert health["service_status"] == "stopped"

    @pytest.mark.asyncio
    async def test_health_with_running_service(self):
        """Test health check with running session manager."""
        # Mock session manager
        mock_manager = Mock()
        mock_manager._is_running = True
        mock_manager.get_active_session_count.return_value = 2
        mcp_server.session_manager = mock_manager

        # Mock resilient indexer
        mock_indexer = Mock()
        mock_indexer.get_degradation_level.return_value = DegradationLevel.FULL

        mock_queue = Mock()
        mock_queue.get_stats.return_value = {
            "queue_size": 5,
            "pending_retries": 3,
            "permanent_failures": 2,
        }
        mock_indexer.retry_queue = mock_queue
        mcp_server.resilient_indexer = mock_indexer

        # Create status aggregator
        aggregator = SessionTrackingStatusAggregator()
        aggregator.set_session_manager(mock_manager)
        aggregator.set_retry_queue(mock_queue)
        aggregator.mark_started()
        mcp_server.status_aggregator = aggregator

        result = await mcp_server.session_tracking_health()
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        health = result_dict["health"]
        assert health["degradation_level"]["level"] == 0
        assert health["degradation_level"]["name"] == "FULL"
        assert health["active_sessions"] == 2

    @pytest.mark.asyncio
    async def test_health_with_degraded_service(self):
        """Test health check when service is degraded."""
        # Mock session manager
        mock_manager = Mock()
        mock_manager._is_running = True
        mock_manager.get_active_session_count.return_value = 1
        mcp_server.session_manager = mock_manager

        # Mock resilient indexer with PARTIAL degradation
        mock_indexer = Mock()
        mock_indexer.get_degradation_level.return_value = DegradationLevel.PARTIAL

        mock_queue = Mock()
        mock_queue.get_stats.return_value = {
            "queue_size": 10,
            "pending_retries": 8,
            "permanent_failures": 2,
        }
        mock_queue.get_all = AsyncMock(return_value=[])
        mock_indexer.retry_queue = mock_queue
        mcp_server.resilient_indexer = mock_indexer

        # Create status aggregator
        aggregator = SessionTrackingStatusAggregator()
        aggregator.set_session_manager(mock_manager)
        aggregator.set_retry_queue(mock_queue)
        aggregator.mark_started()
        mcp_server.status_aggregator = aggregator

        result = await mcp_server.session_tracking_health()
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        health = result_dict["health"]
        assert health["degradation_level"]["level"] == 1
        assert health["degradation_level"]["name"] == "PARTIAL"

    @pytest.mark.asyncio
    async def test_health_error_handling(self):
        """Test health check error handling."""
        # Force an error by setting invalid status aggregator
        mcp_server.status_aggregator = Mock()
        mcp_server.status_aggregator.get_health = AsyncMock(
            side_effect=Exception("Test error")
        )
        mcp_server.resilient_indexer = None

        result = await mcp_server.session_tracking_health()
        result_dict = json.loads(result)

        assert result_dict["status"] == "error"
        assert "Test error" in result_dict["message"]


class TestGetFailedEpisodes:
    """Tests for get_failed_episodes() MCP tool."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Save and restore global state."""
        original_resilient_indexer = mcp_server.resilient_indexer

        yield

        mcp_server.resilient_indexer = original_resilient_indexer

    @pytest.mark.asyncio
    async def test_get_failed_episodes_without_indexer(self):
        """Test getting failed episodes when resilient indexer not initialized."""
        mcp_server.resilient_indexer = None

        result = await mcp_server.get_failed_episodes()
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        assert result_dict["total_count"] == 0
        assert result_dict["episodes"] == []
        assert "Resilient indexer not initialized" in result_dict.get("message", "")

    @pytest.mark.asyncio
    async def test_get_failed_episodes_with_episodes(self):
        """Test getting failed episodes when episodes exist."""
        now = datetime.utcnow()

        # Create mock failed episodes
        mock_episodes = [
            FailedEpisode(
                episode_id="ep-1",
                session_id="session-1",
                session_file="/path/1.jsonl",
                raw_content="content 1",
                group_id="project",
                error_type="LLMUnavailableError",
                error_message="LLM unavailable",
                failed_at=now,
                retry_count=1,
                next_retry_at=now + timedelta(minutes=5),
            ),
            FailedEpisode(
                episode_id="ep-2",
                session_id="session-2",
                session_file="/path/2.jsonl",
                raw_content="content 2",
                group_id="project",
                error_type="RateLimitError",
                error_message="Rate limit exceeded",
                failed_at=now - timedelta(hours=1),
                retry_count=3,
                permanent_failure=True,
            ),
        ]

        # Mock resilient indexer
        mock_indexer = Mock()
        mock_indexer.get_failed_episodes = AsyncMock(return_value=mock_episodes)

        mock_queue = Mock()
        mock_queue.get_stats.return_value = {
            "queue_size": 2,
            "pending_retries": 1,
            "permanent_failures": 1,
            "total_added": 5,
            "total_retried": 3,
            "total_succeeded": 2,
            "total_failed_permanently": 1,
        }
        mock_queue.get_all = AsyncMock(return_value=mock_episodes)
        mock_indexer.retry_queue = mock_queue
        mcp_server.resilient_indexer = mock_indexer

        result = await mcp_server.get_failed_episodes()
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        assert result_dict["total_count"] == 2
        assert result_dict["returned_count"] == 2
        assert len(result_dict["episodes"]) == 2

        # Check first episode
        ep1 = result_dict["episodes"][0]
        assert ep1["episode_id"] == "ep-1"
        assert ep1["error_type"] == "LLMUnavailableError"
        assert ep1["retry_count"] == 1
        assert ep1["permanent_failure"] is False

        # Check stats
        stats = result_dict["stats"]
        assert stats["queue_size"] == 2
        assert stats["pending_retries"] == 1
        assert stats["permanent_failures"] == 1

    @pytest.mark.asyncio
    async def test_get_failed_episodes_exclude_permanent(self):
        """Test excluding permanent failures from results."""
        now = datetime.utcnow()

        # Create mock episodes - mix of pending and permanent
        all_episodes = [
            FailedEpisode(
                episode_id="ep-1",
                session_id="session-1",
                session_file="/path/1.jsonl",
                raw_content="content 1",
                group_id="project",
                error_type="Error",
                error_message="Error",
                failed_at=now,
                permanent_failure=False,
            ),
            FailedEpisode(
                episode_id="ep-2",
                session_id="session-2",
                session_file="/path/2.jsonl",
                raw_content="content 2",
                group_id="project",
                error_type="Error",
                error_message="Error",
                failed_at=now,
                permanent_failure=True,
            ),
        ]

        # When excluding permanent, only return non-permanent
        pending_only = [ep for ep in all_episodes if not ep.permanent_failure]

        mock_indexer = Mock()
        mock_indexer.get_failed_episodes = AsyncMock(return_value=pending_only)

        mock_queue = Mock()
        mock_queue.get_stats.return_value = {
            "queue_size": 2,
            "pending_retries": 1,
            "permanent_failures": 1,
            "total_added": 2,
            "total_retried": 0,
            "total_succeeded": 0,
            "total_failed_permanently": 1,
        }
        mock_queue.get_all = AsyncMock(return_value=pending_only)
        mock_indexer.retry_queue = mock_queue
        mcp_server.resilient_indexer = mock_indexer

        result = await mcp_server.get_failed_episodes(include_permanent=False)
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        assert result_dict["total_count"] == 1
        assert len(result_dict["episodes"]) == 1
        assert result_dict["episodes"][0]["permanent_failure"] is False

    @pytest.mark.asyncio
    async def test_get_failed_episodes_with_limit(self):
        """Test limiting number of returned episodes."""
        now = datetime.utcnow()

        # Create mock episodes
        mock_episodes = [
            FailedEpisode(
                episode_id=f"ep-{i}",
                session_id=f"session-{i}",
                session_file=f"/path/{i}.jsonl",
                raw_content=f"content {i}",
                group_id="project",
                error_type="Error",
                error_message="Error",
                failed_at=now - timedelta(hours=i),
            )
            for i in range(10)
        ]

        mock_indexer = Mock()
        # Limit should be applied - return only first 5
        mock_indexer.get_failed_episodes = AsyncMock(return_value=mock_episodes[:5])

        mock_queue = Mock()
        mock_queue.get_stats.return_value = {
            "queue_size": 10,
            "pending_retries": 10,
            "permanent_failures": 0,
            "total_added": 10,
            "total_retried": 0,
            "total_succeeded": 0,
            "total_failed_permanently": 0,
        }
        mock_queue.get_all = AsyncMock(return_value=mock_episodes)
        mock_indexer.retry_queue = mock_queue
        mcp_server.resilient_indexer = mock_indexer

        result = await mcp_server.get_failed_episodes(limit=5)
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        assert result_dict["total_count"] == 10
        assert result_dict["returned_count"] == 5
        assert len(result_dict["episodes"]) == 5

    @pytest.mark.asyncio
    async def test_get_failed_episodes_limit_clamping(self):
        """Test that limit is clamped to valid range."""
        mock_indexer = Mock()
        mock_indexer.get_failed_episodes = AsyncMock(return_value=[])

        mock_queue = Mock()
        mock_queue.get_stats.return_value = {
            "queue_size": 0,
            "pending_retries": 0,
            "permanent_failures": 0,
            "total_added": 0,
            "total_retried": 0,
            "total_succeeded": 0,
            "total_failed_permanently": 0,
        }
        mock_queue.get_all = AsyncMock(return_value=[])
        mock_indexer.retry_queue = mock_queue
        mcp_server.resilient_indexer = mock_indexer

        # Test with limit > 100 (should be clamped to 100)
        await mcp_server.get_failed_episodes(limit=200)
        mock_indexer.get_failed_episodes.assert_called_with(
            include_permanent=True,
            limit=100
        )

        # Test with limit < 1 (should be clamped to 1)
        await mcp_server.get_failed_episodes(limit=0)
        mock_indexer.get_failed_episodes.assert_called_with(
            include_permanent=True,
            limit=1
        )

    @pytest.mark.asyncio
    async def test_get_failed_episodes_error_handling(self):
        """Test error handling in get_failed_episodes."""
        mock_indexer = Mock()
        mock_indexer.get_failed_episodes = AsyncMock(
            side_effect=Exception("Database error")
        )
        mcp_server.resilient_indexer = mock_indexer

        result = await mcp_server.get_failed_episodes()
        result_dict = json.loads(result)

        assert result_dict["status"] == "error"
        assert "Database error" in result_dict["message"]
