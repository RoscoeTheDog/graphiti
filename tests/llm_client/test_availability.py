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

# Running tests: pytest -xvs tests/llm_client/test_availability.py

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from graphiti_core.llm_client.availability import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    HealthCheckConfig,
    HealthCheckResult,
    LLMAvailabilityConfig,
    LLMAvailabilityManager,
    LLMError,
    LLMErrorClassifier,
    LLMErrorType,
    LLMHealthMonitor,
)
from graphiti_core.llm_client.errors import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMUnavailableError,
)


class TestLLMErrorType:
    """Tests for the LLMErrorType enum."""

    def test_error_types_exist(self):
        """Test that all expected error types exist."""
        assert LLMErrorType.PERMANENT.value == 'permanent'
        assert LLMErrorType.TRANSIENT.value == 'transient'
        assert LLMErrorType.UNKNOWN.value == 'unknown'


class TestLLMError:
    """Tests for the LLMError dataclass."""

    def test_create_llm_error(self):
        """Test creating an LLMError instance."""
        original = ValueError('test error')
        error = LLMError(
            error_type=LLMErrorType.TRANSIENT,
            original_exception=original,
            message='Test error message',
            status_code=429,
            retryable=True,
        )

        assert error.error_type == LLMErrorType.TRANSIENT
        assert error.original_exception == original
        assert error.message == 'Test error message'
        assert error.status_code == 429
        assert error.retryable is True


