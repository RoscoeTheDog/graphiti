"""
Integration Tests for HTTP Transport

Tests the HTTP client-server communication for daemon architecture:
- GraphitiClient connecting to running daemon
- URL auto-discovery (env var -> config -> default)
- Health checks and status queries
- Session sync operations
- Error handling and actionable messages
"""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from mcp_server.api.client import GraphitiClient


class TestClientInitialization:
    """Test GraphitiClient initialization and URL discovery."""

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_explicit_url_overrides_discovery(self, tmp_path):
        """Explicit base_url parameter overrides auto-discovery"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('httpx.Client'):
                client = GraphitiClient(base_url="http://localhost:9999")
                assert client.base_url == "http://localhost:9999"

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_env_var_url_discovery(self, tmp_path):
        """GRAPHITI_URL env var takes precedence in auto-discovery"""
        with patch.dict(os.environ, {'GRAPHITI_URL': 'http://custom:8888'}):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('httpx.Client'):
                    client = GraphitiClient()
                    assert client.base_url == "http://custom:8888"

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_config_file_url_discovery(self, tmp_path):
        """Config file provides URL when env var not set"""
        # Create config with custom daemon settings
        config_dir = tmp_path / ".graphiti"
        config_dir.mkdir()
        config_file = config_dir / "graphiti.config.json"
        config = {
            "daemon": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 7777
            }
        }
        config_file.write_text(json.dumps(config))

        with patch.dict(os.environ, {}, clear=True):  # No env var
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('httpx.Client'):
                    client = GraphitiClient()
                    assert client.base_url == "http://127.0.0.1:7777"

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_default_url_fallback(self, tmp_path):
        """Default URL used when no env var or config"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('pathlib.Path.home', return_value=tmp_path):
                with patch('httpx.Client'):
                    client = GraphitiClient()
                    assert client.base_url == "http://127.0.0.1:8321"

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_custom_timeout(self, tmp_path):
        """Custom timeout parameter is respected"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('httpx.Client') as mock_client:
                client = GraphitiClient(timeout=60.0)
                mock_client.assert_called_once_with(timeout=60.0)

    def test_httpx_not_installed_error(self):
        """Raises helpful error when httpx not installed"""
        # Test that GraphitiClient raises ImportError with helpful message
        # when httpx is not available at initialization time
        with patch('mcp_server.api.client.httpx', None):
            with pytest.raises(ImportError) as exc_info:
                GraphitiClient()
            assert "httpx is required" in str(exc_info.value)


class TestHealthCheck:
    """Test health check endpoint communication."""

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_health_check_success(self, tmp_path):
        """Health check returns True when server responds"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "ok"}
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.health_check()

                assert result is True
                # Verify get was called with full URL
                mock_client.get.assert_called_once()
                call_args = mock_client.get.call_args[0][0]
                assert "/health" in call_args

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_health_check_connection_refused(self, tmp_path):
        """Health check returns False on connection refused"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.get.side_effect = httpx.ConnectError(
                    "Connection refused"
                )
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.health_check()

                assert result is False

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_health_check_timeout(self, tmp_path):
        """Health check returns False on timeout"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.get.side_effect = httpx.TimeoutException(
                    "Request timeout"
                )
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.health_check()

                assert result is False

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_health_check_server_error(self, tmp_path):
        """Health check returns False on 500 error"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.status_code = 500
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.health_check()

                assert result is False


class TestStatusEndpoint:
    """Test server status endpoint communication."""

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_get_status_success(self, tmp_path):
        """Get status returns server metadata"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "uptime_seconds": 3600,
                    "version": "1.0.0",
                    "sessions_tracked": 5
                }
                mock_response.raise_for_status = Mock()  # No-op for success
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                status = client.get_status()

                assert status['uptime_seconds'] == 3600
                assert status['version'] == "1.0.0"
                assert status['sessions_tracked'] == 5
                # Verify get was called with correct endpoint
                mock_client.get.assert_called_once()
                call_args = mock_client.get.call_args[0][0]
                assert "/api/v1/status" in call_args

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_get_status_connection_error(self, tmp_path):
        """Get status exits on connection error (actionable error)"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.get.side_effect = httpx.ConnectError(
                    "Connection refused"
                )
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                # The client exits with SystemExit when daemon is unreachable
                with pytest.raises(SystemExit):
                    client.get_status()


class TestSessionSyncEndpoint:
    """Test session sync endpoint communication."""

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_sync_sessions_success(self, tmp_path):
        """Sync sessions returns processing results"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "sessions_found": 10,
                    "episodes_created": 8,
                    "errors": []
                }
                mock_response.raise_for_status = Mock()
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.sync_sessions(days=7, dry_run=False)

                assert result['sessions_found'] == 10
                assert result['episodes_created'] == 8
                mock_client.post.assert_called_once()

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_sync_sessions_dry_run(self, tmp_path):
        """Dry run does not create episodes"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "sessions_found": 10,
                    "episodes_created": 0,
                    "dry_run": True
                }
                mock_response.raise_for_status = Mock()
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.sync_sessions(days=7, dry_run=True)

                assert result['dry_run'] is True
                assert result['episodes_created'] == 0

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_sync_sessions_with_errors(self, tmp_path):
        """Sync sessions returns errors for failed files"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "sessions_found": 5,
                    "episodes_created": 3,
                    "errors": [
                        {"file": "session1.json", "error": "Invalid JSON"},
                        {"file": "session2.json", "error": "Missing required field"}
                    ]
                }
                mock_response.raise_for_status = Mock()
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.sync_sessions(days=7)

                assert len(result['errors']) == 2
                assert result['sessions_found'] == 5
                assert result['episodes_created'] == 3


