"""
Tests for namespace filtering utilities (Story 7: MCP Server Search Filter Implementation).

This module tests the namespace extraction and filtering functionality used by
search_memory_nodes and search_memory_facts to implement namespace-scoped
knowledge retrieval.

Coverage target: >90% of mcp_server/namespace_filter.py
"""

import pytest
from unittest.mock import MagicMock, patch
import socket

from mcp_server.namespace_filter import (
    extract_namespace_from_content,
    filter_by_namespace,
    get_effective_group_id,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def valid_frontmatter_content():
    """Content with valid YAML frontmatter containing namespace."""
    return """---
graphiti_session_metadata:
  version: '2.0'
  project_namespace: a1b2c3d4e5f6g7h8
  hostname: DESKTOP-TEST
  session_id: test-session-123
---

This is the actual episode content.
It can span multiple lines and contain various information.
"""


@pytest.fixture
def frontmatter_without_namespace():
    """Content with frontmatter but no namespace field."""
    return """---
graphiti_session_metadata:
  version: '2.0'
  hostname: DESKTOP-TEST
---

Content without namespace in metadata.
"""


@pytest.fixture
def frontmatter_with_different_structure():
    """Content with frontmatter but different structure."""
    return """---
title: My Document
author: Test User
---

Content with non-standard frontmatter.
"""


@pytest.fixture
def mock_session_tracking_config():
    """Create a mock SessionTrackingConfig."""
    config = MagicMock()
    config.group_id = None
    config.cross_project_search = True
    config.trusted_namespaces = []
    return config


class MockSearchResult:
    """Mock search result object for testing filter_by_namespace."""

    def __init__(self, content: str, fact: str = None):
        self.content = content
        self.fact = fact if fact is not None else content


# =============================================================================
# UNIT TESTS: extract_namespace_from_content
# =============================================================================


class TestExtractNamespaceFromContent:
    """Tests for extract_namespace_from_content function."""

    def test_extract_namespace_valid_frontmatter(self, valid_frontmatter_content):
        """AC-7.4: Extract namespace from valid YAML frontmatter."""
        result = extract_namespace_from_content(valid_frontmatter_content)
        assert result == "a1b2c3d4e5f6g7h8"

    def test_extract_namespace_no_frontmatter(self):
        """Handle content without YAML frontmatter."""
        content = "This is plain text content without any frontmatter."
        result = extract_namespace_from_content(content)
        assert result is None

    def test_extract_namespace_empty_content(self):
        """Handle empty content string."""
        result = extract_namespace_from_content("")
        assert result is None

    def test_extract_namespace_none_content(self):
        """Handle None content."""
        result = extract_namespace_from_content(None)
        assert result is None

    def test_extract_namespace_partial_frontmatter(self):
        """Handle content that starts with --- but doesn't close."""
        content = "---\nincomplete frontmatter without closing"
        result = extract_namespace_from_content(content)
        assert result is None

    def test_extract_namespace_missing_namespace_field(self, frontmatter_without_namespace):
        """Handle frontmatter without project_namespace field."""
        result = extract_namespace_from_content(frontmatter_without_namespace)
        assert result is None

    def test_extract_namespace_different_structure(self, frontmatter_with_different_structure):
        """Handle frontmatter with different metadata structure."""
        result = extract_namespace_from_content(frontmatter_with_different_structure)
        assert result is None

    def test_extract_namespace_invalid_yaml(self):
        """Handle malformed YAML gracefully."""
        content = """---
invalid: yaml: content: : : :
  - broken
    indentation
---
Content after invalid YAML.
"""
        result = extract_namespace_from_content(content)
        assert result is None

    def test_extract_namespace_special_characters(self):
        """Handle namespace with special characters."""
        content = """---
graphiti_session_metadata:
  project_namespace: abc_123-456.test
---
Content here.
"""
        result = extract_namespace_from_content(content)
        assert result == "abc_123-456.test"

    def test_extract_namespace_hexadecimal_hash(self):
        """Handle typical hexadecimal namespace hash format."""
        content = """---
graphiti_session_metadata:
  version: '2.0'
  project_namespace: 6f61768c
---
Content.
"""
        result = extract_namespace_from_content(content)
        assert result == "6f61768c"

    def test_extract_namespace_with_extra_fields(self):
        """Extract namespace when additional fields present."""
        content = """---
graphiti_session_metadata:
  version: '2.0'
  project_namespace: test_ns_001
  hostname: TEST-HOST
  session_id: sess-123
  extra_field: extra_value
---
Content.
"""
        result = extract_namespace_from_content(content)
        assert result == "test_ns_001"

    def test_extract_namespace_whitespace_handling(self):
        """Handle whitespace in and around frontmatter."""
        content = """---
graphiti_session_metadata:
  project_namespace:   spaced_namespace
---

Content after whitespace.
"""
        result = extract_namespace_from_content(content)
        # yaml.safe_load should strip trailing whitespace but not leading
        # The behavior depends on YAML parsing - check actual result
        assert result is not None
        assert "spaced_namespace" in result


# =============================================================================
# UNIT TESTS: filter_by_namespace
# =============================================================================


class TestFilterByNamespace:
    """Tests for filter_by_namespace function."""

    def test_filter_single_namespace(self):
        """AC-7.4: Filter to single namespace."""
        content_a = """---
graphiti_session_metadata:
  project_namespace: namespace_a
---
Content A.
"""
        content_b = """---
graphiti_session_metadata:
  project_namespace: namespace_b
---
Content B.
"""
        results = [MockSearchResult(content_a), MockSearchResult(content_b)]
        filtered = filter_by_namespace(results, ["namespace_a"])

        assert len(filtered) == 1
        assert "namespace_a" in filtered[0].content

    def test_filter_multiple_namespaces(self):
        """AC-7.4: Filter to multiple namespaces."""
        content_a = """---
graphiti_session_metadata:
  project_namespace: namespace_a
---"""
        content_b = """---
graphiti_session_metadata:
  project_namespace: namespace_b
---"""
        content_c = """---
graphiti_session_metadata:
  project_namespace: namespace_c
---"""
        results = [
            MockSearchResult(content_a),
            MockSearchResult(content_b),
            MockSearchResult(content_c),
        ]

        filtered = filter_by_namespace(results, ["namespace_a", "namespace_c"])

        assert len(filtered) == 2
        namespaces_in_results = [
            extract_namespace_from_content(r.content) for r in filtered
        ]
        assert "namespace_a" in namespaces_in_results
        assert "namespace_c" in namespaces_in_results
        assert "namespace_b" not in namespaces_in_results

    def test_filter_empty_namespace_list(self):
        """AC-7.4: Empty namespace list returns all results."""
        content = """---
graphiti_session_metadata:
  project_namespace: any_ns
---"""
        results = [MockSearchResult(content), MockSearchResult(content)]

        filtered = filter_by_namespace(results, [])

        assert len(filtered) == 2  # All results returned

    def test_filter_includes_results_without_namespace(self):
        """Backward compatibility: results without namespace are included."""
        content_with_ns = """---
graphiti_session_metadata:
  project_namespace: has_namespace
---"""
        content_without_ns = "Plain text without frontmatter"

        results = [
            MockSearchResult(content_with_ns),
            MockSearchResult(content_without_ns),
        ]

        # Filter to a specific namespace
        filtered = filter_by_namespace(results, ["has_namespace"])

        # Both should be included - one matches, one has no namespace (backward compat)
        assert len(filtered) == 2

    def test_filter_excludes_non_matching_namespace(self):
        """Results with non-matching namespace are excluded."""
        content_ns_a = """---
graphiti_session_metadata:
  project_namespace: namespace_a
---"""
        content_ns_b = """---
graphiti_session_metadata:
  project_namespace: namespace_b
---"""

        results = [MockSearchResult(content_ns_a), MockSearchResult(content_ns_b)]

        filtered = filter_by_namespace(results, ["namespace_a"])

        assert len(filtered) == 1
        assert extract_namespace_from_content(filtered[0].content) == "namespace_a"

    def test_filter_custom_content_attr(self):
        """Filter using custom content attribute name."""
        fact_content = """---
graphiti_session_metadata:
  project_namespace: fact_namespace
---
Fact content here.
"""
        results = [MockSearchResult(content="", fact=fact_content)]

        filtered = filter_by_namespace(results, ["fact_namespace"], content_attr="fact")

        assert len(filtered) == 1

    def test_filter_missing_content_attr(self):
        """Handle results missing the content attribute."""
        class NoContentResult:
            pass

        results = [NoContentResult()]
        filtered = filter_by_namespace(results, ["any_namespace"])

        assert len(filtered) == 0  # Skipped due to missing content

    def test_filter_empty_results_list(self):
        """Handle empty results list."""
        filtered = filter_by_namespace([], ["namespace"])
        assert filtered == []

    def test_filter_none_content_value(self):
        """Handle result with None content value."""
        class NoneContentResult:
            content = None

        results = [NoneContentResult()]
        filtered = filter_by_namespace(results, ["namespace"])

        assert len(filtered) == 0


# =============================================================================
# UNIT TESTS: get_effective_group_id
# =============================================================================


class TestGetEffectiveGroupId:
    """Tests for get_effective_group_id function."""

    def test_uses_configured_group_id(self, mock_session_tracking_config):
        """AC-7.1: Use configured group_id when set."""
        mock_session_tracking_config.group_id = "custom_group_id"

        result = get_effective_group_id(mock_session_tracking_config)

        assert result == "custom_group_id"

    def test_computes_default_from_hostname(self, mock_session_tracking_config):
        """AC-7.1: Compute default group_id from hostname when not configured."""
        mock_session_tracking_config.group_id = None

        with patch('socket.gethostname', return_value='TEST-HOSTNAME'):
            result = get_effective_group_id(mock_session_tracking_config)

        assert result == "TEST-HOSTNAME__global"

    def test_hostname_format_matches_pattern(self, mock_session_tracking_config):
        """Verify the {hostname}__global format."""
        mock_session_tracking_config.group_id = None

        with patch('socket.gethostname', return_value='DESKTOP-ABC123'):
            result = get_effective_group_id(mock_session_tracking_config)

        assert result.endswith("__global")
        assert "DESKTOP-ABC123" in result

    def test_empty_string_group_id_uses_default(self, mock_session_tracking_config):
        """Empty string group_id should use hostname-based default."""
        mock_session_tracking_config.group_id = ""

        with patch('socket.gethostname', return_value='MYHOST'):
            result = get_effective_group_id(mock_session_tracking_config)

        # Empty string is falsy, so should compute default
        assert result == "MYHOST__global"


# =============================================================================
# INTEGRATION TESTS: Namespace Filtering Workflow
# =============================================================================


class TestNamespaceFilteringWorkflow:
    """Integration tests for the namespace filtering workflow."""

    def test_cross_project_search_returns_all(self):
        """AC-7.5: With cross_project_search=true, all namespaces returned."""
        # Simulate results from multiple projects
        project_a = """---
graphiti_session_metadata:
  project_namespace: project_a_hash
---
Session from Project A.
"""
        project_b = """---
graphiti_session_metadata:
  project_namespace: project_b_hash
---
Session from Project B.
"""
        results = [MockSearchResult(project_a), MockSearchResult(project_b)]

        # No namespace filter = all results
        filtered = filter_by_namespace(results, [])

        assert len(filtered) == 2

    def test_trusted_namespaces_excludes_untrusted(self):
        """AC-7.3: Only trusted namespaces appear in results."""
        trusted = """---
graphiti_session_metadata:
  project_namespace: trusted_ns
---
Trusted content.
"""
        untrusted = """---
graphiti_session_metadata:
  project_namespace: untrusted_ns
---
Untrusted content.
"""
        results = [MockSearchResult(trusted), MockSearchResult(untrusted)]

        # Filter to only trusted namespace
        filtered = filter_by_namespace(results, ["trusted_ns"])

        assert len(filtered) == 1
        assert "trusted_ns" in filtered[0].content

    def test_namespace_visible_in_results(self, valid_frontmatter_content):
        """AC-7.5: Namespace metadata visible in search results."""
        result = MockSearchResult(valid_frontmatter_content)

        # Verify namespace can be extracted from result content
        namespace = extract_namespace_from_content(result.content)

        assert namespace is not None
        assert namespace == "a1b2c3d4e5f6g7h8"


# =============================================================================
# SECURITY TESTS
# =============================================================================


class TestNamespaceFilteringSecurity:
    """Security tests for namespace filtering."""

    def test_yaml_safe_load_prevents_code_execution(self):
        """Verify yaml.safe_load is used to prevent arbitrary code execution."""
        # This payload would execute code with unsafe yaml.load()
        malicious_content = """---
graphiti_session_metadata: !!python/object/apply:os.system ['echo pwned']
---
Malicious content.
"""
        # Should return None, not execute code
        result = extract_namespace_from_content(malicious_content)
        assert result is None

    def test_yaml_tag_injection_prevented(self):
        """Prevent YAML tag-based injection attacks."""
        injection_content = """---
graphiti_session_metadata:
  project_namespace: !!python/object:__main__.MaliciousClass {}
---
"""
        result = extract_namespace_from_content(injection_content)
        # Should return None for suspicious YAML
        assert result is None

    def test_deeply_nested_yaml_handled(self):
        """Handle deeply nested YAML without stack overflow."""
        # Create deeply nested structure
        nested = "graphiti_session_metadata:\n" + "  nested:\n" * 100 + "    project_namespace: deep\n"
        content = f"---\n{nested}---\nContent."

        # Should not crash, may return None due to structure
        result = extract_namespace_from_content(content)
        # Just verify it doesn't crash - result depends on structure
        assert True  # Reached here without exception

    def test_large_frontmatter_handled(self):
        """Handle large frontmatter without memory issues."""
        large_value = "x" * 100000  # 100KB string
        content = f"""---
graphiti_session_metadata:
  project_namespace: test_ns
  large_field: {large_value}
---
Content.
"""
        result = extract_namespace_from_content(content)
        assert result == "test_ns"

    def test_unicode_in_namespace(self):
        """Handle unicode characters in namespace safely."""
        unicode_content = """---
graphiti_session_metadata:
  project_namespace: test_🚀_namespace
---
Unicode content.
"""
        result = extract_namespace_from_content(unicode_content)
        assert result == "test_🚀_namespace"

    def test_control_characters_handled(self):
        """Handle control characters in content."""
        control_content = "---\ngraphiti_session_metadata:\n  project_namespace: test\x00ns\n---\nContent."

        # Should handle gracefully (may return None or the namespace)
        result = extract_namespace_from_content(control_content)
        # Just verify no crash
        assert True
