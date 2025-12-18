"""
Security tests for error message handling.

Tests verify that error messages and health endpoints do not expose:
- Neo4j credentials
- OpenAI API keys
- Other sensitive configuration values
"""

import re
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
import httpx


class TestCredentialExposure:
    """Verify error messages don't expose credentials."""

    def test_neo4j_password_not_in_errors(self):
        """Verify error messages don't expose Neo4j credentials."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Simulate various error scenarios
        errors = [
            httpx.ConnectError("Connection refused"),
            httpx.TimeoutException("Timeout"),
            Exception("Database connection failed with password: secret123"),
        ]

        for error in errors:
            with patch('httpx.Client.get') as mock_get:
                mock_get.side_effect = error

                captured_stderr = StringIO()
                with patch('sys.stderr', captured_stderr):
                    try:
                        client.health_check()
                    except Exception:
                        pass

                stderr_output = captured_stderr.getvalue()

                # Check for password-like patterns
                password_patterns = [
                    r'password["\']?\s*[:=]\s*["\']?([^"\'\s]+)',
                    r'NEO4J_PASSWORD',
                    r'neo4j\+s[sc]?://[^:]+:([^@]+)@',  # neo4j://user:PASSWORD@host
                ]

                for pattern in password_patterns:
                    matches = re.findall(pattern, stderr_output, re.IGNORECASE)
                    # Should not contain actual passwords (only placeholder text is ok)
                    for match in matches:
                        match_str = match if isinstance(match, str) else match[0]
                        assert match_str in ["***", "REDACTED", "password"], \
                            f"Error should not expose password: {match_str}"

    def test_neo4j_uri_sanitized(self):
        """Verify Neo4j URI in errors has password redacted."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Simulate error with URI in message
        error_msg = "Failed to connect to neo4j+s://user:secretpass@localhost:7687"

        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = Exception(error_msg)

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except Exception:
                    pass

            stderr_output = captured_stderr.getvalue()

            # If URI appears, password should be redacted
            if "neo4j" in stderr_output:
                # Should not contain the actual password
                assert "secretpass" not in stderr_output, \
                    "Neo4j password should be redacted in URIs"

                # Acceptable forms: neo4j+s://user:***@host or neo4j+s://user@host
                uri_with_password_pattern = r'neo4j\+s[sc]?://[^:]+:[^*][^@]*@'
                matches = re.findall(uri_with_password_pattern, stderr_output)
                assert len(matches) == 0, \
                    "Neo4j URI should not contain unredacted password"

    def test_openai_api_key_not_exposed(self):
        """Verify error messages don't expose OpenAI API keys."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Simulate error that might contain API key reference
        error_msg = "LLM client failed with key: sk-1234567890abcdef"

        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = Exception(error_msg)

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except Exception:
                    pass

            stderr_output = captured_stderr.getvalue()

            # Check for OpenAI API key patterns
            api_key_patterns = [
                r'sk-[a-zA-Z0-9]{32,}',  # OpenAI key format
                r'OPENAI_API_KEY["\']?\s*[:=]\s*["\']?([^"\'\s]+)',
            ]

            for pattern in api_key_patterns:
                matches = re.findall(pattern, stderr_output)
                # Should not contain actual API keys
                for match in matches:
                    match_str = match if isinstance(match, str) else match[0]
                    assert match_str in ["***", "REDACTED"], \
                        f"Error should not expose API key: {match_str[:10]}..."


class TestHealthEndpointSecurity:
    """Verify health endpoint doesn't expose sensitive config values."""

    def test_health_no_passwords(self):
        """Verify health endpoint doesn't expose sensitive config values."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # Convert response to string for pattern matching
        response_str = str(data).lower()

        # Should not contain password fields
        sensitive_keys = [
            "password",
            "api_key",
            "apikey",
            "secret",
            "token",
            "bearer",
        ]

        for key in sensitive_keys:
            # It's ok to have the key name, but not the value
            # Check for patterns like "password": "actual_value"
            pattern = f'{key}["\']?\s*[:=]\s*["\']?([^"\'\s,}}]+)'
            matches = re.findall(pattern, response_str, re.IGNORECASE)

            for match in matches:
                # If value exists, it should be redacted or null
                assert match in ["***", "null", "none", "redacted", ""], \
                    f"Health endpoint should not expose {key} values"

    def test_health_config_path_safe(self):
        """Verify config path in health response doesn't expose sensitive info."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        # If config_path present, it should be a safe file system path
        config_path_keys = ["config_path", "daemon_config"]

        for key in config_path_keys:
            if key in data:
                config_path = data[key]

                # Should be a string path, not contain sensitive data
                assert isinstance(config_path, str), \
                    f"{key} should be string path"

                # Should not contain passwords or API keys in the path
                assert "password" not in config_path.lower(), \
                    "Config path should not contain 'password'"
                assert "sk-" not in config_path, \
                    "Config path should not contain API keys"

    def test_health_no_database_credentials(self):
        """Verify health endpoint doesn't expose database credentials."""
        from mcp_server.src.graphiti_mcp_server import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        response_str = str(data)

        # Should not contain Neo4j connection strings with passwords
        assert "neo4j+s://" not in response_str or \
               "neo4j+s://user:***@" in response_str or \
               "neo4j+s://user@" in response_str, \
            "Health endpoint should not expose database URIs with passwords"

        # Check for database credential keys
        db_cred_keys = [
            "neo4j_password",
            "db_password",
            "database_password",
            "uri_with_password",
        ]

        for key in db_cred_keys:
            assert key not in data, \
                f"Health endpoint should not include {key}"


