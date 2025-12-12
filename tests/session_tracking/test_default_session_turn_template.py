"""Tests for Default Session Turn Template.

Tests Story 3 acceptance criteria:
- AC-3.1: Template file exists at built-in location
- AC-3.2: Template contains HIGH/MEDIUM/LOW priority content guidance
- AC-3.3: Template contains entity type hints (File, Tool, Error, Decision, Concept)
- AC-3.4: Template contains relationship extraction guidance
- AC-3.5: Template is under 500 tokens to minimize prompt overhead

Additional coverage:
- Template is registered in DEFAULT_TEMPLATES mapping
- Template content structure and completeness
- Template can be loaded and used
"""

import pytest
import tiktoken
from pathlib import Path

from graphiti_core.session_tracking.prompts import (
    DEFAULT_SESSION_TURN_TEMPLATE,
    DEFAULT_TEMPLATES,
)


class TestDefaultSessionTurnTemplate:
    """Test DEFAULT_SESSION_TURN_TEMPLATE constant and structure."""

    def test_template_registered_in_mapping(self):
        """AC-3.1: Test template is registered in DEFAULT_TEMPLATES."""
        assert "default-session-turn.md" in DEFAULT_TEMPLATES
        assert DEFAULT_TEMPLATES["default-session-turn.md"] == DEFAULT_SESSION_TURN_TEMPLATE

    def test_template_file_exists(self):
        """AC-3.1: Test template file exists at built-in location."""
        template_path = Path("graphiti_core/session_tracking/prompts/default-session-turn.md")
        assert template_path.exists(), f"Template file not found: {template_path}"

    def test_template_under_500_tokens(self):
        """AC-3.5: Test template content is under 500 tokens."""
        enc = tiktoken.encoding_for_model("gpt-4")
        token_count = len(enc.encode(DEFAULT_SESSION_TURN_TEMPLATE))
        assert token_count < 500, f"Template has {token_count} tokens (must be < 500)"

    def test_template_contains_priority_guidance(self):
        """AC-3.2: Test template contains HIGH/MEDIUM/LOW priority guidance."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        assert "HIGH Priority" in template, "Missing HIGH priority section"
        assert "MEDIUM Priority" in template, "Missing MEDIUM priority section"
        assert "LOW Priority" in template, "Missing LOW priority section"

    def test_template_contains_entity_type_hints(self):
        """AC-3.3: Test template contains entity type hints."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        required_entity_types = ["File", "Tool", "Error", "Decision", "Concept"]
        for entity_type in required_entity_types:
            assert entity_type in template, f"Missing entity type: {entity_type}"

    def test_template_contains_relationship_guidance(self):
        """AC-3.4: Test template contains relationship extraction guidance."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        assert "Relationship Guidance" in template, "Missing relationship guidance section"
        # Check for specific relationship patterns
        assert "File-Tool" in template, "Missing File-Tool relationship"
        assert "Error-File" in template, "Missing Error-File relationship"
        assert "Decision-Concept" in template, "Missing Decision-Concept relationship"
        assert "Tool-Error" in template, "Missing Tool-Error relationship"
        assert "Concept-File" in template, "Missing Concept-File relationship"

    def test_template_has_required_sections(self):
        """Test template has all required sections."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        required_sections = [
            "Content Prioritization",
            "Entity Type Hints",
            "Relationship Guidance",
            "Template Variables"
        ]
        for section in required_sections:
            assert section in template, f"Missing section: {section}"

    def test_template_has_variable_placeholders(self):
        """Test template has variable placeholders for content injection."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        assert "{context}" in template, "Missing {context} placeholder"
        assert "{content}" in template, "Missing {content} placeholder"

    def test_template_is_non_empty_string(self):
        """Test template is a non-empty string."""
        assert isinstance(DEFAULT_SESSION_TURN_TEMPLATE, str)
        assert len(DEFAULT_SESSION_TURN_TEMPLATE) > 0

    def test_template_structure_is_well_formed(self):
        """Test template follows markdown structure."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        # Should have markdown headers
        assert "##" in template, "Template should use markdown headers"
        # Should have bullet lists
        assert "-" in template or "*" in template, "Template should use bullet lists"


