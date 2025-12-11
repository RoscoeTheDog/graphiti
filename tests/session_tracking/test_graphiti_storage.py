"""Tests for Graphiti Storage Integration (Story 5).

Tests for the store_session() function in graphiti_storage.py, including:
- New namespace parameters (project_namespace, project_path, hostname, etc.)
- Metadata header prepending to episode body
- Source description with namespace prefix
- Backward compatibility (project_namespace=None)
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from graphiti_core.session_tracking.graphiti_storage import SessionStorage
from graphiti_core.session_tracking.summarizer import SessionSummary


def parse_yaml_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter from content string.

    YAML frontmatter uses `---` as document start/end markers.
    Returns None if no valid frontmatter found.
    """
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

    # Mock add_episode to return a result with episode.uuid
    mock_result = MagicMock()
    mock_result.episode.uuid = "test-uuid-12345"
    mock_result.nodes = []
    mock_result.edges = []
    mock.add_episode = AsyncMock(return_value=mock_result)

    return mock


@pytest.fixture
def sample_session_summary():
    """Create a sample SessionSummary for testing."""
    return SessionSummary(
        sequence_number=1,
        title="Test Session",
        slug="test-session",
        objective="Test the graphiti storage",
        completed_tasks=["Task 1", "Task 2"],
        blocked_items=["Blocked item 1"],
        next_steps=["Next step 1"],
        files_modified=["file1.py", "file2.py"],
        documentation_referenced=["docs/README.md"],
        key_decisions=["Decision 1"],
        mcp_tools_used=["tool1", "tool2"],
        token_count=1000,
        duration_estimate="~2h",
        created_at=datetime(2025, 12, 9, 10, 0, 0, tzinfo=timezone.utc),
        status="ACTIVE",
    )


@pytest.fixture
def sample_summary_short_duration():
    """Create a SessionSummary with short duration for testing."""
    return SessionSummary(
        sequence_number=2,
        title="Short Session",
        slug="short-session",
        objective="Quick test",
        completed_tasks=["Quick task"],
        blocked_items=[],
        next_steps=[],
        files_modified=[],
        documentation_referenced=[],
        key_decisions=[],
        mcp_tools_used=[],
        token_count=100,
        duration_estimate="~30m",
        created_at=datetime(2025, 12, 9, 11, 0, 0, tzinfo=timezone.utc),
        status="ACTIVE",
    )


@pytest.fixture
def sample_summary_no_duration():
    """Create a SessionSummary without duration for testing."""
    return SessionSummary(
        sequence_number=3,
        title="No Duration Session",
        slug="no-duration-session",
        objective="Test without duration",
        completed_tasks=[],
        blocked_items=[],
        next_steps=[],
        files_modified=[],
        documentation_referenced=[],
        key_decisions=[],
        mcp_tools_used=[],
        token_count=None,
        duration_estimate=None,
        created_at=datetime(2025, 12, 9, 12, 0, 0, tzinfo=timezone.utc),
        status="ACTIVE",
    )


