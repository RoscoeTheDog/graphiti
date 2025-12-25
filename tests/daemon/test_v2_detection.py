"""
Unit tests for v2.0 installation detection module.

Tests:
    - Detection returns False on clean system
    - Detection returns True when ~/.graphiti/ exists
    - Windows: detection when GraphitiBootstrap task exists
    - macOS: detection when com.graphiti.bootstrap plist exists
    - Linux: detection when graphiti-bootstrap service exists
    - Graceful handling of permission errors
    - Correct platform detection
    - Return structure validation

See: .claude/sprint/plans/11-plan.yaml
"""

import os
import platform
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcp_server.daemon.v2_detection import (
    _detect_linux_service,
    _detect_macos_launchagent,
    _detect_windows_task,
    detect_v2_0_installation,
)


class TestDetectV20Installation:
    """Test detect_v2_0_installation() function."""

    def test_returns_false_on_clean_system(self, tmp_path, monkeypatch):
        """Test detection returns False when no v2.0 artifacts exist."""
        # Mock Path.home() to return a temporary directory
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock platform.system() to return current platform
        with patch("mcp_server.daemon.v2_detection.platform.system") as mock_platform:
            mock_platform.return_value = "Linux"

            # Mock service detection to return None
            with patch("mcp_server.daemon.v2_detection._detect_linux_service") as mock_service:
                mock_service.return_value = None

                result = detect_v2_0_installation()

                assert result["detected"] is False
                assert result["home_dir"] is None
                assert result["config_file"] is None
                assert result["service_task"] is None

    def test_returns_true_when_home_dir_exists(self, tmp_path, monkeypatch):
        """Test detection returns True when ~/.graphiti/ directory exists."""
        # Create v2.0 home directory
        v2_home = tmp_path / ".graphiti"
        v2_home.mkdir()

        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock platform.system() to return current platform
        with patch("mcp_server.daemon.v2_detection.platform.system") as mock_platform:
            mock_platform.return_value = "Linux"

            # Mock service detection to return None
            with patch("mcp_server.daemon.v2_detection._detect_linux_service") as mock_service:
                mock_service.return_value = None

                result = detect_v2_0_installation()

                assert result["detected"] is True
                assert result["home_dir"] == v2_home
                assert result["config_file"] is None  # config file not created
                assert result["service_task"] is None

    def test_includes_config_file_when_exists(self, tmp_path, monkeypatch):
        """Test detection includes config file when it exists."""
        # Create v2.0 home directory and config file
        v2_home = tmp_path / ".graphiti"
        v2_home.mkdir()
        config_file = v2_home / "graphiti.config.json"
        config_file.write_text("{}")

        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock platform.system() to return current platform
        with patch("mcp_server.daemon.v2_detection.platform.system") as mock_platform:
            mock_platform.return_value = "Linux"

            # Mock service detection to return None
            with patch("mcp_server.daemon.v2_detection._detect_linux_service") as mock_service:
                mock_service.return_value = None

                result = detect_v2_0_installation()

                assert result["detected"] is True
                assert result["home_dir"] == v2_home
                assert result["config_file"] == config_file
                assert result["service_task"] is None

    def test_windows_task_detection(self, tmp_path, monkeypatch):
        """Test Windows task detection when GraphitiBootstrap task exists."""
        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock platform.system() to return Windows
        with patch("mcp_server.daemon.v2_detection.platform.system") as mock_platform:
            mock_platform.return_value = "Windows"

            # Mock _detect_windows_task to return task name
            with patch("mcp_server.daemon.v2_detection._detect_windows_task") as mock_task:
                mock_task.return_value = "GraphitiBootstrap"

                result = detect_v2_0_installation()

                assert result["detected"] is True
                assert result["home_dir"] is None  # no directory
                assert result["config_file"] is None
                assert result["service_task"] == "GraphitiBootstrap"

    def test_macos_launchagent_detection(self, tmp_path, monkeypatch):
        """Test macOS LaunchAgent detection when plist exists."""
        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock platform.system() to return Darwin
        with patch("mcp_server.daemon.v2_detection.platform.system") as mock_platform:
            mock_platform.return_value = "Darwin"

            # Mock _detect_macos_launchagent to return service ID
            with patch("mcp_server.daemon.v2_detection._detect_macos_launchagent") as mock_service:
                mock_service.return_value = "com.graphiti.bootstrap"

                result = detect_v2_0_installation()

                assert result["detected"] is True
                assert result["home_dir"] is None  # no directory
                assert result["config_file"] is None
                assert result["service_task"] == "com.graphiti.bootstrap"

    def test_linux_service_detection(self, tmp_path, monkeypatch):
        """Test Linux systemd service detection when service exists."""
        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock platform.system() to return Linux
        with patch("mcp_server.daemon.v2_detection.platform.system") as mock_platform:
            mock_platform.return_value = "Linux"

            # Mock _detect_linux_service to return service name
            with patch("mcp_server.daemon.v2_detection._detect_linux_service") as mock_service:
                mock_service.return_value = "graphiti-bootstrap"

                result = detect_v2_0_installation()

                assert result["detected"] is True
                assert result["home_dir"] is None  # no directory
                assert result["config_file"] is None
                assert result["service_task"] == "graphiti-bootstrap"

    def test_return_structure_has_expected_keys(self, tmp_path, monkeypatch):
        """Test return structure contains expected keys."""
        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock platform.system() to return current platform
        with patch("mcp_server.daemon.v2_detection.platform.system") as mock_platform:
            mock_platform.return_value = "Linux"

            # Mock service detection to return None
            with patch("mcp_server.daemon.v2_detection._detect_linux_service") as mock_service:
                mock_service.return_value = None

                result = detect_v2_0_installation()

                # Verify all expected keys are present
                assert "detected" in result
                assert "home_dir" in result
                assert "config_file" in result
                assert "service_task" in result

                # Verify types
                assert isinstance(result["detected"], bool)
                assert result["home_dir"] is None or isinstance(result["home_dir"], Path)
                assert result["config_file"] is None or isinstance(result["config_file"], Path)
                assert result["service_task"] is None or isinstance(result["service_task"], str)


