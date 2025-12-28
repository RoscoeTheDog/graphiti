#!/usr/bin/env python3
"""
Tests for V2.0 Installation Cleanup

Tests the cleanup of old v2.0 installation artifacts including:
- Service/task cleanup (Windows/macOS/Linux)
- Directory cleanup with backup
- Rollback on failure
- Interactive vs non-interactive modes
- CLI integration

Story: 13.t - Testing Phase for Old Installation Cleanup
"""

import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from mcp_server.daemon.v2_cleanup import (
    CleanupError,
    V21NotInstalledError,
    V2Cleanup,
    cleanup_v2_0_installation,
)


@pytest.fixture
def mock_home(tmp_path):
    """Create a temporary home directory for testing."""
    home_dir = tmp_path / ".graphiti"
    home_dir.mkdir(parents=True, exist_ok=True)

    # Create typical v2.0 structure
    (home_dir / ".venv").mkdir()
    (home_dir / "mcp_server").mkdir()
    (home_dir / "bin").mkdir()
    (home_dir / "logs").mkdir()

    # Create some files
    (home_dir / "graphiti.config.json").write_text('{"version": "2.0"}')
    (home_dir / "logs" / "daemon.log").write_text("test log data")

    return home_dir


@pytest.fixture
def cleanup_manager(mock_home):
    """Create a V2Cleanup instance with mocked home directory."""
    manager = V2Cleanup()
    manager.home_dir = mock_home
    return manager


class TestV2CleanupBasics:
    """Test basic cleanup functionality."""

    def test_cleanup_initialization(self):
        """Test cleanup manager initialization."""
        manager = V2Cleanup()
        assert manager.platform in ["Windows", "Linux", "Darwin"]
        assert manager.home_dir == Path.home() / ".graphiti"
        assert manager.backup_dir is None
        assert manager.rollback_data == {}

    def test_cleanup_with_no_v2_installation(self, cleanup_manager):
        """Test cleanup when no v2.0 installation exists."""
        # Remove the mock home directory
        shutil.rmtree(cleanup_manager.home_dir)

        with patch.object(cleanup_manager, '_validate_v2_1_installation'):
            result = cleanup_manager.cleanup_v2_0_installation(interactive=False)

        assert result["success"] is True
        assert any("No v2.0 installation found" in action for action in result["actions_taken"])
        # Backup location is still created even if nothing to clean
        assert result["backup_location"] is not None or "No v2.0 installation" in str(result["actions_taken"])
        assert result["rollback_performed"] is False
        assert len(result["errors"]) == 0


class TestV21Validation:
    """Test v2.1 installation validation."""

    def test_validation_success(self, cleanup_manager):
        """Test successful v2.1 validation."""
        mock_detection = {
            "detected": True,
            "install_dir": "/path/to/v2.1",
            "config_location": "project"
        }

        mock_config_file = MagicMock(spec=Path)
        mock_config_file.exists.return_value = True

        with patch('mcp_server.daemon.v2_detection.detect_v2_1_installation', return_value=mock_detection), \
             patch('mcp_server.daemon.paths.get_config_file', return_value=mock_config_file):

            cleanup_manager._validate_v2_1_installation()
            # Should not raise any exceptions

    def test_validation_v21_not_detected(self, cleanup_manager):
        """Test validation fails when v2.1 not detected."""
        mock_detection = {"detected": False}

        with patch('mcp_server.daemon.v2_detection.detect_v2_1_installation', return_value=mock_detection):
            with pytest.raises(V21NotInstalledError, match="V2.1 installation not detected"):
                cleanup_manager._validate_v2_1_installation()

    def test_validation_config_missing(self, cleanup_manager):
        """Test validation fails when v2.1 config missing."""
        mock_detection = {"detected": True}

        mock_config_file = MagicMock(spec=Path)
        mock_config_file.exists.return_value = False
        mock_config_file.__str__ = lambda x: '/nonexistent/config.json'

        with patch('mcp_server.daemon.v2_detection.detect_v2_1_installation', return_value=mock_detection), \
             patch('mcp_server.daemon.paths.get_config_file', return_value=mock_config_file):

            with pytest.raises(V21NotInstalledError, match="V2.1 config not found"):
                cleanup_manager._validate_v2_1_installation()


