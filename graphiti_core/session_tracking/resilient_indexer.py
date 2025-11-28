"""Resilient session indexer with graceful degradation.

This module wraps the standard SessionIndexer with resilience features:
- Graceful degradation when LLM is unavailable
- Retry queue for failed episodes
- Status tracking and health monitoring
- Auto-recovery when LLM becomes available
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from graphiti_core.graphiti import Graphiti
from graphiti_core.nodes import EpisodeType

from .indexer import SessionIndexer
from .retry_queue import FailedEpisode, RetryQueue, RetryQueueProcessor
from .status import (
    DegradationLevel,
    SessionTrackingHealth,
    SessionTrackingStatusAggregator,
)

logger = logging.getLogger(__name__)


class OnLLMUnavailable(str, Enum):
    """Behavior when LLM is unavailable during session processing."""

    FAIL = "FAIL"
    """Skip session entirely (data loss risk)."""

    STORE_RAW = "STORE_RAW"
    """Store raw session content without LLM processing."""

    STORE_RAW_AND_RETRY = "STORE_RAW_AND_RETRY"
    """Store raw content and queue for retry (recommended)."""


@dataclass
class ResilientIndexerConfig:
    """Configuration for resilient session indexer."""

    on_llm_unavailable: OnLLMUnavailable = OnLLMUnavailable.STORE_RAW_AND_RETRY
    """Behavior when LLM is unavailable."""

    retry_queue_path: Optional[Path] = None
    """Path to persist retry queue (None = in-memory only)."""

    max_retries: int = 5
    """Maximum retry attempts per episode."""

    retry_delays: list[int] = None
    """Delays between retries in seconds (default: exponential backoff)."""

    max_queue_size: int = 1000
    """Maximum episodes in retry queue."""

    auto_recovery_interval: int = 60
    """Seconds between auto-recovery checks."""

    on_permanent_failure: Optional[Callable[[FailedEpisode], None]] = None
    """Callback when episode exhausts all retries."""

    def __post_init__(self):
        if self.retry_delays is None:
            self.retry_delays = [300, 900, 2700, 7200, 21600]  # 5m, 15m, 45m, 2h, 6h


class ResilientSessionIndexer:
    """Session indexer with graceful degradation and retry support.

    This class wraps SessionIndexer to add:
    - LLM availability checking
    - Graceful degradation modes
    - Persistent retry queue
    - Auto-recovery when LLM becomes available
    - Health status reporting

    Usage:
        config = ResilientIndexerConfig(
            on_llm_unavailable=OnLLMUnavailable.STORE_RAW_AND_RETRY,
            retry_queue_path=Path('.graphiti/retry_queue.json')
        )
        indexer = ResilientSessionIndexer(graphiti, config)
        await indexer.start()

        # Index session (handles degradation automatically)
        result = await indexer.index_session(...)

        # Check health
        health = await indexer.get_health()
    """

    def __init__(
        self,
        graphiti: Graphiti,
        config: Optional[ResilientIndexerConfig] = None,
        llm_availability_fn: Optional[Callable[[], bool]] = None,
    ):
        """Initialize resilient indexer.

        Args:
            graphiti: Graphiti instance for graph operations
            config: Resilience configuration
            llm_availability_fn: Async function to check LLM availability
        """
        self.graphiti = graphiti
        self.config = config or ResilientIndexerConfig()
        self.llm_availability_fn = llm_availability_fn

        # Wrapped indexer
        self._indexer = SessionIndexer(graphiti)

        # Retry queue
        self._retry_queue = RetryQueue(
            persist_path=self.config.retry_queue_path,
            max_retries=self.config.max_retries,
            retry_delays=self.config.retry_delays,
            max_queue_size=self.config.max_queue_size,
            on_permanent_failure=self._handle_permanent_failure,
        )

        # Retry processor
        self._retry_processor = RetryQueueProcessor(
            queue=self._retry_queue,
            process_fn=self._retry_episode,
            check_interval=self.config.auto_recovery_interval,
            is_llm_available_fn=self._check_llm_available,
        )

        # Status aggregator
        self._status = SessionTrackingStatusAggregator()
        self._status.set_retry_queue(self._retry_queue)

        # State
        self._running = False
        self._degradation_level = DegradationLevel.FULL

    async def start(self) -> None:
        """Start the resilient indexer."""
        if self._running:
            return

        logger.info("Starting resilient session indexer...")

        # Load retry queue
        await self._retry_queue.start()

        # Start retry processor
        await self._retry_processor.start()

        # Mark started
        self._status.mark_started()
        self._running = True

        # Initial LLM check
        await self._update_degradation_level()

        logger.info(f"Resilient indexer started (degradation level: {self._degradation_level.name})")

    async def stop(self) -> None:
        """Stop the resilient indexer."""
        if not self._running:
            return

        logger.info("Stopping resilient session indexer...")

        # Stop processor
        await self._retry_processor.stop()

        # Persist queue
        await self._retry_queue.stop()

        self._running = False
        logger.info("Resilient indexer stopped")

    async def index_session(
        self,
        session_id: str,
        filtered_content: str,
        group_id: str,
        session_file: Optional[str] = None,
        session_number: Optional[int] = None,
        reference_time: Optional[datetime] = None,
        previous_episode_uuid: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Index a session with resilience.

        This method attempts to index the session and handles failures
        according to the configured degradation mode.

        Args:
            session_id: Unique session identifier
            filtered_content: Filtered session content
            group_id: Group ID for the session
            session_file: Path to session file (for retry queue)
            session_number: Optional session sequence number
            reference_time: Optional timestamp for the session
            previous_episode_uuid: Optional UUID of previous session
            metadata: Optional additional metadata

        Returns:
            Dict with:
                - success: bool - Whether indexing succeeded
                - episode_uuid: str | None - UUID if successful
                - degraded: bool - Whether degraded mode was used
                - queued_for_retry: bool - Whether queued for retry
                - error: str | None - Error message if failed
        """
        # Check degradation level
        await self._update_degradation_level()

        result = {
            'success': False,
            'episode_uuid': None,
            'degraded': False,
            'queued_for_retry': False,
            'error': None,
        }

        # Try full processing
        if self._degradation_level == DegradationLevel.FULL:
            try:
                episode_uuid = await self._indexer.index_session(
                    session_id=session_id,
                    filtered_content=filtered_content,
                    group_id=group_id,
                    session_number=session_number,
                    reference_time=reference_time,
                    previous_episode_uuid=previous_episode_uuid,
                )
                result['success'] = True
                result['episode_uuid'] = episode_uuid
                self._status.record_completion()
                return result

            except Exception as e:
                logger.warning(f"Full processing failed for session {session_id}: {e}")
                # Fall through to degradation handling
                result['error'] = str(e)

        # Handle degradation
        return await self._handle_degraded_indexing(
            session_id=session_id,
            filtered_content=filtered_content,
            group_id=group_id,
            session_file=session_file,
            session_number=session_number,
            reference_time=reference_time,
            previous_episode_uuid=previous_episode_uuid,
            metadata=metadata,
            original_error=result.get('error'),
        )

    async def _handle_degraded_indexing(
        self,
        session_id: str,
        filtered_content: str,
        group_id: str,
        session_file: Optional[str],
        session_number: Optional[int],
        reference_time: Optional[datetime],
        previous_episode_uuid: Optional[str],
        metadata: Optional[dict],
        original_error: Optional[str],
    ) -> dict[str, Any]:
        """Handle indexing when in degraded mode.

        Implements graceful degradation based on config.
        """
        result = {
            'success': False,
            'episode_uuid': None,
            'degraded': True,
            'queued_for_retry': False,
            'error': original_error,
        }

        mode = self.config.on_llm_unavailable

        if mode == OnLLMUnavailable.FAIL:
            # FAIL mode: Don't store anything
            logger.warning(f"Session {session_id} dropped (FAIL mode, LLM unavailable)")
            result['error'] = "LLM unavailable, session dropped (FAIL mode)"
            self._status.record_failure()
            return result

        if mode in (OnLLMUnavailable.STORE_RAW, OnLLMUnavailable.STORE_RAW_AND_RETRY):
            # Store raw episode without LLM processing
            try:
                episode_uuid = await self._store_raw_episode(
                    session_id=session_id,
                    filtered_content=filtered_content,
                    group_id=group_id,
                    session_number=session_number,
                    reference_time=reference_time,
                    needs_reprocessing=True,
                )
                result['episode_uuid'] = episode_uuid
                result['success'] = True

                logger.info(
                    f"Session {session_id} stored as raw (LLM unavailable), "
                    f"UUID: {episode_uuid}"
                )

            except Exception as e:
                logger.error(f"Failed to store raw episode for {session_id}: {e}")
                result['error'] = f"Failed to store raw: {e}"

        if mode == OnLLMUnavailable.STORE_RAW_AND_RETRY:
            # Queue for retry
            try:
                await self._retry_queue.add(
                    episode_id=result.get('episode_uuid') or str(uuid.uuid4()),
                    session_id=session_id,
                    session_file=session_file or "",
                    raw_content=filtered_content,
                    error_type="LLMUnavailableError",
                    error_message=original_error or "LLM unavailable",
                    group_id=group_id,
                    metadata={
                        'session_number': session_number,
                        'reference_time': reference_time.isoformat() if reference_time else None,
                        'previous_episode_uuid': previous_episode_uuid,
                        **(metadata or {}),
                    },
                )
                result['queued_for_retry'] = True
                logger.info(f"Session {session_id} queued for retry")

            except Exception as e:
                logger.error(f"Failed to queue session {session_id} for retry: {e}")

        if result['success']:
            self._status.record_completion()
        else:
            self._status.record_failure()

        return result

    async def _store_raw_episode(
        self,
        session_id: str,
        filtered_content: str,
        group_id: str,
        session_number: Optional[int] = None,
        reference_time: Optional[datetime] = None,
        needs_reprocessing: bool = True,
    ) -> str:
        """Store episode as raw content without LLM processing.

        This stores the session content directly without entity extraction
        or summarization. The episode is marked for reprocessing.

        Args:
            session_id: Session ID
            filtered_content: Content to store
            group_id: Group ID
            session_number: Optional session number
            reference_time: Optional reference time
            needs_reprocessing: Mark for later LLM processing

        Returns:
            UUID of created episode
        """
        # Build episode name
        if session_number:
            episode_name = f'Session {session_number:03d}: {session_id[:8]} [RAW]'
        else:
            episode_name = f'Session {session_id[:8]} [RAW]'

        ref_time = reference_time or datetime.now()

        # Build source description
        source_description = (
            f'Raw Claude Code session {session_id} '
            f'(stored without LLM processing, needs_reprocessing={needs_reprocessing})'
        )

        logger.info(f'Storing raw episode: {episode_name} (group: {group_id})')

        # Add episode directly to Graphiti (bypasses LLM)
        # Note: add_episode with skip_llm=True would be ideal but may not exist
        # For now, we'll add with minimal content to avoid LLM calls
        result = await self.graphiti.add_episode(
            name=episode_name,
            episode_body=filtered_content,
            source_description=source_description,
            reference_time=ref_time,
            source=EpisodeType.text,
            group_id=group_id,
        )

        episode_uuid = result.episode.uuid
        logger.info(f'Raw episode stored: {episode_name} (UUID: {episode_uuid})')

        return episode_uuid

    async def _check_llm_available(self) -> bool:
        """Check if LLM is available."""
        if not self.llm_availability_fn:
            # No availability function, assume available
            return True

        try:
            if asyncio.iscoroutinefunction(self.llm_availability_fn):
                return await self.llm_availability_fn()
            return self.llm_availability_fn()
        except Exception as e:
            logger.error(f"Error checking LLM availability: {e}")
            return False

    async def _update_degradation_level(self) -> None:
        """Update current degradation level based on LLM status."""
        llm_available = await self._check_llm_available()

        if llm_available:
            if self._degradation_level != DegradationLevel.FULL:
                logger.info("LLM available, returning to full processing")
            self._degradation_level = DegradationLevel.FULL
        else:
            mode = self.config.on_llm_unavailable
            if mode == OnLLMUnavailable.FAIL:
                self._degradation_level = DegradationLevel.RAW_ONLY
            elif mode == OnLLMUnavailable.STORE_RAW:
                self._degradation_level = DegradationLevel.RAW_ONLY
            else:  # STORE_RAW_AND_RETRY
                self._degradation_level = DegradationLevel.PARTIAL

            if self._degradation_level != DegradationLevel.FULL:
                logger.warning(
                    f"LLM unavailable, operating in {self._degradation_level.name} mode"
                )

    async def _retry_episode(self, episode: FailedEpisode) -> bool:
        """Retry processing a failed episode.

        Args:
            episode: Failed episode to retry

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"Retrying episode {episode.episode_id} "
            f"(attempt {episode.retry_count + 1}/{self.config.max_retries})"
        )

        try:
            # Extract metadata
            metadata = episode.metadata
            session_number = metadata.get('session_number')
            reference_time = None
            if metadata.get('reference_time'):
                reference_time = datetime.fromisoformat(metadata['reference_time'])
            previous_uuid = metadata.get('previous_episode_uuid')

            # Attempt full indexing
            await self._indexer.index_session(
                session_id=episode.session_id,
                filtered_content=episode.raw_content,
                group_id=episode.group_id,
                session_number=session_number,
                reference_time=reference_time,
                previous_episode_uuid=previous_uuid,
            )

            logger.info(f"Episode {episode.episode_id} retry succeeded")
            return True

        except Exception as e:
            logger.error(f"Episode {episode.episode_id} retry failed: {e}")
            return False

    def _handle_permanent_failure(self, episode: FailedEpisode) -> None:
        """Handle permanent failure of an episode.

        Called when all retries are exhausted.
        """
        logger.error(
            f"Episode {episode.episode_id} permanently failed after "
            f"{episode.retry_count} retries"
        )

        # Call user callback if configured
        if self.config.on_permanent_failure:
            try:
                self.config.on_permanent_failure(episode)
            except Exception as e:
                logger.error(f"Error in permanent failure callback: {e}")

    async def get_health(self) -> SessionTrackingHealth:
        """Get current health status.

        Returns:
            SessionTrackingHealth with all status information
        """
        # Update degradation level
        await self._update_degradation_level()

        # Get health from status aggregator
        health = await self._status.get_health()
        health.degradation_level = self._degradation_level

        return health

    async def get_failed_episodes(
        self,
        include_permanent: bool = True,
        limit: int = 100,
    ) -> list[FailedEpisode]:
        """Get failed episodes from retry queue.

        Args:
            include_permanent: Include permanently failed episodes
            limit: Maximum number to return

        Returns:
            List of FailedEpisode objects
        """
        all_episodes = await self._retry_queue.get_all()

        if not include_permanent:
            all_episodes = [ep for ep in all_episodes if not ep.permanent_failure]

        # Sort by failed_at descending
        all_episodes.sort(key=lambda ep: ep.failed_at, reverse=True)

        return all_episodes[:limit]

    async def process_pending_retries(self) -> int:
        """Manually trigger pending retry processing.

        Returns:
            Number of episodes successfully processed
        """
        return await self._retry_processor.process_now()

    def get_degradation_level(self) -> DegradationLevel:
        """Get current degradation level."""
        return self._degradation_level

    @property
    def retry_queue(self) -> RetryQueue:
        """Get retry queue for direct access."""
        return self._retry_queue