class TestDetectWindowsTask:
    """Test _detect_windows_task() function."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_real_detection_on_windows(self):
        """Test actual Windows task detection (requires Windows environment)."""
        result = _detect_windows_task()
        # Result can be either a task name or None (depends on actual system state)
        assert result is None or isinstance(result, str)

    def test_returns_none_on_timeout(self):
        """Test graceful handling when PowerShell query times out."""
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell", timeout=5)

            result = _detect_windows_task()
            assert result is None

    def test_returns_none_on_powershell_not_found(self):
        """Test graceful handling when PowerShell is not available."""
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("powershell.exe not found")

            result = _detect_windows_task()
            assert result is None

    def test_returns_none_on_permission_error(self):
        """Test graceful handling of permission denied errors."""
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = PermissionError("Access denied")

            result = _detect_windows_task()
            assert result is None

    def test_returns_task_name_when_found(self):
        """Test returns task name when PowerShell query succeeds."""
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            # Mock successful query returning task name
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "GraphitiBootstrap\n"
            mock_run.return_value = mock_result

            result = _detect_windows_task()
            assert result == "GraphitiBootstrap"

    def test_returns_first_task_when_multiple_found(self):
        """Test returns first task name when multiple tasks match."""
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            # Mock query returning multiple task names
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "GraphitiBootstrap\nGraphitiBootstrap_Admin\n"
            mock_run.return_value = mock_result

            result = _detect_windows_task()
            assert result == "GraphitiBootstrap"

    def test_returns_none_when_no_tasks_found(self):
        """Test returns None when PowerShell query returns empty."""
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            # Mock query returning empty output
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            result = _detect_windows_task()
            assert result is None


class TestDetectMacOSLaunchAgent:
    """Test _detect_macos_launchagent() function."""

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS-specific test")
    def test_real_detection_on_macos(self):
        """Test actual macOS LaunchAgent detection (requires macOS environment)."""
        result = _detect_macos_launchagent()
        # Result can be either service ID or None (depends on actual system state)
        assert result is None or isinstance(result, str)

    def test_returns_service_id_when_plist_exists(self, tmp_path, monkeypatch):
        """Test returns service ID when plist file exists."""
        # Create LaunchAgents directory and plist
        launch_agents = tmp_path / "Library" / "LaunchAgents"
        launch_agents.mkdir(parents=True)
        plist = launch_agents / "com.graphiti.bootstrap.plist"
        plist.write_text("<plist></plist>")

        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _detect_macos_launchagent()
        assert result == "com.graphiti.bootstrap"

    def test_returns_service_id_when_loaded_in_launchctl(self, tmp_path, monkeypatch):
        """Test returns service ID when service is loaded (even if plist is missing)."""
        # Mock Path.home() to return tmp_path (no plist created)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock launchctl list to return service ID
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "PID\tStatus\tLabel\n123\t0\tcom.graphiti.bootstrap\n"
            mock_run.return_value = mock_result

            result = _detect_macos_launchagent()
            assert result == "com.graphiti.bootstrap"

    def test_returns_none_on_timeout(self, tmp_path, monkeypatch):
        """Test graceful handling when launchctl query times out."""
        # Mock Path.home() to return tmp_path (no plist)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="launchctl", timeout=5)

            result = _detect_macos_launchagent()
            assert result is None

    def test_returns_none_on_launchctl_not_found(self, tmp_path, monkeypatch):
        """Test graceful handling when launchctl is not available."""
        # Mock Path.home() to return tmp_path (no plist)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("launchctl not found")

            result = _detect_macos_launchagent()
            assert result is None

    def test_returns_none_on_permission_error(self, tmp_path, monkeypatch):
        """Test graceful handling of permission denied errors."""
        # Mock Path.home() to return tmp_path (no plist)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = PermissionError("Access denied")

            result = _detect_macos_launchagent()
            assert result is None


class TestDetectLinuxService:
    """Test _detect_linux_service() function."""

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux-specific test")
    def test_real_detection_on_linux(self):
        """Test actual Linux systemd service detection (requires Linux environment)."""
        result = _detect_linux_service()
        # Result can be either service name or None (depends on actual system state)
        assert result is None or isinstance(result, str)

    def test_returns_service_name_when_file_exists(self, tmp_path, monkeypatch):
        """Test returns service name when service file exists."""
        # Create systemd user directory and service file
        systemd_user = tmp_path / ".config" / "systemd" / "user"
        systemd_user.mkdir(parents=True)
        service_file = systemd_user / "graphiti-bootstrap.service"
        service_file.write_text("[Unit]\nDescription=Graphiti Bootstrap\n")

        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _detect_linux_service()
        assert result == "graphiti-bootstrap"

    def test_uses_xdg_config_home_when_set(self, tmp_path, monkeypatch):
        """Test uses XDG_CONFIG_HOME environment variable when set."""
        # Create custom config directory
        custom_config = tmp_path / "custom_config"
        systemd_user = custom_config / "systemd" / "user"
        systemd_user.mkdir(parents=True)
        service_file = systemd_user / "graphiti-bootstrap.service"
        service_file.write_text("[Unit]\nDescription=Graphiti Bootstrap\n")

        # Set XDG_CONFIG_HOME environment variable
        monkeypatch.setenv("XDG_CONFIG_HOME", str(custom_config))

        result = _detect_linux_service()
        assert result == "graphiti-bootstrap"

    def test_returns_service_name_when_loaded_in_systemctl(self, tmp_path, monkeypatch):
        """Test returns service name when service is loaded (even if file is missing)."""
        # Mock Path.home() to return tmp_path (no service file)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock systemctl --user status to return active (returncode 0)
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0  # service is active
            mock_result.stdout = "Active: active (running)"
            mock_run.return_value = mock_result

            result = _detect_linux_service()
            assert result == "graphiti-bootstrap"

    def test_returns_service_name_when_inactive_in_systemctl(self, tmp_path, monkeypatch):
        """Test returns service name when service is inactive (returncode 3)."""
        # Mock Path.home() to return tmp_path (no service file)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock systemctl --user status to return inactive (returncode 3)
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 3  # service is inactive
            mock_result.stdout = "Active: inactive (dead)"
            mock_run.return_value = mock_result

            result = _detect_linux_service()
            assert result == "graphiti-bootstrap"

    def test_returns_none_when_service_not_found_in_systemctl(self, tmp_path, monkeypatch):
        """Test returns None when systemctl returns not found (returncode 4)."""
        # Mock Path.home() to return tmp_path (no service file)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock systemctl --user status to return not found (returncode 4)
        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 4  # service not found
            mock_result.stdout = "Unit graphiti-bootstrap.service could not be found"
            mock_run.return_value = mock_result

            result = _detect_linux_service()
            assert result is None

    def test_returns_none_on_timeout(self, tmp_path, monkeypatch):
        """Test graceful handling when systemctl query times out."""
        # Mock Path.home() to return tmp_path (no service file)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="systemctl", timeout=5)

            result = _detect_linux_service()
            assert result is None

    def test_returns_none_on_systemctl_not_found(self, tmp_path, monkeypatch):
        """Test graceful handling when systemctl is not available."""
        # Mock Path.home() to return tmp_path (no service file)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("systemctl not found")

            result = _detect_linux_service()
            assert result is None

    def test_returns_none_on_permission_error(self, tmp_path, monkeypatch):
        """Test graceful handling of permission denied errors."""
        # Mock Path.home() to return tmp_path (no service file)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("mcp_server.daemon.v2_detection.subprocess.run") as mock_run:
            mock_run.side_effect = PermissionError("Access denied")

            result = _detect_linux_service()
            assert result is None
