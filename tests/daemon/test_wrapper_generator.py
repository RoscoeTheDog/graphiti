"""
Integration Tests for WrapperGenerator

Tests the CLI wrapper script generation functionality:
- Wrapper creation (Windows .cmd and Unix shell scripts)
- Platform-specific path handling
- Executable permissions
- Validation and cleanup
- Error handling

Uses temp directories to test real file operations instead of mocking.
"""

import sys
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.daemon.wrapper_generator import (
    WrapperGenerator,
    WrapperGenerationError,
)


@pytest.fixture
def temp_venv(tmp_path):
    """Create a temporary venv structure for testing."""
    venv_path = tmp_path / ".venv"

    # Create venv structure based on platform
    if sys.platform == "win32":
        scripts_dir = venv_path / "Scripts"
        scripts_dir.mkdir(parents=True)
        python_exe = scripts_dir / "python.exe"
        python_exe.write_text("fake python exe")  # Create fake file
    else:
        bin_dir = venv_path / "bin"
        bin_dir.mkdir(parents=True)
        python_exe = bin_dir / "python"
        python_exe.write_text("#!/usr/bin/env python3")
        python_exe.chmod(0o755)

    return venv_path


@pytest.fixture
def temp_bin(tmp_path):
    """Create a temporary bin directory for testing."""
    return tmp_path / "bin"


class TestWrapperGeneratorBasics:
    """Test basic WrapperGenerator functionality."""

    def test_init_with_default_paths(self):
        """WrapperGenerator uses default paths when none provided"""
        generator = WrapperGenerator()

        # Should use ~/.graphiti/.venv and ~/.graphiti/bin
        assert generator.venv_path == Path.home() / ".graphiti" / ".venv"
        assert generator.bin_path == Path.home() / ".graphiti" / "bin"

    def test_init_with_custom_paths(self, temp_venv, temp_bin):
        """WrapperGenerator accepts custom venv and bin paths"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)

        assert generator.venv_path == temp_venv
        assert generator.bin_path == temp_bin

    def test_get_python_path_returns_correct_path_for_platform(self, temp_venv):
        """get_python_path() returns platform-specific Python path"""
        generator = WrapperGenerator(venv_path=temp_venv)

        python_path = generator.get_python_path()

        if sys.platform == "win32":
            assert python_path == temp_venv / "Scripts" / "python.exe"
        else:
            assert python_path == temp_venv / "bin" / "python"

        assert python_path.exists()

    def test_get_python_path_raises_error_when_venv_missing(self, tmp_path):
        """get_python_path() raises WrapperGenerationError when venv doesn't exist"""
        nonexistent_venv = tmp_path / "nonexistent"
        generator = WrapperGenerator(venv_path=nonexistent_venv)

        with pytest.raises(WrapperGenerationError) as exc_info:
            generator.get_python_path()

        assert "does not exist" in str(exc_info.value).lower()

    def test_create_bin_directory_creates_directory(self, temp_bin):
        """create_bin_directory() creates bin directory"""
        generator = WrapperGenerator(bin_path=temp_bin)

        assert not temp_bin.exists()
        generator.create_bin_directory()
        assert temp_bin.exists()
        assert temp_bin.is_dir()

    def test_create_bin_directory_is_idempotent(self, temp_bin):
        """create_bin_directory() can be called multiple times safely"""
        generator = WrapperGenerator(bin_path=temp_bin)

        generator.create_bin_directory()
        generator.create_bin_directory()  # Should not raise

        assert temp_bin.exists()


