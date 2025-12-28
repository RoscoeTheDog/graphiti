"""
Tests for frozen package deployment functionality.

Tests the _freeze_packages method and related helpers that copy mcp_server
and graphiti_core packages to the installation lib/ directory.

Created: 2025-12-25
Story: 5.t - Frozen Package Deployment Testing Phase
"""

import pytest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

# Test constants
EXCLUDED_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "*.egg-info",
]


def test_freeze_packages_imports():
    """
    (P0) Verify frozen package methods are importable.

    Smoke test to ensure all frozen package functionality exists.
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    installer_methods = dir(GraphitiInstaller)

    # Verify main orchestration method exists
    assert "_freeze_packages" in installer_methods, \
        "_freeze_packages method should exist"

    # Verify helper methods exist
    assert "_find_repo_root" in installer_methods, \
        "_find_repo_root helper should exist"
    assert "_validate_source_packages" in installer_methods, \
        "_validate_source_packages helper should exist"
    assert "_copy_packages" in installer_methods, \
        "_copy_packages helper should exist"
    assert "_verify_frozen_packages" in installer_methods, \
        "_verify_frozen_packages helper should exist"


def test_find_repo_root_with_explicit_path():
    """
    Test _find_repo_root() with explicit source_dir argument.

    Verifies that explicit paths are used when provided.
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        mock_paths = MagicMock()
        mock_paths.daemon_home = Path("/mock/daemon")
        mock_paths.install_dir = Path("/mock/install")
        mock_get_paths.return_value = mock_paths

        installer = GraphitiInstaller()

        # Test with valid explicit path (must exist and contain mcp_server/)
        with tempfile.TemporaryDirectory() as temp_dir:
            explicit_path = Path(temp_dir)
            # Create mcp_server/ to make it valid
            (explicit_path / "mcp_server").mkdir()

            result = installer._find_repo_root(explicit_path)

            assert result == explicit_path, \
                "Should return explicit path when provided and valid"


def test_validate_source_packages_structure():
    """
    Test _validate_source_packages() verifies package structure.

    Ensures both mcp_server and graphiti_core packages are found.
    """
    from mcp_server.daemon.installer import GraphitiInstaller, ValidationError

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        mock_paths = MagicMock()
        mock_paths.daemon_home = Path("/mock/daemon")
        mock_paths.install_dir = Path("/mock/install")
        mock_get_paths.return_value = mock_paths

        installer = GraphitiInstaller()

        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)

            # Create mcp_server package with critical files
            mcp_server_dir = repo_root / "mcp_server"
            mcp_server_dir.mkdir()
            (mcp_server_dir / "__init__.py").touch()
            (mcp_server_dir / "graphiti_mcp_server.py").touch()  # Critical file required

            # Create graphiti_core package (directly under repo_root, not graphiti/graphiti_core)
            graphiti_core_dir = repo_root / "graphiti_core"
            graphiti_core_dir.mkdir()
            (graphiti_core_dir / "__init__.py").touch()

            # Validate packages
            mcp_path, core_path = installer._validate_source_packages(repo_root)

            # Verify returned paths
            assert mcp_path.name == "mcp_server", \
                "Should find mcp_server package"
            assert core_path.name == "graphiti_core", \
                "Should find graphiti_core package"
            assert (mcp_path / "__init__.py").exists(), \
                "mcp_server should have __init__.py"
            assert (mcp_path / "graphiti_mcp_server.py").exists(), \
                "mcp_server should have graphiti_mcp_server.py"
            assert (core_path / "__init__.py").exists(), \
                "graphiti_core should have __init__.py"


def test_validate_source_packages_missing_init():
    """
    Test _validate_source_packages() detects missing __init__.py files.

    Ensures validation fails when packages are incomplete.
    """
    from mcp_server.daemon.installer import GraphitiInstaller, ValidationError

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        mock_paths = MagicMock()
        mock_paths.daemon_home = Path("/mock/daemon")
        mock_paths.install_dir = Path("/mock/install")
        mock_get_paths.return_value = mock_paths

        installer = GraphitiInstaller()

        # Create temporary directory with incomplete package
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)

            # Create mcp_server WITHOUT __init__.py
            mcp_server_dir = repo_root / "mcp_server"
            mcp_server_dir.mkdir()
            # Missing: (mcp_server_dir / "__init__.py").touch()

            graphiti_dir = repo_root / "graphiti"
            graphiti_dir.mkdir()
            graphiti_core_dir = graphiti_dir / "graphiti_core"
            graphiti_core_dir.mkdir()
            (graphiti_core_dir / "__init__.py").touch()

            # Validation should fail
            with pytest.raises(ValidationError) as exc_info:
                installer._validate_source_packages(repo_root)

            # Error message should mention missing __init__.py
            error_msg = str(exc_info.value).lower()
            assert "__init__.py" in error_msg or "incomplete" in error_msg, \
                "Error should mention missing __init__.py"


