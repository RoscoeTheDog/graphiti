"""
Integration Tests for Cross-Project Search (Story 9).

This module tests cross-project search behavior and namespace filtering as implemented
in search_memory_nodes. Tests verify end-to-end behavior including:
- Cross-project search enabled/disabled behavior
- Trusted namespace filtering
- Metadata header parsing from search results
- All tests use mock Graphiti instance (no real Neo4j required)

Coverage target: >90% of cross-project search functionality
Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Section 9.2
"""

import pytest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import yaml


# =============================================================================
# FIXTURES
# =============================================================================


def parse_yaml_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter from content string.

    YAML frontmatter uses `---` as document start/end markers.
    Returns None if no valid frontmatter found.
    """
    if not content or not content.startswith("---"):
        return None

    # Find the closing ---
    try:
        # Skip the first ---
        second_marker = content.index("---", 3)
        yaml_content = content[3:second_marker].strip()
        return yaml.safe_load(yaml_content)
    except (ValueError, yaml.YAMLError):
        return None


def create_mock_node(
    namespace: str,
    content: str,
    uuid: str | None = None,
    name: str | None = None,
    include_frontmatter: bool = True,
) -> MagicMock:
    """Create a mock search result node with realistic structure.

    Args:
        namespace: The project namespace for this node
        content: The actual content/text of the episode
        uuid: Optional UUID (auto-generated if not provided)
        name: Optional name (auto-generated if not provided)
        include_frontmatter: Whether to include YAML frontmatter in summary
    """
    node = MagicMock()
    node.uuid = uuid or f"uuid-{namespace}-{hash(content) % 10000:04d}"
    node.name = name or f"Session from {namespace}"

    if include_frontmatter:
        node.summary = f"""---
graphiti_session_metadata:
  version: "2.0"
  project_namespace: {namespace}
  hostname: TEST-HOST
  indexed_at: "2025-12-10T00:00:00Z"
---

