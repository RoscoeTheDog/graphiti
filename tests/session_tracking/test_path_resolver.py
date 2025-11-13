"""Tests for Claude Code path resolver."""

import hashlib
import platform
import tempfile
from pathlib import Path

import pytest

from graphiti_core.session_tracking.path_resolver import ClaudePathResolver


class TestClaudePathResolver:
    """Test Claude Code path resolution."""

    def test_default_claude_dir(self):
        """Test default Claude directory resolution."""
        resolver = ClaudePathResolver()
        expected = Path.home() / ".claude"
        assert resolver.claude_dir == expected
        assert resolver.projects_dir == expected / "projects"

    def test_custom_claude_dir(self):
        """Test custom Claude directory."""
        custom_dir = Path("/custom/claude")
        resolver = ClaudePathResolver(claude_dir=custom_dir)
        assert resolver.claude_dir == custom_dir
        assert resolver.projects_dir == custom_dir / "projects"

    def test_get_project_hash(self):
        """Test project hash calculation."""
        resolver = ClaudePathResolver()
        project_path = "/home/user/projects/my-app"

        # Get hash
        hash1 = resolver.get_project_hash(project_path)
        assert len(hash1) == 8
        assert hash1.isalnum()

        # Hash should be consistent
        hash2 = resolver.get_project_hash(project_path)
        assert hash1 == hash2

        # Different paths should have different hashes
        other_path = "/home/user/projects/other-app"
        hash3 = resolver.get_project_hash(other_path)
        assert hash3 != hash1

    def test_hash_caching(self):
        """Test that hashes are cached."""
        resolver = ClaudePathResolver()
        project_path = "/home/user/projects/my-app"

        # First call
        hash1 = resolver.get_project_hash(project_path)

        # Should be in cache
        assert project_path in resolver._hash_cache
        assert resolver._hash_cache[project_path] == hash1

        # Second call should use cache
        hash2 = resolver.get_project_hash(project_path)
        assert hash2 == hash1

    def test_normalize_path_for_hash(self):
        """Test path normalization for hashing (always UNIX format)."""
        resolver = ClaudePathResolver()

        # Test POSIX paths
        if platform.system() != "Windows":
            normalized = resolver._normalize_path_for_hash("/home/user/project")
            assert normalized.startswith("/")
            assert "\\" not in normalized
            assert ":" not in normalized
        else:
            # Test Windows paths - should convert to MSYS format
            normalized = resolver._normalize_path_for_hash("C:\\Users\\user\\project")
            # Should convert to /c/Users/user/project format (lowercase drive)
            assert normalized.startswith("/c/") or normalized.startswith("/C/")
            assert "\\" not in normalized
            assert ":" not in normalized  # No colons in MSYS format

    def test_to_native_path(self):
        """Test conversion from UNIX to native path format."""
        resolver = ClaudePathResolver()

        if platform.system() == "Windows":
            # UNIX format should convert to Windows format
            unix_path = "/c/Users/Admin/project"
            native = resolver._to_native_path(unix_path)
            # Should be C:\Users\Admin\project or C:/Users/Admin/project
            path_str = str(native)
            assert path_str.startswith("C:")
            assert "Users" in path_str
        else:
            # On Unix, should pass through unchanged
            unix_path = "/home/user/project"
            native = resolver._to_native_path(unix_path)
            assert str(native) == unix_path

    def test_returned_paths_are_native_format(self):
        """Test that all returned Path objects use native OS format."""
        resolver = ClaudePathResolver()
        project_path = "/tmp/test-project"

        # Get various paths
        sessions_dir = resolver.get_sessions_dir(project_path)
        session_file = resolver.get_session_file(project_path, "test-session-123")

        # Path objects should work with native OS operations
        assert isinstance(sessions_dir, Path)
        assert isinstance(session_file, Path)

        # On Windows, paths should contain backslashes when stringified with str()
        # On Unix, paths should contain forward slashes
        if platform.system() == "Windows":
            # Path objects on Windows use backslashes
            assert "\\" in str(sessions_dir) or "/" in str(sessions_dir.as_posix())
        else:
            # Path objects on Unix use forward slashes
            assert "/" in str(sessions_dir)

    def test_get_sessions_dir(self):
        """Test sessions directory resolution."""
        resolver = ClaudePathResolver()
        project_path = "/home/user/projects/my-app"

        sessions_dir = resolver.get_sessions_dir(project_path)

        # Should include projects directory, hash, and sessions subdirectory
        assert "projects" in sessions_dir.parts
        assert "sessions" in sessions_dir.parts

        # Hash should be in the path
        project_hash = resolver.get_project_hash(project_path)
        assert project_hash in sessions_dir.parts

    def test_get_session_file(self):
        """Test session file path resolution."""
        resolver = ClaudePathResolver()
        project_path = "/home/user/projects/my-app"
        session_id = "abc-123-def-456"

        session_file = resolver.get_session_file(project_path, session_id)

        # Should end with session_id.jsonl
        assert session_file.name == f"{session_id}.jsonl"
        assert session_file.suffix == ".jsonl"

        # Should be in sessions directory
        assert session_file.parent.name == "sessions"

    def test_extract_session_id_from_path(self):
        """Test session ID extraction from file path."""
        resolver = ClaudePathResolver()

        # Valid session file
        file_path = Path("/home/.claude/projects/abc123/sessions/session-id-123.jsonl")
        session_id = resolver.extract_session_id_from_path(file_path)
        assert session_id == "session-id-123"

        # Non-JSONL file
        file_path = Path("/home/.claude/projects/abc123/sessions/data.txt")
        session_id = resolver.extract_session_id_from_path(file_path)
        assert session_id is None

    def test_is_session_file(self):
        """Test session file validation."""
        resolver = ClaudePathResolver()

        # Valid session file
        valid_path = Path("/home/.claude/projects/abc123/sessions/session-1.jsonl")
        assert resolver.is_session_file(valid_path) is True

        # Not a JSONL file
        invalid_path = Path("/home/.claude/projects/abc123/sessions/data.txt")
        assert resolver.is_session_file(invalid_path) is False

        # Not in sessions directory
        invalid_path = Path("/home/.claude/projects/abc123/session-1.jsonl")
        assert resolver.is_session_file(invalid_path) is False

        # Not in projects hierarchy
        invalid_path = Path("/home/user/data/session-1.jsonl")
        assert resolver.is_session_file(invalid_path) is False

    def test_resolve_project_from_session_file(self):
        """Test project hash resolution from session file."""
        resolver = ClaudePathResolver()

        # Valid session file
        file_path = Path("/home/.claude/projects/abc12345/sessions/session-1.jsonl")
        project_hash = resolver.resolve_project_from_session_file(file_path)
        assert project_hash == "abc12345"

        # Invalid path
        invalid_path = Path("/home/user/data/session-1.jsonl")
        project_hash = resolver.resolve_project_from_session_file(invalid_path)
        assert project_hash is None

    def test_find_project_sessions_empty(self):
        """Test finding sessions when directory doesn't exist."""
        resolver = ClaudePathResolver()
        project_path = "/nonexistent/project"

        sessions = resolver.find_project_sessions(project_path)
        assert sessions == []

    def test_find_project_sessions_with_files(self):
        """Test finding sessions with actual files."""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            resolver = ClaudePathResolver(claude_dir=tmpdir_path)

            # Create project path
            project_path = "/tmp/test-project"
            project_hash = resolver.get_project_hash(project_path)
            sessions_dir = tmpdir_path / "projects" / project_hash / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)

            # Create some session files
            (sessions_dir / "session-1.jsonl").touch()
            (sessions_dir / "session-2.jsonl").touch()
            (sessions_dir / "session-3.jsonl").touch()
            (sessions_dir / "not-a-session.txt").touch()

            # Find sessions
            sessions = resolver.find_project_sessions(project_path)

            # Should find only JSONL files
            assert len(sessions) == 3
            assert all(p.suffix == ".jsonl" for p in sessions)
            assert all(p.name.startswith("session-") for p in sessions)

    def test_list_all_projects(self):
        """Test listing all projects."""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            resolver = ClaudePathResolver(claude_dir=tmpdir_path)

            projects_dir = tmpdir_path / "projects"
            projects_dir.mkdir(exist_ok=True)

            # Create multiple project directories with sessions
            for i in range(3):
                project_hash = f"hash{i:03d}"
                sessions_dir = projects_dir / project_hash / "sessions"
                sessions_dir.mkdir(parents=True, exist_ok=True)
                (sessions_dir / "session-1.jsonl").touch()

            # List projects
            projects = resolver.list_all_projects()

            # Should find 3 projects
            assert len(projects) == 3
            assert "hash000" in projects
            assert "hash001" in projects
            assert "hash002" in projects

            # Each should map to sessions directory
            for project_hash, sessions_path in projects.items():
                assert sessions_path.name == "sessions"
                assert sessions_path.parent.name == project_hash

    def test_list_all_projects_empty(self):
        """Test listing projects when directory doesn't exist."""
        # Use a path that definitely doesn't exist
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Use a non-existent subdirectory
            resolver = ClaudePathResolver(claude_dir=tmpdir_path / "nonexistent")

            projects = resolver.list_all_projects()
            assert projects == {}

    def test_watch_all_projects(self):
        """Test getting path to watch for all projects."""
        resolver = ClaudePathResolver()
        watch_path = resolver.watch_all_projects()

        assert watch_path == resolver.projects_dir
        assert watch_path.name == "projects"

    def test_path_normalization_consistency(self):
        """Test that different representations of same path produce same hash."""
        resolver = ClaudePathResolver()

        if platform.system() == "Windows":
            # Test Windows path variations
            paths = [
                "C:/Users/Admin/project",
                "C:\\Users\\Admin\\project",
                "C:/Users/Admin/project/",
            ]
        else:
            # Test Unix path variations
            paths = [
                "/home/user/project",
                "/home/user/project/",
                "/home/user/./project",
            ]

        hashes = [resolver.get_project_hash(p) for p in paths]

        # All hashes should be the same
        assert len(set(hashes)) == 1, f"Hashes differ: {hashes}"

    def test_cross_platform_hash_consistency(self):
        """Test that equivalent paths on different platforms produce same hash."""
        resolver = ClaudePathResolver()

        # These represent the same logical path on different platforms
        if platform.system() == "Windows":
            test_path = "C:/Users/Admin/Documents/project"
            expected_unix = "/c/Users/Admin/Documents/project"
        else:
            test_path = "/home/user/Documents/project"
            expected_unix = "/home/user/Documents/project"

        # Normalize for hashing
        normalized = resolver._normalize_path_for_hash(test_path)

        # Should always be in UNIX format
        assert normalized.startswith("/")
        assert "\\" not in normalized
        assert ":" not in normalized  # No colons in MSYS format


class TestPathResolverIntegration:
    """Integration tests for path resolver."""

    def test_full_workflow(self):
        """Test complete workflow of path resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            resolver = ClaudePathResolver(claude_dir=tmpdir_path)

            # Setup project
            project_path = "/tmp/my-test-project"
            session_id = "test-session-123"

            # Get expected paths
            sessions_dir = resolver.get_sessions_dir(project_path)
            session_file = resolver.get_session_file(project_path, session_id)

            # Create the directory structure
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_file.touch()

            # Verify we can find it
            sessions = resolver.find_project_sessions(project_path)
            assert len(sessions) == 1
            assert sessions[0] == session_file

            # Verify we can extract session ID
            extracted_id = resolver.extract_session_id_from_path(session_file)
            assert extracted_id == session_id

            # Verify it's recognized as a session file
            assert resolver.is_session_file(session_file) is True

            # Verify we can resolve project from file
            project_hash = resolver.resolve_project_from_session_file(session_file)
            expected_hash = resolver.get_project_hash(project_path)
            assert project_hash == expected_hash
