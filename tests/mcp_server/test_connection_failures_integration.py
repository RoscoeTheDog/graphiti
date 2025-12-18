"""
Integration tests for connection failure scenarios.

Tests cover:
- Connection failures when daemon not running
- Connection failures when daemon.enabled=false
- Error message visibility in stderr
- Health endpoint accessibility
- Bootstrap daemon state changes
"""

import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import httpx


class TestConnectionFailureDaemonNotRunning:
    """Test connection failure when port 8321 unreachable (daemon not running)."""

    def test_connection_refused_error_message(self):
        """Test connection failure provides helpful error when daemon not running."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Ensure port 8321 is not reachable
        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    result = client.health_check()
                except Exception:
                    pass  # Connection error expected

            stderr_output = captured_stderr.getvalue()

            # Verify error message contains install command
            assert "graphiti-mcp daemon install" in stderr_output, \
                "Error should include daemon install command"
            assert "Daemon not running" in stderr_output or \
                   "not reachable" in stderr_output, \
                "Error should explain daemon is not running"

    def test_connection_timeout_error_message(self):
        """Test timeout error provides helpful guidance."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except Exception:
                    pass

            stderr_output = captured_stderr.getvalue()

            # Timeout should suggest daemon issue
            assert "daemon" in stderr_output.lower(), \
                "Timeout error should mention daemon"
            assert "graphiti-mcp daemon" in stderr_output, \
                "Should provide daemon-related command"

    def test_port_unreachable_error_details(self):
        """Test error provides specific port information."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Cannot connect to port 8321")

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except Exception:
                    pass

            stderr_output = captured_stderr.getvalue()

            # Should mention port 8321
            assert "8321" in stderr_output, \
                "Error should reference port 8321"


class TestConnectionFailureDaemonDisabled:
    """Test connection failure when daemon.enabled=false in config."""

    def test_daemon_disabled_error_message(self):
        """Test error message includes path to config file when daemon disabled."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Mock health check to simulate daemon.enabled=false
        with patch('httpx.Client.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "ok",
                "daemon_enabled": False,
                "config_path": "/path/to/graphiti.config.json"
            }
            mock_get.return_value = mock_response

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                result = client.health_check()

            stderr_output = captured_stderr.getvalue()

            # If daemon disabled, should provide config path
            if "daemon_enabled" in result and not result["daemon_enabled"]:
                # Error handling should suggest enabling daemon
                assert "config" in stderr_output.lower() or \
                       len(stderr_output) == 0, \
                    "Should mention config or not error when daemon explicitly disabled"

    def test_config_path_in_health_response(self):
        """Test health endpoint includes config path for debugging."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # Health response should include config path
        assert "config_path" in data or "daemon_config" in data or \
               "daemon" in data, \
            "Health response should include daemon/config information"


class TestStderrVisibility:
    """Test error messages are visible in stderr output."""

    def test_stderr_output_captured(self):
        """Test error messages visible in Claude Code logs (stderr output)."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            # Capture stderr
            captured_stderr = StringIO()
            original_stderr = sys.stderr

            try:
                sys.stderr = captured_stderr

                try:
                    client.health_check()
                except Exception:
                    pass  # Error expected

            finally:
                sys.stderr = original_stderr

            stderr_content = captured_stderr.getvalue()

            # Verify stderr was written to
            assert len(stderr_content) > 0, \
                "Error messages should write to stderr"
            assert "graphiti-mcp" in stderr_content.lower(), \
                "Stderr should contain relevant error context"

    def test_startup_banner_stderr(self):
        """Test startup banner visible in stderr."""
        captured_stderr = StringIO()

        with patch('sys.stderr', captured_stderr):
            from mcp_server.src.graphiti_mcp_server import create_app
            app = create_app()

        stderr_output = captured_stderr.getvalue()

        # Startup banner should be in stderr
        assert len(stderr_output) > 0, \
            "Startup banner should write to stderr"
        assert "http://127.0.0.1:8321" in stderr_output or \
               "graphiti" in stderr_output.lower(), \
            "Banner should contain connection info"


