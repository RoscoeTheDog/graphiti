"""
Unit tests for VenvManager package installation functionality.

Tests cover:
- Package installation with uv pip (preferred)
- Fallback to standard pip when uv unavailable in venv
- Error handling for non-existent venv
- Package installation failure scenarios
- Automatic repository detection
- Installation validation
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from mcp_server.daemon.venv_manager import (
    VenvManager,
    VenvCreationError,
)


class TestPackageInstallation:
    """Test suite for VenvManager.install_package() functionality."""

    @pytest.fixture
    def temp_venv_path(self, tmp_path):
        """Provide a temporary venv path for testing."""
        return tmp_path / "test_venv"

    @pytest.fixture
    def manager(self, temp_venv_path):
        """Create VenvManager instance with temporary path."""
        return VenvManager(venv_path=temp_venv_path)

    @pytest.fixture
    def mock_repo_structure(self, tmp_path):
        """Create mock repository structure for testing."""
        repo_path = tmp_path / "graphiti_repo"
        repo_path.mkdir()
        mcp_server_path = repo_path / "mcp_server"
        mcp_server_path.mkdir()
        (mcp_server_path / "pyproject.toml").write_text("[project]\nname = 'mcp_server'")
        return repo_path

    def test_install_package_with_uv_pip(self, manager, temp_venv_path, mock_repo_structure):
        """Test package installation using uv pip (preferred method)."""
        # Setup: venv exists, uv is available in venv
        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'detect_repo_location', return_value=mock_repo_structure), \
             patch.object(manager, 'get_uv_executable', return_value=temp_venv_path / "Scripts" / "uv.exe"), \
             patch.object(manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            success, message = manager.install_package()

            assert success is True
            assert "uv pip" in message.lower() or "successfully" in message.lower()
            mock_run.assert_called_once()

            # Verify uv pip command was used
            call_args = mock_run.call_args[0][0]
            assert "uv" in str(call_args[0])
            assert "pip" in call_args
            assert "install" in call_args

    def test_install_package_fallback_to_standard_pip(self, manager, temp_venv_path, mock_repo_structure):
        """Test fallback to standard pip when uv not available in venv."""
        # Setup: venv exists, uv not available, pip is available
        pip_exe = temp_venv_path / "Scripts" / "pip.exe"

        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'detect_repo_location', return_value=mock_repo_structure), \
             patch.object(manager, 'get_uv_executable', return_value=None), \
             patch.object(manager, 'get_pip_executable', return_value=pip_exe), \
             patch.object(manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            success, message = manager.install_package()

            assert success is True
            assert "pip" in message.lower() or "successfully" in message.lower()
            mock_run.assert_called_once()

            # Verify standard pip command was used
            call_args = mock_run.call_args[0][0]
            assert str(pip_exe) in str(call_args[0])
            assert "install" in call_args

    def test_install_package_raises_on_missing_venv(self, manager):
        """Test error raised when venv does not exist."""
        with patch.object(manager, 'detect_venv', return_value=False):
            with pytest.raises(VenvCreationError) as exc_info:
                manager.install_package()

            assert "does not exist" in str(exc_info.value).lower()
            assert "create_venv" in str(exc_info.value).lower()

    def test_install_package_handles_repo_not_found(self, manager):
        """Test graceful handling when repository cannot be detected."""
        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'detect_repo_location', return_value=None):

            success, message = manager.install_package()

            assert success is False
            assert "cannot find" in message.lower()
            assert "repository" in message.lower() or "mcp_server" in message.lower()

    def test_install_package_handles_subprocess_failure(self, manager, temp_venv_path, mock_repo_structure):
        """Test error handling when pip subprocess fails."""
        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'detect_repo_location', return_value=mock_repo_structure), \
             patch.object(manager, 'get_uv_executable', return_value=None), \
             patch.object(manager, 'get_pip_executable', return_value=temp_venv_path / "Scripts" / "pip.exe"), \
             patch('subprocess.run') as mock_run:

            # Simulate package installation failure
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="ERROR: Could not find a version that satisfies the requirement"
            )

            success, message = manager.install_package()

            assert success is False
            assert "failed" in message.lower()
            assert "exit code 1" in message.lower()

    def test_install_package_handles_timeout(self, manager, temp_venv_path, mock_repo_structure):
        """Test handling of installation timeout (slow network, large dependencies)."""
        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'detect_repo_location', return_value=mock_repo_structure), \
             patch.object(manager, 'get_uv_executable', return_value=None), \
             patch.object(manager, 'get_pip_executable', return_value=temp_venv_path / "Scripts" / "pip.exe"), \
             patch('subprocess.run') as mock_run:

            # Simulate subprocess timeout
            mock_run.side_effect = subprocess.TimeoutExpired("pip install", 300)

            success, message = manager.install_package()

            assert success is False
            assert "timeout" in message.lower() or "error" in message.lower()

    def test_install_package_validates_repo_path_security(self, manager, tmp_path):
        """Test that repository path validation prevents path traversal."""
        # Create malicious-looking path
        malicious_path = tmp_path / ".." / ".." / "etc"

        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'detect_repo_location', return_value=malicious_path):

            success, message = manager.install_package()

            # Should fail because mcp_server/pyproject.toml doesn't exist
            assert success is False
            assert "not found" in message.lower()

    def test_install_package_uses_correct_working_directory(self, manager, temp_venv_path, mock_repo_structure):
        """Test that installation runs from repository root (cwd parameter)."""
        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'detect_repo_location', return_value=mock_repo_structure), \
             patch.object(manager, 'get_uv_executable', return_value=temp_venv_path / "Scripts" / "uv.exe"), \
             patch.object(manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            manager.install_package()

            # Verify cwd was set to repo root
            call_kwargs = mock_run.call_args[1]
            assert 'cwd' in call_kwargs
            assert str(mock_repo_structure) in call_kwargs['cwd']

    def test_install_package_installs_non_editable(self, manager, temp_venv_path, mock_repo_structure):
        """Test that package is installed in non-editable mode (no -e flag)."""
        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'detect_repo_location', return_value=mock_repo_structure), \
             patch.object(manager, 'get_uv_executable', return_value=None), \
             patch.object(manager, 'get_pip_executable', return_value=temp_venv_path / "Scripts" / "pip.exe"), \
             patch.object(manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            manager.install_package()

            # Verify -e flag is NOT present
            call_args = mock_run.call_args[0][0]
            assert "-e" not in call_args
            assert "--editable" not in call_args


class TestRepositoryDetection:
    """Test suite for automatic repository location detection."""

    @pytest.fixture
    def temp_venv_path(self, tmp_path):
        """Provide a temporary venv path for testing."""
        return tmp_path / "test_venv"

    @pytest.fixture
    def manager(self, temp_venv_path):
        """Create VenvManager instance with temporary path."""
        return VenvManager(venv_path=temp_venv_path)

    def test_detect_repo_location_finds_parent(self, manager, tmp_path):
        """Test repository detection when mcp_server is in parent directory."""
        # Create structure: tmp_path/mcp_server/pyproject.toml
        # Venv is at: tmp_path/test_venv/
        repo_path = tmp_path
        mcp_server_path = repo_path / "mcp_server"
        mcp_server_path.mkdir()
        (mcp_server_path / "pyproject.toml").write_text("[project]\nname = 'mcp_server'")

        detected_repo = manager.detect_repo_location()

        assert detected_repo is not None
        assert detected_repo == repo_path

    def test_detect_repo_location_searches_upward(self, manager, tmp_path):
        """Test repository detection searches upward multiple levels."""
        # Create structure: tmp_path/graphiti/mcp_server/pyproject.toml
        # Venv is at: tmp_path/test_venv/
        repo_path = tmp_path / "graphiti"
        repo_path.mkdir()
        mcp_server_path = repo_path / "mcp_server"
        mcp_server_path.mkdir()
        (mcp_server_path / "pyproject.toml").write_text("[project]\nname = 'mcp_server'")

        # Update venv path to be deeper
        manager.venv_path = tmp_path / "test_venv" / "nested"

        detected_repo = manager.detect_repo_location()

        assert detected_repo is not None
        assert detected_repo == repo_path

    def test_detect_repo_location_returns_none_when_not_found(self, manager, tmp_path):
        """Test repository detection returns None when no repo found."""
        # No mcp_server directory created
        detected_repo = manager.detect_repo_location()

        assert detected_repo is None

    def test_detect_repo_location_stops_at_depth_limit(self, manager, tmp_path):
        """Test repository detection doesn't search infinitely (max 5 levels)."""
        # Create very deep venv path (>5 levels)
        deep_venv = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "venv"
        manager.venv_path = deep_venv

        # Put repo at root (>5 levels up)
        repo_path = tmp_path
        mcp_server_path = repo_path / "mcp_server"
        mcp_server_path.mkdir(parents=True)
        (mcp_server_path / "pyproject.toml").write_text("[project]\nname = 'mcp_server'")

        detected_repo = manager.detect_repo_location()

        # Should not find it (too deep)
        assert detected_repo is None


class TestInstallationValidation:
    """Test suite for package installation validation."""

    @pytest.fixture
    def temp_venv_path(self, tmp_path):
        """Provide a temporary venv path for testing."""
        return tmp_path / "test_venv"

    @pytest.fixture
    def manager(self, temp_venv_path):
        """Create VenvManager instance with temporary path."""
        return VenvManager(venv_path=temp_venv_path)

    def test_validate_installation_success(self, manager):
        """Test successful validation when package is importable."""
        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'get_python_executable', return_value=Path("/fake/python")), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = manager.validate_installation("mcp_server")

            assert result is True

    def test_validate_installation_failure(self, manager):
        """Test validation failure when package cannot be imported."""
        with patch.object(manager, 'detect_venv', return_value=True), \
             patch.object(manager, 'get_python_executable', return_value=Path("/fake/python")), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=1, stdout="", stderr="ModuleNotFoundError")

            result = manager.validate_installation("mcp_server")

            assert result is False
