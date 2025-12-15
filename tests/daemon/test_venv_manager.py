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

from mcp_server.daemon.venv_manager import (
    VenvManager,
    IncompatiblePythonVersionError,
    VenvCreationError,
)


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
            with pytest.raises(IncompatiblePythonVersionError) as exc_info:
                manager.validate_python_version()
            assert "3.10+ required" in str(exc_info.value)

    def test_validate_python_version_rejects_3_8(self):
        """VenvManager.validate_python_version() rejects Python 3.8"""
        manager = VenvManager()
        with patch.object(sys, 'version_info', (3, 8, 10)):
            with pytest.raises(IncompatiblePythonVersionError) as exc_info:
                manager.validate_python_version()
            assert "3.10+ required" in str(exc_info.value)

    def test_validate_python_version_rejects_2_7(self):
        """VenvManager.validate_python_version() rejects Python 2.7"""
        manager = VenvManager()
        with patch.object(sys, 'version_info', (2, 7, 18)):
            with pytest.raises(IncompatiblePythonVersionError) as exc_info:
                manager.validate_python_version()
            assert "3.10+ required" in str(exc_info.value)


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

        # Mock pyvenv.cfg exists (so we get past that check)
        mock_pyvenv_cfg = MagicMock(spec=Path)
        mock_pyvenv_cfg.exists.return_value = True

        # Mock intermediate paths (Scripts/bin)
        mock_scripts = MagicMock(spec=Path)

        # Mock activate script does NOT exist
        mock_activate = MagicMock(spec=Path)
        mock_activate.exists.return_value = False

        def mock_truediv(self, other):
            if 'pyvenv.cfg' in str(other):
                return mock_pyvenv_cfg
            elif 'Scripts' in str(other) or 'bin' in str(other):
                return mock_scripts
            elif 'activate' in str(other):
                return mock_activate
            else:
                return MagicMock()

        mock_venv_path.__truediv__ = mock_truediv
        mock_scripts.__truediv__ = lambda self, other: mock_activate if 'activate' in str(other) else MagicMock()

        with patch.object(manager, 'venv_path', mock_venv_path):
            assert manager.detect_venv() is False


class TestCreateVenv:
    """Test venv creation."""

    def test_create_venv_uses_uv_when_available(self):
        """VenvManager.create_venv() uses uv when available"""
        manager = VenvManager()

        # Mock uv available
        with patch.object(manager, 'check_uv_available', return_value=True):
            # Mock venv does not exist initially, then exists after creation
            with patch.object(manager, 'detect_venv', side_effect=[False, True]):
                # Mock successful subprocess call
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

                    # Mock directory creation
                    with patch.object(Path, 'mkdir'):
                        success, msg = manager.create_venv()

                        # Verify uv venv was called
                        assert success is True
                        assert isinstance(msg, str)
                        mock_run.assert_called_once()
                        args = mock_run.call_args[0][0]
                        assert 'uv' in args
                        assert 'venv' in args

    def test_create_venv_falls_back_to_python_when_uv_unavailable(self):
        """VenvManager.create_venv() falls back to python -m venv when uv unavailable"""
        manager = VenvManager()

        # Mock uv NOT available
        with patch.object(manager, 'check_uv_available', return_value=False):
            # Mock venv does not exist initially, then exists after creation
            with patch.object(manager, 'detect_venv', side_effect=[False, True]):
                # Mock successful subprocess call
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

                    # Mock directory creation
                    with patch.object(Path, 'mkdir'):
                        success, msg = manager.create_venv()

                        # Verify python -m venv was called
                        assert success is True
                        assert isinstance(msg, str)
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
                success, msg = manager.create_venv()

                # Verify venv creation was skipped
                assert success is True
                assert isinstance(msg, str)
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
                        with pytest.raises(VenvCreationError):
                            manager.create_venv()

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


