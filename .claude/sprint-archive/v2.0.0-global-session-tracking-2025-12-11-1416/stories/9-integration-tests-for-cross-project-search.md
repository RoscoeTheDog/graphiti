# Story 9: Integration Tests for Cross-Project Search

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Write integration tests verifying cross-project search behavior and namespace filtering.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Section 9.2

## Acceptance Criteria

- [ ] (P0) Test: cross_project_search=true returns results from multiple projects
- [ ] (P0) Test: cross_project_search=false returns only current project
- [ ] (P1) Test: trusted_namespaces filters to specified projects
- [ ] (P1) Test: metadata header present and parseable in indexed episodes
- [ ] (P1) Tests use mock Graphiti instance (no real Neo4j required)

## Dependencies

- Story 8: Unit Tests for New Components

## Implementation Notes

Test file: `tests/session_tracking/test_cross_project_search.py`

Example tests from spec:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_graphiti():
    """Create a mock Graphiti instance."""
    mock = AsyncMock()
    mock.search = AsyncMock()
    return mock

@pytest.fixture
def sample_episodes():
    """Create sample episodes with different namespaces."""
    return [
        create_episode(namespace="proj_a", content="Auth with JWT"),
        create_episode(namespace="proj_b", content="Auth with OAuth"),
        create_episode(namespace="proj_c", content="Auth with SAML"),
    ]

async def test_cross_project_search_enabled(mock_graphiti, sample_episodes):
    """Sessions from multiple projects should be returned when enabled."""
    mock_graphiti.search.return_value = sample_episodes

    config = SessionTrackingConfig(cross_project_search=True)
    results = await search_memory_nodes(
        query="authentication",
        graphiti=mock_graphiti,
        config=config
    )

    namespaces = {extract_namespace(r) for r in results}
    assert namespaces == {"proj_a", "proj_b", "proj_c"}

async def test_cross_project_search_disabled(mock_graphiti, sample_episodes):
    """Only current project sessions should be returned when disabled."""
    mock_graphiti.search.return_value = sample_episodes

    config = SessionTrackingConfig(cross_project_search=False)
    current_namespace = "proj_a"

    results = await search_memory_nodes(
        query="authentication",
        graphiti=mock_graphiti,
        config=config,
        current_namespace=current_namespace
    )

    assert all(extract_namespace(r) == "proj_a" for r in results)

async def test_trusted_namespaces_filter(mock_graphiti, sample_episodes):
    """Only trusted namespace sessions should be returned."""
    mock_graphiti.search.return_value = sample_episodes

    config = SessionTrackingConfig(trusted_namespaces=["proj_a", "proj_b"])

    results = await search_memory_nodes(
        query="authentication",
        graphiti=mock_graphiti,
        config=config
    )

    namespaces = {extract_namespace(r) for r in results}
    assert namespaces == {"proj_a", "proj_b"}
    assert "proj_c" not in namespaces

async def test_metadata_header_parseable(mock_graphiti):
    """Episode metadata header should be parseable YAML."""
    import yaml

    # Create episode with metadata
    episode = await store_session_with_metadata(
        project_namespace="test123",
        project_path="/test/path",
        content="Test session content"
    )

    # Verify YAML is parseable
    content = episode.content
    assert content.startswith("---")
    frontmatter_end = content.index("---", 3)
    frontmatter = yaml.safe_load(content[3:frontmatter_end])

    assert "graphiti_session_metadata" in frontmatter
    assert frontmatter["graphiti_session_metadata"]["project_namespace"] == "test123"
```

## Related Stories

- Story 8: Unit Tests for New Components (dependency)
- Story 7: MCP Server Search Filter Implementation (tests this functionality)
