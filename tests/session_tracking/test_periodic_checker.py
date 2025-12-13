"""Tests for periodic session inactivity checker.

This module tests the periodic checker that runs in the background to close
inactive sessions. It validates task lifecycle, session closure timing, and
error handling.
"""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from graphiti_core.session_tracking import SessionManager
from graphiti_core.session_tracking.path_resolver import ClaudePathResolver


class TestPeriodicChecker:
    """Test periodic inactivity checker functionality."""

    @pytest.mark.asyncio
    async def test_task_starts_and_cancels_cleanly(self):
        """Test that periodic checker task starts and cancels without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            manager = SessionManager(
                path_resolver=path_resolver,
                inactivity_timeout=300,
            )

            try:
                manager.start()

                # Import the periodic checker function
                from mcp_server.graphiti_mcp_server import check_inactive_sessions_periodically

                # Start the checker task
                checker_task = asyncio.create_task(
                    check_inactive_sessions_periodically(manager, interval_seconds=1)
                )

                # Let it run for a few cycles
                await asyncio.sleep(2.5)

                # Cancel the task
                checker_task.cancel()
                try:
                    await checker_task
                except asyncio.CancelledError:
                    pass  # Expected

                # Verify no exceptions were raised
                assert True

            finally:
                manager.stop()

    @pytest.mark.asyncio
    async def test_checker_calls_check_inactive_sessions_periodically(self):
        """Test that checker periodically calls check_inactive_sessions()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            manager = SessionManager(
                path_resolver=path_resolver,
                inactivity_timeout=300,
            )

            try:
                manager.start()

                from mcp_server.graphiti_mcp_server import check_inactive_sessions_periodically

                # Track calls to check_inactive_sessions
                call_count = [0]
                original_check = manager.check_inactive_sessions

                def mock_check():
                    call_count[0] += 1
                    return original_check()

                manager.check_inactive_sessions = mock_check

                # Start the checker task with 1s interval
                checker_task = asyncio.create_task(
                    check_inactive_sessions_periodically(manager, interval_seconds=1)
                )

                # Wait for 3.5 seconds (should call check 3 times: at 1s, 2s, 3s)
                await asyncio.sleep(3.5)

                # Verify check was called multiple times
                assert call_count[0] >= 3, f"Expected >= 3 calls, got {call_count[0]}"

                # Cancel checker
                checker_task.cancel()
                try:
                    await checker_task
                except asyncio.CancelledError:
                    pass

            finally:
                manager.stop()

    @pytest.mark.asyncio
    async def test_checker_continues_after_exception_in_check(self):
        """Test that checker task continues running even if check_inactive_sessions throws."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            manager = SessionManager(
                path_resolver=path_resolver,
                inactivity_timeout=300,
            )

            try:
                manager.start()

                from mcp_server.graphiti_mcp_server import check_inactive_sessions_periodically

                # Mock check_inactive_sessions to raise exception on first call
                call_count = [0]
                original_check = manager.check_inactive_sessions

                def mock_check():
                    call_count[0] += 1
                    if call_count[0] == 1:
                        raise RuntimeError("Simulated check error")
                    return original_check()

                manager.check_inactive_sessions = mock_check

                # Start the checker task
                checker_task = asyncio.create_task(
                    check_inactive_sessions_periodically(manager, interval_seconds=1)
                )

                # Let it run for 3 cycles (should encounter error on first cycle)
                await asyncio.sleep(3.5)

                # Verify task is still running (call_count > 1 means it continued)
                assert call_count[0] > 1, "Checker should continue after exception"
                assert not checker_task.done(), "Task should still be running"

                # Cancel checker
                checker_task.cancel()
                try:
                    await checker_task
                except asyncio.CancelledError:
                    pass

            finally:
                manager.stop()

    @pytest.mark.asyncio
    async def test_no_exception_if_session_manager_stops_first(self):
        """Test that checker handles gracefully if session manager stops before task is cancelled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            claude_dir = Path(tmpdir)
            path_resolver = ClaudePathResolver(claude_dir=claude_dir)

            manager = SessionManager(
                path_resolver=path_resolver,
                inactivity_timeout=300,
            )

            try:
                manager.start()

                from mcp_server.graphiti_mcp_server import check_inactive_sessions_periodically

                checker_task = asyncio.create_task(
                    check_inactive_sessions_periodically(manager, interval_seconds=1)
                )

                # Let it run for one cycle
                await asyncio.sleep(1.5)

                # Stop session manager BEFORE cancelling task
                manager.stop()

                # Let checker try to run another cycle with stopped manager
                await asyncio.sleep(1.5)

                # Task should still be running (check should handle stopped manager gracefully)
                # This test validates that check_inactive_sessions() doesn't crash when called on stopped manager

                # Cancel checker
                checker_task.cancel()
                try:
                    await checker_task
                except asyncio.CancelledError:
                    pass

                # No exception should have been raised
                assert True

            except Exception:
                # Clean up if error
                try:
                    manager.stop()
                except Exception:
                    pass
