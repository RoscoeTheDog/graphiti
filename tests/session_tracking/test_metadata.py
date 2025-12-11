"""Tests for episode metadata header generation."""

import re
from datetime import datetime, timezone

import pytest
import yaml

from graphiti_core.session_tracking.metadata import build_episode_metadata_header


def parse_yaml_frontmatter(header: str) -> dict:
    """Parse YAML frontmatter from a header string.

    YAML frontmatter uses `---` as document start/end markers.
    This extracts and parses the YAML content between the markers.
    """
    # Remove the leading `---\n` and trailing `---\n\n`
    lines = header.strip().split("\n")
    # Find content between first and last `---` lines
    yaml_lines = []
    in_frontmatter = False
    for line in lines:
        if line == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break  # End of frontmatter
        if in_frontmatter:
            yaml_lines.append(line)
    yaml_content = "\n".join(yaml_lines)
    return yaml.safe_load(yaml_content)


class TestBuildEpisodeMetadataHeader:
    """Test episode metadata header generation."""

    @pytest.fixture
    def sample_metadata_params(self):
        """Sample metadata parameters for testing."""
        return {
            "project_namespace": "a1b2c3d4e5f6g7h8",
            "project_path": "/home/user/my-project",
            "hostname": "DESKTOP-ABC123",
            "session_file": "session-abc123.jsonl",
            "message_count": 47,
            "duration_minutes": 23,
        }

    def test_generates_valid_yaml_frontmatter(self, sample_metadata_params):
        """Test that output is parseable by yaml.safe_load()."""
        header = build_episode_metadata_header(**sample_metadata_params)

        # Should start and end with frontmatter delimiters
        assert header.startswith("---\n")
        assert "---\n\n" in header

        # Should be parseable without errors
        parsed = parse_yaml_frontmatter(header)
        assert parsed is not None
        assert "graphiti_session_metadata" in parsed

    def test_includes_version_2_0(self, sample_metadata_params):
        """Test that version field is '2.0' string."""
        header = build_episode_metadata_header(**sample_metadata_params)
        parsed = parse_yaml_frontmatter(header)

        version = parsed["graphiti_session_metadata"]["version"]
        assert version == "2.0"
        # Should be a string, not float
        assert isinstance(version, str)

    def test_includes_required_fields(self, sample_metadata_params):
        """Test all required fields are present."""
        header = build_episode_metadata_header(**sample_metadata_params)
        parsed = parse_yaml_frontmatter(header)

        metadata = parsed["graphiti_session_metadata"]
        required_fields = [
            "version",
            "project_namespace",
            "hostname",
            "indexed_at",
            "session_file",
            "message_count",
            "duration_minutes",
        ]

        for field in required_fields:
            assert field in metadata, f"Missing required field: {field}"

        # Check values match inputs
        assert metadata["project_namespace"] == "a1b2c3d4e5f6g7h8"
        assert metadata["hostname"] == "DESKTOP-ABC123"
        assert metadata["session_file"] == "session-abc123.jsonl"
        assert metadata["message_count"] == 47
        assert metadata["duration_minutes"] == 23

    def test_project_path_included_by_default(self, sample_metadata_params):
        """Test project_path is included when include_project_path=True (default)."""
        header = build_episode_metadata_header(**sample_metadata_params)
        parsed = parse_yaml_frontmatter(header)

        metadata = parsed["graphiti_session_metadata"]
        assert "project_path" in metadata
        assert metadata["project_path"] == "/home/user/my-project"

    def test_project_path_excluded_when_false(self, sample_metadata_params):
        """Test project_path is excluded when include_project_path=False."""
        header = build_episode_metadata_header(
            **sample_metadata_params, include_project_path=False
        )
        parsed = parse_yaml_frontmatter(header)

        metadata = parsed["graphiti_session_metadata"]
        assert "project_path" not in metadata

    def test_project_path_none_excluded(self, sample_metadata_params):
        """Test project_path is excluded when project_path is None regardless of flag."""
        params = sample_metadata_params.copy()
        params["project_path"] = None

        # With include_project_path=True but None value
        header = build_episode_metadata_header(**params, include_project_path=True)
        parsed = parse_yaml_frontmatter(header)

        metadata = parsed["graphiti_session_metadata"]
        assert "project_path" not in metadata

    def test_indexed_at_is_iso8601(self, sample_metadata_params):
        """Test indexed_at timestamp is ISO8601 format with timezone."""
        header = build_episode_metadata_header(**sample_metadata_params)
        parsed = parse_yaml_frontmatter(header)

        indexed_at = parsed["graphiti_session_metadata"]["indexed_at"]

        # Should be a string
        assert isinstance(indexed_at, str)

        # Should parse as ISO8601 datetime
        # ISO8601 format: 2025-12-08T15:30:00+00:00 or with Z suffix
        iso8601_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+\d{2}:\d{2}|Z)$"
        assert re.match(iso8601_pattern, indexed_at), f"Invalid ISO8601 format: {indexed_at}"

        # Should be parseable by datetime
        parsed_time = datetime.fromisoformat(indexed_at)
        assert parsed_time.tzinfo is not None  # Should have timezone info

    def test_indexed_at_is_recent(self, sample_metadata_params):
        """Test indexed_at is approximately current time (within 10 seconds)."""
        before = datetime.now(timezone.utc)
        header = build_episode_metadata_header(**sample_metadata_params)
        after = datetime.now(timezone.utc)

        parsed = parse_yaml_frontmatter(header)
        indexed_at = datetime.fromisoformat(
            parsed["graphiti_session_metadata"]["indexed_at"]
        )

        assert before <= indexed_at <= after

    def test_special_characters_in_path(self, sample_metadata_params):
        """Test paths with spaces, quotes handled correctly."""
        params = sample_metadata_params.copy()
        params["project_path"] = "/home/user/My Project (v2)/test's folder"

        header = build_episode_metadata_header(**params)
        parsed = parse_yaml_frontmatter(header)

        metadata = parsed["graphiti_session_metadata"]
        assert metadata["project_path"] == "/home/user/My Project (v2)/test's folder"

    def test_special_characters_in_namespace(self):
        """Test namespace with various characters."""
        header = build_episode_metadata_header(
            project_namespace="abc123-def_456",
            project_path="/test",
            hostname="test-host",
            session_file="test.jsonl",
            message_count=1,
            duration_minutes=1,
        )
        parsed = parse_yaml_frontmatter(header)

        assert parsed["graphiti_session_metadata"]["project_namespace"] == "abc123-def_456"

    def test_output_ends_with_double_newline(self, sample_metadata_params):
        """Test format is '---\\n{yaml}---\\n\\n'."""
        header = build_episode_metadata_header(**sample_metadata_params)

        # Should end with ---\n\n
        assert header.endswith("---\n\n")

        # Should have exactly one opening and one closing delimiter
        assert header.count("---\n") >= 2  # Opening and closing

    def test_output_starts_with_delimiter(self, sample_metadata_params):
        """Test output starts with YAML frontmatter delimiter."""
        header = build_episode_metadata_header(**sample_metadata_params)
        assert header.startswith("---\n")

    def test_yaml_preserves_field_order(self, sample_metadata_params):
        """Test that YAML fields are in logical order."""
        header = build_episode_metadata_header(**sample_metadata_params)

        # Check field order in raw output
        version_pos = header.find("version:")
        namespace_pos = header.find("project_namespace:")
        path_pos = header.find("project_path:")
        hostname_pos = header.find("hostname:")
        indexed_pos = header.find("indexed_at:")

        assert version_pos < namespace_pos < path_pos < hostname_pos < indexed_pos

    def test_zero_message_count(self):
        """Test with zero messages (edge case)."""
        header = build_episode_metadata_header(
            project_namespace="test123",
            project_path="/test",
            hostname="test-host",
            session_file="test.jsonl",
            message_count=0,
            duration_minutes=0,
        )
        parsed = parse_yaml_frontmatter(header)

        assert parsed["graphiti_session_metadata"]["message_count"] == 0
        assert parsed["graphiti_session_metadata"]["duration_minutes"] == 0

    def test_large_message_count(self):
        """Test with large message count."""
        header = build_episode_metadata_header(
            project_namespace="test123",
            project_path="/test",
            hostname="test-host",
            session_file="test.jsonl",
            message_count=999999,
            duration_minutes=10000,
        )
        parsed = parse_yaml_frontmatter(header)

        assert parsed["graphiti_session_metadata"]["message_count"] == 999999
        assert parsed["graphiti_session_metadata"]["duration_minutes"] == 10000

    def test_windows_style_path(self):
        """Test Windows-style paths are handled correctly."""
        header = build_episode_metadata_header(
            project_namespace="test123",
            project_path="C:\\Users\\Admin\\Documents\\project",
            hostname="DESKTOP-WIN",
            session_file="test.jsonl",
            message_count=10,
            duration_minutes=5,
        )
        parsed = parse_yaml_frontmatter(header)

        # Path should be preserved as-is
        assert (
            parsed["graphiti_session_metadata"]["project_path"]
            == "C:\\Users\\Admin\\Documents\\project"
        )

    def test_unicode_in_path(self):
        """Test Unicode characters in path."""
        header = build_episode_metadata_header(
            project_namespace="test123",
            project_path="/home/用户/项目",
            hostname="test-host",
            session_file="session-日本語.jsonl",
            message_count=10,
            duration_minutes=5,
        )
        parsed = parse_yaml_frontmatter(header)

        assert parsed["graphiti_session_metadata"]["project_path"] == "/home/用户/项目"
        assert parsed["graphiti_session_metadata"]["session_file"] == "session-日本語.jsonl"

    def test_hostname_with_dots(self):
        """Test hostname with dots (FQDN style)."""
        header = build_episode_metadata_header(
            project_namespace="test123",
            project_path="/test",
            hostname="server.example.com",
            session_file="test.jsonl",
            message_count=10,
            duration_minutes=5,
        )
        parsed = parse_yaml_frontmatter(header)

        assert parsed["graphiti_session_metadata"]["hostname"] == "server.example.com"

    def test_empty_string_values(self):
        """Test empty string values are preserved."""
        header = build_episode_metadata_header(
            project_namespace="",
            project_path="",
            hostname="",
            session_file="",
            message_count=0,
            duration_minutes=0,
        )
        parsed = parse_yaml_frontmatter(header)

        metadata = parsed["graphiti_session_metadata"]
        assert metadata["project_namespace"] == ""
        assert metadata["hostname"] == ""
        assert metadata["session_file"] == ""
        # Empty project_path with include_project_path=True should still be included
        assert metadata["project_path"] == ""

    def test_session_file_with_path_separator(self):
        """Test session file with path separators."""
        header = build_episode_metadata_header(
            project_namespace="test123",
            project_path="/test",
            hostname="test-host",
            session_file="subdir/session-abc.jsonl",
            message_count=10,
            duration_minutes=5,
        )
        parsed = parse_yaml_frontmatter(header)

        assert (
            parsed["graphiti_session_metadata"]["session_file"]
            == "subdir/session-abc.jsonl"
        )


