"""
Tests for MCP tool response types (Story 18: MCP Tools Error Handling).
"""

import pytest
from datetime import datetime, timezone

from mcp_server.responses import (
    # Response types
    SuccessResponse,
    DegradedResponse,
    QueuedResponse,
    ErrorResponse,
    MCPResponse,
    ResponseStatus,
    # Enums
    DegradationReason,
    ErrorCategory,
    # Helper classes
    ActionableError,
    # Factory functions
    create_success,
    create_degraded,
    create_queued,
    create_error,
    create_llm_unavailable_error,
    create_llm_auth_error,
    create_llm_rate_limit_error,
    create_network_error,
    create_quota_error,
    create_database_error,
    create_validation_error,
    create_timeout_error,
    # Utility functions
    format_response,
    response_to_dict,
)


class TestSuccessResponse:
    """Tests for SuccessResponse class."""

    def test_default_creation(self):
        """Test creating a success response with defaults."""
        response = SuccessResponse()
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "Operation completed successfully"
        assert response.data is None
        assert isinstance(response.timestamp, datetime)

    def test_custom_message(self):
        """Test success response with custom message."""
        response = SuccessResponse(message="Custom success message")
        assert response.message == "Custom success message"

    def test_with_data(self):
        """Test success response with data payload."""
        data = {"episode_id": "123", "nodes_created": 5}
        response = SuccessResponse(message="Episode added", data=data)
        assert response.data == data
        assert response.data["episode_id"] == "123"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        response = SuccessResponse(
            message="Test success",
            data={"key": "value"}
        )
        result = response.to_dict()
        assert result["status"] == "success"
        assert result["message"] == "Test success"
        assert result["data"] == {"key": "value"}
        assert "timestamp" in result

    def test_to_string(self):
        """Test string representation."""
        response = SuccessResponse(message="Episode 'Test' added successfully")
        assert response.to_string() == "Episode 'Test' added successfully"


class TestDegradedResponse:
    """Tests for DegradedResponse class."""

    def test_default_creation(self):
        """Test creating a degraded response with defaults."""
        response = DegradedResponse()
        assert response.status == ResponseStatus.DEGRADED
        assert response.reason == DegradationReason.LLM_UNAVAILABLE

    def test_with_reason(self):
        """Test degraded response with specific reason."""
        response = DegradedResponse(
            reason=DegradationReason.LLM_RATE_LIMITED,
            message="Rate limited"
        )
        assert response.reason == DegradationReason.LLM_RATE_LIMITED
        assert response.message == "Rate limited"

    def test_with_limitations(self):
        """Test degraded response with limitations list."""
        response = DegradedResponse(
            reason=DegradationReason.LLM_UNAVAILABLE,
            message="Stored with degraded functionality",
            limitations=[
                "Entity extraction skipped",
                "Relationship inference skipped"
            ]
        )
        assert len(response.limitations) == 2
        assert "Entity extraction skipped" in response.limitations

    def test_to_dict(self):
        """Test serialization to dictionary."""
        response = DegradedResponse(
            reason=DegradationReason.STORED_RAW,
            message="Stored raw",
            limitations=["No LLM processing"],
            data={"episode_id": "456"}
        )
        result = response.to_dict()
        assert result["status"] == "degraded"
        assert result["reason"] == "stored_raw"
        assert result["limitations"] == ["No LLM processing"]
        assert result["data"]["episode_id"] == "456"

    def test_to_string_with_limitations(self):
        """Test string representation with limitations."""
        response = DegradedResponse(
            message="Operation completed",
            reason=DegradationReason.LLM_UNAVAILABLE,
            limitations=["Entity extraction skipped"]
        )
        result = response.to_string()
        assert "Operation completed" in result
        assert "llm_unavailable" in result
        assert "Entity extraction skipped" in result


