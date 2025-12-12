"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""Tests for template updates (Story 13).

This module tests the template updates made in Story 13:
- default-user-messages.md length constraint updates
- default-agent-messages.md length constraint updates
- default-session-summary.md creation and placeholder verification
- Template consistency between .md files and prompts.py constants
"""

import os
import re
from pathlib import Path

import pytest

from graphiti_core.session_tracking import prompts
from graphiti_core.session_tracking.prompt_builder import build_extraction_prompt
from graphiti_core.session_tracking.summarizer import SessionSummarySchema


class TestUserMessagesTemplate:
    """Tests for default-user-messages.md template."""

    def test_user_messages_file_exists(self):
        """Verify default-user-messages.md file exists."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-user-messages.md"
        )
        assert template_path.exists(), "default-user-messages.md should exist"

    def test_user_messages_length_constraint(self):
        """Verify default-user-messages.md contains '2 paragraphs or less' text."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-user-messages.md"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # AC-13.1: Should contain '2 paragraphs or less'
        assert (
            "2 paragraphs or less" in content
        ), "User messages template should specify '2 paragraphs or less'"

        # Should not contain old '1-2 sentences' text
        assert (
            "1-2 sentences" not in content
        ), "User messages template should not contain old '1-2 sentences' text"

    def test_user_messages_prompts_constant_match(self):
        """Verify prompts.py DEFAULT_USER_MESSAGES_TEMPLATE matches .md file."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-user-messages.md"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Get constant from prompts.py
        constant_content = prompts.DEFAULT_USER_MESSAGES_TEMPLATE

        # Should match (with normalized whitespace)
        assert (
            file_content.strip() == constant_content.strip()
        ), "DEFAULT_USER_MESSAGES_TEMPLATE constant should match .md file content"


