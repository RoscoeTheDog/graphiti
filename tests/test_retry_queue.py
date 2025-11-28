"""Tests for the retry queue module (Story 19).

This module tests the retry queue functionality for failed session tracking episodes:
- FailedEpisode dataclass
- RetryQueue persistence and operations
- RetryQueueProcessor processing logic
"""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from graphiti_core.session_tracking.retry_queue import (
    FailedEpisode,
    RetryQueue,
    RetryQueueProcessor,
)


class TestFailedEpisode:
    """Tests for FailedEpisode dataclass."""

    def test_create_failed_episode(self):
        """Test creating a FailedEpisode with required fields."""
        episode = FailedEpisode(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            group_id="project-abc",
            error_type="LLMUnavailableError",
            error_message="LLM service unavailable",
            failed_at=datetime.utcnow(),
        )

        assert episode.episode_id == "ep-123"
        assert episode.session_id == "session-456"
        assert episode.retry_count == 0
        assert episode.permanent_failure is False
        assert episode.next_retry_at is None

    def test_to_dict_serialization(self):
        """Test converting FailedEpisode to dict with datetime serialization."""
        now = datetime.utcnow()
        episode = FailedEpisode(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            group_id="project-abc",
            error_type="LLMUnavailableError",
            error_message="LLM service unavailable",
            failed_at=now,
            next_retry_at=now + timedelta(minutes=5),
        )

        data = episode.to_dict()

        assert data["episode_id"] == "ep-123"
        assert isinstance(data["failed_at"], str)
        assert isinstance(data["next_retry_at"], str)
        # Verify ISO format
        assert "T" in data["failed_at"]

    def test_from_dict_deserialization(self):
        """Test creating FailedEpisode from dict with datetime parsing."""
        now = datetime.utcnow()
        data = {
            "episode_id": "ep-123",
            "session_id": "session-456",
            "session_file": "/path/to/session.jsonl",
            "raw_content": "test content",
            "group_id": "project-abc",
            "error_type": "LLMUnavailableError",
            "error_message": "LLM service unavailable",
            "failed_at": now.isoformat(),
            "retry_count": 2,
            "next_retry_at": (now + timedelta(minutes=5)).isoformat(),
            "permanent_failure": False,
            "last_retry_at": None,
            "created_at": now.isoformat(),
            "metadata": {"key": "value"},
        }

        episode = FailedEpisode.from_dict(data)

        assert episode.episode_id == "ep-123"
        assert isinstance(episode.failed_at, datetime)
        assert isinstance(episode.next_retry_at, datetime)
        assert episode.retry_count == 2
        assert episode.metadata == {"key": "value"}


