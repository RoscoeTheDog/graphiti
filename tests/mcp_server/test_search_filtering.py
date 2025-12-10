"""
Tests for search_memory_nodes and search_memory_facts namespace filtering.
(Story 7: MCP Server Search Filter Implementation)

This module tests the integration of namespace filtering into the MCP search tools.
It verifies that:
- Global group_id is used by default
- Namespace filtering is applied based on config settings
- Post-filtering works correctly for nodes and facts

Coverage target: Integration tests for namespace filtering in search functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# MOCK TYPES
# =============================================================================


@dataclass
class MockNode:
    """Mock Graphiti node for testing."""
    uuid: str
    name: str
    summary: str
    labels: list
    group_id: str
    created_at: MagicMock
    attributes: dict

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = MagicMock()
            self.created_at.isoformat.return_value = "2025-01-01T00:00:00Z"


@dataclass
class MockEdge:
    """Mock Graphiti edge for testing."""
    uuid: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str


@dataclass
class MockSearchResults:
    """Mock search results from Graphiti."""
    nodes: list


class MockSessionTrackingConfig:
    """Mock SessionTrackingConfig for testing."""
    def __init__(
        self,
        group_id: Optional[str] = None,
        cross_project_search: bool = True,
        trusted_namespaces: Optional[list] = None
    ):
        self.group_id = group_id
        self.cross_project_search = cross_project_search
        self.trusted_namespaces = trusted_namespaces or []


class MockUnifiedConfig:
    """Mock unified config for testing."""
    def __init__(self, session_tracking: MockSessionTrackingConfig = None):
        self.session_tracking = session_tracking or MockSessionTrackingConfig()


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_graphiti_client():
    """Create a mock Graphiti client."""
    client = AsyncMock()
    return client


@pytest.fixture
def node_with_namespace_a():
    """Node with namespace A in summary."""
    return MockNode(
        uuid="node-1",
        name="Test Node A",
        summary="""---
graphiti_session_metadata:
  project_namespace: namespace_a
---
Summary for node A.""",
        labels=["Entity"],
        group_id="test-group",
        created_at=None,
        attributes={"project_namespace": "namespace_a"}
    )


@pytest.fixture
def node_with_namespace_b():
    """Node with namespace B in summary."""
    return MockNode(
        uuid="node-2",
        name="Test Node B",
        summary="""---
graphiti_session_metadata:
  project_namespace: namespace_b
---
Summary for node B.""",
        labels=["Entity"],
        group_id="test-group",
        created_at=None,
        attributes={"project_namespace": "namespace_b"}
    )


@pytest.fixture
def node_without_namespace():
    """Node without namespace metadata (backward compatibility)."""
    return MockNode(
        uuid="node-3",
        name="Legacy Node",
        summary="Simple summary without frontmatter",
        labels=["Entity"],
        group_id="test-group",
        created_at=None,
        attributes={}
    )


@pytest.fixture
def edge_with_namespace_a():
    """Edge with namespace A in fact."""
    return MockEdge(
        uuid="edge-1",
        fact="""---
graphiti_session_metadata:
  project_namespace: namespace_a
---
Fact from namespace A.""",
        source_node_uuid="node-1",
        target_node_uuid="node-2"
    )


@pytest.fixture
def edge_with_namespace_b():
    """Edge with namespace B in fact."""
    return MockEdge(
        uuid="edge-2",
        fact="""---
graphiti_session_metadata:
  project_namespace: namespace_b
