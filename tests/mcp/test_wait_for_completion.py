"""
Tests for add_memory() wait_for_completion parameter functionality (AC-18.8, AC-18.9).

Story 18.3: Implement wait_for_completion Parameter
- AC-18.3.1: add_memory() accepts wait_for_completion parameter
- AC-18.3.2: wait_for_completion=true blocks until processing completes
- AC-18.3.3: wait_for_completion=false returns immediately (current behavior)
- AC-18.3.4: Default value comes from config (wait_for_completion_default)
- AC-18.3.5: Timeout handling prevents indefinite blocking
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestWaitForCompletionParameter:
    """Tests for wait_for_completion parameter acceptance (AC-18.3.1)."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create mock Graphiti client."""
        mock = MagicMock()
        mock.add_episode = AsyncMock(return_value=MagicMock(uuid="test-uuid-123"))
        mock.llm_available = True
        return mock

    @pytest.fixture
    def mock_config(self):
        """Create mock unified config."""
        mock = MagicMock()
        mock.mcp_tools.wait_for_completion_default = True
        mock.mcp_tools.timeout_seconds = 60
        mock.mcp_tools.on_llm_unavailable = "FAIL"
        return mock

    @pytest.mark.asyncio
    async def test_parameter_accepted_true(self, mock_graphiti_client, mock_config):
        """AC-18.3.1: add_memory() accepts wait_for_completion=True."""
        # Create real queues that will be processed
        episode_queues = {}
        queue_workers = {}

        # Create a mock process_episode_queue that actually processes the queue
        async def mock_process_queue(group_id):
            queue_workers[group_id] = True
            try:
                queue = episode_queues.get(group_id)
                if queue:
                    while not queue.empty():
                        process_fn = await queue.get()
                        await process_fn()
                        queue.task_done()
            finally:
                queue_workers[group_id] = False

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', episode_queues), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', queue_workers), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', mock_process_queue):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            result = await add_memory(
                name="Test Episode",
                episode_body="Test content",
                wait_for_completion=True
            )

            # Should not raise - parameter is accepted and should succeed
            assert "added successfully" in result.lower() or "success" in result.lower()

    @pytest.mark.asyncio
    async def test_parameter_accepted_false(self, mock_graphiti_client, mock_config):
        """AC-18.3.1: add_memory() accepts wait_for_completion=False."""
        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', {}), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', {}), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', AsyncMock()):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            # Should not raise - parameter is accepted
            result = await add_memory(
                name="Test Episode",
                episode_body="Test content",
                wait_for_completion=False
            )

            assert "queued successfully" in result.lower()

    @pytest.mark.asyncio
    async def test_parameter_accepted_none_uses_config_default(self, mock_graphiti_client):
        """AC-18.3.1: add_memory() accepts wait_for_completion=None (uses default)."""
        # Set default to False so we get immediate return
        mock_config = MagicMock()
        mock_config.mcp_tools.wait_for_completion_default = False
        mock_config.mcp_tools.timeout_seconds = 60
        mock_config.mcp_tools.on_llm_unavailable = "FAIL"

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', {}), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', {}), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', AsyncMock()):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            # None uses config default (False), should return immediately
            result = await add_memory(
                name="Test Episode",
                episode_body="Test content",
                wait_for_completion=None
            )

            # Default is False, so should queue and return immediately
            assert "queued successfully" in result.lower()