class TestRetryQueue:
    """Tests for RetryQueue class."""

    @pytest.fixture
    def temp_persist_path(self):
        """Create a temporary file for queue persistence."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        yield path
        # Cleanup
        if path.exists():
            path.unlink()

    @pytest.fixture
    def queue(self):
        """Create a RetryQueue instance (in-memory)."""
        return RetryQueue(
            persist_path=None,
            max_retries=3,
            retry_delays=[60, 120, 300],
            max_queue_size=100,
        )

    @pytest.mark.asyncio
    async def test_add_episode(self, queue):
        """Test adding an episode to the queue."""
        await queue.start()

        episode = await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="LLMUnavailableError",
            error_message="LLM service unavailable",
            group_id="project-abc",
        )

        assert episode is not None
        assert episode.episode_id == "ep-123"
        assert episode.next_retry_at is not None
        assert episode.retry_count == 0

    @pytest.mark.asyncio
    async def test_queue_size_limit(self, queue):
        """Test that queue respects max_queue_size limit."""
        queue.max_queue_size = 2
        await queue.start()

        # Add two episodes
        ep1 = await queue.add(
            episode_id="ep-1",
            session_id="session-1",
            session_file="/path/1.jsonl",
            raw_content="content 1",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )
        ep2 = await queue.add(
            episode_id="ep-2",
            session_id="session-2",
            session_file="/path/2.jsonl",
            raw_content="content 2",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        # Third should be rejected
        ep3 = await queue.add(
            episode_id="ep-3",
            session_id="session-3",
            session_file="/path/3.jsonl",
            raw_content="content 3",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        assert ep1 is not None
        assert ep2 is not None
        assert ep3 is None  # Rejected due to size limit

    @pytest.mark.asyncio
    async def test_duplicate_episode(self, queue):
        """Test that duplicate episodes are not added."""
        await queue.start()

        ep1 = await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )
        ep2 = await queue.add(
            episode_id="ep-123",  # Same ID
            session_id="session-789",
            session_file="/path/to/other.jsonl",
            raw_content="other content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        # Should return the existing episode
        assert ep1 is not None
        assert ep2 is not None
        assert ep1.episode_id == ep2.episode_id

        # Queue should only have one episode
        all_eps = await queue.get_all()
        assert len(all_eps) == 1

    @pytest.mark.asyncio
    async def test_mark_success(self, queue):
        """Test marking an episode as successfully processed."""
        await queue.start()

        await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        assert len(await queue.get_all()) == 1

        await queue.mark_success("ep-123")

        assert len(await queue.get_all()) == 0

    @pytest.mark.asyncio
    async def test_mark_retry_failed_with_retries_remaining(self, queue):
        """Test marking retry failed when retries remain."""
        await queue.start()

        await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        has_more = await queue.mark_retry_failed("ep-123", "Retry failed")

        assert has_more is True

        episode = await queue.get("ep-123")
        assert episode.retry_count == 1
        assert episode.permanent_failure is False
        assert episode.next_retry_at is not None

    @pytest.mark.asyncio
    async def test_mark_retry_failed_exhausted(self, queue):
        """Test marking retry failed when all retries exhausted."""
        queue.max_retries = 2
        await queue.start()

        await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        # First retry
        await queue.mark_retry_failed("ep-123", "Failed 1")
        # Second retry - should exhaust
        has_more = await queue.mark_retry_failed("ep-123", "Failed 2")

        assert has_more is False

        episode = await queue.get("ep-123")
        assert episode.permanent_failure is True
        assert episode.next_retry_at is None

    @pytest.mark.asyncio
    async def test_get_pending(self, queue):
        """Test getting pending episodes ready for retry."""
        await queue.start()

        # Add an episode
        await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        # Initially should not be pending (retry_at in future)
        pending = await queue.get_pending()
        assert len(pending) == 0

        # Manually set next_retry_at to past
        episode = await queue.get("ep-123")
        episode.next_retry_at = datetime.utcnow() - timedelta(minutes=1)

        pending = await queue.get_pending()
        assert len(pending) == 1
        assert pending[0].episode_id == "ep-123"

    @pytest.mark.asyncio
    async def test_persistence(self, temp_persist_path):
        """Test queue persistence to disk."""
        # Create queue with persistence
        queue1 = RetryQueue(
            persist_path=temp_persist_path,
            max_retries=3,
        )
        await queue1.start()

        # Add episode
        await queue1.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        # Stop queue (should persist)
        await queue1.stop()

        # Create new queue and load from disk
        queue2 = RetryQueue(
            persist_path=temp_persist_path,
            max_retries=3,
        )
        await queue2.start()

        # Should have the episode
        all_eps = await queue2.get_all()
        assert len(all_eps) == 1
        assert all_eps[0].episode_id == "ep-123"

    @pytest.mark.asyncio
    async def test_get_stats(self, queue):
        """Test getting queue statistics."""
        await queue.start()

        # Add episodes
        await queue.add(
            episode_id="ep-1",
            session_id="session-1",
            session_file="/path/1.jsonl",
            raw_content="content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )
        await queue.add(
            episode_id="ep-2",
            session_id="session-2",
            session_file="/path/2.jsonl",
            raw_content="content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        stats = queue.get_stats()

        assert stats["queue_size"] == 2
        assert stats["pending_retries"] == 2
        assert stats["permanent_failures"] == 0
        assert stats["total_added"] == 2

    @pytest.mark.asyncio
    async def test_clear_permanent_failures(self, queue):
        """Test clearing permanently failed episodes."""
        queue.max_retries = 1
        await queue.start()

        # Add and exhaust retries
        await queue.add(
            episode_id="ep-1",
            session_id="session-1",
            session_file="/path/1.jsonl",
            raw_content="content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )
        await queue.mark_retry_failed("ep-1", "Failed")

        # Add another pending
        await queue.add(
            episode_id="ep-2",
            session_id="session-2",
            session_file="/path/2.jsonl",
            raw_content="content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        # Should have 1 permanent, 1 pending
        stats = queue.get_stats()
        assert stats["permanent_failures"] == 1
        assert stats["pending_retries"] == 1

        # Clear permanent failures
        cleared = await queue.clear_permanent_failures()

        assert cleared == 1
        assert len(await queue.get_all()) == 1


class TestRetryQueueProcessor:
    """Tests for RetryQueueProcessor class."""

    @pytest.fixture
    def queue(self):
        """Create a RetryQueue instance."""
        return RetryQueue(
            persist_path=None,
            max_retries=3,
            retry_delays=[1, 2, 3],  # Short delays for testing
        )

    @pytest.fixture
    def mock_process_fn(self):
        """Create a mock process function."""
        return AsyncMock(return_value=True)

    @pytest.fixture
    def processor(self, queue, mock_process_fn):
        """Create a RetryQueueProcessor instance."""
        return RetryQueueProcessor(
            queue=queue,
            process_fn=mock_process_fn,
            check_interval=1,
        )

    @pytest.mark.asyncio
    async def test_process_now_success(self, queue, processor, mock_process_fn):
        """Test processing pending retries successfully."""
        await queue.start()

        # Add episode with immediate retry
        await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        # Set next_retry_at to past
        episode = await queue.get("ep-123")
        episode.next_retry_at = datetime.utcnow() - timedelta(minutes=1)

        # Process
        success_count = await processor.process_now()

        assert success_count == 1
        mock_process_fn.assert_called_once()

        # Episode should be removed on success
        assert len(await queue.get_all()) == 0

    @pytest.mark.asyncio
    async def test_process_now_failure(self, queue, mock_process_fn):
        """Test processing when process function returns False."""
        mock_process_fn.return_value = False
        processor = RetryQueueProcessor(
            queue=queue,
            process_fn=mock_process_fn,
            check_interval=1,
        )

        await queue.start()

        # Add episode with immediate retry
        await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )

        # Set next_retry_at to past
        episode = await queue.get("ep-123")
        episode.next_retry_at = datetime.utcnow() - timedelta(minutes=1)

        # Process
        success_count = await processor.process_now()

        assert success_count == 0

        # Episode should still be in queue with incremented retry
        episode = await queue.get("ep-123")
        assert episode is not None
        assert episode.retry_count == 1

    @pytest.mark.asyncio
    async def test_process_now_with_llm_check(self, queue, mock_process_fn):
        """Test that process respects LLM availability check."""
        is_available = AsyncMock(return_value=False)
        processor = RetryQueueProcessor(
            queue=queue,
            process_fn=mock_process_fn,
            check_interval=1,
            is_llm_available_fn=is_available,
        )

        await queue.start()

        # Add episode
        await queue.add(
            episode_id="ep-123",
            session_id="session-456",
            session_file="/path/to/session.jsonl",
            raw_content="test content",
            error_type="Error",
            error_message="Error",
            group_id="project",
        )
        episode = await queue.get("ep-123")
        episode.next_retry_at = datetime.utcnow() - timedelta(minutes=1)

        # Process (should skip due to LLM unavailable)
        success_count = await processor.process_now()

        assert success_count == 0
        is_available.assert_called_once()
        mock_process_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_stop(self, processor):
        """Test starting and stopping the processor."""
        await processor.start()
        assert processor._running is True
        assert processor._task is not None

        await processor.stop()
        assert processor._running is False
