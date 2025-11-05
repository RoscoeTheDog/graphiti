"""Comprehensive resilience tests for MCP server.

Tests timeout behavior, connection failure recovery, and queue worker restart functionality.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server.graphiti_mcp_server import (
    initialize_graphiti_with_retry,
    is_recoverable_error,
    process_episode_queue,
)


class TestTimeoutBehavior:
    """Test episode processing timeout behavior in various scenarios."""

    @pytest.mark.asyncio
    async def test_timeout_configuration_is_respected(self):
        """Timeout configuration should be honored during episode processing."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config:
            # Set a very short timeout
            mock_config.resilience.episode_timeout = 0.5

            with patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
                 patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

                mock_queue = AsyncMock()
                mock_queues.__getitem__.return_value = mock_queue

                # Create a function that exceeds timeout
                async def slow_process():
                    await asyncio.sleep(2)  # Longer than 0.5s timeout

                call_count = 0
                async def get_func():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return slow_process
                    await asyncio.sleep(100)
                    return None

                mock_queue.get.side_effect = get_func

                worker_task = asyncio.create_task(process_episode_queue('test-group'))

                # Wait for timeout to occur
                await asyncio.sleep(1)

                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

                # Verify episode was marked as done despite timeout
                assert mock_queue.task_done.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_consecutive_timeouts(self):
        """Worker should handle multiple consecutive timeouts gracefully."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config:
            mock_config.resilience.episode_timeout = 0.5

            with patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
                 patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

                mock_queue = AsyncMock()
                mock_queues.__getitem__.return_value = mock_queue

                # Create multiple slow functions
                async def slow_process():
                    await asyncio.sleep(2)

                call_count = 0
                async def get_func():
                    nonlocal call_count
                    call_count += 1
                    if call_count <= 3:
                        return slow_process
                    await asyncio.sleep(100)
                    return None

                mock_queue.get.side_effect = get_func

                worker_task = asyncio.create_task(process_episode_queue('test-group'))

                # Wait for all timeouts
                await asyncio.sleep(2.5)

                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

                # All three timeouts should have been handled
                assert mock_queue.task_done.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_then_success(self):
        """Worker should recover and process successful episodes after timeout."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config:
            mock_config.resilience.episode_timeout = 0.5

            with patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
                 patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

                mock_queue = AsyncMock()
                mock_queues.__getitem__.return_value = mock_queue

                success_count = []

                async def slow_process():
                    await asyncio.sleep(2)

                async def fast_process():
                    success_count.append(1)
                    await asyncio.sleep(0.1)

                call_count = 0
                async def get_func():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return slow_process  # Will timeout
                    elif call_count == 2:
                        return fast_process  # Should succeed
                    await asyncio.sleep(100)
                    return None

                mock_queue.get.side_effect = get_func

                worker_task = asyncio.create_task(process_episode_queue('test-group'))

                # Wait for both episodes
                await asyncio.sleep(1.5)

                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

                # Both episodes should be processed
                assert mock_queue.task_done.call_count == 2
                # Success function should have executed
                assert len(success_count) == 1


class TestConnectionFailureRecovery:
    """Test connection failure recovery scenarios."""

    @pytest.mark.asyncio
    async def test_recoverable_vs_non_recoverable_error_handling(self):
        """Worker should differentiate between recoverable and non-recoverable errors."""
        # Test recoverable error triggers reconnection
        assert is_recoverable_error(Exception('Connection refused')) is True
        assert is_recoverable_error(Exception('Connection timeout')) is True

        # Test non-recoverable error does not trigger reconnection
        assert is_recoverable_error(Exception('Authentication failed')) is False
        assert is_recoverable_error(Exception('Permission denied')) is False


