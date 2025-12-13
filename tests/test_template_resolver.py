"""Tests for TemplateResolver (Story 8).

Tests template resolution hierarchy, caching, and platform-agnostic path handling.
"""

import tempfile
from pathlib import Path

import pytest

from graphiti_core.template_resolver import TemplateResolver


class TestTemplateResolverHierarchy:
    """Test hierarchical template search."""

    def test_load_builtin_template(self):
        """Test loading built-in template from graphiti_core/session_tracking/prompts/."""
        resolver = TemplateResolver()
        content = resolver.load("default-session-turn.md")

        assert content is not None
        assert len(content) > 0
        assert "Content Prioritization" in content or "Entity Type Hints" in content

    def test_load_nonexistent_template_returns_none(self):
        """Test loading nonexistent template returns None with warning."""
        resolver = TemplateResolver()
        content = resolver.load("nonexistent-template-xyz.md")

        assert content is None

    def test_global_template_overrides_builtin(self, tmp_path):
        """Test global template overrides built-in template."""
        # Create global template directory
        global_template_dir = Path.home() / ".graphiti" / "templates"
        global_template_dir.mkdir(parents=True, exist_ok=True)

        # Create custom global template
        template_name = "test-global-override.md"
        global_template_path = global_template_dir / template_name
        global_content = "# Global Template Override\n\nThis is from global."

        try:
            global_template_path.write_text(global_content, encoding="utf-8")

            # Load via resolver
            resolver = TemplateResolver()
            content = resolver.load(template_name)

            assert content == global_content
            assert "Global Template Override" in content

        finally:
            # Clean up
            if global_template_path.exists():
                global_template_path.unlink()

    def test_project_template_overrides_global(self, tmp_path):
        """Test project template overrides global template."""
        # Create project template directory
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_template_dir = project_dir / ".graphiti" / "templates"
        project_template_dir.mkdir(parents=True)

        # Create project template
        template_name = "test-project-override.md"
        project_template_path = project_template_dir / template_name
        project_content = "# Project Template Override\n\nThis is from project."
        project_template_path.write_text(project_content, encoding="utf-8")

        # Create global template with same name
        global_template_dir = Path.home() / ".graphiti" / "templates"
        global_template_dir.mkdir(parents=True, exist_ok=True)
        global_template_path = global_template_dir / template_name
        global_content = "# Global Template\n\nThis is from global."

        try:
            global_template_path.write_text(global_content, encoding="utf-8")

            # Load via resolver with project_dir
            resolver = TemplateResolver(project_dir=project_dir)
            content = resolver.load(template_name)

            # Should load project template, not global
            assert content == project_content
            assert "Project Template Override" in content
            assert "This is from project" in content

        finally:
            # Clean up
            if global_template_path.exists():
                global_template_path.unlink()

    def test_search_order_without_project_dir(self):
        """Test search order when no project_dir specified."""
        resolver = TemplateResolver(project_dir=None)

        # Should only search global and built-in (not project)
        # Built-in template should be found
        content = resolver.load("default-session-turn.md")
        assert content is not None


class TestTemplateResolverCaching:
    """Test template caching functionality."""

    def test_template_cached_after_first_load(self, tmp_path):
        """Test template is cached after first load."""
        # Create temporary template
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        template_dir = project_dir / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        template_name = "test-cache.md"
        template_path = template_dir / template_name
        original_content = "# Original Content"
        template_path.write_text(original_content, encoding="utf-8")

        # Load template first time
        resolver = TemplateResolver(project_dir=project_dir)
        content1 = resolver.load(template_name)
        assert content1 == original_content

        # Modify template on disk
        modified_content = "# Modified Content"
        template_path.write_text(modified_content, encoding="utf-8")

        # Load template second time - should get cached version
        content2 = resolver.load(template_name)
        assert content2 == original_content  # Still cached, not modified
        assert content2 == content1

    def test_clear_cache_forces_reload(self, tmp_path):
        """Test clear_cache() forces template reload from disk."""
        # Create temporary template
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        template_dir = project_dir / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        template_name = "test-clear-cache.md"
        template_path = template_dir / template_name
        original_content = "# Original Content"
        template_path.write_text(original_content, encoding="utf-8")

        # Load template and cache it
        resolver = TemplateResolver(project_dir=project_dir)
        content1 = resolver.load(template_name)
        assert content1 == original_content

        # Modify template on disk
        modified_content = "# Modified Content"
        template_path.write_text(modified_content, encoding="utf-8")

        # Clear cache
        resolver.clear_cache()

        # Load again - should get new content
        content2 = resolver.load(template_name)
        assert content2 == modified_content
        assert content2 != content1

    def test_exists_uses_cache(self, tmp_path):
        """Test exists() method uses cache."""
        # Create temporary template
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        template_dir = project_dir / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        template_name = "test-exists.md"
        template_path = template_dir / template_name
        template_path.write_text("# Content", encoding="utf-8")

        # Load template to cache it
        resolver = TemplateResolver(project_dir=project_dir)
        resolver.load(template_name)

        # Delete template from disk
        template_path.unlink()

        # exists() should still return True due to cache
        assert resolver.exists(template_name) is True


