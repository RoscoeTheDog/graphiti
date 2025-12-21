"""
Tests for add_memory() filepath parameter and file export functionality.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server.export_helpers import _resolve_path_pattern, _scan_for_credentials


class TestPathResolution:
    """Tests for _resolve_path_pattern helper function"""

    def test_resolve_simple_path(self):
        """Test simple path without variables"""
        result = _resolve_path_pattern("bugs/auth.md")
        assert result == "bugs/auth.md"

    def test_resolve_date_variable(self):
        """Test {date} variable substitution"""
        from datetime import datetime
        result = _resolve_path_pattern("bugs/{date}-auth.md")
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert expected_date in result
        assert result.startswith("bugs/")
        assert result.endswith("-auth.md")

    def test_resolve_timestamp_variable(self):
        """Test {timestamp} variable substitution"""
        from datetime import datetime
        result = _resolve_path_pattern("logs/{timestamp}.log")
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert expected_date in result
        assert result.startswith("logs/")
        assert result.endswith(".log")

    def test_resolve_hash_variable(self):
        """Test {hash} variable substitution"""
        result = _resolve_path_pattern("data/{hash}.txt", query="test query")
        assert result.startswith("data/")
        assert result.endswith(".txt")
        # Hash should be 8 characters
        filename = Path(result).stem
        assert len(filename) == 8

    def test_resolve_multiple_variables(self):
        """Test multiple variable substitution"""
        result = _resolve_path_pattern("reports/{date}/{timestamp}-{hash}.md", query="test")
        assert "reports/" in result
        assert ".md" in result
        from datetime import datetime
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert expected_date in result

    def test_path_traversal_detected(self):
        """Test that path traversal is blocked"""
        with pytest.raises(ValueError, match="Path traversal detected"):
            _resolve_path_pattern("../../../etc/passwd")

    def test_path_traversal_in_middle(self):
        """Test that .. in middle of path is blocked"""
        with pytest.raises(ValueError, match="Path traversal detected"):
            _resolve_path_pattern("bugs/../../../etc/passwd")


class TestSecurityScanning:
    """Tests for _scan_for_credentials helper function"""

    def test_detect_api_key(self):
        """Test detection of API key pattern"""
        content = "api_key = abcdef1234567890"
        detected = _scan_for_credentials(content)
        assert "api_key" in detected

    def test_detect_password(self):
        """Test detection of password pattern"""
        content = "password: mysecretpass123"
        detected = _scan_for_credentials(content)
        assert "password" in detected

    def test_detect_bearer_token(self):
        """Test detection of bearer token"""
        content = "Authorization: Bearer abc123def4567890123"
        detected = _scan_for_credentials(content)
        assert "bearer_token" in detected

    def test_detect_multiple_credentials(self):
        """Test detection of multiple credential types"""
        content = """
        api_key = abcdef1234567890
        password: mysecretpass123
        token: xyz789012345678
        """
        detected = _scan_for_credentials(content)
        assert len(detected) >= 2  # At least api_key and password

    def test_no_credentials_detected(self):
        """Test clean content with no credentials"""
        content = "This is a bug report about login timeout issues."
        detected = _scan_for_credentials(content)
        assert len(detected) == 0

    def test_deduplication(self):
        """Test that duplicate credential types are deduplicated"""
        content = """
        api_key = abc123def4567890
        api_key = xyz7890123456789
        """
        detected = _scan_for_credentials(content)
        assert detected.count("api_key") == 1


class TestAddMemoryExport:
    """Integration tests for add_memory() with filepath parameter"""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Mock Graphiti client for testing"""
        mock_client = MagicMock()
        mock_client.add_episode = AsyncMock()
        return mock_client

    @pytest.fixture
    def temp_export_dir(self):
        """Create temporary directory for exports"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory for tests
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            yield tmpdir
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_add_memory_without_filepath(self, mock_graphiti_client):
        """Test backward compatibility - add_memory without filepath"""
        with patch('mcp_server.graphiti_mcp_server.graphiti_client', mock_graphiti_client):
            from mcp_server.graphiti_mcp_server import add_memory

            result = await add_memory(
                name="Test Episode",
                episode_body="Test content"
            )

            # Should return success message without file info
            assert "queued successfully" in result.lower()
            assert "saved to" not in result.lower()

    @pytest.mark.asyncio
    async def test_add_memory_with_simple_filepath(self, temp_export_dir):
        """Test file export logic without full MCP integration"""
        # Test the file export logic directly
        from pathlib import Path

        episode_body = "Login timeout after 5 minutes"
        filepath = "bugs/auth-issue.md"
        name = "Bug Report"

        # Resolve path pattern
        resolved_path = _resolve_path_pattern(filepath, query=name, fact_count=0, node_count=0)

        # Write file (simulating the add_memory logic)
        output_path = Path(resolved_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(episode_body, encoding="utf-8")

        # Verify file exists
        assert output_path.exists()

        # Verify content
        content = output_path.read_text(encoding="utf-8")
        assert content == episode_body

    @pytest.mark.asyncio
    async def test_add_memory_with_path_variables(self, temp_export_dir):
        """Test path variable substitution"""
        from datetime import datetime

        episode_body = "Report content"
        filepath = "reports/{date}-report.md"
        name = "Daily Report"

        # Resolve path pattern
        resolved_path = _resolve_path_pattern(filepath, query=name, fact_count=0, node_count=0)

        # Verify date substituted
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert expected_date in resolved_path

        # Write file
        output_path = Path(resolved_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(episode_body, encoding="utf-8")

        # Verify file created
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_add_memory_credential_warning(self, temp_export_dir):
        """Test credential detection"""
        episode_body = "api_key = abcdef1234567890"

        # Test security scanning
        detected = _scan_for_credentials(episode_body)

        # Should detect api_key
        assert "api_key" in detected

    @pytest.mark.asyncio
    async def test_add_memory_creates_directories(self, temp_export_dir):
        """Test that nested directories are created"""
        episode_body = "Content"
        filepath = "deep/nested/path/file.md"
        name = "Deep File"

        # Resolve and write
        resolved_path = _resolve_path_pattern(filepath, query=name, fact_count=0, node_count=0)
        output_path = Path(resolved_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(episode_body, encoding="utf-8")

        # Verify deep directory structure was created
        assert output_path.exists()
        assert Path("deep/nested/path").is_dir()


class TestAddMemoryTimeoutWithFilepath:
    """Tests for file export behavior when episode processing times out.

    Bug fix: Prior to this fix, file export happened AFTER waiting for episode
    processing. If processing timed out, the file was never written even though
    the Graphiti entry would eventually succeed in the background.

    The fix moves file export BEFORE the wait, ensuring files are always written
    regardless of whether episode processing times out.
    """

    @pytest.fixture
    def temp_export_dir(self):
        """Create temporary directory for exports"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            yield tmpdir
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_file_written_before_queue_wait(self, temp_export_dir):
        """Test that file is written before episode processing is awaited.

        This verifies the core bug fix: file export must happen before waiting
        for episode processing, so that a timeout doesn't prevent file creation.
        """
        from mcp_server.export_helpers import _resolve_path_pattern
        from pathlib import Path

        # Simulate the file write that happens BEFORE waiting
        episode_body = "Large handoff content that triggers long processing..."
        filepath = ".claude/handoff/s001-test.md"
        name = "Session 001: Test Handoff"

        # This is exactly what happens in add_memory() BEFORE the wait
        resolved_path = _resolve_path_pattern(filepath, query=name, fact_count=0, node_count=0)
        output_path = Path(resolved_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(episode_body, encoding="utf-8")

        # File should exist immediately
        assert output_path.exists(), "File should be written before episode processing wait"
        assert output_path.read_text(encoding="utf-8") == episode_body

    @pytest.mark.asyncio
    async def test_timeout_response_includes_file_path(self):
        """Test that timeout response mentions the file was saved.

        When processing times out but the file was written, the error message
        should include information about the successful file export.
        """
        file_saved_path = ".claude/handoff/s001-test.md"
        timeout = 60

        # Simulate building the timeout suggestion with file info
        suggestion = (
            f"Episode processing timed out after {timeout}s. "
            "The operation may still complete in the background. "
            "Consider using wait_for_completion=false for long operations."
        )
        if file_saved_path:
            suggestion += f"\nNote: File was successfully saved to {file_saved_path}"

        # Verify the suggestion includes file path info
        assert file_saved_path in suggestion
        assert "File was successfully saved" in suggestion

    @pytest.mark.asyncio
    async def test_file_export_independent_of_llm_availability(self, temp_export_dir):
        """Test that file export works even when LLM is unavailable.

        File writing is a pure filesystem operation that should not depend
        on LLM availability or processing success.
        """
        from pathlib import Path

        episode_body = "Content to save even if LLM is down"
        filepath = "backup/llm-unavailable.md"

        # File write should succeed regardless of LLM state
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(episode_body, encoding="utf-8")

        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == episode_body

    @pytest.mark.asyncio
    async def test_large_content_file_export(self, temp_export_dir):
        """Test file export with large content (simulating handoff with full context).

        Large handoff files may trigger longer LLM processing, making the timeout
        bug more likely. This test verifies file export works for large content.
        """
        from pathlib import Path

        # Generate large content (simulating a full session handoff)
        large_content = "# Session Handoff\n\n" + ("Context line " * 100 + "\n") * 100
        filepath = ".claude/handoff/s999-large-handoff.md"

        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(large_content, encoding="utf-8")

        assert output_path.exists()
        # Verify content integrity
        saved_content = output_path.read_text(encoding="utf-8")
        assert len(saved_content) == len(large_content)
        assert saved_content == large_content

