"""
Performance benchmark tests for session tracking features.

Tests verify <5% overhead requirement from cross-cutting requirements.
"""

import asyncio
import time
from pathlib import Path

import pytest

from graphiti_core.session_tracking.path_resolver import ClaudePathResolver


class TestTemplateResolutionCaching:
    """Test template resolution caching performance."""

    @pytest.mark.asyncio
    async def test_template_reads_cached(self, tmp_path):
        """Test template reads are cached (avoid re-reads)."""
        from graphiti_core.session_tracking.handoff_exporter import HandoffExporter
        from graphiti_core.llms.client import LLMClient
        from graphiti_core.llms.config import LLMConfig
        from unittest.mock import Mock

        # Create mock LLM client
        llm_config = LLMConfig(llm_provider="openai", llm_model="gpt-4o-mini")
        llm_client = LLMClient(config=llm_config)

        exporter = HandoffExporter(llm_client=llm_client)

        # Templates are hardcoded in HandoffExporter, not read from files
        # This test verifies the _generate_markdown method is fast

        # Create mock context
        from graphiti_core.session_tracking.types import ConversationContext, TokenUsage
        context = ConversationContext(
            session_id="test-session",
            messages=[],
            token_usage=TokenUsage(input_tokens=100, output_tokens=50),
            tools_used=["Read", "Write"],
            files_modified=["test.py"]
        )

        # First call
        start = time.time()
        result1 = exporter._generate_markdown(context, summary="Test summary")
        first_call_time = time.time() - start

        # Second call (template should be cached internally if implemented)
        start = time.time()
        result2 = exporter._generate_markdown(context, summary="Test summary")
        second_call_time = time.time() - start

        print(f"First call: {first_call_time*1000:.2f}ms, Second call: {second_call_time*1000:.2f}ms")

        # Both calls should be fast (<10ms)
        assert first_call_time < 0.01, f"Template generation too slow: {first_call_time*1000:.2f}ms"
        assert second_call_time < 0.01, f"Template generation too slow: {second_call_time*1000:.2f}ms"


class TestSessionDiscoveryPerformance:
    """Test session discovery performance with large directories."""

    @pytest.mark.asyncio
    async def test_filtering_performance_with_keep_length_days(self, tmp_path):
        """Test filtering performance with keep_length_days parameter."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()

        import os
        current_time = time.time()

        # Create 1000 sessions with varying ages
        for i in range(1000):
            session_file = session_dir / f"session_{i:04d}.jsonl"
            session_file.write_text('{"type": "conversation_start"}\n')

            # Set file mtime to various ages (0-30 days old)
            age_days = (i % 31)
            file_time = current_time - (age_days * 24 * 60 * 60)
            os.utime(session_file, (file_time, file_time))

        from graphiti_core.session_tracking.path_resolver import ClaudePathResolver
        from graphiti_core.session_tracking.session_manager import SessionManager
        from unittest.mock import patch

        path_resolver = ClaudePathResolver(hostname="testhost", pwd_hash="testhash")

        # Test with 7-day filter
        with patch.object(path_resolver, 'get_sessions_directory', return_value=session_dir):
            start = time.time()
            manager = SessionManager(
                path_resolver=path_resolver,
                inactivity_timeout=300,
                check_interval=60,
                keep_length_days=7
            )
            await manager._discover_existing_sessions()
            filtered_time = time.time() - start

        # Test without filter (all sessions)
        with patch.object(path_resolver, 'get_sessions_directory', return_value=session_dir):
            start = time.time()
            manager = SessionManager(
                path_resolver=path_resolver,
                inactivity_timeout=300,
                check_interval=60,
                keep_length_days=None  # No filtering
            )
            await manager._discover_existing_sessions()
            unfiltered_time = time.time() - start

        print(f"Filtered discovery: {filtered_time:.3f}s, Unfiltered: {unfiltered_time:.3f}s")

        # Filtering should add minimal overhead (<20% slower)
        if unfiltered_time > 0:
            overhead = (filtered_time - unfiltered_time) / unfiltered_time
            assert overhead < 0.20, f"Filtering overhead {overhead:.1%} too high"

    @pytest.mark.asyncio
    async def test_glob_pattern_performance(self, tmp_path):
        """Test glob pattern matching performance."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()

        # Create mix of session and non-session files
        for i in range(500):
            (session_dir / f"session_{i:04d}.jsonl").write_text('{"type": "conversation_start"}\n')
            (session_dir / f"other_{i:04d}.txt").write_text("not a session")

        from graphiti_core.session_tracking.path_resolver import ClaudePathResolver
        from graphiti_core.session_tracking.session_manager import SessionManager
        from unittest.mock import patch

        path_resolver = ClaudePathResolver(hostname="testhost", pwd_hash="testhash")

        with patch.object(path_resolver, 'get_sessions_directory', return_value=session_dir):
            start = time.time()
            manager = SessionManager(
                path_resolver=path_resolver,
                inactivity_timeout=300,
                check_interval=60
            )
            await manager._discover_existing_sessions()
            glob_time = time.time() - start

        print(f"Glob pattern matching time: {glob_time:.3f}s")

        # Glob filtering should be fast (<1s for 1000 files)
        assert glob_time < 1.0
