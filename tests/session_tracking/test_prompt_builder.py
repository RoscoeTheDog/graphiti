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

"""Tests for prompt_builder module (Story 9)."""

import pytest

from graphiti_core.session_tracking.activity_vector import ActivityVector
from graphiti_core.session_tracking.prompt_builder import (
    DEFAULT_PROMPT_TEMPLATE,
    FIELD_INSTRUCTIONS,
    PromptTemplate,
    _format_activity_profile,
    _format_prioritized_fields,
    build_extraction_prompt,
)


class TestFieldInstructions:
    """Tests for FIELD_INSTRUCTIONS constant."""

    def test_field_instructions_completeness(self):
        """Verify all SessionSummarySchema fields have instructions."""
        # All 10 expected fields from SessionSummarySchema
        expected_fields = {
            "completed_tasks",
            "key_decisions",
            "errors_resolved",
            "discoveries",
            "config_changes",
            "test_results",
            "files_modified",
            "next_steps",
            "blocked_items",
            "documentation_referenced",
        }

        # Verify all fields present
        assert set(FIELD_INSTRUCTIONS.keys()) == expected_fields

        # Verify all instructions are non-empty
        for field, instruction in FIELD_INSTRUCTIONS.items():
            assert instruction, f"Field '{field}' has empty instruction"
            assert len(instruction) > 10, f"Field '{field}' instruction too short"


class TestFormatActivityProfile:
    """Tests for _format_activity_profile helper."""

    def test_format_activity_profile_top_three(self):
        """Verify activity profile shows top 3 dimensions by score."""
        activity = ActivityVector(
            fixing=0.9,
            configuring=0.7,
            testing=0.5,
            exploring=0.3,
            creating=0.2,
        )

        result = _format_activity_profile(activity)

        # Should show top 3 in descending order
        assert "fixing (0.90)" in result
        assert "configuring (0.70)" in result
        assert "testing (0.50)" in result
        # Should not include lower-ranked dimensions
        assert "exploring" not in result
        assert "creating" not in result
        # Verify order (fixing first)
        assert result.index("fixing") < result.index("configuring")
        assert result.index("configuring") < result.index("testing")

    def test_format_activity_profile_low_activity(self):
        """Verify 'general session' when all dimensions below threshold."""
        # All dimensions below 0.1 threshold
        activity = ActivityVector(
            fixing=0.05,
            configuring=0.08,
            testing=0.03,
        )

        result = _format_activity_profile(activity)

        assert result == "general session"

    def test_format_activity_profile_less_than_three(self):
        """Verify handling when fewer than 3 dimensions above threshold."""
        # Only 2 dimensions above 0.1
        activity = ActivityVector(
            fixing=0.8,
            testing=0.6,
            creating=0.05,
        )

        result = _format_activity_profile(activity)

        # Should show only the 2 significant dimensions
        assert "fixing (0.80)" in result
        assert "testing (0.60)" in result
        assert "creating" not in result


class TestFormatPrioritizedFields:
    """Tests for _format_prioritized_fields helper."""

    def test_format_prioritized_fields_order(self):
        """Verify fields ordered by priority descending."""
        priorities = [
            ("errors_resolved", 0.92),
            ("test_results", 0.73),
            ("discoveries", 0.45),
        ]

        result = _format_prioritized_fields(priorities)

        # Verify numbering (1, 2, 3)
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("1. **errors_resolved**")
        assert lines[1].startswith("2. **test_results**")
        assert lines[2].startswith("3. **discoveries**")

    def test_format_prioritized_fields_includes_priority(self):
        """Verify priority scores included in output."""
        priorities = [
            ("errors_resolved", 0.92),
            ("test_results", 0.73),
        ]

        result = _format_prioritized_fields(priorities)

        # Verify priority scores formatted correctly
        assert "(priority: 0.92)" in result
        assert "(priority: 0.73)" in result

    def test_format_prioritized_fields_includes_instructions(self):
        """Verify field instructions included in output."""
        priorities = [
            ("errors_resolved", 0.92),
            ("completed_tasks", 0.65),
        ]

        result = _format_prioritized_fields(priorities)

        # Verify instructions from FIELD_INSTRUCTIONS
        assert FIELD_INSTRUCTIONS["errors_resolved"] in result
        assert FIELD_INSTRUCTIONS["completed_tasks"] in result

    def test_format_prioritized_fields_unknown_field_fallback(self):
        """Verify fallback instruction for unknown fields."""
        priorities = [("unknown_field", 0.50)]

        result = _format_prioritized_fields(priorities)

        # Should use fallback instruction
        assert "Extract relevant information for this field" in result