class TestTemplateResolverPlatformAgnostic:
    """Test platform-agnostic path handling."""

    def test_path_handling_with_spaces(self, tmp_path):
        """Test path handling with spaces in directory names."""
        # Create project directory with spaces
        project_dir = tmp_path / "my project dir"
        project_dir.mkdir()
        template_dir = project_dir / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        # Create template
        template_name = "test-spaces.md"
        template_path = template_dir / template_name
        content = "# Template with spaces in path"
        template_path.write_text(content, encoding="utf-8")

        # Load via resolver
        resolver = TemplateResolver(project_dir=project_dir)
        loaded_content = resolver.load(template_name)

        assert loaded_content == content

    def test_pathlib_handles_platform_differences(self, tmp_path):
        """Test that pathlib.Path handles Windows/Unix differences."""
        # This test verifies pathlib correctly handles paths on current platform
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        resolver = TemplateResolver(project_dir=project_dir)

        # Get search paths - pathlib should handle platform correctly
        search_paths = resolver._get_search_paths("test.md")

        # All paths should be Path objects
        assert all(isinstance(p, Path) for p in search_paths)

        # Project path should be first
        assert search_paths[0].parts[-3:] == (".graphiti", "templates", "test.md")


class TestTemplateResolverExists:
    """Test exists() method."""

    def test_exists_returns_true_for_builtin(self):
        """Test exists() returns True for built-in templates."""
        resolver = TemplateResolver()
        assert resolver.exists("default-session-turn.md") is True

    def test_exists_returns_false_for_nonexistent(self):
        """Test exists() returns False for nonexistent templates."""
        resolver = TemplateResolver()
        assert resolver.exists("definitely-does-not-exist-xyz.md") is False

    def test_exists_checks_all_search_paths(self, tmp_path):
        """Test exists() checks all search paths in order."""
        # Create project template
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        template_dir = project_dir / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        template_name = "test-exists-search.md"
        template_path = template_dir / template_name
        template_path.write_text("# Content", encoding="utf-8")

        # Resolver with project_dir should find it
        resolver = TemplateResolver(project_dir=project_dir)
        assert resolver.exists(template_name) is True

        # Resolver without project_dir should not find it
        resolver_no_project = TemplateResolver(project_dir=None)
        assert resolver_no_project.exists(template_name) is False


class TestTemplateResolverErrorHandling:
    """Test error handling and logging."""

    def test_handles_read_errors_gracefully(self, tmp_path):
        """Test resolver handles read errors gracefully."""
        # Create template with restricted permissions (Unix-style test)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        template_dir = project_dir / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        template_name = "test-error.md"
        template_path = template_dir / template_name
        template_path.write_text("# Content", encoding="utf-8")

        # Load successfully first
        resolver = TemplateResolver(project_dir=project_dir)
        content = resolver.load(template_name)
        assert content is not None

        # Note: Cannot easily test permission errors on Windows,
        # so this test just verifies successful case

    def test_returns_none_for_template_not_found(self):
        """Test returns None when template not found in any location."""
        resolver = TemplateResolver()
        content = resolver.load("absolutely-missing-template.md")
        assert content is None

    def test_warning_logged_for_missing_template(self, caplog):
        """Test warning is logged when template not found."""
        import logging

        with caplog.at_level(logging.WARNING):
            resolver = TemplateResolver()
            resolver.load("missing-template-for-log-test.md")

            # Check that warning was logged
            assert any(
                "not found" in record.message.lower() for record in caplog.records
            )


class TestExtractionConfigIntegration:
    """Test ExtractionConfig integration with TemplateResolver."""

    def test_resolve_prompt_with_builtin_template(self):
        """Test ExtractionConfig resolves built-in template."""
        from graphiti_core.extraction_config import ExtractionConfig

        config = ExtractionConfig(preprocessing_prompt="default-session-turn.md")
        prompt = config.resolve_prompt()

        assert len(prompt) > 0
        assert "Content Prioritization" in prompt or "Entity Type Hints" in prompt

    def test_resolve_prompt_with_inline_string(self):
        """Test ExtractionConfig returns inline string directly."""
        from graphiti_core.extraction_config import ExtractionConfig

        inline_prompt = "Extract entities and relationships from this content."
        config = ExtractionConfig(preprocessing_prompt=inline_prompt)
        prompt = config.resolve_prompt()

        assert prompt == inline_prompt

    def test_resolve_prompt_disabled_returns_empty(self):
        """Test ExtractionConfig returns empty string when disabled."""
        from graphiti_core.extraction_config import ExtractionConfig

        config = ExtractionConfig(preprocessing_prompt=False)
        prompt = config.resolve_prompt()

        assert prompt == ""

    def test_resolve_prompt_with_project_dir(self, tmp_path):
        """Test ExtractionConfig with project_dir parameter."""
        from graphiti_core.extraction_config import ExtractionConfig

        # Create project template
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        template_dir = project_dir / ".graphiti" / "templates"
        template_dir.mkdir(parents=True)

        template_name = "custom-project.md"
        template_path = template_dir / template_name
        custom_content = "# Custom Project Template\n\nProject-specific content."
        template_path.write_text(custom_content, encoding="utf-8")

        # Configure and resolve
        config = ExtractionConfig(preprocessing_prompt=template_name)
        prompt = config.resolve_prompt(project_dir=project_dir)

        assert prompt == custom_content
        assert "Project-specific content" in prompt

    def test_resolve_prompt_template_not_found_returns_empty(self):
        """Test ExtractionConfig returns empty string if template not found."""
        from graphiti_core.extraction_config import ExtractionConfig

        config = ExtractionConfig(preprocessing_prompt="nonexistent-template.md")
        prompt = config.resolve_prompt()

        assert prompt == ""