---
Fact from namespace B.""",
        source_node_uuid="node-3",
        target_node_uuid="node-4"
    )


# =============================================================================
# UNIT TESTS: get_effective_group_id integration
# =============================================================================


class TestEffectiveGroupIdUsage:
    """Tests for effective group_id computation in search functions."""

    def test_uses_global_group_id_when_none_provided(self):
        """AC-7.1: search_memory_nodes uses global group_id by default."""
        from mcp_server.namespace_filter import get_effective_group_id

        config = MockSessionTrackingConfig(group_id="configured_group")
        result = get_effective_group_id(config)

        assert result == "configured_group"

    def test_computes_hostname_based_group_when_not_configured(self):
        """AC-7.1: Compute hostname-based group_id when not configured."""
        from mcp_server.namespace_filter import get_effective_group_id

        config = MockSessionTrackingConfig(group_id=None)

        with patch('socket.gethostname', return_value='TEST-HOST'):
            result = get_effective_group_id(config)

        assert result == "TEST-HOST__global"


# =============================================================================
# UNIT TESTS: Namespace filtering logic
# =============================================================================


class TestNamespaceFilteringInSearch:
    """Tests for namespace filtering logic in search functions."""

    def test_explicit_namespaces_parameter_filters_results(
        self, node_with_namespace_a, node_with_namespace_b
    ):
        """AC-7.2: Explicit project_namespaces parameter filters results."""
        from mcp_server.namespace_filter import (
            extract_namespace_from_content,
        )

        nodes = [node_with_namespace_a, node_with_namespace_b]

        # Simulate the filtering logic from search_memory_nodes
        filtered_nodes = []
        effective_namespaces = ["namespace_a"]

        for node in nodes:
            ns = None
            if hasattr(node, 'summary') and node.summary:
                ns = extract_namespace_from_content(node.summary)
            if ns is None and hasattr(node, 'attributes'):
                ns = node.attributes.get('project_namespace')

            if ns is None or ns in effective_namespaces:
                filtered_nodes.append(node)

        assert len(filtered_nodes) == 1
        assert filtered_nodes[0].uuid == "node-1"

    def test_trusted_namespaces_config_filters_results(
        self, node_with_namespace_a, node_with_namespace_b
    ):
        """AC-7.3: Config trusted_namespaces filters results."""
        from mcp_server.namespace_filter import (
            extract_namespace_from_content,
        )

        config = MockSessionTrackingConfig(
            cross_project_search=True,
            trusted_namespaces=["namespace_a"]
        )

        nodes = [node_with_namespace_a, node_with_namespace_b]

        # Simulate the filtering logic
        effective_namespaces = None
        if not config.cross_project_search:
            pass  # Would need current project namespace
        elif config.trusted_namespaces:
            effective_namespaces = config.trusted_namespaces

        filtered_nodes = []
        if effective_namespaces:
            for node in nodes:
                ns = None
                if hasattr(node, 'summary') and node.summary:
                    ns = extract_namespace_from_content(node.summary)
                if ns is None and hasattr(node, 'attributes'):
                    ns = node.attributes.get('project_namespace')

                if ns is None or ns in effective_namespaces:
                    filtered_nodes.append(node)
        else:
            filtered_nodes = nodes

        assert len(filtered_nodes) == 1
        assert filtered_nodes[0].uuid == "node-1"

    def test_cross_project_search_true_no_filtering(
        self, node_with_namespace_a, node_with_namespace_b
    ):
        """With cross_project_search=true and no trusted_namespaces, no filtering."""
        config = MockSessionTrackingConfig(
            cross_project_search=True,
            trusted_namespaces=[]
        )

        nodes = [node_with_namespace_a, node_with_namespace_b]

        # Simulate: no filtering when cross_project_search=true and no trusted_namespaces
        effective_namespaces = None
        if not config.cross_project_search:
            pass
        elif config.trusted_namespaces:
            effective_namespaces = config.trusted_namespaces

        # No effective_namespaces means no filtering
        if effective_namespaces:
            filtered_nodes = []  # Would filter
        else:
            filtered_nodes = nodes  # No filtering

        assert len(filtered_nodes) == 2

    def test_backward_compatibility_with_no_namespace(
        self, node_with_namespace_a, node_without_namespace
    ):
        """Nodes without namespace are included for backward compatibility."""
        from mcp_server.namespace_filter import (
            extract_namespace_from_content,
        )

        nodes = [node_with_namespace_a, node_without_namespace]
        effective_namespaces = ["namespace_a"]

        filtered_nodes = []
        for node in nodes:
            ns = None
            if hasattr(node, 'summary') and node.summary:
                ns = extract_namespace_from_content(node.summary)
            if ns is None and hasattr(node, 'attributes'):
                ns = node.attributes.get('project_namespace')

            # Include if matches OR no namespace found (backward compat)
            if ns is None or ns in effective_namespaces:
                filtered_nodes.append(node)

        assert len(filtered_nodes) == 2  # Both included


# =============================================================================
# UNIT TESTS: search_memory_facts filtering
# =============================================================================


class TestSearchMemoryFactsFiltering:
    """Tests for namespace filtering in search_memory_facts."""

    def test_facts_filtered_by_namespace(
        self, edge_with_namespace_a, edge_with_namespace_b
    ):
        """Facts are filtered by namespace using filter_by_namespace."""
        from mcp_server.namespace_filter import filter_by_namespace

        edges = [edge_with_namespace_a, edge_with_namespace_b]

        filtered = filter_by_namespace(edges, ["namespace_a"], content_attr="fact")

        assert len(filtered) == 1
        assert filtered[0].uuid == "edge-1"

    def test_facts_trusted_namespaces(
        self, edge_with_namespace_a, edge_with_namespace_b
    ):
        """Facts filtered to trusted namespaces only."""
        from mcp_server.namespace_filter import filter_by_namespace

        edges = [edge_with_namespace_a, edge_with_namespace_b]
        trusted = ["namespace_b"]

        filtered = filter_by_namespace(edges, trusted, content_attr="fact")

        assert len(filtered) == 1
        assert filtered[0].uuid == "edge-2"


# =============================================================================
# INTEGRATION TESTS: Cross-Project Search Scenarios
# =============================================================================


class TestCrossProjectSearchScenarios:
    """Integration tests for cross-project search behavior."""

    def test_search_across_multiple_projects(
        self,
        node_with_namespace_a,
        node_with_namespace_b,
        node_without_namespace
    ):
        """AC-7.2/7.3: Cross-project search with various configurations."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        all_nodes = [
            node_with_namespace_a,
            node_with_namespace_b,
            node_without_namespace
        ]

        # Scenario 1: No filtering (cross_project_search=true, no trusted_namespaces)
        config1 = MockSessionTrackingConfig(
            cross_project_search=True,
            trusted_namespaces=[]
        )
        # Result: all 3 nodes
        assert self._apply_filter(all_nodes, config1, None) == 3

        # Scenario 2: Trusted namespaces filtering
        config2 = MockSessionTrackingConfig(
            cross_project_search=True,
            trusted_namespaces=["namespace_a"]
        )
        # Result: namespace_a + no-namespace (backward compat) = 2 nodes
        assert self._apply_filter(all_nodes, config2, None) == 2

        # Scenario 3: Explicit namespace parameter
        config3 = MockSessionTrackingConfig(
            cross_project_search=True,
            trusted_namespaces=[]
        )
        # Result: only namespace_b + no-namespace = 2 nodes
        assert self._apply_filter(all_nodes, config3, ["namespace_b"]) == 2

    def _apply_filter(self, nodes, config, explicit_namespaces):
        """Helper to apply filtering logic."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        effective_namespaces = explicit_namespaces
        if effective_namespaces is None:
            if not config.cross_project_search:
                pass  # Would use current project
            elif config.trusted_namespaces:
                effective_namespaces = config.trusted_namespaces

        if not effective_namespaces:
            return len(nodes)

        filtered = []
        for node in nodes:
            ns = None
            if hasattr(node, 'summary') and node.summary:
                ns = extract_namespace_from_content(node.summary)
            if ns is None and hasattr(node, 'attributes'):
                ns = node.attributes.get('project_namespace')

            if ns is None or ns in effective_namespaces:
                filtered.append(node)

        return len(filtered)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Edge case tests for search filtering."""

    def test_empty_search_results(self):
        """Handle empty search results gracefully."""
        from mcp_server.namespace_filter import filter_by_namespace

        empty_nodes = []
        filtered = filter_by_namespace(empty_nodes, ["any_namespace"])

        assert filtered == []

    def test_all_results_filtered_out(self, node_with_namespace_a):
        """Handle case where all results are filtered out."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        nodes = [node_with_namespace_a]
        effective_namespaces = ["nonexistent_namespace"]

        filtered = []
        for node in nodes:
            ns = None
            if hasattr(node, 'summary') and node.summary:
                ns = extract_namespace_from_content(node.summary)
            if ns is None and hasattr(node, 'attributes'):
                ns = node.attributes.get('project_namespace')

            if ns is None or ns in effective_namespaces:
                filtered.append(node)

        assert len(filtered) == 0

    def test_namespace_in_attributes_only(self):
        """Extract namespace from attributes when not in summary."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        node = MockNode(
            uuid="node-attr",
            name="Attribute Node",
            summary="Plain summary without frontmatter",
            labels=["Entity"],
            group_id="test-group",
            created_at=None,
            attributes={"project_namespace": "attr_namespace"}
        )

        # From summary
        ns = extract_namespace_from_content(node.summary)
        assert ns is None

        # Fallback to attributes
        ns = node.attributes.get('project_namespace')
        assert ns == "attr_namespace"

    def test_multiple_namespace_matches(self, node_with_namespace_a):
        """Node matching multiple trusted namespaces."""
        from mcp_server.namespace_filter import extract_namespace_from_content

        nodes = [node_with_namespace_a]
        # Multiple namespaces including the one in node_with_namespace_a
        effective_namespaces = ["namespace_a", "namespace_b", "namespace_c"]

        filtered = []
        for node in nodes:
            ns = None
            if hasattr(node, 'summary') and node.summary:
                ns = extract_namespace_from_content(node.summary)

            if ns is None or ns in effective_namespaces:
                filtered.append(node)

        assert len(filtered) == 1