class TestBuildExtractionPrompt:
    """Tests for main build_extraction_prompt function."""

    def test_build_extraction_prompt_debugging_session(self):
        """Verify prompt structure for debugging session (fixing=0.9)."""
        activity = ActivityVector(fixing=0.9, testing=0.5, exploring=0.1)
        content = "Fixed authentication bug in login handler"

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        # Verify activity profile included
        assert "Session Activity Profile" in prompt
        assert "fixing" in prompt

        # Verify prioritized fields section exists
        assert "Extract the following information" in prompt
        assert "**errors_resolved**" in prompt

        # errors_resolved should appear before discoveries (priority ordering)
        # Since fixing=0.9, errors_resolved will have high priority
        # But we need to verify it's in the prompt
        assert "(priority:" in prompt  # Priority scores present

        # Verify content included
        assert content in prompt
        assert "Fixed authentication bug" in prompt

        # Verify response format instructions
        assert "Response Format" in prompt
        assert "JSON" in prompt

    def test_build_extraction_prompt_exploration_session(self):
        """Verify prompt structure for exploration session (exploring=0.9)."""
        activity = ActivityVector(exploring=0.9, debugging_tools=0.6, creating=0.3)
        content = "Explored new graph traversal algorithms"

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        # Verify activity profile shows exploring
        assert "exploring" in prompt

        # For exploration sessions, discoveries should be prioritized
        assert "**discoveries**" in prompt

        # documentation_referenced should be included for exploration
        # (though it depends on exact priority algorithm)
        # Just verify prompt structure is valid
        assert "Extract the following information" in prompt
        assert content in prompt

    def test_threshold_filtering(self):
        """Verify threshold filters low-priority fields."""
        activity = ActivityVector(fixing=0.5, testing=0.3, exploring=0.2)
        content = "Session content"

        # High threshold should include fewer fields
        prompt_high = build_extraction_prompt(activity, content, threshold=0.7)
        prompt_low = build_extraction_prompt(activity, content, threshold=0.1)

        # Count field markers (numbered items)
        high_count = prompt_high.count("**")  # Bold field names
        low_count = prompt_low.count("**")

        # Low threshold should include more fields
        assert low_count > high_count, "Low threshold should include more fields"

    def test_custom_template_override(self):
        """Verify custom template integration point."""

        # Custom template implementation
        class CustomTemplate:
            def build_prompt(
                self, activity: ActivityVector, content: str, threshold: float
            ) -> str:
                return f"CUSTOM: {content} (threshold={threshold})"

        activity = ActivityVector(fixing=0.9)
        content = "Test content"
        custom = CustomTemplate()

        result = build_extraction_prompt(
            activity, content, threshold=0.5, custom_template=custom
        )

        # Verify custom template was used
        assert result.startswith("CUSTOM:")
        assert "Test content" in result
        assert "threshold=0.5" in result

    def test_default_template_when_no_custom(self):
        """Verify default template used when custom_template=None."""
        activity = ActivityVector(fixing=0.9)
        content = "Test content"

        result = build_extraction_prompt(activity, content, custom_template=None)

        # Should use default template structure
        assert "Session Activity Profile" in result
        assert "Extract the following information" in result
        assert "Response Format" in result

    def test_prompt_contains_content(self):
        """Verify session content included in prompt."""
        activity = ActivityVector(fixing=0.5)
        content = "This is unique session content 12345"

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        assert content in prompt
        assert "This is unique session content 12345" in prompt

    def test_prompt_contains_response_format(self):
        """Verify JSON response format instructions included."""
        activity = ActivityVector(fixing=0.5)
        content = "Content"

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        # Verify response format guidance
        assert "Response Format" in prompt
        assert "JSON" in prompt

    def test_prompt_token_reduction(self):
        """Verify dynamic prompt reduces tokens vs static."""
        activity = ActivityVector(fixing=0.9, testing=0.5)
        content = "Session content"

        # Build dynamic prompt with threshold
        dynamic_prompt = build_extraction_prompt(activity, content, threshold=0.5)

        # Estimate: A static prompt would include all 10 fields
        # Dynamic prompt should include only high-priority fields (~4-6)
        # Count field markers to estimate
        dynamic_field_count = dynamic_prompt.count("**")

        # Should have fewer than 20 bold markers (10 fields * 2 if all included)
        # Typical: 4-6 fields = 8-12 bold markers
        assert (
            dynamic_field_count < 20
        ), "Dynamic prompt should include subset of fields"

        # Estimate token reduction (chars/4)
        dynamic_tokens = len(dynamic_prompt) / 4

        # A static prompt with all 10 fields would be significantly longer
        # We can't test exact static prompt without creating it, but we can verify
        # the dynamic prompt is reasonably sized
        assert dynamic_tokens < 2000, "Dynamic prompt should be token-efficient"


class TestPromptTemplateProtocol:
    """Tests for PromptTemplate protocol and custom override."""

    def test_protocol_interface(self):
        """Verify PromptTemplate protocol has correct interface."""
        # This tests that the protocol is importable and has correct method
        import inspect

        # Get the protocol's build_prompt method
        assert hasattr(PromptTemplate, "build_prompt")

        # Verify it's a protocol (has __protocol__ attribute in typing)
        # We can check by trying to implement it
        class ValidTemplate:
            def build_prompt(
                self, activity: ActivityVector, content: str, threshold: float
            ) -> str:
                return "valid"

        # Should not raise TypeError when used
        instance = ValidTemplate()
        assert callable(instance.build_prompt)

    def test_custom_template_called_with_correct_args(self):
        """Verify custom template receives correct arguments."""

        captured_args = {}

        class CapturingTemplate:
            def build_prompt(
                self, activity: ActivityVector, content: str, threshold: float
            ) -> str:
                captured_args["activity"] = activity
                captured_args["content"] = content
                captured_args["threshold"] = threshold
                return "result"

        activity = ActivityVector(fixing=0.8)
        content = "Test content"
        threshold = 0.42
        template = CapturingTemplate()

        build_extraction_prompt(activity, content, threshold, custom_template=template)

        # Verify correct arguments passed
        assert captured_args["activity"] is activity
        assert captured_args["content"] == content
        assert captured_args["threshold"] == threshold


