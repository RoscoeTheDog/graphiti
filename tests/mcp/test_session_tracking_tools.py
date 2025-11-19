"""Tests for session tracking MCP tools.

This module tests the three session tracking MCP tools:
- session_tracking_start()
- session_tracking_stop()
- session_tracking_status()
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the MCP server module
# Note: This will import the module-level globals
import mcp_server.graphiti_mcp_server as mcp_server


class TestSessionTrackingStart:
    """Tests for session_tracking_start() MCP tool."""

    @pytest.mark.asyncio
    async def test_start_without_session_manager(self):
        """Test starting session tracking when session manager is not initialized."""
        # Temporarily set session_manager to None
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = None

        try:
            result = await mcp_server.session_tracking_start()
            result_dict = json.loads(result)

            assert result_dict["status"] == "error"
            assert "not initialized" in result_dict["message"].lower()
            assert result_dict["enabled"] is False
        finally:
            mcp_server.session_manager = original_manager

    @pytest.mark.asyncio
    async def test_start_with_global_enabled(self):
        """Test starting session tracking when globally enabled."""
        # Mock session manager
        mock_manager = Mock()
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = mock_manager

        # Mock global config
        original_config = mcp_server.unified_config
        mock_config = Mock()
        mock_config.session_tracking.enabled = True
        mcp_server.unified_config = mock_config

        try:
            result = await mcp_server.session_tracking_start(session_id="test-session")
            result_dict = json.loads(result)

            assert result_dict["status"] == "success"
            assert result_dict["enabled"] is True
            assert result_dict["session_id"] == "test-session"
            assert result_dict["forced"] is False
            assert result_dict["global_config"] is True

            # Check runtime state
            assert mcp_server.runtime_session_tracking_state["test-session"] is True
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config
            mcp_server.runtime_session_tracking_state.clear()

    @pytest.mark.asyncio
    async def test_start_with_global_disabled_without_force(self):
        """Test starting session tracking when globally disabled without force."""
        # Mock session manager
        mock_manager = Mock()
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = mock_manager

        # Mock global config
        original_config = mcp_server.unified_config
        mock_config = Mock()
        mock_config.session_tracking.enabled = False
        mcp_server.unified_config = mock_config

        try:
            result = await mcp_server.session_tracking_start(session_id="test-session", force=False)
            result_dict = json.loads(result)

            assert result_dict["status"] == "disabled"
            assert "globally disabled" in result_dict["message"].lower()
            assert result_dict["enabled"] is False
            assert result_dict["global_config"] is False
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config
            mcp_server.runtime_session_tracking_state.clear()

    @pytest.mark.asyncio
    async def test_start_with_force_override(self):
        """Test starting session tracking with force=True overrides global config."""
        # Mock session manager
        mock_manager = Mock()
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = mock_manager

        # Mock global config (disabled)
        original_config = mcp_server.unified_config
        mock_config = Mock()
        mock_config.session_tracking.enabled = False
        mcp_server.unified_config = mock_config

        try:
            result = await mcp_server.session_tracking_start(session_id="test-session", force=True)
            result_dict = json.loads(result)

            assert result_dict["status"] == "success"
            assert result_dict["enabled"] is True
            assert result_dict["forced"] is True
            assert result_dict["global_config"] is False

            # Check runtime state
            assert mcp_server.runtime_session_tracking_state["test-session"] is True
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config
            mcp_server.runtime_session_tracking_state.clear()

    @pytest.mark.asyncio
    async def test_start_without_session_id(self):
        """Test starting session tracking without providing session_id."""
        # Mock session manager
        mock_manager = Mock()
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = mock_manager

        # Mock global config
        original_config = mcp_server.unified_config
        mock_config = Mock()
        mock_config.session_tracking.enabled = True
        mcp_server.unified_config = mock_config

        try:
            result = await mcp_server.session_tracking_start()
            result_dict = json.loads(result)

            assert result_dict["status"] == "success"
            assert result_dict["session_id"] == "current"
            assert result_dict["enabled"] is True

            # Check runtime state
            assert mcp_server.runtime_session_tracking_state["current"] is True
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config
            mcp_server.runtime_session_tracking_state.clear()


class TestSessionTrackingStop:
    """Tests for session_tracking_stop() MCP tool."""

    @pytest.mark.asyncio
    async def test_stop_with_session_id(self):
        """Test stopping session tracking for a specific session."""
        result = await mcp_server.session_tracking_stop(session_id="test-session")
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        assert result_dict["session_id"] == "test-session"
        assert result_dict["enabled"] is False

        # Check runtime state
        assert mcp_server.runtime_session_tracking_state["test-session"] is False

        # Cleanup
        mcp_server.runtime_session_tracking_state.clear()

    @pytest.mark.asyncio
    async def test_stop_without_session_id(self):
        """Test stopping session tracking without providing session_id."""
        result = await mcp_server.session_tracking_stop()
        result_dict = json.loads(result)

        assert result_dict["status"] == "success"
        assert result_dict["session_id"] == "current"
        assert result_dict["enabled"] is False

        # Check runtime state
        assert mcp_server.runtime_session_tracking_state["current"] is False

        # Cleanup
        mcp_server.runtime_session_tracking_state.clear()

    @pytest.mark.asyncio
    async def test_stop_multiple_sessions(self):
        """Test stopping tracking for multiple sessions independently."""
        # Stop first session
        result1 = await mcp_server.session_tracking_stop(session_id="session-1")
        result1_dict = json.loads(result1)

        # Stop second session
        result2 = await mcp_server.session_tracking_stop(session_id="session-2")
        result2_dict = json.loads(result2)

        assert result1_dict["status"] == "success"
        assert result2_dict["status"] == "success"

        # Check runtime state
        assert mcp_server.runtime_session_tracking_state["session-1"] is False
        assert mcp_server.runtime_session_tracking_state["session-2"] is False

        # Cleanup
        mcp_server.runtime_session_tracking_state.clear()


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
    async def test_status_with_runtime_override(self):
        """Test getting status with runtime override applied."""
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

        # Set runtime override (disabled)
        mcp_server.runtime_session_tracking_state["test-session"] = False

        try:
            result = await mcp_server.session_tracking_status(session_id="test-session")
            result_dict = json.loads(result)

            assert result_dict["status"] == "success"
            assert result_dict["session_id"] == "test-session"
            assert result_dict["enabled"] is False  # Runtime override takes precedence
            assert result_dict["global_config"]["enabled"] is True
            assert result_dict["runtime_override"] is False
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config
            mcp_server.runtime_session_tracking_state.clear()

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
            assert "runtime_override" in result_dict
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


class TestIntegration:
    """Integration tests for session tracking tools."""

    @pytest.mark.asyncio
    async def test_start_stop_status_workflow(self):
        """Test complete workflow: start -> status -> stop -> status."""
        # Mock session manager
        mock_manager = Mock()
        mock_manager._is_running = True
        mock_manager.get_active_session_count.return_value = 1
        original_manager = mcp_server.session_manager
        mcp_server.session_manager = mock_manager

        # Mock global config
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
            session_id = "integration-test-session"

            # Step 1: Start tracking
            start_result = await mcp_server.session_tracking_start(session_id=session_id)
            start_dict = json.loads(start_result)
            assert start_dict["status"] == "success"
            assert start_dict["enabled"] is True

            # Step 2: Check status (should show enabled)
            status_result = await mcp_server.session_tracking_status(session_id=session_id)
            status_dict = json.loads(status_result)
            assert status_dict["enabled"] is True
            assert status_dict["runtime_override"] is True

            # Step 3: Stop tracking
            stop_result = await mcp_server.session_tracking_stop(session_id=session_id)
            stop_dict = json.loads(stop_result)
            assert stop_dict["status"] == "success"
            assert stop_dict["enabled"] is False

            # Step 4: Check status again (should show disabled)
            status_result2 = await mcp_server.session_tracking_status(session_id=session_id)
            status_dict2 = json.loads(status_result2)
            assert status_dict2["enabled"] is False
            assert status_dict2["runtime_override"] is False
        finally:
            mcp_server.session_manager = original_manager
            mcp_server.unified_config = original_config
            mcp_server.runtime_session_tracking_state.clear()
