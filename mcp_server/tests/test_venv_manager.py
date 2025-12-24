"""
Unit tests for VenvManager with requirements.txt-based installation.

Tests cover:
- Installation from ~/.graphiti/requirements.txt
- Tool preference order: uvx → uv pip → pip
- Error handling for missing/malformed requirements.txt
- Platform-agnostic path handling
- Installation validation
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from mcp_server.daemon.venv_manager import VenvManager, VenvCreationError


class TestVenvManagerInstallPackage:
    """Test VenvManager.install_package() with requirements.txt."""

    @pytest.fixture
    def temp_venv_path(self, tmp_path):
        """Create temporary venv path."""
        venv_path = tmp_path / ".graphiti" / ".venv"
        venv_path.mkdir(parents=True)

        # Create venv structure
        if sys.platform == "win32":
            scripts_dir = venv_path / "Scripts"
            scripts_dir.mkdir()
            (scripts_dir / "python.exe").touch()
            (scripts_dir / "pip.exe").touch()
            (scripts_dir / "activate.bat").touch()
        else:
            bin_dir = venv_path / "bin"
            bin_dir.mkdir()
            (bin_dir / "python").touch()
            (bin_dir / "pip").touch()
            (bin_dir / "activate").touch()

        (venv_path / "pyvenv.cfg").write_text("version = 3.10.0\n")

        return venv_path

    @pytest.fixture
    def mock_requirements_txt(self, tmp_path):
        """Create mock requirements.txt file."""
        req_file = tmp_path / ".graphiti" / "requirements.txt"
        req_file.parent.mkdir(parents=True, exist_ok=True)
        req_file.write_text(
            "mcp>=1.9.4\n"
            "openai>=1.91.0\n"
            "graphiti-core>=0.23.1\n"
        )
        return req_file

    def test_install_package_with_uvx(self, temp_venv_path, tmp_path):
        """Test install_package() uses uvx when available."""
        venv_manager = VenvManager(venv_path=temp_venv_path)

        # Mock requirements.txt exists
        req_path = tmp_path / ".graphiti" / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_path.write_text("mcp>=1.9.4\n")

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch('shutil.which', return_value='/usr/local/bin/uvx'), \
             patch.object(venv_manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            success, message = venv_manager.install_package()

            assert success is True
            assert "uvx" in message.lower()

            # Verify subprocess was called with uvx command
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == '/usr/local/bin/uvx'
            assert call_args[1] == 'pip'
            assert call_args[2] == 'install'
            assert '-r' in call_args
            assert str(req_path) in call_args

    def test_install_package_with_uv_pip(self, temp_venv_path, tmp_path):
        """Test install_package() uses uv pip when uvx not available."""
        venv_manager = VenvManager(venv_path=temp_venv_path)

        # Mock requirements.txt exists
        req_path = tmp_path / ".graphiti" / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_path.write_text("mcp>=1.9.4\n")

        # Create mock uv executable in venv
        if sys.platform == "win32":
            uv_exe = temp_venv_path / "Scripts" / "uv.exe"
        else:
            uv_exe = temp_venv_path / "bin" / "uv"
        uv_exe.parent.mkdir(parents=True, exist_ok=True)
        uv_exe.touch()

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch('shutil.which', return_value=None), \
             patch.object(venv_manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            success, message = venv_manager.install_package()

            assert success is True
            assert "uv pip" in message.lower()

            # Verify subprocess was called with uv pip command
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert str(uv_exe) == call_args[0]
            assert call_args[1] == 'pip'
            assert call_args[2] == 'install'

    def test_install_package_with_standard_pip(self, temp_venv_path, tmp_path):
        """Test install_package() falls back to standard pip."""
        venv_manager = VenvManager(venv_path=temp_venv_path)

        # Mock requirements.txt exists
        req_path = tmp_path / ".graphiti" / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_path.write_text("mcp>=1.9.4\n")

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch('shutil.which', return_value=None), \
             patch.object(venv_manager, 'get_uv_executable', return_value=None), \
             patch.object(venv_manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            success, message = venv_manager.install_package()

            assert success is True
            # Message should indicate pip (not uvx or uv pip)
            assert "pip" in message.lower()

            # Verify subprocess was called with pip install -r
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert 'install' in call_args
            assert '-r' in call_args
            assert str(req_path) in call_args

    def test_install_package_missing_requirements_txt(self, temp_venv_path, tmp_path):
        """Test install_package() raises error if requirements.txt missing."""
        venv_manager = VenvManager(venv_path=temp_venv_path)

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch.object(venv_manager, 'detect_venv', return_value=True):

            success, error_msg = venv_manager.install_package()

            assert success is False
            assert "Requirements file not found" in error_msg
            assert str(tmp_path / ".graphiti" / "requirements.txt") in error_msg
            assert "installation process first" in error_msg

    def test_install_package_validates_mcp_server_importable(self, temp_venv_path, tmp_path):
        """Test install_package() validates mcp_server is importable after installation."""
        venv_manager = VenvManager(venv_path=temp_venv_path)

        # Mock requirements.txt exists
        req_path = tmp_path / ".graphiti" / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_path.write_text("mcp>=1.9.4\n")

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch('shutil.which', return_value=None), \
             patch.object(venv_manager, 'get_uv_executable', return_value=None), \
             patch('subprocess.run') as mock_run:

            # Mock installation subprocess success
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Mock validation failure
            with patch.object(venv_manager, 'validate_installation', return_value=False):
                success, error_msg = venv_manager.install_package()

                assert success is False
                assert "validation failed" in error_msg.lower()
                assert "not importable" in error_msg.lower()

    def test_install_package_error_handling(self, temp_venv_path, tmp_path):
        """Test install_package() returns proper error message if installation fails."""
        venv_manager = VenvManager(venv_path=temp_venv_path)

        # Mock requirements.txt exists
        req_path = tmp_path / ".graphiti" / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_path.write_text("mcp>=1.9.4\n")

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch('shutil.which', return_value=None), \
             patch.object(venv_manager, 'get_uv_executable', return_value=None), \
             patch('subprocess.run') as mock_run:

            # Mock installation failure
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="ERROR: Could not find version 99.99.99"
            )

            success, error_msg = venv_manager.install_package()

            assert success is False
            assert "Package installation failed" in error_msg
            assert "exit code 1" in error_msg
            assert "ERROR: Could not find version" in error_msg

    def test_install_package_uses_correct_command(self, temp_venv_path, tmp_path):
        """Test install_package() uses correct command: 'pip install -r ~/.graphiti/requirements.txt'."""
        venv_manager = VenvManager(venv_path=temp_venv_path)

        # Mock requirements.txt exists
        req_path = tmp_path / ".graphiti" / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_path.write_text("mcp>=1.9.4\n")

        with patch('pathlib.Path.home', return_value=tmp_path), \
             patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch('shutil.which', return_value=None), \
             patch.object(venv_manager, 'get_uv_executable', return_value=None), \
             patch.object(venv_manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            venv_manager.install_package()

            # Verify subprocess call
            mock_run.assert_called_once()
            call_args, call_kwargs = mock_run.call_args

            # Check command arguments
            cmd = call_args[0]
            assert 'install' in cmd
            assert '-r' in cmd
            assert str(req_path) in cmd
            assert '--quiet' in cmd

            # Check no cwd is specified (requirements.txt has absolute path)
            assert 'cwd' not in call_kwargs or call_kwargs['cwd'] is None

    def test_path_resolution_uses_path_home(self, temp_venv_path, tmp_path):
        """Test path resolution uses Path.home() for cross-platform compatibility."""
        venv_manager = VenvManager(venv_path=temp_venv_path)

        # Mock requirements.txt exists
        req_path = tmp_path / ".graphiti" / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_path.write_text("mcp>=1.9.4\n")

        with patch('pathlib.Path.home', return_value=tmp_path) as mock_home, \
             patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch('shutil.which', return_value=None), \
             patch.object(venv_manager, 'get_uv_executable', return_value=None), \
             patch.object(venv_manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            venv_manager.install_package()

            # Verify Path.home() was called to construct requirements path
            mock_home.assert_called()

    def test_install_package_no_venv(self, tmp_path):
        """Test install_package() raises error if venv doesn't exist."""
        venv_path = tmp_path / ".graphiti" / ".venv"
        venv_manager = VenvManager(venv_path=venv_path)

        # Venv doesn't exist
        with pytest.raises(VenvCreationError) as exc_info:
            venv_manager.install_package()

        assert "Venv does not exist" in str(exc_info.value)
        assert "create_venv()" in str(exc_info.value)


class TestVenvManagerIntegration:
    """Integration tests for VenvManager with real ~/.graphiti/requirements.txt file."""

    def test_install_package_integration_with_real_requirements(self, tmp_path):
        """Test install_package() with real ~/.graphiti/requirements.txt file."""
        # This would require setting up a real venv and requirements.txt
        # For now, this is a placeholder for future integration tests
        pass
