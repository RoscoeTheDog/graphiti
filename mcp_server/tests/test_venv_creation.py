"""
Unit tests for VenvManager venv creation and detection functionality.

Tests cover:
- Venv creation with uv (preferred)
- Fallback to python -m venv when uv unavailable
- Venv detection (valid/invalid scenarios)
- Force recreation of existing venvs
- Python version validation (requires >=3.10)
- Error handling for subprocess failures
"""

import sys
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from mcp_server.daemon.venv_manager import (
    VenvManager,
    VenvCreationError,
    IncompatiblePythonVersionError,
)


class TestVenvCreation:
    """Test suite for VenvManager.create_venv() functionality."""

    @pytest.fixture
    def temp_venv_path(self, tmp_path):
        """Provide a temporary venv path for testing."""
        return tmp_path / "test_venv"

    @pytest.fixture
    def manager(self, temp_venv_path):
        """Create VenvManager instance with temporary path."""
        return VenvManager(venv_path=temp_venv_path)

    def test_create_venv_with_uv(self, manager, temp_venv_path):
        """Test venv creation using uv (preferred method)."""
        with patch.object(manager, 'check_uv_available', return_value=True), \
             patch.object(manager, 'validate_python_version', return_value=True), \
             patch('subprocess.run') as mock_run, \
             patch.object(manager, 'detect_venv', side_effect=[False, True]):

            mock_run.return_value = Mock(returncode=0)

            success, message = manager.create_venv()

            assert success is True
            assert "uv" in message.lower()
            mock_run.assert_called_once()
            # Verify uv command was used
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "uv"
            assert "venv" in call_args

    def test_create_venv_fallback_to_python(self, manager, temp_venv_path):
        """Test fallback to python -m venv when uv unavailable."""
        with patch.object(manager, 'check_uv_available', return_value=False), \
             patch.object(manager, 'validate_python_version', return_value=True), \
             patch('subprocess.run') as mock_run, \
             patch.object(manager, 'detect_venv', side_effect=[False, True]):

            mock_run.return_value = Mock(returncode=0)

            success, message = manager.create_venv()

            assert success is True
            assert "python" in message.lower()
            mock_run.assert_called_once()
            # Verify python -m venv command was used
            call_args = mock_run.call_args[0][0]
            assert sys.executable in call_args
            assert "-m" in call_args
            assert "venv" in call_args

    def test_create_venv_skips_if_exists(self, manager, temp_venv_path):
        """Test that create_venv skips creation if venv already exists."""
        with patch.object(manager, 'validate_python_version', return_value=True), \
             patch.object(manager, 'detect_venv', return_value=True), \
             patch('subprocess.run') as mock_run:

            success, message = manager.create_venv()

            assert success is True
            assert "already exists" in message.lower()
            mock_run.assert_not_called()

    def test_create_venv_force_recreates(self, manager, temp_venv_path):
        """Test force=True recreates existing venv."""
        with patch.object(manager, 'validate_python_version', return_value=True), \
             patch.object(manager, 'detect_venv', side_effect=[True, False, True]), \
             patch.object(manager, 'check_uv_available', return_value=True), \
             patch('shutil.rmtree') as mock_rmtree, \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0)

            success, message = manager.create_venv(force=True)

            assert success is True
            assert "recreat" in message.lower() or "created" in message.lower()
            mock_rmtree.assert_called_once_with(temp_venv_path)
            mock_run.assert_called_once()

    def test_create_venv_raises_on_incompatible_python(self, manager):
        """Test error raised for Python < 3.10."""
        with patch.object(manager, 'validate_python_version', side_effect=IncompatiblePythonVersionError("Python 3.10+ required")):

            with pytest.raises(IncompatiblePythonVersionError) as exc_info:
                manager.create_venv()

            assert "3.10" in str(exc_info.value)

    def test_create_venv_raises_on_subprocess_failure(self, manager, temp_venv_path):
        """Test error handling when subprocess fails."""
        with patch.object(manager, 'validate_python_version', return_value=True), \
             patch.object(manager, 'detect_venv', return_value=False), \
             patch.object(manager, 'check_uv_available', return_value=True), \
             patch('subprocess.run') as mock_run:

            # Simulate subprocess failure
            mock_run.side_effect = subprocess.CalledProcessError(1, "uv")

            with pytest.raises(VenvCreationError) as exc_info:
                manager.create_venv()

            assert "failed" in str(exc_info.value).lower()


