"""
Unit tests for WrapperGenerator CLI wrapper script generation.

Tests cover:
- Windows .cmd wrapper generation with correct Python path
- Unix shell script wrapper generation with correct Python path
- Executable permissions set on Unix scripts
- Script content validation (correct module invocation)
- Bin directory creation
- Error handling for missing venv
- Cross-platform wrapper generation
"""

import os
import stat
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pytest

from mcp_server.daemon.wrapper_generator import (
    WrapperGenerator,
    WrapperGenerationError,
)


class TestWrapperGeneration:
    """Test suite for CLI wrapper script generation."""

    @pytest.fixture
    def temp_paths(self, tmp_path):
        """Provide temporary paths for testing."""
        venv_path = tmp_path / ".venv"
        bin_path = tmp_path / "bin"
        return venv_path, bin_path

    @pytest.fixture
    def generator(self, temp_paths):
        """Create WrapperGenerator instance with temporary paths."""
        venv_path, bin_path = temp_paths
        return WrapperGenerator(venv_path=venv_path, bin_path=bin_path)

    @pytest.fixture
    def mock_venv(self, temp_paths):
        """Create mock venv structure."""
        venv_path, _ = temp_paths
        venv_path.mkdir(parents=True)

        if sys.platform == "win32":
            scripts_dir = venv_path / "Scripts"
            scripts_dir.mkdir()
            python_exe = scripts_dir / "python.exe"
        else:
            bin_dir = venv_path / "bin"
            bin_dir.mkdir()
            python_exe = bin_dir / "python"

        python_exe.touch()
        return python_exe

    def test_generate_windows_wrapper_creates_cmd_file(self, generator, mock_venv, temp_paths):
        """Test Windows wrapper generation creates .cmd file with correct content."""
        _, bin_path = temp_paths
        bin_path.mkdir(parents=True)

        with patch('sys.platform', 'win32'):
            python_path = generator.get_python_path()
            wrapper_path = generator.generate_windows_wrapper(
                "graphiti-mcp",
                "mcp_server.graphiti_mcp_server",
                python_path
            )

        assert wrapper_path.exists()
        assert wrapper_path.suffix == ".cmd"
        assert wrapper_path.name == "graphiti-mcp.cmd"

        # Verify content
        content = wrapper_path.read_text()
        assert "@echo off" in content
        assert str(python_path) in content
        assert "-m mcp_server.graphiti_mcp_server" in content
        assert "%*" in content  # Windows argument forwarding

    def test_generate_unix_wrapper_creates_shell_script(self, generator, mock_venv, temp_paths):
        """Test Unix wrapper generation creates shell script with correct content."""
        _, bin_path = temp_paths
        bin_path.mkdir(parents=True)

        with patch('sys.platform', 'linux'):
            python_path = generator.get_python_path()
            wrapper_path = generator.generate_unix_wrapper(
                "graphiti-mcp",
                "mcp_server.graphiti_mcp_server",
                python_path
            )

        assert wrapper_path.exists()
        assert wrapper_path.suffix == ""  # No extension on Unix scripts
        assert wrapper_path.name == "graphiti-mcp"

        # Verify content
        content = wrapper_path.read_text()
        assert "#!/bin/bash" in content or "#!/usr/bin/env bash" in content
        assert str(python_path) in content
        assert "-m mcp_server.graphiti_mcp_server" in content
        assert '"$@"' in content  # Unix argument forwarding

    def test_unix_wrapper_sets_executable_permissions(self, generator, mock_venv, temp_paths):
        """Test that Unix wrappers have executable permissions set."""
        _, bin_path = temp_paths
        bin_path.mkdir(parents=True)

        with patch('sys.platform', 'linux'):
            python_path = generator.get_python_path()
            wrapper_path = generator.generate_unix_wrapper(
                "graphiti-mcp",
                "mcp_server.graphiti_mcp_server",
                python_path
            )

        # Check file permissions
        file_stats = wrapper_path.stat()
        is_executable = bool(file_stats.st_mode & stat.S_IXUSR)

        assert is_executable, "Unix wrapper should have executable permissions"

    @pytest.mark.parametrize("command_name,module_path", [
        ("graphiti-mcp", "mcp_server.graphiti_mcp_server"),
        ("graphiti-bootstrap", "mcp_server.daemon.bootstrap"),
        ("graphiti-mcp-daemon", "mcp_server.daemon.manager"),
    ])
    def test_wrapper_content_correctness(self, generator, mock_venv, temp_paths, command_name, module_path):
        """Test wrapper content for different commands."""
        _, bin_path = temp_paths
        bin_path.mkdir(parents=True)

        python_path = generator.get_python_path()
        wrapper_path = generator.generate_windows_wrapper(
            command_name,
            module_path,
            python_path
        )

        content = wrapper_path.read_text()
        assert str(python_path) in content
        assert f"-m {module_path}" in content

    def test_get_python_path_windows(self, generator, temp_paths):
        """Test Python path detection on Windows."""
        venv_path, _ = temp_paths
        venv_path.mkdir(parents=True)
        scripts_dir = venv_path / "Scripts"
        scripts_dir.mkdir()
        python_exe = scripts_dir / "python.exe"
        python_exe.touch()

        with patch('sys.platform', 'win32'):
            python_path = generator.get_python_path()

        assert python_path == python_exe
        assert python_path.name == "python.exe"

    def test_get_python_path_unix(self, generator, temp_paths):
        """Test Python path detection on Unix."""
        venv_path, _ = temp_paths
        venv_path.mkdir(parents=True)
        bin_dir = venv_path / "bin"
        bin_dir.mkdir()
        python_exe = bin_dir / "python"
        python_exe.touch()

        with patch('sys.platform', 'linux'):
            python_path = generator.get_python_path()

        assert python_path == python_exe
        assert python_path.name == "python"

    def test_get_python_path_raises_on_missing_venv(self, generator):
        """Test error raised when venv doesn't exist."""
        with pytest.raises(WrapperGenerationError) as exc_info:
            generator.get_python_path()

        assert "does not exist" in str(exc_info.value).lower()
        assert "venv" in str(exc_info.value).lower()

    def test_get_python_path_raises_on_missing_python_exe(self, generator, temp_paths):
        """Test error raised when Python executable is missing in venv."""
        venv_path, _ = temp_paths
        venv_path.mkdir(parents=True)

        # Create venv structure but no python executable
        if sys.platform == "win32":
            (venv_path / "Scripts").mkdir()
        else:
            (venv_path / "bin").mkdir()

        with pytest.raises(WrapperGenerationError) as exc_info:
            generator.get_python_path()

        assert "python executable not found" in str(exc_info.value).lower()


