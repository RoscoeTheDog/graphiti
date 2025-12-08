"""Tests for rolling period filter (Story 12 - keep_length_days).

Tests time-based session discovery filtering to prevent bulk historical indexing.
"""

import os
import tempfile
import time
from pathlib import Path

import pytest

from graphiti_core.session_tracking import SessionManager
from graphiti_core.session_tracking.path_resolver import ClaudePathResolver


class TestRollingPeriodFilter:
    """Test keep_length_days parameter for time-based filtering."""

    def test_discover_all_sessions_when_keep_length_days_is_none(self):
        """Test that None value discovers all sessions (historical sync mode)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            # Create proper directory structure: projects/<project_hash>/sessions/
            projects_dir = claude_dir / "projects"
            project_hash = path_resolver.get_project_hash("/fake/project/path")
            sessions_dir = projects_dir / project_hash / "sessions"
            sessions_dir.mkdir(parents=True)

            # Old session (10 days ago)
            old_session = sessions_dir / "session1.jsonl"
            old_session.write_text('{"message": "old"}\n')
            old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
            os.utime(old_session, (old_time, old_time))

            # Medium session (5 days ago)
            medium_session = sessions_dir / "session2.jsonl"
            medium_session.write_text('{"message": "medium"}\n')
            medium_time = time.time() - (5 * 24 * 60 * 60)  # 5 days ago
            os.utime(medium_session, (medium_time, medium_time))

            # Recent session (1 day ago)
            recent_session = sessions_dir / "session3.jsonl"
            recent_session.write_text('{"message": "recent"}\n')
            recent_time = time.time() - (1 * 24 * 60 * 60)  # 1 day ago
            os.utime(recent_session, (recent_time, recent_time))

            # Create manager with keep_length_days=None (discover all)
            manager = SessionManager(
                path_resolver=path_resolver,
                keep_length_days=None,  # No time filter
            )

            try:
                manager.start()

                # All 3 sessions should be discovered
                assert len(manager.active_sessions) == 3
                session_ids = list(manager.active_sessions.keys())
                assert "session1" in session_ids
                assert "session2" in session_ids
                assert "session3" in session_ids

            finally:
                manager.stop()

    def test_discover_only_recent_sessions_with_keep_length_days(self):
        """Test that keep_length_days filters old sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            # Create proper directory structure: projects/<project_hash>/sessions/
            projects_dir = claude_dir / "projects"
            project_hash = path_resolver.get_project_hash("/fake/project/path")
            sessions_dir = projects_dir / project_hash / "sessions"
            sessions_dir.mkdir(parents=True)

            # Old session (10 days ago) - should be filtered
            old_session = sessions_dir / "session1.jsonl"
            old_session.write_text('{"message": "old"}\n')
            old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
            os.utime(old_session, (old_time, old_time))

            # Medium session (5 days ago) - should be discovered
            medium_session = sessions_dir / "session2.jsonl"
            medium_session.write_text('{"message": "medium"}\n')
            medium_time = time.time() - (5 * 24 * 60 * 60)  # 5 days ago
            os.utime(medium_session, (medium_time, medium_time))

            # Recent session (1 day ago) - should be discovered
            recent_session = sessions_dir / "session3.jsonl"
            recent_session.write_text('{"message": "recent"}\n')
            recent_time = time.time() - (1 * 24 * 60 * 60)  # 1 day ago
            os.utime(recent_session, (recent_time, recent_time))

            # Create manager with keep_length_days=7 (rolling 7-day window)
            manager = SessionManager(
                path_resolver=path_resolver,
                keep_length_days=7,  # Last 7 days only
            )

            try:
                manager.start()

                # Only 2 recent sessions should be discovered (session2, session3)
                assert len(manager.active_sessions) == 2
                session_ids = list(manager.active_sessions.keys())
                assert "session1" not in session_ids  # Filtered (too old)
                assert "session2" in session_ids  # Within 7 days
                assert "session3" in session_ids  # Within 7 days

            finally:
                manager.stop()

    def test_sessions_at_boundary_are_included(self):
        """Test that sessions exactly at the cutoff time are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            # Create proper directory structure: projects/<project_hash>/sessions/
            projects_dir = claude_dir / "projects"
            project_hash = path_resolver.get_project_hash("/fake/project/path")
            sessions_dir = projects_dir / project_hash / "sessions"
            sessions_dir.mkdir(parents=True)

            # Calculate consistent cutoff time to avoid race conditions
            current_time = time.time()
            cutoff = current_time - (7 * 24 * 60 * 60)

            # Session exactly at 7-day boundary (just after cutoff to ensure inclusion)
            boundary_session = sessions_dir / "boundary.jsonl"
            boundary_session.write_text('{"message": "boundary"}\n')
            boundary_time = cutoff + 1  # 1 second after cutoff
            os.utime(boundary_session, (boundary_time, boundary_time))

            # Session before boundary (6.9 days - well within window)
            before_session = sessions_dir / "before.jsonl"
            before_session.write_text('{"message": "before"}\n')
            before_time = current_time - (6.9 * 24 * 60 * 60)
            os.utime(before_session, (before_time, before_time))

            # Session after boundary (7.1 days - should be filtered)
            after_session = sessions_dir / "after.jsonl"
            after_session.write_text('{"message": "after"}\n')
            after_time = cutoff - 1  # 1 second before cutoff
            os.utime(after_session, (after_time, after_time))

            manager = SessionManager(
                path_resolver=path_resolver,
                keep_length_days=7,
            )

            try:
                manager.start()

                session_ids = list(manager.active_sessions.keys())

                # Boundary and before should be included
                assert "boundary" in session_ids  # At boundary
                assert "before" in session_ids  # Before boundary

                # After should be filtered
                assert "after" not in session_ids  # After boundary (too old)

            finally:
                manager.stop()

    def test_default_keep_length_days_is_seven(self):
        """Test that default keep_length_days is 7 days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            # Create manager without specifying keep_length_days
            manager = SessionManager(
                path_resolver=path_resolver,
                # keep_length_days not specified, should default to 7
            )

            # Verify default is 7
            assert manager.keep_length_days == 7

    def test_discovery_logging(self, caplog):
        """Test that discovery logs filter statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            # Create proper directory structure: projects/<project_hash>/sessions/
            projects_dir = claude_dir / "projects"
            project_hash = path_resolver.get_project_hash("/fake/project/path")
            sessions_dir = projects_dir / project_hash / "sessions"
            sessions_dir.mkdir(parents=True)

            # Create old and new sessions
            old_session = sessions_dir / "old.jsonl"
            old_session.write_text('{"message": "old"}\n')
            old_time = time.time() - (10 * 24 * 60 * 60)
            os.utime(old_session, (old_time, old_time))

            recent_session = sessions_dir / "recent.jsonl"
            recent_session.write_text('{"message": "recent"}\n')

            manager = SessionManager(
                path_resolver=path_resolver,
                keep_length_days=7,
            )

            try:
                with caplog.at_level("INFO"):
                    manager.start()

                # Check that log mentions filtering
                assert any("Discovered" in record.message and "filtered" in record.message for record in caplog.records)

            finally:
                manager.stop()

    def test_file_modification_time_used_for_filtering(self):
        """Test that file modification time (not creation time) is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            # Create proper directory structure: projects/<project_hash>/sessions/
            projects_dir = claude_dir / "projects"
            project_hash = path_resolver.get_project_hash("/fake/project/path")
            sessions_dir = projects_dir / project_hash / "sessions"
            sessions_dir.mkdir(parents=True)

            # Create file with old modification time
            session = sessions_dir / "session.jsonl"
            session.write_text('{"message": "test"}\n')
            old_time = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
            os.utime(session, (old_time, old_time))  # Set both access and modification time

            manager = SessionManager(
                path_resolver=path_resolver,
                keep_length_days=7,
            )

            try:
                manager.start()

                # Session should be filtered based on modification time
                assert len(manager.active_sessions) == 0

            finally:
                manager.stop()
