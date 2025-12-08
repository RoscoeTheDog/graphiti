"""Tests for session tracking MCP tools.

This module tests the session tracking MCP tools:
- session_tracking_status()
- session_tracking_sync_history()

NOTE: session_tracking_start() and session_tracking_stop() were removed in Story R2.
Session tracking is now controlled via configuration (graphiti.config.json -> session_tracking.enabled).
MCP tools are read-only for monitoring/diagnostics only.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the MCP server module
# Note: This will import the module-level globals
import mcp_server.graphiti_mcp_server as mcp_server


class TestSessionTrackingStatus:
    """Tests for session_tracking_status() MCP tool."""

    @pytest.mark.asyncio
    async def test_status_without_session_id(self):
        """Test getting global status without session_id."""
        # Mock session manager
        mock_manager = Mock()
        mock_manager._is_running = True
        mock_manager.get_active_session_count.return_value = 3
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = mock_manager

        # Mock global config
        original_config = mcp_server.unified_config
        mock_config = Mock()
        mock_config.session_tracking.enabled = True
        mock_config.session_tracking.watch_path = "/test/path"
        mock_config.session_tracking.inactivity_timeout = 300
        mock_config.session_tracking.check_interval = 60
        mock_config.session_tracking.filter = Mock()
        mock_config.session_tracking.filter.tool_calls.value = "SUMMARY"
        mock_config.session_tracking.filter.tool_content.value = "SUMMARY"
        mock_config.session_tracking.filter.user_messages.value = "FULL"
        mock_config.session_tracking.filter.agent_messages.value = "FULL"
        mcp_server.unified_config = mock_config

        try:
            result = await mcp_server.session_tracking_status()
            result_dict = json.loads(result)

            assert result_dict["status"] == "success"
            assert result_dict["enabled"] is True
            assert result_dict["global_config"]["enabled"] is True
            assert result_dict["global_config"]["watch_path"] == "/test/path"
            assert result_dict["global_config"]["inactivity_timeout"] == 300
            assert result_dict["global_config"]["check_interval"] == 60
            assert result_dict["session_manager"]["running"] is True
            assert result_dict["session_manager"]["active_sessions"] == 3
            assert result_dict["filter_config"]["tool_calls"] == "SUMMARY"
            assert result_dict["filter_config"]["user_messages"] == "FULL"
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config

    @pytest.mark.asyncio
    async def test_status_without_session_manager(self):
        """Test getting status when session manager is not initialized."""
        # Temporarily set session_manager to None
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = None

        # Mock global config
        original_config = mcp_server.unified_config
        mock_config = Mock()
        mock_config.session_tracking.enabled = False
        mock_config.session_tracking.watch_path = None
        mock_config.session_tracking.inactivity_timeout = 300
        mock_config.session_tracking.check_interval = 60
        mock_config.session_tracking.filter = None
        mcp_server.unified_config = mock_config

        try:
            result = await mcp_server.session_tracking_status()
            result_dict = json.loads(result)

            assert result_dict["status"] == "success"
            assert result_dict["enabled"] is False
            assert result_dict["session_manager"]["running"] is False
            assert result_dict["session_manager"]["active_sessions"] == 0
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config

    @pytest.mark.asyncio
    async def test_status_response_format(self):
        """Test that status response has correct JSON structure."""
        # Mock session manager
        mock_manager = Mock()
        mock_manager._is_running = False
        mock_manager.get_active_session_count.return_value = 0
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = mock_manager

        # Mock global config
        original_config = mcp_server.unified_config
        mock_config = Mock()
        mock_config.session_tracking.enabled = False
        mock_config.session_tracking.watch_path = None
        mock_config.session_tracking.inactivity_timeout = 300
        mock_config.session_tracking.check_interval = 60
        mock_config.session_tracking.filter = None
        mcp_server.unified_config = mock_config

        try:
            result = await mcp_server.session_tracking_status()
            result_dict = json.loads(result)

            # Verify all required keys are present
            assert "status" in result_dict
            assert "session_id" in result_dict
            assert "enabled" in result_dict
            assert "global_config" in result_dict
            assert "session_manager" in result_dict
            assert "filter_config" in result_dict

            # Verify nested structures
            assert "enabled" in result_dict["global_config"]
            assert "watch_path" in result_dict["global_config"]
            assert "inactivity_timeout" in result_dict["global_config"]
            assert "check_interval" in result_dict["global_config"]

            assert "running" in result_dict["session_manager"]
            assert "active_sessions" in result_dict["session_manager"]

            assert "tool_calls" in result_dict["filter_config"]
            assert "tool_content" in result_dict["filter_config"]
            assert "user_messages" in result_dict["filter_config"]
            assert "agent_messages" in result_dict["filter_config"]
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config

    @pytest.mark.asyncio
    async def test_status_config_only_control(self):
        """Test that status reflects config-only control (no runtime overrides)."""
        # Mock session manager
        mock_manager = Mock()
        mock_manager._is_running = True
        mock_manager.get_active_session_count.return_value = 1
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = mock_manager

        # Mock global config (enabled)
        original_config = mcp_server.unified_config
        mock_config = Mock()
        mock_config.session_tracking.enabled = True
        mock_config.session_tracking.watch_path = None
        mock_config.session_tracking.inactivity_timeout = 300
        mock_config.session_tracking.check_interval = 60
        mock_config.session_tracking.filter = Mock()
        mock_config.session_tracking.filter.tool_calls.value = "SUMMARY"
        mock_config.session_tracking.filter.tool_content.value = "SUMMARY"
        mock_config.session_tracking.filter.user_messages.value = "FULL"
        mock_config.session_tracking.filter.agent_messages.value = "FULL"
        mcp_server.unified_config = mock_config

        try:
            # Get status for a specific session
            result = await mcp_server.session_tracking_status(session_id="test-session")
            result_dict = json.loads(result)

            assert result_dict["status"] == "success"
            assert result_dict["session_id"] == "test-session"
            # Enabled should match config (no runtime override possible)
            assert result_dict["enabled"] is True
            assert result_dict["global_config"]["enabled"] is True
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config


class TestSessionTrackingSyncHistory:
    """Tests for session_tracking_sync_history() MCP tool wrapper."""

    @pytest.mark.asyncio
    async def test_sync_history_not_initialized(self):
        """Test sync_history returns error when session_manager is None."""
        # Store original values
        original_manager = mcp_server.session_manager
        original_client = mcp_server.graphiti_client
        mcp_server.session_manager = None
        mcp_server.graphiti_client = Mock()

        try:
            result = await mcp_server.session_tracking_sync_history()
            result_dict = json.loads(result)

            assert result_dict["status"] == "error"
            assert "not initialized" in result_dict["error"].lower()
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.graphiti_client = original_client

    @pytest.mark.asyncio
    async def test_sync_history_dry_run_default(self):
        """Test sync_history defaults to dry_run=True."""
        # Mock session manager with minimal setup
        mock_manager = Mock()
        mock_manager.path_resolver = Mock()
        mock_manager.path_resolver.list_all_projects.return_value = {}

        original_manager = mcp_server.session_manager
        original_client = mcp_server.graphiti_client
        original_config = mcp_server.unified_config

        mcp_server.session_manager = mock_manager
        mcp_server.graphiti_client = Mock()

        mock_config = Mock()
        mock_config.session_tracking.filter = None
        mcp_server.unified_config = mock_config

        try:
            result = await mcp_server.session_tracking_sync_history()
            result_dict = json.loads(result)

            assert result_dict["status"] == "success"
            assert result_dict["dry_run"] is True
            assert result_dict["sessions_found"] == 0  # No sessions in empty mock
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.graphiti_client = original_client
            mcp_server.unified_config = original_config

    @pytest.mark.asyncio
    async def test_sync_history_parameters_passed(self):
        """Test sync_history passes parameters correctly to underlying function.

        Note: dry_run parameter was removed from MCP tool signature in Story R3.
        The MCP tool is now read-only (always dry_run=True internally).
        """
        mock_manager = Mock()
        mock_manager.path_resolver = Mock()
        mock_manager.path_resolver.list_all_projects.return_value = {}

        original_manager = mcp_server.session_manager
        original_client = mcp_server.graphiti_client
        original_config = mcp_server.unified_config

        mcp_server.session_manager = mock_manager
        mcp_server.graphiti_client = Mock()

        mock_config = Mock()
        mock_config.session_tracking.filter = None
        mcp_server.unified_config = mock_config

        try:
            # Test with custom parameters (dry_run removed - MCP tool is read-only)
            result = await mcp_server.session_tracking_sync_history(
                project="/test/path",
                days=30,
                max_sessions=50,
            )
            result_dict = json.loads(result)

            # Should succeed with dry_run=True (always read-only)
            assert result_dict["status"] == "success"
            assert result_dict["dry_run"] is True
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.graphiti_client = original_client
            mcp_server.unified_config = original_config

    @pytest.mark.asyncio
    async def test_sync_history_always_read_only(self):
        """Test that MCP tool is always read-only (Story R3 requirement).

        The MCP tool no longer exposes dry_run parameter. It always operates
        in read-only mode (dry_run=True internally). Actual sync requires CLI.
        """
        mock_manager = Mock()
        mock_manager.path_resolver = Mock()
        mock_manager.path_resolver.list_all_projects.return_value = {}

        original_manager = mcp_server.session_manager
        original_client = mcp_server.graphiti_client
        original_config = mcp_server.unified_config

        mcp_server.session_manager = mock_manager
        mcp_server.graphiti_client = Mock()

        mock_config = Mock()
        mock_config.session_tracking.filter = None
        mcp_server.unified_config = mock_config

        try:
            # Call MCP tool without any parameters
            result = await mcp_server.session_tracking_sync_history()
            result_dict = json.loads(result)

            # Verify it's always dry_run=True
            assert result_dict["dry_run"] is True
            # In dry_run mode, response has sessions_found (not sessions_indexed)
            assert "sessions_found" in result_dict
            # sessions_indexed should NOT be present in dry_run mode
            assert "sessions_indexed" not in result_dict

            # Call with all available parameters - still should be read-only
            result2 = await mcp_server.session_tracking_sync_history(
                project="/some/project",
                days=1,
                max_sessions=10,
            )
            result_dict2 = json.loads(result2)

            # Still read-only
            assert result_dict2["dry_run"] is True
            assert "sessions_indexed" not in result_dict2
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.graphiti_client = original_client
            mcp_server.unified_config = original_config

    @pytest.mark.asyncio
    async def test_sync_history_no_dry_run_parameter(self):
        """Test that MCP tool signature does not accept dry_run parameter.

        Story R3 removed dry_run from the MCP tool to prevent AI assistants
        from triggering actual indexing. Only CLI can perform actual sync.
        """
        import inspect

        # Get the MCP tool function signature
        sig = inspect.signature(mcp_server.session_tracking_sync_history)
        param_names = list(sig.parameters.keys())

        # Verify dry_run is NOT in the parameters
        assert "dry_run" not in param_names, (
            "dry_run parameter should not be exposed in MCP tool. "
            "MCP tool should be read-only (Story R3)."
        )

        # Verify expected parameters are present
        assert "project" in param_names
        assert "days" in param_names
        assert "max_sessions" in param_names