def test_copy_packages_creates_lib_directory():
    """
    (P0) Test _copy_packages() creates lib/ directory.

    Verifies that the destination lib/ directory is created.
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        with tempfile.TemporaryDirectory() as temp_install:
            install_dir = Path(temp_install)
            lib_dir = install_dir / "lib"

            mock_paths = MagicMock()
            mock_paths.daemon_home = Path("/mock/daemon")
            mock_paths.install_dir = install_dir
            mock_get_paths.return_value = mock_paths

            installer = GraphitiInstaller()

            # Create source packages
            with tempfile.TemporaryDirectory() as temp_src:
                src_root = Path(temp_src)

                mcp_src = src_root / "mcp_server"
                mcp_src.mkdir()
                (mcp_src / "__init__.py").write_text("# mcp_server")

                core_src = src_root / "graphiti_core"
                core_src.mkdir()
                (core_src / "__init__.py").write_text("# graphiti_core")

                # Copy packages
                installer._copy_packages((mcp_src, core_src))

                # Verify lib directory was created
                assert lib_dir.exists(), "lib/ directory should be created"
                assert lib_dir.is_dir(), "lib/ should be a directory"


def test_copy_packages_excludes_patterns():
    """
    (P0) Test _copy_packages() excludes unwanted files/directories.

    Verifies that exclusion patterns work correctly:
    - __pycache__/ directories excluded
    - .pyc, .pyo files excluded
    - .git directories excluded
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        with tempfile.TemporaryDirectory() as temp_install:
            install_dir = Path(temp_install)

            mock_paths = MagicMock()
            mock_paths.daemon_home = Path("/mock/daemon")
            mock_paths.install_dir = install_dir
            mock_get_paths.return_value = mock_paths

            installer = GraphitiInstaller()

            # Create source package with excluded items
            with tempfile.TemporaryDirectory() as temp_src:
                src_root = Path(temp_src)

                mcp_src = src_root / "mcp_server"
                mcp_src.mkdir()
                (mcp_src / "__init__.py").write_text("# init")
                (mcp_src / "module.py").write_text("# module")

                # Create excluded items
                pycache_dir = mcp_src / "__pycache__"
                pycache_dir.mkdir()
                (pycache_dir / "module.cpython-313.pyc").touch()

                (mcp_src / "compiled.pyc").touch()
                (mcp_src / "compiled.pyo").touch()

                git_dir = mcp_src / ".git"
                git_dir.mkdir()
                (git_dir / "config").touch()

                core_src = src_root / "graphiti_core"
                core_src.mkdir()
                (core_src / "__init__.py").write_text("# core")

                # Copy packages
                installer._copy_packages((mcp_src, core_src))

                # Verify excluded items not copied
                lib_mcp = install_dir / "lib" / "mcp_server"

                assert not (lib_mcp / "__pycache__").exists(), \
                    "__pycache__ should be excluded"
                assert not (lib_mcp / "compiled.pyc").exists(), \
                    ".pyc files should be excluded"
                assert not (lib_mcp / "compiled.pyo").exists(), \
                    ".pyo files should be excluded"
                assert not (lib_mcp / ".git").exists(), \
                    ".git directory should be excluded"

                # Verify included items ARE copied
                assert (lib_mcp / "__init__.py").exists(), \
                    "__init__.py should be included"
                assert (lib_mcp / "module.py").exists(), \
                    ".py files should be included"


