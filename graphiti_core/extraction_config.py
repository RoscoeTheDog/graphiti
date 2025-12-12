"""
Extraction configuration for preprocessing prompt injection.

This module defines the configurable preprocessing behavior for entity/edge
extraction in Graphiti knowledge graph construction.
"""

from typing import Literal, Union

from pydantic import BaseModel, Field


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

        # Template-based preprocessing
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

    def resolve_prompt(self) -> str:
        """Resolve preprocessing prompt to final string.

        This method is a stub for future template resolution logic.
        Template resolution will be implemented in Story 8 (TemplateResolver).

        Returns:
            Empty string (stub implementation).

        Note:
            Full implementation deferred to Story 8 (TemplateResolver with hierarchy).
            Future implementation will:
            - Load templates from project/.claude/templates/
            - Fall back to global ~/.claude/templates/
            - Fall back to built-in templates
            - Return inline strings directly
        """
        # TODO: Implement template resolution in Story 8
        # For now, return empty string as stub
        return ""