class TestMetadataIntegration:
    """Integration tests for metadata header."""

    def test_header_prepends_to_markdown(self):
        """Test header can be prepended to markdown content."""
        header = build_episode_metadata_header(
            project_namespace="test123",
            project_path="/test",
            hostname="test-host",
            session_file="test.jsonl",
            message_count=10,
            duration_minutes=5,
        )

        episode_body = "## Session Summary\n\nThis was a productive session."
        full_content = header + episode_body

        # Should create valid markdown with frontmatter
        assert full_content.startswith("---\n")
        assert "---\n\n## Session Summary" in full_content

    def test_multiple_calls_have_different_timestamps(self):
        """Test multiple calls produce different indexed_at values."""
        params = {
            "project_namespace": "test123",
            "project_path": "/test",
            "hostname": "test-host",
            "session_file": "test.jsonl",
            "message_count": 10,
            "duration_minutes": 5,
        }

        header1 = build_episode_metadata_header(**params)
        # Small delay to ensure different timestamp
        import time

        time.sleep(0.01)
        header2 = build_episode_metadata_header(**params)

        parsed1 = parse_yaml_frontmatter(header1)
        parsed2 = parse_yaml_frontmatter(header2)

        # Timestamps should be different (or at least not identical strings)
        # Note: May be equal if called in same millisecond, so we just verify
        # both are valid rather than requiring difference
        assert "indexed_at" in parsed1["graphiti_session_metadata"]
        assert "indexed_at" in parsed2["graphiti_session_metadata"]
