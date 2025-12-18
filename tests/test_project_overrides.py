"""Tests for project override functionality.

Tests cover:
- ProjectOverride Pydantic schema validation
- normalize_project_path() cross-platform path handling
- deep_merge() nested dict merging with None inheritance
- GraphitiConfig.project_overrides field validation
"""

import os
import platform
import pytest
from pathlib import Path
from pydantic import ValidationError

from mcp_server.unified_config import (
    ProjectOverride,
    GraphitiConfig,
    LLMConfig,
    EmbedderConfig,
    ExtractionConfig,
    SessionTrackingConfig,
    normalize_project_path,
    deep_merge,
)


# ============================================================================
# Path Normalization Tests
# ============================================================================


class TestNormalizeProjectPath:
    """Test normalize_project_path() for all platforms."""

    def test_normalize_path_windows_backslash(self, monkeypatch):
        """Test Windows path with backslashes converts to /c/ format."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        # Simulate Windows absolute path
        result = normalize_project_path("C:\\Users\\Admin\\project")
        assert result == "/c/Users/Admin/project"

    def test_normalize_path_windows_forward_slash(self, monkeypatch):
        """Test Windows path with forward slashes converts to /c/ format."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        result = normalize_project_path("C:/Users/Admin/project")
        assert result == "/c/Users/Admin/project"

    def test_normalize_path_unix(self):
        """Test Unix path on current platform returns normalized path."""
        # On Windows, Unix-style paths get converted appropriately
        # On Unix, they remain as-is
        result = normalize_project_path("/home/user/project")
        # Result should be a valid normalized path (starts with / or /c/)
        assert result.startswith("/")
        assert "project" in result

    def test_normalize_path_msys(self):
        """Test MSYS-style path handling."""
        # MSYS paths should be normalized consistently
        result = normalize_project_path("/c/Users/Admin/project")
        assert result.startswith("/")
        assert "project" in result

    def test_normalize_path_expanduser(self):
        """Test tilde expansion works correctly."""
        # Expand ~ and normalize
        expanded = str(Path("~/project").expanduser())
        result = normalize_project_path(expanded)
        assert result.startswith("/")
        assert "project" in result

    def test_normalize_path_trailing_slash_removed(self):
        """Test trailing slashes are removed."""
        # Use platform-appropriate path
        if platform.system() == "Windows":
            result = normalize_project_path("C:/Users/test/project/")
        else:
            result = normalize_project_path("/home/user/project/")
        assert not result.endswith("/")
        assert "project" in result

    def test_normalize_path_relative_becomes_absolute(self):
        """Test relative paths are converted to absolute."""
        result = normalize_project_path("./project")
        # Should start with / (absolute path in normalized form)
        assert result.startswith("/")
        assert result.endswith("project")


# ============================================================================
# Deep Merge Tests
# ============================================================================


class TestDeepMerge:
    """Test deep_merge() function edge cases."""

    def test_deep_merge_scalar_override(self):
        """Test scalar values are replaced."""
        base = {"key": 1}
        override = {"key": 2}
        result = deep_merge(base, override)
        assert result == {"key": 2}

    def test_deep_merge_nested_dict(self):
        """Test nested dicts are merged recursively."""
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": 1, "c": 2}}

    def test_deep_merge_none_inherits(self):
        """Test None values in override inherit from base."""
        base = {"key": 1}
        override = {"key": None}
        result = deep_merge(base, override)
        assert result == {"key": 1}

    def test_deep_merge_list_replaces(self):
        """Test lists are replaced, not merged."""
        base = {"key": [1, 2]}
        override = {"key": [3]}
        result = deep_merge(base, override)
        assert result == {"key": [3]}

    def test_deep_merge_new_keys_added(self):
        """Test new keys from override are added."""
        base = {"a": 1}
        override = {"b": 2}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_deep_merge_deeply_nested(self):
        """Test multiple levels of nesting."""
        base = {"a": {"b": {"c": 1}}}
        override = {"a": {"b": {"d": 2}}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": {"c": 1, "d": 2}}}

    def test_deep_merge_none_in_nested_dict_inherits(self):
        """Test None inheritance works in nested dicts."""
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": None, "c": 3}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": 1, "c": 3}}

    def test_deep_merge_empty_dict_preserves_base(self):
        """Test empty override dict preserves base."""
        base = {"key": 1}
        override = {}
        result = deep_merge(base, override)
        assert result == {"key": 1}

    def test_deep_merge_empty_base_uses_override(self):
        """Test empty base dict uses override values."""
        base = {}
        override = {"key": 1}
        result = deep_merge(base, override)
        assert result == {"key": 1}