class TestLLMErrorClassifier:
    """Tests for the LLMErrorClassifier class (AC-17.5, AC-17.6, AC-17.7)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = LLMErrorClassifier()

    def test_classify_authentication_error_401(self):
        """Test classifying 401 authentication errors as PERMANENT (AC-17.5)."""
        response = MagicMock()
        response.status_code = 401
        error = httpx.HTTPStatusError('Unauthorized', request=MagicMock(), response=response)

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.PERMANENT
        assert result.status_code == 401
        assert result.retryable is False

    def test_classify_authentication_error_403(self):
        """Test classifying 403 forbidden errors as PERMANENT (AC-17.5)."""
        response = MagicMock()
        response.status_code = 403
        error = httpx.HTTPStatusError('Forbidden', request=MagicMock(), response=response)

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.PERMANENT
        assert result.status_code == 403
        assert result.retryable is False

    def test_classify_rate_limit_error_429(self):
        """Test classifying 429 rate limit errors as TRANSIENT (AC-17.6)."""
        response = MagicMock()
        response.status_code = 429
        error = httpx.HTTPStatusError('Rate Limited', request=MagicMock(), response=response)

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.TRANSIENT
        assert result.status_code == 429
        assert result.retryable is True

    def test_classify_server_error_500(self):
        """Test classifying 500 server errors as TRANSIENT (AC-17.6)."""
        response = MagicMock()
        response.status_code = 500
        error = httpx.HTTPStatusError('Server Error', request=MagicMock(), response=response)

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.TRANSIENT
        assert result.status_code == 500
        assert result.retryable is True

    def test_classify_server_error_503(self):
        """Test classifying 503 service unavailable errors as TRANSIENT (AC-17.6)."""
        response = MagicMock()
        response.status_code = 503
        error = httpx.HTTPStatusError('Service Unavailable', request=MagicMock(), response=response)

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.TRANSIENT
        assert result.status_code == 503
        assert result.retryable is True

    def test_classify_connection_error(self):
        """Test classifying connection errors as TRANSIENT (AC-17.6)."""
        error = ConnectionError('Connection refused')

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.TRANSIENT
        assert result.retryable is True

    def test_classify_timeout_error(self):
        """Test classifying timeout errors as TRANSIENT (AC-17.6)."""
        error = TimeoutError('Request timed out')

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.TRANSIENT
        assert result.retryable is True

    def test_classify_invalid_api_key_message(self):
        """Test classifying errors with 'invalid api key' message as PERMANENT (AC-17.7)."""
        error = ValueError('Invalid API key provided')

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.PERMANENT
        assert result.retryable is False

    def test_classify_authentication_failed_message(self):
        """Test classifying errors with 'authentication failed' message as PERMANENT (AC-17.7)."""
        error = ValueError('Authentication failed: bad credentials')

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.PERMANENT
        assert result.retryable is False

    def test_classify_unknown_error(self):
        """Test classifying unknown errors as UNKNOWN."""
        error = ValueError('Some random error')

        result = self.classifier.classify(error)

        assert result.error_type == LLMErrorType.UNKNOWN
        assert result.retryable is True  # Default to retryable for safety


class TestCircuitBreakerConfig:
    """Tests for the CircuitBreakerConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.enabled is True
        assert config.failure_threshold == 5
        assert config.recovery_timeout_seconds == 300.0
        assert config.half_open_max_calls == 3

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            enabled=False,
            failure_threshold=10,
            recovery_timeout_seconds=60.0,
            half_open_max_calls=5,
        )

        assert config.enabled is False
        assert config.failure_threshold == 10
        assert config.recovery_timeout_seconds == 60.0
        assert config.half_open_max_calls == 5


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class (AC-17.8-17.11)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=1,
            half_open_max_calls=2,
        )
        self.circuit_breaker = CircuitBreaker(self.config)

    def test_initial_state_is_closed(self):
        """Test that initial state is CLOSED (AC-17.8)."""
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.is_available is True

    @pytest.mark.asyncio
    async def test_stays_closed_under_threshold(self):
        """Test circuit stays CLOSED when failures are under threshold (AC-17.8)."""
        for _ in range(self.config.failure_threshold - 1):
            await self.circuit_breaker.record_failure()

        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.is_available is True

    @pytest.mark.asyncio
    async def test_opens_on_threshold_reached(self):
        """Test circuit OPENS when failure threshold is reached (AC-17.9)."""
        for _ in range(self.config.failure_threshold):
            await self.circuit_breaker.record_failure()

        assert self.circuit_breaker.state == CircuitState.OPEN
        assert self.circuit_breaker.is_available is False

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test that success resets failure count (AC-17.8)."""
        await self.circuit_breaker.record_failure()
        await self.circuit_breaker.record_failure()
        await self.circuit_breaker.record_success()

        assert self.circuit_breaker._failure_count == 0
        assert self.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        """Test transition to HALF_OPEN after recovery timeout (AC-17.10)."""
        # Open the circuit
        for _ in range(self.config.failure_threshold):
            await self.circuit_breaker.record_failure()

        assert self.circuit_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        import time

        time.sleep(self.config.recovery_timeout_seconds + 0.1)

        # attempt_call triggers the transition (is_available just checks without transitioning)
        result = await self.circuit_breaker.attempt_call()

        assert result is True
        assert self.circuit_breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_from_half_open_on_success(self):
        """Test transition from HALF_OPEN to CLOSED on success (AC-17.11)."""
        # Set up HALF_OPEN state manually
        self.circuit_breaker._state = CircuitState.HALF_OPEN
        self.circuit_breaker._half_open_calls = self.config.half_open_max_calls - 1

        await self.circuit_breaker.record_success()

        assert self.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_from_half_open_on_failure(self):
        """Test transition from HALF_OPEN to OPEN on failure (AC-17.10)."""
        # Set up HALF_OPEN state manually
        self.circuit_breaker._state = CircuitState.HALF_OPEN

        await self.circuit_breaker.record_failure()

        assert self.circuit_breaker.state == CircuitState.OPEN

    def test_state_property(self):
        """Test state property returns correct state."""
        assert self.circuit_breaker.state == CircuitState.CLOSED

    def test_is_available_property(self):
        """Test is_available property returns correct value."""
        assert self.circuit_breaker.is_available is True


class TestHealthCheckConfig:
    """Tests for the HealthCheckConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HealthCheckConfig()

        assert config.enabled is True
        assert config.interval_seconds == 60.0
        assert config.timeout_seconds == 10.0
        assert config.on_startup is True
        assert config.history_size == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HealthCheckConfig(
            enabled=False,
            interval_seconds=120.0,
            timeout_seconds=20.0,
            on_startup=False,
            history_size=50,
        )

        assert config.enabled is False
        assert config.interval_seconds == 120.0
        assert config.timeout_seconds == 20.0
        assert config.on_startup is False
        assert config.history_size == 50