class TestWindowsWrapperGeneration:
    """Test Windows .cmd wrapper generation."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_generate_windows_wrapper_creates_cmd_file(self, temp_venv, temp_bin):
        """generate_windows_wrapper() creates .cmd file on Windows"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)
        generator.create_bin_directory()
        python_path = generator.get_python_path()

        wrapper_path = generator.generate_windows_wrapper(
            "graphiti-mcp", "mcp_server.graphiti_mcp_server", python_path
        )

        assert wrapper_path.exists()
        assert wrapper_path.name == "graphiti-mcp.cmd"
        assert wrapper_path.parent == temp_bin

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_windows_wrapper_contains_correct_content(self, temp_venv, temp_bin):
        """Windows wrapper contains correct batch script content"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)
        generator.create_bin_directory()
        python_path = generator.get_python_path()

        wrapper_path = generator.generate_windows_wrapper(
            "graphiti-mcp", "mcp_server.graphiti_mcp_server", python_path
        )

        content = wrapper_path.read_text()

        # Should contain batch header
        assert "@echo off" in content

        # Should contain absolute path to Python
        assert str(python_path) in content

        # Should contain module invocation
        assert "-m mcp_server.graphiti_mcp_server" in content

        # Should forward arguments with %*
        assert "%*" in content


class TestUnixWrapperGeneration:
    """Test Unix shell wrapper generation."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
    def test_generate_unix_wrapper_creates_shell_script(self, temp_venv, temp_bin):
        """generate_unix_wrapper() creates shell script on Unix"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)
        generator.create_bin_directory()
        python_path = generator.get_python_path()

        wrapper_path = generator.generate_unix_wrapper(
            "graphiti-mcp", "mcp_server.graphiti_mcp_server", python_path
        )

        assert wrapper_path.exists()
        assert wrapper_path.name == "graphiti-mcp"  # No extension
        assert wrapper_path.parent == temp_bin

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
    def test_unix_wrapper_has_executable_permissions(self, temp_venv, temp_bin):
        """Unix wrapper has executable permissions (0o755)"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)
        generator.create_bin_directory()
        python_path = generator.get_python_path()

        wrapper_path = generator.generate_unix_wrapper(
            "graphiti-mcp", "mcp_server.graphiti_mcp_server", python_path
        )

        # Check permissions
        file_stat = wrapper_path.stat()
        permissions = stat.S_IMODE(file_stat.st_mode)

        assert permissions == 0o755

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
    def test_unix_wrapper_contains_correct_content(self, temp_venv, temp_bin):
        """Unix wrapper contains correct shell script content"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)
        generator.create_bin_directory()
        python_path = generator.get_python_path()

        wrapper_path = generator.generate_unix_wrapper(
            "graphiti-mcp", "mcp_server.graphiti_mcp_server", python_path
        )

        content = wrapper_path.read_text()

        # Should contain shebang
        assert content.startswith("#!/bin/bash")

        # Should contain absolute path to Python
        assert str(python_path) in content

        # Should contain module invocation
        assert "-m mcp_server.graphiti_mcp_server" in content

        # Should forward arguments with "$@"
        assert '"$@"' in content


class TestWrapperGenerationOrchestration:
    """Test generate_wrappers() orchestration."""

    def test_generate_wrappers_creates_all_three_commands(self, temp_venv, temp_bin):
        """generate_wrappers() creates wrappers for all three commands"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)

        success, message = generator.generate_wrappers()

        assert success is True
        assert "3 wrapper scripts" in message or "graphiti-mcp" in message

        # Check all three wrappers exist
        if sys.platform == "win32":
            assert (temp_bin / "graphiti-mcp.cmd").exists()
            assert (temp_bin / "graphiti-bootstrap.cmd").exists()
            assert (temp_bin / "graphiti-mcp-daemon.cmd").exists()
        else:
            assert (temp_bin / "graphiti-mcp").exists()
            assert (temp_bin / "graphiti-bootstrap").exists()
            assert (temp_bin / "graphiti-mcp-daemon").exists()

    def test_generate_wrappers_creates_bin_directory(self, temp_venv, temp_bin):
        """generate_wrappers() creates bin directory if it doesn't exist"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)

        assert not temp_bin.exists()
        success, _ = generator.generate_wrappers()
        assert success is True
        assert temp_bin.exists()

    def test_generate_wrappers_fails_when_venv_missing(self, tmp_path, temp_bin):
        """generate_wrappers() returns (False, error) when venv doesn't exist"""
        nonexistent_venv = tmp_path / "nonexistent"
        generator = WrapperGenerator(venv_path=nonexistent_venv, bin_path=temp_bin)

        success, message = generator.generate_wrappers()

        assert success is False
        assert "does not exist" in message.lower() or "failed" in message.lower()


