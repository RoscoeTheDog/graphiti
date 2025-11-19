"""
Message summarization for session tracking content modes.

This module provides LLM-based summarization for user and agent messages
when string template or prompt is configured in the filtering system.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from graphiti_core.llm_client import LLMClient
from graphiti_core.session_tracking.prompts import DEFAULT_TEMPLATES

logger = logging.getLogger(__name__)


def resolve_template_path(
    template_ref: str,
    project_root: Optional[Path] = None,
) -> tuple[str, bool]:
    """Resolve template reference to content and is_inline flag.

    Resolution hierarchy:
    1. Absolute path → use directly
    2. Project template → <project>/.graphiti/auto-tracking/templates/{ref}
    3. Global template → ~/.graphiti/auto-tracking/templates/{ref}
    4. Built-in template → graphiti_core/session_tracking/prompts/{ref}
    5. Inline prompt → use string directly (if not .md extension)

    Args:
        template_ref: Template reference (file path or inline prompt)
        project_root: Optional project root directory

    Returns:
        tuple[str, bool]: (template_content, is_inline)

    Raises:
        FileNotFoundError: If template file not found in hierarchy

    Examples:
        >>> # Inline prompt
        >>> content, is_inline = resolve_template_path("Summarize: {content}")
        >>> assert is_inline is True

        >>> # Built-in template
        >>> content, is_inline = resolve_template_path("default-tool-content.md")
        >>> assert is_inline is False

        >>> # Project template (if exists)
        >>> content, is_inline = resolve_template_path(
        ...     "custom-template.md",
        ...     project_root=Path("/project")
        ... )
    """
    # Check if inline prompt (not .md file)
    if not template_ref.endswith(".md"):
        logger.debug(f"Using inline prompt (length: {len(template_ref)} chars)")
        return (template_ref, True)

    # Check absolute path
    template_path = Path(template_ref)
    if template_path.is_absolute():
        if template_path.exists():
            logger.debug(f"Using absolute template: {template_path}")
            return (template_path.read_text(encoding="utf-8"), False)
        raise FileNotFoundError(f"Template not found: {template_ref}")

    # Check project template
    if project_root:
        project_template = project_root / ".graphiti" / "auto-tracking" / "templates" / template_ref
        if project_template.exists():
            logger.debug(f"Using project template: {project_template}")
            return (project_template.read_text(encoding="utf-8"), False)

    # Check global template
    global_template = Path.home() / ".graphiti" / "auto-tracking" / "templates" / template_ref
    if global_template.exists():
        logger.debug(f"Using global template: {global_template}")
        return (global_template.read_text(encoding="utf-8"), False)

    # Check built-in template
    if template_ref in DEFAULT_TEMPLATES:
        logger.debug(f"Using built-in template: {template_ref}")
        return (DEFAULT_TEMPLATES[template_ref], False)

    # Check packaged template files
    package_template = Path(__file__).parent / "prompts" / template_ref
    if package_template.exists():
        logger.debug(f"Using packaged template: {package_template}")
        return (package_template.read_text(encoding="utf-8"), False)

    # Template not found
    raise FileNotFoundError(
        f"Template '{template_ref}' not found in hierarchy: "
        f"project > global > built-in > packaged"
    )


class MessageSummarizer:
    """LLM-based message summarizer for string template or prompt.

    Uses Graphiti's existing LLM client to generate concise summaries of
    user and agent messages. Includes caching to avoid re-summarizing
    identical content.

    Attributes:
        llm_client: Graphiti LLM client for text generation
        max_length: Maximum summary length in characters
        cache: In-memory cache of content hash -> summary
        cache_hits: Number of cache hits (for metrics)
        cache_misses: Number of cache misses (for metrics)

    Examples:
        >>> from graphiti_core.llm_client import OpenAIClient
        >>> llm_client = OpenAIClient()
        >>> summarizer = MessageSummarizer(llm_client)
        >>> summary = await summarizer.summarize("Long message content here...")
        >>> print(summary)
        "Brief summary of message content"
    """

    def __init__(
        self,
        llm_client: LLMClient,
        max_length: int = 200,
        model: str = "gpt-4o-mini",
        project_root: Optional[Path] = None,
    ):
        """Initialize message summarizer.

        Args:
            llm_client: Graphiti LLM client for text generation
            max_length: Maximum summary length in characters (default: 200)
            model: LLM model to use for summarization (default: gpt-4o-mini)
            project_root: Optional project root for template resolution

        Notes:
            - Uses gpt-4o-mini for cost efficiency (~$0.15 per 1M tokens)
            - Cache is in-memory only (resets between sessions)
            - Summaries are truncated to max_length if needed
        """
        self.llm_client = llm_client
        self.max_length = max_length
        self.model = model
        self.project_root = project_root
        self.cache: dict[str, str] = {}
        self.template_cache: dict[str, str] = {}  # Cache resolved templates
        self.cache_hits = 0
        self.cache_misses = 0

    def _generate_cache_key(self, content: str) -> str:
        """Generate cache key from content hash.

        Args:
            content: Message content to hash

        Returns:
            SHA256 hash of content (first 16 characters)
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def summarize(
        self,
        content: str,
        context: Optional[str] = None,
        template: Optional[str] = None,
    ) -> str:
        """Summarize message content using LLM.

        Args:
            content: Message content to summarize
            context: Optional context (e.g., "user message", "agent response")
            template: Optional template reference (file path or inline prompt)

        Returns:
            Concise 1-2 sentence summary of the content

        Raises:
            Exception: If LLM call fails (caller should handle gracefully)

        Notes:
            - Uses cache to avoid re-summarizing identical content
            - Truncates summary to max_length if needed
            - Logs cache hit/miss for metrics
            - Template variables: {content}, {context}
        """
        # Check cache first
        cache_key = self._generate_cache_key(content)
        if cache_key in self.cache:
            self.cache_hits += 1
            logger.debug(
                f"Cache hit for content (key: {cache_key}), "
                f"hits: {self.cache_hits}, misses: {self.cache_misses}"
            )
            return self.cache[cache_key]

        self.cache_misses += 1
        logger.debug(
            f"Cache miss for content (key: {cache_key}), "
            f"hits: {self.cache_hits}, misses: {self.cache_misses}"
        )

        # Build prompt from template or default
        if template:
            # Resolve template if not in cache
            if template not in self.template_cache:
                template_content, _is_inline = resolve_template_path(
                    template, self.project_root
                )
                self.template_cache[template] = template_content
            else:
                template_content = self.template_cache[template]

            # Substitute template variables
            prompt = template_content.format(
                content=content, context=context or "general message"
            )
        else:
            # Use default prompt
            context_hint = f" ({context})" if context else ""
            prompt = (
                f"Summarize this message{context_hint} concisely in 1-2 sentences, "
                f"preserving key intent and context:\n\n{content}"
            )

        try:
            # Call LLM (using generate_response for compatibility)
            # Note: LLMClient uses generate_response, not generate_text
            logger.debug(f"Calling LLM to summarize content (length: {len(content)} chars)")

            # Create messages format for LLM
            messages = [{"role": "user", "content": prompt}]

            # Call LLM with model override
            response = await self.llm_client.generate_response(messages=messages)

            # Extract summary from response
            summary = response.strip()

            # Truncate if needed
            if len(summary) > self.max_length:
                summary = summary[: self.max_length - 3] + "..."
                logger.debug(f"Truncated summary to {self.max_length} characters")

            # Cache result
            self.cache[cache_key] = summary

            # Log summary statistics (avoid division by zero for empty content)
            if len(content) > 0:
                reduction = (1 - len(summary) / len(content)) * 100
                logger.info(
                    f"Summarized content: {len(content)} chars → {len(summary)} chars "
                    f"({reduction:.1f}% reduction)"
                )
            else:
                logger.info(f"Summarized empty content (0 chars → {len(summary)} chars)")

            return summary

        except Exception as e:
            logger.error(f"Failed to summarize content: {e}", exc_info=True)
            raise  # Let caller handle gracefully (fallback to FULL)

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - size: Current cache size (number of entries)
            - hit_rate: Cache hit rate (0.0-1.0)
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "size": len(self.cache),
            "hit_rate": hit_rate,
        }

    def clear_cache(self):
        """Clear the summary cache.

        Notes:
            - Resets cache hits/misses counters
            - Use when switching sessions or to free memory
        """
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Summary cache cleared")
