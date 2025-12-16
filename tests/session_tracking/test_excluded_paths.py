"""Tests for session tracking excluded paths feature (Story 1).

Tests for:
- excluded_paths configuration in SessionTrackingConfig
- Path exclusion logic in SessionManager
- Platform-agnostic path matching
- Glob pattern support
"""

import platform
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from graphiti_core.session_tracking.path_resolver import ClaudePathResolver
from graphiti_core.session_tracking.session_manager import SessionManager
from mcp_server.unified_config import SessionTrackingConfig


class TestExcludedPathsConfig:
    """Test excluded_paths configuration field."""

    def test_empty_excluded_paths_default(self):
        """Test default excluded_paths is empty list (AC-2)."""
        config = SessionTrackingConfig(enabled=True, watch_path="~/.claude/projects")
        assert config.excluded_paths == []
        assert isinstance(config.excluded_paths, list)

    def test_excluded_paths_accepts_list(self):
        """Test excluded_paths accepts list of strings."""
        config = SessionTrackingConfig(
            enabled=True,
            watch_path="~/.claude/projects",
            excluded_paths=["/absolute/path", "relative/path", "**/pattern/**"],
        )
        assert config.excluded_paths == ["/absolute/path", "relative/path", "**/pattern/**"]

    def test_excluded_paths_type_validation(self):
        """Test excluded_paths validates as list of strings."""
        # Should accept list of strings
        config = SessionTrackingConfig(
            enabled=True, watch_path="~/.claude/projects", excluded_paths=["path1", "path2"]
        )
        assert len(config.excluded_paths) == 2

        # Empty list should be valid
        config_empty = SessionTrackingConfig(
            enabled=True, watch_path="~/.claude/projects", excluded_paths=[]
        )
        assert config_empty.excluded_paths == []