def test_copy_packages_preserves_structure():
    """
    Test _copy_packages() preserves package directory structure.

    Verifies that nested packages and modules are copied correctly.
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        with tempfile.TemporaryDirectory() as temp_install:
            install_dir = Path(temp_install)

            mock_paths = MagicMock()
            mock_paths.daemon_home = Path("/mock/daemon")
            mock_paths.install_dir = install_dir
            mock_get_paths.return_value = mock_paths

            installer = GraphitiInstaller()

            # Create nested package structure
            with tempfile.TemporaryDirectory() as temp_src:
                src_root = Path(temp_src)

                mcp_src = src_root / "mcp_server"
                mcp_src.mkdir()
                (mcp_src / "__init__.py").touch()

                # Create nested subpackage
                daemon_pkg = mcp_src / "daemon"
                daemon_pkg.mkdir()
                (daemon_pkg / "__init__.py").touch()
                (daemon_pkg / "installer.py").touch()

                core_src = src_root / "graphiti_core"
                core_src.mkdir()
                (core_src / "__init__.py").touch()

                # Copy packages
                installer._copy_packages((mcp_src, core_src))

                # Verify structure preserved
                lib_mcp = install_dir / "lib" / "mcp_server"
                lib_daemon = lib_mcp / "daemon"

                assert lib_daemon.exists(), \
                    "Nested subpackage should be copied"
                assert (lib_daemon / "__init__.py").exists(), \
                    "Nested __init__.py should be copied"
                assert (lib_daemon / "installer.py").exists(), \
                    "Nested modules should be copied"


def test_verify_frozen_packages_completeness():
    """
    (P0) Test _verify_frozen_packages() checks package completeness.

    Verifies that all __init__.py files are present in frozen packages.
    """
    from mcp_server.daemon.installer import GraphitiInstaller, InstallationError

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        with tempfile.TemporaryDirectory() as temp_install:
            install_dir = Path(temp_install)
            lib_dir = install_dir / "lib"
            lib_dir.mkdir()

            mock_paths = MagicMock()
            mock_paths.daemon_home = Path("/mock/daemon")
            mock_paths.install_dir = install_dir
            mock_get_paths.return_value = mock_paths

            installer = GraphitiInstaller()

            # Create complete frozen packages with all critical files
            mcp_pkg = lib_dir / "mcp_server"
            mcp_pkg.mkdir()
            (mcp_pkg / "__init__.py").touch()
            (mcp_pkg / "graphiti_mcp_server.py").touch()  # Critical file

            daemon_pkg = mcp_pkg / "daemon"
            daemon_pkg.mkdir()
            (daemon_pkg / "__init__.py").touch()

            config_pkg = mcp_pkg / "config"
            config_pkg.mkdir()
            (config_pkg / "__init__.py").touch()

            core_pkg = lib_dir / "graphiti_core"
            core_pkg.mkdir()
            (core_pkg / "__init__.py").touch()

            # Verification should pass
            installer._verify_frozen_packages()

            # Now test with missing critical file
            (mcp_pkg / "graphiti_mcp_server.py").unlink()

            # Verification should fail
            with pytest.raises(InstallationError) as exc_info:
                installer._verify_frozen_packages()

            error_msg = str(exc_info.value).lower()
            assert "missing" in error_msg or "graphiti_mcp_server" in error_msg or "critical" in error_msg, \
                "Error should mention missing critical file"


def test_frozen_packages_importable():
    """
    (P0) Test frozen packages are importable with PYTHONPATH set.

    Verifies that frozen packages can be imported when lib/ is in PYTHONPATH.
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        with tempfile.TemporaryDirectory() as temp_install:
            install_dir = Path(temp_install)
            lib_dir = install_dir / "lib"
            lib_dir.mkdir()

            mock_paths = MagicMock()
            mock_paths.daemon_home = Path("/mock/daemon")
            mock_paths.install_dir = install_dir
            mock_get_paths.return_value = mock_paths

            installer = GraphitiInstaller()

            # Create frozen packages with unique module names to avoid conflicts
            frozen_mcp_pkg = lib_dir / "frozen_mcp_test"
            frozen_mcp_pkg.mkdir()
            (frozen_mcp_pkg / "__init__.py").write_text("VERSION = '2.1.0'")

            frozen_core_pkg = lib_dir / "frozen_core_test"
            frozen_core_pkg.mkdir()
            (frozen_core_pkg / "__init__.py").write_text("CORE_VERSION = '1.0.0'")

            # Add lib to Python path and test import
            import sys
            sys.path.insert(0, str(lib_dir))

            try:
                # Import frozen packages (using unique names to avoid conflicts)
                import frozen_mcp_test
                import frozen_core_test

                # Verify imports succeeded
                assert hasattr(frozen_mcp_test, 'VERSION'), \
                    "Frozen package should be importable"
                assert frozen_mcp_test.VERSION == '2.1.0', \
                    "Frozen package should have correct content"

                assert hasattr(frozen_core_test, 'CORE_VERSION'), \
                    "Frozen package should be importable"
                assert frozen_core_test.CORE_VERSION == '1.0.0', \
                    "Frozen package should have correct content"

            finally:
                # Cleanup: Remove from path and delete imported modules
                sys.path.remove(str(lib_dir))
                if 'frozen_mcp_test' in sys.modules:
                    del sys.modules['frozen_mcp_test']
                if 'frozen_core_test' in sys.modules:
                    del sys.modules['frozen_core_test']