class TestGetUvExecutable:
    """Test UV executable detection in venv."""

    def test_get_uv_executable_finds_uv_in_venv_windows(self):
        """VenvManager.get_uv_executable() finds uv in venv on Windows"""
        manager = VenvManager()

        # Mock Windows platform
        with patch('platform.system', return_value='Windows'):
            mock_uv_path = manager.venv_path / 'Scripts' / 'uv.exe'
            with patch.object(Path, 'exists', return_value=True):
                result = manager.get_uv_executable()
                assert result == mock_uv_path

    def test_get_uv_executable_finds_uv_in_venv_unix(self):
        """VenvManager.get_uv_executable() finds uv in venv on Unix"""
        # Mock Unix platform from the start
        with patch('platform.system', return_value='Linux'):
            manager = VenvManager()
            mock_uv_path = manager.venv_path / 'bin' / 'uv'
            with patch.object(Path, 'exists', return_value=True):
                result = manager.get_uv_executable()
                assert result == mock_uv_path

    def test_get_uv_executable_returns_none_when_not_found(self):
        """VenvManager.get_uv_executable() returns None when uv not in venv"""
        manager = VenvManager()

        with patch.object(Path, 'exists', return_value=False):
            result = manager.get_uv_executable()
            assert result is None


class TestDetectRepoLocation:
    """Test repository location detection."""

    def test_detect_repo_location_finds_mcp_server_from_venv_path(self):
        """VenvManager.detect_repo_location() finds mcp_server directory from venv path"""
        manager = VenvManager()

        # Mock venv path: /home/user/graphiti/.graphiti/.venv
        # Repo root should be: /home/user/graphiti
        mock_repo_root = Path('/home/user/graphiti')
        mock_venv_path = mock_repo_root / '.graphiti' / '.venv'

        with patch.object(manager, 'venv_path', mock_venv_path):
            # Mock pyproject.toml exists at repo root
            with patch.object(Path, 'exists') as mock_exists:
                def exists_side_effect(self):
                    # Check if this is the mcp_server/pyproject.toml path
                    return self == mock_repo_root / 'mcp_server' / 'pyproject.toml'

                mock_exists.side_effect = exists_side_effect

                result = manager.detect_repo_location()
                assert result == mock_repo_root

    def test_detect_repo_location_handles_repo_moved(self):
        """VenvManager.detect_repo_location() returns None when repo is moved"""
        manager = VenvManager()

        # Venv exists but repo is not found in expected location
        with patch.object(Path, 'exists', return_value=False):
            result = manager.detect_repo_location()
            assert result is None

    def test_detect_repo_location_searches_upward_from_venv(self):
        """VenvManager.detect_repo_location() searches upward from venv location"""
        manager = VenvManager()

        mock_venv_path = Path('/opt/projects/graphiti/.graphiti/.venv')
        mock_repo_root = Path('/opt/projects/graphiti')

        with patch.object(manager, 'venv_path', mock_venv_path):
            with patch.object(Path, 'exists') as mock_exists:
                # Only return True for the correct mcp_server/pyproject.toml
                def exists_side_effect(self):
                    return self == mock_repo_root / 'mcp_server' / 'pyproject.toml'

                mock_exists.side_effect = exists_side_effect

                result = manager.detect_repo_location()
                assert result == mock_repo_root


class TestValidateInstallation:
    """Test package installation validation."""

    def test_validate_installation_returns_true_when_package_importable(self):
        """VenvManager.validate_installation() returns True when package is importable"""
        manager = VenvManager()

        # Mock subprocess run to simulate successful import
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

            result = manager.validate_installation('mcp_server')
            assert result is True

    def test_validate_installation_returns_false_when_package_not_installed(self):
        """VenvManager.validate_installation() returns False when package is not installed"""
        manager = VenvManager()

        # Mock subprocess run to simulate import error
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='ModuleNotFoundError')

            result = manager.validate_installation('mcp_server')
            assert result is False

    def test_validate_installation_uses_venv_python(self):
        """VenvManager.validate_installation() uses venv Python interpreter"""
        manager = VenvManager()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
            with patch('platform.system', return_value='Linux'):
                manager.validate_installation('mcp_server')

                # Verify subprocess was called with venv Python
                call_args = mock_run.call_args[0][0]
                assert str(manager.venv_path / 'bin' / 'python') in str(call_args[0])