class TestAgentMessagesTemplate:
    """Tests for default-agent-messages.md template."""

    def test_agent_messages_file_exists(self):
        """Verify default-agent-messages.md file exists."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-agent-messages.md"
        )
        assert template_path.exists(), "default-agent-messages.md should exist"

    def test_agent_messages_length_constraint(self):
        """Verify default-agent-messages.md contains '2 paragraphs or less' text."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-agent-messages.md"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # AC-13.2: Should contain '2 paragraphs or less'
        assert (
            "2 paragraphs or less" in content
        ), "Agent messages template should specify '2 paragraphs or less'"

    def test_agent_messages_prompts_constant_match(self):
        """Verify prompts.py DEFAULT_AGENT_MESSAGES_TEMPLATE matches .md file."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-agent-messages.md"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Get constant from prompts.py
        constant_content = prompts.DEFAULT_AGENT_MESSAGES_TEMPLATE

        # Should match (with normalized whitespace)
        assert (
            file_content.strip() == constant_content.strip()
        ), "DEFAULT_AGENT_MESSAGES_TEMPLATE constant should match .md file content"


class TestSessionSummaryTemplate:
    """Tests for default-session-summary.md template."""

    def test_session_summary_file_exists(self):
        """Verify default-session-summary.md file exists."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-session-summary.md"
        )
        # AC-13.3: File should exist
        assert template_path.exists(), "default-session-summary.md should exist"

    def test_session_summary_required_placeholders(self):
        """Verify default-session-summary.md contains required placeholders."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-session-summary.md"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # AC-13.3: Should contain required placeholders
        required_placeholders = [
            "{activity_profile}",
            "{dynamic_extraction_instructions}",
            "{content}",
        ]

        for placeholder in required_placeholders:
            assert (
                placeholder in content
            ), f"Session summary template should contain {placeholder} placeholder"

    def test_session_summary_activity_profile_reference(self):
        """Verify session summary template references activity profile when available."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-session-summary.md"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # AC-13.4: Should reference activity profile
        assert (
            "{activity_profile}" in content
        ), "Session summary template should reference activity profile placeholder"

    def test_session_summary_prompts_constant_match(self):
        """Verify prompts.py DEFAULT_SESSION_SUMMARY_TEMPLATE matches .md file."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "graphiti_core"
            / "session_tracking"
            / "prompts"
            / "default-session-summary.md"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Get constant from prompts.py
        constant_content = prompts.DEFAULT_SESSION_SUMMARY_TEMPLATE

        # Should match (with normalized whitespace)
        assert (
            file_content.strip() == constant_content.strip()
        ), "DEFAULT_SESSION_SUMMARY_TEMPLATE constant should match .md file content"


class TestPromptsModuleConsistency:
    """Tests for prompts.py module consistency."""

    def test_all_templates_in_default_templates_dict(self):
        """Verify prompts.py DEFAULT_TEMPLATES contains all three templates."""
        # Should have at least the three template names as keys
        required_templates = {
            "default-user-messages.md",
            "default-agent-messages.md",
            "default-session-summary.md",
        }

        assert (
            required_templates.issubset(set(prompts.DEFAULT_TEMPLATES.keys()))
        ), "DEFAULT_TEMPLATES should contain all three required template filenames"

    def test_default_templates_content_matches_constants(self):
        """Verify DEFAULT_TEMPLATES dictionary content matches individual constants."""
        # User messages template
        assert (
            prompts.DEFAULT_TEMPLATES["default-user-messages.md"]
            == prompts.DEFAULT_USER_MESSAGES_TEMPLATE
        ), "DEFAULT_TEMPLATES['default-user-messages.md'] should match constant"

        # Agent messages template
        assert (
            prompts.DEFAULT_TEMPLATES["default-agent-messages.md"]
            == prompts.DEFAULT_AGENT_MESSAGES_TEMPLATE
        ), "DEFAULT_TEMPLATES['default-agent-messages.md'] should match constant"

        # Session summary template
        assert (
            prompts.DEFAULT_TEMPLATES["default-session-summary.md"]
            == prompts.DEFAULT_SESSION_SUMMARY_TEMPLATE
        ), "DEFAULT_TEMPLATES['default-session-summary.md'] should match constant"


class TestTemplateLoadingIntegration:
    """Integration tests for template loading system."""

    def test_all_templates_can_be_loaded(self):
        """Verify template loading system can load all three templates successfully."""
        # All templates should be accessible from DEFAULT_TEMPLATES
        for template_name in [
            "default-user-messages.md",
            "default-agent-messages.md",
            "default-session-summary.md",
        ]:
            template_content = prompts.DEFAULT_TEMPLATES.get(template_name)
            assert (
                template_content is not None
            ), f"Template {template_name} should be loadable"
            assert (
                len(template_content) > 0
            ), f"Template {template_name} should have content"

    def test_session_template_aligns_with_schema(self):
        """Verify new session template format aligns with SessionSummarySchema."""
        template_content = prompts.DEFAULT_SESSION_SUMMARY_TEMPLATE

        # Should have placeholders that align with schema fields
        # The template uses dynamic_extraction_instructions which is populated
        # based on SessionSummarySchema fields
        assert (
            "{dynamic_extraction_instructions}" in template_content
        ), "Template should have dynamic extraction instructions placeholder"

        # Verify SessionSummarySchema has expected core fields
        schema_fields = SessionSummarySchema.model_fields.keys()
        core_fields = {
            "completed_tasks",
            "key_decisions",
            "errors_resolved",
            "config_changes",
            "test_results",
            "files_modified",
            "next_steps",
            "blocked_items",
            "documentation_referenced",
        }

        assert (
            core_fields.issubset(schema_fields)
        ), "SessionSummarySchema should have all core expected fields"

    def test_activity_profile_placeholder_integration(self):
        """Verify activity profile placeholder works with prompt_builder.py."""
        # This tests the integration with prompt_builder.py
        # The activity_profile placeholder should be replaced by prompt_builder
        from graphiti_core.session_tracking.activity_vector import ActivityVector

        # Create a sample activity vector
        activity = ActivityVector(
            code_writing=0.8,
            debugging=0.2,
            research=0.0,
            discussion=0.0,
            documentation=0.0,
            testing=0.0,
        )

        # Build a prompt with activity profile (simulating real usage)
        # This should not raise an error and should format correctly
        try:
            # The build_extraction_prompt function uses the correct parameter name
            prompt = build_extraction_prompt(
                activity=activity,
                content="Sample session content",
            )

            # Verify the prompt was built successfully
            assert len(prompt) > 0, "Prompt should be generated successfully"

            # The activity profile should be included in the generated prompt
            # (as formatted by prompt_builder)
            assert (
                "code_writing" in prompt.lower()
                or "session activities" in prompt.lower()
                or "activity profile" in prompt.lower()
                or "coding" in prompt.lower()
            ), "Generated prompt should include activity information"

        except Exception as e:
            pytest.fail(f"Activity profile integration failed: {e}")


class TestTemplateSecurity:
    """Security tests for template content."""

    def test_no_credential_leakage(self):
        """Verify no credential leakage in template content."""
        # Check all template files for common credential patterns
        credential_patterns = [
            r"sk-[a-zA-Z0-9]{20,}",  # API keys
            r"password\s*[:=]\s*['\"][^'\"]+['\"]",  # Hardcoded passwords
            r"token\s*[:=]\s*['\"][^'\"]+['\"]",  # Hardcoded tokens
            r"secret\s*[:=]\s*['\"][^'\"]+['\"]",  # Hardcoded secrets
        ]

        templates = [
            prompts.DEFAULT_USER_MESSAGES_TEMPLATE,
            prompts.DEFAULT_AGENT_MESSAGES_TEMPLATE,
            prompts.DEFAULT_SESSION_SUMMARY_TEMPLATE,
        ]

        for template in templates:
            for pattern in credential_patterns:
                matches = re.findall(pattern, template, re.IGNORECASE)
                assert (
                    len(matches) == 0
                ), f"Template should not contain credentials matching pattern: {pattern}"

    def test_template_placeholders_properly_escaped(self):
        """Verify template placeholders are properly escaped."""
        # Placeholders should use curly braces but not be executable code
        templates = {
            "user": prompts.DEFAULT_USER_MESSAGES_TEMPLATE,
            "agent": prompts.DEFAULT_AGENT_MESSAGES_TEMPLATE,
            "session": prompts.DEFAULT_SESSION_SUMMARY_TEMPLATE,
        }

        for name, template in templates.items():
            # Should not contain executable code patterns
            dangerous_patterns = [
                r"\$\{.*?\}",  # Shell variable expansion
                r"<\?.*?\?>",  # PHP-style code execution
                r"<%.*?%>",  # Template code execution
                r"{{.*?}}",  # Jinja2 code execution (should use single braces)
            ]

            for pattern in dangerous_patterns:
                matches = re.findall(pattern, template)
                assert (
                    len(matches) == 0
                ), f"{name} template should not contain executable code pattern: {pattern}"

            # Should only use safe placeholder format: {variable_name}
            # Extract all placeholders
            placeholders = re.findall(r"\{([^}]+)\}", template)

            # All placeholders should be simple variable names (no code execution)
            for placeholder in placeholders:
                assert re.match(
                    r"^[a-zA-Z_][a-zA-Z0-9_]*$", placeholder
                ), f"Placeholder '{placeholder}' should be a simple variable name"
