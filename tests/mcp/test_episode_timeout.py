"""Tests for episode processing timeout functionality."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the function we want to test
from mcp_server.graphiti_mcp_server import process_episode_queue


class TestEpisodeTimeout:
    """Test episode processing timeout behavior."""

    @pytest.mark.asyncio
    async def test_episode_processing_completes_within_timeout(self):
        """Episode processing should complete successfully if within timeout."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config:
            # Set timeout to 5 seconds
            mock_config.resilience.episode_timeout = 5

            # Create mock queue and worker tracking
            with patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
                 patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

                # Create a mock queue
                mock_queue = AsyncMock()
                mock_queues.__getitem__.return_value = mock_queue

                # Create a fast processing function (completes in 1 second)
                async def fast_process():
                    await asyncio.sleep(1)

                # Set up queue to return the fast function once, then block
                call_count = 0
                async def get_func():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return fast_process
                    # Block indefinitely to allow test to complete
                    await asyncio.sleep(100)
                    return None

                mock_queue.get.side_effect = get_func

                # Start the worker
                worker_task = asyncio.create_task(process_episode_queue('test-group'))

                # Wait for processing to complete
                await asyncio.sleep(2)

                # Cancel the worker task
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

                # Verify task_done was called (successful completion)
                assert mock_queue.task_done.call_count == 1

    @pytest.mark.asyncio
    async def test_episode_processing_times_out(self):
        """Episode processing should timeout and continue with next episode."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config, \
             patch('mcp_server.graphiti_mcp_server.logger') as mock_logger:

            # Set a short timeout
            mock_config.resilience.episode_timeout = 1

            # Create mock queue and worker tracking
            with patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
                 patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

                # Create a mock queue
                mock_queue = AsyncMock()
                mock_queues.__getitem__.return_value = mock_queue

                # Create a slow processing function (takes 5 seconds)
                async def slow_process():
                    await asyncio.sleep(5)

                # Set up queue to return the slow function once, then block
                call_count = 0
                async def get_func():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return slow_process
                    # Block to allow test to verify timeout
                    await asyncio.sleep(100)
                    return None

                mock_queue.get.side_effect = get_func

                # Start the worker
                worker_task = asyncio.create_task(process_episode_queue('test-group'))

                # Wait for timeout to occur
                await asyncio.sleep(2)

                # Cancel the worker task
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

                # Verify timeout was logged
                timeout_logged = any(
                    'timed out' in str(call).lower()
                    for call in mock_logger.error.call_args_list
                )
                assert timeout_logged, "Expected timeout error to be logged"

                # Verify task_done was called (episode marked as done despite timeout)
                assert mock_queue.task_done.call_count == 1

    @pytest.mark.asyncio
    async def test_worker_continues_after_timeout(self):
        """Worker should continue processing next episodes after a timeout."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config:
            # Set a short timeout
            mock_config.resilience.episode_timeout = 1

            # Create mock queue and worker tracking
            with patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
                 patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

                # Create a mock queue
                mock_queue = AsyncMock()
                mock_queues.__getitem__.return_value = mock_queue

                # Create one slow and one fast function
                async def slow_process():
                    await asyncio.sleep(5)

                async def fast_process():
                    await asyncio.sleep(0.1)

                # Set up queue to return slow, then fast, then block
                call_count = 0
                async def get_func():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return slow_process
                    elif call_count == 2:
                        return fast_process
                    # Block
                    await asyncio.sleep(100)
                    return None

                mock_queue.get.side_effect = get_func

                # Start the worker
                worker_task = asyncio.create_task(process_episode_queue('test-group'))

                # Wait for both episodes to be processed
                await asyncio.sleep(3)

                # Cancel the worker task
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

                # Verify task_done was called twice (once for timeout, once for success)
                assert mock_queue.task_done.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_does_not_stop_worker(self):
        """Timeout should not mark worker as stopped."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config:
            # Set a short timeout
            mock_config.resilience.episode_timeout = 1

            # Create mock queue and worker tracking
            with patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
                 patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

                # Initialize workers dict
                mock_workers.__getitem__ = MagicMock(return_value=True)
                mock_workers.__setitem__ = MagicMock()
                mock_workers.get = MagicMock(return_value=True)

                # Create a mock queue
                mock_queue = AsyncMock()
                mock_queues.__getitem__.return_value = mock_queue

                # Create a slow processing function
                async def slow_process():
                    await asyncio.sleep(5)

                # Set up queue to return the slow function once
                call_count = 0
                async def get_func():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return slow_process
                    await asyncio.sleep(100)
                    return None

                mock_queue.get.side_effect = get_func

                # Start the worker
                worker_task = asyncio.create_task(process_episode_queue('test-group'))

                # Wait for timeout to occur
                await asyncio.sleep(2)

                # Cancel the worker task
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

                # Verify worker was not marked as stopped (False) due to timeout
                # The worker should only be set to False in the finally block
                calls_to_set_false = [
                    call for call in mock_workers.__setitem__.call_args_list
                    if len(call[0]) > 1 and call[0][1] is False
                ]
                # Should only be set to False once in the finally block, not during timeout handling
                assert len(calls_to_set_false) <= 1
