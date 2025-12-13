"""
Integration tests for deprecated parameter removal.

Tests for Story 1 - Deprecated Parameter Removal (Integration Testing)
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConfigLoadingWithoutDeprecatedFields:
    """Test loading graphiti.config.json without deprecated fields."""

    def test_load_config_without_deprecated_fields(self, tmp_path, monkeypatch):
        """Test loading graphiti.config.json without deprecated fields.

        Validates AC-1.3: Config file can be loaded without deprecated parameters.
        """
        from mcp_server.unified_config import GraphitiConfig

        # Create a config file without deprecated fields
        config_data = {
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD",
                    "database": "neo4j"
                }
            },
            "llm": {
                "provider": "openai",
                "default_model": "gpt-4o-mini"
            },
            "session_tracking": {
                "enabled": True,
                "group_id": "test_integration",
                "cross_project_search": True,
                "trusted_namespaces": ["abc123"],
                "include_project_path": False
                # NOTE: No deprecated fields (inactivity_timeout, check_interval, auto_summarize)
            }
        }

        config_file = tmp_path / "graphiti.config.json"
        config_file.write_text(json.dumps(config_data, indent=2))
        monkeypatch.chdir(tmp_path)

        # Load config from file
        config = GraphitiConfig.from_file()

        # Verify config loaded successfully
        assert config is not None
        assert config.session_tracking.enabled is True
        assert config.session_tracking.group_id == "test_integration"

        # Verify deprecated fields are not present
        assert not hasattr(config.session_tracking, 'inactivity_timeout')
        assert not hasattr(config.session_tracking, 'check_interval')
        assert not hasattr(config.session_tracking, 'auto_summarize')


    def test_load_config_with_deprecated_fields_in_file(self, tmp_path, monkeypatch):
        """Test loading config file that still contains deprecated fields (user hasn't updated yet).

        The config system should ignore these fields gracefully or raise validation error.
        """
        from mcp_server.unified_config import GraphitiConfig

        # Create a config file WITH deprecated fields (simulating old user config)
        config_data = {
            "database": {"backend": "neo4j"},
            "llm": {"provider": "openai"},
            "session_tracking": {
                "enabled": True,
                "group_id": "test",
                "inactivity_timeout": 300,  # Deprecated
                "check_interval": 60,  # Deprecated
                "auto_summarize": True  # Deprecated
            }
        }

        config_file = tmp_path / "graphiti.config.json"
        config_file.write_text(json.dumps(config_data, indent=2))
        monkeypatch.chdir(tmp_path)

        # Attempt to load config - should either:
        # 1. Raise validation error (strict mode)
        # 2. Ignore deprecated fields (permissive mode)
        try:
            config = GraphitiConfig.from_file()

            # If loading succeeded (permissive mode), verify deprecated fields ignored
            assert not hasattr(config.session_tracking, 'inactivity_timeout'), \
                "Deprecated field should be ignored"
            assert not hasattr(config.session_tracking, 'check_interval'), \
                "Deprecated field should be ignored"
            assert not hasattr(config.session_tracking, 'auto_summarize'), \
                "Deprecated field should be ignored"

        except Exception as e:
            # If loading failed (strict mode), verify error mentions deprecated field
            error_msg = str(e).lower()
            assert any(field in error_msg for field in ['inactivity_timeout', 'check_interval', 'auto_summarize']), \
                "Error should mention deprecated field"


class TestMCPServerStartup:
    """Test MCP server starts with updated config schema."""

    def test_mcp_server_startup_with_new_config(self, tmp_path, monkeypatch):
        """Test MCP server can start with config schema without deprecated fields.

        Validates AC-1.5: MCP server initialization works with updated config.
        """
        from mcp_server.unified_config import GraphitiConfig

        # Create minimal config without deprecated fields
        config_data = {
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD"
                }
            },
            "llm": {
                "provider": "openai",
                "openai": {
                    "api_key_env": "OPENAI_API_KEY"
                }
            },
            "session_tracking": {
                "enabled": False
            }
        }

        config_file = tmp_path / "graphiti.config.json"
        config_file.write_text(json.dumps(config_data, indent=2))
        monkeypatch.chdir(tmp_path)

        # Load config (simulating MCP server startup)
        config = GraphitiConfig.from_file()

        # Verify config is valid for MCP server use
        assert config.database.backend == "neo4j"
        assert config.llm.provider == "openai"
        assert config.session_tracking.enabled is False

        # Verify no deprecated fields present
        assert not hasattr(config.session_tracking, 'inactivity_timeout')
        assert not hasattr(config.session_tracking, 'check_interval')
        assert not hasattr(config.session_tracking, 'auto_summarize')


class TestConfigGeneration:
    """Test config generation produces files without deprecated help text."""

    def test_generated_config_no_deprecated_help(self):
        """Test that generated config files don't include deprecated field help text.

        Validates AC-1.5: Config generation code removed deprecated help text.
        """
        from pathlib import Path

        # Read the MCP server source to verify help text removal
        server_source_path = Path("mcp_server/graphiti_mcp_server.py")

        if not server_source_path.exists():
            pytest.skip("MCP server source file not found")

        server_source = server_source_path.read_text(encoding='utf-8')

        # Verify deprecated help text removed
        assert "_inactivity_timeout_help" not in server_source, \
            "_inactivity_timeout_help should be removed from config generation"
        assert "_check_interval_help" not in server_source, \
            "_check_interval_help should be removed from config generation"
        assert "_auto_summarize_help" not in server_source, \
            "_auto_summarize_help should be removed from config generation"


# Run with: pytest tests/test_deprecated_config_integration.py -v
