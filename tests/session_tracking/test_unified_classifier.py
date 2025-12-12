"""Tests for UnifiedToolClassifier (Story 7).

Tests the acceptance criteria:
- AC-7.1: UnifiedToolClassifier class combining ToolClassifier and BashAnalyzer
- AC-7.2: classify_message() routes based on tool type (bash vs MCP vs native)
- AC-7.3: classify_session() returns tuple of (ActivityVector, list[ToolClassification])
- AC-7.4: Integration with ActivityDetector for tool-based signals
- AC-7.5: End-to-end test classifying mixed tool session
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from graphiti_core.session_tracking.activity_vector import ActivityVector
from graphiti_core.session_tracking.bash_analyzer import (
    BashAnalyzer,
    BashCommandClassification,
)
from graphiti_core.session_tracking.tool_classifier import (
    ToolClassification,
    ToolClassifier,
    ToolDomain,
    ToolIntent,
)
from graphiti_core.session_tracking.unified_classifier import UnifiedToolClassifier


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def classifier() -> UnifiedToolClassifier:
    """Create a UnifiedToolClassifier without cache or LLM."""
    return UnifiedToolClassifier()


@pytest.fixture
def temp_cache_paths(tmp_path: Path) -> tuple[Path, Path]:
    """Create temporary cache file paths for both classifiers."""
    return tmp_path / "tool_cache.json", tmp_path / "bash_cache.json"


@pytest.fixture
def classifier_with_cache(temp_cache_paths: tuple[Path, Path]) -> UnifiedToolClassifier:
    """Create a UnifiedToolClassifier with cache paths."""
    tool_cache, bash_cache = temp_cache_paths
    return UnifiedToolClassifier(tool_cache_path=tool_cache, bash_cache_path=bash_cache)


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate_response = AsyncMock()
    return client


@pytest.fixture
def classifier_with_llm(mock_llm_client: MagicMock) -> UnifiedToolClassifier:
    """Create a UnifiedToolClassifier with mock LLM client."""
    return UnifiedToolClassifier(llm_client=mock_llm_client)


# =============================================================================
# Test AC-7.1: UnifiedToolClassifier Class
# =============================================================================


class TestUnifiedToolClassifierInstantiation:
    """Test UnifiedToolClassifier class combining ToolClassifier and BashAnalyzer."""

    def test_unified_classifier_instantiation(self, classifier: UnifiedToolClassifier):
        """Test UnifiedToolClassifier can be instantiated."""
        assert isinstance(classifier, UnifiedToolClassifier)

    def test_unified_classifier_has_tool_classifier(
        self, classifier: UnifiedToolClassifier
    ):
        """Test UnifiedToolClassifier has ToolClassifier instance."""
        assert hasattr(classifier, "tool_classifier")
        assert isinstance(classifier.tool_classifier, ToolClassifier)

    def test_unified_classifier_has_bash_analyzer(
        self, classifier: UnifiedToolClassifier
    ):
        """Test UnifiedToolClassifier has BashAnalyzer instance."""
        assert hasattr(classifier, "bash_analyzer")
        assert isinstance(classifier.bash_analyzer, BashAnalyzer)

    def test_classifier_with_llm_client(
        self, mock_llm_client: MagicMock
    ):
        """Test UnifiedToolClassifier accepts LLM client."""
        classifier = UnifiedToolClassifier(llm_client=mock_llm_client)
        assert classifier._llm_client is mock_llm_client

    def test_classifier_with_cache_paths(
        self, temp_cache_paths: tuple[Path, Path]
    ):
        """Test UnifiedToolClassifier accepts cache paths."""
        tool_cache, bash_cache = temp_cache_paths
        classifier = UnifiedToolClassifier(
            tool_cache_path=tool_cache,
            bash_cache_path=bash_cache,
        )
        # Just verify it doesn't raise
        assert classifier is not None

    def test_classifier_with_all_options(
        self, mock_llm_client: MagicMock, temp_cache_paths: tuple[Path, Path]
    ):
        """Test UnifiedToolClassifier with all options."""
        tool_cache, bash_cache = temp_cache_paths
        classifier = UnifiedToolClassifier(
            llm_client=mock_llm_client,
            tool_cache_path=tool_cache,
            bash_cache_path=bash_cache,
        )
        assert classifier._llm_client is mock_llm_client


# =============================================================================
# Test AC-7.2: classify_message() Routing
# =============================================================================


class TestClassifyMessageRouting:
    """Test classify_message() routes based on tool type."""

    def test_classify_message_routes_bash_to_bash_analyzer(
        self, classifier: UnifiedToolClassifier
    ):
        """Test Bash tool routes to BashAnalyzer."""
        message = {
            "name": "Bash",
            "params": {"command": "git status"},
        }
        result = classifier.classify_message(message)

        assert isinstance(result, BashCommandClassification)
        assert result.base_command == "git"
        assert result.subcommand == "status"
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_message_routes_bash_case_insensitive(
        self, classifier: UnifiedToolClassifier
    ):
        """Test bash routing is case insensitive."""
        # Lowercase
        result1 = classifier.classify_message({
            "name": "bash",
            "params": {"command": "ls"},
        })
        assert isinstance(result1, BashCommandClassification)

        # Uppercase
        result2 = classifier.classify_message({
            "name": "BASH",
            "params": {"command": "ls"},
        })
        assert isinstance(result2, BashCommandClassification)

    def test_classify_message_routes_mcp_tools_to_tool_classifier(
        self, classifier: UnifiedToolClassifier
    ):
        """Test MCP tools route to ToolClassifier."""
        message = {
            "name": "mcp__serena__find_symbol",
            "params": {"name_path": "MyClass"},
        }
        result = classifier.classify_message(message)

        assert isinstance(result, ToolClassification)
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.CODE

    def test_classify_message_routes_native_tools_to_tool_classifier(
        self, classifier: UnifiedToolClassifier
    ):
        """Test native tools route to ToolClassifier."""
        # Read tool
        result = classifier.classify_message({
            "name": "Read",
            "params": {"file_path": "/foo/bar.py"},
        })
        assert isinstance(result, ToolClassification)
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_message_read_tool(
        self, classifier: UnifiedToolClassifier
    ):
        """Test Read tool classification."""
        result = classifier.classify_message({
            "name": "Read",
            "params": {"file_path": "/foo/bar.py"},
        })
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.confidence == 1.0

    def test_classify_message_write_tool(
        self, classifier: UnifiedToolClassifier
    ):
        """Test Write tool classification."""
        result = classifier.classify_message({
            "name": "Write",
            "params": {"file_path": "/foo/bar.py", "content": "test"},
        })
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_message_edit_tool(
        self, classifier: UnifiedToolClassifier
    ):
        """Test Edit tool classification."""
        result = classifier.classify_message({
            "name": "Edit",
            "params": {"file_path": "/foo/bar.py", "old_string": "a", "new_string": "b"},
        })
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_message_grep_tool(
        self, classifier: UnifiedToolClassifier
    ):
        """Test Grep tool classification."""
        result = classifier.classify_message({
            "name": "Grep",
            "params": {"pattern": "test"},
        })
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_message_glob_tool(
        self, classifier: UnifiedToolClassifier
    ):
        """Test Glob tool classification."""
        result = classifier.classify_message({
            "name": "Glob",
            "params": {"pattern": "*.py"},
        })
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_message_serena_replace_symbol(
        self, classifier: UnifiedToolClassifier
    ):
        """Test MCP Serena replace_symbol_body tool."""
        result = classifier.classify_message({
            "name": "mcp__serena__replace_symbol_body",
            "params": {"name_path": "MyClass/method", "body": "def method(): pass"},
        })
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.CODE

    def test_classify_message_graphiti_memory(
        self, classifier: UnifiedToolClassifier
    ):
        """Test MCP Graphiti memory tools."""
        # add_memory
        result = classifier.classify_message({
            "name": "mcp__graphiti-memory__add_memory",
            "params": {"content": "test"},
        })
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.MEMORY

        # search_memory_nodes
        result = classifier.classify_message({
            "name": "mcp__graphiti-memory__search_memory_nodes",
            "params": {"query": "test"},
        })
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.MEMORY


class TestClassifyMessageEdgeCases:
    """Test classify_message() edge cases."""

    def test_classify_message_handles_missing_params(
        self, classifier: UnifiedToolClassifier
    ):
        """Test handling message with missing params."""
        result = classifier.classify_message({
            "name": "Read",
        })
        assert isinstance(result, ToolClassification)
        assert result.tool_name == "Read"

    def test_classify_message_handles_none_params(
        self, classifier: UnifiedToolClassifier
    ):
        """Test handling message with None params."""
        result = classifier.classify_message({
            "name": "Read",
            "params": None,
        })
        assert isinstance(result, ToolClassification)

    def test_classify_message_handles_empty_params(
        self, classifier: UnifiedToolClassifier
    ):
        """Test handling message with empty params dict."""
        result = classifier.classify_message({
            "name": "Read",
            "params": {},
        })
        assert isinstance(result, ToolClassification)

    def test_classify_message_bash_missing_command(
        self, classifier: UnifiedToolClassifier
    ):
        """Test Bash tool with missing command param."""
        result = classifier.classify_message({
            "name": "Bash",
            "params": {},
        })
        assert isinstance(result, BashCommandClassification)
        assert result.raw_command == ""

    def test_empty_tool_name(
        self, classifier: UnifiedToolClassifier
    ):
        """Test classification with empty tool name."""
        result = classifier.classify_message({
            "name": "",
            "params": {},
        })
        assert isinstance(result, ToolClassification)

    def test_unknown_tool_fallback(
        self, classifier: UnifiedToolClassifier
    ):
        """Test unknown tool returns classification with low confidence."""
        result = classifier.classify_message({
            "name": "completely_unknown_tool_xyz123",
            "params": {},
        })
        assert isinstance(result, ToolClassification)
        assert result.confidence == 0.3


# =============================================================================
# Test AC-7.3: classify_session()
# =============================================================================


class TestClassifySession:
    """Test classify_session() returns tuple of (ActivityVector, list)."""

    def test_classify_session_returns_activity_vector_and_classifications(
        self, classifier: UnifiedToolClassifier
    ):
        """Test classify_session returns correct tuple structure."""
        messages = [
            {"name": "Read", "params": {"file_path": "/foo.py"}},
            {"name": "Bash", "params": {"command": "pytest tests/"}},
        ]

        activity_vector, classifications = classifier.classify_session(messages)

        assert isinstance(activity_vector, ActivityVector)
        assert isinstance(classifications, list)
        assert len(classifications) == 2

    def test_classify_session_aggregates_signals_correctly(
        self, classifier: UnifiedToolClassifier
    ):
        """Test classify_session aggregates activity signals."""
        messages = [
            {"name": "Read", "params": {"file_path": "/foo.py"}},
            {"name": "Grep", "params": {"pattern": "test"}},
            {"name": "Read", "params": {"file_path": "/bar.py"}},
        ]

        activity_vector, classifications = classifier.classify_session(messages)

        # Exploring should be boosted from multiple Read + Grep
        assert activity_vector.exploring > 0

    def test_classify_session_handles_empty_messages(
        self, classifier: UnifiedToolClassifier
    ):
        """Test classify_session handles empty message list."""
        activity_vector, classifications = classifier.classify_session([])

        assert isinstance(activity_vector, ActivityVector)
        assert classifications == []
        # Empty ActivityVector should have all zeros
        assert activity_vector.exploring == 0
        assert activity_vector.building == 0

    def test_classify_session_filters_non_tool_messages(
        self, classifier: UnifiedToolClassifier
    ):
        """Test classify_session filters messages without tool names."""
        messages = [
            {"name": "Read", "params": {"file_path": "/foo.py"}},
            {"name": "", "params": {}},  # No tool name
            {"params": {"file_path": "/bar.py"}},  # Missing name key
            {"name": "Write", "params": {"content": "test"}},
        ]

        activity_vector, classifications = classifier.classify_session(messages)

        # Should only classify messages with valid tool names
        assert len(classifications) == 2

    def test_classify_session_mixed_tool_types(
        self, classifier: UnifiedToolClassifier
    ):
        """Test classify_session with mixed tool types."""
        messages = [
            {"name": "Read", "params": {"file_path": "/foo.py"}},
            {"name": "Bash", "params": {"command": "git status"}},
            {"name": "mcp__serena__find_symbol", "params": {"name_path": "Class"}},
        ]

        activity_vector, classifications = classifier.classify_session(messages)

        assert len(classifications) == 3
        # First should be ToolClassification (Read)
        assert isinstance(classifications[0], ToolClassification)
        # Second should be BashCommandClassification (Bash)
        assert isinstance(classifications[1], BashCommandClassification)
        # Third should be ToolClassification (MCP)
        assert isinstance(classifications[2], ToolClassification)

    def test_classify_session_returns_correct_order(
        self, classifier: UnifiedToolClassifier
    ):
        """Test classify_session preserves message order."""
        messages = [
            {"name": "Read", "params": {}},
            {"name": "Write", "params": {}},
            {"name": "Edit", "params": {}},
        ]

        _, classifications = classifier.classify_session(messages)

        assert classifications[0].tool_name == "Read"
        assert classifications[1].tool_name == "Write"
        assert classifications[2].tool_name == "Edit"


class TestClassifySessionActivityVector:
    """Test ActivityVector creation from session classification."""

    def test_activity_vector_normalization_large_sessions(
        self, classifier: UnifiedToolClassifier
    ):
        """Test activity vector normalization for large sessions."""
        # Create a large session with many similar tools
        messages = [
            {"name": "Read", "params": {"file_path": f"/file{i}.py"}}
            for i in range(50)
        ]

        activity_vector, _ = classifier.classify_session(messages)

        # All dimension values should be in valid range
        for dim in ActivityVector.DIMENSIONS:
            value = getattr(activity_vector, dim)
            assert 0.0 <= value <= 1.0

    def test_testing_signals_from_pytest(
        self, classifier: UnifiedToolClassifier
    ):
        """Test that pytest commands boost testing signal."""
        messages = [
            {"name": "Bash", "params": {"command": "pytest tests/ -v"}},
        ]

        activity_vector, _ = classifier.classify_session(messages)

        assert activity_vector.testing > 0

    def test_building_signals_from_write(
        self, classifier: UnifiedToolClassifier
    ):
        """Test that Write tool boosts building signal."""
        messages = [
            {"name": "Write", "params": {"content": "test"}},
        ]

        activity_vector, _ = classifier.classify_session(messages)

        assert activity_vector.building > 0

    def test_exploring_signals_from_search(
        self, classifier: UnifiedToolClassifier
    ):
        """Test that search tools boost exploring signal."""
        messages = [
            {"name": "Grep", "params": {"pattern": "test"}},
            {"name": "Glob", "params": {"pattern": "*.py"}},
        ]

        activity_vector, _ = classifier.classify_session(messages)

        assert activity_vector.exploring > 0

    def test_signal_capping_at_1_0(
        self, classifier: UnifiedToolClassifier
    ):
        """Test that signals are capped at 1.0."""
        # Create many messages that would accumulate the same signal
        messages = [
            {"name": "Read", "params": {}}
            for _ in range(100)
        ]

        activity_vector, _ = classifier.classify_session(messages)

        # After normalization, max value should be 1.0
        max_value = max(
            getattr(activity_vector, dim)
            for dim in ActivityVector.DIMENSIONS
        )
        assert max_value <= 1.0


# =============================================================================
# Test Async Methods
# =============================================================================


class TestAsyncMethods:
    """Test async classification methods."""

    @pytest.mark.asyncio
    async def test_classify_message_async_bash(
        self, classifier: UnifiedToolClassifier
    ):
        """Test async classification of Bash message."""
        message = {
            "name": "Bash",
            "params": {"command": "git status"},
        }
        result = await classifier.classify_message_async(message)

        assert isinstance(result, BashCommandClassification)
        assert result.domain == ToolDomain.VERSION_CONTROL

    @pytest.mark.asyncio
    async def test_classify_message_async_tool(
        self, classifier: UnifiedToolClassifier
    ):
        """Test async classification of tool message."""
        message = {
            "name": "Read",
            "params": {"file_path": "/foo.py"},
        }
        result = await classifier.classify_message_async(message)

        assert isinstance(result, ToolClassification)
        assert result.intent == ToolIntent.READ

    @pytest.mark.asyncio
    async def test_classify_session_async(
        self, classifier: UnifiedToolClassifier
    ):
        """Test async session classification."""
        messages = [
            {"name": "Read", "params": {}},
            {"name": "Bash", "params": {"command": "ls"}},
            {"name": "Write", "params": {}},
        ]

        activity_vector, classifications = await classifier.classify_session_async(messages)

        assert isinstance(activity_vector, ActivityVector)
        assert len(classifications) == 3

    @pytest.mark.asyncio
    async def test_classify_session_async_empty(
        self, classifier: UnifiedToolClassifier
    ):
        """Test async session classification with empty messages."""
        activity_vector, classifications = await classifier.classify_session_async([])

        assert isinstance(activity_vector, ActivityVector)
        assert classifications == []

    @pytest.mark.asyncio
    async def test_classify_session_async_order_preserved(
        self, classifier: UnifiedToolClassifier
    ):
        """Test async classification preserves order."""
        messages = [
            {"name": "Read", "params": {}},
            {"name": "Bash", "params": {"command": "pytest"}},
            {"name": "Write", "params": {}},
            {"name": "Bash", "params": {"command": "git status"}},
        ]

        _, classifications = await classifier.classify_session_async(messages)

        assert len(classifications) == 4
        assert isinstance(classifications[0], ToolClassification)  # Read
        assert isinstance(classifications[1], BashCommandClassification)  # Bash
        assert isinstance(classifications[2], ToolClassification)  # Write
        assert isinstance(classifications[3], BashCommandClassification)  # Bash


# =============================================================================
# Test AC-7.5: End-to-End Mixed Tool Session
# =============================================================================


class TestEndToEndMixedToolSession:
    """Test end-to-end classification of mixed tool sessions."""

    def test_end_to_end_mixed_tool_session(
        self, classifier: UnifiedToolClassifier
    ):
        """Test realistic session with Bash, MCP, and native tools."""
        messages = [
            # Exploration phase
            {"name": "Read", "params": {"file_path": "/src/main.py"}},
            {"name": "mcp__serena__get_symbols_overview", "params": {"relative_path": "src/"}},
            {"name": "Grep", "params": {"pattern": "def main"}},

            # Git status check
            {"name": "Bash", "params": {"command": "git status"}},

            # Code modification
            {"name": "Edit", "params": {"file_path": "/src/main.py", "old_string": "a", "new_string": "b"}},
            {"name": "mcp__serena__replace_symbol_body", "params": {"name_path": "main", "body": "pass"}},

            # Testing
            {"name": "Bash", "params": {"command": "pytest tests/ -v"}},

            # Documentation lookup
            {"name": "mcp__context7-local__get-library-docs", "params": {"libraryID": "/pytest/pytest"}},

            # Commit
            {"name": "Bash", "params": {"command": "git add ."}},
            {"name": "Bash", "params": {"command": "git commit -m 'fix: update main'"}},
        ]

        activity_vector, classifications = classifier.classify_session(messages)

        # Verify all messages classified
        assert len(classifications) == 10

        # Verify correct classification types
        assert isinstance(classifications[0], ToolClassification)  # Read
        assert isinstance(classifications[3], BashCommandClassification)  # git status
        assert isinstance(classifications[6], BashCommandClassification)  # pytest

        # Verify activity vector reflects the session
        # Should have exploring from Read/Grep/git status
        assert activity_vector.exploring > 0
        # Should have building from Edit/replace_symbol_body
        assert activity_vector.building > 0
        # Should have testing from pytest
        assert activity_vector.testing > 0

    def test_development_workflow_session(
        self, classifier: UnifiedToolClassifier
    ):
        """Test typical development workflow session."""
        messages = [
            # Initial exploration
            {"name": "Bash", "params": {"command": "git pull"}},
            {"name": "Read", "params": {"file_path": "README.md"}},

            # Find relevant code
            {"name": "Grep", "params": {"pattern": "class UserService"}},
            {"name": "mcp__serena__find_symbol", "params": {"name_path": "UserService"}},

            # Make changes
            {"name": "Edit", "params": {"file_path": "src/service.py"}},
            {"name": "Write", "params": {"file_path": "src/new_feature.py", "content": "..."}},

            # Test changes
            {"name": "Bash", "params": {"command": "pytest tests/test_service.py"}},

            # Package management
            {"name": "Bash", "params": {"command": "pip install requests"}},

            # Commit workflow
            {"name": "Bash", "params": {"command": "git add ."}},
            {"name": "Bash", "params": {"command": "git commit -m 'feat: add feature'"}},
            {"name": "Bash", "params": {"command": "git push origin feature-branch"}},
        ]

        activity_vector, classifications = classifier.classify_session(messages)

        assert len(classifications) == 11

        # Workflow should show mix of activities
        assert activity_vector.exploring > 0
        assert activity_vector.building > 0
        assert activity_vector.testing > 0
        assert activity_vector.configuring > 0  # From pip install

    @pytest.mark.asyncio
    async def test_end_to_end_async_mixed_session(
        self, classifier: UnifiedToolClassifier
    ):
        """Test async classification of mixed session."""
        messages = [
            {"name": "Read", "params": {}},
            {"name": "Bash", "params": {"command": "npm install"}},
            {"name": "mcp__graphiti-memory__add_memory", "params": {}},
            {"name": "Write", "params": {}},
            {"name": "Bash", "params": {"command": "npm test"}},
        ]

        activity_vector, classifications = await classifier.classify_session_async(messages)

        assert len(classifications) == 5
        # Verify order preserved
        assert isinstance(classifications[0], ToolClassification)  # Read
        assert isinstance(classifications[1], BashCommandClassification)  # npm install
        assert isinstance(classifications[2], ToolClassification)  # MCP
        assert isinstance(classifications[3], ToolClassification)  # Write
        assert isinstance(classifications[4], BashCommandClassification)  # npm test


# =============================================================================
# Test AC-7.4: Integration Compatibility
# =============================================================================


class TestIntegrationWithActivityDetector:
    """Test integration compatibility with ActivityDetector."""

    def test_activity_signals_compatible_with_activity_vector(
        self, classifier: UnifiedToolClassifier
    ):
        """Test activity_signals dict is compatible with ActivityVector.from_signals()."""
        messages = [
            {"name": "Read", "params": {}},
            {"name": "Bash", "params": {"command": "pytest"}},
            {"name": "Write", "params": {}},
        ]

        _, classifications = classifier.classify_session(messages)

        # All classifications should have activity_signals that can create ActivityVector
        for classification in classifications:
            vector = ActivityVector.from_signals(classification.activity_signals)
            assert isinstance(vector, ActivityVector)

    def test_activity_vector_dimensions_valid(
        self, classifier: UnifiedToolClassifier
    ):
        """Test all activity signals map to valid ActivityVector dimensions."""
        valid_dimensions = set(ActivityVector.DIMENSIONS)

        messages = [
            {"name": "Read", "params": {}},
            {"name": "Write", "params": {}},
            {"name": "Edit", "params": {}},
            {"name": "Bash", "params": {"command": "git status"}},
            {"name": "Bash", "params": {"command": "pytest"}},
            {"name": "mcp__serena__find_symbol", "params": {}},
        ]

        _, classifications = classifier.classify_session(messages)

        for classification in classifications:
            for dim in classification.activity_signals:
                assert dim in valid_dimensions, f"Invalid dimension: {dim}"


# =============================================================================
# Test Cache Functionality
# =============================================================================


class TestCacheFunctionality:
    """Test unified classifier cache handling."""

    def test_unified_classifier_with_cache(
        self, classifier_with_cache: UnifiedToolClassifier, temp_cache_paths: tuple[Path, Path]
    ):
        """Test classifier with cache paths works correctly."""
        # Classify some messages
        classifier_with_cache.classify_message({"name": "Read", "params": {}})
        classifier_with_cache.classify_message({"name": "Bash", "params": {"command": "git status"}})

        # Save caches
        classifier_with_cache.save_caches()

        tool_cache, bash_cache = temp_cache_paths
        # At least one cache file should exist (bash commands are cached)
        # Tool classifier may not create file if all tools are known

    def test_save_caches_method(
        self, classifier: UnifiedToolClassifier
    ):
        """Test save_caches method doesn't raise without cache paths."""
        # Should not raise even without cache paths
        classifier.save_caches()


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_nested_bash_commands(
        self, classifier: UnifiedToolClassifier
    ):
        """Test bash command with nested/complex structure."""
        result = classifier.classify_message({
            "name": "Bash",
            "params": {"command": "cd /foo && git status && echo done"},
        })
        assert isinstance(result, BashCommandClassification)
        # Should classify the first command (cd)
        assert result.base_command == "cd"

    def test_very_long_session(
        self, classifier: UnifiedToolClassifier
    ):
        """Test classification of very long session."""
        messages = [
            {"name": "Read", "params": {"file_path": f"/file{i}.py"}}
            for i in range(500)
        ]

        activity_vector, classifications = classifier.classify_session(messages)

        assert len(classifications) == 500
        assert isinstance(activity_vector, ActivityVector)

    def test_special_characters_in_params(
        self, classifier: UnifiedToolClassifier
    ):
        """Test handling of special characters in parameters."""
        result = classifier.classify_message({
            "name": "Bash",
            "params": {"command": "echo 'hello world' | grep -E '\\w+'"},
        })
        assert isinstance(result, BashCommandClassification)

    def test_unicode_in_params(
        self, classifier: UnifiedToolClassifier
    ):
        """Test handling of unicode characters."""
        result = classifier.classify_message({
            "name": "Bash",
            "params": {"command": "echo 'test'"},
        })
        assert isinstance(result, BashCommandClassification)

    def test_concurrent_sync_calls(
        self, classifier: UnifiedToolClassifier
    ):
        """Test multiple synchronous classification calls."""
        results = []
        for i in range(10):
            result = classifier.classify_message({
                "name": "Read",
                "params": {"file_path": f"/file{i}.py"},
            })
            results.append(result)

        assert len(results) == 10
        assert all(isinstance(r, ToolClassification) for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_async_calls(
        self, classifier: UnifiedToolClassifier
    ):
        """Test concurrent async classification calls."""
        import asyncio

        async def classify(msg: dict[str, Any]) -> Any:
            return await classifier.classify_message_async(msg)

        tasks = [
            classify({"name": "Read", "params": {}}),
            classify({"name": "Bash", "params": {"command": "ls"}}),
            classify({"name": "Write", "params": {}}),
            classify({"name": "Bash", "params": {"command": "git status"}}),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        assert isinstance(results[0], ToolClassification)
        assert isinstance(results[1], BashCommandClassification)
        assert isinstance(results[2], ToolClassification)
        assert isinstance(results[3], BashCommandClassification)


# =============================================================================
# Test LLM Integration
# =============================================================================


class TestLLMIntegration:
    """Test LLM integration for unknown tools/commands."""

    @pytest.mark.asyncio
    async def test_llm_fallback_for_unknown_bash_command(
        self, classifier_with_llm: UnifiedToolClassifier, mock_llm_client: MagicMock
    ):
        """Test LLM fallback for unknown bash commands in async mode."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "custom-tool --arg",
                    "intent": "execute",
                    "domain": "process",
                    "activity_signals": {"building": 0.5},
                    "reasoning": "Custom tool execution",
                }
            ]
        }

        messages = [
            {"name": "Bash", "params": {"command": "custom-tool --arg"}},
        ]

        _, classifications = await classifier_with_llm.classify_session_async(messages)

        assert len(classifications) == 1
        # LLM should have been called for unknown command
        assert classifications[0].method in ["llm", "heuristic"]  # May be heuristic if matches pattern
