"""
Message summarization for session tracking content modes.

This module provides LLM-based summarization for user and agent messages
when ContentMode.SUMMARY is configured in the filtering system.
"""

import hashlib
import logging
from typing import Optional

from graphiti_core.llm_client import LLMClient

logger = logging.getLogger(__name__)


class MessageSummarizer:
    """LLM-based message summarizer for ContentMode.SUMMARY.

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
    ):
        """Initialize message summarizer.

        Args:
            llm_client: Graphiti LLM client for text generation
            max_length: Maximum summary length in characters (default: 200)
            model: LLM model to use for summarization (default: gpt-4o-mini)

        Notes:
            - Uses gpt-4o-mini for cost efficiency (~$0.15 per 1M tokens)
            - Cache is in-memory only (resets between sessions)
            - Summaries are truncated to max_length if needed
        """
        self.llm_client = llm_client
        self.max_length = max_length
        self.model = model
        self.cache: dict[str, str] = {}
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

    async def summarize(self, content: str, context: Optional[str] = None) -> str:
        """Summarize message content using LLM.

        Args:
            content: Message content to summarize
            context: Optional context (e.g., "user message", "agent response")

        Returns:
            Concise 1-2 sentence summary of the content

        Raises:
            Exception: If LLM call fails (caller should handle gracefully)

        Notes:
            - Uses cache to avoid re-summarizing identical content
            - Truncates summary to max_length if needed
            - Logs cache hit/miss for metrics
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

        # Build prompt
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