class TestVenvDetection:
    """Test suite for VenvManager.detect_venv() functionality."""

    @pytest.fixture
    def temp_venv_path(self, tmp_path):
        """Provide a temporary venv path for testing."""
        return tmp_path / "test_venv"

    @pytest.fixture
    def manager(self, temp_venv_path):
        """Create VenvManager instance with temporary path."""
        return VenvManager(venv_path=temp_venv_path)

    def test_detect_venv_not_exists(self, manager, temp_venv_path):
        """Test detection fails when venv directory doesn't exist."""
        assert manager.detect_venv() is False

    def test_detect_venv_missing_pyvenv_cfg(self, manager, temp_venv_path):
        """Test detection fails when pyvenv.cfg is missing."""
        temp_venv_path.mkdir(parents=True)
        assert manager.detect_venv() is False

    def test_detect_venv_missing_activate_script(self, manager, temp_venv_path):
        """Test detection fails when activate script is missing."""
        temp_venv_path.mkdir(parents=True)
        (temp_venv_path / "pyvenv.cfg").touch()
        assert manager.detect_venv() is False

    @pytest.mark.parametrize("platform,activate_path", [
        ("win32", "Scripts/activate.bat"),
        ("linux", "bin/activate"),
        ("darwin", "bin/activate"),
    ])
    def test_detect_venv_valid_platform_specific(self, manager, temp_venv_path, platform, activate_path):
        """Test detection succeeds for valid venv (platform-specific activate scripts)."""
        temp_venv_path.mkdir(parents=True)
        (temp_venv_path / "pyvenv.cfg").write_text("version = 3.10.0")

        activate_file = temp_venv_path / activate_path
        activate_file.parent.mkdir(parents=True, exist_ok=True)
        activate_file.touch()

        with patch('sys.platform', platform):
            assert manager.detect_venv() is True

    def test_detect_venv_reports_valid_venv(self, manager, temp_venv_path):
        """Test that detect_venv correctly identifies a complete, valid venv."""
        # Create minimal valid venv structure
        temp_venv_path.mkdir(parents=True)
        (temp_venv_path / "pyvenv.cfg").write_text("home = /usr/bin\nversion = 3.10.0")

        if sys.platform == "win32":
            scripts_dir = temp_venv_path / "Scripts"
            scripts_dir.mkdir()
            (scripts_dir / "activate.bat").touch()
        else:
            bin_dir = temp_venv_path / "bin"
            bin_dir.mkdir()
            (bin_dir / "activate").touch()

        assert manager.detect_venv() is True


class TestPythonVersionValidation:
    """Test suite for Python version compatibility checks."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create VenvManager instance."""
        return VenvManager(venv_path=tmp_path / "test_venv")

    def test_validate_python_version_success(self, manager):
        """Test validation passes for Python >= 3.10."""
        with patch('sys.version_info', (3, 10, 0)):
            assert manager.validate_python_version() is True

    def test_validate_python_version_failure_39(self, manager):
        """Test validation fails for Python 3.9."""
        with patch('sys.version_info', (3, 9, 0)):
            with pytest.raises(IncompatiblePythonVersionError) as exc_info:
                manager.validate_python_version()
            assert "3.10" in str(exc_info.value)
            assert "3.9" in str(exc_info.value)

    def test_validate_python_version_failure_27(self, manager):
        """Test validation fails for Python 2.7."""
        with patch('sys.version_info', (2, 7, 0)):
            with pytest.raises(IncompatiblePythonVersionError) as exc_info:
                manager.validate_python_version()
            assert "3.10" in str(exc_info.value)


class TestUvAvailabilityCheck:
    """Test suite for uv availability detection."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create VenvManager instance."""
        return VenvManager(venv_path=tmp_path / "test_venv")

    def test_check_uv_available_found(self, manager):
        """Test uv detection when uv is in PATH."""
        with patch('shutil.which', return_value="/usr/bin/uv"):
            assert manager.check_uv_available() is True

    def test_check_uv_available_not_found(self, manager):
        """Test uv detection when uv is not in PATH."""
        with patch('shutil.which', return_value=None):
            assert manager.check_uv_available() is False
