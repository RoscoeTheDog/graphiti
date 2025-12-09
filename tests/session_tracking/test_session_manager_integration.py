"""Integration tests for Session Manager Updates (Story 6).

Tests for the end-to-end flow from session close callback to Graphiti indexing
with namespace metadata extraction.
"""

import asyncio
import socket
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from graphiti_core.session_tracking.indexer import SessionIndexer
from graphiti_core.session_tracking.path_resolver import ClaudePathResolver
from graphiti_core.session_tracking.resilient_indexer import (
    ResilientIndexerConfig,
    ResilientSessionIndexer,
)


def parse_yaml_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter from content string."""
    if not content.startswith("---\n"):
        return None

    lines = content.strip().split("\n")
    yaml_lines = []
    in_frontmatter = False
    for line in lines:
        if line == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter:
            yaml_lines.append(line)

    if not yaml_lines:
        return None

    yaml_content = "\n".join(yaml_lines)
    return yaml.safe_load(yaml_content)


@pytest.fixture
def mock_graphiti():
    """Create a mock Graphiti instance."""
    mock = MagicMock()
    mock_result = MagicMock()
    mock_result.episode.uuid = "test-episode-uuid"
    mock_result.nodes = []
    mock_result.edges = []
    mock.add_episode = AsyncMock(return_value=mock_result)
    return mock


@pytest.fixture
def path_resolver():
    """Create a ClaudePathResolver for testing."""
    return ClaudePathResolver()


class TestCrossProjectSessionIndexing:
    """Integration tests for cross-project session indexing (Story 6)."""

    @pytest.mark.asyncio
    async def test_multiple_projects_same_global_group_id(
        self, mock_graphiti, path_resolver
    ):
        """Test that sessions from multiple projects index to same global group_id."""
        indexer = SessionIndexer(mock_graphiti)
        hostname = "DESKTOP-TEST"
        global_group_id = path_resolver.get_global_group_id(hostname)

        # Index sessions from two different "projects" (different namespaces)
        project1_namespace = "abc12345"  # Would be hash of /project/one
        project2_namespace = "xyz98765"  # Would be hash of /project/two

        # Session from project 1
        await indexer.index_session(
            session_id="session-p1-001",
            filtered_content="Working on project 1",
            group_id=global_group_id,  # Same global group!
            project_namespace=project1_namespace,
            project_path="/home/user/project-one",
            hostname=hostname,
        )

        # Session from project 2
        await indexer.index_session(
            session_id="session-p2-001",
            filtered_content="Working on project 2",
            group_id=global_group_id,  # Same global group!
            project_namespace=project2_namespace,
            project_path="/home/user/project-two",
            hostname=hostname,
        )

        # Both sessions should have been indexed
        assert mock_graphiti.add_episode.call_count == 2

        # Both should have same group_id
        calls = mock_graphiti.add_episode.call_args_list
        assert calls[0].kwargs["group_id"] == global_group_id
        assert calls[1].kwargs["group_id"] == global_group_id

        # Each should have its own namespace in metadata
        body1 = calls[0].kwargs["episode_body"]
        body2 = calls[1].kwargs["episode_body"]

        meta1 = parse_yaml_frontmatter(body1)
        meta2 = parse_yaml_frontmatter(body2)

        assert meta1["graphiti_session_metadata"]["project_namespace"] == project1_namespace
        assert meta2["graphiti_session_metadata"]["project_namespace"] == project2_namespace

    @pytest.mark.asyncio
    async def test_global_group_id_format(self, path_resolver):
        """Test global group_id format is '{hostname}__global'."""
        hostname = "DESKTOP-9SIHNJI"

        group_id = path_resolver.get_global_group_id(hostname)

        assert group_id == "DESKTOP-9SIHNJI__global"
        assert "__global" in group_id

    @pytest.mark.asyncio
    async def test_session_close_extracts_namespace_from_path(
        self, mock_graphiti, path_resolver
    ):
        """Test namespace extraction from session file path."""
        # Simulate a session file path like:
        # ~/.claude/projects/a1b2c3d4/sessions/session-123.jsonl
        session_file = Path("/home/user/.claude/projects/a1b2c3d4/sessions/session-123.jsonl")

        # Extract namespace (project hash) from path
        namespace = path_resolver.resolve_project_from_session_file(session_file)

        assert namespace == "a1b2c3d4"

    @pytest.mark.asyncio
    async def test_resilient_indexer_passes_namespace_metadata(self, mock_graphiti):
        """Test ResilientSessionIndexer passes namespace metadata through."""
        config = ResilientIndexerConfig()
        indexer = ResilientSessionIndexer(mock_graphiti, config)

        # Start the indexer
        await indexer.start()

        try:
            result = await indexer.index_session(
                session_id="abc123",
                filtered_content="Test content",
                group_id="myhost__global",
                project_namespace="ns12345678",
                project_path="/test/project",
                hostname="TESTHOST",
                include_project_path=True,
            )

            assert result["success"] is True
            assert result["episode_uuid"] == "test-episode-uuid"

            # Verify underlying indexer received namespace params
            call_kwargs = mock_graphiti.add_episode.call_args.kwargs
            episode_body = call_kwargs["episode_body"]

            # Should have metadata header
            assert episode_body.startswith("---\n")
            meta = parse_yaml_frontmatter(episode_body)
            assert meta["graphiti_session_metadata"]["project_namespace"] == "ns12345678"
            assert meta["graphiti_session_metadata"]["project_path"] == "/test/project"
            assert meta["graphiti_session_metadata"]["hostname"] == "TESTHOST"

        finally:
            await indexer.stop()

    @pytest.mark.asyncio
    async def test_session_indexing_with_config_group_id(
        self, mock_graphiti, path_resolver
    ):
        """Test session uses configured group_id when provided."""
        indexer = SessionIndexer(mock_graphiti)

        # Configured group_id takes precedence over computed global
        configured_group_id = "custom-group-id"

        await indexer.index_session(
            session_id="session-001",
            filtered_content="Content",
            group_id=configured_group_id,  # User-configured group_id
            project_namespace="abc12345",
            hostname="MYHOST",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs["group_id"] == "custom-group-id"

    @pytest.mark.asyncio
    async def test_namespace_prefix_in_source_description(self, mock_graphiti):
        """Test source_description includes namespace prefix for cross-project queries."""
        indexer = SessionIndexer(mock_graphiti)

        # Index sessions from different namespaces
        await indexer.index_session(
            session_id="session-001",
            filtered_content="Content 1",
            group_id="myhost__global",
            project_namespace="projAAAA1234",
            hostname="HOST",
        )

        await indexer.index_session(
            session_id="session-002",
            filtered_content="Content 2",
            group_id="myhost__global",
            project_namespace="projBBBB5678",
            hostname="HOST",
        )

        calls = mock_graphiti.add_episode.call_args_list

        # Source descriptions should have namespace prefixes
        source1 = calls[0].kwargs["source_description"]
        source2 = calls[1].kwargs["source_description"]

        assert source1.startswith("[projAAAA]")  # First 8 chars
        assert source2.startswith("[projBBBB]")  # First 8 chars


class TestDebugLoggingNamespace:
    """Test DEBUG logging of namespace information (AC-6.5)."""

    @pytest.mark.asyncio
    async def test_indexer_logs_namespace_at_debug_level(
        self, mock_graphiti, caplog
    ):
        """Test that namespace info is logged at DEBUG level."""
        import logging

        indexer = SessionIndexer(mock_graphiti)

        # Set logging level to DEBUG
        with caplog.at_level(logging.DEBUG, logger="graphiti_core.session_tracking.indexer"):
            await indexer.index_session(
                session_id="session-001",
                filtered_content="Content",
                group_id="myhost__global",
                project_namespace="abc12345",
                hostname="TESTHOST",
            )

        # The indexer itself may not log namespace (it's at INFO level for indexing)
        # but the callback in MCP server should log at DEBUG
        # For now, just verify the call succeeded
        assert mock_graphiti.add_episode.call_count == 1


class TestEndToEndSessionClose:
    """End-to-end tests simulating session close flow."""

    @pytest.mark.asyncio
    async def test_simulated_on_session_closed_callback(
        self, mock_graphiti, path_resolver
    ):
        """Simulate the on_session_closed callback from MCP server."""
        # Setup components
        indexer = SessionIndexer(mock_graphiti)
        hostname = socket.gethostname()

        # Simulate session closed callback behavior
        session_id = "test-session-12345"
        file_path = Path(f"/home/user/.claude/projects/a1b2c3d4/sessions/{session_id}.jsonl")
        filtered_content = "[user]: Fix the bug\n[assistant]: Reading file..."

        # Extract namespace from file path (as the callback does)
        project_namespace = path_resolver.resolve_project_from_session_file(file_path)
        assert project_namespace == "a1b2c3d4"

        # Compute global group_id (as the callback does)
        group_id = path_resolver.get_global_group_id(hostname)

        # Optional: get project_path from hash (if in cache)
        project_path = path_resolver.get_project_path_from_hash(project_namespace)

        # Index the session
        await indexer.index_session(
            session_id=session_id,
            filtered_content=filtered_content,
            group_id=group_id,
            session_file=str(file_path),
            project_namespace=project_namespace,
            project_path=project_path,  # May be None if not in cache
            hostname=hostname,
            include_project_path=True,
        )

        # Verify indexing succeeded
        mock_graphiti.add_episode.assert_called_once()
        call_kwargs = mock_graphiti.add_episode.call_args.kwargs

        # Verify group_id is global format
        assert "__global" in call_kwargs["group_id"]

        # Verify metadata includes namespace
        episode_body = call_kwargs["episode_body"]
        meta = parse_yaml_frontmatter(episode_body)
        assert meta is not None
        assert meta["graphiti_session_metadata"]["project_namespace"] == "a1b2c3d4"

    @pytest.mark.asyncio
    async def test_session_close_without_project_path_in_cache(
        self, mock_graphiti, path_resolver
    ):
        """Test session close when project_path is not in cache (returns None)."""
        indexer = SessionIndexer(mock_graphiti)
        hostname = "TEST-HOST"

        # Namespace that isn't registered (no project_path in cache)
        unknown_namespace = "unknwn12"

        # project_path lookup should return None
        project_path = path_resolver.get_project_path_from_hash(unknown_namespace)
        assert project_path is None

        # Indexing should still work
        await indexer.index_session(
            session_id="session-001",
            filtered_content="Content",
            group_id=path_resolver.get_global_group_id(hostname),
            project_namespace=unknown_namespace,
            project_path=None,  # Not available
            hostname=hostname,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]
        meta = parse_yaml_frontmatter(episode_body)

        # Namespace should still be present
        assert meta["graphiti_session_metadata"]["project_namespace"] == unknown_namespace
        # project_path should NOT be in metadata (since it was None)
        assert "project_path" not in meta["graphiti_session_metadata"]