class TestQueueWorkerRestart:
    """Test queue worker restart functionality (covered in test_reconnection.py)."""

    @pytest.mark.asyncio
    async def test_worker_stops_permanently_on_failed_reconnection(self):
        """Worker should stop if all reconnection attempts fail."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config, \
             patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
             patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers, \
             patch('mcp_server.graphiti_mcp_server.initialize_graphiti_with_retry') as mock_retry, \
             patch('mcp_server.graphiti_mcp_server.metrics_tracker'):

            mock_config.resilience.episode_timeout = 5
            mock_queue = AsyncMock()
            mock_queues.__getitem__.return_value = mock_queue
            mock_queue.task_done = MagicMock()

            worker_stopped = []

            def track_worker_stop(key, value):
                if value is False:
                    worker_stopped.append(True)

            mock_workers.__setitem__.side_effect = track_worker_stop

            async def get_func():
                async def error_func():
                    raise Exception('Connection refused')
                return error_func

            mock_queue.get.side_effect = get_func
            mock_retry.return_value = False  # Reconnection fails

            worker_task = asyncio.create_task(process_episode_queue('test-group'))

            await asyncio.sleep(0.5)

            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

            # Worker should have been marked as stopped
            assert len(worker_stopped) >= 1


class TestMetricsTracking:
    """Test metrics tracking during resilience events."""

    @pytest.mark.asyncio
    async def test_timeout_events_are_tracked(self):
        """Timeout events should be tracked in metrics."""
        from mcp_server.graphiti_mcp_server import MetricsTracker

        tracker = MetricsTracker()

        # Record a timeout
        tracker.record_episode_timeout()

        # Verify timeout was tracked
        assert tracker.episode_timeout_count == 1

    @pytest.mark.asyncio
    async def test_success_and_failure_tracking(self):
        """Success and failure counts should be tracked correctly."""
        from mcp_server.graphiti_mcp_server import MetricsTracker

        tracker = MetricsTracker()

        # Record successes and failures
        tracker.record_episode_success(duration=1.0)
        tracker.record_episode_success(duration=2.0)
        tracker.record_episode_failure()

        assert tracker.episode_success_count == 2
        assert tracker.episode_failure_count == 1

    @pytest.mark.asyncio
    async def test_average_duration_calculation(self):
        """Average episode duration should be calculated correctly."""
        from mcp_server.graphiti_mcp_server import MetricsTracker

        tracker = MetricsTracker()

        # Record episodes with different durations
        tracker.record_episode_success(duration=1.0)
        tracker.record_episode_success(duration=3.0)
        tracker.record_episode_success(duration=5.0)

        # Average should be (1 + 3 + 5) / 3 = 3.0
        avg = tracker.get_average_processing_time()
        assert avg == 3.0


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    @pytest.mark.asyncio
    async def test_empty_queue_handling(self):
        """Worker should handle empty queue gracefully."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config, \
             patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
             patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

            mock_config.resilience.episode_timeout = 5
            mock_queue = AsyncMock()
            mock_queues.__getitem__.return_value = mock_queue

            # Queue blocks indefinitely (empty)
            async def get_func():
                await asyncio.sleep(100)
                return None

            mock_queue.get.side_effect = get_func

            worker_task = asyncio.create_task(process_episode_queue('test-group'))

            await asyncio.sleep(0.5)

            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

            # No errors should occur with empty queue
            assert mock_queue.task_done.call_count == 0

    @pytest.mark.asyncio
    async def test_rapid_episode_submission(self):
        """Worker should handle rapid episode submission without issues."""
        with patch('mcp_server.graphiti_mcp_server.unified_config') as mock_config, \
             patch('mcp_server.graphiti_mcp_server.episode_queues') as mock_queues, \
             patch('mcp_server.graphiti_mcp_server.queue_workers') as mock_workers:

            mock_config.resilience.episode_timeout = 5
            mock_queue = AsyncMock()
            mock_queues.__getitem__.return_value = mock_queue

            processed_count = []

            async def fast_process():
                processed_count.append(1)
                await asyncio.sleep(0.05)

            call_count = 0
            async def get_func():
                nonlocal call_count
                call_count += 1
                if call_count <= 10:
                    return fast_process
                await asyncio.sleep(100)
                return None

            mock_queue.get.side_effect = get_func

            worker_task = asyncio.create_task(process_episode_queue('test-group'))

            # Wait for processing
            await asyncio.sleep(1)

            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

            # All episodes should be processed
            assert len(processed_count) == 10
            assert mock_queue.task_done.call_count == 10

    def test_error_classification_edge_cases(self):
        """Test edge cases in error classification."""
        # Empty message
        assert isinstance(is_recoverable_error(Exception('')), bool)

        # None message
        try:
            assert isinstance(is_recoverable_error(Exception(None)), bool)
        except TypeError:
            pass  # Some Exception implementations may not accept None

        # Very long message
        long_msg = 'Connection refused ' * 1000
        assert is_recoverable_error(Exception(long_msg)) is True

        # Mixed case
        assert is_recoverable_error(Exception('CONNECTION REFUSED')) is True
        assert is_recoverable_error(Exception('connection REFUSED')) is True


class TestRetryLogic:
    """Test retry logic and backoff behavior."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Verify exponential backoff delays are correct."""
        with patch('mcp_server.graphiti_mcp_server.initialize_graphiti') as mock_init:
            mock_init.side_effect = Exception('Connection refused')

            delays = []

            async def mock_sleep(delay):
                delays.append(delay)

            with patch('asyncio.sleep', side_effect=mock_sleep):
                await initialize_graphiti_with_retry(max_retries=4)

                # Should have delays of 1s, 2s, 4s (exponential: 2^0, 2^1, 2^2)
                assert delays == [1, 2, 4]

    @pytest.mark.asyncio
    async def test_configurable_max_retries(self):
        """Max retries parameter should be respected."""
        with patch('mcp_server.graphiti_mcp_server.initialize_graphiti') as mock_init:
            mock_init.side_effect = Exception('Connection refused')

            with patch('asyncio.sleep'):
                # Test with different retry counts
                await initialize_graphiti_with_retry(max_retries=1)
                assert mock_init.call_count == 1

                mock_init.reset_mock()

                await initialize_graphiti_with_retry(max_retries=5)
                assert mock_init.call_count == 5