class TestQueuedResponse:
    """Tests for QueuedResponse class."""

    def test_default_creation(self):
        """Test creating a queued response with defaults."""
        response = QueuedResponse()
        assert response.status == ResponseStatus.QUEUED
        assert response.message == "Operation queued for processing"

    def test_with_queue_info(self):
        """Test queued response with queue details."""
        response = QueuedResponse(
            episode_id="ep-123",
            queue_id="queue-456",
            estimated_wait_seconds=30.0
        )
        assert response.episode_id == "ep-123"
        assert response.queue_id == "queue-456"
        assert response.estimated_wait_seconds == 30.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        response = QueuedResponse(
            episode_id="ep-789",
            estimated_wait_seconds=60.0
        )
        result = response.to_dict()
        assert result["status"] == "queued"
        assert result["episode_id"] == "ep-789"
        assert result["estimated_wait_seconds"] == 60.0

    def test_to_string_with_wait_time(self):
        """Test string representation with wait time."""
        response = QueuedResponse(
            message="Episode queued",
            estimated_wait_seconds=45.0
        )
        result = response.to_string()
        assert "Episode queued" in result
        assert "45.0s" in result


class TestErrorResponse:
    """Tests for ErrorResponse class."""

    def test_default_creation(self):
        """Test creating an error response with defaults."""
        response = ErrorResponse()
        assert response.status == ResponseStatus.ERROR
        assert response.error is None

    def test_with_actionable_error(self):
        """Test error response with actionable error details."""
        error = ActionableError(
            category=ErrorCategory.LLM_UNAVAILABLE,
            message="LLM service unavailable",
            recoverable=True,
            suggestion="Wait for circuit breaker recovery",
            retry_after_seconds=300.0
        )
        response = ErrorResponse(error=error)
        assert response.error.category == ErrorCategory.LLM_UNAVAILABLE
        assert response.error.recoverable is True
        assert response.error.retry_after_seconds == 300.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        error = ActionableError(
            category=ErrorCategory.DATABASE_CONNECTION,
            message="Cannot connect to Neo4j",
            recoverable=True,
            suggestion="Check Neo4j is running"
        )
        response = ErrorResponse(error=error)
        result = response.to_dict()
        assert result["status"] == "error"
        assert result["error"]["category"] == "database_connection"
        assert result["error"]["recoverable"] is True
        assert result["error"]["suggestion"] == "Check Neo4j is running"

    def test_to_string_with_suggestion(self):
        """Test string representation with suggestion."""
        error = ActionableError(
            category=ErrorCategory.LLM_AUTHENTICATION,
            message="Invalid API key",
            recoverable=False,
            suggestion="Check OPENAI_API_KEY environment variable"
        )
        response = ErrorResponse(error=error)
        result = response.to_string()
        assert "Invalid API key" in result
        assert "OPENAI_API_KEY" in result


class TestActionableError:
    """Tests for ActionableError class."""

    def test_basic_creation(self):
        """Test creating a basic actionable error."""
        error = ActionableError(
            category=ErrorCategory.VALIDATION,
            message="Invalid source type"
        )
        assert error.category == ErrorCategory.VALIDATION
        assert error.message == "Invalid source type"
        assert error.recoverable is True  # default
        assert error.suggestion is None

    def test_full_creation(self):
        """Test creating error with all fields."""
        error = ActionableError(
            category=ErrorCategory.LLM_RATE_LIMIT,
            message="Rate limit exceeded",
            recoverable=True,
            suggestion="Wait 60 seconds and retry",
            retry_after_seconds=60.0,
            details={"provider": "openai", "limit": 100}
        )
        assert error.retry_after_seconds == 60.0
        assert error.details["provider"] == "openai"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        error = ActionableError(
            category=ErrorCategory.TIMEOUT,
            message="Operation timed out",
            recoverable=True,
            suggestion="Retry with smaller batch"
        )
        result = error.to_dict()
        assert result["category"] == "timeout"
        assert result["message"] == "Operation timed out"
        assert result["recoverable"] is True
        assert result["suggestion"] == "Retry with smaller batch"


