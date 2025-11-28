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

"""
MCP Tool Response Types (Story 18: MCP Tools Error Handling)

Defines structured response types for MCP tools with explicit status indicators,
actionable error messages, and degradation mode information.

Response Types:
- SuccessResponse: Normal success with full processing
- DegradedResponse: Success with reduced functionality (e.g., LLM unavailable, stored raw)
- QueuedResponse: Operation queued for later processing
- ErrorResponse: Operation failed with actionable error details
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal


class ResponseStatus(Enum):
    """Response status categories."""

    SUCCESS = "success"  # Full success with complete processing
    DEGRADED = "degraded"  # Partial success with reduced functionality
    QUEUED = "queued"  # Operation queued for later processing
    ERROR = "error"  # Operation failed


class DegradationReason(Enum):
    """Reasons for degraded operation."""

    LLM_UNAVAILABLE = "llm_unavailable"  # LLM circuit breaker open or health check failed
    LLM_RATE_LIMITED = "llm_rate_limited"  # LLM rate limit exceeded
    LLM_TIMEOUT = "llm_timeout"  # LLM request timed out
    STORED_RAW = "stored_raw"  # Data stored without LLM processing
    PARTIAL_PROCESSING = "partial_processing"  # Some processing steps skipped


class ErrorCategory(Enum):
    """Error categories for actionable error messages."""

    LLM_UNAVAILABLE = "llm_unavailable"  # LLM service not available
    LLM_AUTHENTICATION = "llm_authentication"  # Invalid API key or credentials
    LLM_RATE_LIMIT = "llm_rate_limit"  # Rate limit exceeded
    DATABASE_CONNECTION = "database_connection"  # Cannot connect to database
    DATABASE_QUERY = "database_query"  # Database query failed
    VALIDATION = "validation"  # Input validation failed
    TIMEOUT = "timeout"  # Operation timed out
    INTERNAL = "internal"  # Unexpected internal error
    CONFIGURATION = "configuration"  # Configuration error


@dataclass
class ActionableError:
    """
    Actionable error with recovery suggestions (AC-18.4).

    Provides structured error information with explicit recovery paths
    to help users and agents understand how to resolve the issue.
    """

    category: ErrorCategory
    message: str
    recoverable: bool = True
    suggestion: str | None = None
    retry_after_seconds: float | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "category": self.category.value,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.suggestion:
            result["suggestion"] = self.suggestion
        if self.retry_after_seconds is not None:
            result["retry_after_seconds"] = self.retry_after_seconds
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class SuccessResponse:
    """
    Full success response (AC-18.1).

    Indicates the operation completed successfully with full processing.
    """

    status: Literal[ResponseStatus.SUCCESS] = ResponseStatus.SUCCESS
    message: str = "Operation completed successfully"
    data: dict[str, Any] | None = None
    episode_id: str | None = None
    processing_time_ms: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.data:
            result["data"] = self.data
        if self.episode_id:
            result["episode_id"] = self.episode_id
        if self.processing_time_ms is not None:
            result["processing_time_ms"] = self.processing_time_ms
        return result

    def to_string(self) -> str:
        """Convert to user-friendly string."""
        return self.message


@dataclass
class DegradedResponse:
    """
    Degraded success response (AC-18.2).

    Indicates the operation completed but with reduced functionality.
    Common scenarios:
    - LLM unavailable, data stored raw
    - Rate limited, partial processing completed
    - Some entity extraction skipped
    """

    status: Literal[ResponseStatus.DEGRADED] = ResponseStatus.DEGRADED
    message: str = "Operation completed with degraded functionality"
    reason: DegradationReason = DegradationReason.LLM_UNAVAILABLE
    data: dict[str, Any] | None = None
    limitations: list[str] | None = None
    episode_id: str | None = None
    processing_time_ms: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": self.status.value,
            "message": self.message,
            "reason": self.reason.value,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.data:
            result["data"] = self.data
        if self.limitations:
            result["limitations"] = self.limitations
        if self.episode_id:
            result["episode_id"] = self.episode_id
        if self.processing_time_ms is not None:
            result["processing_time_ms"] = self.processing_time_ms
        return result

    def to_string(self) -> str:
        """Convert to user-friendly string."""
        limitations_str = ""
        if self.limitations:
            limitations_str = f"\nLimitations: {', '.join(self.limitations)}"
        return f"{self.message}\nReason: {self.reason.value}{limitations_str}"


@dataclass
class QueuedResponse:
    """
    Queued response (AC-18.3).

    Indicates the operation was queued for later processing.
    Returned when:
    - LLM unavailable and QUEUE_RETRY mode is configured
    - wait_for_completion=False and async processing started
    """

    status: Literal[ResponseStatus.QUEUED] = ResponseStatus.QUEUED
    message: str = "Operation queued for processing"
    queue_id: str | None = None
    episode_id: str | None = None
    estimated_wait_seconds: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.queue_id:
            result["queue_id"] = self.queue_id
        if self.episode_id:
            result["episode_id"] = self.episode_id
        if self.estimated_wait_seconds is not None:
            result["estimated_wait_seconds"] = self.estimated_wait_seconds
        return result

    def to_string(self) -> str:
        """Convert to user-friendly string."""
        wait_str = ""
        if self.estimated_wait_seconds:
            wait_str = f" (estimated wait: {self.estimated_wait_seconds}s)"
        return f"{self.message}{wait_str}"


@dataclass
class ErrorResponse:
    """
    Error response (AC-18.4).

    Indicates the operation failed with actionable error information.
    """

    status: Literal[ResponseStatus.ERROR] = ResponseStatus.ERROR
    error: ActionableError | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.error:
            result["error"] = self.error.to_dict()
        return result

    def to_string(self) -> str:
        """Convert to user-friendly string."""
        if not self.error:
            return "Unknown error"

        result = f"Error: {self.error.message}"
        if self.error.suggestion:
            result += f"\nSuggestion: {self.error.suggestion}"
        if self.error.retry_after_seconds:
            result += f"\nRetry after: {self.error.retry_after_seconds}s"
        return result


# Type alias for any MCP response
MCPResponse = SuccessResponse | DegradedResponse | QueuedResponse | ErrorResponse


def create_success(
    message: str = "Operation completed successfully",
    episode_id: str | None = None,
    processing_time_ms: float | None = None,
    **data,
) -> SuccessResponse:
    """Create a success response with optional data."""
    return SuccessResponse(
        message=message,
        data=data if data else None,
        episode_id=episode_id,
        processing_time_ms=processing_time_ms,
    )


def create_degraded(
    reason: DegradationReason,
    message: str | None = None,
    limitations: list[str] | None = None,
    episode_id: str | None = None,
    processing_time_ms: float | None = None,
    **data,
) -> DegradedResponse:
    """Create a degraded response."""
    if message is None:
        message = f"Operation completed with degraded functionality: {reason.value}"
    return DegradedResponse(
        message=message,
        reason=reason,
        data=data if data else None,
        limitations=limitations,
        episode_id=episode_id,
        processing_time_ms=processing_time_ms,
    )


def create_queued(
    episode_id: str | None = None,
    queue_id: str | None = None,
    estimated_wait_seconds: float | None = None,
    message: str = "Operation queued for processing",
) -> QueuedResponse:
    """Create a queued response."""
    return QueuedResponse(
        message=message,
        episode_id=episode_id,
        queue_id=queue_id,
        estimated_wait_seconds=estimated_wait_seconds,
    )


def create_error(
    category: ErrorCategory,
    message: str,
    recoverable: bool = True,
    suggestion: str | None = None,
    retry_after_seconds: float | None = None,
    **details,
) -> ErrorResponse:
    """Create an error response with actionable information."""
    return ErrorResponse(
        error=ActionableError(
            category=category,
            message=message,
            recoverable=recoverable,
            suggestion=suggestion,
            retry_after_seconds=retry_after_seconds,
            details=details if details else None,
        )
    )


# =============================================================================
# Pre-defined Error Responses (AC-18.4)
# =============================================================================


def create_llm_unavailable_error(
    circuit_state: str | None = None,
    retry_after_seconds: float | None = None,
) -> ErrorResponse:
    """Create LLM unavailable error with recovery suggestions."""
    suggestion = "The LLM service is temporarily unavailable. "
    if circuit_state == "open":
        suggestion += (
            "Circuit breaker is open due to repeated failures. "
            "Wait for recovery timeout or check health_check tool for status."
        )
    else:
        suggestion += "Wait for the service to recover and retry."

    return create_error(
        category=ErrorCategory.LLM_UNAVAILABLE,
        message="LLM service is unavailable",
        recoverable=True,
        suggestion=suggestion,
        retry_after_seconds=retry_after_seconds,
        circuit_state=circuit_state,
    )


def create_llm_auth_error(provider: str | None = None) -> ErrorResponse:
    """Create LLM authentication error with recovery suggestions."""
    provider_str = f" ({provider})" if provider else ""
    return create_error(
        category=ErrorCategory.LLM_AUTHENTICATION,
        message=f"LLM authentication failed{provider_str}",
        recoverable=False,
        suggestion=(
            "Check your API key is valid and has not expired. "
            "Verify the API key environment variable is set correctly. "
            "For OpenAI: OPENAI_API_KEY, for Anthropic: ANTHROPIC_API_KEY."
        ),
        provider=provider,
    )


def create_llm_rate_limit_error(retry_after_seconds: float | None = None) -> ErrorResponse:
    """Create LLM rate limit error with recovery suggestions."""
    suggestion = "LLM rate limit exceeded. "
    if retry_after_seconds:
        suggestion += f"Retry after {retry_after_seconds} seconds."
    else:
        suggestion += "Wait a moment and retry, or reduce request frequency."

    return create_error(
        category=ErrorCategory.LLM_RATE_LIMIT,
        message="LLM rate limit exceeded",
        recoverable=True,
        suggestion=suggestion,
        retry_after_seconds=retry_after_seconds,
    )


def create_database_error(message: str, recoverable: bool = True) -> ErrorResponse:
    """Create database error with recovery suggestions."""
    return create_error(
        category=ErrorCategory.DATABASE_CONNECTION,
        message=f"Database error: {message}",
        recoverable=recoverable,
        suggestion=(
            "Check database connection settings. "
            "Verify Neo4j is running and accessible. "
            "Use health_check tool to verify database connectivity."
        ),
    )


def create_validation_error(message: str, field: str | None = None) -> ErrorResponse:
    """Create validation error with details."""
    return create_error(
        category=ErrorCategory.VALIDATION,
        message=f"Validation error: {message}",
        recoverable=True,
        suggestion="Check input parameters and try again.",
        field=field,
    )


def create_timeout_error(
    operation: str,
    timeout_seconds: float,
    suggestion: str | None = None,
) -> ErrorResponse:
    """Create timeout error with recovery suggestions."""
    if suggestion is None:
        suggestion = (
            f"Operation '{operation}' timed out after {timeout_seconds}s. "
            "The operation may still complete in the background. "
            "Consider using wait_for_completion=false for long operations."
        )
    return create_error(
        category=ErrorCategory.TIMEOUT,
        message=f"Operation timed out after {timeout_seconds}s",
        recoverable=True,
        suggestion=suggestion,
        operation=operation,
        timeout_seconds=timeout_seconds,
    )


def format_response(response: MCPResponse) -> str:
    """
    Format an MCP response as a user-friendly string.

    This is the primary function for converting response objects
    to the string format expected by MCP tools.
    """
    return response.to_string()


def response_to_dict(response: MCPResponse) -> dict[str, Any]:
    """
    Convert an MCP response to a dictionary.

    Useful for JSON serialization or structured logging.
    """
    return response.to_dict()