class TestTemplateContentQuality:
    """Test template content quality and completeness."""

    def test_priority_sections_have_guidance(self):
        """Test each priority level has actionable guidance."""
        template = DEFAULT_SESSION_TURN_TEMPLATE

        # Check HIGH priority has specific guidance
        high_section_start = template.find("HIGH Priority")
        medium_section_start = template.find("MEDIUM Priority")
        high_section = template[high_section_start:medium_section_start]
        assert "always extract" in high_section.lower(), "HIGH priority should say 'always extract'"

        # Check MEDIUM priority has specific guidance
        low_section_start = template.find("LOW Priority")
        medium_section = template[medium_section_start:low_section_start]
        assert "if significant" in medium_section.lower(), "MEDIUM priority should say 'if significant'"

        # Check LOW priority has specific guidance
        entity_hints_start = template.find("Entity Type Hints")
        low_section = template[low_section_start:entity_hints_start]
        assert "only if" in low_section.lower(), "LOW priority should say 'only if'"

    def test_entity_hints_have_descriptions(self):
        """Test entity type hints include descriptions."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        entity_section_start = template.find("Entity Type Hints")
        relationship_section_start = template.find("Relationship Guidance")
        entity_section = template[entity_section_start:relationship_section_start]

        # Each entity type should have a description (bold format: **Entity**:)
        assert "**File**:" in entity_section, "File entity should have description"
        assert "**Tool**:" in entity_section, "Tool entity should have description"
        assert "**Error**:" in entity_section, "Error entity should have description"
        assert "**Decision**:" in entity_section, "Decision entity should have description"
        assert "**Concept**:" in entity_section, "Concept entity should have description"

    def test_relationship_patterns_are_specific(self):
        """Test relationship guidance includes specific patterns."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        relationship_section_start = template.find("Relationship Guidance")
        template_vars_start = template.find("Template Variables")
        relationship_section = template[relationship_section_start:template_vars_start]

        # Should explain what each relationship captures
        assert "capture" in relationship_section.lower() or "extract" in relationship_section.lower()


class TestTemplateTokenEfficiency:
    """Test template token efficiency and optimization."""

    def test_template_within_budget_with_margin(self):
        """Test template has safety margin under 500 token limit."""
        enc = tiktoken.encoding_for_model("gpt-4")
        token_count = len(enc.encode(DEFAULT_SESSION_TURN_TEMPLATE))
        # Should be well under 500 to leave room for template variable substitution
        assert token_count <= 450, f"Template should be <= 450 tokens (has {token_count})"

    def test_template_uses_concise_language(self):
        """Test template uses concise, actionable language."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        # Should not have excessive verbosity
        lines = template.split("\n")
        for line in lines:
            if line.strip() and not line.startswith("#"):
                # Content lines should be reasonably short (< 100 chars for readability)
                assert len(line) < 150, f"Line too long: {line[:50]}..."


class TestTemplateIntegration:
    """Integration tests for template loading and usage."""

    def test_template_matches_file_content(self):
        """Test template constant matches file on disk."""
        template_path = Path("graphiti_core/session_tracking/prompts/default-session-turn.md")
        if template_path.exists():
            file_content = template_path.read_text(encoding="utf-8")
            # Template constant should match file (allowing for line ending differences)
            template_normalized = DEFAULT_SESSION_TURN_TEMPLATE.replace("\r\n", "\n").strip()
            file_normalized = file_content.replace("\r\n", "\n").strip()
            assert template_normalized == file_normalized, "Template constant doesn't match file"

    def test_template_can_be_formatted(self):
        """Test template placeholders can be substituted."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        # Test basic string formatting
        formatted = template.format(context="test context", content="test content")
        assert "{context}" not in formatted
        assert "{content}" not in formatted
        assert "test context" in formatted
        assert "test content" in formatted


class TestTemplateSecurity:
    """Security tests for template content."""

    def test_template_contains_no_sensitive_info(self):
        """Test template does not contain sensitive information."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        # Check for common sensitive patterns
        sensitive_patterns = [
            "password",
            "api_key",
            "secret",
            "token",
            "credential",
            "@example.com",
            "127.0.0.1",
            "localhost"
        ]
        template_lower = template.lower()
        for pattern in sensitive_patterns:
            assert pattern not in template_lower, f"Template contains sensitive pattern: {pattern}"

    def test_template_has_no_injection_vectors(self):
        """Test template cannot be used for prompt injection."""
        template = DEFAULT_SESSION_TURN_TEMPLATE
        # Template should not contain instructions that could be exploited
        injection_patterns = [
            "ignore previous",
            "ignore all",
            "disregard",
            "instead of",
            "forget"
        ]
        template_lower = template.lower()
        for pattern in injection_patterns:
            assert pattern not in template_lower, f"Template contains injection pattern: {pattern}"