class TestStoreSessionParameters:
    """Test store_session with new namespace parameters."""

    @pytest.mark.asyncio
    async def test_store_session_with_all_parameters(
        self, mock_graphiti, sample_session_summary
    ):
        """Test store_session with all new parameters provided (AC-5.1)."""
        storage = SessionStorage(mock_graphiti)

        result = await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="a1b2c3d4e5f6g7h8",
            project_path="/home/user/my-project",
            hostname="DESKTOP-TEST",
            include_project_path=True,
            session_file="session-test.jsonl",
            message_count=47,
        )

        # Verify add_episode was called
        mock_graphiti.add_episode.assert_called_once()
        assert result == "test-uuid-12345"

        # Get the call arguments
        call_kwargs = mock_graphiti.add_episode.call_args.kwargs

        # Verify group_id is passed through
        assert call_kwargs["group_id"] == "test-group"

    @pytest.mark.asyncio
    async def test_store_session_backward_compatibility(
        self, mock_graphiti, sample_session_summary
    ):
        """Test store_session works with project_namespace=None (AC-5.5)."""
        storage = SessionStorage(mock_graphiti)

        result = await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace=None,  # Legacy mode
        )

        # Should still succeed
        assert result == "test-uuid-12345"
        mock_graphiti.add_episode.assert_called_once()

        # Get episode_body from call
        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        # Should NOT have metadata header (backward compatibility)
        assert not episode_body.startswith("---\n")

        # Should still have session content
        assert "# Session 001: Test Session" in episode_body

    @pytest.mark.asyncio
    async def test_store_session_include_project_path_false(
        self, mock_graphiti, sample_session_summary
    ):
        """Test store_session with include_project_path=False."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="a1b2c3d4e5f6g7h8",
            project_path="/home/user/my-project",
            hostname="DESKTOP-TEST",
            include_project_path=False,  # Should exclude project_path from metadata
            session_file="session-test.jsonl",
            message_count=47,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        # Parse metadata header
        parsed = parse_yaml_frontmatter(episode_body)
        assert parsed is not None

        metadata = parsed["graphiti_session_metadata"]
        # project_path should NOT be in metadata
        assert "project_path" not in metadata

    @pytest.mark.asyncio
    async def test_store_session_hostname_defaults_to_socket(
        self, mock_graphiti, sample_session_summary
    ):
        """Test store_session uses socket.gethostname() when hostname=None."""
        storage = SessionStorage(mock_graphiti)

        with patch("socket.gethostname", return_value="MOCKED-HOSTNAME"):
            await storage.store_session(
                summary=sample_session_summary,
                group_id="test-group",
                project_namespace="a1b2c3d4e5f6g7h8",
                hostname=None,  # Should use socket.gethostname()
            )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        parsed = parse_yaml_frontmatter(episode_body)
        assert parsed is not None

        metadata = parsed["graphiti_session_metadata"]
        assert metadata["hostname"] == "MOCKED-HOSTNAME"


class TestMetadataHeaderPrepending:
    """Test metadata header is correctly prepended to episode body (AC-5.2)."""

    @pytest.mark.asyncio
    async def test_metadata_header_prepended(
        self, mock_graphiti, sample_session_summary
    ):
        """Test that metadata header is prepended to episode body."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="a1b2c3d4e5f6g7h8",
            project_path="/home/user/project",
            hostname="TEST-HOST",
            session_file="session.jsonl",
            message_count=50,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        # Should start with YAML frontmatter
        assert episode_body.startswith("---\n")

        # Should have valid YAML
        parsed = parse_yaml_frontmatter(episode_body)
        assert parsed is not None
        assert "graphiti_session_metadata" in parsed

        # Session content should follow frontmatter
        assert "# Session 001: Test Session" in episode_body

    @pytest.mark.asyncio
    async def test_metadata_header_contains_required_fields(
        self, mock_graphiti, sample_session_summary
    ):
        """Test metadata header contains all required fields."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="namespace123",
            project_path="/test/project",
            hostname="MY-HOST",
            session_file="my-session.jsonl",
            message_count=42,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        parsed = parse_yaml_frontmatter(episode_body)
        metadata = parsed["graphiti_session_metadata"]

        # Check all required fields
        assert metadata["version"] == "2.0"
        assert metadata["project_namespace"] == "namespace123"
        assert metadata["project_path"] == "/test/project"
        assert metadata["hostname"] == "MY-HOST"
        assert metadata["session_file"] == "my-session.jsonl"
        assert metadata["message_count"] == 42
        assert "indexed_at" in metadata

    @pytest.mark.asyncio
    async def test_metadata_header_duration_from_hours(
        self, mock_graphiti, sample_session_summary
    ):
        """Test duration_minutes calculation from ~Xh format."""
        storage = SessionStorage(mock_graphiti)

        # sample_session_summary has duration_estimate="~2h"
        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="test",
            hostname="host",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        parsed = parse_yaml_frontmatter(episode_body)
        metadata = parsed["graphiti_session_metadata"]

        # ~2h should become 120 minutes
        assert metadata["duration_minutes"] == 120

    @pytest.mark.asyncio
    async def test_metadata_header_duration_from_minutes(
        self, mock_graphiti, sample_summary_short_duration
    ):
        """Test duration_minutes calculation from ~Xm format."""
        storage = SessionStorage(mock_graphiti)

        # sample_summary_short_duration has duration_estimate="~30m"
        await storage.store_session(
            summary=sample_summary_short_duration,
            group_id="test-group",
            project_namespace="test",
            hostname="host",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        parsed = parse_yaml_frontmatter(episode_body)
        metadata = parsed["graphiti_session_metadata"]

        # ~30m should become 30 minutes
        assert metadata["duration_minutes"] == 30

    @pytest.mark.asyncio
    async def test_metadata_header_duration_none(
        self, mock_graphiti, sample_summary_no_duration
    ):
        """Test duration_minutes is 0 when duration_estimate is None."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_summary_no_duration,
            group_id="test-group",
            project_namespace="test",
            hostname="host",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        parsed = parse_yaml_frontmatter(episode_body)
        metadata = parsed["graphiti_session_metadata"]

        assert metadata["duration_minutes"] == 0

    @pytest.mark.asyncio
    async def test_default_session_file_generated(
        self, mock_graphiti, sample_session_summary
    ):
        """Test default session_file is generated from slug when not provided."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="test",
            hostname="host",
            session_file=None,  # Should auto-generate
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        parsed = parse_yaml_frontmatter(episode_body)
        metadata = parsed["graphiti_session_metadata"]

        # Should use slug to generate filename
        assert metadata["session_file"] == "session-test-session.jsonl"


class TestSourceDescriptionPrefix:
    """Test source_description includes namespace prefix (AC-5.3)."""

    @pytest.mark.asyncio
    async def test_source_description_with_namespace_prefix(
        self, mock_graphiti, sample_session_summary
    ):
        """Test source_description is prefixed with [{namespace[:8]}]."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="a1b2c3d4e5f6g7h8i9j0",  # Long namespace
            hostname="host",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        source_description = call_kwargs["source_description"]

        # Should start with first 8 chars of namespace
        assert source_description.startswith("[a1b2c3d4]")

        # Should contain task counts
        assert "2 completed tasks" in source_description
        assert "1 blocked items" in source_description
        assert "2 files modified" in source_description

    @pytest.mark.asyncio
    async def test_source_description_without_namespace(
        self, mock_graphiti, sample_session_summary
    ):
        """Test source_description without namespace prefix (backward compat)."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace=None,  # No namespace
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        source_description = call_kwargs["source_description"]

        # Should NOT have namespace prefix
        assert not source_description.startswith("[")

        # Should still have counts
        assert "2 completed tasks" in source_description
        assert "Session handoff summary" in source_description

    @pytest.mark.asyncio
    async def test_source_description_short_namespace(
        self, mock_graphiti, sample_session_summary
    ):
        """Test source_description with namespace shorter than 8 chars."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="abc",  # Short namespace
            hostname="host",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        source_description = call_kwargs["source_description"]

        # Should use full namespace (since it's < 8 chars)
        assert source_description.startswith("[abc]")


