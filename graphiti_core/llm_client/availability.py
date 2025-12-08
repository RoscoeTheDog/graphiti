"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .client import LLMClient

logger = logging.getLogger(__name__)


# =============================================================================
# Error Classification (AC-17.5, AC-17.6, AC-17.7)
# =============================================================================


class LLMErrorType(Enum):
    """Classification of LLM errors by permanence."""

    PERMANENT = "permanent"  # Invalid API key, account suspended, model not available
    TRANSIENT = "transient"  # Rate limit, timeout, server error, connection refused
    UNKNOWN = "unknown"  # Unclassified errors


@dataclass
class LLMError:
    """Structured representation of an LLM error."""

    error_type: LLMErrorType
    message: str
    original_exception: Exception | None = None
    status_code: int | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retryable: bool = False

    def __str__(self) -> str:
        return f"[{self.error_type.value}] {self.message}"


# Error classes are imported from errors.py to avoid duplication
# Import them here for convenience of users importing from availability module
from .errors import LLMAuthenticationError, LLMRateLimitError, LLMUnavailableError


class LLMErrorClassifier:
    """
    Classifies LLM errors as transient or permanent (AC-17.5, AC-17.6).

    Error Classification Rules:
    - PERMANENT: 401 (Unauthorized), 403 (Forbidden - account suspended),
                 404 (Model not found), invalid API key errors
    - TRANSIENT: 429 (Rate limit), 5xx (Server errors), timeouts,
                 connection errors, network failures
    """

    # HTTP status codes that indicate permanent errors
    PERMANENT_STATUS_CODES = {401, 403, 404}

    # HTTP status codes that indicate transient errors
    TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}

    # Error message patterns for permanent errors
    PERMANENT_PATTERNS = [
        "invalid api key",
        "invalid_api_key",
        "authentication failed",
        "account suspended",
        "account deactivated",
        "model not found",
        "model does not exist",
        "permission denied",
        "access denied",
        "unauthorized",
        "forbidden",
    ]

    # Error message patterns for transient errors
    TRANSIENT_PATTERNS = [
        "rate limit",
        "ratelimit",
        "too many requests",
        "timeout",
        "timed out",
        "connection error",
        "connection refused",
        "connection reset",
        "network error",
        "server error",
        "internal server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "overloaded",
        "capacity",
        "temporarily unavailable",
    ]

    @classmethod
    def classify(cls, exception: Exception) -> LLMError:
        """
        Classify an exception as permanent or transient.

        Args:
            exception: The exception to classify

        Returns:
            LLMError with classification and metadata
        """
        error_message = str(exception).lower()
        status_code = cls._extract_status_code(exception)

        # Check status code first
        if status_code is not None:
            if status_code in cls.PERMANENT_STATUS_CODES:
                return LLMError(
                    error_type=LLMErrorType.PERMANENT,
                    message=str(exception),
                    original_exception=exception,
                    status_code=status_code,
                    retryable=False,
                )
            if status_code in cls.TRANSIENT_STATUS_CODES:
                return LLMError(
                    error_type=LLMErrorType.TRANSIENT,
                    message=str(exception),
                    original_exception=exception,
                    status_code=status_code,
                    retryable=True,
                )

        # Check error message patterns
        for pattern in cls.PERMANENT_PATTERNS:
            if pattern in error_message:
                return LLMError(
                    error_type=LLMErrorType.PERMANENT,
                    message=str(exception),
                    original_exception=exception,
                    status_code=status_code,
                    retryable=False,
                )

        for pattern in cls.TRANSIENT_PATTERNS:
            if pattern in error_message:
                return LLMError(
                    error_type=LLMErrorType.TRANSIENT,
                    message=str(exception),
                    original_exception=exception,
                    status_code=status_code,
                    retryable=True,
                )

        # Check for common exception types
        exception_name = type(exception).__name__.lower()
        if any(
            t in exception_name
            for t in ["timeout", "connection", "network", "ratelimit", "rate"]
        ):
            return LLMError(
                error_type=LLMErrorType.TRANSIENT,
                message=str(exception),
                original_exception=exception,
                status_code=status_code,
                retryable=True,
            )

        if any(t in exception_name for t in ["auth", "permission", "forbidden"]):
            return LLMError(
                error_type=LLMErrorType.PERMANENT,
                message=str(exception),
                original_exception=exception,
                status_code=status_code,
                retryable=False,
            )

        # Default to unknown (treat as transient for safety)
        return LLMError(
            error_type=LLMErrorType.UNKNOWN,
            message=str(exception),
            original_exception=exception,
            status_code=status_code,
            retryable=True,
        )

    @classmethod
    def _extract_status_code(cls, exception: Exception) -> int | None:
        """Extract HTTP status code from exception if available."""
        # Try common attributes
        if hasattr(exception, "status_code"):
            return getattr(exception, "status_code")
        if hasattr(exception, "status"):
            return getattr(exception, "status")
        if hasattr(exception, "response"):
            response = getattr(exception, "response")
            if hasattr(response, "status_code"):
                return response.status_code
            if hasattr(response, "status"):
                return response.status
        return None


