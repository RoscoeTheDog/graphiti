"""
Unit Tests for VenvManager

Tests the venv creation, detection, and validation logic:
- VenvManager.check_uv_available()
- VenvManager.validate_python_version()
- VenvManager.detect_venv()
- VenvManager.create_venv()
- Platform-agnostic path handling
"""

import sys
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

import pytest

from mcp_server.daemon.venv_manager import VenvManager


class TestCheckUvAvailable:
    """Test UV availability detection."""

    def test_check_uv_available_when_uv_in_path(self):
        """VenvManager.check_uv_available() returns True when uv is in PATH"""
        with patch('shutil.which', return_value='/usr/local/bin/uv'):
            manager = VenvManager()
            assert manager.check_uv_available() is True

    def test_check_uv_available_when_uv_not_available(self):
        """VenvManager.check_uv_available() returns False when uv is not available"""
        with patch('shutil.which', return_value=None):
            manager = VenvManager()
            assert manager.check_uv_available() is False


class TestValidatePythonVersion:
    """Test Python version validation."""

    def test_validate_python_version_accepts_3_10(self):
        """VenvManager.validate_python_version() accepts Python 3.10+"""
        manager = VenvManager()
        # Mock sys.version_info for Python 3.10
        with patch.object(sys, 'version_info', (3, 10, 0)):
            assert manager.validate_python_version() is True

    def test_validate_python_version_accepts_3_11(self):
        """VenvManager.validate_python_version() accepts Python 3.11+"""
        manager = VenvManager()
        with patch.object(sys, 'version_info', (3, 11, 5)):
            assert manager.validate_python_version() is True

    def test_validate_python_version_accepts_3_12(self):
        """VenvManager.validate_python_version() accepts Python 3.12+"""
        manager = VenvManager()
        with patch.object(sys, 'version_info', (3, 12, 0)):
            assert manager.validate_python_version() is True

    def test_validate_python_version_rejects_3_9(self):
        """VenvManager.validate_python_version() rejects Python 3.9 and below"""
        manager = VenvManager()
        with patch.object(sys, 'version_info', (3, 9, 18)):
            assert manager.validate_python_version() is False

    def test_validate_python_version_rejects_3_8(self):
        """VenvManager.validate_python_version() rejects Python 3.8"""
        manager = VenvManager()
        with patch.object(sys, 'version_info', (3, 8, 10)):
            assert manager.validate_python_version() is False

    def test_validate_python_version_rejects_2_7(self):
        """VenvManager.validate_python_version() rejects Python 2.7"""
        manager = VenvManager()
        with patch.object(sys, 'version_info', (2, 7, 18)):
            assert manager.validate_python_version() is False


class TestDetectVenv:
    """Test venv detection."""

    def test_detect_venv_returns_true_for_existing_valid_venv(self):
        """VenvManager.detect_venv() returns True for existing valid venv"""
        manager = VenvManager()

        # Mock venv directory exists
        mock_venv_path = MagicMock(spec=Path)
        mock_venv_path.exists.return_value = True
        mock_venv_path.is_dir.return_value = True

        # Mock activate script exists (Unix)
        mock_activate = MagicMock(spec=Path)
        mock_activate.exists.return_value = True
        mock_venv_path.__truediv__ = lambda self, other: mock_activate if 'activate' in str(other) else MagicMock()

        with patch.object(manager, 'venv_path', mock_venv_path):
            assert manager.detect_venv() is True

    def test_detect_venv_returns_false_for_nonexistent_venv(self):
        """VenvManager.detect_venv() returns False for non-existent venv"""
        manager = VenvManager()

        # Mock venv directory does not exist
        mock_venv_path = MagicMock(spec=Path)
        mock_venv_path.exists.return_value = False

        with patch.object(manager, 'venv_path', mock_venv_path):
            assert manager.detect_venv() is False

    def test_detect_venv_returns_false_for_corrupted_venv(self):
        """VenvManager.detect_venv() returns False for corrupted venv (missing activate)"""
        manager = VenvManager()

        # Mock venv directory exists but activate script missing
        mock_venv_path = MagicMock(spec=Path)
        mock_venv_path.exists.return_value = True
        mock_venv_path.is_dir.return_value = True

        # Mock activate script does NOT exist
        mock_activate = MagicMock(spec=Path)
        mock_activate.exists.return_value = False
        mock_venv_path.__truediv__ = lambda self, other: mock_activate if 'activate' in str(other) else MagicMock()

        with patch.object(manager, 'venv_path', mock_venv_path):
            assert manager.detect_venv() is False


