"""Unit tests for ExtractionConfig."""

import tempfile
from pathlib import Path

import pytest

from graphiti_core.extraction_config import ExtractionConfig


class TestExtractionConfig:
    """Test ExtractionConfig class."""

    def test_is_enabled_default(self):
        """Test is_enabled with default (False)."""
        config = ExtractionConfig()
        assert config.is_enabled() is False

    def test_is_enabled_false(self):
        """Test is_enabled with explicit False."""
        config = ExtractionConfig(preprocessing_prompt=False)
        assert config.is_enabled() is False

    def test_is_enabled_none(self):
        """Test is_enabled with None."""
        config = ExtractionConfig(preprocessing_prompt=None)
        assert config.is_enabled() is False

    def test_is_enabled_template(self):
        """Test is_enabled with template file."""
        config = ExtractionConfig(preprocessing_prompt="template.md")
        assert config.is_enabled() is True

    def test_is_enabled_inline(self):
        """Test is_enabled with inline prompt."""
        config = ExtractionConfig(preprocessing_prompt="Extract entities.")
        assert config.is_enabled() is True

    def test_is_enabled_empty_string(self):
        """Test is_enabled with empty string."""
        config = ExtractionConfig(preprocessing_prompt="")
        assert config.is_enabled() is False


class TestResolvePrompt:
    """Test resolve_prompt method."""

    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory with test templates."""
        temp_dir = tempfile.mkdtemp()
        template_dir = Path(temp_dir) / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        # Create test templates
        test_template = template_dir / "test-template.md"
        test_template.write_text("# Test Template\n\nThis is a test preprocessing prompt.")

        yield temp_dir, test_template

        # Cleanup
        test_template.unlink()
        template_dir.rmdir()
        (Path(temp_dir) / ".graphiti").rmdir()
        Path(temp_dir).rmdir()

    def test_resolve_prompt_disabled_false(self):
        """Test resolve_prompt returns empty string when disabled (False)."""
        config = ExtractionConfig(preprocessing_prompt=False)
        result = config.resolve_prompt()
        assert result == ""

    def test_resolve_prompt_disabled_none(self):
        """Test resolve_prompt returns empty string when disabled (None)."""
        config = ExtractionConfig(preprocessing_prompt=None)
        result = config.resolve_prompt()
        assert result == ""

    def test_resolve_prompt_inline_prompt(self):
        """Test resolve_prompt returns inline prompt directly."""
        inline_prompt = "Consider session context when extracting entities."
        config = ExtractionConfig(preprocessing_prompt=inline_prompt)
        result = config.resolve_prompt()
        assert result == inline_prompt

    def test_resolve_prompt_template_exists(self, temp_template_dir):
        """Test resolve_prompt loads template from hierarchy."""
        project_dir, test_template = temp_template_dir

        config = ExtractionConfig(preprocessing_prompt="test-template.md")
        result = config.resolve_prompt(project_dir=Path(project_dir))

        assert result != ""
        assert "Test Template" in result
        assert "test preprocessing prompt" in result

    def test_resolve_prompt_template_not_found(self):
        """Test resolve_prompt returns empty string when template not found."""
        config = ExtractionConfig(preprocessing_prompt="nonexistent-template.md")
        result = config.resolve_prompt()

        # Graceful degradation: missing template returns empty string
        assert result == ""

    def test_resolve_prompt_builtin_template(self):
        """Test resolve_prompt loads built-in template."""
        # Use the default session turn template that should exist
        config = ExtractionConfig(preprocessing_prompt="default-session-turn.md")
        result = config.resolve_prompt()

        # Should load successfully from built-in location
        assert result != ""
        assert len(result) > 0

    def test_resolve_prompt_template_detection(self):
        """Test template vs inline prompt detection logic."""
        # Template files (end with .md)
        config_md = ExtractionConfig(preprocessing_prompt="template.md")
        assert config_md.preprocessing_prompt.endswith(".md")

        # Template files (contain path separator)
        config_path = ExtractionConfig(preprocessing_prompt="path/to/template.md")
        assert "/" in config_path.preprocessing_prompt

        # Inline prompts (no .md extension, no path separator)
        config_inline = ExtractionConfig(preprocessing_prompt="Extract entities from text.")
        prompt = config_inline.preprocessing_prompt
        assert not prompt.endswith(".md")
        assert "/" not in prompt
        assert "\\" not in prompt

    def test_resolve_prompt_with_project_dir(self, temp_template_dir):
        """Test resolve_prompt respects project_dir parameter."""
        project_dir, test_template = temp_template_dir

        config = ExtractionConfig(preprocessing_prompt="test-template.md")

        # Should find template in project directory
        result_with_dir = config.resolve_prompt(project_dir=Path(project_dir))
        assert result_with_dir != ""
        assert "Test Template" in result_with_dir

    def test_resolve_prompt_without_project_dir(self):
        """Test resolve_prompt without project_dir (global + builtin only)."""
        config = ExtractionConfig(preprocessing_prompt="default-session-turn.md")

        # Should still find built-in template
        result = config.resolve_prompt(project_dir=None)
        assert result != ""


class TestExtractionConfigModels:
    """Test ExtractionConfig model validation."""

    def test_default_values(self):
        """Test default values are set correctly."""
        config = ExtractionConfig()
        assert config.preprocessing_prompt is False
        assert config.preprocessing_mode == "prepend"

    def test_valid_modes(self):
        """Test valid preprocessing modes."""
        config_prepend = ExtractionConfig(
            preprocessing_prompt="template.md", preprocessing_mode="prepend"
        )
        assert config_prepend.preprocessing_mode == "prepend"

        config_append = ExtractionConfig(
            preprocessing_prompt="template.md", preprocessing_mode="append"
        )
        assert config_append.preprocessing_mode == "append"

    def test_invalid_mode_raises_error(self):
        """Test invalid preprocessing mode raises validation error."""
        with pytest.raises(ValueError):
            ExtractionConfig(
                preprocessing_prompt="template.md",
                preprocessing_mode="invalid",  # type: ignore
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