# =============================================================================
# Circuit Breaker (AC-17.8, AC-17.9, AC-17.10, AC-17.11)
# =============================================================================


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    enabled: bool = True
    failure_threshold: int = 5  # Consecutive failures to open circuit
    recovery_timeout_seconds: float = 300.0  # Time before testing recovery
    half_open_max_calls: int = 3  # Max calls in half-open state


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures (AC-17.8-17.11).

    States:
    - CLOSED: Normal operation, tracking failures
    - OPEN: Circuit tripped, rejecting all calls
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def is_available(self) -> bool:
        """Check if circuit allows calls."""
        if not self.config.enabled:
            return True
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.recovery_timeout_seconds:
                    return True  # Allow transition to half-open
            return False
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        return True

    async def record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.config.half_open_max_calls:
                    # Enough successes, close the circuit
                    self._transition_to_closed()
                    logger.info("Circuit breaker closed after successful recovery")
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def record_failure(self, error: LLMError | None = None) -> None:
        """Record a failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state reopens the circuit
                self._transition_to_open()
                logger.warning("Circuit breaker reopened after failure in half-open state")
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
                    logger.warning(
                        f"Circuit breaker opened after {self._failure_count} consecutive failures"
                    )

    async def attempt_call(self) -> bool:
        """
        Check if a call should be attempted.

        Returns:
            True if call should proceed, False if circuit is open
        """
        if not self.config.enabled:
            return True

        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if we should transition to half-open
                if self._last_failure_time is not None:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.config.recovery_timeout_seconds:
                        self._transition_to_half_open()
                        logger.info(
                            "Circuit breaker entering half-open state for recovery test"
                        )
                        return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return True

    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self._state = CircuitState.OPEN
        self._half_open_calls = 0

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._failure_count = 0

    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0


# =============================================================================
# Health Monitor (AC-17.1, AC-17.3, AC-17.4)
# =============================================================================


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    healthy: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float | None = None
    error: LLMError | None = None
    provider: str = "unknown"

    def __str__(self) -> str:
        status = "healthy" if self.healthy else "unhealthy"
        latency = f" ({self.latency_ms:.0f}ms)" if self.latency_ms else ""
        return f"[{self.provider}] {status}{latency}"


@dataclass
class HealthCheckConfig:
    """Configuration for health monitoring."""

    enabled: bool = True
    interval_seconds: float = 60.0
    on_startup: bool = True
    timeout_seconds: float = 10.0
    history_size: int = 10


class LLMHealthMonitor:
    """
    Monitors LLM health with periodic checks (AC-17.1, AC-17.3, AC-17.4).

    Features:
    - Periodic health checks at configurable intervals
    - Health check history tracking
    - Success rate calculation
    - Integration with circuit breaker
    """

    def __init__(
        self,
        health_check_fn: Callable[[], Any] | None = None,
        config: HealthCheckConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        """
        Initialize health monitor.

        Args:
            health_check_fn: Async function to perform health check
            config: Health check configuration
            circuit_breaker: Optional circuit breaker to integrate with
        """
        self.config = config or HealthCheckConfig()
        self._health_check_fn = health_check_fn
        self._circuit_breaker = circuit_breaker

        # Health check history
        self._history: deque[HealthCheckResult] = deque(maxlen=self.config.history_size)
        self._last_check: HealthCheckResult | None = None

        # Background task management
        self._monitor_task: asyncio.Task[None] | None = None
        self._running = False
        self._provider = "unknown"

    def set_health_check_fn(self, fn: Callable[[], Any]) -> None:
        """Set the health check function."""
        self._health_check_fn = fn

    def set_provider(self, provider: str) -> None:
        """Set the provider name for logging."""
        self._provider = provider

    @property
    def is_healthy(self) -> bool:
        """Check if last health check was successful."""
        if self._last_check is None:
            return True  # Assume healthy if no check has been performed
        return self._last_check.healthy

    @property
    def success_rate(self) -> float:
        """Calculate success rate from recent health checks."""
        if not self._history:
            return 1.0
        successes = sum(1 for r in self._history if r.healthy)
        return successes / len(self._history)

    @property
    def last_check(self) -> HealthCheckResult | None:
        """Get the most recent health check result."""
        return self._last_check

    @property
    def history(self) -> list[HealthCheckResult]:
        """Get health check history."""
        return list(self._history)

    async def check_health(self) -> HealthCheckResult:
        """
        Perform a health check.

        Returns:
            HealthCheckResult with status and metadata
        """
        if self._health_check_fn is None:
            # No health check function configured, assume healthy
            result = HealthCheckResult(healthy=True, provider=self._provider)
            self._last_check = result
            return result

        start_time = time.time()
        try:
            # Call the health check function with timeout
            if asyncio.iscoroutinefunction(self._health_check_fn):
                await asyncio.wait_for(
                    self._health_check_fn(), timeout=self.config.timeout_seconds
                )
            else:
                self._health_check_fn()

            latency_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                healthy=True, latency_ms=latency_ms, provider=self._provider
            )

            # Update circuit breaker if configured
            if self._circuit_breaker:
                await self._circuit_breaker.record_success()

            logger.debug(f"Health check passed: {result}")

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            error = LLMError(
                error_type=LLMErrorType.TRANSIENT,
                message=f"Health check timed out after {self.config.timeout_seconds}s",
            )
            result = HealthCheckResult(
                healthy=False, latency_ms=latency_ms, error=error, provider=self._provider
            )
            if self._circuit_breaker:
                await self._circuit_breaker.record_failure(error)
            logger.warning(f"Health check timed out: {error}")

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error = LLMErrorClassifier.classify(e)
            result = HealthCheckResult(
                healthy=False, latency_ms=latency_ms, error=error, provider=self._provider
            )
            if self._circuit_breaker:
                await self._circuit_breaker.record_failure(error)
            logger.warning(f"Health check failed: {error}")

        self._last_check = result
        self._history.append(result)
        return result

    async def start_monitoring(self) -> None:
        """Start background health monitoring."""
        if not self.config.enabled:
            logger.debug("Health monitoring disabled")
            return

        if self._running:
            logger.debug("Health monitoring already running")
            return

        self._running = True

        # Perform startup check if configured
        if self.config.on_startup:
            logger.info("Performing startup health check...")
            await self.check_health()

        # Start background monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"Started health monitoring (interval: {self.config.interval_seconds}s)"
        )

    async def stop_monitoring(self) -> None:
        """Stop background health monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        logger.info("Stopped health monitoring")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.interval_seconds)
                if self._running:
                    await self.check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")


