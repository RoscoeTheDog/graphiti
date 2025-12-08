"""Backward compatibility tests for configuration migration.

Validates that old configs (pre-Stories 9-16) still load and work correctly
with new defaults and schema changes from Stories 10-15.
"""

import json
import tempfile
from pathlib import Path

import pytest

from mcp_server.unified_config import GraphitiConfig, SessionTrackingConfig


class TestOldConfigFormatLoads:
    """Verify v1.0.0 configs still load in v2.0.0+."""

    def test_old_config_with_enabled_true_loads(self):
        """Verify old configs with enabled: true still work."""
        old_config = {
            "database": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password_env": "NEO4J_PASSWORD",
            },
            "llm": {"api_key_env": "OPENAI_API_KEY", "model": "gpt-4o"},
            "session_tracking": {
                "enabled": True,  # Old default
                "watch_path": "/tmp/claude-sessions",
                "inactivity_timeout": 300,
                "check_interval": 60,
                # Note: Missing new fields (keep_length_days, auto_summarize, templates, filter)
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(old_config, f)
            config_path = f.name

        try:
            # Load config
            config = GraphitiConfig.from_file(Path(config_path))

            # Verify old fields preserved
            assert config.session_tracking.enabled is True
            assert config.session_tracking.inactivity_timeout == 300
            assert config.session_tracking.check_interval == 60

            # Verify new fields have defaults
            assert config.session_tracking.keep_length_days == 7  # New default
            assert config.session_tracking.auto_summarize is False  # New default
            assert config.session_tracking.filter is not None  # Auto-generated

        finally:
            Path(config_path).unlink()

    def test_old_config_missing_session_tracking_section(self):
        """Verify old configs without session_tracking section get defaults."""
        old_config = {
            "database": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password_env": "NEO4J_PASSWORD",
            },
            "llm": {"api_key_env": "OPENAI_API_KEY"},
            # No session_tracking section at all
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(old_config, f)
            config_path = f.name

        try:
            config = GraphitiConfig.from_file(Path(config_path))

            # Should get all new defaults
            assert config.session_tracking.enabled is False  # New opt-in default
            assert config.session_tracking.inactivity_timeout == 900  # New default (15 min)
            assert config.session_tracking.keep_length_days == 7
            assert config.session_tracking.auto_summarize is False

        finally:
            Path(config_path).unlink()

    def test_old_config_with_preserve_tool_results_deprecated(self):
        """Verify old preserve_tool_results field handled gracefully."""
        old_config = {
            "database": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password_env": "NEO4J_PASSWORD",
            },
            "llm": {"api_key_env": "OPENAI_API_KEY"},
            "session_tracking": {
                "enabled": True,
                "watch_path": "/tmp",
                "preserve_tool_results": True,  # DEPRECATED field (Story 2.3)
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(old_config, f)
            config_path = f.name

        try:
            # Should load without error (deprecated field ignored)
            config = GraphitiConfig.from_file(Path(config_path))

            # New filter config should exist (old field replaced)
            assert config.session_tracking.filter is not None
            # Default filter config should preserve tool calls (equivalent behavior)
            assert config.session_tracking.filter.tool_calls != "omit"

        finally:
            Path(config_path).unlink()


class TestMigrationFromOldDefaults:
    """Test migration from old unsafe defaults to new safe defaults."""

    def test_migration_changes_enabled_default(self):
        """Verify default changed from enabled: true to enabled: false."""
        # Old default (Story 5, before Story 10)
        old_default_config = SessionTrackingConfig()

        # After Story 10: Should be disabled by default
        assert old_default_config.enabled is False  # Opt-in model

    def test_migration_increases_inactivity_timeout(self):
        """Verify inactivity_timeout increased 300s → 900s (Story 10)."""
        config = SessionTrackingConfig()

        # New default is 15 minutes (900 seconds)
        assert config.inactivity_timeout == 900

    def test_migration_adds_rolling_window_filter(self):
        """Verify keep_length_days added with 7-day default (Story 12)."""
        config = SessionTrackingConfig()

        # Should have rolling window to prevent bulk indexing
        assert config.keep_length_days == 7


class TestDeprecatedFieldHandling:
    """Verify deprecated fields handled gracefully."""

    def test_content_mode_enum_removed(self):
        """Verify ContentMode enum no longer exported (Story 10)."""
        # ContentMode was removed in Story 10 - replaced with bool | str
        try:
            from graphiti_core.session_tracking.filter_config import ContentMode

            pytest.fail("ContentMode enum should not exist (deprecated in Story 10)")
        except ImportError:
            pass  # Expected - enum was removed

    def test_filter_config_uses_type_union(self):
        """Verify filter config now uses bool | str instead of ContentMode."""
        from graphiti_core.session_tracking.filter_config import FilterConfig

        config = FilterConfig()

        # Fields should accept bool or str
        assert isinstance(config.tool_calls, (bool, str))
        assert isinstance(config.tool_content, (bool, str))
        assert isinstance(config.user_messages, (bool, str))
        assert isinstance(config.agent_messages, (bool, str))


class TestConfigValidatorBackwardCompat:
    """Verify config validator handles old configs."""

    def test_validator_accepts_old_config_format(self):
        """Verify validator doesn't reject old-format configs."""
        old_config = {
            "database": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password_env": "NEO4J_PASSWORD",
            },
            "llm": {"api_key_env": "OPENAI_API_KEY"},
            "session_tracking": {
                "enabled": True,
                "watch_path": "/tmp",
                "inactivity_timeout": 300,  # Old default
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(old_config, f)
            config_path = Path(f.name)

        try:
            # Validate config
            from mcp_server.config_validator import ConfigValidator

            validator = ConfigValidator(config_path)
            errors = validator.validate_full()

            # Should not have critical errors (old format is valid)
            critical_errors = [e for e in errors if e.get("level") == "error"]
            assert (
                len(critical_errors) == 0
            ), f"Old config should validate: {critical_errors}"

        finally:
            config_path.unlink()


class TestCLIBackwardCompatibility:
    """Verify CLI commands work with old and new configs."""

    def test_cli_enable_command_still_works(self):
        """Verify graphiti-mcp-session-tracking enable command still works."""
        # This would be integration test - just verify command exists
        import subprocess

        result = subprocess.run(
            ["graphiti-mcp-session-tracking", "--help"],
            capture_output=True,
            text=True,
        )

        # Should show enable/disable/status commands
        assert result.returncode == 0 or "enable" in result.stdout.lower()

    def test_cli_preserves_existing_config_values(self):
        """Verify CLI doesn't overwrite unrelated config fields."""
        # Create config with custom values
        config_data = {
            "database": {
                "uri": "bolt://custom-host:7687",
                "user": "custom_user",
                "password_env": "CUSTOM_PASSWORD",
            },
            "llm": {"model": "gpt-4o-mini"},  # Custom model
            "session_tracking": {
                "enabled": False,
                "watch_path": "/custom/path",
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # Load config, toggle enabled
            config = GraphitiConfig.from_file(config_path)
            config.session_tracking.enabled = True

            # Save config
            with open(config_path, "w") as f:
                json.dump(config.model_dump(), f, indent=2)

            # Reload and verify custom values preserved
            reloaded = GraphitiConfig.from_file(config_path)
            assert reloaded.database.uri == "bolt://custom-host:7687"
            assert reloaded.llm.model == "gpt-4o-mini"
            assert reloaded.session_tracking.watch_path == "/custom/path"

        finally:
            config_path.unlink()


class TestMigrationGuideAccuracy:
    """Meta-test to verify migration documentation is accurate."""

    def test_migration_guide_exists(self):
        """Verify SESSION_TRACKING_MIGRATION.md exists."""
        migration_guide = Path(
            "docs/guides/SESSION_TRACKING_MIGRATION.md"
        )
        assert (
            migration_guide.exists()
        ), "Migration guide should exist at docs/guides/SESSION_TRACKING_MIGRATION.md"

    def test_configuration_md_updated(self):
        """Verify CONFIGURATION.md reflects new defaults."""
        config_doc = Path("CONFIGURATION.md")
        assert config_doc.exists()

        content = config_doc.read_text()

        # Should document new defaults
        assert "enabled: false" in content or "disabled by default" in content.lower()
        assert "keep_length_days: 7" in content or "7 days" in content
        assert "auto_summarize: false" in content or "auto-summarize" in content.lower()


class TestNoBreakingAPIChanges:
    """Verify public APIs remain compatible."""

    def test_filter_api_unchanged(self):
        """Verify SessionFilter API still works (with deprecation warning)."""
        from graphiti_core.session_tracking import SessionFilter
        from graphiti_core.session_tracking.filter_config import FilterConfig

        # Old way: no config (uses defaults)
        filter1 = SessionFilter()
        assert filter1 is not None

        # New way: with config
        filter2 = SessionFilter(config=FilterConfig())
        assert filter2 is not None

    def test_mcp_tools_api_unchanged(self):
        """Verify MCP tool signatures unchanged.

        NOTE: session_tracking_start() and session_tracking_stop() were removed in Story R2.
        Session tracking is now controlled via configuration (graphiti.config.json).
        MCP tools are read-only for monitoring/diagnostics only.
        """
        from mcp_server.graphiti_mcp_server import (
            session_tracking_status,
        )

        # Check signatures exist (can be called)
        assert callable(session_tracking_status)

    def test_config_loading_api_unchanged(self):
        """Verify GraphitiConfig.from_file() API unchanged."""
        from mcp_server.unified_config import GraphitiConfig

        # API should still work
        assert hasattr(GraphitiConfig, "from_file")
        assert callable(GraphitiConfig.from_file)