{content}
"""
    else:
        node.summary = content

    node.labels = ["EpisodicNode"]
    node.group_id = "TEST-HOST__global"
    node.created_at = datetime.now(timezone.utc)
    node.attributes = {"project_namespace": namespace}
    return node


@pytest.fixture
def mock_graphiti_client():
    """Create a mock Graphiti client with AsyncMock for _search."""
    mock = MagicMock()
    mock._search = AsyncMock()
    return mock


@pytest.fixture
def sample_episodes_multi_namespace():
    """Create sample search results from different project namespaces."""
    return [
        create_mock_node("proj_a", "Auth with JWT tokens"),
        create_mock_node("proj_b", "Auth with OAuth2 flow"),
        create_mock_node("proj_c", "Auth with SAML SSO"),
    ]


@pytest.fixture
def mock_session_tracking_config():
    """Create a mock SessionTrackingConfig with configurable fields."""
    config = MagicMock()
    config.cross_project_search = True
    config.trusted_namespaces = None
    config.group_id = None
    return config


@pytest.fixture
def mock_unified_config(mock_session_tracking_config):
    """Create mock unified config containing session tracking config."""
    config = MagicMock()
    config.session_tracking = mock_session_tracking_config
    return config


@pytest.fixture
def mock_search_results(sample_episodes_multi_namespace):
    """Create mock SearchResults object."""
    results = MagicMock()
    results.nodes = sample_episodes_multi_namespace
    return results


# =============================================================================
# TEST CLASS: Cross-Project Search Enabled (AC-9.1)
# =============================================================================


class TestCrossProjectSearchEnabled:
    """Tests for cross_project_search=true returns results from multiple projects."""

    @pytest.mark.asyncio
    async def test_returns_all_namespaces_when_enabled(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """AC-9.1 (P0): cross_project_search=true returns results from multiple projects."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        # Configure mock
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        # Set config for cross-project search enabled
        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        # Call search_memory_nodes with mocked dependencies
        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="authentication",
                group_ids=["TEST-HOST__global"],
                max_nodes=10,
            )

        # Verify all namespaces are returned
        # Response is TypedDict (dict), access via keys
        assert "nodes" in result, f"Unexpected response type: {type(result)}"
        assert len(result["nodes"]) == 3, f"Expected 3 nodes, got {len(result['nodes'])}"

        # Extract namespaces from results
        namespaces = set()
        for node in result["nodes"]:
            ns = extract_namespace_from_content(node.get("summary", ""))
            if ns:
                namespaces.add(ns)

        assert namespaces == {"proj_a", "proj_b", "proj_c"}

    @pytest.mark.asyncio
    async def test_no_filtering_with_no_trusted_namespaces(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """With cross_project_search=true and no trusted_namespaces, all results returned."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="auth",
                group_ids=["TEST-HOST__global"],
            )

        # All 3 nodes returned (no filtering applied)
        assert "nodes" in result
        assert len(result["nodes"]) == 3

    @pytest.mark.asyncio
    async def test_explicit_project_namespaces_override_config(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """Explicit project_namespaces parameter overrides config settings."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        # Config says cross-project enabled
        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            # Explicitly filter to only proj_a
            result = await search_memory_nodes(
                query="auth",
                group_ids=["TEST-HOST__global"],
                project_namespaces=["proj_a"],
            )

        # Only proj_a returned due to explicit parameter override
        assert "nodes" in result
        assert len(result["nodes"]) == 1
        assert "proj_a" in result["nodes"][0].get("summary", "")


# =============================================================================
# TEST CLASS: Cross-Project Search Disabled (AC-9.2)
# =============================================================================


class TestCrossProjectSearchDisabled:
    """Tests for cross_project_search=false returns only current project."""

    @pytest.mark.asyncio
    async def test_logs_warning_when_no_namespaces_provided(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """AC-9.2 (P0): Warning logged when cross_project_search=false without namespaces."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        # Disable cross-project search
        mock_unified_config.session_tracking.cross_project_search = False
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch(
            "mcp_server.graphiti_mcp_server.unified_config", mock_unified_config
        ), patch(
            "mcp_server.graphiti_mcp_server.logger"
        ) as mock_logger:
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            await search_memory_nodes(
                query="authentication",
                group_ids=["TEST-HOST__global"],
                # No project_namespaces provided
            )

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "cross_project_search is False" in warning_call
            assert "no project_namespaces provided" in warning_call

    @pytest.mark.asyncio
    async def test_filters_to_single_project_when_specified(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """AC-9.2 (P0): Only current project returned when namespace specified."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        # Disable cross-project search
        mock_unified_config.session_tracking.cross_project_search = False
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            # Specify current project namespace
            result = await search_memory_nodes(
                query="authentication",
                group_ids=["TEST-HOST__global"],
                project_namespaces=["proj_a"],
            )

        # Only proj_a results returned
        assert "nodes" in result
        assert len(result["nodes"]) == 1

        ns = extract_namespace_from_content(result["nodes"][0].get("summary", ""))
        assert ns == "proj_a"

    @pytest.mark.asyncio
    async def test_excludes_other_project_results(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """Results from other projects are excluded when filtering to current project."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = False
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="authentication",
                group_ids=["TEST-HOST__global"],
                project_namespaces=["proj_b"],  # Only proj_b
            )

        assert "nodes" in result
        assert len(result["nodes"]) == 1

        # Verify proj_a and proj_c are NOT in results
        for node in result["nodes"]:
            summary = node.get("summary", "")
            assert "proj_a" not in summary or "project_namespace: proj_a" not in summary
            assert "proj_c" not in summary or "project_namespace: proj_c" not in summary


# =============================================================================
# TEST CLASS: Trusted Namespaces Filter (AC-9.3)
# =============================================================================


class TestTrustedNamespacesFilter:
    """Tests for trusted_namespaces filters to specified projects."""

    @pytest.mark.asyncio
    async def test_filters_to_trusted_namespaces_only(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """AC-9.3 (P1): Only trusted namespace sessions returned."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        # Enable cross-project but with trusted namespaces
        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = ["proj_a", "proj_b"]

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="authentication",
                group_ids=["TEST-HOST__global"],
            )

        # Only proj_a and proj_b returned (trusted)
        assert "nodes" in result
        assert len(result["nodes"]) == 2

        namespaces = set()
        for node in result["nodes"]:
            ns = extract_namespace_from_content(node.get("summary", ""))
            if ns:
                namespaces.add(ns)

        assert namespaces == {"proj_a", "proj_b"}
        assert "proj_c" not in namespaces

    @pytest.mark.asyncio
    async def test_excludes_untrusted_namespace(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """Untrusted namespace (proj_c) is excluded from results."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        # Only trust proj_a
        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = ["proj_a"]

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="auth",
                group_ids=["TEST-HOST__global"],
            )

        assert "nodes" in result
        assert len(result["nodes"]) == 1

        # Verify proj_b and proj_c excluded
        for node in result["nodes"]:
            summary = node.get("summary", "")
            assert "project_namespace: proj_b" not in summary
            assert "project_namespace: proj_c" not in summary

    @pytest.mark.asyncio
    async def test_empty_trusted_namespaces_returns_all(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """Empty trusted_namespaces list means no filtering (return all)."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = []  # Empty list

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="auth",
                group_ids=["TEST-HOST__global"],
            )

        # Empty list is falsy, so no filtering applied
        assert "nodes" in result
        assert len(result["nodes"]) == 3


# =============================================================================
# TEST CLASS: Metadata Header Parseable (AC-9.4)
# =============================================================================


class TestMetadataHeaderParseable:
    """Tests for metadata header present and parseable in indexed episodes."""

    @pytest.mark.asyncio
    async def test_yaml_frontmatter_parseable(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """AC-9.4 (P1): Episode metadata header is parseable YAML."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="auth",
                group_ids=["TEST-HOST__global"],
            )

        # Verify YAML is parseable for each result
        for node in result["nodes"]:
            summary = node.get("summary", "")
            assert summary.startswith("---"), "Summary should start with YAML marker"

            frontmatter = parse_yaml_frontmatter(summary)
            assert frontmatter is not None, "Frontmatter should be parseable"
            assert (
                "graphiti_session_metadata" in frontmatter
            ), "Should contain graphiti_session_metadata"

    @pytest.mark.asyncio
    async def test_metadata_contains_project_namespace(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """Metadata contains project_namespace field."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="auth",
                group_ids=["TEST-HOST__global"],
            )

        for node in result["nodes"]:
            summary = node.get("summary", "")
            frontmatter = parse_yaml_frontmatter(summary)
            assert frontmatter is not None

            metadata = frontmatter.get("graphiti_session_metadata", {})
            assert (
                "project_namespace" in metadata
            ), "Metadata should contain project_namespace"
            assert metadata["project_namespace"] in {
                "proj_a",
                "proj_b",
                "proj_c",
            }, "project_namespace should be one of the test namespaces"

    @pytest.mark.asyncio
    async def test_metadata_contains_required_fields(
        self,
        mock_graphiti_client,
        mock_unified_config,
    ):
        """Metadata contains all required fields (version, hostname, indexed_at)."""
        # Create node with complete metadata
        node = create_mock_node("test_ns", "Test content")

        mock_search_results = MagicMock()
        mock_search_results.nodes = [node]
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="test",
                group_ids=["TEST-HOST__global"],
            )

        summary = result["nodes"][0].get("summary", "")
        frontmatter = parse_yaml_frontmatter(summary)
        assert frontmatter is not None

        metadata = frontmatter.get("graphiti_session_metadata", {})
        assert "version" in metadata, "Should contain version"
        assert "hostname" in metadata, "Should contain hostname"
        assert "indexed_at" in metadata, "Should contain indexed_at"
        assert "project_namespace" in metadata, "Should contain project_namespace"

    @pytest.mark.asyncio
    async def test_nodes_without_frontmatter_included(
        self,
        mock_graphiti_client,
        mock_unified_config,
    ):
        """Nodes without frontmatter are included (backward compatibility)."""
        # Create nodes with and without frontmatter
        node_with_fm = create_mock_node("proj_a", "Content with metadata")
        node_without_fm = create_mock_node(
            "proj_b", "Content without metadata", include_frontmatter=False
        )

        mock_search_results = MagicMock()
        mock_search_results.nodes = [node_with_fm, node_without_fm]
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="content",
                group_ids=["TEST-HOST__global"],
            )

        # Both nodes should be returned (backward compat)
        assert len(result["nodes"]) == 2