class TestConfigFileContentSecurity:
    """Verify config file references don't leak sensitive data."""

    def test_error_references_config_safely(self):
        """Verify error messages referencing config file don't expose contents."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Simulate error that mentions config file
        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = Exception("Config error in graphiti.config.json")

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except Exception:
                    pass

            stderr_output = captured_stderr.getvalue()

            # Can mention the file path, but not the contents
            if "config" in stderr_output.lower():
                # Should not contain sensitive config values
                assert "sk-" not in stderr_output, \
                    "Error should not expose API keys from config"
                assert "neo4j+s://" not in stderr_output or \
                       "***" in stderr_output, \
                    "Error should not expose database URIs from config"


class TestLoggingSecurity:
    """Verify logging output doesn't expose credentials."""

    def test_bootstrap_logs_no_credentials(self):
        """Verify bootstrap logs don't expose credentials."""
        from mcp_server.daemon.bootstrap import BootstrapService
        import logging

        log_capture = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(record.getMessage())

        service = BootstrapService()

        test_handler = TestHandler()
        service.logger.addHandler(test_handler)
        service.logger.setLevel(logging.DEBUG)  # Capture all levels

        try:
            # Trigger various operations
            service.update_daemon_state(enabled=True)
            service.start_daemon()
            service.stop_daemon()

            # Check all log messages
            all_logs = " ".join(log_capture)

            # Should not contain sensitive patterns
            assert "sk-" not in all_logs, \
                "Logs should not contain API keys"

            # Check for password in non-redacted form
            password_pattern = r'password["\']?\s*[:=]\s*["\']?([^*"\'\s]+)'
            matches = re.findall(password_pattern, all_logs, re.IGNORECASE)

            for match in matches:
                assert match in ["***", "REDACTED", "password"], \
                    f"Logs should not expose passwords: {match}"

        finally:
            service.logger.removeHandler(test_handler)

    def test_startup_banner_no_credentials(self):
        """Verify startup banner doesn't expose credentials."""
        captured_stderr = StringIO()

        with patch('sys.stderr', captured_stderr):
            from mcp_server.src.graphiti_mcp_server import create_app
            app = create_app()

        stderr_output = captured_stderr.getvalue()

        # Banner should not contain sensitive data
        assert "sk-" not in stderr_output, \
            "Startup banner should not contain API keys"

        # Check for Neo4j URIs with passwords
        uri_pattern = r'neo4j\+s[sc]?://[^:]+:([^*@]+)@'
        matches = re.findall(uri_pattern, stderr_output)

        for match in matches:
            assert match in ["***", "REDACTED"], \
                f"Startup banner should not expose database passwords: {match}"


class TestErrorSanitization:
    """Test that error sanitization is applied consistently."""

    def test_exception_messages_sanitized(self):
        """Test that exception messages are sanitized before display."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Create error with embedded credentials
        sensitive_errors = [
            Exception("Connection to neo4j+s://user:mypassword123@host:7687 failed"),
            Exception("API key sk-1234567890abcdefghijklmnopqrstuv is invalid"),
            Exception("Secret token: abc123xyz789"),
        ]

        for error in sensitive_errors:
            with patch('httpx.Client.get') as mock_get:
                mock_get.side_effect = error

                captured_stderr = StringIO()
                with patch('sys.stderr', captured_stderr):
                    try:
                        client.health_check()
                    except Exception:
                        pass

                stderr_output = captured_stderr.getvalue()

                # Check that sensitive parts are redacted
                assert "mypassword123" not in stderr_output, \
                    "Exception messages should sanitize passwords"
                assert "sk-1234567890abcdefghijklmnopqrstuv" not in stderr_output, \
                    "Exception messages should sanitize API keys"

    def test_stack_traces_sanitized(self):
        """Test that stack traces don't expose credentials."""
        from mcp_server.api.client import GraphitiMcpClient

        client = GraphitiMcpClient()

        # Simulate error that would generate stack trace
        def fail_with_sensitive_data():
            api_key = "sk-sensitive1234567890"
            raise Exception(f"Failed with key: {api_key}")

        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = fail_with_sensitive_data

            captured_stderr = StringIO()
            with patch('sys.stderr', captured_stderr):
                try:
                    client.health_check()
                except Exception:
                    pass

            stderr_output = captured_stderr.getvalue()

            # Stack trace should not expose the API key
            assert "sk-sensitive1234567890" not in stderr_output, \
                "Stack traces should sanitize credentials"