class TestPathExclusionLogic:
    """Test _is_path_excluded() method in SessionManager."""

    @pytest.fixture
    def mock_graphiti(self):
        """Create mock Graphiti instance."""
        return MagicMock()

    @pytest.fixture
    def path_resolver(self):
        """Create ClaudePathResolver for testing."""
        return ClaudePathResolver()

    @pytest.fixture
    def session_manager_factory(self, mock_graphiti, path_resolver):
        """Factory for creating SessionManager instances with different configs."""

        def _create_manager(excluded_paths=None, watch_path=None):
            # Create temporary watch path if not provided
            if watch_path is None:
                watch_path = Path(tempfile.mkdtemp())
            else:
                watch_path = Path(watch_path)

            manager = SessionManager(
                path_resolver=path_resolver,
                excluded_paths=excluded_paths or [],
                watch_path=watch_path,
            )
            return manager

        return _create_manager

    def test_empty_excluded_paths_no_exclusions(self, session_manager_factory):
        """Test empty excluded_paths list excludes nothing."""
        manager = session_manager_factory(excluded_paths=[])

        # Any path should NOT be excluded
        test_paths = [
            "/absolute/path/session.jsonl",
            "relative/path/session.jsonl",
            "/temporal-server/session.jsonl",
        ]

        for path in test_paths:
            assert manager._is_path_excluded(Path(path)) is False

    def test_absolute_path_exclusion_exact_match(self, session_manager_factory):
        """Test absolute path exclusion with exact match."""
        excluded = "/projects/temporal-server"
        manager = session_manager_factory(excluded_paths=[excluded])

        # Should exclude paths under the excluded directory
        assert manager._is_path_excluded(Path("/projects/temporal-server/session.jsonl"))
        assert manager._is_path_excluded(Path("/projects/temporal-server/subdir/session.jsonl"))

        # Should NOT exclude paths outside the excluded directory
        assert not manager._is_path_excluded(Path("/projects/other-server/session.jsonl"))
        assert not manager._is_path_excluded(Path("/different/temporal-server/session.jsonl"))

    def test_relative_path_exclusion(self, session_manager_factory):
        """Test relative path exclusion (relative to watch_path)."""
        with tempfile.TemporaryDirectory() as watch_dir:
            manager = session_manager_factory(
                excluded_paths=["temporal-server"], watch_path=watch_dir
            )

            # Build paths relative to watch_dir
            excluded_path = Path(watch_dir) / "temporal-server" / "session.jsonl"
            non_excluded_path = Path(watch_dir) / "other-project" / "session.jsonl"

            assert manager._is_path_excluded(excluded_path)
            assert not manager._is_path_excluded(non_excluded_path)

    def test_glob_pattern_simple_wildcard(self, session_manager_factory):
        """Test glob pattern with simple wildcard (**)."""
        with tempfile.TemporaryDirectory() as watch_dir:
            manager = session_manager_factory(
                excluded_paths=["**/temporal-*/**"], watch_path=watch_dir
            )

            # Build test paths
            watch_path = Path(watch_dir)
            excluded_paths = [
                watch_path / "temporal-server" / "session.jsonl",
                watch_path / "project" / "temporal-orchestrator" / "session.jsonl",
                watch_path / "deep" / "nested" / "temporal-worker" / "data" / "session.jsonl",
            ]

            non_excluded_paths = [
                watch_path / "other-server" / "session.jsonl",
                watch_path / "project" / "session.jsonl",
            ]

            for path in excluded_paths:
                assert manager._is_path_excluded(
                    path
                ), f"Expected {path} to be excluded by pattern **/temporal-*/**"

            for path in non_excluded_paths:
                assert not manager._is_path_excluded(
                    path
                ), f"Expected {path} NOT to be excluded"

    def test_glob_pattern_multi_level(self, session_manager_factory):
        """Test glob pattern with multiple directory levels."""
        with tempfile.TemporaryDirectory() as watch_dir:
            manager = session_manager_factory(
                excluded_paths=["**/orchestrator/**/sessions/**"], watch_path=watch_dir
            )

            watch_path = Path(watch_dir)

            # Should match multi-level pattern
            excluded = watch_path / "project" / "orchestrator" / "worker1" / "sessions" / "s1.jsonl"
            assert manager._is_path_excluded(excluded)

            # Should NOT match if path doesn't have all components
            non_excluded = watch_path / "project" / "orchestrator" / "s1.jsonl"
            assert not manager._is_path_excluded(non_excluded)

    def test_platform_specific_path_normalization_windows(self, session_manager_factory):
        """Test Windows backslash normalization."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        with tempfile.TemporaryDirectory() as watch_dir:
            # Use Windows-style backslash paths
            manager = session_manager_factory(
                excluded_paths=["temporal-server"], watch_path=watch_dir
            )

            # Test with backslash path
            windows_path = Path(watch_dir) / "temporal-server" / "session.jsonl"
            assert manager._is_path_excluded(windows_path)

    def test_platform_specific_path_normalization_unix(self, session_manager_factory):
        """Test Unix forward slash path handling."""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")

        with tempfile.TemporaryDirectory() as watch_dir:
            manager = session_manager_factory(
                excluded_paths=["temporal-server"], watch_path=watch_dir
            )

            unix_path = Path(watch_dir) / "temporal-server" / "session.jsonl"
            assert manager._is_path_excluded(unix_path)

    def test_multiple_exclusion_patterns(self, session_manager_factory):
        """Test configuration with multiple exclusion patterns."""
        with tempfile.TemporaryDirectory() as watch_dir:
            manager = session_manager_factory(
                excluded_paths=[
                    "**/temporal-*/**",
                    "**/orchestrator/**",
                    "private-project",
                ],
                watch_path=watch_dir,
            )

            watch_path = Path(watch_dir)

            # Each pattern should work
            assert manager._is_path_excluded(watch_path / "temporal-server" / "s1.jsonl")
            assert manager._is_path_excluded(watch_path / "orchestrator" / "s2.jsonl")
            assert manager._is_path_excluded(watch_path / "private-project" / "s3.jsonl")

            # Non-matching path should not be excluded
            assert not manager._is_path_excluded(watch_path / "public-project" / "s4.jsonl")


class TestSessionManagerIntegration:
    """Integration tests for SessionManager with excluded paths."""

    @pytest.fixture
    def mock_graphiti(self):
        """Create mock Graphiti instance."""
        return MagicMock()

    @pytest.fixture
    def path_resolver(self):
        """Create ClaudePathResolver for testing."""
        return ClaudePathResolver()

    def test_start_tracking_session_skips_excluded(
        self, mock_graphiti, path_resolver, tmp_path
    ):
        """Test _start_tracking_session() skips excluded paths."""
        # Create temporary session file
        excluded_dir = tmp_path / "temporal-server"
        excluded_dir.mkdir()
        session_file = excluded_dir / "session.jsonl"
        session_file.write_text('{"role": "user", "content": "test"}\n')

        manager = SessionManager(
            path_resolver=path_resolver,
            excluded_paths=["temporal-server"],
            watch_path=tmp_path,
        )

        # Mock path resolver to return project hash
        with patch.object(path_resolver, "get_project_hash", return_value="test-hash"):
            # Call _start_tracking_session with excluded path
            manager._start_tracking_session(session_file, "test-hash")

            # Session should NOT be added to active_sessions
            assert len(manager.active_sessions) == 0

    def test_start_tracking_session_tracks_non_excluded(
        self, mock_graphiti, path_resolver, tmp_path
    ):
        """Test _start_tracking_session() still tracks non-excluded paths."""
        # Create temporary session file in non-excluded directory
        allowed_dir = tmp_path / "allowed-project"
        allowed_dir.mkdir()
        session_file = allowed_dir / "session.jsonl"
        session_file.write_text('{"role": "user", "content": "test"}\n')

        manager = SessionManager(
            path_resolver=path_resolver,
            excluded_paths=["temporal-server"],
            watch_path=tmp_path,
        )

        # Mock path resolver and parser
        with patch.object(path_resolver, "get_project_hash", return_value="test-hash"):
            with patch.object(path_resolver, "extract_session_id_from_path", return_value="s123"):
                with patch.object(manager.parser, "parse_file", return_value=([], 0)):
                    # Call _start_tracking_session with non-excluded path
                    manager._start_tracking_session(session_file, "test-hash")

                    # Session SHOULD be added to active_sessions
                    assert len(manager.active_sessions) == 1
                    assert "s123" in manager.active_sessions

    @patch("graphiti_core.session_tracking.session_manager.logger")
    def test_excluded_session_logs_debug_message(
        self, mock_logger, mock_graphiti, path_resolver, tmp_path
    ):
        """Test that excluded session logs DEBUG message (AC-9)."""
        # Create temporary session file
        excluded_dir = tmp_path / "temporal-server"
        excluded_dir.mkdir()
        session_file = excluded_dir / "session.jsonl"
        session_file.write_text('{"role": "user", "content": "test"}\n')

        manager = SessionManager(
            path_resolver=path_resolver,
            excluded_paths=["temporal-server"],
            watch_path=tmp_path,
        )

        with patch.object(path_resolver, "get_project_hash", return_value="test-hash"):
            # Call _start_tracking_session with excluded path
            manager._start_tracking_session(session_file, "test-hash")

            # Verify DEBUG log was called
            mock_logger.debug.assert_called_once()
            log_message = mock_logger.debug.call_args[0][0]
            assert "Skipping excluded path" in log_message
            assert str(session_file) in log_message


class TestSecurityTests:
    """Security tests for excluded paths feature."""

    @pytest.fixture
    def mock_graphiti(self):
        """Create mock Graphiti instance."""
        return MagicMock()

    @pytest.fixture
    def path_resolver(self):
        """Create ClaudePathResolver for testing."""
        return ClaudePathResolver()

    def test_path_traversal_prevention(self, mock_graphiti, path_resolver):
        """Test that path traversal patterns are handled safely."""
        with tempfile.TemporaryDirectory() as watch_dir:
            manager = SessionManager(
                path_resolver=path_resolver,
                excluded_paths=["../sensitive", "../../etc"],  # Malicious patterns
                watch_path=Path(watch_dir),
            )

            # Test that path traversal doesn't cause errors
            test_path = Path(watch_dir) / "normal-project" / "session.jsonl"
            # Should not raise exception
            result = manager._is_path_excluded(test_path)
            assert isinstance(result, bool)

    def test_absolute_path_outside_watch_path(self, mock_graphiti, path_resolver):
        """Test that absolute path outside watch_path doesn't cause errors."""
        with tempfile.TemporaryDirectory() as watch_dir:
            manager = SessionManager(
                path_resolver=path_resolver,
                excluded_paths=["/etc/passwd"],  # Absolute path outside watch_path
                watch_path=Path(watch_dir),
            )

            # Test path inside watch_path
            test_path = Path(watch_dir) / "project" / "session.jsonl"
            # Should not raise exception
            result = manager._is_path_excluded(test_path)
            assert isinstance(result, bool)
