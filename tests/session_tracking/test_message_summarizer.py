"""Tests for MessageSummarizer LLM-based content summarization."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from graphiti_core.session_tracking.message_summarizer import MessageSummarizer


class MockLLMClient:
    """Mock LLM client for testing without real API calls."""

    def __init__(self, mock_response="This is a test summary."):
        self.mock_response = mock_response
        self.call_count = 0
        self.last_messages = None

    async def generate_response(self, messages):
        """Mock LLM response generation."""
        self.call_count += 1
        self.last_messages = messages
        return self.mock_response


@pytest.mark.asyncio
class TestMessageSummarizer:
    """Test MessageSummarizer class."""

    async def test_initialization(self):
        """Test summarizer initialization."""
        llm_client = MockLLMClient()
        summarizer = MessageSummarizer(llm_client, max_length=150)

        assert summarizer.llm_client == llm_client
        assert summarizer.max_length == 150
        assert summarizer.model == "gpt-4o-mini"
        assert summarizer.cache == {}
        assert summarizer.cache_hits == 0
        assert summarizer.cache_misses == 0

    async def test_basic_summarization(self):
        """Test basic LLM summarization."""
        llm_client = MockLLMClient("Brief summary of the content.")
        summarizer = MessageSummarizer(llm_client)

        content = "This is a very long message that needs to be summarized into something shorter."
        summary = await summarizer.summarize(content)

        assert summary == "Brief summary of the content."
        assert llm_client.call_count == 1
        assert summarizer.cache_misses == 1
        assert summarizer.cache_hits == 0

    async def test_summarization_with_context(self):
        """Test summarization with context hint."""
        llm_client = MockLLMClient("User wants to know about...")
        summarizer = MessageSummarizer(llm_client)

        content = "Can you explain how session tracking works?"
        summary = await summarizer.summarize(content, context="user message")

        assert summary == "User wants to know about..."
        # Check that context was included in prompt
        assert "user message" in llm_client.last_messages[0]["content"]

    async def test_cache_hit(self):
        """Test cache hit for identical content."""
        llm_client = MockLLMClient("Cached summary.")
        summarizer = MessageSummarizer(llm_client)

        content = "Identical message content"

        # First call - cache miss
        summary1 = await summarizer.summarize(content)
        assert summary1 == "Cached summary."
        assert llm_client.call_count == 1
        assert summarizer.cache_misses == 1
        assert summarizer.cache_hits == 0

        # Second call - cache hit
        summary2 = await summarizer.summarize(content)
        assert summary2 == "Cached summary."
        assert llm_client.call_count == 1  # No new LLM call
        assert summarizer.cache_misses == 1
        assert summarizer.cache_hits == 1

    async def test_truncation(self):
        """Test summary truncation to max_length."""
        long_summary = "A" * 500  # 500 characters
        llm_client = MockLLMClient(long_summary)
        summarizer = MessageSummarizer(llm_client, max_length=100)

        content = "Some content"
        summary = await summarizer.summarize(content)

        assert len(summary) == 100
        assert summary.endswith("...")

    async def test_no_truncation_needed(self):
        """Test that short summaries are not truncated."""
        llm_client = MockLLMClient("Short summary.")
        summarizer = MessageSummarizer(llm_client, max_length=200)

        content = "Some content"
        summary = await summarizer.summarize(content)

        assert summary == "Short summary."
        assert not summary.endswith("...")

    async def test_cache_key_generation(self):
        """Test cache key generation from content."""
        llm_client = MockLLMClient()
        summarizer = MessageSummarizer(llm_client)

        content1 = "Test content"
        content2 = "Test content"  # Identical
        content3 = "Different content"

        key1 = summarizer._generate_cache_key(content1)
        key2 = summarizer._generate_cache_key(content2)
        key3 = summarizer._generate_cache_key(content3)

        assert key1 == key2  # Same content = same key
        assert key1 != key3  # Different content = different key
        assert len(key1) == 16  # First 16 chars of hash

    async def test_get_cache_stats(self):
        """Test cache statistics retrieval."""
        llm_client = MockLLMClient("Summary.")
        summarizer = MessageSummarizer(llm_client)

        # Initial stats
        stats = summarizer.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        assert stats["hit_rate"] == 0.0

        # After one miss
        await summarizer.summarize("Content 1")
        stats = summarizer.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 0.0

        # After one hit
        await summarizer.summarize("Content 1")
        stats = summarizer.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 0.5

    async def test_clear_cache(self):
        """Test cache clearing."""
        llm_client = MockLLMClient("Summary.")
        summarizer = MessageSummarizer(llm_client)

        # Populate cache
        await summarizer.summarize("Content 1")
        await summarizer.summarize("Content 2")

        assert len(summarizer.cache) == 2
        assert summarizer.cache_misses == 2

        # Clear cache
        summarizer.clear_cache()

        assert len(summarizer.cache) == 0
        assert summarizer.cache_hits == 0
        assert summarizer.cache_misses == 0

    async def test_error_handling(self):
        """Test error propagation from LLM client."""

        class FailingLLMClient:
            async def generate_response(self, messages):
                raise ValueError("LLM API error")

        llm_client = FailingLLMClient()
        summarizer = MessageSummarizer(llm_client)

        with pytest.raises(ValueError, match="LLM API error"):
            await summarizer.summarize("Content")

    async def test_multiple_different_contents(self):
        """Test caching with multiple different contents."""
        llm_client = MockLLMClient()
        summarizer = MessageSummarizer(llm_client)

        # Different summaries for different content
        llm_client.mock_response = "Summary 1"
        await summarizer.summarize("Content 1")

        llm_client.mock_response = "Summary 2"
        await summarizer.summarize("Content 2")

        llm_client.mock_response = "Summary 3"
        await summarizer.summarize("Content 3")

        assert len(summarizer.cache) == 3
        assert summarizer.cache_misses == 3
        assert summarizer.cache_hits == 0

        # Re-request first content (should hit cache with old summary)
        summary = await summarizer.summarize("Content 1")
        assert summary == "Summary 1"  # Cached value
        assert summarizer.cache_hits == 1

    async def test_empty_content(self):
        """Test summarization of empty content."""
        llm_client = MockLLMClient("")
        summarizer = MessageSummarizer(llm_client)

        summary = await summarizer.summarize("")
        assert summary == ""
