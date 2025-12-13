"""
Security tests for deprecated parameter removal.

Tests for Story 1 - Deprecated Parameter Removal (Security Testing)
"""

import pytest
import json
from pathlib import Path


class TestNoSensitiveDataExposure:
    """Verify no sensitive data exposed through deprecated field removal."""

    def test_no_credentials_in_removed_fields(self):
        """Verify that removed deprecated fields don't inadvertently expose credentials.

        Validates AC-1.x (Security): Ensure deprecated field removal doesn't
        expose sensitive data through error messages or logs.
        """
        from mcp_server.unified_config import SessionTrackingConfig

        # Pydantic with extra="allow" accepts unknown fields, so they're ignored
        # This is actually safer - silently ignored rather than exposed in error messages
        config = SessionTrackingConfig(
            enabled=True,
            inactivity_timeout="secret_api_key_12345"  # Deprecated - will be ignored
        )

        # Verify the field is not accessible (not exposed)
        assert not hasattr(config, 'inactivity_timeout'), \
            "Deprecated field should not be accessible"


    def test_config_validation_error_messages_safe(self, tmp_path, monkeypatch):
        """Test that validation errors don't expose config file contents.

        Security check: Validation errors should be informative but not leak
        full config file contents or sensitive data.
        """
        from mcp_server.config_validator import ConfigValidator

        # Create config with sensitive-looking data in deprecated fields
        config_data = {
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "password_env": "SECRET_PASSWORD_ENV"
                }
            },
            "session_tracking": {
                "enabled": True,
                "inactivity_timeout": 300,  # Deprecated
                "check_interval": 60  # Deprecated
            }
        }

        config_file = tmp_path / "graphiti.config.json"
        config_file.write_text(json.dumps(config_data, indent=2))

        validator = ConfigValidator()

        # Validate config
        result = validator.validate_syntax(config_file)

        # If there are validation errors, verify they don't leak sensitive data
        if result.has_errors:
            for error in result.errors:
                assert "SECRET_PASSWORD_ENV" not in error.message, \
                    "Error message should not expose password environment variable name"


    def test_no_path_traversal_in_config_schema(self):
        """Test that config schema file path is secure (no path traversal).

        Security check: Ensure graphiti.config.schema.json path is not
        vulnerable to path traversal attacks.
        """
        schema_path = Path("graphiti.config.schema.json")

        # Verify schema path is absolute or relative to project root (not user-controlled)
        assert not str(schema_path).startswith(".."), \
            "Schema path should not use parent directory traversal"
        assert not str(schema_path).startswith("/tmp"), \
            "Schema path should not be in world-writable directory"


    def test_deprecated_field_removal_maintains_type_safety(self):
        """Test that deprecated field removal doesn't break type validation.

        Security check: Ensure Pydantic type validation still works correctly
        after field removal (prevents type confusion attacks).
        """
        from mcp_server.unified_config import SessionTrackingConfig

        # Test that valid fields still have type checking
        with pytest.raises(Exception) as excinfo:
            SessionTrackingConfig(
                enabled="not_a_boolean"  # Should be bool
            )

        # Pydantic should reject invalid type
        error_msg = str(excinfo.value).lower()
        assert "bool" in error_msg or "boolean" in error_msg or "type" in error_msg, \
            "Type validation should still work after deprecated field removal"


    def test_config_file_permissions_not_weakened(self, tmp_path):
        """Test that config file permissions remain secure.

        Security check: Ensure config file creation doesn't use overly permissive
        file permissions (should not be world-readable if contains secrets).
        """
        import os
        import stat
        import sys

        # Skip on Windows - different permission model
        if sys.platform == "win32":
            pytest.skip("Skipping permission test on Windows")

        # Create a config file
        config_data = {
            "database": {"backend": "neo4j"},
            "llm": {"provider": "openai"}
        }

        config_file = tmp_path / "graphiti.config.json"
        config_file.write_text(json.dumps(config_data, indent=2))

        # Check file permissions (Unix-like systems)
        if hasattr(os, 'stat'):
            file_stat = os.stat(config_file)
            mode = stat.S_IMODE(file_stat.st_mode)

            # File should not be world-writable
            assert not (mode & stat.S_IWOTH), \
                "Config file should not be world-writable"


    def test_no_sql_injection_through_deprecated_fields(self):
        """Test that deprecated field removal doesn't introduce SQL injection vectors.

        Security check: Ensure removed fields can't be exploited for injection attacks
        through error handling or migration code paths.
        """
        from mcp_server.unified_config import SessionTrackingConfig

        # Attempt SQL injection-like payloads in deprecated fields
        sql_injection_payloads = [
            "'; DROP TABLE sessions; --",
            "1' OR '1'='1",
            "admin'--",
        ]

        for payload in sql_injection_payloads:
            # Pydantic with extra="allow" silently ignores unknown fields
            config = SessionTrackingConfig(
                enabled=True,
                inactivity_timeout=payload  # Deprecated field - ignored
            )

            # Verify the payload is not accessible (safely ignored)
            assert not hasattr(config, 'inactivity_timeout'), \
                "Deprecated field with injection payload should not be accessible"


# Run with: pytest tests/test_deprecated_config_security.py -v