class TestBinDirectoryCreation:
    """Test suite for bin directory management."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create WrapperGenerator instance."""
        return WrapperGenerator(
            venv_path=tmp_path / ".venv",
            bin_path=tmp_path / "bin"
        )

    def test_create_bin_directory_succeeds(self, generator, tmp_path):
        """Test bin directory creation."""
        generator.create_bin_directory()

        bin_path = tmp_path / "bin"
        assert bin_path.exists()
        assert bin_path.is_dir()

    def test_create_bin_directory_idempotent(self, generator, tmp_path):
        """Test that create_bin_directory can be called multiple times safely."""
        generator.create_bin_directory()
        generator.create_bin_directory()  # Should not raise

        bin_path = tmp_path / "bin"
        assert bin_path.exists()

    def test_create_bin_directory_creates_parents(self, tmp_path):
        """Test that parent directories are created if needed."""
        deep_bin_path = tmp_path / "a" / "b" / "c" / "bin"
        generator = WrapperGenerator(
            venv_path=tmp_path / ".venv",
            bin_path=deep_bin_path
        )

        generator.create_bin_directory()

        assert deep_bin_path.exists()
        assert deep_bin_path.is_dir()

    def test_create_bin_directory_handles_permission_error(self, generator, tmp_path):
        """Test error handling for permission denied."""
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Access denied")):
            with pytest.raises(WrapperGenerationError) as exc_info:
                generator.create_bin_directory()

            assert "failed to create" in str(exc_info.value).lower()
            assert "permission" in str(exc_info.value).lower()


