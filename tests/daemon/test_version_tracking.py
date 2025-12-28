"""
Tests for Version Tracking functionality.

Tests the VERSION and INSTALL_INFO file generation, version reading,
and upgrade detection functionality.

Created: 2025-12-25
Story: 6.t - Version Tracking Testing Phase
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime

# Test imports
def test_version_tracking_imports():
    """
    (P0) Verify version tracking functions import without errors.

    Ensures the version tracking module and functions are accessible.
    """
    try:
        from mcp_server.daemon.installer import (
            get_source_version,
            get_installed_version,
            check_for_upgrade
        )
        assert get_source_version is not None
        assert get_installed_version is not None
        assert check_for_upgrade is not None
    except ImportError as e:
        pytest.fail(f"Failed to import version tracking functions: {e}")


def test_write_version_info_creates_version_file():
    """
    (P0) Verify VERSION file is created correctly.

    Tests that _write_version_info() creates a VERSION file with
    a valid semantic version string.
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_dir = temp_path / "source"
        source_dir.mkdir()

        # Create a mock pyproject.toml with version
        (source_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "graphiti"
version = "2.1.0"
""")

        # Mock get_paths
        with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
            mock_paths = MagicMock()
            mock_paths.daemon_home = temp_path / "daemon"
            mock_paths.venv_dir = temp_path / "venv"
            mock_paths.bin_dir = temp_path / "bin"
            mock_paths.install_dir = temp_path / "install"
            mock_get_paths.return_value = mock_paths

            # Create install directory
            mock_paths.install_dir.mkdir(parents=True)

            installer = GraphitiInstaller()

            # Call _write_version_info
            version = installer._write_version_info(source_dir)

            # Verify VERSION file was created
            version_file = mock_paths.install_dir / "VERSION"
            assert version_file.exists(), "VERSION file should be created"

            # Verify version string format (semantic versioning: X.Y.Z)
            version_content = version_file.read_text().strip()
            parts = version_content.split('.')
            assert len(parts) == 3, "Version should have 3 parts (major.minor.patch)"
            assert all(part.isdigit() for part in parts), "Version parts should be numeric"
            assert version == version_content, "Returned version should match file content"


def test_write_version_info_creates_install_info():
    """
    (P0) Verify INSTALL_INFO JSON is valid and contains all fields.

    Tests that _write_version_info() creates INSTALL_INFO with
    required metadata fields.
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_dir = temp_path / "source"
        source_dir.mkdir()

        # Create a mock pyproject.toml with version
        (source_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "graphiti"
version = "2.1.0"
""")

        # Initialize a git repo in source_dir for commit hash
        import subprocess
        subprocess.run(['git', 'init'], cwd=source_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=source_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=source_dir, capture_output=True)
        (source_dir / "test.txt").write_text("test")
        subprocess.run(['git', 'add', '.'], cwd=source_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'test'], cwd=source_dir, capture_output=True)

        # Mock get_paths
        with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
            mock_paths = MagicMock()
            mock_paths.daemon_home = temp_path / "daemon"
            mock_paths.venv_dir = temp_path / "venv"
            mock_paths.bin_dir = temp_path / "bin"
            mock_paths.install_dir = temp_path / "install"
            mock_get_paths.return_value = mock_paths

            # Create install directory
            mock_paths.install_dir.mkdir(parents=True)

            installer = GraphitiInstaller()

            # Call _write_version_info
            installer._write_version_info(source_dir)

            # Verify INSTALL_INFO file was created
            install_info_file = mock_paths.install_dir / "INSTALL_INFO"
            assert install_info_file.exists(), "INSTALL_INFO file should be created"

            # Parse JSON
            install_info = json.loads(install_info_file.read_text())

            # Verify required fields
            required_fields = [
                "version",
                "installed_at",
                "installed_from",
                "source_commit",
                "python_version",
                "platform",
                "installer_version"
            ]
            for field in required_fields:
                assert field in install_info, f"INSTALL_INFO should contain '{field}' field"

            # Verify field formats
            assert install_info["version"] == "2.1.0", "Version should match source"

            # Verify installed_at is ISO 8601 format
            datetime.fromisoformat(install_info["installed_at"].replace('Z', '+00:00'))

            # Verify source_commit is a hex string
            assert len(install_info["source_commit"]) in [7, 40], "Commit hash should be short (7) or full (40)"

            # Verify python_version format (e.g., "3.10.18")
            py_parts = install_info["python_version"].split('.')
            assert len(py_parts) >= 2, "Python version should have at least major.minor"


def test_get_installed_version_reads_version_file():
    """
    (P0) Test get_installed_version() reads VERSION file.

    Verifies that the function correctly reads the VERSION file
    from the install directory.
    """
    from mcp_server.daemon.installer import get_installed_version

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create VERSION file
        version_file = temp_path / "VERSION"
        version_file.write_text("2.1.0\n")

        # Read version
        version = get_installed_version(temp_path)

        assert version == "2.1.0", "Should read version from VERSION file"


def test_get_installed_version_returns_none_when_missing():
    """
    Test get_installed_version() returns None when VERSION file missing.

    Verifies graceful handling of missing VERSION file.
    """
    from mcp_server.daemon.installer import get_installed_version

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # No VERSION file exists
        version = get_installed_version(temp_path)

        assert version is None, "Should return None when VERSION file missing"


def test_get_source_version_reads_from_repo():
    """
    Test get_source_version() reads version from source repo.

    Verifies that the function reads from pyproject.toml in source directory.
    """
    from mcp_server.daemon.installer import get_source_version

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create pyproject.toml with version
        (temp_path / "pyproject.toml").write_text("""
[tool.poetry]
name = "graphiti"
version = "2.2.0"
""")

        # Read version
        version = get_source_version(temp_path)

        assert version == "2.2.0", "Should read version from source pyproject.toml"


def test_check_for_upgrade_detects_upgrade_available():
    """
    (P0) Test upgrade detection (installed < available).

    Verifies that check_for_upgrade() correctly detects when
    an upgrade is available.
    """
    from mcp_server.daemon.installer import check_for_upgrade

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Setup install dir with older version
        install_dir = temp_path / "install"
        install_dir.mkdir()
        (install_dir / "VERSION").write_text("2.0.0\n")

        # Setup source dir with newer version
        source_dir = temp_path / "source"
        source_dir.mkdir()
        (source_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "graphiti"
version = "2.1.0"
""")

        # Check for upgrade
        result = check_for_upgrade(install_dir, source_dir)

        assert result["upgrade_available"] is True, "Should detect upgrade available"
        assert result["installed_version"] == "2.0.0"
        assert result["source_version"] == "2.1.0"


def test_check_for_upgrade_no_upgrade_needed():
    """
    (P0) Test no upgrade needed (installed >= available).

    Verifies that check_for_upgrade() correctly detects when
    no upgrade is needed.
    """
    from mcp_server.daemon.installer import check_for_upgrade

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Setup install dir with same version
        install_dir = temp_path / "install"
        install_dir.mkdir()
        (install_dir / "VERSION").write_text("2.1.0\n")

        # Setup source dir with same version
        source_dir = temp_path / "source"
        source_dir.mkdir()
        (source_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "graphiti"
version = "2.1.0"
""")

        # Check for upgrade
        result = check_for_upgrade(install_dir, source_dir)

        assert result["upgrade_available"] is False, "Should detect no upgrade needed (same version)"
        assert result["installed_version"] == "2.1.0"
        assert result["source_version"] == "2.1.0"


def test_check_for_upgrade_installed_newer():
    """
    Test no upgrade needed when installed version is newer.

    Verifies correct behavior when installed version is ahead of source.
    """
    from mcp_server.daemon.installer import check_for_upgrade

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Setup install dir with newer version
        install_dir = temp_path / "install"
        install_dir.mkdir()
        (install_dir / "VERSION").write_text("2.2.0\n")

        # Setup source dir with older version
        source_dir = temp_path / "source"
        source_dir.mkdir()
        (source_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "graphiti"
version = "2.1.0"
""")

        # Check for upgrade
        result = check_for_upgrade(install_dir, source_dir)

        assert result["upgrade_available"] is False, "Should detect no upgrade needed (installed newer)"
        assert result["installed_version"] == "2.2.0"
        assert result["source_version"] == "2.1.0"


def test_check_for_upgrade_handles_missing_installed():
    """
    Test check_for_upgrade() handles missing installed version.

    Verifies graceful handling when VERSION file missing in install dir.
    """
    from mcp_server.daemon.installer import check_for_upgrade

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Setup install dir without VERSION
        install_dir = temp_path / "install"
        install_dir.mkdir()

        # Setup source dir with version
        source_dir = temp_path / "source"
        source_dir.mkdir()
        (source_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "graphiti"
version = "2.1.0"
""")

        # Check for upgrade
        result = check_for_upgrade(install_dir, source_dir)

        # When not installed, upgrade_available is False (it's a fresh install, not an upgrade)
        # But we should verify it returns the correct status
        assert result["upgrade_available"] is False, "Not an upgrade when nothing installed"
        assert result["installed_version"] is None
        assert result["source_version"] == "2.1.0"
        assert result["comparison"] == "not_installed"