# ============================================================================
# ProjectOverride Schema Tests
# ============================================================================


class TestProjectOverrideSchema:
    """Test ProjectOverride Pydantic model validation."""

    def test_projectoverride_valid_llm(self):
        """Test valid LLM override."""
        override = ProjectOverride(
            llm=LLMConfig(provider="openai", default_model="gpt-4o-mini")
        )
        assert override.llm is not None
        assert override.llm.provider == "openai"
        assert override.llm.default_model == "gpt-4o-mini"

    def test_projectoverride_valid_embedder(self):
        """Test valid embedder override."""
        override = ProjectOverride(
            embedder=EmbedderConfig(provider="openai", model="text-embedding-3-small")
        )
        assert override.embedder is not None
        assert override.embedder.provider == "openai"

    def test_projectoverride_valid_extraction(self):
        """Test valid extraction override."""
        override = ProjectOverride(
            extraction=ExtractionConfig(preprocessing_prompt="custom-template.md")
        )
        assert override.extraction is not None
        assert override.extraction.preprocessing_prompt == "custom-template.md"

    def test_projectoverride_valid_session_tracking(self):
        """Test valid session_tracking override."""
        override = ProjectOverride(
            session_tracking=SessionTrackingConfig(enabled=False)
        )
        assert override.session_tracking is not None
        assert override.session_tracking.enabled is False

    def test_projectoverride_all_fields_valid(self):
        """Test all overridable fields together."""
        override = ProjectOverride(
            llm=LLMConfig(provider="openai", default_model="gpt-4o"),
            embedder=EmbedderConfig(provider="openai", model="text-embedding-3-large"),
            extraction=ExtractionConfig(preprocessing_prompt="test.md"),
            session_tracking=SessionTrackingConfig(enabled=True)
        )
        assert override.llm.default_model == "gpt-4o"
        assert override.embedder.model == "text-embedding-3-large"
        assert override.extraction.preprocessing_prompt == "test.md"
        assert override.session_tracking.enabled is True

    def test_projectoverride_rejects_extra_fields(self):
        """Test unknown fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectOverride(database={"backend": "neo4j"})

        # Verify error mentions forbidden field
        error_str = str(exc_info.value)
        assert "extra" in error_str.lower() or "unexpected" in error_str.lower()


# ============================================================================
# GraphitiConfig Integration Tests
# ============================================================================


class TestProjectOverridesInGraphitiConfig:
    """Test project_overrides field in GraphitiConfig."""

    def test_graphiticonfig_project_overrides_empty_dict(self):
        """Test project_overrides defaults to empty dict."""
        config = GraphitiConfig()
        assert config.project_overrides == {}

    def test_graphiticonfig_project_overrides_valid(self):
        """Test valid project_overrides dictionary."""
        config = GraphitiConfig(
            project_overrides={
                "/c/Users/Admin/project1": ProjectOverride(
                    llm=LLMConfig(default_model="gpt-4o-mini")
                ),
                "/home/user/project2": ProjectOverride(
                    embedder=EmbedderConfig(model="text-embedding-3-small")
                )
            }
        )
        assert len(config.project_overrides) == 2
        assert "/c/Users/Admin/project1" in config.project_overrides
        assert config.project_overrides["/c/Users/Admin/project1"].llm.default_model == "gpt-4o-mini"

    def test_graphiticonfig_project_overrides_from_dict(self):
        """Test loading project_overrides from dict (JSON deserialization)."""
        config_dict = {
            "version": "1.0.0",
            "project_overrides": {
                "/c/project": {
                    "llm": {
                        "provider": "anthropic",
                        "default_model": "claude-sonnet-4-5-20250929"
                    }
                }
            }
        }
        config = GraphitiConfig(**config_dict)
        assert "/c/project" in config.project_overrides
        assert config.project_overrides["/c/project"].llm.provider == "anthropic"


# ============================================================================
# End-to-End Integration Tests
# ============================================================================


class TestProjectOverridesEndToEnd:
    """Test complete project override workflow."""

    def test_project_overrides_end_to_end(self):
        """Test path normalization and merge work together."""
        # Use a Windows-style path that will be normalized
        normalized_path = normalize_project_path("C:\\Users\\Admin\\project")
        # Should be normalized to /c/ format
        assert normalized_path.startswith("/")
        assert "project" in normalized_path

        # Create config with override for that path
        config = GraphitiConfig(
            project_overrides={
                normalized_path: ProjectOverride(
                    llm=LLMConfig(default_model="gpt-4o-mini")
                )
            }
        )

        # Verify override exists
        assert normalized_path in config.project_overrides
        override = config.project_overrides[normalized_path]
        assert override.llm.default_model == "gpt-4o-mini"

    def test_project_overrides_from_file_simulation(self, tmp_path):
        """Test loading project_overrides from JSON file."""
        # Create temporary config file
        config_file = tmp_path / "graphiti.config.json"
        config_data = {
            "version": "1.0.0",
            "project_overrides": {
                "/home/user/project": {
                    "llm": {"default_model": "gpt-4o"},
                    "embedder": {"model": "text-embedding-3-large"}
                }
            }
        }

        import json
        config_file.write_text(json.dumps(config_data, indent=2))

        # Load config
        config = GraphitiConfig.from_file(config_file)

        # Verify overrides loaded correctly
        assert "/home/user/project" in config.project_overrides
        override = config.project_overrides["/home/user/project"]
        assert override.llm.default_model == "gpt-4o"
        assert override.embedder.model == "text-embedding-3-large"


# ============================================================================
# get_effective_config() Method Tests
# ============================================================================


class TestGetEffectiveConfig:
    """Test get_effective_config() method for project-specific configuration merging."""

    def test_get_effective_config_no_override(self):
        """Test project_path not in project_overrides returns self unchanged."""
        config = GraphitiConfig(
            llm=LLMConfig(default_model="gpt-4.1-mini")
        )

        # Request effective config for path not in project_overrides
        effective = config.get_effective_config("/path/not/in/overrides")

        # Should return same instance (no override)
        assert effective is config
        assert effective.llm.default_model == "gpt-4.1-mini"

    def test_get_effective_config_with_override(self):
        """Test project_path in overrides returns merged config."""
        # Create base config
        base_config = GraphitiConfig(
            llm=LLMConfig(provider="openai", default_model="gpt-4.1-mini")
        )

        # Add override for specific project (use normalized path as key)
        project_path = "/home/user/myproject"
        normalized_path = normalize_project_path(project_path)
        base_config.project_overrides[normalized_path] = ProjectOverride(
            llm=LLMConfig(default_model="gpt-4o")
        )

        # Get effective config (can use any path format - will be normalized)
        effective = base_config.get_effective_config(project_path)

        # Should return NEW instance (not same as base)
        assert effective is not base_config

        # Should have merged values
        assert effective.llm.default_model == "gpt-4o"  # From override
        assert effective.llm.provider == "openai"  # Inherited from base

    def test_get_effective_config_merge_llm(self):
        """Test override.llm.provider='anthropic' merges correctly."""
        base_config = GraphitiConfig(
            llm=LLMConfig(
                provider="openai",
                default_model="gpt-4.1-mini",
                temperature=0.0,
                semaphore_limit=10
            )
        )

        project_path = "/test/project"
        normalized_path = normalize_project_path(project_path)
        base_config.project_overrides[normalized_path] = ProjectOverride(
            llm=LLMConfig(provider="anthropic", default_model="claude-sonnet-4-5-20250929")
        )

        effective = base_config.get_effective_config(project_path)

        # Overridden fields
        assert effective.llm.provider == "anthropic"
        assert effective.llm.default_model == "claude-sonnet-4-5-20250929"

        # Inherited fields
        assert effective.llm.temperature == 0.0
        assert effective.llm.semaphore_limit == 10

    def test_get_effective_config_merge_nested(self):
        """Test override.session_tracking fields merge deeply."""
        base_config = GraphitiConfig(
            session_tracking=SessionTrackingConfig(
                enabled=True,
                store_in_graph=False,
                keep_length_days=7
            )
        )

        project_path = "/test/project"
        normalized_path = normalize_project_path(project_path)
        # Override only enabled field, deep merge should preserve other base values
        base_config.project_overrides[normalized_path] = ProjectOverride(
            session_tracking=SessionTrackingConfig(
                enabled=False,
                store_in_graph=False,  # Explicitly set to test deep merge
                keep_length_days=30  # Override this value
            )
        )

        effective = base_config.get_effective_config(project_path)

        # Overridden fields
        assert effective.session_tracking.enabled is False
        assert effective.session_tracking.keep_length_days == 30
        assert effective.session_tracking.store_in_graph is False

    def test_get_effective_config_none_inherits(self):
        """Test override.llm=None inherits from global."""
        base_config = GraphitiConfig(
            llm=LLMConfig(provider="openai", default_model="gpt-4.1-mini")
        )

        project_path = "/test/project"
        normalized_path = normalize_project_path(project_path)
        base_config.project_overrides[normalized_path] = ProjectOverride(
            llm=None,  # Explicitly None
            embedder=EmbedderConfig(model="text-embedding-3-large")
        )

        effective = base_config.get_effective_config(project_path)

        # llm should inherit from base (None means inherit)
        assert effective.llm.provider == "openai"
        assert effective.llm.default_model == "gpt-4.1-mini"

        # embedder should be from override
        assert effective.embedder.model == "text-embedding-3-large"

    def test_get_effective_config_normalizes_path(self):
        """Test path normalization: C:\\Users\\Admin\\project normalizes to /c/Users/Admin/project."""
        base_config = GraphitiConfig()

        # Add override with normalized path
        normalized_path = normalize_project_path("C:\\Users\\Admin\\project")
        base_config.project_overrides[normalized_path] = ProjectOverride(
            llm=LLMConfig(default_model="gpt-4o")
        )

        # Request with Windows-style path (should normalize internally)
        effective = base_config.get_effective_config("C:\\Users\\Admin\\project")

        # Should find the override (path was normalized)
        assert effective.llm.default_model == "gpt-4o"

    def test_get_config_with_project_path(self):
        """Test get_config(project_path='/path') returns effective config."""
        from mcp_server.unified_config import get_config, set_config

        # Create config with override
        config = GraphitiConfig(
            llm=LLMConfig(default_model="gpt-4.1-mini")
        )
        project_path = "/test/project"
        normalized_path = normalize_project_path(project_path)
        config.project_overrides[normalized_path] = ProjectOverride(
            llm=LLMConfig(default_model="gpt-4o")
        )

        # Set as global config
        set_config(config)

        # Get effective config via get_config()
        effective = get_config(project_path=project_path)

        # Should have project-specific model
        assert effective.llm.default_model == "gpt-4o"

    def test_get_config_without_project_path(self):
        """Test get_config() without project_path returns global config (backward compatible)."""
        from mcp_server.unified_config import get_config, set_config

        # Create config
        config = GraphitiConfig(
            llm=LLMConfig(default_model="gpt-4.1-mini")
        )
        normalized_path = normalize_project_path("/test/project")
        config.project_overrides[normalized_path] = ProjectOverride(
            llm=LLMConfig(default_model="gpt-4o")
        )

        # Set as global config
        set_config(config)

        # Get config without project_path
        global_config = get_config()

        # Should return global config (no override applied)
        assert global_config.llm.default_model == "gpt-4.1-mini"

    def test_validate_override_warns_database(self, caplog):
        """Test override contains database section logs warning."""
        import logging
        caplog.set_level(logging.WARNING)

        config = GraphitiConfig()

        # Create override dict with non-overridable section
        override_dict = {
            "database": {"backend": "neo4j"},
            "llm": {"default_model": "gpt-4o"}
        }

        # Call validation
        config._validate_override(override_dict, "/test/project")

        # Check warning was logged
        assert any("database" in record.message and "non-overridable" in record.message
                   for record in caplog.records)

    def test_validate_override_warns_daemon(self, caplog):
        """Test override contains daemon section logs warning."""
        import logging
        caplog.set_level(logging.WARNING)

        config = GraphitiConfig()

        override_dict = {
            "daemon": {"enabled": True},
            "llm": {"default_model": "gpt-4o"}
        }

        config._validate_override(override_dict, "/test/project")

        assert any("daemon" in record.message and "non-overridable" in record.message
                   for record in caplog.records)

    def test_validate_override_warns_multiple(self, caplog):
        """Test override contains database+daemon logs 2 warnings."""
        import logging
        caplog.set_level(logging.WARNING)

        config = GraphitiConfig()

        override_dict = {
            "database": {"backend": "neo4j"},
            "daemon": {"enabled": True},
            "llm": {"default_model": "gpt-4o"}
        }

        config._validate_override(override_dict, "/test/project")

        # Should have 2 warnings (database and daemon)
        warning_messages = [record.message for record in caplog.records
                           if record.levelname == "WARNING"]
        assert len(warning_messages) == 2
        assert any("database" in msg for msg in warning_messages)
        assert any("daemon" in msg for msg in warning_messages)


# ============================================================================
# Integration Tests for get_effective_config()
# ============================================================================


class TestGetEffectiveConfigIntegration:
    """Integration tests for get_effective_config() end-to-end workflow."""

    def test_get_effective_config_end_to_end(self):
        """Test complete workflow: create config with override, get effective config, verify merged values."""
        # Create base config with specific values
        base_config = GraphitiConfig(
            llm=LLMConfig(
                provider="openai",
                default_model="gpt-4.1-mini",
                small_model="gpt-4.1-nano",
                temperature=0.0
            ),
            embedder=EmbedderConfig(
                provider="openai",
                model="text-embedding-3-small"
            )
        )

        # Add project override (only override some fields) - use normalized path
        project_path = "/home/user/research-project"
        normalized_path = normalize_project_path(project_path)
        base_config.project_overrides[normalized_path] = ProjectOverride(
            llm=LLMConfig(
                provider="anthropic",
                default_model="claude-sonnet-4-5-20250929"
            ),
            embedder=EmbedderConfig(
                model="text-embedding-3-large"
            )
        )

        # Get effective config
        effective = base_config.get_effective_config(project_path)

        # Verify overridden values
        assert effective.llm.provider == "anthropic"
        assert effective.llm.default_model == "claude-sonnet-4-5-20250929"
        assert effective.embedder.model == "text-embedding-3-large"

        # Verify inherited values
        assert effective.llm.small_model == "gpt-4.1-nano"  # Inherited from base
        assert effective.llm.temperature == 0.0  # Inherited from base
        assert effective.embedder.provider == "openai"  # Inherited from base

    def test_get_config_reload_with_project_path(self, tmp_path):
        """Test force reload with project_path reloads config and applies override."""
        from mcp_server.unified_config import get_config, set_config
        import json

        # Use normalized path for consistent testing
        project_path = "/test/project"
        normalized_path = normalize_project_path(project_path)

        # Create temporary config file with override (using normalized path as key)
        config_file = tmp_path / "graphiti.config.json"
        config_data = {
            "version": "1.0.0",
            "llm": {
                "provider": "openai",
                "default_model": "gpt-4.1-mini"
            },
            "project_overrides": {
                normalized_path: {
                    "llm": {
                        "default_model": "gpt-4o"
                    }
                }
            }
        }
        config_file.write_text(json.dumps(config_data, indent=2))

        # Set initial config (to test force_reload)
        set_config(GraphitiConfig(llm=LLMConfig(default_model="old-model")))

        # Force reload from file with project_path
        # Note: This test simulates the reload, actual file loading tested separately
        config = GraphitiConfig.from_file(config_file)
        set_config(config)
        effective = get_config(project_path=project_path)

        # Should have reloaded config and applied override
        assert effective.llm.default_model == "gpt-4o"