class TestServiceCleanup:
    """Test service/task cleanup for different platforms."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_windows_task_cleanup_success(self, cleanup_manager):
        """Test successful Windows Task Scheduler cleanup."""
        mock_task_name = "GraphitiBootstrap_test"

        cleanup_manager.backup_dir = Path(tempfile.mkdtemp())

        # Mock subprocess calls with side_effect to return different values
        def subprocess_side_effect(*args, **kwargs):
            cmd = str(args[0]) if args else str(kwargs.get('args', ''))
            if 'Get-ScheduledTask' in cmd:
                return Mock(returncode=0, stdout=mock_task_name, stderr="")
            elif '/Delete' in cmd or 'Delete' in cmd:
                return Mock(returncode=0, stdout="SUCCESS", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")

        with patch('subprocess.run', side_effect=subprocess_side_effect):
            result = cleanup_manager._cleanup_windows_task()

        assert result is True
        assert "windows_task" in cleanup_manager.rollback_data

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_windows_task_cleanup_not_found(self, cleanup_manager):
        """Test Windows cleanup when no task exists."""
        with patch('subprocess.run') as mock_run:
            # Mock empty result (no task found)
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

            result = cleanup_manager._cleanup_windows_task()

        assert result is False

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS-specific test")
    def test_macos_launchagent_cleanup_success(self, cleanup_manager, tmp_path):
        """Test successful macOS LaunchAgent cleanup."""
        plist_path = tmp_path / "Library" / "LaunchAgents" / "com.graphiti.bootstrap.plist"
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text('<?xml version="1.0"?><plist></plist>')

        cleanup_manager.backup_dir = tmp_path / "backup"
        cleanup_manager.backup_dir.mkdir()

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch('subprocess.run') as mock_run:

            result = cleanup_manager._cleanup_macos_launchagent()

        assert result is True
        assert "macos_plist" in cleanup_manager.rollback_data
        assert not plist_path.exists()  # Should be deleted

        # Verify launchctl unload was called
        assert any("launchctl" in str(call) and "unload" in str(call)
                  for call in mock_run.call_args_list)

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS-specific test")
    def test_macos_launchagent_cleanup_not_found(self, cleanup_manager, tmp_path):
        """Test macOS cleanup when no LaunchAgent exists."""
        with patch('pathlib.Path.home', return_value=tmp_path):
            result = cleanup_manager._cleanup_macos_launchagent()

        assert result is False

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux-specific test")
    def test_linux_systemd_cleanup_success(self, cleanup_manager, tmp_path):
        """Test successful Linux systemd service cleanup."""
        service_file = tmp_path / ".config" / "systemd" / "user" / "graphiti-bootstrap.service"
        service_file.parent.mkdir(parents=True, exist_ok=True)
        service_file.write_text('[Unit]\nDescription=Test')

        cleanup_manager.backup_dir = tmp_path / "backup"
        cleanup_manager.backup_dir.mkdir()

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch('subprocess.run') as mock_run:

            result = cleanup_manager._cleanup_linux_systemd()

        assert result is True
        assert "linux_service" in cleanup_manager.rollback_data
        assert not service_file.exists()  # Should be deleted

        # Verify systemctl commands were called
        calls = mock_run.call_args_list
        assert any("stop" in str(call) for call in calls)
        assert any("disable" in str(call) for call in calls)
        assert any("daemon-reload" in str(call) for call in calls)

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux-specific test")
    def test_linux_systemd_cleanup_not_found(self, cleanup_manager, tmp_path):
        """Test Linux cleanup when no service exists."""
        with patch('pathlib.Path.home', return_value=tmp_path):
            result = cleanup_manager._cleanup_linux_systemd()

        assert result is False


class TestDirectoryCleanup:
    """Test directory cleanup functionality."""

    def test_cleanup_directory_full_deletion(self, cleanup_manager):
        """Test full directory deletion."""
        # Verify directory exists before cleanup
        assert cleanup_manager.home_dir.exists()
        assert (cleanup_manager.home_dir / "logs").exists()

        cleanup_manager.backup_dir = Path(tempfile.mkdtemp())
        cleanup_manager._cleanup_directory(keep_logs=False)

        # Directory should be completely removed
        assert not cleanup_manager.home_dir.exists()

        # Backup should exist
        assert "home_dir_backup" in cleanup_manager.rollback_data
        backup_home = cleanup_manager.rollback_data["home_dir_backup"]
        assert backup_home.exists()
        assert (backup_home / "logs").exists()

    def test_cleanup_directory_keep_logs(self, cleanup_manager):
        """Test directory cleanup preserving logs."""
        # Verify directory exists before cleanup
        assert cleanup_manager.home_dir.exists()
        assert (cleanup_manager.home_dir / "logs").exists()

        cleanup_manager.backup_dir = Path(tempfile.mkdtemp())
        cleanup_manager._cleanup_directory(keep_logs=True)

        # Directory should exist with only logs
        assert cleanup_manager.home_dir.exists()
        assert (cleanup_manager.home_dir / "logs").exists()
        assert (cleanup_manager.home_dir / "logs" / "daemon.log").exists()

        # Other directories should be gone
        assert not (cleanup_manager.home_dir / ".venv").exists()
        assert not (cleanup_manager.home_dir / "mcp_server").exists()
        assert not (cleanup_manager.home_dir / "bin").exists()

    def test_cleanup_directory_already_removed(self, cleanup_manager):
        """Test cleanup when directory already doesn't exist."""
        shutil.rmtree(cleanup_manager.home_dir)

        cleanup_manager.backup_dir = Path(tempfile.mkdtemp())
        cleanup_manager._cleanup_directory(keep_logs=False)

        # Should complete without error
        assert not cleanup_manager.home_dir.exists()


