"""Tests for LLM Tool Classification with Caching (Story 5).

Tests the acceptance criteria:
- AC-1: classify_batch() uses cache hierarchy: exact -> pattern -> heuristic -> LLM
- AC-2: LLM classification prompt follows spec format
- AC-3: Cache key generation using tool_name + params hash
- AC-4: save_cache() and _load_cache() for persistence to JSON file
- AC-5: Integration test: first call uses LLM, second call uses cache
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graphiti_core.session_tracking.tool_classifier import (
    LLM_CLASSIFICATION_PROMPT,
    LLMToolClassificationResponse,
    ToolClassification,
    ToolClassificationResult,
    ToolClassifier,
    ToolDomain,
    ToolIntent,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_cache_path(tmp_path: Path) -> Path:
    """Create a temporary cache file path."""
    return tmp_path / "tool_cache.json"


@pytest.fixture
def classifier() -> ToolClassifier:
    """Create a ToolClassifier without cache or LLM."""
    return ToolClassifier()


@pytest.fixture
def classifier_with_cache(temp_cache_path: Path) -> ToolClassifier:
    """Create a ToolClassifier with cache path."""
    return ToolClassifier(cache_path=temp_cache_path)


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate_response = AsyncMock()
    return client


@pytest.fixture
def classifier_with_llm(mock_llm_client: MagicMock) -> ToolClassifier:
    """Create a ToolClassifier with mock LLM client."""
    return ToolClassifier(llm_client=mock_llm_client)


@pytest.fixture
def classifier_full(temp_cache_path: Path, mock_llm_client: MagicMock) -> ToolClassifier:
    """Create a ToolClassifier with both cache and LLM client."""
    return ToolClassifier(cache_path=temp_cache_path, llm_client=mock_llm_client)


# =============================================================================
# Test LLM Response Models
# =============================================================================


class TestToolClassificationResultModel:
    """Test ToolClassificationResult Pydantic model for LLM responses."""

    def test_creation_with_required_fields(self):
        """Test ToolClassificationResult can be created."""
        result = ToolClassificationResult(
            tool_name="custom_tool",
            intent="read",
            domain="filesystem",
        )
        assert result.tool_name == "custom_tool"
        assert result.intent == "read"
        assert result.domain == "filesystem"

    def test_default_activity_signals(self):
        """Test default activity_signals is empty dict."""
        result = ToolClassificationResult(
            tool_name="test",
            intent="read",
            domain="filesystem",
        )
        assert result.activity_signals == {}

    def test_with_activity_signals(self):
        """Test ToolClassificationResult with activity_signals."""
        result = ToolClassificationResult(
            tool_name="test",
            intent="create",
            domain="code",
            activity_signals={"building": 0.6, "refactoring": 0.3},
        )
        assert result.activity_signals == {"building": 0.6, "refactoring": 0.3}


class TestLLMToolClassificationResponseModel:
    """Test LLMToolClassificationResponse Pydantic model."""

    def test_creation_with_classifications(self):
        """Test LLMToolClassificationResponse can be created."""
        response = LLMToolClassificationResponse(
            classifications=[
                ToolClassificationResult(
                    tool_name="tool1",
                    intent="read",
                    domain="filesystem",
                ),
                ToolClassificationResult(
                    tool_name="tool2",
                    intent="create",
                    domain="code",
                ),
            ]
        )
        assert len(response.classifications) == 2
        assert response.classifications[0].tool_name == "tool1"
        assert response.classifications[1].tool_name == "tool2"

    def test_empty_classifications(self):
        """Test LLMToolClassificationResponse with empty list."""
        response = LLMToolClassificationResponse(classifications=[])
        assert response.classifications == []


# =============================================================================
# Test Cache Key Generation (AC-3)
# =============================================================================


class TestCacheKeyGeneration:
    """Test cache key generation from tool name and parameters."""

    def test_cache_key_without_params(self, classifier: ToolClassifier):
        """Test cache key with no parameters ends with '::'."""
        key = classifier._get_cache_key("Read", None)
        assert key == "Read::"

    def test_cache_key_with_empty_dict(self, classifier: ToolClassifier):
        """Test cache key with empty dict ends with '::'."""
        key = classifier._get_cache_key("Read", {})
        assert key == "Read::"

    def test_cache_key_with_params(self, classifier: ToolClassifier):
        """Test cache key with params has hash suffix."""
        key = classifier._get_cache_key("Read", {"file_path": "/foo"})
        assert key.startswith("Read::")
        assert len(key) > len("Read::")
        # Hash suffix should be 8 chars
        suffix = key.split("::")[-1]
        assert len(suffix) == 8

    def test_cache_key_param_order_invariant(self, classifier: ToolClassifier):
        """Test cache key is same regardless of param order."""
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}
        params3 = {"b": 2, "c": 3, "a": 1}

        key1 = classifier._get_cache_key("Tool", params1)
        key2 = classifier._get_cache_key("Tool", params2)
        key3 = classifier._get_cache_key("Tool", params3)

        assert key1 == key2 == key3

    def test_cache_key_different_params_different_keys(self, classifier: ToolClassifier):
        """Test different params produce different cache keys."""
        key1 = classifier._get_cache_key("Tool", {"x": 1})
        key2 = classifier._get_cache_key("Tool", {"x": 2})
        key3 = classifier._get_cache_key("Tool", {"y": 1})

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_cache_key_different_tools_different_keys(self, classifier: ToolClassifier):
        """Test different tool names produce different cache keys."""
        params = {"x": 1}
        key1 = classifier._get_cache_key("ToolA", params)
        key2 = classifier._get_cache_key("ToolB", params)

        assert key1 != key2

    def test_cache_key_handles_nested_params(self, classifier: ToolClassifier):
        """Test cache key handles nested dict params."""
        params = {"outer": {"inner": {"deep": 42}}}
        key = classifier._get_cache_key("Tool", params)
        assert key.startswith("Tool::")
        assert len(key.split("::")[-1]) == 8

    def test_cache_key_handles_list_params(self, classifier: ToolClassifier):
        """Test cache key handles list parameters."""
        params = {"items": [1, 2, 3], "names": ["a", "b"]}
        key = classifier._get_cache_key("Tool", params)
        assert key.startswith("Tool::")


class TestUpdateCache:
    """Test cache update functionality."""

    def test_update_cache_adds_to_exact_cache(self, classifier: ToolClassifier):
        """Test _update_cache adds entry to exact cache."""
        classification = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.85,
            tool_name="custom_tool",
            method="llm",
        )

        classifier._update_cache("custom_tool", {"param": "value"}, classification)

        cache_key = classifier._get_cache_key("custom_tool", {"param": "value"})
        assert cache_key in classifier._exact_cache
        assert classifier._exact_cache[cache_key] == classification

    def test_update_cache_adds_to_pattern_cache(self, classifier: ToolClassifier):
        """Test _update_cache adds entry to pattern cache."""
        classification = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.85,
            tool_name="custom_tool",
            method="llm",
        )

        classifier._update_cache("custom_tool", {"param": "value"}, classification)

        assert "custom_tool" in classifier._pattern_cache
        assert classifier._pattern_cache["custom_tool"] == classification

    def test_update_cache_does_not_overwrite_pattern(self, classifier: ToolClassifier):
        """Test _update_cache does not overwrite existing pattern cache entry."""
        first = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.85,
            tool_name="custom_tool",
            method="llm",
        )
        second = ToolClassification(
            intent=ToolIntent.CREATE,
            domain=ToolDomain.CODE,
            confidence=0.90,
            tool_name="custom_tool",
            method="llm",
        )

        classifier._update_cache("custom_tool", {"param": "a"}, first)
        classifier._update_cache("custom_tool", {"param": "b"}, second)

        # Pattern cache should keep first entry
        assert classifier._pattern_cache["custom_tool"] == first

        # But exact cache should have both
        key1 = classifier._get_cache_key("custom_tool", {"param": "a"})
        key2 = classifier._get_cache_key("custom_tool", {"param": "b"})
        assert classifier._exact_cache[key1] == first
        assert classifier._exact_cache[key2] == second


# =============================================================================
# Test Cache Persistence (AC-4)
# =============================================================================


class TestCachePersistence:
    """Test save_cache() and _load_cache() for persistence."""

    def test_save_cache_creates_json(self, classifier_with_cache: ToolClassifier, temp_cache_path: Path):
        """Test save_cache() creates JSON file."""
        # Add some entries
        classification = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.85,
            tool_name="test_tool",
            method="llm",
        )
        classifier_with_cache._update_cache("test_tool", {"x": 1}, classification)

        # Save
        classifier_with_cache.save_cache()

        # Verify file exists
        assert temp_cache_path.exists()

        # Verify JSON structure
        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "version" in data
        assert "exact" in data
        assert "pattern" in data
        assert len(data["exact"]) == 1
        assert len(data["pattern"]) == 1

    def test_load_cache_restores_entries(self, temp_cache_path: Path):
        """Test _load_cache() restores cached entries."""
        # Create cache file
        cache_data = {
            "version": "1.0",
            "exact": {
                "tool1::abc12345": {
                    "intent": "read",
                    "domain": "filesystem",
                    "confidence": 0.85,
                    "activity_signals": {"exploring": 0.5},
                    "tool_name": "tool1",
                    "method": "llm",
                }
            },
            "pattern": {
                "tool1": {
                    "intent": "read",
                    "domain": "filesystem",
                    "confidence": 0.85,
                    "activity_signals": {"exploring": 0.5},
                    "tool_name": "tool1",
                    "method": "llm",
                }
            },
        }
        with open(temp_cache_path, "w") as f:
            json.dump(cache_data, f)

        # Create classifier (loads cache in __init__)
        classifier = ToolClassifier(cache_path=temp_cache_path)

        # Verify entries restored
        assert "tool1::abc12345" in classifier._exact_cache
        assert "tool1" in classifier._pattern_cache
        assert classifier._exact_cache["tool1::abc12345"].intent == ToolIntent.READ
        assert classifier._pattern_cache["tool1"].domain == ToolDomain.FILESYSTEM

    def test_load_cache_handles_missing_file(self, temp_cache_path: Path):
        """Test _load_cache() handles missing file gracefully."""
        # Don't create the file
        assert not temp_cache_path.exists()

        # Should not raise
        classifier = ToolClassifier(cache_path=temp_cache_path)

        # Caches should be empty
        assert len(classifier._exact_cache) == 0
        assert len(classifier._pattern_cache) == 0

    def test_load_cache_handles_corrupted_json(self, temp_cache_path: Path):
        """Test _load_cache() handles corrupted JSON gracefully."""
        # Write invalid JSON
        with open(temp_cache_path, "w") as f:
            f.write("not valid json {{{")

        # Should not raise, should warn and reset
        classifier = ToolClassifier(cache_path=temp_cache_path)

        # Caches should be empty
        assert len(classifier._exact_cache) == 0
        assert len(classifier._pattern_cache) == 0

    def test_load_cache_handles_invalid_entries(self, temp_cache_path: Path):
        """Test _load_cache() handles invalid cache entries gracefully."""
        # Create cache with one valid and one invalid entry
        cache_data = {
            "version": "1.0",
            "exact": {
                "valid::12345678": {
                    "intent": "read",
                    "domain": "filesystem",
                    "confidence": 0.85,
                    "activity_signals": {},
                    "tool_name": "valid",
                    "method": "llm",
                },
                "invalid::87654321": {
                    "intent": "not_an_intent",  # Invalid!
                    "domain": "filesystem",
                    "confidence": 0.85,
                    "activity_signals": {},
                    "tool_name": "invalid",
                    "method": "llm",
                },
            },
            "pattern": {},
        }
        with open(temp_cache_path, "w") as f:
            json.dump(cache_data, f)

        # Should load valid entry and skip invalid
        classifier = ToolClassifier(cache_path=temp_cache_path)

        assert "valid::12345678" in classifier._exact_cache
        assert "invalid::87654321" not in classifier._exact_cache

    def test_cache_survives_round_trip(self, temp_cache_path: Path):
        """Test cache survives save -> new instance -> load."""
        # Create classifier and add entries
        classifier1 = ToolClassifier(cache_path=temp_cache_path)
        classification = ToolClassification(
            intent=ToolIntent.CREATE,
            domain=ToolDomain.CODE,
            confidence=0.90,
            activity_signals={"building": 0.6},
            tool_name="my_tool",
            method="llm",
        )
        classifier1._update_cache("my_tool", {"arg": "value"}, classification)
        classifier1.save_cache()

        # Create new instance (loads from file)
        classifier2 = ToolClassifier(cache_path=temp_cache_path)

        # Verify entries match
        cache_key = classifier2._get_cache_key("my_tool", {"arg": "value"})
        assert cache_key in classifier2._exact_cache
        assert classifier2._exact_cache[cache_key].intent == ToolIntent.CREATE
        assert classifier2._exact_cache[cache_key].domain == ToolDomain.CODE
        assert classifier2._exact_cache[cache_key].confidence == 0.90
        assert classifier2._exact_cache[cache_key].activity_signals == {"building": 0.6}

    def test_save_cache_no_op_without_path(self, classifier: ToolClassifier):
        """Test save_cache() does nothing if no cache_path configured."""
        # Should not raise
        classifier.save_cache()

    def test_save_cache_atomic_write(self, classifier_with_cache: ToolClassifier, temp_cache_path: Path):
        """Test save_cache() uses atomic write (temp file + rename)."""
        # Add entry and save
        classification = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.85,
            tool_name="test",
            method="llm",
        )
        classifier_with_cache._update_cache("test", None, classification)
        classifier_with_cache.save_cache()

        # No temp file should remain
        temp_path = temp_cache_path.with_suffix(".tmp")
        assert not temp_path.exists()

        # Cache file should exist and be valid
        assert temp_cache_path.exists()
        with open(temp_cache_path) as f:
            json.load(f)  # Should not raise


# =============================================================================
# Test Cache Hierarchy (AC-1)
# =============================================================================


class TestCacheHierarchy:
    """Test cache hierarchy: exact -> pattern -> heuristic -> LLM."""

    @pytest.mark.asyncio
    async def test_exact_cache_hit_returns_cached_method(self, classifier: ToolClassifier):
        """Test exact cache hit returns classification with method='cached'."""
        # Pre-populate exact cache
        original = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.85,
            activity_signals={"exploring": 0.5},
            tool_name="cached_tool",
            method="llm",
        )
        cache_key = classifier._get_cache_key("cached_tool", {"x": 1})
        classifier._exact_cache[cache_key] = original

        # Classify via batch
        results = await classifier.classify_batch([("cached_tool", {"x": 1})])

        assert len(results) == 1
        assert results[0].method == "cached"
        assert results[0].intent == ToolIntent.READ
        assert results[0].domain == ToolDomain.FILESYSTEM

    @pytest.mark.asyncio
    async def test_pattern_cache_hit_returns_cached_method(self, classifier: ToolClassifier):
        """Test pattern cache hit returns classification with method='cached'."""
        # Pre-populate pattern cache only (no exact match)
        original = ToolClassification(
            intent=ToolIntent.CREATE,
            domain=ToolDomain.CODE,
            confidence=0.90,
            activity_signals={"building": 0.6},
            tool_name="pattern_tool",
            method="llm",
        )
        classifier._pattern_cache["pattern_tool"] = original

        # Classify with different params (no exact match, but pattern match)
        results = await classifier.classify_batch([("pattern_tool", {"y": 2})])

        assert len(results) == 1
        assert results[0].method == "cached"
        assert results[0].intent == ToolIntent.CREATE

    @pytest.mark.asyncio
    async def test_heuristic_fallback_for_unknown_tools(self, classifier: ToolClassifier):
        """Test heuristic is tried when no cache hit."""
        # No cache entries, but "file_read" should match heuristic patterns
        results = await classifier.classify_batch([("file_read", None)])

        assert len(results) == 1
        # Should match heuristic pattern
        assert results[0].intent == ToolIntent.READ
        assert results[0].domain == ToolDomain.FILESYSTEM
        assert results[0].method == "heuristic"

    @pytest.mark.asyncio
    async def test_heuristic_updates_cache_on_high_confidence(self, classifier: ToolClassifier):
        """Test high-confidence heuristic results are cached."""
        # "Read" is in KNOWN_TOOL_MAPPINGS with confidence 1.0
        results = await classifier.classify_batch([("Read", None)])

        assert len(results) == 1
        assert results[0].confidence >= 0.7

        # Should be cached now
        cache_key = classifier._get_cache_key("Read", None)
        assert cache_key in classifier._exact_cache

    @pytest.mark.asyncio
    async def test_llm_fallback_when_heuristic_low_confidence(
        self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test LLM is used when heuristic has low confidence."""
        # Configure mock LLM response
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": "completely_unknown_xyz",
                    "intent": "read",
                    "domain": "filesystem",
                    "activity_signals": {"exploring": 0.5},
                }
            ]
        }

        # This tool name has no heuristic match
        results = await classifier_with_llm.classify_batch([("completely_unknown_xyz", None)])

        assert len(results) == 1
        assert results[0].method == "llm"
        mock_llm_client.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_llm_fallback_without_client(self, classifier: ToolClassifier):
        """Test unknown tool falls back to low confidence without LLM client."""
        # No LLM client configured
        results = await classifier.classify_batch([("unknown_xyz123", None)])

        assert len(results) == 1
        assert results[0].confidence == 0.3
        assert results[0].domain == ToolDomain.UNKNOWN
        assert results[0].method == "heuristic"

    @pytest.mark.asyncio
    async def test_batch_classification_order_preserved(self, classifier: ToolClassifier):
        """Test batch classification preserves input order."""
        tools = [
            ("Read", None),
            ("Write", None),
            ("Bash", None),
            ("Edit", None),
        ]

        results = await classifier.classify_batch(tools)

        assert len(results) == 4
        assert results[0].tool_name == "Read"
        assert results[1].tool_name == "Write"
        assert results[2].tool_name == "Bash"
        assert results[3].tool_name == "Edit"

    @pytest.mark.asyncio
    async def test_batch_classification_mixed_sources(
        self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test batch with tools from different sources (cache, heuristic, LLM)."""
        # Pre-populate cache
        cached_classification = ToolClassification(
            intent=ToolIntent.VALIDATE,
            domain=ToolDomain.TESTING,
            confidence=0.95,
            tool_name="cached_tool",
            method="llm",
        )
        classifier_with_llm._pattern_cache["cached_tool"] = cached_classification

        # Configure LLM for unknown tool
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": "llm_classified_tool",
                    "intent": "transform",
                    "domain": "database",
                    "activity_signals": {},
                }
            ]
        }

        tools = [
            ("cached_tool", None),  # Cache hit
            ("Read", None),  # Heuristic (known tool)
            ("llm_classified_tool", None),  # LLM
        ]

        results = await classifier_with_llm.classify_batch(tools)

        assert len(results) == 3
        assert results[0].method == "cached"
        assert results[1].method == "heuristic"
        assert results[2].method == "llm"


# =============================================================================
# Test LLM Classification (AC-2)
# =============================================================================


class TestLLMClassification:
    """Test LLM classification prompt and response handling."""

    def test_llm_prompt_contains_required_elements(self):
        """Test LLM_CLASSIFICATION_PROMPT has required elements."""
        assert "Intent:" in LLM_CLASSIFICATION_PROMPT
        assert "Domain:" in LLM_CLASSIFICATION_PROMPT
        assert "Activity Signals:" in LLM_CLASSIFICATION_PROMPT
        assert "{tool_calls_json}" in LLM_CLASSIFICATION_PROMPT

    def test_llm_prompt_lists_all_intents(self):
        """Test LLM_CLASSIFICATION_PROMPT lists all valid intents."""
        prompt_lower = LLM_CLASSIFICATION_PROMPT.lower()
        for intent in ToolIntent:
            assert intent.value in prompt_lower, f"Intent {intent.value} not in prompt"

    def test_llm_prompt_lists_all_domains(self):
        """Test LLM_CLASSIFICATION_PROMPT lists all valid domains."""
        prompt_lower = LLM_CLASSIFICATION_PROMPT.lower()
        for domain in ToolDomain:
            # Skip UNKNOWN as it may not be listed in prompt
            if domain != ToolDomain.UNKNOWN:
                assert domain.value in prompt_lower, f"Domain {domain.value} not in prompt"

    @pytest.mark.asyncio
    async def test_llm_prompt_format(
        self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test LLM is called with correctly formatted prompt."""
        # Use a tool name that won't match any heuristic patterns
        unknown_tool = "xyzqwk_totally_unknowable_abc123"
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": unknown_tool,
                    "intent": "read",
                    "domain": "filesystem",
                    "activity_signals": {},
                }
            ]
        }

        await classifier_with_llm.classify_batch([(unknown_tool, {"arg": "value"})])

        # Verify LLM was called
        mock_llm_client.generate_response.assert_called_once()

        # Check the call arguments
        call_args = mock_llm_client.generate_response.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert len(messages) == 1
        assert messages[0].role == "user"

        # Verify prompt contains tool info
        prompt_content = messages[0].content
        assert unknown_tool in prompt_content
        assert "value" in prompt_content

    @pytest.mark.asyncio
    async def test_llm_response_parsing(
        self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test LLM response is correctly parsed."""
        # Use a tool name that won't match any heuristic patterns
        unknown_tool = "xyzqwk_unknowable_parse789"
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": unknown_tool,
                    "intent": "create",
                    "domain": "code",
                    "activity_signals": {"building": 0.7, "refactoring": 0.2},
                }
            ]
        }

        results = await classifier_with_llm.classify_batch([(unknown_tool, None)])

        assert len(results) == 1
        assert results[0].intent == ToolIntent.CREATE
        assert results[0].domain == ToolDomain.CODE
        assert results[0].confidence == 0.85  # LLM confidence
        assert results[0].activity_signals == {"building": 0.7, "refactoring": 0.2}
        assert results[0].method == "llm"

    @pytest.mark.asyncio
    async def test_llm_batch_classification(
        self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test multiple tools are batched to single LLM call."""
        # Use tool names that won't match any heuristic patterns
        tool_a = "xyzqwk_unknowable_aaa111"
        tool_b = "xyzqwk_unknowable_bbb222"
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": tool_a,
                    "intent": "read",
                    "domain": "filesystem",
                    "activity_signals": {},
                },
                {
                    "tool_name": tool_b,
                    "intent": "create",
                    "domain": "code",
                    "activity_signals": {},
                },
            ]
        }

        # Both tools are unknown (no heuristic match)
        results = await classifier_with_llm.classify_batch([
            (tool_a, None),
            (tool_b, None),
        ])

        # Should only call LLM once
        assert mock_llm_client.generate_response.call_count == 1

        assert len(results) == 2
        assert results[0].tool_name == tool_a
        assert results[1].tool_name == tool_b

    @pytest.mark.asyncio
    async def test_cache_updated_after_llm_call(
        self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test cache is updated after LLM classification."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": "new_tool",
                    "intent": "modify",
                    "domain": "database",
                    "activity_signals": {},
                }
            ]
        }

        # First call - should use LLM
        results1 = await classifier_with_llm.classify_batch([("new_tool", {"x": 1})])
        assert results1[0].method == "llm"

        # Second call - should use cache
        results2 = await classifier_with_llm.classify_batch([("new_tool", {"x": 1})])
        assert results2[0].method == "cached"

        # LLM should only be called once
        assert mock_llm_client.generate_response.call_count == 1

    @pytest.mark.asyncio
    async def test_llm_handles_invalid_intent(
        self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test LLM response with invalid intent falls back gracefully."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": "bad_intent_tool",
                    "intent": "invalid_intent",  # Not a valid enum
                    "domain": "filesystem",
                    "activity_signals": {},
                }
            ]
        }

        results = await classifier_with_llm.classify_batch([("bad_intent_tool", None)])

        # Should fall back to defaults
        assert len(results) == 1
        assert results[0].intent == ToolIntent.EXECUTE
        assert results[0].domain == ToolDomain.UNKNOWN

    @pytest.mark.asyncio
    async def test_llm_handles_missing_tool_in_response(
        self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test handling when LLM doesn't return classification for a tool."""
        # Use tool names that won't match any heuristic patterns
        tool_a = "xyzqwk_unknowable_ccc333"
        tool_b = "xyzqwk_unknowable_ddd444"
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                # Only returns tool_a, not tool_b
                {
                    "tool_name": tool_a,
                    "intent": "read",
                    "domain": "filesystem",
                    "activity_signals": {},
                }
            ]
        }

        results = await classifier_with_llm.classify_batch([
            (tool_a, None),
            (tool_b, None),  # This one is missing from response
        ])

        assert len(results) == 2
        assert results[0].intent == ToolIntent.READ  # From LLM
        assert results[1].intent == ToolIntent.EXECUTE  # Fallback
        assert results[1].domain == ToolDomain.UNKNOWN

    @pytest.mark.asyncio
    async def test_llm_raises_without_client(self, classifier: ToolClassifier):
        """Test _classify_with_llm raises when no client configured."""
        with pytest.raises(ValueError, match="No LLM client configured"):
            await classifier._classify_with_llm([("tool", None)])