class TestLLMHealthMonitor:
    """Tests for the LLMHealthMonitor class (AC-17.1, AC-17.3, AC-17.4)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = HealthCheckConfig(interval_seconds=1.0, timeout_seconds=5.0, history_size=10)
        self.monitor = LLMHealthMonitor(config=self.config)

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test successful health check (AC-17.3)."""
        health_check_fn = AsyncMock(return_value=True)
        self.monitor.set_health_check_fn(health_check_fn)

        result = await self.monitor.check_health()

        assert result.healthy is True
        assert result.latency_ms is not None

    @pytest.mark.asyncio
    async def test_check_health_exception(self):
        """Test health check with exception (AC-17.3)."""
        health_check_fn = AsyncMock(side_effect=Exception('Health check failed'))
        self.monitor.set_health_check_fn(health_check_fn)

        result = await self.monitor.check_health()

        assert result.healthy is False
        assert result.error is not None
        # result.error is an LLMError object, check its message attribute
        assert 'Health check failed' in result.error.message

    @pytest.mark.asyncio
    async def test_check_health_no_function_set(self):
        """Test health check when no function is set - assumes healthy."""
        result = await self.monitor.check_health()

        # When no health check function is set, it assumes healthy
        assert result.healthy is True

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self):
        """Test success rate calculation (AC-17.4)."""
        health_check_fn = AsyncMock(return_value=True)
        self.monitor.set_health_check_fn(health_check_fn)

        # Run multiple health checks
        await self.monitor.check_health()
        await self.monitor.check_health()

        health_check_fn.side_effect = Exception('Failed')
        await self.monitor.check_health()

        # 2 successes, 1 failure = 66.67% success rate
        success_rate = self.monitor.success_rate
        assert 0.6 <= success_rate <= 0.7

    def test_last_check_none_initially(self):
        """Test that last_check returns None initially."""
        assert self.monitor.last_check is None

    @pytest.mark.asyncio
    async def test_last_check_after_check(self):
        """Test that last_check returns the last result after a check."""
        health_check_fn = AsyncMock(return_value=True)
        self.monitor.set_health_check_fn(health_check_fn)

        await self.monitor.check_health()

        result = self.monitor.last_check
        assert result is not None
        assert result.healthy is True


class TestLLMAvailabilityConfig:
    """Tests for the LLMAvailabilityConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LLMAvailabilityConfig()

        assert config.health_check is not None
        assert config.circuit_breaker is not None

    def test_custom_values(self):
        """Test custom configuration values."""
        health_config = HealthCheckConfig(interval_seconds=30)
        circuit_config = CircuitBreakerConfig(failure_threshold=10)

        config = LLMAvailabilityConfig(
            health_check=health_config,
            circuit_breaker=circuit_config,
        )

        assert config.health_check.interval_seconds == 30
        assert config.circuit_breaker.failure_threshold == 10


class TestLLMAvailabilityManager:
    """Tests for the LLMAvailabilityManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = LLMAvailabilityManager()

    @pytest.mark.asyncio
    async def test_is_available_initially_true(self):
        """Test that is_available is True initially."""
        assert await self.manager.is_available() is True

    @pytest.mark.asyncio
    async def test_record_success(self):
        """Test recording a successful operation."""
        await self.manager.record_success()
        assert self.manager.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_record_failure(self):
        """Test recording a failed operation."""
        await self.manager.record_failure(ValueError('test error'))
        # Should still be closed after one failure
        assert self.manager.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_check_health(self):
        """Test health check through manager's health monitor."""
        health_check_fn = AsyncMock(return_value=True)
        self.manager.set_health_check_fn(health_check_fn)

        # Manager doesn't have check_health directly, use health_monitor
        result = await self.manager.health_monitor.check_health()

        assert result.healthy is True

    def test_get_status(self):
        """Test get_status returns comprehensive status."""
        status = self.manager.get_status()

        assert 'available' in status
        assert 'circuit_state' in status
        assert 'health_status' in status
        assert status['available'] is True
        assert status['circuit_state'] == 'closed'

    def test_set_provider(self):
        """Test setting the provider."""
        # set_provider sets it on the health monitor
        self.manager.set_provider('anthropic')
        # Verify health monitor has the provider
        assert self.manager.health_monitor._provider == 'anthropic'


class TestNewErrorTypes:
    """Tests for the new error types (AC-17.5)."""

    def test_llm_unavailable_error_default(self):
        """Test LLMUnavailableError with default values."""
        error = LLMUnavailableError()
        assert 'unavailable' in error.message.lower()
        assert error.retryable is True

    def test_llm_unavailable_error_custom(self):
        """Test LLMUnavailableError with custom values."""
        error = LLMUnavailableError(message='Custom message', retryable=False)
        assert error.message == 'Custom message'
        assert error.retryable is False

    def test_llm_authentication_error(self):
        """Test LLMAuthenticationError."""
        error = LLMAuthenticationError()
        assert 'authentication' in error.message.lower()

    def test_llm_authentication_error_custom(self):
        """Test LLMAuthenticationError with custom message."""
        error = LLMAuthenticationError(message='Invalid API key')
        assert error.message == 'Invalid API key'

    def test_llm_rate_limit_error_default(self):
        """Test LLMRateLimitError with default values."""
        error = LLMRateLimitError()
        assert 'rate limit' in error.message.lower()
        assert error.retry_after is None

    def test_llm_rate_limit_error_with_retry_after(self):
        """Test LLMRateLimitError with retry_after."""
        error = LLMRateLimitError(retry_after=30.0)
        assert error.retry_after == 30.0


if __name__ == '__main__':
    pytest.main(['-v', 'test_availability.py'])
