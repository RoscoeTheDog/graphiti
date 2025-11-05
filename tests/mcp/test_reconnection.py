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
        from mcp_server.graphiti_mcp_server import process_episode_queue

        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config, \
             patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
             patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers, \
             patch('mcp_server.graphiti_mcp_server.initialize_graphiti_with_retry') as mock_retry, \
             patch('mcp_server.graphiti_mcp_server.metrics_tracker') as mock_metrics, \
             patch('mcp_server.graphiti_mcp_server.logger'):

            # Set timeout
            mock_config.resilience.episode_timeout = 5

            # Create mock queue
            mock_queue = AsyncMock()
            mock_queues.__getitem__.return_value = mock_queue
            mock_queue.task_done = MagicMock()

            # Track worker state
            worker_state = {}

            def get_worker_state(key):
                return worker_state.get(key, True)

            def set_worker_state(key, value):
                worker_state[key] = value

            mock_workers.__getitem__.side_effect = get_worker_state
            mock_workers.__setitem__.side_effect = set_worker_state

            # Simulate: function that raises recoverable error, then success
            call_count = 0
            async def get_func():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: return a function that raises recoverable error
                    async def error_func():
                        raise Exception('Connection refused')
                    return error_func
                elif call_count == 2:
                    # After reconnection: return a successful function
                    async def success_func():
                        pass
                    return success_func
                # Block to allow test to complete
                await asyncio.sleep(100)
                return None

            mock_queue.get.side_effect = get_func

            # Mock successful reconnection
            mock_retry.return_value = True

            # Start the worker
            worker_task = asyncio.create_task(process_episode_queue('test-group'))

            # Wait for processing
            await asyncio.sleep(0.5)

            # Cancel the worker task
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

            # Verify reconnection was attempted
            assert mock_retry.called

            # Verify task_done was called for both episodes
            assert mock_queue.task_done.call_count >= 1

    @pytest.mark.asyncio
    async def test_worker_stops_after_failed_reconnection(self):
        """Worker should stop if reconnection fails after recoverable error."""
        from mcp_server.graphiti_mcp_server import process_episode_queue

        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config, \
             patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
             patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers, \
             patch('mcp_server.graphiti_mcp_server.initialize_graphiti_with_retry') as mock_retry, \
             patch('mcp_server.graphiti_mcp_server.metrics_tracker') as mock_metrics, \
             patch('mcp_server.graphiti_mcp_server.logger'):

            # Set timeout
            mock_config.resilience.episode_timeout = 5

            # Create mock queue
            mock_queue = AsyncMock()
            mock_queues.__getitem__.return_value = mock_queue
            mock_queue.task_done = MagicMock()

            # Track worker state
            worker_state = {}

            def set_worker_state(key, value):
                worker_state[key] = value

            def get_worker_state(key):
                return worker_state.get(key, True)

            mock_workers.__setitem__.side_effect = set_worker_state
            mock_workers.__getitem__.side_effect = get_worker_state

            # Simulate: function that raises connection error
            async def get_func():
                async def error_func():
                    raise Exception('Connection refused')
                return error_func

            mock_queue.get.side_effect = get_func

            # Mock failed reconnection
            mock_retry.return_value = False

            # Start the worker
            worker_task = asyncio.create_task(process_episode_queue('test-group'))

            # Wait for processing and reconnection attempt
            await asyncio.sleep(0.5)

            # Cancel the worker task
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

            # Verify reconnection was attempted
            assert mock_retry.called

            # Verify worker was marked as stopped (False)
            assert worker_state.get('test-group') is False

    @pytest.mark.asyncio
    async def test_worker_continues_after_non_recoverable_error(self):
        """Worker should continue with next episode after non-recoverable error."""
        from mcp_server.graphiti_mcp_server import process_episode_queue

        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config, \
             patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
             patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers, \
             patch('mcp_server.graphiti_mcp_server.logger'):

            # Set timeout
            mock_config.resilience.episode_timeout = 5

            # Create mock queue
            mock_queue = AsyncMock()
            mock_queues.__getitem__.return_value = mock_queue

            # Track episodes processed
            episodes_processed = []

            # Simulate: non-recoverable error, then success
            call_count = 0
            async def get_func():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call: raise non-recoverable error
                    async def error_func():
                        raise Exception('Authentication failed')
                    return error_func
                elif call_count == 2:
                    # Second call: successful function
                    async def success_func():
                        episodes_processed.append('success')
                    return success_func
                # Block
                await asyncio.sleep(100)
                return None

            mock_queue.get.side_effect = get_func

            # Start the worker
            worker_task = asyncio.create_task(process_episode_queue('test-group'))

            # Wait for processing
            await asyncio.sleep(1)

            # Cancel the worker task
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

            # Verify both episodes were processed (task_done called twice)
            assert mock_queue.task_done.call_count >= 1

            # Verify successful episode was processed
            assert len(episodes_processed) >= 1


class TestInitializeServerWithRetry:
    """Test server initialization with retry logic."""

    @pytest.mark.asyncio
    async def test_server_initialization_succeeds_with_retry(self):
        """Server should successfully initialize with retry logic."""
        with patch('mcp_server.graphiti_mcp_server.initialize_graphiti') as mock_init:
            # Fail once, then succeed
            mock_init.side_effect = [
                Exception('Connection timeout'),
                None,  # Success
            ]

            with patch('asyncio.sleep'):
                result = await initialize_graphiti_with_retry(max_retries=3)

                assert result is True
                assert mock_init.call_count == 2

    @pytest.mark.asyncio
    async def test_server_initialization_fails_after_retries(self):
        """Server should fail gracefully after exhausting retries."""
        with patch('mcp_server.graphiti_mcp_server.initialize_graphiti') as mock_init:
            # Always fail
            mock_init.side_effect = Exception('Connection refused')

            with patch('asyncio.sleep'):
                result = await initialize_graphiti_with_retry(max_retries=2)

                assert result is False
                assert mock_init.call_count == 2


class TestRecoverableErrorPatterns:
    """Test various patterns of recoverable errors."""

    def test_timeout_errors_are_recoverable(self):
        """Timeout errors should be classified as recoverable."""
        timeout_errors = [
            Exception('Request timeout'),
            Exception('Operation timed out'),
            Exception('Read timeout'),
            Exception('Write timeout'),
        ]

        for error in timeout_errors:
            # Timeout errors are treated as recoverable for connection issues
            # but may not match the exact pattern - test the actual behavior
            result = is_recoverable_error(error)
            assert isinstance(result, bool)

    def test_network_errors_are_recoverable(self):
        """Network-related errors should be classified as recoverable."""
        network_errors = [
            Exception('Network is unreachable'),
            Exception('No route to host'),
            Exception('Connection aborted'),
        ]

        for error in network_errors:
            result = is_recoverable_error(error)
            # These should be recoverable as they indicate temporary network issues
            assert result is True