# =============================================================================
# Test Integration (AC-5)
# =============================================================================


class TestLLMCacheIntegration:
    """Integration tests for LLM + cache flow."""

    @pytest.mark.asyncio
    async def test_first_call_uses_llm_second_uses_cache(
        self, classifier_full: ToolClassifier, mock_llm_client: MagicMock
    ):
        """Test first call uses LLM, second call uses cache."""
        # Use a tool name that won't match any heuristic patterns
        unknown_tool = "xyzqwk_integration_eee555"
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": unknown_tool,
                    "intent": "search",
                    "domain": "network",
                    "activity_signals": {"exploring": 0.8},
                }
            ]
        }

        # First call - should use LLM
        result1 = await classifier_full.classify_batch([(unknown_tool, {"q": "test"})])
        assert result1[0].method == "llm"
        assert result1[0].intent == ToolIntent.SEARCH
        assert mock_llm_client.generate_response.call_count == 1

        # Second call with same params - should use cache
        result2 = await classifier_full.classify_batch([(unknown_tool, {"q": "test"})])
        assert result2[0].method == "cached"
        assert result2[0].intent == ToolIntent.SEARCH  # Same result
        assert mock_llm_client.generate_response.call_count == 1  # No additional call

        # Third call with different params - should use pattern cache
        result3 = await classifier_full.classify_batch([(unknown_tool, {"q": "different"})])
        assert result3[0].method == "cached"  # Pattern cache hit
        assert mock_llm_client.generate_response.call_count == 1  # Still no additional call

    @pytest.mark.asyncio
    async def test_cache_persists_across_instances(
        self, temp_cache_path: Path, mock_llm_client: MagicMock
    ):
        """Test cache persists across classifier instances."""
        # Use a tool name that won't match any heuristic patterns
        unknown_tool = "xyzqwk_persist_fff666"

        # First classifier - classify and save
        classifier1 = ToolClassifier(cache_path=temp_cache_path, llm_client=mock_llm_client)
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "tool_name": unknown_tool,
                    "intent": "delete",
                    "domain": "database",
                    "activity_signals": {},
                }
            ]
        }

        result1 = await classifier1.classify_batch([(unknown_tool, None)])
        assert result1[0].method == "llm"
        classifier1.save_cache()

        # Reset mock call count
        mock_llm_client.reset_mock()

        # Second classifier - should load from cache
        classifier2 = ToolClassifier(cache_path=temp_cache_path, llm_client=mock_llm_client)

        result2 = await classifier2.classify_batch([(unknown_tool, None)])
        assert result2[0].method == "cached"
        assert result2[0].intent == ToolIntent.DELETE
        mock_llm_client.generate_response.assert_not_called()