class TestFactoryFunctions:
    """Tests for response factory functions."""

    def test_create_success(self):
        """Test create_success factory function."""
        response = create_success("Episode added", episode_id="123", count=5)
        assert isinstance(response, SuccessResponse)
        assert response.message == "Episode added"
        assert response.episode_id == "123"  # Now a direct field, not in data
        assert response.data["count"] == 5

    def test_create_degraded(self):
        """Test create_degraded factory function."""
        response = create_degraded(
            reason=DegradationReason.LLM_UNAVAILABLE,
            limitations=["Entity extraction skipped"],
            episode_id="456"
        )
        assert isinstance(response, DegradedResponse)
        assert response.reason == DegradationReason.LLM_UNAVAILABLE
        assert response.limitations == ["Entity extraction skipped"]
        assert response.episode_id == "456"  # Now a direct field, not in data

    def test_create_queued(self):
        """Test create_queued factory function."""
        response = create_queued(
            episode_id="789",
            estimated_wait_seconds=120.0
        )
        assert isinstance(response, QueuedResponse)
        assert response.episode_id == "789"
        assert response.estimated_wait_seconds == 120.0

    def test_create_error(self):
        """Test create_error factory function."""
        response = create_error(
            category=ErrorCategory.CONFIGURATION,
            message="Invalid config",
            recoverable=False,
            suggestion="Check graphiti.config.json"
        )
        assert isinstance(response, ErrorResponse)
        assert response.error.category == ErrorCategory.CONFIGURATION
        assert response.error.message == "Invalid config"
        assert response.error.recoverable is False