class TestWrapperValidation:
    """Test wrapper validation."""

    def test_validate_wrappers_returns_true_when_all_exist(self, temp_venv, temp_bin):
        """validate_wrappers() returns True when all wrappers exist"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)
        generator.generate_wrappers()

        all_exist, message = generator.validate_wrappers()

        assert all_exist is True
        assert "all" in message.lower() or "exist" in message.lower()

    def test_validate_wrappers_returns_false_when_bin_missing(self, temp_venv, temp_bin):
        """validate_wrappers() returns False when bin directory doesn't exist"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)

        all_exist, message = generator.validate_wrappers()

        assert all_exist is False
        assert "does not exist" in message.lower()

    def test_validate_wrappers_returns_false_when_wrapper_missing(self, temp_venv, temp_bin):
        """validate_wrappers() returns False when some wrappers are missing"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)
        generator.generate_wrappers()

        # Remove one wrapper
        if sys.platform == "win32":
            (temp_bin / "graphiti-mcp.cmd").unlink()
        else:
            (temp_bin / "graphiti-mcp").unlink()

        all_exist, message = generator.validate_wrappers()

        assert all_exist is False
        assert "missing" in message.lower()


class TestWrapperCleanup:
    """Test wrapper cleanup."""

    def test_cleanup_wrappers_removes_all_wrappers(self, temp_venv, temp_bin):
        """cleanup_wrappers() removes all generated wrappers"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)
        generator.generate_wrappers()

        # Verify wrappers exist
        assert temp_bin.exists()
        if sys.platform == "win32":
            assert (temp_bin / "graphiti-mcp.cmd").exists()
        else:
            assert (temp_bin / "graphiti-mcp").exists()

        # Cleanup
        success, message = generator.cleanup_wrappers()

        assert success is True
        assert "removed" in message.lower() or "3" in message

        # Verify wrappers removed
        if sys.platform == "win32":
            assert not (temp_bin / "graphiti-mcp.cmd").exists()
            assert not (temp_bin / "graphiti-bootstrap.cmd").exists()
            assert not (temp_bin / "graphiti-mcp-daemon.cmd").exists()
        else:
            assert not (temp_bin / "graphiti-mcp").exists()
            assert not (temp_bin / "graphiti-bootstrap").exists()
            assert not (temp_bin / "graphiti-mcp-daemon").exists()

    def test_cleanup_wrappers_handles_missing_bin_gracefully(self, temp_venv, temp_bin):
        """cleanup_wrappers() succeeds even if bin directory doesn't exist"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)

        success, message = generator.cleanup_wrappers()

        assert success is True
        assert "does not exist" in message or "nothing to clean" in message.lower()


class TestPlatformAgnosticPaths:
    """Test platform-agnostic path handling."""

    def test_windows_wrapper_uses_scripts_directory(self, temp_venv, temp_bin):
        """Windows configuration uses Scripts/python.exe path"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)

        with patch('sys.platform', 'win32'):
            # Ensure Scripts/python.exe exists for test
            scripts_dir = temp_venv / "Scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            python_exe = scripts_dir / "python.exe"
            python_exe.write_text("fake")

            python_path = generator.get_python_path()

            assert python_path == temp_venv / "Scripts" / "python.exe"

    def test_unix_wrapper_uses_bin_directory(self, temp_venv, temp_bin):
        """Unix configuration uses bin/python path"""
        generator = WrapperGenerator(venv_path=temp_venv, bin_path=temp_bin)

        with patch('sys.platform', 'linux'):
            # Ensure bin/python exists for test
            bin_dir = temp_venv / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            python = bin_dir / "python"
            python.write_text("#!/usr/bin/env python3")

            python_path = generator.get_python_path()

            assert python_path == temp_venv / "bin" / "python"
