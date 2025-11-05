"""Tests for MCP server health check functionality."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the function and types we want to test
from mcp_server.graphiti_mcp_server import health_check


class TestHealthCheck:
    """Test health check endpoint and connection monitoring."""

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_when_client_not_initialized(self):
        """Health check should return unhealthy status when Graphiti client is None."""
        with patch('mcp_server.graphiti_mcp_server.graphiti_client', None), \
             patch('mcp_server.graphiti_mcp_server.consecutive_connection_failures', 2):

            response = await health_check()

            assert response['status'] == 'unhealthy'
            assert response['database_connected'] is False
            assert response['last_successful_connection'] is None
            assert response['consecutive_failures'] == 2
            assert response['error_details'] == 'Graphiti client not initialized'

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_when_database_connected(self):
        """Health check should return healthy status when database is accessible."""
        # Create mock driver session
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'test': 1})

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        # Create mock driver
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        # Create mock Graphiti client
        mock_client = MagicMock()
        mock_client.driver = mock_driver

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_client), \
             patch('mcp_server.graphiti_mcp_server.last_successful_connection', None), \
             patch('mcp_server.graphiti_mcp_server.consecutive_connection_failures', 0):

            response = await health_check()

            assert response['status'] == 'healthy'
            assert response['database_connected'] is True
            assert response['last_successful_connection'] is not None
            assert response['consecutive_failures'] == 0
            assert response['error_details'] is None

            # Verify the test query was executed
            mock_session.run.assert_called_once_with('RETURN 1 as test')

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_database_error(self):
        """Health check should return unhealthy status when database query fails."""
        # Create mock driver session that raises an exception
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(side_effect=Exception('Connection refused'))
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Create mock driver
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        # Create mock Graphiti client
        mock_client = MagicMock()
        mock_client.driver = mock_driver

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_client), \
             patch('mcp_server.graphiti_mcp_server.consecutive_connection_failures', 0), \
             patch('mcp_server.graphiti_mcp_server.logger') as mock_logger:

            response = await health_check()

            assert response['status'] == 'unhealthy'
            assert response['database_connected'] is False
            assert 'Connection refused' in response['error_details']

            # Verify error was logged
            assert mock_logger.error.called

    @pytest.mark.asyncio
    async def test_health_check_tracks_consecutive_failures(self):
        """Health check should track consecutive connection failures."""
        # Create mock driver session that raises an exception
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(side_effect=Exception('Connection timeout'))
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Create mock driver
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        # Create mock Graphiti client
        mock_client = MagicMock()
        mock_client.driver = mock_driver

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_client), \
             patch('mcp_server.graphiti_mcp_server.consecutive_connection_failures', 2), \
             patch('mcp_server.graphiti_mcp_server.logger'):

            response = await health_check()

            # Should have incremented failures counter
            assert response['consecutive_failures'] >= 2

    @pytest.mark.asyncio
    async def test_health_check_resets_failure_count_on_success(self):
        """Health check should reset consecutive failures to 0 on successful connection."""
        # Create mock driver session
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'test': 1})

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        # Create mock driver
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        # Create mock Graphiti client
        mock_client = MagicMock()
        mock_client.driver = mock_driver

        # Start with some failures
        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_client), \
             patch('mcp_server.graphiti_mcp_server.consecutive_connection_failures', 5):

            response = await health_check()

            # Failures should be reset to 0
            assert response['consecutive_failures'] == 0
            assert response['status'] == 'healthy'

    @pytest.mark.asyncio
    async def test_health_check_updates_last_successful_connection_timestamp(self):
        """Health check should update last_successful_connection timestamp on success."""
        # Create mock driver session
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'test': 1})

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        # Create mock driver
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        # Create mock Graphiti client
        mock_client = MagicMock()
        mock_client.driver = mock_driver

        # Set a past timestamp
        past_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_client), \
             patch('mcp_server.graphiti_mcp_server.last_successful_connection', past_time):

            response = await health_check()

            # Timestamp should be updated (not equal to past time)
            assert response['last_successful_connection'] is not None
            assert response['last_successful_connection'] != past_time.isoformat()
            assert response['status'] == 'healthy'


class TestConnectionStateTracking:
    """Test internal connection state tracking for monitoring."""

    @pytest.mark.asyncio
    async def test_connection_metrics_included_in_health_response(self):
        """Health check response should include connection metrics."""
        # Create mock driver session
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'test': 1})

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        # Create mock driver
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        # Create mock Graphiti client
        mock_client = MagicMock()
        mock_client.driver = mock_driver

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_client):

            response = await health_check()

            # Verify all required metrics are present
            assert 'status' in response
            assert 'database_connected' in response
            assert 'last_successful_connection' in response
            assert 'consecutive_failures' in response
            assert 'error_details' in response

    @pytest.mark.asyncio
    async def test_health_check_can_be_called_multiple_times(self):
        """Health check should be callable multiple times without side effects."""
        # Create mock driver session
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={'test': 1})

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        # Create mock driver
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        # Create mock Graphiti client
        mock_client = MagicMock()
        mock_client.driver = mock_driver

        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_client):

            # Call multiple times
            response1 = await health_check()
            response2 = await health_check()
            response3 = await health_check()

            # All should succeed
            assert response1['status'] == 'healthy'
            assert response2['status'] == 'healthy'
            assert response3['status'] == 'healthy'

            # Verify query was executed each time
            assert mock_session.run.call_count == 3