class TestGroupIdHandling:
    """Test group_id parameter handling (AC-5.4)."""

    @pytest.mark.asyncio
    async def test_group_id_passed_to_graphiti(
        self, mock_graphiti, sample_session_summary
    ):
        """Test group_id is passed to add_episode."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="global-session-group",
            project_namespace="test",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs["group_id"] == "global-session-group"

    @pytest.mark.asyncio
    async def test_group_id_with_namespace(
        self, mock_graphiti, sample_session_summary
    ):
        """Test group_id works independently of namespace."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="my-custom-group",
            project_namespace="different-namespace",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs

        # group_id should be what we passed
        assert call_kwargs["group_id"] == "my-custom-group"

        # namespace should be in the episode body metadata
        parsed = parse_yaml_frontmatter(call_kwargs["episode_body"])
        assert parsed["graphiti_session_metadata"]["project_namespace"] == "different-namespace"


class TestHandoffFileReference:
    """Test handoff_file_path handling."""

    @pytest.mark.asyncio
    async def test_handoff_file_appended_to_body(
        self, mock_graphiti, sample_session_summary
    ):
        """Test handoff file reference is appended to episode body."""
        storage = SessionStorage(mock_graphiti)

        handoff_path = Path("/path/to/handoff.md")
        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="test",
            handoff_file_path=handoff_path,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        # Should contain handoff file reference (path may be platform-specific)
        assert "**Handoff File**:" in episode_body
        # Path is rendered as string, may have platform-specific separators
        assert str(handoff_path) in episode_body or "handoff.md" in episode_body

    @pytest.mark.asyncio
    async def test_no_handoff_file_reference_when_none(
        self, mock_graphiti, sample_session_summary
    ):
        """Test no handoff reference when handoff_file_path=None."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="test",
            handoff_file_path=None,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        # Should NOT contain handoff file reference
        assert "**Handoff File**:" not in episode_body


class TestPreviousSessionLinking:
    """Test previous_session_uuid handling."""

    @pytest.mark.asyncio
    async def test_previous_session_linked(
        self, mock_graphiti, sample_session_summary
    ):
        """Test previous_session_uuid is passed to add_episode."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            previous_session_uuid="prev-uuid-123",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs["previous_episode_uuids"] == ["prev-uuid-123"]

    @pytest.mark.asyncio
    async def test_no_previous_session(
        self, mock_graphiti, sample_session_summary
    ):
        """Test previous_episode_uuids is None when no previous session."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            previous_session_uuid=None,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs["previous_episode_uuids"] is None


class TestEpisodeNaming:
    """Test episode naming convention."""

    @pytest.mark.asyncio
    async def test_episode_name_format(
        self, mock_graphiti, sample_session_summary
    ):
        """Test episode name follows 'Session XXX: Title' format."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs["name"] == "Session 001: Test Session"

    @pytest.mark.asyncio
    async def test_episode_name_large_sequence(self, mock_graphiti):
        """Test episode name with large sequence number."""
        summary = SessionSummary(
            sequence_number=999,
            title="Large Sequence",
            slug="large-sequence",
            objective="Test",
            completed_tasks=[],
            blocked_items=[],
            next_steps=[],
            files_modified=[],
            documentation_referenced=[],
            key_decisions=[],
            mcp_tools_used=[],
            token_count=None,
            duration_estimate=None,
            created_at=datetime.now(timezone.utc),
        )

        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=summary,
            group_id="test-group",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs["name"] == "Session 999: Large Sequence"