class TestPreDefinedErrors:
    """Tests for pre-defined error factory functions."""

    def test_create_llm_unavailable_error(self):
        """Test LLM unavailable error factory."""
        response = create_llm_unavailable_error(
            circuit_state="open",
            retry_after_seconds=300.0
        )
        assert response.error.category == ErrorCategory.LLM_UNAVAILABLE
        assert "circuit breaker" in response.error.suggestion.lower()
        assert response.error.retry_after_seconds == 300.0

    def test_create_llm_auth_error(self):
        """Test LLM authentication error factory."""
        response = create_llm_auth_error(provider="openai")
        assert response.error.category == ErrorCategory.LLM_AUTHENTICATION
        assert response.error.recoverable is False
        assert "API key" in response.error.suggestion

    def test_create_llm_rate_limit_error(self):
        """Test LLM rate limit error factory."""
        response = create_llm_rate_limit_error(retry_after_seconds=60.0)
        assert response.error.category == ErrorCategory.LLM_RATE_LIMIT
        assert response.error.recoverable is True
        assert "60" in response.error.suggestion

    def test_create_database_error(self):
        """Test database error factory."""
        response = create_database_error("Connection refused")
        assert response.error.category == ErrorCategory.DATABASE_CONNECTION
        assert "Neo4j" in response.error.suggestion

    def test_create_validation_error(self):
        """Test validation error factory."""
        response = create_validation_error("Invalid source type", field="source")
        assert response.error.category == ErrorCategory.VALIDATION
        assert response.error.details["field"] == "source"

    def test_create_timeout_error(self):
        """Test timeout error factory."""
        response = create_timeout_error("add_episode", timeout_seconds=60.0)
        assert response.error.category == ErrorCategory.TIMEOUT
        assert response.error.details["operation"] == "add_episode"
        assert response.error.details["timeout_seconds"] == 60.0

    def test_create_network_error(self):
        """Test network error factory (AC-18.5)."""
        response = create_network_error(provider="openai")
        assert response.error.category == ErrorCategory.LLM_NETWORK
        assert response.error.recoverable is True
        assert "Cannot reach LLM provider" in response.error.message
        assert "openai" in response.error.message
        assert "network connection" in response.error.suggestion.lower()

    def test_create_network_error_with_retry(self):
        """Test network error with retry time."""
        response = create_network_error(retry_after_seconds=30.0)
        assert response.error.retry_after_seconds == 30.0
        assert "30" in response.error.suggestion

    def test_create_quota_error(self):
        """Test quota exceeded error factory (AC-18.5)."""
        response = create_quota_error(provider="openai")
        assert response.error.category == ErrorCategory.LLM_QUOTA_EXCEEDED
        assert response.error.recoverable is False
        assert "quota exceeded" in response.error.message.lower()
        assert "billing" in response.error.suggestion.lower()
        assert "platform.openai.com" in response.error.suggestion

    def test_create_quota_error_anthropic(self):
        """Test quota error with Anthropic provider."""
        response = create_quota_error(provider="anthropic")
        assert "console.anthropic.com" in response.error.suggestion

    def test_create_quota_error_custom_url(self):
        """Test quota error with custom billing URL."""
        response = create_quota_error(
            provider="custom",
            provider_url="https://custom.ai/billing"
        )
        assert "custom.ai/billing" in response.error.suggestion


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_format_response_success(self):
        """Test format_response with success response."""
        response = create_success("Episode added")
        result = format_response(response)
        assert isinstance(result, str)
        assert "Episode added" in result

    def test_format_response_degraded(self):
        """Test format_response with degraded response."""
        response = create_degraded(
            reason=DegradationReason.LLM_UNAVAILABLE,
            message="Stored raw",
            limitations=["No entity extraction"]
        )
        result = format_response(response)
        assert "Stored raw" in result
        assert "llm_unavailable" in result

    def test_format_response_error(self):
        """Test format_response with error response."""
        response = create_error(
            category=ErrorCategory.LLM_UNAVAILABLE,
            message="Service unavailable",
            suggestion="Retry later"
        )
        result = format_response(response)
        assert "Service unavailable" in result
        assert "Retry later" in result

    def test_response_to_dict_all_types(self):
        """Test response_to_dict with all response types."""
        # Success
        success = create_success("OK")
        assert response_to_dict(success)["status"] == "success"

        # Degraded
        degraded = create_degraded(DegradationReason.LLM_UNAVAILABLE)
        assert response_to_dict(degraded)["status"] == "degraded"

        # Queued
        queued = create_queued(episode_id="123")
        assert response_to_dict(queued)["status"] == "queued"

        # Error
        error = create_error(ErrorCategory.INTERNAL, "Test error")
        assert response_to_dict(error)["status"] == "error"


class TestEnums:
    """Tests for enum values."""

    def test_response_status_values(self):
        """Test ResponseStatus enum values."""
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.DEGRADED.value == "degraded"
        assert ResponseStatus.QUEUED.value == "queued"
        assert ResponseStatus.ERROR.value == "error"

    def test_degradation_reason_values(self):
        """Test DegradationReason enum values."""
        assert DegradationReason.LLM_UNAVAILABLE.value == "llm_unavailable"
        assert DegradationReason.LLM_RATE_LIMITED.value == "llm_rate_limited"
        assert DegradationReason.STORED_RAW.value == "stored_raw"

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.LLM_UNAVAILABLE.value == "llm_unavailable"
        assert ErrorCategory.LLM_AUTHENTICATION.value == "llm_authentication"
        assert ErrorCategory.LLM_NETWORK.value == "llm_network"
        assert ErrorCategory.LLM_QUOTA_EXCEEDED.value == "llm_quota_exceeded"
        assert ErrorCategory.DATABASE_CONNECTION.value == "database_connection"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.INTERNAL.value == "internal"


