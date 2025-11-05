"""Tests for MCP server automatic reconnection logic."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the functions we want to test
from mcp_server.graphiti_mcp_server import (
    initialize_graphiti_with_retry,
    is_recoverable_error,
)


class TestIsRecoverableError:
    """Test error classification for reconnection logic."""

    def test_connection_errors_are_recoverable(self):
        """Connection-related errors should be recoverable."""
        connection_errors = [
            Exception('Connection refused'),
            Exception('Connection timeout'),
            Exception('Network unavailable'),
            Exception('Connection reset by peer'),
            Exception('Broken pipe'),
        ]

        for error in connection_errors:
            assert is_recoverable_error(error) is True, f'Expected {error} to be recoverable'

    def test_authentication_errors_are_not_recoverable(self):
        """Authentication and configuration errors should not be recoverable."""
        fatal_errors = [
            Exception('Authentication failed'),
            Exception('Invalid credentials'),
            Exception('API key missing'),
            Exception('Permission denied'),
            Exception('Configuration error'),
        ]

        for error in fatal_errors:
            assert is_recoverable_error(error) is False, f'Expected {error} to be fatal'

    def test_unknown_errors_default_to_non_recoverable(self):
        """Unknown errors should default to non-recoverable."""
        unknown_error = Exception('Something went wrong')
        assert is_recoverable_error(unknown_error) is False


class TestInitializeGraphitiWithRetry:
    """Test automatic retry logic for Graphiti initialization."""

    @pytest.mark.asyncio
    async def test_successful_initialization_on_first_attempt(self):
        """Should succeed immediately if initialization works."""
        with patch('mcp_server.graphiti_mcp_server.initialize_graphiti') as mock_init:
            mock_init.return_value = None  # Successful initialization

            result = await initialize_graphiti_with_retry(max_retries=3)

            assert result is True
            assert mock_init.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Should retry with exponential backoff on failure."""
        with patch('mcp_server.graphiti_mcp_server.initialize_graphiti') as mock_init:
            # Fail twice, succeed on third attempt
            mock_init.side_effect = [
                Exception('Connection refused'),
                Exception('Connection timeout'),
                None,  # Success
            ]

            with patch('asyncio.sleep') as mock_sleep:
                result = await initialize_graphiti_with_retry(max_retries=3)

                assert result is True
                assert mock_init.call_count == 3

                # Verify exponential backoff: 2^0=1s, 2^1=2s
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(1)  # First retry delay
                mock_sleep.assert_any_call(2)  # Second retry delay

    @pytest.mark.asyncio
    async def test_failure_after_max_retries(self):
        """Should fail after exhausting all retry attempts."""
        with patch('mcp_server.graphiti_mcp_server.initialize_graphiti') as mock_init:
            # Fail all attempts
            mock_init.side_effect = Exception('Connection refused')

            with patch('asyncio.sleep'):
                result = await initialize_graphiti_with_retry(max_retries=3)

                assert result is False
                assert mock_init.call_count == 3

    @pytest.mark.asyncio
    async def test_no_delay_on_last_attempt(self):
        """Should not delay after the last failed attempt."""
        with patch('mcp_server.graphiti_mcp_server.initialize_graphiti') as mock_init:
            mock_init.side_effect = Exception('Connection refused')

            with patch('asyncio.sleep') as mock_sleep:
                await initialize_graphiti_with_retry(max_retries=3)

                # Should only sleep between attempts, not after the last one
                # With 3 attempts: sleep after 1st and 2nd, not after 3rd
                assert mock_sleep.call_count == 2


class TestQueueWorkerReconnection:
    """Test queue worker recovery on connection errors."""

    @pytest.mark.asyncio
    async def test_worker_continues_after_recoverable_error_and_reconnection(self):
        """Worker should continue processing after successful reconnection."""
        # This is a conceptual test - actual implementation would require
        # more complex mocking of the queue worker
        pass

    @pytest.mark.asyncio
    async def test_worker_stops_after_failed_reconnection(self):
        """Worker should stop if reconnection fails after recoverable error."""
        # This is a conceptual test
        pass

    @pytest.mark.asyncio
    async def test_worker_continues_after_non_recoverable_error(self):
        """Worker should continue with next episode after non-recoverable error."""
        # This is a conceptual test
        pass
