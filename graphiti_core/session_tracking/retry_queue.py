"""Retry queue for failed session tracking episodes.

This module provides a persistent retry queue for episodes that failed during
LLM processing. Episodes are stored with exponential backoff retry scheduling
and can be recovered when the LLM becomes available again.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class FailedEpisode:
    """A session episode that failed LLM processing.

    Tracks all information needed to retry processing when LLM recovers.
    """

    episode_id: str
    """Unique identifier for this episode."""

    session_id: str
    """Session ID this episode belongs to."""

    session_file: str
    """Path to the original session file."""

    raw_content: str
    """Raw episode content (preserved for retry)."""

    group_id: str
    """Group ID for the session (project-scoped)."""

    error_type: str
    """Classification of the error (e.g., 'RateLimitError', 'LLMUnavailableError')."""

    error_message: str
    """Human-readable error message."""

    failed_at: datetime
    """When the episode first failed."""

    retry_count: int = 0
    """Number of retry attempts so far."""

    next_retry_at: Optional[datetime] = None
    """Scheduled time for next retry attempt."""

    permanent_failure: bool = False
    """True if all retries exhausted (permanent failure)."""

    last_retry_at: Optional[datetime] = None
    """When the last retry was attempted."""

    created_at: datetime = field(default_factory=datetime.utcnow)
    """When this failed episode was created."""

    metadata: dict = field(default_factory=dict)
    """Additional metadata (e.g., session summary, token count)."""

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        data = asdict(self)
        # Convert datetime fields to ISO format strings
        for key in ['failed_at', 'next_retry_at', 'last_retry_at', 'created_at']:
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'FailedEpisode':
        """Create from dictionary (e.g., loaded from JSON)."""
        # Convert ISO format strings back to datetime
        for key in ['failed_at', 'next_retry_at', 'last_retry_at', 'created_at']:
            if data.get(key) is not None:
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class RetryQueue:
    """Persistent queue for failed episode retries.

    Provides:
    - Exponential backoff scheduling
    - Disk persistence for crash recovery
    - Queue size limits
    - Automatic retry triggering

    Usage:
        queue = RetryQueue(
            persist_path=Path('.graphiti/retry_queue.json'),
            max_retries=5,
            retry_delays=[300, 900, 2700, 7200, 21600]  # 5m, 15m, 45m, 2h, 6h
        )
        await queue.start()

        # Add failed episode
        await queue.add(episode_id, session_id, content, error, group_id)

        # Process pending retries
        await queue.process_pending(process_fn)
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        max_retries: int = 5,
        retry_delays: Optional[list[int]] = None,
        max_queue_size: int = 1000,
        on_permanent_failure: Optional[Callable[[FailedEpisode], None]] = None,
    ):
        """Initialize the retry queue.

        Args:
            persist_path: Path to JSON file for persistence (None = in-memory only)
            max_retries: Maximum retry attempts per episode
            retry_delays: List of delays in seconds for each retry (exponential backoff)
            max_queue_size: Maximum number of episodes to queue
            on_permanent_failure: Callback when episode exhausts all retries
        """
        self.persist_path = persist_path
        self.max_retries = max_retries
        self.retry_delays = retry_delays or [300, 900, 2700, 7200, 21600]
        self.max_queue_size = max_queue_size
        self.on_permanent_failure = on_permanent_failure

        # Queue storage
        self._queue: dict[str, FailedEpisode] = {}
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = {
            'total_added': 0,
            'total_retried': 0,
            'total_succeeded': 0,
            'total_failed_permanently': 0,
        }

    async def start(self) -> None:
        """Start the retry queue, loading persisted data."""
        if self.persist_path and self.persist_path.exists():
            await self._load_from_disk()
            logger.info(f"Loaded {len(self._queue)} failed episodes from disk")

    async def stop(self) -> None:
        """Stop the retry queue, persisting data."""
        if self.persist_path:
            await self._persist_to_disk()
            logger.info(f"Persisted {len(self._queue)} failed episodes to disk")

    async def add(
        self,
        episode_id: str,
        session_id: str,
        session_file: str,
        raw_content: str,
        error_type: str,
        error_message: str,
        group_id: str,
        metadata: Optional[dict] = None,
    ) -> Optional[FailedEpisode]:
        """Add a failed episode to the retry queue.

        Args:
            episode_id: Unique identifier for the episode
            session_id: Session ID the episode belongs to
            session_file: Path to the session file
            raw_content: Raw episode content for retry
            error_type: Error classification string
            error_message: Human-readable error message
            group_id: Group ID for the session
            metadata: Optional additional metadata

        Returns:
            The created FailedEpisode, or None if queue is full
        """
        async with self._lock:
            # Check queue size limit
            if len(self._queue) >= self.max_queue_size:
                logger.warning(
                    f"Retry queue full ({self.max_queue_size}), dropping episode {episode_id}"
                )
                return None

            # Check if already queued
            if episode_id in self._queue:
                logger.debug(f"Episode {episode_id} already in retry queue")
                return self._queue[episode_id]

            # Calculate first retry time
            first_delay = self.retry_delays[0] if self.retry_delays else 300
            next_retry = datetime.utcnow() + timedelta(seconds=first_delay)

            # Create failed episode
            episode = FailedEpisode(
                episode_id=episode_id,
                session_id=session_id,
                session_file=session_file,
                raw_content=raw_content,
                group_id=group_id,
                error_type=error_type,
                error_message=error_message,
                failed_at=datetime.utcnow(),
                next_retry_at=next_retry,
                metadata=metadata or {},
            )

            self._queue[episode_id] = episode
            self._stats['total_added'] += 1

            logger.info(
                f"Added episode {episode_id} to retry queue "
                f"(next retry at {next_retry.isoformat()})"
            )

            # Persist to disk
            if self.persist_path:
                await self._persist_to_disk()

            return episode

    async def get_pending(self) -> list[FailedEpisode]:
        """Get all episodes due for retry.

        Returns:
            List of episodes where next_retry_at <= now and not permanent failure
        """
        now = datetime.utcnow()
        async with self._lock:
            return [
                ep for ep in self._queue.values()
                if not ep.permanent_failure
                and ep.next_retry_at is not None
                and ep.next_retry_at <= now
            ]

    async def get_all(self) -> list[FailedEpisode]:
        """Get all episodes in the queue."""
        async with self._lock:
            return list(self._queue.values())

    async def get(self, episode_id: str) -> Optional[FailedEpisode]:
        """Get a specific episode by ID."""
        async with self._lock:
            return self._queue.get(episode_id)

    async def mark_success(self, episode_id: str) -> None:
        """Mark an episode as successfully processed (removes from queue)."""
        async with self._lock:
            if episode_id in self._queue:
                del self._queue[episode_id]
                self._stats['total_succeeded'] += 1
                logger.info(f"Episode {episode_id} processed successfully, removed from queue")

                if self.persist_path:
                    await self._persist_to_disk()

    async def mark_retry_failed(self, episode_id: str, error_message: str) -> bool:
        """Mark a retry attempt as failed, schedule next retry.

        Args:
            episode_id: Episode to mark failed
            error_message: Error message from this attempt

        Returns:
            True if more retries available, False if permanent failure
        """
        async with self._lock:
            episode = self._queue.get(episode_id)
            if not episode:
                return False

            episode.retry_count += 1
            episode.last_retry_at = datetime.utcnow()
            episode.error_message = error_message
            self._stats['total_retried'] += 1

            # Check if exhausted retries
            if episode.retry_count >= self.max_retries:
                episode.permanent_failure = True
                episode.next_retry_at = None
                self._stats['total_failed_permanently'] += 1

                logger.warning(
                    f"Episode {episode_id} exhausted all retries ({self.max_retries}), "
                    "marking as permanent failure"
                )

                # Trigger notification callback
                if self.on_permanent_failure:
                    try:
                        self.on_permanent_failure(episode)
                    except Exception as e:
                        logger.error(f"Error in permanent failure callback: {e}")

                if self.persist_path:
                    await self._persist_to_disk()

                return False

            # Schedule next retry
            delay_index = min(episode.retry_count, len(self.retry_delays) - 1)
            delay = self.retry_delays[delay_index]
            episode.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)

            logger.info(
                f"Episode {episode_id} retry {episode.retry_count}/{self.max_retries} failed, "
                f"next retry in {delay}s at {episode.next_retry_at.isoformat()}"
            )

            if self.persist_path:
                await self._persist_to_disk()

            return True

    async def remove(self, episode_id: str) -> bool:
        """Remove an episode from the queue.

        Args:
            episode_id: Episode to remove

        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            if episode_id in self._queue:
                del self._queue[episode_id]
                if self.persist_path:
                    await self._persist_to_disk()
                return True
            return False

    async def clear_permanent_failures(self) -> int:
        """Remove all permanently failed episodes.

        Returns:
            Number of episodes removed
        """
        async with self._lock:
            to_remove = [
                ep_id for ep_id, ep in self._queue.items()
                if ep.permanent_failure
            ]
            for ep_id in to_remove:
                del self._queue[ep_id]

            if to_remove and self.persist_path:
                await self._persist_to_disk()

            return len(to_remove)

    def get_stats(self) -> dict:
        """Get queue statistics."""
        pending_count = sum(
            1 for ep in self._queue.values()
            if not ep.permanent_failure
        )
        failed_count = sum(
            1 for ep in self._queue.values()
            if ep.permanent_failure
        )

        # Find next retry time
        next_retry = None
        for ep in self._queue.values():
            if ep.next_retry_at and not ep.permanent_failure:
                if next_retry is None or ep.next_retry_at < next_retry:
                    next_retry = ep.next_retry_at

        # Find oldest failure
        oldest_failure = None
        for ep in self._queue.values():
            if oldest_failure is None or ep.failed_at < oldest_failure:
                oldest_failure = ep.failed_at

        return {
            'queue_size': len(self._queue),
            'pending_retries': pending_count,
            'permanent_failures': failed_count,
            'next_retry_at': next_retry.isoformat() if next_retry else None,
            'oldest_failure': oldest_failure.isoformat() if oldest_failure else None,
            **self._stats,
        }

    async def _load_from_disk(self) -> None:
        """Load queue from disk persistence."""
        if not self.persist_path or not self.persist_path.exists():
            return

        try:
            data = json.loads(self.persist_path.read_text(encoding='utf-8'))
            self._queue = {
                ep_id: FailedEpisode.from_dict(ep_data)
                for ep_id, ep_data in data.get('queue', {}).items()
            }
            self._stats = data.get('stats', self._stats)
        except Exception as e:
            logger.error(f"Error loading retry queue from disk: {e}")
            self._queue = {}

    async def _persist_to_disk(self) -> None:
        """Persist queue to disk."""
        if not self.persist_path:
            return

        try:
            # Ensure parent directory exists
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'queue': {ep_id: ep.to_dict() for ep_id, ep in self._queue.items()},
                'stats': self._stats,
                'last_updated': datetime.utcnow().isoformat(),
            }
            self.persist_path.write_text(
                json.dumps(data, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"Error persisting retry queue to disk: {e}")


class RetryQueueProcessor:
    """Processes pending retries from the queue.

    Monitors the retry queue and automatically processes pending episodes
    when the LLM becomes available.
    """

    def __init__(
        self,
        queue: RetryQueue,
        process_fn: Callable[[FailedEpisode], bool],
        check_interval: int = 60,
        is_llm_available_fn: Optional[Callable[[], bool]] = None,
    ):
        """Initialize the processor.

        Args:
            queue: RetryQueue to process
            process_fn: Async function to process a failed episode (returns True on success)
            check_interval: Seconds between checking for pending retries
            is_llm_available_fn: Optional function to check LLM availability
        """
        self.queue = queue
        self.process_fn = process_fn
        self.check_interval = check_interval
        self.is_llm_available_fn = is_llm_available_fn

        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the processor loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("RetryQueueProcessor started")

    async def stop(self) -> None:
        """Stop the processor loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("RetryQueueProcessor stopped")

    async def process_now(self) -> int:
        """Process all pending retries immediately.

        Returns:
            Number of episodes successfully processed
        """
        # Check LLM availability
        if self.is_llm_available_fn and not await self._check_llm():
            logger.debug("LLM not available, skipping retry processing")
            return 0

        pending = await self.queue.get_pending()
        if not pending:
            return 0

        logger.info(f"Processing {len(pending)} pending retries")
        success_count = 0

        for episode in pending:
            try:
                if asyncio.iscoroutinefunction(self.process_fn):
                    success = await self.process_fn(episode)
                else:
                    success = self.process_fn(episode)

                if success:
                    await self.queue.mark_success(episode.episode_id)
                    success_count += 1
                else:
                    await self.queue.mark_retry_failed(
                        episode.episode_id,
                        "Processing returned False"
                    )
            except Exception as e:
                logger.error(f"Error processing retry for {episode.episode_id}: {e}")
                await self.queue.mark_retry_failed(episode.episode_id, str(e))

        return success_count

    async def _check_llm(self) -> bool:
        """Check if LLM is available."""
        if not self.is_llm_available_fn:
            return True

        try:
            if asyncio.iscoroutinefunction(self.is_llm_available_fn):
                return await self.is_llm_available_fn()
            return self.is_llm_available_fn()
        except Exception as e:
            logger.error(f"Error checking LLM availability: {e}")
            return False

    async def _process_loop(self) -> None:
        """Background loop to process pending retries."""
        while self._running:
            try:
                await self.process_now()
            except Exception as e:
                logger.error(f"Error in retry processing loop: {e}")

            await asyncio.sleep(self.check_interval)
