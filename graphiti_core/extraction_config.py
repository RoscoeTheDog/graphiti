"""
Extraction configuration for preprocessing prompt injection.

This module defines the configurable preprocessing behavior for entity/edge
extraction in Graphiti knowledge graph construction.
"""

import logging
from pathlib import Path
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

from .template_resolver import TemplateResolver

logger = logging.getLogger(__name__)


class ExtractionConfig(BaseModel):
    """Configuration for entity/edge extraction preprocessing.

    Controls how preprocessing prompts are injected into extraction operations.
    Supports turn-based template resolution with hierarchical template loading.

    Preprocessing prompt values use bool | str type system:
    - None/False: Disable preprocessing (no injection)
    - "template.md": Load template from hierarchy (project > global > built-in)
    - "inline prompt...": Use string as direct LLM prompt

    Attributes:
        preprocessing_prompt: Preprocessing prompt configuration (default: False)
        preprocessing_mode: Where to inject prompt - prepend or append (default: "prepend")

    Examples:
        # No preprocessing (default)
        config = ExtractionConfig()

        # Template-based preprocessing (built-in template)
        config = ExtractionConfig(
            preprocessing_prompt="default-session-turn.md"
        )

        # Custom template-based preprocessing
        config = ExtractionConfig(
            preprocessing_prompt="session-turn-extraction.md"
        )

        # Inline prompt with append mode
        config = ExtractionConfig(
            preprocessing_prompt="Consider session context when extracting entities.",
            preprocessing_mode="append"
        )

        # Explicitly disabled
        config = ExtractionConfig(
            preprocessing_prompt=False
        )
    """

    preprocessing_prompt: Union[bool, str, None] = Field(
        default=False,
        description=(
            "Preprocessing prompt configuration: "
            "None/False (disabled), "
            '"template.md" (template file), or "inline prompt..." (direct LLM prompt)'
        )
    )

    preprocessing_mode: Literal["prepend", "append"] = Field(
        default="prepend",
        description=(
            "Injection mode for preprocessing prompt: "
            '"prepend" (inject before extraction prompt) or '
            '"append" (inject after extraction prompt)'
        )
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "preprocessing_prompt": False,
                    "preprocessing_mode": "prepend"
                },
                {
                    "preprocessing_prompt": "default-session-turn.md",
                    "preprocessing_mode": "prepend"
                },
                {
                    "preprocessing_prompt": "session-turn-extraction.md",
                    "preprocessing_mode": "prepend"
                },
                {
                    "preprocessing_prompt": "Consider session context when extracting entities.",
                    "preprocessing_mode": "append"
                }
            ]
        }
    }

    def is_enabled(self) -> bool:
        """Check if preprocessing is enabled.

        Returns:
            True if preprocessing_prompt is a non-empty string, False otherwise.

        Examples:
            >>> config = ExtractionConfig()
            >>> config.is_enabled()
            False

            >>> config = ExtractionConfig(preprocessing_prompt="template.md")
            >>> config.is_enabled()
            True

            >>> config = ExtractionConfig(preprocessing_prompt=False)
            >>> config.is_enabled()
            False

            >>> config = ExtractionConfig(preprocessing_prompt=None)
            >>> config.is_enabled()
            False
        """
        return isinstance(self.preprocessing_prompt, str) and len(self.preprocessing_prompt) > 0

    def resolve_prompt(self, project_dir: Optional[Path] = None) -> str:
        """Resolve preprocessing prompt to final string.

        Handles both template files and inline prompts:
        - Template files (e.g., "template.md"): Loaded via TemplateResolver hierarchy
        - Inline prompts (e.g., "Extract entities..."): Returned directly
        - Disabled (False/None): Returns empty string

        Template resolution searches in this order:
        1. Project templates: {project_dir}/.graphiti/templates/
        2. Global templates: ~/.graphiti/templates/
        3. Built-in templates: graphiti_core/session_tracking/prompts/

        Args:
            project_dir: Optional project root for project-level templates.
                If None, only global and built-in templates are searched.

        Returns:
            Resolved prompt string, or empty string if disabled or not found.

        Examples:
            >>> config = ExtractionConfig(preprocessing_prompt="template.md")
            >>> prompt = config.resolve_prompt()  # Loads from hierarchy

            >>> config = ExtractionConfig(preprocessing_prompt="Extract entities.")
            >>> prompt = config.resolve_prompt()  # Returns inline prompt directly
            'Extract entities.'

            >>> config = ExtractionConfig(preprocessing_prompt=False)
            >>> prompt = config.resolve_prompt()  # Returns empty string
            ''
        """
        # If disabled or not set, return empty string
        if not self.is_enabled():
            return ""

        prompt_value = self.preprocessing_prompt
        assert isinstance(prompt_value, str), "is_enabled() ensures this is a string"

        # Check if it looks like a template filename (ends with .md or contains path separator)
        is_template = prompt_value.endswith(".md") or "/" in prompt_value or "\\" in prompt_value

        if is_template:
            # Load template via TemplateResolver
            resolver = TemplateResolver(project_dir=project_dir)
            content = resolver.load(prompt_value)

            if content is None:
                logger.warning(
                    "Template '%s' not found in hierarchy, returning empty string",
                    prompt_value,
                )
                return ""

            return content
        else:
            # Treat as inline prompt - return directly
            logger.debug("Using inline preprocessing prompt (length: %d)", len(prompt_value))
            return prompt_value