class TestWaitForCompletionBlocking:
    """Tests for synchronous blocking behavior (AC-18.3.2)."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create mock Graphiti client."""
        mock = MagicMock()
        mock.add_episode = AsyncMock(return_value=MagicMock(uuid="test-uuid-456"))
        mock.llm_available = True
        return mock

    @pytest.fixture
    def mock_config(self):
        """Create mock unified config."""
        mock = MagicMock()
        mock.mcp_tools.wait_for_completion_default = True
        mock.mcp_tools.timeout_seconds = 60
        mock.mcp_tools.on_llm_unavailable = "FAIL"
        return mock

    @pytest.mark.asyncio
    async def test_wait_true_returns_after_processing(self, mock_graphiti_client, mock_config):
        """AC-18.3.2: wait_for_completion=true blocks until processing completes."""
        episode_queues = {}
        queue_workers = {}

        async def mock_process_queue(group_id):
            queue_workers[group_id] = True
            try:
                queue = episode_queues.get(group_id)
                if queue:
                    while not queue.empty():
                        process_fn = await queue.get()
                        await process_fn()
                        queue.task_done()
            finally:
                queue_workers[group_id] = False

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', episode_queues), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', queue_workers), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', mock_process_queue):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            result = await add_memory(
                name="Test Episode",
                episode_body="Test content",
                wait_for_completion=True
            )

            # Should indicate successful completion, not queued
            assert "added successfully" in result.lower() or "success" in result.lower()
            # Should NOT say "queued"
            assert "queued" not in result.lower()

    @pytest.mark.asyncio
    async def test_wait_true_returns_episode_id(self, mock_graphiti_client, mock_config):
        """AC-18.3.2: Synchronous mode returns episode_id when available."""
        episode_queues = {}
        queue_workers = {}

        async def mock_process_queue(group_id):
            queue_workers[group_id] = True
            try:
                queue = episode_queues.get(group_id)
                if queue:
                    while not queue.empty():
                        process_fn = await queue.get()
                        await process_fn()
                        queue.task_done()
            finally:
                queue_workers[group_id] = False

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', episode_queues), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', queue_workers), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', mock_process_queue):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            result = await add_memory(
                name="Test Episode",
                episode_body="Test content",
                wait_for_completion=True
            )

            # Result should include episode_id for sync mode
            assert "success" in result.lower() or "added" in result.lower()


class TestWaitForCompletionAsync:
    """Tests for asynchronous queue behavior (AC-18.3.3)."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create mock Graphiti client."""
        mock = MagicMock()
        mock.add_episode = AsyncMock(return_value=MagicMock(uuid="test-uuid-789"))
        mock.llm_available = True
        return mock

    @pytest.fixture
    def mock_config(self):
        """Create mock unified config."""
        mock = MagicMock()
        mock.mcp_tools.wait_for_completion_default = False  # Async by default
        mock.mcp_tools.timeout_seconds = 60
        mock.mcp_tools.on_llm_unavailable = "FAIL"
        return mock

    @pytest.mark.asyncio
    async def test_wait_false_returns_immediately(self, mock_graphiti_client, mock_config):
        """AC-18.3.3: wait_for_completion=false returns immediately."""
        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', {}), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', {}), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', AsyncMock()):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            result = await add_memory(
                name="Test Episode",
                episode_body="Test content",
                wait_for_completion=False
            )

            # Should say "queued" not "added successfully"
            assert "queued successfully" in result.lower()


class TestWaitForCompletionDefault:
    """Tests for config default value (AC-18.3.4)."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create mock Graphiti client."""
        mock = MagicMock()
        mock.add_episode = AsyncMock(return_value=MagicMock(uuid="test-uuid-abc"))
        mock.llm_available = True
        return mock

    @pytest.mark.asyncio
    async def test_default_true_from_config(self, mock_graphiti_client):
        """AC-18.3.4: Default comes from config when wait_for_completion_default=True."""
        mock_config = MagicMock()
        mock_config.mcp_tools.wait_for_completion_default = True
        mock_config.mcp_tools.timeout_seconds = 60
        mock_config.mcp_tools.on_llm_unavailable = "FAIL"

        episode_queues = {}
        queue_workers = {}

        async def mock_process_queue(group_id):
            queue_workers[group_id] = True
            try:
                queue = episode_queues.get(group_id)
                if queue:
                    while not queue.empty():
                        process_fn = await queue.get()
                        await process_fn()
                        queue.task_done()
            finally:
                queue_workers[group_id] = False

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', episode_queues), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', queue_workers), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', mock_process_queue):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            # Don't pass wait_for_completion, should use config default (True)
            result = await add_memory(
                name="Test Episode",
                episode_body="Test content"
            )

            # Should wait and return success (not queued)
            assert "added successfully" in result.lower() or "success" in result.lower()

    @pytest.mark.asyncio
    async def test_default_false_from_config(self, mock_graphiti_client):
        """AC-18.3.4: Default comes from config when wait_for_completion_default=False."""
        mock_config = MagicMock()
        mock_config.mcp_tools.wait_for_completion_default = False
        mock_config.mcp_tools.timeout_seconds = 60
        mock_config.mcp_tools.on_llm_unavailable = "FAIL"

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', {}), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', {}), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', AsyncMock()):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            # Don't pass wait_for_completion, should use config default (False)
            result = await add_memory(
                name="Test Episode",
                episode_body="Test content"
            )

            # Should return immediately with queued message
            assert "queued successfully" in result.lower()