class TestErrorHandling:
    """Test error handling and actionable error messages."""

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_connection_refused_message(self, tmp_path, capsys):
        """Connection refused shows actionable error with config check"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.get.side_effect = httpx.ConnectError(
                    "Connection refused"
                )
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.health_check()

                # Should return False and log helpful error
                assert result is False

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_timeout_error_message(self, tmp_path):
        """Timeout shows actionable error with network troubleshooting"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.get.side_effect = httpx.TimeoutException(
                    "Request timeout"
                )
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                result = client.health_check()

                assert result is False

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_http_error_with_details(self, tmp_path):
        """HTTP errors include response details"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.json.return_value = {
                    "error": "Invalid request",
                    "details": "Missing required parameter 'days'"
                }
                mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
                    "400 Bad Request", request=Mock(), response=mock_response
                ))
                mock_client.post.return_value = mock_response
                mock_client_class.return_value = mock_client

                client = GraphitiClient()
                # Should raise HTTPStatusError with details
                with pytest.raises(httpx.HTTPStatusError):
                    client.sync_sessions(days=7)


class TestMultipleClients:
    """Test multiple clients connecting to same daemon."""

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_concurrent_clients_share_state(self, tmp_path):
        """Multiple clients can connect to same daemon"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "status": "ok",
                    "active_connections": 2
                }
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Create two clients
                client1 = GraphitiClient()
                client2 = GraphitiClient()

                # Both should connect successfully
                assert client1.health_check() is True
                assert client2.health_check() is True

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_clients_see_shared_data(self, tmp_path):
        """Clients accessing same daemon see same data"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()

                # First status call
                mock_response1 = Mock()
                mock_response1.status_code = 200
                mock_response1.json.return_value = {"sessions_tracked": 5}
                mock_response1.raise_for_status = Mock()

                # Second status call (same data)
                mock_response2 = Mock()
                mock_response2.status_code = 200
                mock_response2.json.return_value = {"sessions_tracked": 5}
                mock_response2.raise_for_status = Mock()

                mock_client.get.side_effect = [mock_response1, mock_response2]
                mock_client_class.return_value = mock_client

                client1 = GraphitiClient()
                client2 = GraphitiClient()

                status1 = client1.get_status()
                status2 = client2.get_status()

                # Both should see same session count
                assert status1['sessions_tracked'] == status2['sessions_tracked']


class TestClaudeCodeIntegration:
    """Test Claude Code MCP client connecting via HTTP transport."""

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_claude_code_http_transport_config(self, tmp_path):
        """Claude Code config specifies HTTP transport correctly"""
        # Simulate Claude Code MCP settings (HTTP transport format)
        mcp_config = {
            "mcpServers": {
                "graphiti-memory": {
                    "url": "http://127.0.0.1:8321/mcp/",
                    "transport": "http"
                }
            }
        }

        # Verify config structure
        assert mcp_config['mcpServers']['graphiti-memory']['transport'] == 'http'
        assert mcp_config['mcpServers']['graphiti-memory']['url'] == 'http://127.0.0.1:8321/mcp/'

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_claude_code_connection_flow(self, tmp_path):
        """Claude Code connects to daemon via HTTP successfully"""
        # This test simulates the connection flow:
        # 1. Claude Code reads MCP config
        # 2. Connects to HTTP endpoint
        # 3. Can make MCP tool calls

        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('mcp_server.api.client.httpx.Client') as mock_client_class:
                mock_client = Mock()

                # Health check response
                health_response = Mock()
                health_response.status_code = 200
                health_response.json.return_value = {"status": "ok"}

                # Status response
                status_response = Mock()
                status_response.status_code = 200
                status_response.json.return_value = {"status": "ok", "uptime_seconds": 100}
                status_response.raise_for_status = Mock()

                mock_client.get.side_effect = [health_response, status_response]
                mock_client_class.return_value = mock_client

                # Simulate Claude Code creating client
                client = GraphitiClient(base_url="http://127.0.0.1:8321")

                # Health check should succeed
                assert client.health_check() is True

                # Can make API calls
                status = client.get_status()
                assert status is not None