def test_freeze_packages_end_to_end():
    """
    Test complete _freeze_packages() workflow end-to-end.

    Integration test covering the full frozen package deployment.
    """
    from mcp_server.daemon.installer import GraphitiInstaller

    with patch('mcp_server.daemon.installer.get_paths') as mock_get_paths:
        with tempfile.TemporaryDirectory() as temp_install:
            install_dir = Path(temp_install)

            mock_paths = MagicMock()
            mock_paths.daemon_home = Path("/mock/daemon")
            mock_paths.install_dir = install_dir
            mock_get_paths.return_value = mock_paths

            installer = GraphitiInstaller()

            # Create source repository structure
            with tempfile.TemporaryDirectory() as temp_repo:
                repo_root = Path(temp_repo)

                # Create mcp_server package with critical files
                mcp_src = repo_root / "mcp_server"
                mcp_src.mkdir()
                (mcp_src / "__init__.py").write_text("# mcp_server v2.1.0")
                (mcp_src / "graphiti_mcp_server.py").write_text("# main MCP server")  # Critical file

                daemon_src = mcp_src / "daemon"
                daemon_src.mkdir()
                (daemon_src / "__init__.py").write_text("# daemon")
                (daemon_src / "installer.py").write_text("# installer module")

                config_src = mcp_src / "config"
                config_src.mkdir()
                (config_src / "__init__.py").write_text("# config")

                # Create graphiti_core package (directly under repo_root)
                core_src = repo_root / "graphiti_core"
                core_src.mkdir()
                (core_src / "__init__.py").write_text("# graphiti_core")
                (core_src / "engine.py").write_text("# engine module")

                # Add some excluded items
                (mcp_src / "test.pyc").touch()
                pycache = daemon_src / "__pycache__"
                pycache.mkdir()
                (pycache / "installer.cpython-313.pyc").touch()

                # Execute frozen package deployment
                installer._freeze_packages(repo_root)

                # Verify results
                lib_dir = install_dir / "lib"
                assert lib_dir.exists(), "lib/ directory should be created"

                # Verify mcp_server copied correctly
                lib_mcp = lib_dir / "mcp_server"
                assert lib_mcp.exists(), "mcp_server should be copied"
                assert (lib_mcp / "__init__.py").exists(), \
                    "mcp_server __init__.py should exist"
                assert (lib_mcp / "graphiti_mcp_server.py").exists(), \
                    "mcp_server critical file should exist"
                assert (lib_mcp / "daemon" / "installer.py").exists(), \
                    "Nested modules should be copied"
                assert (lib_mcp / "config" / "__init__.py").exists(), \
                    "Config package should be copied"

                # Verify graphiti_core copied correctly
                lib_core = lib_dir / "graphiti_core"
                assert lib_core.exists(), "graphiti_core should be copied"
                assert (lib_core / "__init__.py").exists(), \
                    "graphiti_core __init__.py should exist"
                assert (lib_core / "engine.py").exists(), \
                    "Core modules should be copied"

                # Verify exclusions worked
                assert not (lib_mcp / "test.pyc").exists(), \
                    ".pyc files should be excluded"
                assert not (lib_mcp / "daemon" / "__pycache__").exists(), \
                    "__pycache__ should be excluded"

                # Verify package manifest created
                manifest = lib_dir / "PACKAGE_MANIFEST.json"
                assert manifest.exists(), "Package manifest should be created"
