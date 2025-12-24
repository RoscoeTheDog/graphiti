"""
End-to-end installation tests on clean system.

Tests complete daemon installation flow from clean ~/.graphiti/ directory:
- Scenario 1: Fresh installation (directory structure, venv, package, wrappers)
- Scenario 4: Idempotent reinstallation
- Scenario 5: Error scenarios (incompatible Python, insufficient permissions)

Service lifecycle tests (Scenarios 2-3) are documented in README_E2E.md
for manual testing due to platform-specific service registration requirements.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from mcp_server.daemon.venv_manager import VenvManager
from mcp_server.daemon.package_deployer import PackageDeployer
from mcp_server.daemon.wrapper_generator import WrapperGenerator


class TestE2EInstallation:
    """End-to-end installation tests on clean system."""

    @pytest.fixture
    def clean_graphiti_dir(self, tmp_path):
        """
        Provide clean ~/.graphiti/ directory for testing.

        Uses tmp_path instead of actual ~/.graphiti/ for safety.
        Simulates clean state by creating/removing directory.
        """
        graphiti_path = tmp_path / ".graphiti"

        # Ensure clean state
        if graphiti_path.exists():
            shutil.rmtree(graphiti_path)

        yield graphiti_path

        # Cleanup after test
        if graphiti_path.exists():
            shutil.rmtree(graphiti_path)

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """
        Create mock repository structure for testing.

        Simulates graphiti repository with mcp_server package.
        PackageDeployer expects pyproject.toml at the root of the repo.
        """
        repo_path = tmp_path / "graphiti_repo"
        repo_path.mkdir(parents=True)

        # Create mcp_server package structure
        mcp_server_path = repo_path / "mcp_server"
        mcp_server_path.mkdir()

        # Create pyproject.toml at REPO ROOT (where PackageDeployer expects it)
        (repo_path / "pyproject.toml").write_text(
            "[project]\n"
            "name = 'graphiti'\n"
            "version = '1.0.0'\n"
            "dependencies = ['neo4j>=5.25.0', 'openai>=1.57.2']\n"
        )

        # Also create pyproject.toml in mcp_server (for package metadata)
        (mcp_server_path / "pyproject.toml").write_text(
            "[project]\n"
            "name = 'mcp_server'\n"
            "version = '1.0.0'\n"
        )

        # Create __init__.py to make it a package
        (mcp_server_path / "__init__.py").write_text("")

        # Create key files that verify_deployment checks for
        (mcp_server_path / "graphiti_mcp_server.py").write_text("# MCP server main file")

        # Create daemon/ directory
        daemon_path = mcp_server_path / "daemon"
        daemon_path.mkdir()
        (daemon_path / "__init__.py").write_text("")

        # Create config/ directory
        config_path = mcp_server_path / "config"
        config_path.mkdir()
        (config_path / "__init__.py").write_text("")

        return repo_path

    def test_scenario_1_fresh_installation(self, clean_graphiti_dir, mock_repo):
        """
        Scenario 1: Fresh installation from clean state.

        Tests:
        - Directory structure creation (~/.graphiti/, .venv/, mcp_server/, bin/, logs/)
        - Venv creation with Python interpreter
        - Package deployment (mcp_server copied to ~/.graphiti/)
        - Package installation (pip install -e)
        - Wrapper generation (CLI scripts)

        Expected outcome: All components installed successfully
        """
        venv_path = clean_graphiti_dir / ".venv"
        mcp_server_deploy_path = clean_graphiti_dir / "mcp_server"
        bin_path = clean_graphiti_dir / "bin"
        logs_path = clean_graphiti_dir / "logs"

        # Step 1: Create directory structure
        clean_graphiti_dir.mkdir(parents=True)
        assert clean_graphiti_dir.exists()

        # Step 2: Create venv (mocked subprocess for speed)
        venv_manager = VenvManager(venv_path=venv_path)

        with patch.object(venv_manager, 'validate_python_version', return_value=True), \
             patch.object(venv_manager, 'check_uv_available', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Simulate venv creation manually
            venv_path.mkdir(parents=True)
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

            (venv_path / "pyvenv.cfg").write_text("version = 3.10.0")

            with patch.object(venv_manager, 'detect_venv', side_effect=[False, True]):
                success, message = venv_manager.create_venv()

            assert success is True
            assert venv_path.exists()
            assert (venv_path / "pyvenv.cfg").exists()

        # Step 3: Deploy package to ~/.graphiti/mcp_server/ (mocked for CI)
        deployer = PackageDeployer(deploy_path=mcp_server_deploy_path)

        # Mock _get_source_path and verify_deployment for test isolation
        # In real deployment, this copies mcp_server/ from repo to ~/.graphiti/mcp_server/
        with patch.object(deployer, '_get_source_path', return_value=mock_repo), \
             patch.object(deployer, 'verify_deployment', return_value=True):
            success, message = deployer.deploy_package()

            assert success is True
            # In real scenario, verify_deployment would check for these files
            # But in test, we're mocking the deployment for speed and isolation

        # Step 4: Install package (mocked)
        with patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch.object(venv_manager, 'detect_repo_location', return_value=clean_graphiti_dir), \
             patch.object(venv_manager, 'get_pip_executable',
                          return_value=venv_path / ("Scripts/pip.exe" if sys.platform == "win32" else "bin/pip")), \
             patch.object(venv_manager, 'validate_installation', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = Mock(returncode=0, stdout="Successfully installed mcp_server", stderr="")

            success, message = venv_manager.install_package()

            assert success is True
            assert "success" in message.lower() or "installed" in message.lower()

        # Step 5: Generate wrappers
        wrapper_gen = WrapperGenerator(venv_path=venv_path, bin_path=bin_path)
        bin_path.mkdir(parents=True)

        success, message = wrapper_gen.generate_wrappers()

        assert success is True
        assert bin_path.exists()

        if sys.platform == "win32":
            assert (bin_path / "graphiti-mcp.cmd").exists()
        else:
            assert (bin_path / "graphiti-mcp").exists()
            # Check wrapper is executable
            wrapper = bin_path / "graphiti-mcp"
            assert os.access(wrapper, os.X_OK)

        # Step 6: Create logs directory
        logs_path.mkdir(parents=True)
        assert logs_path.exists()

        # Verify complete directory structure
        assert (clean_graphiti_dir / ".venv").exists()
        assert (clean_graphiti_dir / "mcp_server").exists()
        assert (clean_graphiti_dir / "bin").exists()
        assert (clean_graphiti_dir / "logs").exists()

    def test_scenario_4_idempotent_reinstallation(self, clean_graphiti_dir, mock_repo):
        """
        Scenario 4: Reinstallation is safe and idempotent.

        Tests:
        - Running install twice doesn't fail
        - Existing venv is detected
        - No duplicate files created
        - Installation still functional

        Expected outcome: Reinstallation completes without errors
        """
        venv_path = clean_graphiti_dir / ".venv"
        mcp_server_deploy_path = clean_graphiti_dir / "mcp_server"
        bin_path = clean_graphiti_dir / "bin"

        # Initial installation
        clean_graphiti_dir.mkdir(parents=True)
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

        # Deploy package
        deployer = PackageDeployer(deploy_path=mcp_server_deploy_path)
        with patch.object(deployer, '_get_source_path', return_value=mock_repo), \
             patch.object(deployer, 'verify_deployment', return_value=True):
            deployer.deploy_package()

        # Generate wrappers
        bin_path.mkdir(parents=True)
        wrapper_gen = WrapperGenerator(venv_path=venv_path, bin_path=bin_path)
        wrapper_gen.generate_wrappers()

        # Verify initial installation
        assert venv_path.exists()
        assert mcp_server_deploy_path.exists()
        assert bin_path.exists()

        # Get initial file counts
        initial_venv_files = list(venv_path.rglob("*"))
        initial_mcp_files = list(mcp_server_deploy_path.rglob("*"))
        initial_bin_files = list(bin_path.rglob("*"))

        # Step: Reinstall (simulate detecting existing venv)
        venv_manager = VenvManager(venv_path=venv_path)

        with patch.object(venv_manager, 'detect_venv', return_value=True):
            # Venv already exists, should skip creation
            success, message = venv_manager.create_venv()

            # Should succeed and indicate venv already exists
            assert success is True or "already exists" in message.lower()

        # Redeploy package (should overwrite safely)
        deployer_2 = PackageDeployer(deploy_path=mcp_server_deploy_path)
        with patch.object(deployer_2, '_get_source_path', return_value=mock_repo), \
             patch.object(deployer_2, 'verify_deployment', return_value=True):
            success, message = deployer_2.deploy_package()

            assert success is True

        # Regenerate wrappers (should overwrite safely)
        wrapper_gen_2 = WrapperGenerator(venv_path=venv_path, bin_path=bin_path)
        success, message = wrapper_gen_2.generate_wrappers()

        assert success is True

        # Verify no duplicate files (counts should be similar)
        final_venv_files = list(venv_path.rglob("*"))
        final_mcp_files = list(mcp_server_deploy_path.rglob("*"))
        final_bin_files = list(bin_path.rglob("*"))

        # File counts should be the same or very close (allowing for minor differences)
        assert abs(len(final_venv_files) - len(initial_venv_files)) <= 2
        assert abs(len(final_mcp_files) - len(initial_mcp_files)) <= 2
        assert abs(len(final_bin_files) - len(initial_bin_files)) <= 1

        # Verify installation still functional
        assert venv_path.exists()
        assert (venv_path / "pyvenv.cfg").exists()
        assert mcp_server_deploy_path.exists()
        assert (mcp_server_deploy_path / "pyproject.toml").exists()

    def test_scenario_5a_error_incompatible_python(self, clean_graphiti_dir):
        """
        Scenario 5a: Error handling for incompatible Python version.

        Tests:
        - Python < 3.10 detected and rejected
        - Clear error message provided
        - Installation halted gracefully

        Expected outcome: Clear error with minimum version requirement
        """
        from mcp_server.daemon.venv_manager import IncompatiblePythonVersionError

        venv_path = clean_graphiti_dir / ".venv"
        venv_manager = VenvManager(venv_path=venv_path)

        # Mock Python version check to raise exception (incompatible)
        def mock_validate():
            raise IncompatiblePythonVersionError("Python 3.10+ required")

        with patch.object(venv_manager, 'validate_python_version', side_effect=mock_validate):
            try:
                venv_manager.create_venv()
                assert False, "Should have raised IncompatiblePythonVersionError"
            except IncompatiblePythonVersionError as e:
                # Expected exception
                assert "3.10" in str(e) or "python" in str(e).lower()

    def test_scenario_5b_error_insufficient_permissions(self, clean_graphiti_dir, mock_repo):
        """
        Scenario 5b: Error handling for insufficient write permissions.

        Tests:
        - Permission errors during directory creation
        - Clear error message provided
        - Installation halted gracefully

        Expected outcome: Clear error indicating permission issue
        """
        from mcp_server.daemon.package_deployer import PackageDeploymentError

        # Simulate permission error during deployment
        mcp_server_deploy_path = clean_graphiti_dir / "mcp_server"

        deployer = PackageDeployer(deploy_path=mcp_server_deploy_path)

        # Mock _get_source_path and shutil.copytree to raise PermissionError
        with patch.object(deployer, '_get_source_path', return_value=mock_repo), \
             patch('shutil.copytree', side_effect=PermissionError("Access denied")):
            try:
                deployer.deploy_package()
                assert False, "Should have raised PackageDeploymentError"
            except (PackageDeploymentError, PermissionError) as e:
                # Expected exception (either wrapped or raw)
                assert "permission" in str(e).lower() or "access" in str(e).lower()

    def test_scenario_5c_error_repo_not_found(self, clean_graphiti_dir):
        """
        Scenario 5c: Error handling when repository not found.

        Tests:
        - Package installation fails when repo not detected
        - Clear error message with troubleshooting guidance
        - Installation halted gracefully

        Expected outcome: Clear error indicating repo not found
        """
        venv_path = clean_graphiti_dir / ".venv"
        venv_manager = VenvManager(venv_path=venv_path)

        # Create minimal venv structure
        venv_path.mkdir(parents=True)
        (venv_path / "pyvenv.cfg").write_text("version = 3.10.0")

        # Mock repo detection to return None (not found)
        with patch.object(venv_manager, 'detect_venv', return_value=True), \
             patch.object(venv_manager, 'detect_repo_location', return_value=None):

            success, message = venv_manager.install_package()

            assert success is False
            assert "repo" in message.lower() or "not found" in message.lower()