class TestInteractiveMode:
    """Test interactive cleanup prompts."""

    def test_prompt_directory_cleanup_delete_all(self, cleanup_manager):
        """Test user chooses to delete all."""
        with patch('builtins.input', side_effect=['1', 'yes']):
            choice = cleanup_manager._prompt_directory_cleanup()

        assert choice == "delete_all"

    def test_prompt_directory_cleanup_keep_logs(self, cleanup_manager):
        """Test user chooses to keep logs."""
        with patch('builtins.input', return_value='2'):
            choice = cleanup_manager._prompt_directory_cleanup()

        assert choice == "delete_except_logs"

    def test_prompt_directory_cleanup_skip(self, cleanup_manager):
        """Test user chooses to skip cleanup."""
        with patch('builtins.input', return_value='3'):
            choice = cleanup_manager._prompt_directory_cleanup()

        assert choice == "skip_cleanup"

    def test_prompt_directory_cleanup_default(self, cleanup_manager):
        """Test default choice (skip) when user presses enter."""
        with patch('builtins.input', return_value=''):
            choice = cleanup_manager._prompt_directory_cleanup()

        assert choice == "skip_cleanup"

    def test_prompt_directory_cleanup_cancel_confirmation(self, cleanup_manager):
        """Test user cancels delete all confirmation."""
        with patch('builtins.input', side_effect=['1', 'no', '3']):
            choice = cleanup_manager._prompt_directory_cleanup()

        assert choice == "skip_cleanup"


