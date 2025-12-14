"""
Filter configuration for session tracking content modes.

This module defines the configurable filtering behavior for different
message types in Claude Code session tracking.
"""

from typing import Union

from pydantic import BaseModel, Field


class FilterConfig(BaseModel):
    """Configuration for session message filtering.

    Controls how different message types are filtered during session tracking.
    Allows fine-grained control over token reduction vs information preservation.

    Filter values use bool | str type system:
    - true: Preserve full content (no filtering)
    - false: Omit content entirely
    - "template.md": Load template from hierarchy (project > global > built-in)
    - "inline prompt...": Use string as direct LLM prompt

    Attributes:
        tool_calls: Whether to preserve tool call structure (default: True)
        tool_content: How to handle tool result content (default: "default-tool-content.md")
        user_messages: How to handle user message content (default: True to preserve user intent)
        agent_messages: How to handle agent text responses (default: True for context continuity)

    Examples:
        # Default configuration (template-based tool summarization)
        config = FilterConfig()

        # Maximum token reduction (omit all tool results)
        config = FilterConfig(tool_content=False)

        # No filtering (preserve everything)
        config = FilterConfig(
            tool_content=True,
            user_messages=True,
            agent_messages=True
        )

        # Custom template for tool content
        config = FilterConfig(
            tool_content="my-custom-template.md"
        )

        # Inline prompt for agent messages
        config = FilterConfig(
            agent_messages="Summarize this message in 1 sentence."
        )
    """

    tool_calls: bool = Field(
        default=True,
        description="Preserve tool call structure (names, parameters) even when filtering content"
    )

    tool_content: Union[bool, str] = Field(
        default="default-tool-content.md",
        description=(
            "Content mode for tool results: "
            "true (no filtering), false (omit), "
            '"template.md" (template file), or "inline prompt..." (direct LLM prompt)'
        )
    )

    user_messages: Union[bool, str] = Field(
        default=True,
        description=(
            "Content mode for user messages: "
            "true (preserve), false (omit), "
            '"template.md" (template file), or "inline prompt..." (direct LLM prompt)'
        )
    )

    agent_messages: Union[bool, str] = Field(
        default=True,
        description=(
            "Content mode for agent text responses: "
            "true (preserve), false (omit), "
            '"template.md" (template file), or "inline prompt..." (direct LLM prompt)'
        )
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tool_calls": True,
                    "tool_content": "default-tool-content.md",
                    "user_messages": True,
                    "agent_messages": True
                },
                {
                    "tool_calls": True,
                    "tool_content": False,
                    "user_messages": True,
                    "agent_messages": "Summarize in 1 sentence."
                }
            ]
        }
    }

    def is_no_filtering(self) -> bool:
        """Check if configuration preserves all content (no filtering)."""
        return (
            self.tool_content is True
            and self.user_messages is True
            and self.agent_messages is True
        )

    def is_aggressive_filtering(self) -> bool:
        """Check if configuration uses aggressive filtering (omit modes)."""
        return (
            self.tool_content is False
            or self.user_messages is False
            or self.agent_messages is False
        )

    def estimate_token_reduction(self) -> float:
        """Estimate approximate token reduction percentage.

        Returns:
            Estimated reduction (0.0-1.0) based on configuration.

        .. warning:: UNVALIDATED ASSUMPTIONS
            All values in this method are engineering estimates, NOT empirically
            measured. Actual token reduction may vary significantly. See
            `docs/SESSION_TRACKING_ASSUMPTIONS.md` for validation status.

        Notes:
            - True (full content): 0% reduction
            - Template/inline prompt: ~70% reduction for tool results, ~50% for messages
              [UNVALIDATED - basis: engineering guess]
            - False (omit): ~95% reduction [UNVALIDATED - basis: engineering guess]

        Examples:
            >>> config = FilterConfig()  # Default (template for tools)
            >>> config.estimate_token_reduction()
            0.42  # ~42% reduction (template-based tool summarization) [UNVALIDATED]

            >>> config = FilterConfig(tool_content=False)
            >>> config.estimate_token_reduction()
            0.57  # ~57% reduction (omit tool results) [UNVALIDATED]
        """
        # =======================================================================
        # UNVALIDATED ASSUMPTIONS - Token Composition Weights
        # Basis: Engineering estimate, no empirical measurement
        # Risk: If wrong, estimate_token_reduction() misleads callers
        # Validation: See docs/SESSION_TRACKING_ASSUMPTIONS.md
        # =======================================================================
        # Tool results: ~60% of tokens [UNVALIDATED]
        # User messages: ~15% of tokens [UNVALIDATED]
        # Agent messages: ~25% of tokens [UNVALIDATED]
        TOOL_WEIGHT = 0.60  # UNVALIDATED
        USER_WEIGHT = 0.15  # UNVALIDATED
        AGENT_WEIGHT = 0.25  # UNVALIDATED

        def get_reduction(value: Union[bool, str]) -> float:
            if value is True:
                return 0.0  # No filtering
            elif value is False:
                # UNVALIDATED ASSUMPTION: 95% reduction when omitting
                # Basis: Engineering guess (omit = ~5% overhead for markers)
                return 0.95
            else:
                # UNVALIDATED ASSUMPTION: 70% reduction for templates
                # Basis: Engineering guess, not measured against real sessions
                # Risk: Agents may make decisions based on this estimate
                return 0.7

        tool_reduction = get_reduction(self.tool_content)

        # UNVALIDATED ASSUMPTION: 50% reduction for user/agent templates
        # Basis: Engineering guess (messages need more context than tool results)
        user_reduction = 0.5 if isinstance(self.user_messages, str) else get_reduction(self.user_messages)
        agent_reduction = 0.5 if isinstance(self.agent_messages, str) else get_reduction(self.agent_messages)

        # Weighted average using UNVALIDATED weights
        return (
            TOOL_WEIGHT * tool_reduction +
            USER_WEIGHT * user_reduction +
            AGENT_WEIGHT * agent_reduction
        )