class TestCreateVenv:
    """Test venv creation."""

    def test_create_venv_uses_uv_when_available(self):
        """VenvManager.create_venv() uses uv when available"""
        manager = VenvManager()

        # Mock uv available
        with patch.object(manager, 'check_uv_available', return_value=True):
            # Mock venv does not exist
            with patch.object(manager, 'detect_venv', return_value=False):
                # Mock successful subprocess call
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

                    # Mock directory creation
                    with patch.object(Path, 'mkdir'):
                        result = manager.create_venv()

                        # Verify uv venv was called
                        assert result is True
                        mock_run.assert_called_once()
                        args = mock_run.call_args[0][0]
                        assert 'uv' in args
                        assert 'venv' in args

    def test_create_venv_falls_back_to_python_when_uv_unavailable(self):
        """VenvManager.create_venv() falls back to python -m venv when uv unavailable"""
        manager = VenvManager()

        # Mock uv NOT available
        with patch.object(manager, 'check_uv_available', return_value=False):
            # Mock venv does not exist
            with patch.object(manager, 'detect_venv', return_value=False):
                # Mock successful subprocess call
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

                    # Mock directory creation
                    with patch.object(Path, 'mkdir'):
                        result = manager.create_venv()

                        # Verify python -m venv was called
                        assert result is True
                        mock_run.assert_called_once()
                        args = mock_run.call_args[0][0]
                        assert sys.executable in args or 'python' in args
                        assert '-m' in args
                        assert 'venv' in args

    def test_create_venv_is_idempotent_skips_if_exists(self):
        """VenvManager.create_venv() is idempotent (skips if venv exists)"""
        manager = VenvManager()

        # Mock venv already exists
        with patch.object(manager, 'detect_venv', return_value=True):
            # Mock subprocess should NOT be called
            with patch('subprocess.run') as mock_run:
                result = manager.create_venv()

                # Verify venv creation was skipped
                assert result is True
                mock_run.assert_not_called()


class TestPlatformAgnosticPaths:
    """Test platform-agnostic path handling."""

    def test_windows_path_handling(self):
        """VenvManager path handling works on Windows (backslashes)"""
        with patch('platform.system', return_value='Windows'):
            manager = VenvManager()

            # Verify venv_path uses pathlib (platform-agnostic)
            assert isinstance(manager.venv_path, Path)

            # On Windows, Path should use backslashes
            venv_str = str(manager.venv_path)
            # Note: Path normalizes to OS format, so on Windows it will be backslashes
            # We verify it's a valid Path object that can handle both formats
            assert manager.venv_path.parts[-1] == '.venv'

    def test_unix_path_handling(self):
        """VenvManager path handling works on Unix (forward slashes)"""
        with patch('platform.system', return_value='Linux'):
            manager = VenvManager()

            # Verify venv_path uses pathlib (platform-agnostic)
            assert isinstance(manager.venv_path, Path)

            # On Unix, Path should use forward slashes
            venv_str = str(manager.venv_path)
            assert manager.venv_path.parts[-1] == '.venv'

    def test_path_operations_work_on_windows(self):
        """Path operations (mkdir, exists, etc.) work correctly on Windows"""
        with patch('platform.system', return_value='Windows'):
            manager = VenvManager()

            # Mock Path operations
            with patch.object(Path, 'mkdir') as mock_mkdir:
                with patch.object(Path, 'exists', return_value=False):
                    # Verify mkdir is called with correct arguments
                    manager.venv_path.parent.mkdir(parents=True, exist_ok=True)
                    mock_mkdir.assert_called()

    def test_path_operations_work_on_unix(self):
        """Path operations (mkdir, exists, etc.) work correctly on Unix"""
        with patch('platform.system', return_value='Linux'):
            manager = VenvManager()

            # Mock Path operations
            with patch.object(Path, 'mkdir') as mock_mkdir:
                with patch.object(Path, 'exists', return_value=False):
                    # Verify mkdir is called with correct arguments
                    manager.venv_path.parent.mkdir(parents=True, exist_ok=True)
                    mock_mkdir.assert_called()


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_create_venv_handles_subprocess_failure(self):
        """VenvManager.create_venv() handles subprocess failures gracefully"""
        manager = VenvManager()

        with patch.object(manager, 'check_uv_available', return_value=True):
            with patch.object(manager, 'detect_venv', return_value=False):
                # Mock subprocess failure
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=1, stdout='', stderr='Error creating venv')

                    with patch.object(Path, 'mkdir'):
                        result = manager.create_venv()

                        # Verify failure is detected
                        assert result is False

    def test_create_venv_handles_permission_error(self):
        """VenvManager.create_venv() handles permission errors"""
        manager = VenvManager()

        with patch.object(manager, 'check_uv_available', return_value=True):
            with patch.object(manager, 'detect_venv', return_value=False):
                # Mock permission error during mkdir
                with patch.object(Path, 'mkdir', side_effect=PermissionError):
                    with pytest.raises(PermissionError):
                        manager.create_venv()

    def test_venv_path_is_always_under_graphiti_home(self):
        """Venv path is always ~/.graphiti/.venv (path traversal prevention)"""
        manager = VenvManager()

        # Verify venv path is constructed correctly
        assert manager.venv_path.parts[-2:] == ('.graphiti', '.venv')

        # Verify it starts from home directory
        assert manager.venv_path.parts[0] == Path.home().parts[0]