class TestResponseFieldsAC18_2:
    """Tests for AC-18.2 response fields (episode_id, processing_time_ms)."""

    def test_success_response_with_episode_id(self):
        """Test success response with episode_id field."""
        response = SuccessResponse(
            message="Episode added",
            episode_id="ep-123",
            processing_time_ms=150.5
        )
        assert response.episode_id == "ep-123"
        assert response.processing_time_ms == 150.5

    def test_success_response_to_dict_with_fields(self):
        """Test success response serialization includes new fields."""
        response = SuccessResponse(
            message="Episode added",
            episode_id="ep-123",
            processing_time_ms=150.5
        )
        result = response.to_dict()
        assert result["episode_id"] == "ep-123"
        assert result["processing_time_ms"] == 150.5

    def test_success_response_to_dict_excludes_none_fields(self):
        """Test success response serialization excludes None fields."""
        response = SuccessResponse(message="Test")
        result = response.to_dict()
        assert "episode_id" not in result
        assert "processing_time_ms" not in result

    def test_degraded_response_with_episode_id(self):
        """Test degraded response with episode_id field."""
        response = DegradedResponse(
            message="Stored raw",
            episode_id="ep-456",
            processing_time_ms=200.0
        )
        assert response.episode_id == "ep-456"
        assert response.processing_time_ms == 200.0

    def test_degraded_response_to_dict_with_fields(self):
        """Test degraded response serialization includes new fields."""
        response = DegradedResponse(
            message="Stored raw",
            episode_id="ep-456",
            processing_time_ms=200.0
        )
        result = response.to_dict()
        assert result["episode_id"] == "ep-456"
        assert result["processing_time_ms"] == 200.0

    def test_degraded_response_to_dict_excludes_none_fields(self):
        """Test degraded response serialization excludes None fields."""
        response = DegradedResponse(message="Test")
        result = response.to_dict()
        assert "episode_id" not in result
        assert "processing_time_ms" not in result

    def test_create_success_factory_with_new_fields(self):
        """Test create_success factory function with new fields."""
        response = create_success(
            "Episode added",
            episode_id="ep-789",
            processing_time_ms=100.0,
            extra_data="value"
        )
        assert response.episode_id == "ep-789"
        assert response.processing_time_ms == 100.0
        assert response.data["extra_data"] == "value"

    def test_create_degraded_factory_with_new_fields(self):
        """Test create_degraded factory function with new fields."""
        response = create_degraded(
            reason=DegradationReason.LLM_UNAVAILABLE,
            episode_id="ep-101",
            processing_time_ms=250.0
        )
        assert response.episode_id == "ep-101"
        assert response.processing_time_ms == 250.0

    def test_processing_time_ms_zero_is_serialized(self):
        """Test that processing_time_ms=0 is serialized (not treated as None)."""
        response = SuccessResponse(
            message="Fast operation",
            processing_time_ms=0.0
        )
        result = response.to_dict()
        assert result["processing_time_ms"] == 0.0

    def test_all_response_fields_in_success(self):
        """Test all fields together in success response."""
        response = SuccessResponse(
            message="Complete success",
            data={"key": "value"},
            episode_id="ep-full",
            processing_time_ms=500.0
        )
        result = response.to_dict()
        assert result["status"] == "success"
        assert result["message"] == "Complete success"
        assert result["data"] == {"key": "value"}
        assert result["episode_id"] == "ep-full"
        assert result["processing_time_ms"] == 500.0
        assert "timestamp" in result

    def test_all_response_fields_in_degraded(self):
        """Test all fields together in degraded response."""
        response = DegradedResponse(
            message="Degraded operation",
            reason=DegradationReason.STORED_RAW,
            data={"key": "value"},
            limitations=["No LLM processing"],
            episode_id="ep-degraded",
            processing_time_ms=300.0
        )
        result = response.to_dict()
        assert result["status"] == "degraded"
        assert result["message"] == "Degraded operation"
        assert result["reason"] == "stored_raw"
        assert result["data"] == {"key": "value"}
        assert result["limitations"] == ["No LLM processing"]
        assert result["episode_id"] == "ep-degraded"
        assert result["processing_time_ms"] == 300.0
        assert "timestamp" in result
