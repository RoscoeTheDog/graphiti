"""Tests for template system (Story 11).

Tests template resolution hierarchy, packaged templates, and MessageSummarizer integration.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from graphiti_core.session_tracking.message_summarizer import (
    MessageSummarizer,
    resolve_template_path,
)
from graphiti_core.session_tracking.prompts import DEFAULT_TEMPLATES


class TestTemplateResolution:
    """Test template resolution hierarchy."""

    def test_inline_prompt(self):
        """Test inline prompt (not .md file) returns as-is."""
        template_ref = "Summarize: {content}"
        content, is_inline = resolve_template_path(template_ref)

        assert is_inline is True
        assert content == template_ref

    def test_built_in_template(self):
        """Test built-in template loads from DEFAULT_TEMPLATES."""
        template_ref = "default-tool-content.md"
        content, is_inline = resolve_template_path(template_ref)

        assert is_inline is False
        assert "{content}" in content
        assert "{context}" in content

    def test_packaged_template(self, tmp_path):
        """Test packaged template loads from prompts/ directory."""
        template_ref = "default-user-messages.md"
        content, is_inline = resolve_template_path(template_ref)

        assert is_inline is False
        assert "{content}" in content
        assert "{context}" in content

    def test_global_template_overrides_built_in(self, tmp_path):
        """Test global template overrides built-in."""
        # Create global template
        global_template_dir = Path.home() / ".graphiti" / "auto-tracking" / "templates"
        global_template_dir.mkdir(parents=True, exist_ok=True)
        global_template_path = global_template_dir / "custom-template.md"
        global_template_path.write_text("Global template: {content}", encoding="utf-8")

        try:
            template_ref = "custom-template.md"
            content, is_inline = resolve_template_path(template_ref)

            assert is_inline is False
            assert content == "Global template: {content}"
        finally:
            # Cleanup
            global_template_path.unlink(missing_ok=True)

    def test_project_template_overrides_global(self, tmp_path):
        """Test project template overrides global."""
        # Create project template
        project_root = tmp_path
        project_template_dir = project_root / ".graphiti" / "auto-tracking" / "templates"
        project_template_dir.mkdir(parents=True, exist_ok=True)
        project_template_path = project_template_dir / "custom-template.md"
        project_template_path.write_text("Project template: {content}", encoding="utf-8")

        template_ref = "custom-template.md"
        content, is_inline = resolve_template_path(template_ref, project_root=project_root)

        assert is_inline is False
        assert content == "Project template: {content}"

    def test_absolute_path_used_directly(self, tmp_path):
        """Test absolute path is used directly."""
        # Create temp template file
        template_path = tmp_path / "absolute-template.md"
        template_path.write_text("Absolute template: {content}", encoding="utf-8")

        template_ref = str(template_path)
        content, is_inline = resolve_template_path(template_ref)

        assert is_inline is False
        assert content == "Absolute template: {content}"

    def test_template_not_found_raises_error(self):
        """Test missing template raises FileNotFoundError."""
        template_ref = "nonexistent-template.md"

        with pytest.raises(FileNotFoundError) as exc_info:
            resolve_template_path(template_ref)

        assert "not found in hierarchy" in str(exc_info.value)


class TestMessageSummarizerTemplates:
    """Test MessageSummarizer with template system."""

    @pytest.mark.asyncio
    async def test_summarize_with_inline_template(self):
        """Test summarizing with inline template."""
        llm_client = AsyncMock()
        llm_client.generate_response = AsyncMock(return_value="Test summary")

        summarizer = MessageSummarizer(llm_client)

        template = "Summarize this: {content}"
        result = await summarizer.summarize("Test content", template=template)

        assert result == "Test summary"
        # Verify prompt was formatted with template
        call_args = llm_client.generate_response.call_args
        messages = call_args.kwargs["messages"]
        assert "Summarize this: Test content" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_summarize_with_built_in_template(self):
        """Test summarizing with built-in template."""
        llm_client = AsyncMock()
        llm_client.generate_response = AsyncMock(return_value="Test summary")

        summarizer = MessageSummarizer(llm_client)

        template = "default-tool-content.md"
        result = await summarizer.summarize("Test content", context="test tool", template=template)

        assert result == "Test summary"
        # Verify prompt was formatted with template variables
        call_args = llm_client.generate_response.call_args
        messages = call_args.kwargs["messages"]
        assert "Test content" in messages[0]["content"]
        assert "test tool" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_template_caching(self):
        """Test template caching works correctly."""
        llm_client = AsyncMock()
        llm_client.generate_response = AsyncMock(return_value="Test summary")

        summarizer = MessageSummarizer(llm_client)

        template = "default-tool-content.md"

        # First call - should resolve and cache
        await summarizer.summarize("Content 1", template=template)
        assert template in summarizer.template_cache

        # Second call - should use cache
        await summarizer.summarize("Content 2", template=template)
        # Template should still be cached
        assert template in summarizer.template_cache

    @pytest.mark.asyncio
    async def test_template_variable_substitution(self):
        """Test template variables are substituted correctly."""
        llm_client = AsyncMock()
        llm_client.generate_response = AsyncMock(return_value="Test summary")

        summarizer = MessageSummarizer(llm_client)

        template = "Context: {context}, Content: {content}"
        await summarizer.summarize("My content", context="my context", template=template)

        call_args = llm_client.generate_response.call_args
        messages = call_args.kwargs["messages"]
        assert "Context: my context, Content: My content" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_default_prompt_without_template(self):
        """Test default prompt is used when no template specified."""
        llm_client = AsyncMock()
        llm_client.generate_response = AsyncMock(return_value="Test summary")

        summarizer = MessageSummarizer(llm_client)

        result = await summarizer.summarize("Test content", context="test context")

        assert result == "Test summary"
        # Verify default prompt was used
        call_args = llm_client.generate_response.call_args
        messages = call_args.kwargs["messages"]
        assert "Summarize this message" in messages[0]["content"]
        assert "test context" in messages[0]["content"]


class TestEnsureDefaultTemplatesExist:
    """Test ensure_default_templates_exist function."""

    def test_templates_created_on_first_run(self, tmp_path, monkeypatch):
        """Test templates are created on first run."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Import and run function
        from mcp_server.graphiti_mcp_server import ensure_default_templates_exist

        ensure_default_templates_exist()

        # Verify templates were created
        templates_dir = tmp_path / ".graphiti" / "auto-tracking" / "templates"
        assert templates_dir.exists()

        for filename in DEFAULT_TEMPLATES.keys():
            template_path = templates_dir / filename
            assert template_path.exists()
            content = template_path.read_text(encoding="utf-8")
            assert "{content}" in content

    def test_no_overwrite_on_subsequent_runs(self, tmp_path, monkeypatch):
        """Test templates are not overwritten on subsequent runs."""
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create custom template first
        templates_dir = tmp_path / ".graphiti" / "auto-tracking" / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        custom_template = templates_dir / "default-tool-content.md"
        custom_content = "Custom content: {content}"
        custom_template.write_text(custom_content, encoding="utf-8")

        # Run function
        from mcp_server.graphiti_mcp_server import ensure_default_templates_exist

        ensure_default_templates_exist()

        # Verify custom content was not overwritten
        assert custom_template.read_text(encoding="utf-8") == custom_content