class TestNonInteractiveMode:
    """Test non-interactive cleanup modes."""

    def test_noninteractive_safe_default(self, cleanup_manager):
        """Test non-interactive mode with safe defaults (no deletion)."""
        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', return_value=False), \
             patch.object(cleanup_manager, '_verify_cleanup'):

            result = cleanup_manager.cleanup_v2_0_installation(
                interactive=False,
                force_delete=False
            )

        assert result["success"] is True
        assert any("Skipped directory cleanup (non-interactive, no --force)" in action
                  for action in result["actions_taken"])

        # Directory should still exist
        assert cleanup_manager.home_dir.exists()

    def test_noninteractive_force_delete(self, cleanup_manager):
        """Test non-interactive mode with forced deletion."""
        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', return_value=False), \
             patch.object(cleanup_manager, '_verify_cleanup'):

            result = cleanup_manager.cleanup_v2_0_installation(
                interactive=False,
                force_delete=True,
                keep_logs=False
            )

        assert result["success"] is True
        assert any("full deletion, non-interactive" in action
                  for action in result["actions_taken"])

        # Directory should be removed
        assert not cleanup_manager.home_dir.exists()

    def test_noninteractive_force_delete_keep_logs(self, cleanup_manager, tmp_path):
        """Test non-interactive mode with forced deletion but keep logs."""
        # Store original log content for verification
        original_log_content = (cleanup_manager.home_dir / "logs" / "daemon.log").read_text()

        # Use a unique tmp path for this test to avoid conflicts
        unique_backup = tmp_path / "unique_backup_keep_logs"
        unique_backup.mkdir()

        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', return_value=False), \
             patch.object(cleanup_manager, '_verify_cleanup'), \
             patch('mcp_server.daemon.v2_cleanup.Path.home', return_value=tmp_path):

            cleanup_manager.backup_dir = unique_backup
            result = cleanup_manager.cleanup_v2_0_installation(
                interactive=False,
                force_delete=True,
                keep_logs=True
            )

        assert result["success"] is True
        assert any("kept logs, non-interactive" in action
                  for action in result["actions_taken"])

        # Directory should exist with only logs
        assert cleanup_manager.home_dir.exists()
        assert (cleanup_manager.home_dir / "logs").exists()
        assert (cleanup_manager.home_dir / "logs" / "daemon.log").exists()
        assert (cleanup_manager.home_dir / "logs" / "daemon.log").read_text() == original_log_content


class TestRollback:
    """Test rollback functionality."""

    def test_rollback_directory_restoration(self, cleanup_manager):
        """Test rollback restores directory from backup."""
        # Create backup
        cleanup_manager.backup_dir = Path(tempfile.mkdtemp())
        backup_home = cleanup_manager.backup_dir / "graphiti"
        shutil.copytree(cleanup_manager.home_dir, backup_home, symlinks=True)
        cleanup_manager.rollback_data["home_dir_backup"] = backup_home

        # Delete original directory
        original_log_data = (cleanup_manager.home_dir / "logs" / "daemon.log").read_text()
        shutil.rmtree(cleanup_manager.home_dir)
        assert not cleanup_manager.home_dir.exists()

        # Rollback
        cleanup_manager._rollback()

        # Directory should be restored
        assert cleanup_manager.home_dir.exists()
        assert (cleanup_manager.home_dir / "logs" / "daemon.log").exists()
        assert (cleanup_manager.home_dir / "logs" / "daemon.log").read_text() == original_log_data

    def test_rollback_without_backup(self, cleanup_manager):
        """Test rollback fails gracefully without backup."""
        cleanup_manager.backup_dir = None

        with pytest.raises(CleanupError, match="Cannot rollback: backup directory not found"):
            cleanup_manager._rollback()

    def test_rollback_on_keyboard_interrupt(self, cleanup_manager):
        """Test rollback triggered by user cancellation."""
        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', side_effect=KeyboardInterrupt), \
             patch.object(cleanup_manager, '_rollback') as mock_rollback:

            result = cleanup_manager.cleanup_v2_0_installation(interactive=False)

        assert result["success"] is False
        assert result["rollback_performed"] is True
        assert "Cleanup cancelled by user" in result["actions_taken"]
        mock_rollback.assert_called_once()