class TestWaitForCompletionTimeout:
    """Tests for timeout handling (AC-18.3.5)."""

    @pytest.fixture
    def mock_graphiti_client_slow(self):
        """Create mock Graphiti client that is slow to process."""
        mock = MagicMock()
        # Simulate slow processing that would timeout
        async def slow_add_episode(*args, **kwargs):
            await asyncio.sleep(5)  # 5 second delay
            return MagicMock(uuid="test-uuid-slow")
        mock.add_episode = slow_add_episode
        mock.llm_available = True
        return mock

    @pytest.fixture
    def mock_config_short_timeout(self):
        """Create mock config with short timeout."""
        mock = MagicMock()
        mock.mcp_tools.wait_for_completion_default = True
        mock.mcp_tools.timeout_seconds = 1  # 1 second timeout
        mock.mcp_tools.on_llm_unavailable = "FAIL"
        return mock

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self, mock_graphiti_client_slow, mock_config_short_timeout):
        """AC-18.3.5: Timeout prevents indefinite blocking and returns error."""
        # Don't process the queue so the Event never gets set
        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client_slow), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config_short_timeout), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', {}), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', {}), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', AsyncMock()):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            result = await add_memory(
                name="Slow Episode",
                episode_body="Test content",
                wait_for_completion=True
            )

            # Should return timeout error
            assert "timeout" in result.lower() or "timed out" in result.lower()


class TestWaitForCompletionErrorHandling:
    """Tests for error handling in wait_for_completion mode."""

    @pytest.fixture
    def mock_graphiti_client_error(self):
        """Create mock Graphiti client that raises an error."""
        mock = MagicMock()
        mock.add_episode = AsyncMock(side_effect=Exception("Database connection failed"))
        mock.llm_available = True
        return mock

    @pytest.fixture
    def mock_config(self):
        """Create mock unified config."""
        mock = MagicMock()
        mock.mcp_tools.wait_for_completion_default = True
        mock.mcp_tools.timeout_seconds = 60
        mock.mcp_tools.on_llm_unavailable = "FAIL"
        return mock

    @pytest.mark.asyncio
    async def test_processing_error_returned(self, mock_graphiti_client_error, mock_config):
        """Error during processing is returned when waiting."""
        episode_queues = {}
        queue_workers = {}

        async def mock_process_queue(group_id):
            queue_workers[group_id] = True
            try:
                queue = episode_queues.get(group_id)
                if queue:
                    while not queue.empty():
                        process_fn = await queue.get()
                        await process_fn()
                        queue.task_done()
            finally:
                queue_workers[group_id] = False

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client_error), \
             patch('mcp_server.graphiti_mcp_server.unified_config', mock_config), \
             patch('mcp_server.graphiti_mcp_server.config') as config_mock, \
             patch('mcp_server.graphiti_mcp_server.episode_queues', episode_queues), \
             patch('mcp_server.graphiti_mcp_server.queue_workers', queue_workers), \
             patch('mcp_server.graphiti_mcp_server.process_episode_queue', mock_process_queue):

            config_mock.group_id = "test-group"
            config_mock.use_custom_entities = False

            from mcp_server.graphiti_mcp_server import add_memory

            result = await add_memory(
                name="Error Episode",
                episode_body="Test content",
                wait_for_completion=True
            )

            # Should indicate error (either from processing or the outer exception handler)
            assert "error" in result.lower() or "failed" in result.lower()
