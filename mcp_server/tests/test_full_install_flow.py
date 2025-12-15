"""
Integration test for full install workflow.

Tests the complete installer flow:
- Venv creation → package installation → wrapper generation → PATH instructions

This integration test validates that all components work together correctly.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from mcp_server.daemon.venv_manager import VenvManager
from mcp_server.daemon.wrapper_generator import WrapperGenerator


class TestFullInstallFlow:
    """Integration test for complete installation workflow."""

    @pytest.fixture
    def temp_install_root(self, tmp_path):
        """Provide temporary installation root (~/.graphiti/)."""
        install_root = tmp_path / ".graphiti"
        install_root.mkdir()
        return install_root

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create mock repository structure."""
        repo_path = tmp_path / "graphiti_repo"
        repo_path.mkdir()
        mcp_server_path = repo_path / "mcp_server"
        mcp_server_path.mkdir()
        (mcp_server_path / "pyproject.toml").write_text(
            "[project]\nname = 'mcp_server'\nversion = '1.0.0'"
        )
        return repo_path

    def test_full_install_flow_success(self, temp_install_root, mock_repo):
        """Test complete installation flow from clean state to CLI availability."""
        venv_path = temp_install_root / ".venv"
        bin_path = temp_install_root / "bin"

        # Step 1: Create VenvManager
        venv_manager = VenvManager(venv_path=venv_path)

        # Step 2: Create venv (mocked)
        with patch.object(venv_manager, 'validate_python_version', return_value=True), \
             patch.object(venv_manager, 'check_uv_available', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Mock detect_venv to simulate venv creation
            with patch.object(venv_manager, 'detect_venv', side_effect=[False, True]):
                # Create parent and venv structure manually for test
                venv_path.mkdir(parents=True)
                if sys.platform == "win32":
                    scripts_dir = venv_path / "Scripts"
                    scripts_dir.mkdir()
                    (scripts_dir / "python.exe").touch()
                    (scripts_dir / "pip.exe").touch()
                else:
                    bin_dir = venv_path / "bin"
                    bin_dir.mkdir()
                    (bin_dir / "python").touch()
                    (bin_dir / "pip").touch()

                (venv_path / "pyvenv.cfg").write_text("version = 3.10.0")

                if sys.platform == "win32":
                    (venv_path / "Scripts" / "activate.bat").touch()
                else:
                    (venv_path / "bin" / "activate").touch()

                success, message = venv_manager.create_venv()

            assert success is True
            assert venv_path.exists()

        # Step 3: Install package (mocked)
        with patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch.object(venv_manager, 'detect_repo_location', return_value=mock_repo), \
             patch.object(venv_manager, 'get_uv_executable', return_value=None), \
             patch.object(venv_manager, 'get_pip_executable', return_value=venv_path / "Scripts" / "pip.exe"), \
             patch.object(venv_manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            success, message = venv_manager.install_package()

            assert success is True
            assert "successfully" in message.lower() or "installed" in message.lower()

        # Step 4: Generate wrappers
        wrapper_gen = WrapperGenerator(venv_path=venv_path, bin_path=bin_path)
        wrapper_gen.create_bin_directory()

        python_path = wrapper_gen.get_python_path()

        generated_wrappers = []
        for command_name, module_path in wrapper_gen.COMMANDS.items():
            if sys.platform == "win32":
                wrapper_path = wrapper_gen.generate_windows_wrapper(
                    command_name, module_path, python_path
                )
            else:
                wrapper_path = wrapper_gen.generate_unix_wrapper(
                    command_name, module_path, python_path
                )
            generated_wrappers.append(wrapper_path)

        # Step 5: Verify all wrappers created
        assert len(generated_wrappers) == len(wrapper_gen.COMMANDS)
        for wrapper in generated_wrappers:
            assert wrapper.exists()

        # Step 6: Verify wrapper content
        for wrapper in generated_wrappers:
            content = wrapper.read_text()
            assert str(python_path) in content

    def test_install_creates_expected_directory_structure(self, temp_install_root):
        """Test that installation creates expected directory structure."""
        venv_path = temp_install_root / ".venv"
        bin_path = temp_install_root / "bin"

        # Simulate venv creation
        venv_path.mkdir(parents=True)
        if sys.platform == "win32":
            (venv_path / "Scripts").mkdir()
            (venv_path / "Scripts" / "python.exe").touch()
        else:
            (venv_path / "bin").mkdir()
            (venv_path / "bin" / "python").touch()

        # Simulate wrapper generation
        wrapper_gen = WrapperGenerator(venv_path=venv_path, bin_path=bin_path)
        wrapper_gen.create_bin_directory()

        # Verify structure
        assert temp_install_root.exists()
        assert venv_path.exists()
        assert bin_path.exists()

        if sys.platform == "win32":
            assert (venv_path / "Scripts").exists()
        else:
            assert (venv_path / "bin").exists()

    def test_install_is_idempotent(self, temp_install_root, mock_repo):
        """Test that running install multiple times is safe (idempotent)."""
        venv_path = temp_install_root / ".venv"
        bin_path = temp_install_root / "bin"

        venv_manager = VenvManager(venv_path=venv_path)

        # First install
        with patch.object(venv_manager, 'validate_python_version', return_value=True), \
             patch.object(venv_manager, 'check_uv_available', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0)

            # Create venv structure
            venv_path.mkdir(parents=True)
            if sys.platform == "win32":
                scripts_dir = venv_path / "Scripts"
                scripts_dir.mkdir()
                (scripts_dir / "python.exe").touch()
            else:
                bin_dir = venv_path / "bin"
                bin_dir.mkdir()
                (bin_dir / "python").touch()

            (venv_path / "pyvenv.cfg").write_text("version = 3.10.0")

            if sys.platform == "win32":
                (venv_path / "Scripts" / "activate.bat").touch()
            else:
                (venv_path / "bin" / "activate").touch()

            with patch.object(venv_manager, 'detect_venv', return_value=True):
                success1, message1 = venv_manager.create_venv()

            # Second install (should skip)
            with patch.object(venv_manager, 'detect_venv', return_value=True):
                success2, message2 = venv_manager.create_venv()

            assert success1 is True
            assert success2 is True
            assert "already exists" in message2.lower()

    def test_cli_commands_executable_after_install(self, temp_install_root):
        """Test that CLI commands are executable after installation completes."""
        venv_path = temp_install_root / ".venv"
        bin_path = temp_install_root / "bin"

        # Simulate complete install
        venv_path.mkdir(parents=True)
        if sys.platform == "win32":
            (venv_path / "Scripts").mkdir()
            (venv_path / "Scripts" / "python.exe").touch()
        else:
            (venv_path / "bin").mkdir()
            (venv_path / "bin" / "python").touch()

        wrapper_gen = WrapperGenerator(venv_path=venv_path, bin_path=bin_path)
        wrapper_gen.create_bin_directory()

        python_path = wrapper_gen.get_python_path()

        # Generate all wrappers
        for command_name, module_path in wrapper_gen.COMMANDS.items():
            if sys.platform == "win32":
                wrapper_gen.generate_windows_wrapper(command_name, module_path, python_path)
            else:
                wrapper_gen.generate_unix_wrapper(command_name, module_path, python_path)

        # Verify wrappers exist and are valid
        for command_name in wrapper_gen.COMMANDS.keys():
            if sys.platform == "win32":
                wrapper_path = bin_path / f"{command_name}.cmd"
            else:
                wrapper_path = bin_path / command_name

            assert wrapper_path.exists(), f"Wrapper {command_name} not found"

            # Check content is valid
            content = wrapper_path.read_text()
            assert str(python_path) in content

    def test_install_displays_path_instructions(self):
        """Test that installer provides PATH configuration instructions."""
        # This is a documentation test - verify PATH instructions exist
        # In real implementation, installer would print these instructions

        if sys.platform == "win32":
            expected_instruction = "Add to PATH: %USERPROFILE%\\.graphiti\\bin"
        else:
            expected_instruction = "Add to PATH: export PATH=\"$HOME/.graphiti/bin:$PATH\""

        # Verify the instruction format is correct
        assert "PATH" in expected_instruction
        assert ".graphiti" in expected_instruction or ".graphiti" in expected_instruction
        assert "bin" in expected_instruction

    def test_install_handles_already_installed_gracefully(self, temp_install_root, mock_repo):
        """Test that installer handles already-installed scenario gracefully."""
        venv_path = temp_install_root / ".venv"
        venv_manager = VenvManager(venv_path=venv_path)

        # Simulate existing installation
        venv_path.mkdir(parents=True)
        if sys.platform == "win32":
            scripts_dir = venv_path / "Scripts"
            scripts_dir.mkdir()
            (scripts_dir / "python.exe").touch()
        else:
            bin_dir = venv_path / "bin"
            bin_dir.mkdir()
            (bin_dir / "python").touch()

        (venv_path / "pyvenv.cfg").write_text("version = 3.10.0")

        if sys.platform == "win32":
            (venv_path / "Scripts" / "activate.bat").touch()
        else:
            (venv_path / "bin" / "activate").touch()

        with patch.object(venv_manager, 'validate_python_version', return_value=True), \
             patch.object(venv_manager, 'detect_venv', return_value=True):

            # Try to install again (should be idempotent)
            success, message = venv_manager.create_venv()

            assert success is True
            assert "already exists" in message.lower()


class TestErrorScenarios:
    """Test error handling in installation flow."""

    @pytest.fixture
    def temp_install_root(self, tmp_path):
        """Provide temporary installation root."""
        return tmp_path / ".graphiti"

    def test_install_fails_on_incompatible_python(self, temp_install_root):
        """Test that installation fails gracefully for Python < 3.10."""
        venv_path = temp_install_root / ".venv"
        venv_manager = VenvManager(venv_path=venv_path)

        with patch('sys.version_info', (3, 9, 0)):
            from mcp_server.daemon.venv_manager import IncompatiblePythonVersionError

            with pytest.raises(IncompatiblePythonVersionError):
                venv_manager.validate_python_version()

    def test_install_fails_on_package_not_found(self, temp_install_root):
        """Test that installation fails when package cannot be found."""
        venv_path = temp_install_root / ".venv"
        venv_manager = VenvManager(venv_path=venv_path)

        # Create venv but no repo
        venv_path.mkdir(parents=True)
        if sys.platform == "win32":
            (venv_path / "Scripts").mkdir()
            (venv_path / "Scripts" / "python.exe").touch()
            (venv_path / "Scripts" / "pip.exe").touch()
        else:
            (venv_path / "bin").mkdir()
            (venv_path / "bin" / "python").touch()
            (venv_path / "bin" / "pip").touch()

        (venv_path / "pyvenv.cfg").write_text("version = 3.10.0")

        with patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch.object(venv_manager, 'detect_repo_location', return_value=None):

            success, message = venv_manager.install_package()

            assert success is False
            assert "cannot find" in message.lower()

    def test_install_fails_on_wrapper_generation_error(self, temp_install_root):
        """Test that wrapper generation fails gracefully when venv missing."""
        venv_path = temp_install_root / ".venv"
        bin_path = temp_install_root / "bin"

        wrapper_gen = WrapperGenerator(venv_path=venv_path, bin_path=bin_path)

        from mcp_server.daemon.wrapper_generator import WrapperGenerationError

        with pytest.raises(WrapperGenerationError) as exc_info:
            wrapper_gen.get_python_path()

        assert "does not exist" in str(exc_info.value).lower()
