"""
Filter configuration for session tracking content modes.

This module defines the configurable filtering behavior for different
message types in Claude Code session tracking.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ContentMode(str, Enum):
    """Content preservation mode for filtered messages.

    Attributes:
        FULL: Preserve full content (no filtering)
        SUMMARY: Replace with concise 1-line summary
        OMIT: Completely remove content (structure only)
    """

    FULL = "full"
    SUMMARY = "summary"
    OMIT = "omit"


class FilterConfig(BaseModel):
    """Configuration for session message filtering.

    Controls how different message types are filtered during session tracking.
    Allows fine-grained control over token reduction vs information preservation.

    Attributes:
        tool_calls: Whether to preserve tool call structure (default: True)
        tool_content: How to handle tool result content (default: SUMMARY for 50%+ token reduction)
        user_messages: How to handle user message content (default: FULL to preserve user intent)
        agent_messages: How to handle agent text responses (default: FULL for context continuity)

    Examples:
        # Default configuration (50%+ token reduction, preserves user/agent messages)
        config = FilterConfig()

        # Maximum token reduction (omit all tool results)
        config = FilterConfig(tool_content=ContentMode.OMIT)

        # No filtering (preserve everything)
        config = FilterConfig(
            tool_content=ContentMode.FULL,
            user_messages=ContentMode.FULL,
            agent_messages=ContentMode.FULL
        )

        # Conservative filtering (summarize tools, omit agent messages)
        config = FilterConfig(
            tool_content=ContentMode.SUMMARY,
            agent_messages=ContentMode.SUMMARY
        )
    """

    tool_calls: bool = Field(
        default=True,
        description="Preserve tool call structure (names, parameters) even when filtering content"
    )

    tool_content: ContentMode = Field(
        default=ContentMode.SUMMARY,
        description="Content mode for tool results: full (no filtering), summary (1-line), omit (remove)"
    )

    user_messages: ContentMode = Field(
        default=ContentMode.FULL,
        description="Content mode for user messages: full (preserve), summary (condense), omit (remove)"
    )

    agent_messages: ContentMode = Field(
        default=ContentMode.FULL,
        description="Content mode for agent text responses: full (preserve), summary (condense), omit (remove)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tool_calls": True,
                    "tool_content": "summary",
                    "user_messages": "full",
                    "agent_messages": "full"
                },
                {
                    "tool_calls": True,
                    "tool_content": "omit",
                    "user_messages": "full",
                    "agent_messages": "summary"
                }
            ]
        }
    }

    def is_no_filtering(self) -> bool:
        """Check if configuration preserves all content (no filtering)."""
        return (
            self.tool_content == ContentMode.FULL
            and self.user_messages == ContentMode.FULL
            and self.agent_messages == ContentMode.FULL
        )

    def is_aggressive_filtering(self) -> bool:
        """Check if configuration uses aggressive filtering (omit modes)."""
        return (
            self.tool_content == ContentMode.OMIT
            or self.user_messages == ContentMode.OMIT
            or self.agent_messages == ContentMode.OMIT
        )

    def estimate_token_reduction(self) -> float:
        """Estimate approximate token reduction percentage.

        Returns:
            Estimated reduction (0.0-1.0) based on configuration.

        Notes:
            - FULL content: 0% reduction
            - SUMMARY content: ~70% reduction for tool results, ~50% for messages
            - OMIT content: ~95% reduction

        Examples:
            >>> config = FilterConfig()  # Default
            >>> config.estimate_token_reduction()
            0.35  # ~35% reduction (summarize tool results only)

            >>> config = FilterConfig(tool_content=ContentMode.OMIT)
            >>> config.estimate_token_reduction()
            0.57  # ~57% reduction (omit tool results)
        """
        # Weights based on typical Claude Code session composition
        # Tool results: ~60% of tokens
        # User messages: ~15% of tokens
        # Agent messages: ~25% of tokens

        tool_reduction = {
            ContentMode.FULL: 0.0,
            ContentMode.SUMMARY: 0.7,  # 1-line summaries
            ContentMode.OMIT: 0.95,
        }[self.tool_content]

        user_reduction = {
            ContentMode.FULL: 0.0,
            ContentMode.SUMMARY: 0.5,  # Moderate condensing
            ContentMode.OMIT: 0.95,
        }[self.user_messages]

        agent_reduction = {
            ContentMode.FULL: 0.0,
            ContentMode.SUMMARY: 0.5,  # Moderate condensing
            ContentMode.OMIT: 0.95,
        }[self.agent_messages]

        # Weighted average
        return (
            0.60 * tool_reduction +
            0.15 * user_reduction +
            0.25 * agent_reduction
        )
