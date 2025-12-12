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

"""Dynamic prompt generation for session summarization.

This module provides dynamic prompt construction based on activity vectors,
including only high-priority extraction fields to reduce token usage and
improve LLM focus.

Example:
    >>> from graphiti_core.session_tracking import ActivityVector
    >>> activity = ActivityVector(fixing=0.9, testing=0.5)
    >>> prompt = build_extraction_prompt(activity, content="Session content here", threshold=0.3)
    >>> # Prompt includes errors_resolved prioritized over discoveries
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .activity_vector import ActivityVector

from .extraction_priority import get_extraction_priorities


# Field-specific instructions for extraction
# Maps each extraction field to concise guidance for the LLM
FIELD_INSTRUCTIONS: dict[str, str] = {
    "completed_tasks": "List specific tasks that were accomplished",
    "key_decisions": "Capture decisions made WITH rationale (why this choice?)",
    "errors_resolved": "For each error: what was it, root cause, how fixed, verified?",
    "config_changes": "List config file changes with before/after values",
    "test_results": "Summarize test execution results and failures",
    "discoveries": "Key insights or learnings from exploration",
    "files_modified": "Files modified with brief description of changes",
    "next_steps": "Tasks to continue this work",
    "blocked_items": "Blockers preventing progress",
    "documentation_referenced": "Documentation paths referenced",
}


# Default prompt template with placeholders
DEFAULT_PROMPT_TEMPLATE = """Summarize this session into a structured format.

**Session Activity Profile**: {activity_profile}

Extract the following information (in order of importance):

{prioritized_fields}

## Session Content

{content}

## Response Format
Respond with a JSON object matching the EnhancedSessionSummary schema.
"""


class PromptTemplate(Protocol):
    """Protocol for custom prompt templates.

    Implementations can provide alternative prompt structures while
    maintaining compatibility with the prompt builder interface.
    """

    def build_prompt(
        self, activity: 'ActivityVector', content: str, threshold: float
    ) -> str:
        """Build a custom extraction prompt.

        Args:
            activity: The activity vector representing session activities
            content: The session content to analyze
            threshold: Minimum priority score for field inclusion

        Returns:
            Complete prompt string ready for LLM submission
        """
        ...


def _format_activity_profile(activity: 'ActivityVector') -> str:
    """Format activity vector as human-readable profile string.

    Shows the top 3 activity dimensions that are above the significance
    threshold (0.1). If no dimensions are significant, returns a generic
    indicator.

    Args:
        activity: The activity vector to format

    Returns:
        Formatted string like "fixing (0.80), configuring (0.70), testing (0.50)"
        or "general session" if all dimensions are below 0.1

    Example:
        >>> activity = ActivityVector(fixing=0.9, configuring=0.7, testing=0.5)
        >>> _format_activity_profile(activity)
        'fixing (0.90), configuring (0.70), testing (0.50)'
    """
    # Get all dimensions and their values
    dimensions = [
        (name, getattr(activity, name))
        for name in activity.DIMENSIONS
        if getattr(activity, name) > 0.1  # Significance threshold
    ]

    # Sort by value descending and take top 3
    dimensions.sort(key=lambda x: x[1], reverse=True)
    top_dimensions = dimensions[:3]

    if not top_dimensions:
        return "general session"

    # Format as comma-separated list with values
    parts = [f"{name} ({value:.2f})" for name, value in top_dimensions]
    return ", ".join(parts)


def _format_prioritized_fields(priorities: list[tuple[str, float]]) -> str:
    """Format prioritized fields as numbered list with instructions.

    Creates a numbered list showing field name, priority score, and
    extraction instructions. Priority scores help the LLM understand
    relative importance.

    Args:
        priorities: List of (field_name, priority_score) tuples from
                    get_extraction_priorities(), ordered by priority

    Returns:
        Formatted numbered list like:
        "1. **errors_resolved** (priority: 0.92): For each error: ..."

    Example:
        >>> priorities = [("errors_resolved", 0.92), ("test_results", 0.73)]
        >>> _format_prioritized_fields(priorities)
        '1. **errors_resolved** (priority: 0.92): For each error: ...\\n2. ...'
    """
    lines = []
    for index, (field, priority) in enumerate(priorities, start=1):
        instruction = FIELD_INSTRUCTIONS.get(
            field, "Extract relevant information for this field"
        )
        lines.append(
            f"{index}. **{field}** (priority: {priority:.2f}): {instruction}"
        )

    return "\n".join(lines)


def build_extraction_prompt(
    activity: 'ActivityVector',
    content: str,
    threshold: float = 0.3,
    custom_template: PromptTemplate | None = None,
) -> str:
    """Build dynamic extraction prompt based on activity vector.

    Constructs a prompt that includes only high-priority extraction fields,
    reducing token usage and focusing LLM attention on what matters most
    for the session type. Debugging sessions prioritize error resolution
    while exploration sessions prioritize discoveries.

    Args:
        activity: The activity vector representing session activities
        content: The session content to analyze
        threshold: Minimum priority score (0.0-1.0) for field inclusion.
                   Default 0.3 balances coverage with token efficiency.
        custom_template: Optional custom template implementing PromptTemplate
                         protocol. If provided, delegates to custom logic.

    Returns:
        Complete prompt string ready for LLM submission, including:
        - Activity profile context (top 3 dimensions)
        - Prioritized field list with instructions and scores
        - Session content
        - Response format guidance

    Example:
        >>> activity = ActivityVector(fixing=0.9, testing=0.5)
        >>> prompt = build_extraction_prompt(activity, "Fixed auth bug...", threshold=0.3)
        >>> # Prompt prioritizes errors_resolved and test_results
        >>> # Token reduction: ~30-60% vs static prompt with all fields
    """
    # Delegate to custom template if provided
    if custom_template is not None:
        return custom_template.build_prompt(activity, content, threshold)

    # Get prioritized fields from extraction priority algorithm
    priorities = get_extraction_priorities(activity, threshold)

    # Format activity profile (top 3 dimensions)
    activity_profile = _format_activity_profile(activity)

    # Format prioritized fields with instructions
    prioritized_fields = _format_prioritized_fields(priorities)

    # Substitute into template
    prompt = DEFAULT_PROMPT_TEMPLATE.format(
        activity_profile=activity_profile,
        prioritized_fields=prioritized_fields,
        content=content,
    )

    return prompt