class TestIntegration:
    """Integration tests with other sprint components."""

    def test_integration_with_extraction_priority(self):
        """Verify correct integration with get_extraction_priorities()."""
        # This tests that build_extraction_prompt correctly uses
        # get_extraction_priorities() from Story 8
        activity = ActivityVector(fixing=0.9, testing=0.7, exploring=0.2)
        content = "Content"

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        # For fixing=0.9, testing=0.7, we expect:
        # - errors_resolved to have high priority
        # - test_results to have high priority
        # - These should appear in the prompt

        # Verify fields are present and correctly prioritized
        assert "**errors_resolved**" in prompt
        assert "**test_results**" in prompt

        # Verify priority scores are included
        assert "(priority:" in prompt

    def test_integration_with_activity_vector(self):
        """Verify correct handling of ActivityVector.to_dict() format."""
        activity = ActivityVector(
            fixing=0.9,
            configuring=0.7,
            testing=0.5,
            creating=0.3,
            exploring=0.2,
            debugging_tools=0.1,
            refactoring=0.05,
            documenting=0.02,
        )
        content = "Content"

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        # Verify activity profile correctly formats vector
        # Should show top 3: fixing, configuring, testing
        profile_section = prompt.split("Extract the following")[0]
        assert "fixing" in profile_section
        assert "configuring" in profile_section
        assert "testing" in profile_section

        # Lower dimensions should not appear in profile
        assert "refactoring" not in profile_section
        assert "documenting" not in profile_section

    def test_full_workflow_debugging_scenario(self):
        """Test complete workflow for debugging scenario."""
        # Simulate a debugging session
        activity = ActivityVector(
            fixing=0.95,  # Primary activity
            testing=0.80,  # Verifying fixes
            debugging_tools=0.60,  # Using debugger
            exploring=0.20,  # Some investigation
        )

        content = """
        Fixed critical authentication bug in login handler.
        Root cause: JWT token validation was checking wrong claim.
        Solution: Updated validation to check 'sub' claim instead of 'user_id'.
        Tests: All 45 auth tests passing.
        """

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        # Verify prompt structure
        assert "Session Activity Profile" in prompt
        assert "fixing (0.95)" in prompt

        # High-priority fields for debugging should be present
        assert "**errors_resolved**" in prompt
        assert "**test_results**" in prompt

        # Content should be included
        assert "Fixed critical authentication bug" in prompt

        # Should have response format
        assert "JSON" in prompt

    def test_full_workflow_exploration_scenario(self):
        """Test complete workflow for exploration scenario."""
        # Simulate an exploration session
        activity = ActivityVector(
            exploring=0.90,  # Primary activity
            debugging_tools=0.50,  # Investigating code
            creating=0.30,  # Trying things
        )

        content = """
        Explored new graph traversal algorithms for Neo4j.
        Discovered that breadth-first search is more efficient for our use case.
        Referenced: Neo4j documentation on Cypher query optimization.
        Next: Implement BFS algorithm in traversal module.
        """

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        # Verify prompt structure
        assert "exploring (0.90)" in prompt

        # High-priority fields for exploration should be present
        assert "**discoveries**" in prompt
        # documentation_referenced may or may not appear depending on threshold
        # but the prompt should be valid

        # Content should be included
        assert "Explored new graph traversal algorithms" in prompt

    def test_edge_case_zero_activity(self):
        """Test handling of zero activity vector."""
        activity = ActivityVector()  # All zeros
        content = "Minimal session"

        prompt = build_extraction_prompt(activity, content, threshold=0.3)

        # Should handle gracefully
        assert "general session" in prompt
        assert content in prompt
        assert "Response Format" in prompt

    def test_edge_case_high_threshold(self):
        """Test handling of very high threshold (0.9)."""
        activity = ActivityVector(fixing=0.95, testing=0.85)
        content = "Content"

        prompt = build_extraction_prompt(activity, content, threshold=0.9)

        # Should include only very high-priority fields
        # At threshold=0.9, likely only 1-2 fields will qualify
        field_count = prompt.count("**")

        # Should be minimal
        assert field_count < 6, "High threshold should result in few fields"

    def test_edge_case_low_threshold(self):
        """Test handling of very low threshold (0.05)."""
        activity = ActivityVector(fixing=0.5, testing=0.3)
        content = "Content"

        prompt = build_extraction_prompt(activity, content, threshold=0.05)

        # Should include many fields
        field_count = prompt.count("**")

        # Should be comprehensive
        assert field_count > 10, "Low threshold should result in many fields"