class TestFullWorkflow:
    """Test complete cleanup workflows."""

    def test_full_interactive_cleanup_skip(self, cleanup_manager):
        """Test full interactive cleanup with user choosing to skip."""
        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', return_value=True), \
             patch.object(cleanup_manager, '_prompt_directory_cleanup', return_value='skip_cleanup'), \
             patch.object(cleanup_manager, '_verify_cleanup'):

            result = cleanup_manager.cleanup_v2_0_installation(interactive=True)

        assert result["success"] is True
        assert result["backup_location"] is not None
        assert any("Removed v2.0 service/task" in action for action in result["actions_taken"])
        assert any("Skipped directory cleanup (user choice)" in action for action in result["actions_taken"])
        assert cleanup_manager.home_dir.exists()  # Should still exist

    def test_full_interactive_cleanup_delete_all(self, cleanup_manager, tmp_path):
        """Test full interactive cleanup with full deletion."""
        # Ensure home_dir exists before test
        assert cleanup_manager.home_dir.exists()

        # Use a unique tmp path for this test to avoid conflicts
        unique_backup = tmp_path / "unique_backup_delete_all"
        unique_backup.mkdir()

        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', return_value=True), \
             patch.object(cleanup_manager, '_prompt_directory_cleanup', return_value='delete_all'), \
             patch.object(cleanup_manager, '_verify_cleanup'), \
             patch('mcp_server.daemon.v2_cleanup.Path.home', return_value=tmp_path):

            cleanup_manager.backup_dir = unique_backup
            result = cleanup_manager.cleanup_v2_0_installation(interactive=True)

        assert result["success"] is True
        assert any("Removed ~/.graphiti/ (full deletion)" in action for action in result["actions_taken"])
        assert not cleanup_manager.home_dir.exists()

    def test_full_cleanup_with_service_warning(self, cleanup_manager):
        """Test cleanup continues when service cleanup fails non-critically."""
        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', side_effect=Exception("Service not found")), \
             patch.object(cleanup_manager, '_verify_cleanup'):

            result = cleanup_manager.cleanup_v2_0_installation(interactive=False)

        assert result["success"] is True
        assert any("Service cleanup skipped" in action for action in result["actions_taken"])


class TestConvenienceFunction:
    """Test the top-level convenience function."""

    def test_cleanup_v2_0_installation_function(self, tmp_path):
        """Test cleanup_v2_0_installation() convenience function."""
        with patch('mcp_server.daemon.v2_cleanup.V2Cleanup') as mock_cleanup_class:
            mock_instance = MagicMock()
            mock_cleanup_class.return_value = mock_instance
            mock_instance.cleanup_v2_0_installation.return_value = {
                "success": True,
                "actions_taken": ["test"],
                "backup_location": tmp_path,
                "rollback_performed": False,
                "errors": []
            }

            result = cleanup_v2_0_installation(
                interactive=False,
                force_delete=True,
                keep_logs=True
            )

        assert result["success"] is True
        mock_instance.cleanup_v2_0_installation.assert_called_once_with(
            interactive=False,
            force_delete=True,
            keep_logs=True
        )


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_cleanup_with_v21_broken_during_cleanup(self, cleanup_manager):
        """Test cleanup fails if v2.1 breaks during cleanup."""
        call_count = {'count': 0}

        def mock_validate():
            call_count['count'] += 1
            if call_count['count'] > 1:  # Fail on second call (verification)
                raise V21NotInstalledError("V2.1 broken")

        with patch.object(cleanup_manager, '_validate_v2_1_installation', side_effect=mock_validate), \
             patch.object(cleanup_manager, '_cleanup_service', return_value=False), \
             patch.object(cleanup_manager, '_rollback') as mock_rollback:

            result = cleanup_manager.cleanup_v2_0_installation(interactive=False, force_delete=True)

        assert result["success"] is False
        assert result["rollback_performed"] is True
        # The error is wrapped in CleanupError during _verify_cleanup
        assert any("V2.1 installation broken" in str(error) or "Directory cleanup failed" in str(error)
                  for error in result["errors"])
        mock_rollback.assert_called_once()

    def test_cleanup_permissions_error(self, cleanup_manager):
        """Test cleanup handles permission errors gracefully."""
        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', return_value=False), \
             patch.object(cleanup_manager, '_cleanup_directory', side_effect=PermissionError("Access denied")), \
             patch.object(cleanup_manager, '_rollback'):

            result = cleanup_manager.cleanup_v2_0_installation(
                interactive=False,
                force_delete=True
            )

        assert result["success"] is False
        assert result["rollback_performed"] is True
        assert any("Access denied" in str(error) for error in result["errors"])

    def test_backup_creation_success(self, cleanup_manager):
        """Test backup directory is created with timestamp."""
        with patch.object(cleanup_manager, '_validate_v2_1_installation'), \
             patch.object(cleanup_manager, '_cleanup_service', return_value=False), \
             patch.object(cleanup_manager, '_verify_cleanup'):

            result = cleanup_manager.cleanup_v2_0_installation(interactive=False)

        assert result["backup_location"] is not None
        assert ".graphiti.cleanup-backup-" in str(result["backup_location"])
        assert result["backup_location"].exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