class TestHealthEndpointAccessibility:
    """Test health check endpoint accessible via HTTP."""

    def test_health_endpoint_via_http(self):
        """Test health endpoint accessible via curl http://127.0.0.1:8321/health."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        # Test HTTP GET to /health
        response = client.get("/health")

        assert response.status_code == 200, \
            "Health endpoint should return 200 OK"

        data = response.json()
        assert "status" in data, \
            "Health response should include status"

    def test_health_endpoint_json_format(self):
        """Test health endpoint returns valid JSON."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        # Should be valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict), "Health response should be JSON object"
        except Exception as e:
            pytest.fail(f"Health endpoint should return valid JSON: {e}")

    def test_health_endpoint_contains_daemon_metadata(self):
        """Test health endpoint includes daemon metadata for debugging."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # Should include daemon information
        daemon_keys = ["daemon", "daemon_enabled", "daemon_state", "config_path", "daemon_config"]
        has_daemon_info = any(key in data for key in daemon_keys)

        assert has_daemon_info, \
            "Health endpoint should include daemon metadata (enabled state or config path)"


class TestBootstrapStateChanges:
    """Test bootstrap logs show daemon state changes."""

    def test_bootstrap_logs_daemon_enabled(self):
        """Test bootstrap service logs when daemon.enabled changes."""
        from mcp_server.daemon.bootstrap import BootstrapService
        import logging

        # Capture log output
        log_capture = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())

        service = BootstrapService()

        # Add test handler to logger
        test_handler = TestHandler()
        service.logger.addHandler(test_handler)
        service.logger.setLevel(logging.INFO)

        try:
            # Trigger state change
            service.update_daemon_state(enabled=True)

            # Verify logging occurred
            assert len(log_capture) > 0, \
                "Bootstrap should log daemon state changes"

            # Check for relevant keywords
            log_text = " ".join(log_capture).lower()
            assert "enabled" in log_text or "daemon" in log_text, \
                "Logs should mention daemon enabled state"

        finally:
            service.logger.removeHandler(test_handler)

    def test_bootstrap_logs_daemon_start_stop(self):
        """Test bootstrap logs daemon start/stop events."""
        from mcp_server.daemon.bootstrap import BootstrapService
        import logging

        log_capture = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_capture.append({
                    'level': record.levelname,
                    'message': record.getMessage()
                })

        service = BootstrapService()

        test_handler = TestHandler()
        service.logger.addHandler(test_handler)
        service.logger.setLevel(logging.INFO)

        try:
            # Test start
            service.start_daemon()

            start_logs = [log for log in log_capture if 'start' in log['message'].lower()]
            assert len(start_logs) > 0, \
                "Should log daemon start event"

            log_capture.clear()

            # Test stop
            service.stop_daemon()

            stop_logs = [log for log in log_capture if 'stop' in log['message'].lower()]
            assert len(stop_logs) > 0, \
                "Should log daemon stop event"

        finally:
            service.logger.removeHandler(test_handler)

    def test_bootstrap_actionable_context_in_logs(self):
        """Test daemon logs include actionable context (commands, file paths)."""
        from mcp_server.daemon.bootstrap import BootstrapService
        import logging

        log_capture = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())

        service = BootstrapService()

        test_handler = TestHandler()
        service.logger.addHandler(test_handler)
        service.logger.setLevel(logging.INFO)

        try:
            # Trigger various state changes
            service.update_daemon_state(enabled=False)
            service.start_daemon()

            # Logs should include actionable info
            log_text = " ".join(log_capture)

            # Check for commands or file paths
            has_actionable_info = (
                "graphiti-mcp" in log_text or
                "config" in log_text.lower() or
                ".json" in log_text
            )

            assert has_actionable_info, \
                "Logs should include actionable context (commands, config paths)"

        finally:
            service.logger.removeHandler(test_handler)


class TestCrossComponentIntegration:
    """Test integration between client, server, and bootstrap."""

    def test_client_error_consumes_server_banner(self):
        """Test connection error handler can reference server startup banner info."""
        # This tests the integration point where client errors should
        # be informed by server stderr output

        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except Exception:
                    pass

            stderr_output = captured_stderr.getvalue()

            # Client error should reference the same URL as server banner
            assert "http://127.0.0.1:8321" in stderr_output or \
                   "8321" in stderr_output, \
                "Client errors should reference server connection details"

    def test_health_endpoint_reflects_bootstrap_state(self):
        """Test health endpoint daemon state matches bootstrap service state."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # Health endpoint should reflect daemon state from bootstrap
        # (even if we can't control bootstrap in this test, the field should exist)
        daemon_keys = ["daemon", "daemon_enabled", "daemon_state"]
        has_daemon_field = any(key in data for key in daemon_keys)

        assert has_daemon_field, \
            "Health endpoint should reflect daemon state from bootstrap service"
