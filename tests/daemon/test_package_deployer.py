"""
Unit Tests for PackageDeployer (Story 2.i)

Tests package deployment functionality:
- PackageDeployer.deploy_package() creates install_dir/lib/ directory (v2.1 architecture)
- PackageDeployer.deploy_package() copies all mcp_server/ files excluding .venv, __pycache__, tests
- PackageDeployer.deploy_package() creates .version file with current version from pyproject.toml
- PackageDeployer.deploy_package() is idempotent (running twice produces same result)
- PackageDeployer.backup_existing() creates timestamped backup when deployment exists
- PackageDeployer.verify_deployment() validates deployment structure and version file
- PackageDeployer handles Windows backslash and Unix forward slash paths correctly
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from tempfile import TemporaryDirectory

import pytest

from mcp_server.daemon.package_deployer import (
    PackageDeployer,
    PackageDeploymentError,
)
from mcp_server.daemon.paths import get_install_dir


class TestPackageDeployerInit:
    """Test PackageDeployer initialization."""

    def test_default_deploy_path(self):
        """PackageDeployer uses install_dir/lib/ as default deploy path (v2.1 architecture)"""
        deployer = PackageDeployer()
        expected_path = get_install_dir() / "lib"
        assert deployer.deploy_path == expected_path

    def test_custom_deploy_path(self):
        """PackageDeployer accepts custom deploy path"""
        custom_path = Path("/tmp/custom/mcp_server")
        deployer = PackageDeployer(deploy_path=custom_path)
        assert deployer.deploy_path == custom_path

    def test_version_file_path(self):
        """PackageDeployer sets version_file to deploy_path/.version"""
        deployer = PackageDeployer()
        expected_version_file = deployer.deploy_path / ".version"
        assert deployer.version_file == expected_version_file


class TestGetSourcePath:
    """Test _get_source_path() repository detection."""

    def test_get_source_path_from_cwd(self):
        """_get_source_path() detects source from current working directory"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create mock repo structure with both required directories
            repo_path = tmpdir_path / "graphiti"
            mcp_server_path = repo_path / "mcp_server"
            graphiti_core_path = repo_path / "graphiti_core"
            mcp_server_path.mkdir(parents=True)
            graphiti_core_path.mkdir(parents=True)
            (mcp_server_path / "pyproject.toml").write_text("version = '1.0.0'")
            (graphiti_core_path / "__init__.py").write_text("# graphiti_core")

            deployer = PackageDeployer()

            # Must mock both cwd and __file__ to prevent fallback to real repo
            with patch("pathlib.Path.cwd", return_value=repo_path):
                with patch("mcp_server.daemon.package_deployer.__file__", str(tmpdir_path / "fake.py")):
                    source = deployer._get_source_path()
                    assert source == mcp_server_path

    def test_get_source_path_from_env_var(self):
        """_get_source_path() uses GRAPHITI_REPO_PATH environment variable"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create mock repo structure with both required directories
            repo_path = tmpdir_path / "graphiti"
            mcp_server_path = repo_path / "mcp_server"
            graphiti_core_path = repo_path / "graphiti_core"
            mcp_server_path.mkdir(parents=True)
            graphiti_core_path.mkdir(parents=True)
            (mcp_server_path / "pyproject.toml").write_text("version = '1.0.0'")
            (graphiti_core_path / "__init__.py").write_text("# graphiti_core")

            deployer = PackageDeployer()

            # Mock __file__ to prevent fallback to real repo
            with patch("mcp_server.daemon.package_deployer.__file__", str(tmpdir_path / "fake.py")):
                with patch.dict("os.environ", {"GRAPHITI_REPO_PATH": str(repo_path)}):
                    source = deployer._get_source_path()
                    assert source == mcp_server_path

    def test_get_source_path_raises_when_not_found(self, tmp_path):
        """_get_source_path() raises PackageDeploymentError when source not found"""
        deployer = PackageDeployer()

        # Create an empty directory with no mcp_server subdirectory
        nonexistent_repo = tmp_path / "empty_repo"
        nonexistent_repo.mkdir()

        with patch("pathlib.Path.cwd", return_value=nonexistent_repo):
            # Clear env var and mock __file__ location to point to tmp_path
            with patch.dict("os.environ", {}, clear=True):
                # Mock __file__ to point to a non-existent location
                with patch("mcp_server.daemon.package_deployer.__file__", str(nonexistent_repo / "fake.py")):
                    with pytest.raises(PackageDeploymentError) as exc_info:
                        deployer._get_source_path()
                    assert "Cannot find Graphiti repository root" in str(exc_info.value)


class TestGetVersionFromPyproject:
    """Test _get_version_from_pyproject() version extraction."""

    def test_extract_version_from_pyproject(self):
        """_get_version_from_pyproject() extracts version from pyproject.toml"""
        with TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mcp_server"
            source_path.mkdir()
            pyproject = source_path / "pyproject.toml"
            pyproject.write_text('[tool.poetry]\nname = "mcp_server"\nversion = "1.2.3"\n')

            deployer = PackageDeployer()
            version = deployer._get_version_from_pyproject(source_path)
            assert version == "1.2.3"

    def test_version_extraction_with_quotes(self):
        """_get_version_from_pyproject() handles single and double quotes"""
        with TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mcp_server"
            source_path.mkdir()
            pyproject = source_path / "pyproject.toml"

            # Test double quotes
            pyproject.write_text('version = "2.0.0"')
            deployer = PackageDeployer()
            assert deployer._get_version_from_pyproject(source_path) == "2.0.0"

            # Test single quotes
            pyproject.write_text("version = '3.0.0'")
            assert deployer._get_version_from_pyproject(source_path) == "3.0.0"

    def test_version_missing_raises_error(self):
        """_get_version_from_pyproject() raises error when version not found"""
        with TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mcp_server"
            source_path.mkdir()
            pyproject = source_path / "pyproject.toml"
            pyproject.write_text('[tool.poetry]\nname = "mcp_server"\n')  # No version

            deployer = PackageDeployer()
            with pytest.raises(PackageDeploymentError) as exc_info:
                deployer._get_version_from_pyproject(source_path)
            assert "Version field not found" in str(exc_info.value)


class TestShouldIgnore:
    """Test _should_ignore() exclusion logic."""

    def test_ignores_pycache(self):
        """_should_ignore() ignores __pycache__ directories"""
        deployer = PackageDeployer()
        root = Path("/repo/mcp_server")
        path = root / "daemon" / "__pycache__"
        assert deployer._should_ignore(path, root) is True

    def test_ignores_venv(self):
        """_should_ignore() ignores .venv directories"""
        deployer = PackageDeployer()
        root = Path("/repo/mcp_server")
        path = root / ".venv" / "lib"
        assert deployer._should_ignore(path, root) is True

    def test_ignores_tests(self):
        """_should_ignore() ignores tests directories"""
        deployer = PackageDeployer()
        root = Path("/repo/mcp_server")
        path = root / "tests" / "test_something.py"
        assert deployer._should_ignore(path, root) is True

    def test_ignores_pyc_files(self):
        """_should_ignore() ignores .pyc files"""
        deployer = PackageDeployer()
        root = Path("/repo/mcp_server")
        path = root / "module.pyc"
        assert deployer._should_ignore(path, root) is True

    def test_does_not_ignore_regular_files(self):
        """_should_ignore() does not ignore regular Python files"""
        deployer = PackageDeployer()
        root = Path("/repo/mcp_server")
        path = root / "daemon" / "manager.py"
        assert deployer._should_ignore(path, root) is False


class TestBackupExisting:
    """Test backup_existing() backup creation."""

    def test_backup_creates_timestamped_directory(self):
        """backup_existing() creates timestamped backup directory"""
        with TemporaryDirectory() as tmpdir:
            deploy_path = Path(tmpdir) / "mcp_server"
            deploy_path.mkdir()
            (deploy_path / "test_file.py").write_text("content")

            deployer = PackageDeployer(deploy_path=deploy_path)

            with patch("mcp_server.daemon.package_deployer.datetime") as mock_dt:
                mock_dt.now.return_value.strftime.return_value = "20231215-143022"
                backup_path = deployer.backup_existing()

            assert backup_path is not None
            assert backup_path.name == "mcp_server.backup.20231215-143022"
            assert (backup_path / "test_file.py").exists()

    def test_backup_returns_none_when_no_deployment(self):
        """backup_existing() returns None when no existing deployment"""
        with TemporaryDirectory() as tmpdir:
            deploy_path = Path(tmpdir) / "mcp_server"
            deployer = PackageDeployer(deploy_path=deploy_path)

            backup_path = deployer.backup_existing()
            assert backup_path is None

    def test_backup_preserves_directory_structure(self):
        """backup_existing() preserves subdirectory structure"""
        with TemporaryDirectory() as tmpdir:
            deploy_path = Path(tmpdir) / "mcp_server"
            (deploy_path / "daemon").mkdir(parents=True)
            (deploy_path / "daemon" / "manager.py").write_text("code")

            deployer = PackageDeployer(deploy_path=deploy_path)
            backup_path = deployer.backup_existing()

            assert (backup_path / "daemon" / "manager.py").exists()


class TestVerifyDeployment:
    """Test verify_deployment() validation logic."""

    def test_valid_deployment_returns_true(self):
        """verify_deployment() returns True for valid deployment"""
        with TemporaryDirectory() as tmpdir:
            # v2.1: deploy_path is lib/, packages are in lib/mcp_server/ and lib/graphiti_core/
            deploy_path = Path(tmpdir) / "lib"
            deploy_path.mkdir()

            # Create required files - mcp_server package
            mcp_server = deploy_path / "mcp_server"
            mcp_server.mkdir()
            (mcp_server / "graphiti_mcp_server.py").write_text("# MCP server")
            (mcp_server / "daemon").mkdir()
            (mcp_server / "config").mkdir()

            # Create required files - graphiti_core package
            graphiti_core = deploy_path / "graphiti_core"
            graphiti_core.mkdir()
            (graphiti_core / "__init__.py").write_text("# graphiti_core")

            # Version file at deploy_path level
            (deploy_path / ".version").write_text("1.0.0")

            deployer = PackageDeployer(deploy_path=deploy_path)
            assert deployer.verify_deployment() is True

    def test_missing_version_file_returns_false(self):
        """verify_deployment() returns False when .version file missing"""
        with TemporaryDirectory() as tmpdir:
            deploy_path = Path(tmpdir) / "lib"
            deploy_path.mkdir()

            # Create packages but no version file
            mcp_server = deploy_path / "mcp_server"
            mcp_server.mkdir()
            (mcp_server / "graphiti_mcp_server.py").write_text("# MCP server")
            (mcp_server / "daemon").mkdir()
            (mcp_server / "config").mkdir()

            graphiti_core = deploy_path / "graphiti_core"
            graphiti_core.mkdir()
            (graphiti_core / "__init__.py").write_text("# graphiti_core")

            deployer = PackageDeployer(deploy_path=deploy_path)
            assert deployer.verify_deployment() is False

    def test_missing_key_files_returns_false(self):
        """verify_deployment() returns False when key files missing"""
        with TemporaryDirectory() as tmpdir:
            deploy_path = Path(tmpdir) / "lib"
            deploy_path.mkdir()
            (deploy_path / ".version").write_text("1.0.0")
            # Missing mcp_server/, graphiti_core/

            deployer = PackageDeployer(deploy_path=deploy_path)
            assert deployer.verify_deployment() is False


class TestDeployPackage:
    """Test deploy_package() main deployment logic."""

    def test_deploy_creates_directory_structure(self):
        """deploy_package() creates ~/.graphiti/mcp_server/ directory"""
        with TemporaryDirectory() as tmpdir:
            # Create source structure
            repo_path = Path(tmpdir) / "repo"
            source_path = repo_path / "mcp_server"
            source_path.mkdir(parents=True)
            (source_path / "pyproject.toml").write_text('version = "1.0.0"')
            (source_path / "graphiti_mcp_server.py").write_text("# MCP")
            (source_path / "daemon").mkdir()
            (source_path / "config").mkdir()

            # Create deployer with temp deploy path
            deploy_path = Path(tmpdir) / "deploy" / "mcp_server"
            deployer = PackageDeployer(deploy_path=deploy_path)

            with patch.object(deployer, "_get_source_path", return_value=source_path):
                success, msg = deployer.deploy_package()

            assert success is True
            assert deploy_path.exists()
            assert "Successfully deployed" in msg

    def test_deploy_excludes_venv_pycache_tests(self):
        """deploy_package() excludes .venv, __pycache__, tests during copy"""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create mcp_server source with excluded directories
            mcp_source = tmpdir_path / "mcp_server"
            mcp_source.mkdir()
            (mcp_source / "pyproject.toml").write_text('version = "1.0.0"')
            (mcp_source / "graphiti_mcp_server.py").write_text("# MCP")
            (mcp_source / "daemon").mkdir()
            (mcp_source / "config").mkdir()

            # Create excluded directories in mcp_server
            (mcp_source / ".venv").mkdir()
            (mcp_source / ".venv" / "lib").mkdir()
            (mcp_source / "__pycache__").mkdir()
            (mcp_source / "tests").mkdir()
            (mcp_source / "tests" / "test_something.py").write_text("test")

            # Create graphiti_core source (required by v2.1)
            graphiti_source = tmpdir_path / "graphiti_core"
            graphiti_source.mkdir()
            (graphiti_source / "__init__.py").write_text("# graphiti_core")

            # deploy_path is the lib/ directory
            deploy_path = tmpdir_path / "deploy" / "lib"
            deployer = PackageDeployer(deploy_path=deploy_path)

            with patch.object(deployer, "_get_source_path", return_value=mcp_source), \
                 patch.object(deployer, "_get_graphiti_core_path", return_value=graphiti_source):
                success, msg = deployer.deploy_package()

            assert success is True
            # Verify excluded directories not copied (in mcp_server subdirectory)
            mcp_deployed = deploy_path / "mcp_server"
            assert not (mcp_deployed / ".venv").exists()
            assert not (mcp_deployed / "__pycache__").exists()
            assert not (mcp_deployed / "tests").exists()
            # Verify required directories copied
            assert (mcp_deployed / "daemon").exists()
            assert (mcp_deployed / "config").exists()
            # Verify graphiti_core deployed
            assert (deploy_path / "graphiti_core" / "__init__.py").exists()

    def test_deploy_creates_version_file(self):
        """deploy_package() creates .version file with version from pyproject.toml"""
        with TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mcp_server"
            source_path.mkdir()
            (source_path / "pyproject.toml").write_text('version = "2.5.1"')
            (source_path / "graphiti_mcp_server.py").write_text("# MCP")
            (source_path / "daemon").mkdir()
            (source_path / "config").mkdir()

            deploy_path = Path(tmpdir) / "deploy" / "mcp_server"
            deployer = PackageDeployer(deploy_path=deploy_path)

            with patch.object(deployer, "_get_source_path", return_value=source_path):
                success, msg = deployer.deploy_package()

            assert success is True
            assert (deploy_path / ".version").exists()
            assert (deploy_path / ".version").read_text() == "2.5.1"

    def test_deploy_is_idempotent(self):
        """deploy_package() is idempotent (running twice with same version is safe)"""
        with TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mcp_server"
            source_path.mkdir()
            (source_path / "pyproject.toml").write_text('version = "1.0.0"')
            (source_path / "graphiti_mcp_server.py").write_text("# MCP")
            (source_path / "daemon").mkdir()
            (source_path / "config").mkdir()

            deploy_path = Path(tmpdir) / "deploy" / "mcp_server"
            deployer = PackageDeployer(deploy_path=deploy_path)

            with patch.object(deployer, "_get_source_path", return_value=source_path):
                # First deployment
                success1, msg1 = deployer.deploy_package()
                assert success1 is True

                # Second deployment (should skip)
                success2, msg2 = deployer.deploy_package()
                assert success2 is True
                assert "already exists" in msg2
                assert "skipping" in msg2

    def test_deploy_backs_up_old_deployment(self):
        """deploy_package() backs up existing deployment when version changes"""
        with TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mcp_server"
            source_path.mkdir()
            (source_path / "pyproject.toml").write_text('version = "2.0.0"')
            (source_path / "graphiti_mcp_server.py").write_text("# MCP")
            (source_path / "daemon").mkdir()
            (source_path / "config").mkdir()

            deploy_path = Path(tmpdir) / "deploy" / "mcp_server"
            deploy_path.mkdir(parents=True)
            (deploy_path / ".version").write_text("1.0.0")  # Old version
            (deploy_path / "old_file.py").write_text("old")

            deployer = PackageDeployer(deploy_path=deploy_path)

            with patch.object(deployer, "_get_source_path", return_value=source_path):
                success, msg = deployer.deploy_package()

            assert success is True
            # Check backup was created
            backups = list(deploy_path.parent.glob("mcp_server.backup.*"))
            assert len(backups) == 1
            assert (backups[0] / "old_file.py").exists()

    def test_deploy_with_force_redeployment(self):
        """deploy_package(force=True) forces redeployment even with same version"""
        with TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mcp_server"
            source_path.mkdir()
            (source_path / "pyproject.toml").write_text('version = "1.0.0"')
            (source_path / "graphiti_mcp_server.py").write_text("# MCP")
            (source_path / "daemon").mkdir()
            (source_path / "config").mkdir()

            deploy_path = Path(tmpdir) / "deploy" / "mcp_server"
            deployer = PackageDeployer(deploy_path=deploy_path)

            with patch.object(deployer, "_get_source_path", return_value=source_path):
                # First deployment
                success1, msg1 = deployer.deploy_package()
                assert success1 is True

                # Force redeployment
                success2, msg2 = deployer.deploy_package(force=True)
                assert success2 is True
                assert "Successfully deployed" in msg2
                # Should NOT say "skipping"


class TestGetDeployedVersion:
    """Test get_deployed_version() version reading."""

    def test_get_deployed_version_returns_version(self):
        """get_deployed_version() returns version string from .version file"""
        with TemporaryDirectory() as tmpdir:
            deploy_path = Path(tmpdir) / "mcp_server"
            deploy_path.mkdir()
            (deploy_path / ".version").write_text("3.2.1")

            deployer = PackageDeployer(deploy_path=deploy_path)
            version = deployer.get_deployed_version()
            assert version == "3.2.1"

    def test_get_deployed_version_returns_none_when_not_deployed(self):
        """get_deployed_version() returns None when deployment doesn't exist"""
        with TemporaryDirectory() as tmpdir:
            deploy_path = Path(tmpdir) / "mcp_server"
            deployer = PackageDeployer(deploy_path=deploy_path)
            version = deployer.get_deployed_version()
            assert version is None


class TestCrossPlatformPaths:
    """Test platform-agnostic path handling."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_windows_backslash_paths(self):
        """PackageDeployer handles Windows backslash paths correctly"""
        deployer = PackageDeployer()
        # Default path should use backslashes on Windows
        assert "\\" in str(deployer.deploy_path) or deployer.deploy_path.drive

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_unix_forward_slash_paths(self):
        """PackageDeployer handles Unix forward slash paths correctly"""
        deployer = PackageDeployer()
        # Default path should use forward slashes on Unix
        assert str(deployer.deploy_path).startswith("/")