# =============================================================================
# LLM Availability Manager
# =============================================================================


@dataclass
class LLMAvailabilityConfig:
    """Combined configuration for LLM availability management."""

    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)


class LLMAvailabilityManager:
    """
    Unified manager for LLM availability (integrates all components).

    Combines:
    - Health monitoring
    - Error classification
    - Circuit breaker

    Usage:
        manager = LLMAvailabilityManager()
        manager.set_health_check_fn(client.health_check)
        await manager.start()

        # Before making an LLM call
        if not await manager.is_available():
            raise LLMUnavailableError()

        try:
            result = await llm_call()
            await manager.record_success()
        except Exception as e:
            await manager.record_failure(e)
            raise
    """

    def __init__(self, config: LLMAvailabilityConfig | None = None):
        self.config = config or LLMAvailabilityConfig()

        # Initialize components
        self._circuit_breaker = CircuitBreaker(self.config.circuit_breaker)
        self._health_monitor = LLMHealthMonitor(
            config=self.config.health_check, circuit_breaker=self._circuit_breaker
        )
        self._classifier = LLMErrorClassifier()

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get the circuit breaker instance."""
        return self._circuit_breaker

    @property
    def health_monitor(self) -> LLMHealthMonitor:
        """Get the health monitor instance."""
        return self._health_monitor

    def set_health_check_fn(self, fn: Callable[[], Any]) -> None:
        """Set the health check function."""
        self._health_monitor.set_health_check_fn(fn)

    def set_provider(self, provider: str) -> None:
        """Set the provider name."""
        self._health_monitor.set_provider(provider)

    async def start(self) -> None:
        """Start availability management (health monitoring)."""
        await self._health_monitor.start_monitoring()

    async def stop(self) -> None:
        """Stop availability management."""
        await self._health_monitor.stop_monitoring()

    async def is_available(self) -> bool:
        """
        Check if LLM is currently available.

        Considers both circuit breaker state and health check status.
        """
        # Check circuit breaker
        if not await self._circuit_breaker.attempt_call():
            return False

        # Health status is informational, circuit breaker is authoritative
        return True

    async def record_success(self) -> None:
        """Record a successful LLM call."""
        await self._circuit_breaker.record_success()

    async def record_failure(self, exception: Exception) -> LLMError:
        """
        Record a failed LLM call.

        Args:
            exception: The exception that occurred

        Returns:
            Classified LLMError
        """
        error = self._classifier.classify(exception)
        await self._circuit_breaker.record_failure(error)
        return error

    def get_status(self) -> dict[str, Any]:
        """Get current availability status."""
        return {
            "available": self._circuit_breaker.is_available,
            "circuit_state": self._circuit_breaker.state.value,
            "health_status": {
                "healthy": self._health_monitor.is_healthy,
                "success_rate": self._health_monitor.success_rate,
                "last_check": str(self._health_monitor.last_check)
                if self._health_monitor.last_check
                else None,
            },
        }
