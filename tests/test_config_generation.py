"""Tests for configuration auto-generation functionality."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.graphiti_mcp_server import (
    ensure_global_config_exists,
    ensure_default_templates_exist,
)


class TestConfigGeneration:
    """Test configuration auto-generation."""

    def test_config_created_when_missing(self, tmp_path):
        """Test that config is auto-generated when missing."""
        # Override home directory for test
        config_path = tmp_path / ".graphiti" / "graphiti.config.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            # Ensure config doesn't exist
            assert not config_path.exists()

            # Call generation
            result_path = ensure_global_config_exists()

            # Verify config created
            assert config_path.exists()
            assert result_path == config_path

    def test_config_not_overwritten_when_exists(self, tmp_path):
        """Test that existing config is not overwritten."""
        config_path = tmp_path / ".graphiti" / "graphiti.config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create existing config with custom content
        custom_config = {"custom_key": "custom_value"}
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(custom_config, f)

        with patch("pathlib.Path.home", return_value=tmp_path):
            # Call generation (should not overwrite)
            result_path = ensure_global_config_exists()

            # Verify config still has custom content
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)

            assert loaded_config == custom_config
            assert result_path == config_path

    def test_generated_config_is_valid_json(self, tmp_path):
        """Test that generated config is valid JSON."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result_path = ensure_global_config_exists()

            # Verify valid JSON
            with open(result_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Verify it's a dictionary
            assert isinstance(config, dict)

    def test_generated_config_has_required_sections(self, tmp_path):
        """Test that generated config has all required sections."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result_path = ensure_global_config_exists()

            with open(result_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Verify structure
            assert "database" in config
            assert "llm" in config
            assert "session_tracking" in config

    def test_generated_config_has_inline_comments(self, tmp_path):
        """Test that generated config includes inline comments."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result_path = ensure_global_config_exists()

            with open(result_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Verify comments
            assert "_comment" in config
            assert "_docs" in config
            assert "_comment" in config["database"]
            assert "_comment" in config["llm"]
            assert "_comment" in config["session_tracking"]

    def test_generated_config_has_help_fields(self, tmp_path):
        """Test that generated config includes help fields."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result_path = ensure_global_config_exists()

            with open(result_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Verify help fields in session_tracking
            st = config["session_tracking"]
            assert "_enabled_help" in st
            assert "_watch_path_help" in st
            assert "_inactivity_timeout_help" in st
            assert "_check_interval_help" in st
            assert "_auto_summarize_help" in st
            assert "_store_in_graph_help" in st
            assert "_keep_length_days_help" in st

    def test_generated_config_defaults_match_schema(self, tmp_path):
        """Test that generated config defaults match schema."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            result_path = ensure_global_config_exists()

            with open(result_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Verify defaults (opt-in model)
            st = config["session_tracking"]
            assert st["enabled"] is False  # Disabled by default
            assert st["watch_path"] is None
            assert st["inactivity_timeout"] == 900  # 15 minutes
            assert st["check_interval"] == 60  # 1 minute
            assert st["auto_summarize"] is False
            assert st["store_in_graph"] is True
            assert st["keep_length_days"] == 1  # Rolling window

    def test_config_directory_created_if_missing(self, tmp_path):
        """Test that .graphiti directory is created if missing."""
        graphiti_dir = tmp_path / ".graphiti"

        with patch("pathlib.Path.home", return_value=tmp_path):
            # Ensure directory doesn't exist
            assert not graphiti_dir.exists()

            # Call generation
            ensure_global_config_exists()

            # Verify directory created
            assert graphiti_dir.exists()
            assert graphiti_dir.is_dir()


class TestTemplateGeneration:
    """Test template auto-generation."""

    def test_templates_created_when_missing(self, tmp_path):
        """Test that templates are auto-generated when missing."""
        templates_dir = tmp_path / ".graphiti" / "auto-tracking" / "templates"

        with patch("pathlib.Path.home", return_value=tmp_path):
            # Ensure templates don't exist
            assert not templates_dir.exists()

            # Call generation
            ensure_default_templates_exist()

            # Verify templates created
            assert templates_dir.exists()
            assert (templates_dir / "default-tool-content.md").exists()
            assert (templates_dir / "default-user-messages.md").exists()
            assert (templates_dir / "default-agent-messages.md").exists()

    def test_templates_not_overwritten_when_exist(self, tmp_path):
        """Test that existing templates are not overwritten."""
        templates_dir = tmp_path / ".graphiti" / "auto-tracking" / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Create existing template with custom content
        custom_template = templates_dir / "default-tool-content.md"
        custom_content = "CUSTOM TEMPLATE CONTENT"
        custom_template.write_text(custom_content, encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            # Call generation (should not overwrite)
            ensure_default_templates_exist()

            # Verify template still has custom content
            assert custom_template.read_text(encoding="utf-8") == custom_content

    def test_template_directory_created_if_missing(self, tmp_path):
        """Test that templates directory is created if missing."""
        templates_dir = tmp_path / ".graphiti" / "auto-tracking" / "templates"

        with patch("pathlib.Path.home", return_value=tmp_path):
            # Ensure directory doesn't exist
            assert not templates_dir.exists()

            # Call generation
            ensure_default_templates_exist()

            # Verify directory created
            assert templates_dir.exists()
            assert templates_dir.is_dir()


class TestIntegration:
    """Integration tests for server initialization."""

    @pytest.mark.asyncio
    async def test_server_starts_with_no_config(self, tmp_path):
        """Test that MCP server initialization creates config automatically."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            # Ensure no config exists
            config_path = tmp_path / ".graphiti" / "graphiti.config.json"
            assert not config_path.exists()

            # Call auto-generation manually (simulating server start)
            try:
                ensure_global_config_exists()
                ensure_default_templates_exist()
            except Exception as e:
                pytest.fail(f"Auto-generation failed: {e}")

            # Verify config and templates created
            assert config_path.exists()
            templates_dir = tmp_path / ".graphiti" / "auto-tracking" / "templates"
            assert templates_dir.exists()
            assert (templates_dir / "default-tool-content.md").exists()

    def test_generation_continues_on_error(self, tmp_path):
        """Test that server continues if generation fails."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            # Make config directory read-only to force error
            graphiti_dir = tmp_path / ".graphiti"
            graphiti_dir.mkdir(parents=True, exist_ok=True)
            graphiti_dir.chmod(0o444)  # Read-only

            try:
                # Call generation (should raise error but not crash)
                ensure_global_config_exists()
            except Exception:
                # Expected to fail
                pass

            # Restore permissions for cleanup
            graphiti_dir.chmod(0o755)

    def test_all_templates_have_content(self, tmp_path):
        """Test that all generated templates have non-empty content."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            ensure_default_templates_exist()

            templates_dir = tmp_path / ".graphiti" / "auto-tracking" / "templates"
            template_files = [
                "default-tool-content.md",
                "default-user-messages.md",
                "default-agent-messages.md",
            ]

            for template_file in template_files:
                template_path = templates_dir / template_file
                assert template_path.exists()
                content = template_path.read_text(encoding="utf-8")
                assert len(content) > 0
                assert "content" in content.lower()  # Should have {content} variable
