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

    def test_normalize_path_unix(self, monkeypatch):
        """Test Unix path remains unchanged."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        result = normalize_project_path("/home/user/project")
        assert result == "/home/user/project"

    def test_normalize_path_msys(self, monkeypatch):
        """Test MSYS-style path remains unchanged."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        result = normalize_project_path("/c/Users/Admin/project")
        assert result == "/c/Users/Admin/project"

    def test_normalize_path_expanduser(self, monkeypatch):
        """Test tilde expansion works correctly."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        # Mock Path.home() to avoid actual home directory dependency
        home = "/home/testuser"
        monkeypatch.setattr(Path, "home", lambda: Path(home))

        # Manually expand ~ for test (normalize_project_path uses Path.resolve)
        result = normalize_project_path(str(Path("~/project").expanduser()))
        assert result.startswith("/")
        assert "project" in result

    def test_normalize_path_trailing_slash_removed(self, monkeypatch):
        """Test trailing slashes are removed."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        result = normalize_project_path("/home/user/project/")
        assert result == "/home/user/project"

    def test_normalize_path_relative_becomes_absolute(self, monkeypatch):
        """Test relative paths are converted to absolute."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        result = normalize_project_path("./project")
        # Should start with / (absolute path)
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
            llm=LLMConfig(provider="openai", model="gpt-4o-mini")
        )
        assert override.llm is not None
        assert override.llm.provider == "openai"
        assert override.llm.model == "gpt-4o-mini"

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
            extraction=ExtractionConfig(max_workers=2)
        )
        assert override.extraction is not None
        assert override.extraction.max_workers == 2

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
            llm=LLMConfig(provider="openai", model="gpt-4o"),
            embedder=EmbedderConfig(provider="openai", model="text-embedding-3-large"),
            extraction=ExtractionConfig(max_workers=4),
            session_tracking=SessionTrackingConfig(enabled=True)
        )
        assert override.llm.model == "gpt-4o"
        assert override.embedder.model == "text-embedding-3-large"
        assert override.extraction.max_workers == 4
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
                    llm=LLMConfig(model="gpt-4o-mini")
                ),
                "/home/user/project2": ProjectOverride(
                    embedder=EmbedderConfig(model="text-embedding-3-small")
                )
            }
        )
        assert len(config.project_overrides) == 2
        assert "/c/Users/Admin/project1" in config.project_overrides
        assert config.project_overrides["/c/Users/Admin/project1"].llm.model == "gpt-4o-mini"

    def test_graphiticonfig_project_overrides_from_dict(self):
        """Test loading project_overrides from dict (JSON deserialization)."""
        config_dict = {
            "version": "1.0.0",
            "project_overrides": {
                "/c/project": {
                    "llm": {
                        "provider": "anthropic",
                        "model": "claude-sonnet-4-5-20250929"
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

    def test_project_overrides_end_to_end(self, monkeypatch):
        """Test path normalization and merge work together."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")

        # Normalize a Windows path
        normalized_path = normalize_project_path("C:\\Users\\Admin\\project")
        assert normalized_path == "/c/Users/Admin/project"

        # Create config with override for that path
        config = GraphitiConfig(
            project_overrides={
                normalized_path: ProjectOverride(
                    llm=LLMConfig(model="gpt-4o-mini")
                )
            }
        )

        # Verify override exists
        assert normalized_path in config.project_overrides
        override = config.project_overrides[normalized_path]
        assert override.llm.model == "gpt-4o-mini"

    def test_project_overrides_from_file_simulation(self, tmp_path, monkeypatch):
        """Test loading project_overrides from JSON file."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")

        # Create temporary config file
        config_file = tmp_path / "graphiti.config.json"
        config_data = {
            "version": "1.0.0",
            "project_overrides": {
                "/home/user/project": {
                    "llm": {"model": "gpt-4o"},
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
        assert override.llm.model == "gpt-4o"
        assert override.embedder.model == "text-embedding-3-large"