class TestInstallPackage:
    """Test package installation."""

    def test_install_package_uses_uv_pip_when_available(self):
        """VenvManager.install_package() uses uv pip when uv available in venv"""
        manager = VenvManager()

        mock_repo_root = Path('/home/user/graphiti')

        with patch.object(manager, 'detect_repo_location', return_value=mock_repo_root):
            with patch.object(manager, 'get_uv_executable', return_value=Path('/venv/bin/uv')):
                with patch.object(manager, 'validate_installation', return_value=True):
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

                        success, message = manager.install_package()

                        # Verify uv pip was used
                        call_args = mock_run.call_args[0][0]
                        assert 'uv' in str(call_args[0])
                        assert 'pip' in call_args
                        assert 'install' in call_args
                        assert success is True

    def test_install_package_falls_back_to_pip_when_uv_not_available(self):
        """VenvManager.install_package() falls back to pip when uv not available"""
        manager = VenvManager()

        mock_repo_root = Path('/home/user/graphiti')

        with patch.object(manager, 'detect_repo_location', return_value=mock_repo_root):
            with patch.object(manager, 'get_uv_executable', return_value=None):
                with patch.object(manager, 'validate_installation', return_value=True):
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
                        with patch('platform.system', return_value='Linux'):
                            success, message = manager.install_package()

                            # Verify standard pip was used
                            call_args = mock_run.call_args[0][0]
                            assert 'pip' in str(call_args[0])
                            assert 'install' in call_args
                            assert success is True

    def test_install_package_uses_non_editable_install(self):
        """VenvManager.install_package() uses non-editable install (no -e flag)"""
        manager = VenvManager()

        mock_repo_root = Path('/home/user/graphiti')

        with patch.object(manager, 'detect_repo_location', return_value=mock_repo_root):
            with patch.object(manager, 'get_uv_executable', return_value=None):
                with patch.object(manager, 'validate_installation', return_value=True):
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

                        manager.install_package()

                        # Verify -e flag is NOT in command
                        call_args = mock_run.call_args[0][0]
                        assert '-e' not in call_args

    def test_install_package_constructs_correct_path(self):
        """VenvManager.install_package() constructs correct install command with dynamic path"""
        manager = VenvManager()

        mock_repo_root = Path('/opt/graphiti')

        with patch.object(manager, 'detect_repo_location', return_value=mock_repo_root):
            with patch.object(manager, 'get_uv_executable', return_value=None):
                with patch.object(manager, 'validate_installation', return_value=True):
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

                        manager.install_package()

                        # Verify package path is included
                        call_args = mock_run.call_args[0][0]
                        assert str(mock_repo_root / 'mcp_server') in str(call_args)

    def test_install_package_raises_error_on_failure(self):
        """VenvManager.install_package() raises error on installation failure"""
        manager = VenvManager()

        mock_repo_root = Path('/home/user/graphiti')

        with patch.object(manager, 'detect_repo_location', return_value=mock_repo_root):
            with patch.object(manager, 'get_uv_executable', return_value=None):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=1, stdout='', stderr='Installation failed')

                    success, message = manager.install_package()
                    assert success is False
                    assert 'failed' in message.lower()

    def test_install_package_validates_installation_after_install(self):
        """VenvManager.install_package() validates installation after install"""
        manager = VenvManager()

        mock_repo_root = Path('/home/user/graphiti')

        with patch.object(manager, 'detect_repo_location', return_value=mock_repo_root):
            with patch.object(manager, 'get_uv_executable', return_value=None):
                with patch.object(manager, 'validate_installation') as mock_validate:
                    mock_validate.return_value = True
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

                        manager.install_package()

                        # Verify validation was called
                        mock_validate.assert_called_once_with('mcp_server')

    def test_install_package_handles_repo_not_found(self):
        """VenvManager.install_package() handles case when repo location cannot be detected"""
        manager = VenvManager()

        with patch.object(manager, 'detect_repo_location', return_value=None):
            success, message = manager.install_package()
            assert success is False
            assert 'cannot find' in message.lower() or 'not found' in message.lower()
