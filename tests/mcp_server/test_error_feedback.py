"""
Unit tests for MCP server error feedback functionality.

Tests cover:
- Startup banner formatting and content
- Health endpoint daemon state reporting
- Error message templates and consistency
"""

import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest


class TestStartupBanner:
    """Test startup banner contains connection URL and daemon install command."""

    def test_banner_contains_connection_url(self):
        """Test startup banner contains connection URL (http://127.0.0.1:8321)."""
        # Capture stderr
        captured_stderr = StringIO()

        with patch('sys.stderr', captured_stderr):
            # Import after patching stderr to capture startup output
            from mcp_server.src.graphiti_mcp_server import create_app

            # Create app (triggers startup banner)
            app = create_app()

        stderr_output = captured_stderr.getvalue()

        # Verify connection URL present
        assert "http://127.0.0.1:8321" in stderr_output, \
            "Startup banner should contain connection URL"

        # Verify readable format
        assert "Graphiti MCP Server" in stderr_output or \
               "Starting" in stderr_output, \
            "Banner should have clear header"

    def test_banner_contains_daemon_install_command(self):
        """Test startup banner contains daemon install command."""
        captured_stderr = StringIO()

        with patch('sys.stderr', captured_stderr):
            from mcp_server.src.graphiti_mcp_server import create_app
            app = create_app()

        stderr_output = captured_stderr.getvalue()

        # Verify install command present
        assert "graphiti-mcp daemon install" in stderr_output, \
            "Banner should contain daemon install command"

    def test_banner_timing_before_mcp_protocol(self):
        """Test startup banner appears before MCP protocol initialization."""
        # This test ensures banner is visible during troubleshooting
        # by verifying it's printed to stderr early in startup

        captured_stderr = StringIO()

        with patch('sys.stderr', captured_stderr):
            from mcp_server.src.graphiti_mcp_server import create_app
            app = create_app()

        stderr_output = captured_stderr.getvalue()

        # Banner should be one of the first things printed
        # (within first 500 chars of stderr output)
        assert len(stderr_output) > 0, "Should have stderr output"
        assert stderr_output.find("http://127.0.0.1:8321") < 500 or \
               stderr_output.find("graphiti-mcp") < 500, \
            "Banner should appear early in startup output"


class TestHealthEndpoint:
    """Test health endpoint returns daemon state."""

    def test_health_endpoint_includes_daemon_state(self):
        """Test health endpoint returns daemon state (enabled: true/false)."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200, "Health endpoint should be accessible"
        data = response.json()

        # Verify daemon state field exists
        assert "daemon" in data or "daemon_enabled" in data, \
            "Health response should include daemon state"

        # Verify it's a boolean
        daemon_state = data.get("daemon") or data.get("daemon_enabled")
        assert isinstance(daemon_state, bool), \
            "Daemon state should be boolean (true/false)"

    def test_health_endpoint_includes_config_path(self):
        """Test health endpoint returns config file path."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # Verify config path field exists
        assert "config_path" in data or "daemon_config" in data, \
            "Health response should include config file path"

        # Verify it's a string
        config_path = data.get("config_path") or data.get("daemon_config")
        assert isinstance(config_path, str), \
            "Config path should be string"

    def test_health_endpoint_format_compatibility(self):
        """Test health endpoint maintains backward compatibility."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # Verify essential fields still present
        assert "status" in data, "Health response should include status field"
        assert data["status"] in ["ok", "healthy", "up"], \
            "Status field should indicate health"


class TestErrorMessageFormatting:
    """Test error message formatting matches template."""

    def test_error_template_structure(self):
        """Test error message formatting matches template (header, causes, actions)."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Simulate connection error
        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = ConnectionRefusedError("Connection refused")

            # Capture stderr
            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except:
                    pass  # Error expected

            stderr_output = captured_stderr.getvalue()

            # Verify template structure
            assert "❌" in stderr_output or "ERROR" in stderr_output, \
                "Error should have clear header marker"
            assert "Possible causes:" in stderr_output or \
                   "Daemon not running" in stderr_output, \
                "Error should explain cause"
            assert "graphiti-mcp daemon install" in stderr_output or \
                   "Run:" in stderr_output, \
                "Error should provide actionable command"

    def test_error_consistency_emoji_markers(self):
        """Test all error messages follow consistent format with emoji markers."""
        from mcp_server.api.client import GraphitiMcpClient

        # Test multiple error scenarios
        error_scenarios = [
            ConnectionRefusedError("Connection refused"),
            TimeoutError("Timeout"),
        ]

        for error in error_scenarios:
            client = GraphitiMcpClient()

            with patch('httpx.Client.get') as mock_get:
                mock_get.side_effect = error

                captured_stderr = StringIO()
                with patch('sys.stderr', captured_stderr):
                    try:
                        client.health_check()
                    except:
                        pass

                stderr_output = captured_stderr.getvalue()

                # All errors should have emoji or ERROR marker
                assert "❌" in stderr_output or "ERROR" in stderr_output, \
                    f"Error {error.__class__.__name__} should have clear marker"

    def test_port_conflict_detection_hint(self):
        """Test port conflict detection hint included when appropriate."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Simulate port in use error
        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = OSError("Address already in use")

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except:
                    pass

            stderr_output = captured_stderr.getvalue()

            # Should mention port 8321
            assert "8321" in stderr_output, \
                "Port conflict error should mention port number"


class TestBootstrapLogging:
    """Test bootstrap daemon state logging."""

    def test_daemon_state_change_logging(self):
        """Test stderr logging when daemon.enabled changes state."""
        from mcp_server.daemon.bootstrap import BootstrapService

        # Create bootstrap service
        service = BootstrapService()

        captured_logs = []

        # Mock logger to capture log calls
        with patch.object(service, 'logger') as mock_logger:
            mock_logger.info = lambda msg, *args, **kwargs: captured_logs.append(('info', msg))
            mock_logger.warning = lambda msg, *args, **kwargs: captured_logs.append(('warning', msg))

            # Simulate state change
            service.update_daemon_state(enabled=True)

            # Verify logging occurred
            assert len(captured_logs) > 0, "Should log daemon state changes"

            # Verify log content mentions enabled state
            log_messages = [msg for level, msg in captured_logs]
            assert any("enabled" in msg.lower() for msg in log_messages), \
                "Should log 'enabled' state"

    def test_daemon_start_stop_logging(self):
        """Test daemon start/stop events logged with actionable context."""
        from mcp_server.daemon.bootstrap import BootstrapService

        service = BootstrapService()

        captured_logs = []

        with patch.object(service, 'logger') as mock_logger:
            mock_logger.info = lambda msg, *args, **kwargs: captured_logs.append(('info', msg))
            mock_logger.error = lambda msg, *args, **kwargs: captured_logs.append(('error', msg))

            # Test start event
            service.start_daemon()

            # Verify start logged
            start_logs = [msg for level, msg in captured_logs if level == 'info']
            assert any("start" in msg.lower() for msg in start_logs), \
                "Should log daemon start event"

            captured_logs.clear()

            # Test stop event
            service.stop_daemon()

            # Verify stop logged
            stop_logs = [msg for level, msg in captured_logs if level == 'info']
            assert any("stop" in msg.lower() for msg in stop_logs), \
                "Should log daemon stop event"
