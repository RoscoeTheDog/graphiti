"""Session tracking status and health monitoring.

This module provides status aggregation and health monitoring for the
session tracking system, including the retry queue and LLM availability.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Overall service status."""

    RUNNING = "running"
    """Service is running normally."""

    STOPPED = "stopped"
    """Service is not running."""

    DEGRADED = "degraded"
    """Service is running but with reduced functionality."""

    ERROR = "error"
    """Service is in error state."""


class DegradationLevel(int, Enum):
    """Session tracking degradation levels.

    These levels define how much functionality is available based on
    LLM and database availability.
    """

    FULL = 0
    """Level 0: Full Processing - LLM available, all features enabled."""

    PARTIAL = 1
    """Level 1: Partial Processing - Store raw + queue for retry."""

    RAW_ONLY = 2
    """Level 2: Raw Storage Only - LLM unavailable, store raw content only."""


@dataclass
class LLMStatus:
    """LLM service status."""

    available: bool = False
    """Whether LLM is currently available."""

    last_check: Optional[datetime] = None
    """When the last health check was performed."""

    provider: Optional[str] = None
    """LLM provider name (e.g., 'openai', 'anthropic')."""

    circuit_state: Optional[str] = None
    """Circuit breaker state (closed/open/half_open)."""

    error: Optional[str] = None
    """Error message if unavailable."""

    success_rate: Optional[float] = None
    """Recent success rate (0.0 to 1.0)."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'available': self.available,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'provider': self.provider,
            'circuit_state': self.circuit_state,
            'error': self.error,
            'success_rate': self.success_rate,
        }


@dataclass
class QueueStatus:
    """Processing queue status (today's activity)."""

    pending: int = 0
    """Number of sessions pending processing."""

    processing: int = 0
    """Number of sessions currently being processed."""

    completed_today: int = 0
    """Number of sessions completed today."""

    failed_today: int = 0
    """Number of sessions failed today."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'pending': self.pending,
            'processing': self.processing,
            'completed_today': self.completed_today,
            'failed_today': self.failed_today,
        }


@dataclass
class RetryQueueStatus:
    """Retry queue status."""

    count: int = 0
    """Total number of episodes in retry queue."""

    pending_retries: int = 0
    """Number of episodes pending retry."""

    permanent_failures: int = 0
    """Number of permanently failed episodes."""

    next_retry: Optional[datetime] = None
    """When the next retry is scheduled."""

    oldest_failure: Optional[datetime] = None
    """When the oldest failure occurred."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'count': self.count,
            'pending_retries': self.pending_retries,
            'permanent_failures': self.permanent_failures,
            'next_retry': self.next_retry.isoformat() if self.next_retry else None,
            'oldest_failure': self.oldest_failure.isoformat() if self.oldest_failure else None,
        }