# =============================================================================
# TEST CLASS: Mock Graphiti Usage (AC-9.5)
# =============================================================================


class TestMockGraphitiUsage:
    """Tests verify mock Graphiti instance is used (no real Neo4j required)."""

    @pytest.mark.asyncio
    async def test_graphiti_search_is_mocked(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """AC-9.5 (P1): Tests use mock Graphiti instance - verify _search is called."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            await search_memory_nodes(
                query="test query",
                group_ids=["TEST-HOST__global"],
            )

        # Verify _search was called exactly once
        mock_graphiti_client._search.assert_called_once()

        # Verify query was passed correctly
        call_kwargs = mock_graphiti_client._search.call_args.kwargs
        assert call_kwargs["query"] == "test query"

    @pytest.mark.asyncio
    async def test_no_real_network_calls(
        self,
        mock_graphiti_client,
        mock_unified_config,
    ):
        """Verify no real network calls are made - search returns mock data."""
        # Create minimal mock result
        mock_search_results = MagicMock()
        mock_search_results.nodes = []
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="nonexistent",
                group_ids=["TEST-HOST__global"],
            )

        # Should get empty result (from mock), not network error
        assert "nodes" in result or "message" in result

    @pytest.mark.asyncio
    async def test_mock_allows_custom_responses(
        self,
        mock_graphiti_client,
        mock_unified_config,
    ):
        """Mock allows testing various response scenarios."""
        # Test with custom response structure
        custom_node = create_mock_node("custom_ns", "Custom test content")
        mock_search_results = MagicMock()
        mock_search_results.nodes = [custom_node]
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="custom",
                group_ids=["TEST-HOST__global"],
            )

        assert len(result["nodes"]) == 1
        assert "custom_ns" in result["nodes"][0].get("summary", "")


# =============================================================================
# TEST CLASS: Namespace Extraction from Results
# =============================================================================


class TestNamespaceExtractionFromResults:
    """Tests for extract_namespace_from_content working on search results."""

    def test_extract_from_valid_frontmatter(self):
        """Extract namespace from valid YAML frontmatter."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        node = create_mock_node("extracted_ns", "Content here")
        ns = extract_namespace_from_content(node.summary)
        assert ns == "extracted_ns"

    def test_extract_returns_none_for_no_frontmatter(self):
        """Return None when no frontmatter present."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        node = create_mock_node("ns", "content", include_frontmatter=False)
        ns = extract_namespace_from_content(node.summary)
        assert ns is None

    def test_extract_from_attributes_fallback(self):
        """Verify attributes contain project_namespace as fallback."""
        node = create_mock_node("attr_ns", "Content")
        assert node.attributes.get("project_namespace") == "attr_ns"


# =============================================================================
# TEST CLASS: Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_search_results(
        self,
        mock_graphiti_client,
        mock_unified_config,
    ):
        """Handle empty search results gracefully."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = []
        mock_graphiti_client._search.return_value = mock_search_results

        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="nonexistent",
                group_ids=["TEST-HOST__global"],
            )

        # Should return empty nodes list or message
        assert "message" in result or (
            "nodes" in result and len(result["nodes"]) == 0
        )

    @pytest.mark.asyncio
    async def test_filtering_excludes_all_results(
        self,
        mock_graphiti_client,
        sample_episodes_multi_namespace,
        mock_unified_config,
    ):
        """When filtering excludes all results, empty response returned."""
        mock_search_results = MagicMock()
        mock_search_results.nodes = sample_episodes_multi_namespace
        mock_graphiti_client._search.return_value = mock_search_results

        # Filter to namespace that doesn't exist in results
        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="auth",
                group_ids=["TEST-HOST__global"],
                project_namespaces=["nonexistent_namespace"],
            )

        # Should return empty or message about no results
        assert "message" in result or (
            "nodes" in result and len(result["nodes"]) == 0
        )

    @pytest.mark.asyncio
    async def test_mixed_results_with_and_without_namespace(
        self,
        mock_graphiti_client,
        mock_unified_config,
    ):
        """Handle mixed results: some with namespace, some without."""
        # Create mixed nodes
        node_with_ns = create_mock_node("proj_a", "With namespace")
        node_without_ns = create_mock_node("legacy", "No namespace", include_frontmatter=False)
        # Remove attributes for the legacy node too
        node_without_ns.attributes = {}

        mock_search_results = MagicMock()
        mock_search_results.nodes = [node_with_ns, node_without_ns]
        mock_graphiti_client._search.return_value = mock_search_results

        # Filter to proj_a
        mock_unified_config.session_tracking.cross_project_search = True
        mock_unified_config.session_tracking.trusted_namespaces = None

        with patch(
            "mcp_server.graphiti_mcp_server.graphiti_client", mock_graphiti_client
        ), patch("mcp_server.graphiti_mcp_server.unified_config", mock_unified_config):
            from mcp_server.graphiti_mcp_server import search_memory_nodes

            result = await search_memory_nodes(
                query="namespace",
                group_ids=["TEST-HOST__global"],
                project_namespaces=["proj_a"],
            )

        # Both should be returned: one matches, one has no namespace (backward compat)
        assert len(result["nodes"]) == 2