class TestErrorHandling:
    """Test error handling in store_session."""

    @pytest.mark.asyncio
    async def test_graphiti_error_propagates(
        self, mock_graphiti, sample_session_summary
    ):
        """Test that Graphiti errors are propagated."""
        mock_graphiti.add_episode = AsyncMock(side_effect=Exception("Graphiti error"))

        storage = SessionStorage(mock_graphiti)

        with pytest.raises(Exception, match="Graphiti error"):
            await storage.store_session(
                summary=sample_session_summary,
                group_id="test-group",
            )

    @pytest.mark.asyncio
    async def test_invalid_duration_format_handled(self, mock_graphiti):
        """Test invalid duration_estimate format is handled gracefully."""
        summary = SessionSummary(
            sequence_number=1,
            title="Invalid Duration",
            slug="invalid-duration",
            objective="Test",
            completed_tasks=[],
            blocked_items=[],
            next_steps=[],
            files_modified=[],
            documentation_referenced=[],
            key_decisions=[],
            mcp_tools_used=[],
            token_count=None,
            duration_estimate="invalid-format",  # Not ~Xh or ~Xm
            created_at=datetime.now(timezone.utc),
        )

        storage = SessionStorage(mock_graphiti)

        # Should not raise, should use 0 as fallback
        await storage.store_session(
            summary=summary,
            group_id="test-group",
            project_namespace="test",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        parsed = parse_yaml_frontmatter(call_kwargs["episode_body"])
        assert parsed["graphiti_session_metadata"]["duration_minutes"] == 0


class TestIntegration:
    """Integration tests for end-to-end storage flow."""

    @pytest.mark.asyncio
    async def test_full_episode_content_structure(
        self, mock_graphiti, sample_session_summary
    ):
        """Test complete episode content structure with metadata."""
        storage = SessionStorage(mock_graphiti)

        handoff_path = Path("/handoff/file.md")
        await storage.store_session(
            summary=sample_session_summary,
            group_id="integration-test-group",
            project_namespace="integ12345678",
            project_path="/home/user/integration-project",
            hostname="INTEG-HOST",
            session_file="integration-session.jsonl",
            message_count=100,
            handoff_file_path=handoff_path,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        # Should start with YAML frontmatter
        assert episode_body.startswith("---\n")

        # Parse the frontmatter using our helper
        parsed = parse_yaml_frontmatter(episode_body)
        assert parsed is not None
        assert "graphiti_session_metadata" in parsed

        # Check metadata fields
        metadata = parsed["graphiti_session_metadata"]
        assert metadata["project_namespace"] == "integ12345678"
        assert metadata["hostname"] == "INTEG-HOST"
        assert metadata["message_count"] == 100

        # Second part should contain session content
        assert "# Session 001: Test Session" in episode_body
        assert "**Status**: ACTIVE" in episode_body
        assert "## Completed" in episode_body

        # Handoff file should be at the end
        assert "**Handoff File**:" in episode_body
        assert "file.md" in episode_body

    @pytest.mark.asyncio
    async def test_yaml_frontmatter_valid_for_parsers(
        self, mock_graphiti, sample_session_summary
    ):
        """Test YAML frontmatter is valid for standard YAML parsers."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
            project_namespace="abc123",
            project_path="/test",
            hostname="HOST",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        episode_body = call_kwargs["episode_body"]

        # Extract just the frontmatter
        end_idx = episode_body.find("---\n\n")
        if end_idx > 0:
            frontmatter = episode_body[: end_idx + 4]  # Include closing ---

            # Should be parseable by yaml.safe_load
            parsed = yaml.safe_load(frontmatter[4:end_idx])  # Skip opening ---
            assert "graphiti_session_metadata" in parsed

    @pytest.mark.asyncio
    async def test_reference_time_from_summary(
        self, mock_graphiti, sample_session_summary
    ):
        """Test reference_time comes from summary.created_at."""
        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs["reference_time"] == sample_session_summary.created_at

    @pytest.mark.asyncio
    async def test_episode_type_is_text(
        self, mock_graphiti, sample_session_summary
    ):
        """Test episode type is EpisodeType.text."""
        from graphiti_core.nodes import EpisodeType

        storage = SessionStorage(mock_graphiti)

        await storage.store_session(
            summary=sample_session_summary,
            group_id="test-group",
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs["source"] == EpisodeType.text