@dataclass
class RecentFailure:
    """Information about a recent failure."""

    episode_id: str
    """Episode that failed."""

    session_id: str
    """Session the episode belongs to."""

    error: str
    """Error type/message."""

    retry_count: int
    """Number of retry attempts."""

    next_retry: Optional[datetime] = None
    """When the next retry is scheduled."""

    failed_at: Optional[datetime] = None
    """When the failure occurred."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'episode_id': self.episode_id,
            'session_id': self.session_id,
            'error': self.error,
            'retry_count': self.retry_count,
            'next_retry': self.next_retry.isoformat() if self.next_retry else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
        }


@dataclass
class SessionTrackingHealth:
    """Complete session tracking health status.

    This is the primary status object returned by the health check tool.
    """

    service_status: ServiceStatus = ServiceStatus.STOPPED
    """Overall service status."""

    degradation_level: DegradationLevel = DegradationLevel.FULL
    """Current degradation level."""

    llm_status: LLMStatus = field(default_factory=LLMStatus)
    """LLM service status."""

    queue_status: QueueStatus = field(default_factory=QueueStatus)
    """Processing queue status."""

    retry_queue: RetryQueueStatus = field(default_factory=RetryQueueStatus)
    """Retry queue status."""

    recent_failures: list[RecentFailure] = field(default_factory=list)
    """List of recent failures (last 10)."""

    uptime_seconds: Optional[int] = None
    """Service uptime in seconds."""

    started_at: Optional[datetime] = None
    """When the service was started."""

    last_activity: Optional[datetime] = None
    """When the last session was processed."""

    active_sessions: int = 0
    """Number of currently active (open) sessions."""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'service_status': self.service_status.value,
            'degradation_level': {
                'level': self.degradation_level.value,
                'name': self.degradation_level.name,
                'description': self._get_degradation_description(),
            },
            'llm_status': self.llm_status.to_dict(),
            'queue_status': self.queue_status.to_dict(),
            'retry_queue': self.retry_queue.to_dict(),
            'recent_failures': [f.to_dict() for f in self.recent_failures],
            'uptime_seconds': self.uptime_seconds,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'active_sessions': self.active_sessions,
        }

    def _get_degradation_description(self) -> str:
        """Get human-readable description of degradation level."""
        descriptions = {
            DegradationLevel.FULL: "Full processing - LLM available, all features enabled",
            DegradationLevel.PARTIAL: "Partial processing - storing raw content, queuing for retry",
            DegradationLevel.RAW_ONLY: "Raw storage only - LLM unavailable, no summarization",
        }
        return descriptions.get(self.degradation_level, "Unknown")


class SessionTrackingStatusAggregator:
    """Aggregates status from multiple sources.

    Collects status information from:
    - Session manager
    - Retry queue
    - LLM availability manager
    - Daily statistics

    Usage:
        aggregator = SessionTrackingStatusAggregator()
        aggregator.set_session_manager(session_manager)
        aggregator.set_retry_queue(retry_queue)
        aggregator.set_llm_manager(llm_manager)

        health = await aggregator.get_health()
    """

    def __init__(self):
        """Initialize the aggregator."""
        self._session_manager = None
        self._retry_queue = None
        self._llm_manager = None
        self._started_at: Optional[datetime] = None

        # Daily statistics (reset at midnight)
        self._stats_date: Optional[datetime] = None
        self._daily_stats = {
            'completed': 0,
            'failed': 0,
        }

    def set_session_manager(self, manager) -> None:
        """Set the session manager reference."""
        self._session_manager = manager

    def set_retry_queue(self, queue) -> None:
        """Set the retry queue reference."""
        self._retry_queue = queue

    def set_llm_manager(self, manager) -> None:
        """Set the LLM availability manager reference."""
        self._llm_manager = manager

    def mark_started(self) -> None:
        """Mark service as started."""
        self._started_at = datetime.utcnow()

    def record_completion(self) -> None:
        """Record a successful session completion."""
        self._reset_daily_if_needed()
        self._daily_stats['completed'] += 1

    def record_failure(self) -> None:
        """Record a session processing failure."""
        self._reset_daily_if_needed()
        self._daily_stats['failed'] += 1

    async def get_health(self) -> SessionTrackingHealth:
        """Get complete health status.

        Returns:
            SessionTrackingHealth with all status information
        """
        health = SessionTrackingHealth()

        # Calculate uptime
        if self._started_at:
            health.started_at = self._started_at
            health.uptime_seconds = int(
                (datetime.utcnow() - self._started_at).total_seconds()
            )

        # Get service status from session manager
        if self._session_manager:
            health.service_status = await self._get_service_status()
            health.active_sessions = self._session_manager.get_active_session_count()

        # Get LLM status
        if self._llm_manager:
            health.llm_status = await self._get_llm_status()

        # Calculate degradation level
        health.degradation_level = self._calculate_degradation_level(health)

        # Get queue status
        self._reset_daily_if_needed()
        health.queue_status = QueueStatus(
            pending=0,  # TODO: Track pending sessions
            processing=health.active_sessions,
            completed_today=self._daily_stats['completed'],
            failed_today=self._daily_stats['failed'],
        )

        # Get retry queue status
        if self._retry_queue:
            health.retry_queue = await self._get_retry_queue_status()
            health.recent_failures = await self._get_recent_failures()

        return health

    async def _get_service_status(self) -> ServiceStatus:
        """Determine service status from session manager."""
        if not self._session_manager:
            return ServiceStatus.STOPPED

        if not self._session_manager._is_running:
            return ServiceStatus.STOPPED

        # Check for degradation
        if self._llm_manager:
            try:
                is_available = await self._llm_manager.is_available()
                if not is_available:
                    return ServiceStatus.DEGRADED
            except Exception:
                return ServiceStatus.DEGRADED

        return ServiceStatus.RUNNING

    async def _get_llm_status(self) -> LLMStatus:
        """Get LLM status from availability manager."""
        if not self._llm_manager:
            return LLMStatus(available=True)  # Assume available if no manager

        try:
            status = self._llm_manager.get_status()
            return LLMStatus(
                available=status.get('available', False),
                last_check=datetime.fromisoformat(status['last_health_check'])
                if status.get('last_health_check')
                else None,
                provider=status.get('provider'),
                circuit_state=status.get('circuit_state'),
                error=status.get('error'),
                success_rate=status.get('success_rate'),
            )
        except Exception as e:
            logger.error(f"Error getting LLM status: {e}")
            return LLMStatus(available=False, error=str(e))

    def _calculate_degradation_level(self, health: SessionTrackingHealth) -> DegradationLevel:
        """Calculate degradation level based on current state."""
        if health.service_status == ServiceStatus.STOPPED:
            return DegradationLevel.RAW_ONLY

        if not health.llm_status.available:
            # LLM unavailable - check if we're storing raw
            return DegradationLevel.RAW_ONLY

        if health.retry_queue.pending_retries > 0:
            # Have pending retries - partial processing
            return DegradationLevel.PARTIAL

        return DegradationLevel.FULL

    async def _get_retry_queue_status(self) -> RetryQueueStatus:
        """Get retry queue status."""
        if not self._retry_queue:
            return RetryQueueStatus()

        stats = self._retry_queue.get_stats()
        return RetryQueueStatus(
            count=stats.get('queue_size', 0),
            pending_retries=stats.get('pending_retries', 0),
            permanent_failures=stats.get('permanent_failures', 0),
            next_retry=datetime.fromisoformat(stats['next_retry_at'])
            if stats.get('next_retry_at')
            else None,
            oldest_failure=datetime.fromisoformat(stats['oldest_failure'])
            if stats.get('oldest_failure')
            else None,
        )

    async def _get_recent_failures(self, limit: int = 10) -> list[RecentFailure]:
        """Get recent failures from retry queue."""
        if not self._retry_queue:
            return []

        try:
            all_episodes = await self._retry_queue.get_all()
            # Sort by failed_at descending
            sorted_episodes = sorted(
                all_episodes,
                key=lambda ep: ep.failed_at,
                reverse=True
            )[:limit]

            return [
                RecentFailure(
                    episode_id=ep.episode_id,
                    session_id=ep.session_id,
                    error=ep.error_type,
                    retry_count=ep.retry_count,
                    next_retry=ep.next_retry_at,
                    failed_at=ep.failed_at,
                )
                for ep in sorted_episodes
            ]
        except Exception as e:
            logger.error(f"Error getting recent failures: {e}")
            return []

    def _reset_daily_if_needed(self) -> None:
        """Reset daily stats if date changed."""
        today = datetime.utcnow().date()
        if self._stats_date != today:
            self._stats_date = today
            self._daily_stats = {'completed': 0, 'failed': 0}