class TestWrapperValidation:
    """Test suite for wrapper validation functionality."""

    @pytest.fixture
    def temp_paths(self, tmp_path):
        """Provide temporary paths for testing."""
        venv_path = tmp_path / ".venv"
        bin_path = tmp_path / "bin"
        return venv_path, bin_path

    @pytest.fixture
    def generator(self, temp_paths):
        """Create WrapperGenerator instance."""
        venv_path, bin_path = temp_paths
        return WrapperGenerator(venv_path=venv_path, bin_path=bin_path)

    @pytest.fixture
    def mock_venv(self, temp_paths):
        """Create mock venv structure."""
        venv_path, _ = temp_paths
        venv_path.mkdir(parents=True)

        if sys.platform == "win32":
            scripts_dir = venv_path / "Scripts"
            scripts_dir.mkdir()
            python_exe = scripts_dir / "python.exe"
        else:
            bin_dir = venv_path / "bin"
            bin_dir.mkdir()
            python_exe = bin_dir / "python"

        python_exe.touch()
        return python_exe

    def test_validate_wrapper_checks_file_exists(self, generator, mock_venv, temp_paths):
        """Test wrapper validation checks file existence."""
        _, bin_path = temp_paths
        bin_path.mkdir(parents=True)

        python_path = generator.get_python_path()
        wrapper_path = generator.generate_windows_wrapper(
            "graphiti-mcp",
            "mcp_server.graphiti_mcp_server",
            python_path
        )

        # Validation: file should exist
        assert wrapper_path.exists()

    def test_validate_wrapper_checks_content_format(self, generator, mock_venv, temp_paths):
        """Test wrapper validation checks content correctness."""
        _, bin_path = temp_paths
        bin_path.mkdir(parents=True)

        python_path = generator.get_python_path()
        wrapper_path = generator.generate_windows_wrapper(
            "graphiti-mcp",
            "mcp_server.graphiti_mcp_server",
            python_path
        )

        content = wrapper_path.read_text()

        # Validation: content must contain Python path and module invocation
        assert str(python_path) in content
        assert "-m mcp_server.graphiti_mcp_server" in content

    def test_wrapper_handles_spaces_in_path(self, tmp_path):
        """Test that wrappers handle spaces in Python path correctly."""
        # Create venv in path with spaces
        venv_path = tmp_path / "My Venv" / ".venv"
        bin_path = tmp_path / "bin"
        venv_path.mkdir(parents=True)

        if sys.platform == "win32":
            scripts_dir = venv_path / "Scripts"
            scripts_dir.mkdir()
            python_exe = scripts_dir / "python.exe"
        else:
            bin_dir = venv_path / "bin"
            bin_dir.mkdir()
            python_exe = bin_dir / "python"

        python_exe.touch()
        bin_path.mkdir(parents=True)

        generator = WrapperGenerator(venv_path=venv_path, bin_path=bin_path)
        python_path = generator.get_python_path()
        wrapper_path = generator.generate_windows_wrapper(
            "graphiti-mcp",
            "mcp_server.graphiti_mcp_server",
            python_path
        )

        content = wrapper_path.read_text()

        # On Windows, paths with spaces should be quoted
        if sys.platform == "win32":
            assert f'"{python_path}"' in content
        else:
            # Unix wrappers should also quote paths
            assert f'"{python_path}"' in content or f"'{python_path}'" in content


class TestGenerateAllWrappers:
    """Test suite for batch wrapper generation."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create WrapperGenerator instance."""
        venv_path = tmp_path / ".venv"
        bin_path = tmp_path / "bin"

        # Create mock venv
        venv_path.mkdir(parents=True)
        if sys.platform == "win32":
            scripts_dir = venv_path / "Scripts"
            scripts_dir.mkdir()
            (scripts_dir / "python.exe").touch()
        else:
            bin_dir = venv_path / "bin"
            bin_dir.mkdir()
            (bin_dir / "python").touch()

        return WrapperGenerator(venv_path=venv_path, bin_path=bin_path)

    def test_generate_all_commands(self, generator):
        """Test that all commands in COMMANDS dict get wrappers generated."""
        generator.create_bin_directory()
        python_path = generator.get_python_path()

        generated_wrappers = []
        for command_name, module_path in generator.COMMANDS.items():
            if sys.platform == "win32":
                wrapper_path = generator.generate_windows_wrapper(
                    command_name, module_path, python_path
                )
            else:
                wrapper_path = generator.generate_unix_wrapper(
                    command_name, module_path, python_path
                )
            generated_wrappers.append(wrapper_path)

        assert len(generated_wrappers) == len(generator.COMMANDS)
        for wrapper in generated_wrappers:
            assert wrapper.exists()