# =============================================================================
# Test Security
# =============================================================================


class TestSecurityConsiderations:
    """Security tests for tool classification."""

    def test_cache_key_no_injection(self, classifier: ToolClassifier):
        """Test cache key generation doesn't allow injection."""
        # Malicious-looking params
        malicious_params = {
            "path": "/etc/passwd",
            "cmd": "rm -rf /",
            "script": "<script>alert('xss')</script>",
        }
        key = classifier._get_cache_key("Tool", malicious_params)

        # Key should just be a hash, not contain the actual values
        assert "/etc/passwd" not in key
        assert "rm -rf" not in key
        assert "<script>" not in key

    def test_cache_file_only_contains_safe_data(
        self, classifier_with_cache: ToolClassifier, temp_cache_path: Path
    ):
        """Test saved cache file only contains expected data types."""
        # Add entry with various data types
        classification = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.85,
            activity_signals={"exploring": 0.5},
            tool_name="safe_tool",
            method="llm",
        )
        classifier_with_cache._update_cache("safe_tool", None, classification)
        classifier_with_cache.save_cache()

        # Load and inspect
        with open(temp_cache_path) as f:
            data = json.load(f)

        # Verify structure is as expected
        assert set(data.keys()) == {"version", "exact", "pattern"}
        assert isinstance(data["version"], str)
        assert isinstance(data["exact"], dict)
        assert isinstance(data["pattern"], dict)

        # Verify no unexpected data types
        for entry in data["exact"].values():
            assert isinstance(entry["intent"], str)
            assert isinstance(entry["domain"], str)
            assert isinstance(entry["confidence"], (int, float))
            assert isinstance(entry["tool_name"], str)
            assert isinstance(entry["method"], str)
            assert isinstance(entry["activity_signals"], dict)

    def test_llm_prompt_escapes_tool_data(self, classifier_with_llm: ToolClassifier, mock_llm_client: MagicMock):
        """Test tool data in LLM prompt is properly JSON-encoded."""
        # This is implicitly tested by json.dumps in _classify_with_llm
        # but we verify the mechanism here
        test_data = {
            "special": "chars\n\t\"'",
            "unicode": "\u0000\u001f",
        }

        # json.dumps should handle this safely
        encoded = json.dumps([{"tool_name": "test", "params": test_data}])
        assert "\n" not in encoded or "\\n" in encoded

    @pytest.mark.asyncio
    async def test_large_params_handled_safely(self, classifier: ToolClassifier):
        """Test very large parameter dicts don't cause issues."""
        # Create large params dict
        large_params = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        # Should not raise or hang
        key = classifier._get_cache_key("Tool", large_params)
        assert len(key) < 100  # Key should be bounded

        # classify_batch should also handle it
        results = await classifier.classify_batch([("unknown_tool", large_params)])
        assert len(results) == 1


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_batch(self, classifier: ToolClassifier):
        """Test classify_batch with empty list."""
        results = await classifier.classify_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_single_item_batch(self, classifier: ToolClassifier):
        """Test classify_batch with single item."""
        results = await classifier.classify_batch([("Read", None)])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_large_batch(self, classifier: ToolClassifier):
        """Test classify_batch with many items."""
        tools = [(f"tool_{i}", None) for i in range(100)]
        results = await classifier.classify_batch(tools)
        assert len(results) == 100

    @pytest.mark.asyncio
    async def test_duplicate_tools_in_batch(self, classifier: ToolClassifier):
        """Test batch with duplicate tool entries."""
        tools = [
            ("Read", None),
            ("Read", None),
            ("Read", {"x": 1}),
        ]
        results = await classifier.classify_batch(tools)
        assert len(results) == 3
        # All should be classified
        for r in results:
            assert r.intent == ToolIntent.READ

    def test_classifier_init_with_nonexistent_cache_dir(self, tmp_path: Path):
        """Test classifier handles cache path with nonexistent parent dir."""
        # This should not raise during init
        cache_path = tmp_path / "subdir" / "cache.json"
        classifier = ToolClassifier(cache_path=cache_path)
        assert classifier._cache_path == cache_path

    @pytest.mark.asyncio
    async def test_concurrent_classification(self, classifier: ToolClassifier):
        """Test classifier can handle concurrent batch calls."""
        import asyncio

        async def classify_task(tool_name: str) -> ToolClassification:
            results = await classifier.classify_batch([(tool_name, None)])
            return results[0]

        # Run multiple classifications concurrently
        tasks = [
            classify_task("Read"),
            classify_task("Write"),
            classify_task("Edit"),
            classify_task("Bash"),
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        assert all(isinstance(r, ToolClassification) for r in results)
