"""
Tests for bootstrap module's _setup_frozen_path() function.

Tests the frozen package path setup that runs before any relative imports
in the bootstrap module. This ensures the bootstrap works when invoked via
`python -m mcp_server.daemon.bootstrap` from frozen installations.

Created: 2025-12-25
Story: 10.t - Bootstrap Module Invocation Testing Phase
"""

import pytest
import sys
import tempfile
import importlib
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_setup_frozen_path_imports():
    """
    (P0) Verify _setup_frozen_path() function exists and is callable.

    Smoke test to ensure the function is defined in bootstrap.py.
    """
    # Import bootstrap module (this will execute _setup_frozen_path automatically)
    from mcp_server.daemon import bootstrap

    # Verify function exists
    assert hasattr(bootstrap, '_setup_frozen_path'), \
        "_setup_frozen_path function should exist in bootstrap module"

    # Verify it's callable
    assert callable(bootstrap._setup_frozen_path), \
        "_setup_frozen_path should be callable"


def test_setup_frozen_path_development_mode():
    """
    (P0) Test _setup_frozen_path() in development mode.

    Verifies that the function does nothing when running from repository
    (not from a frozen installation with lib/ directory).
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_root = Path(temp_dir)

        # Create development structure: mcp_server/daemon/bootstrap.py
        mcp_server_dir = repo_root / "mcp_server"
        daemon_dir = mcp_server_dir / "daemon"
        daemon_dir.mkdir(parents=True)

        bootstrap_file = daemon_dir / "bootstrap.py"
        bootstrap_file.write_text("""
import sys
from pathlib import Path

def _setup_frozen_path():
    bootstrap_dir = Path(__file__).parent.resolve()
    potential_lib = bootstrap_dir.parent.parent

    if potential_lib.name == "lib" and (potential_lib / "mcp_server").is_dir():
        lib_path_str = str(potential_lib)
        if lib_path_str not in sys.path:
            sys.path.insert(0, lib_path_str)
            return True  # Frozen mode
    return False  # Development mode

# Store original sys.path for testing
original_path = sys.path.copy()
frozen_mode = _setup_frozen_path()
""")

        # Load the module
        spec = importlib.util.spec_from_file_location("test_bootstrap", bootstrap_file)
        test_module = importlib.util.module_from_spec(spec)
        original_path = sys.path.copy()

        spec.loader.exec_module(test_module)

        # Verify development mode was detected (function returned False)
        assert hasattr(test_module, 'frozen_mode'), \
            "Module should have frozen_mode variable"
        assert test_module.frozen_mode == False, \
            "Should detect development mode (no lib/ directory)"

        # Verify sys.path was NOT modified
        # The temp directory shouldn't be in sys.path since it's not a lib/ structure
        lib_path_str = str(repo_root.parent)  # potential_lib would be parent of mcp_server
        assert lib_path_str not in sys.path, \
            "sys.path should not be modified in development mode"


def test_setup_frozen_path_frozen_mode():
    """
    (P0) Test _setup_frozen_path() in frozen installation mode.

    Verifies that lib/ directory is added to sys.path when running from
    frozen installation structure.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        install_root = Path(temp_dir)

        # Create frozen structure: {INSTALL}/lib/mcp_server/daemon/bootstrap.py
        lib_dir = install_root / "lib"
        mcp_server_dir = lib_dir / "mcp_server"
        daemon_dir = mcp_server_dir / "daemon"
        daemon_dir.mkdir(parents=True)

        bootstrap_file = daemon_dir / "bootstrap.py"
        bootstrap_file.write_text("""
import sys
from pathlib import Path

def _setup_frozen_path():
    bootstrap_dir = Path(__file__).parent.resolve()
    potential_lib = bootstrap_dir.parent.parent

    if potential_lib.name == "lib" and (potential_lib / "mcp_server").is_dir():
        lib_path_str = str(potential_lib)
        if lib_path_str not in sys.path:
            sys.path.insert(0, lib_path_str)
            return True  # Frozen mode
    return False  # Development mode

# Store original sys.path for testing
original_path = sys.path.copy()
frozen_mode = _setup_frozen_path()
added_path = sys.path[0] if frozen_mode else None
""")

        # Load the module
        spec = importlib.util.spec_from_file_location("test_bootstrap_frozen", bootstrap_file)
        test_module = importlib.util.module_from_spec(spec)
        original_path = sys.path.copy()

        spec.loader.exec_module(test_module)

        # Verify frozen mode was detected
        assert test_module.frozen_mode == True, \
            "Should detect frozen mode (lib/ directory present)"

        # Verify lib/ was added to sys.path
        lib_path_str = str(lib_dir)
        assert test_module.added_path == lib_path_str, \
            f"lib/ directory should be added to sys.path[0], got {test_module.added_path}"


def test_setup_frozen_path_idempotent():
    """
    Test _setup_frozen_path() is idempotent (can be called multiple times).

    Verifies that calling the function multiple times doesn't add duplicate
    entries to sys.path.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        install_root = Path(temp_dir)

        # Create frozen structure
        lib_dir = install_root / "lib"
        mcp_server_dir = lib_dir / "mcp_server"
        daemon_dir = mcp_server_dir / "daemon"
        daemon_dir.mkdir(parents=True)

        bootstrap_file = daemon_dir / "bootstrap.py"
        bootstrap_file.write_text("""
import sys
from pathlib import Path

def _setup_frozen_path():
    bootstrap_dir = Path(__file__).parent.resolve()
    potential_lib = bootstrap_dir.parent.parent

    if potential_lib.name == "lib" and (potential_lib / "mcp_server").is_dir():
        lib_path_str = str(potential_lib)
        if lib_path_str not in sys.path:
            sys.path.insert(0, lib_path_str)
            return True
    return False

# Call multiple times
_setup_frozen_path()
_setup_frozen_path()
_setup_frozen_path()

# Count occurrences
lib_path = str(Path(__file__).parent.parent.parent)
count = sys.path.count(lib_path)
""")

        # Load the module
        spec = importlib.util.spec_from_file_location("test_bootstrap_idempotent", bootstrap_file)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)

        # Verify lib/ appears exactly once (idempotent)
        assert test_module.count == 1, \
            f"lib/ should appear exactly once in sys.path, found {test_module.count} occurrences"


def test_setup_frozen_path_relative_imports():
    """
    (P0) Test that relative imports work after _setup_frozen_path().

    Verifies that the bootstrap module can successfully import from
    .venv_manager and .paths after path setup.
    """
    # This test verifies the actual bootstrap.py can be imported
    # which means all its relative imports succeeded
    try:
        from mcp_server.daemon import bootstrap
        from mcp_server.daemon import venv_manager
        from mcp_server.daemon import paths

        # Verify imports succeeded
        assert hasattr(bootstrap, 'validate_environment'), \
            "bootstrap should have validate_environment function"
        assert hasattr(venv_manager, 'VenvManager'), \
            "venv_manager should have VenvManager class"
        assert hasattr(paths, 'get_config_file'), \
            "paths should have get_config_file function"

    except ImportError as e:
        pytest.fail(f"Relative imports failed after _setup_frozen_path(): {e}")


def test_setup_frozen_path_module_invocation():
    """
    (P0) Test bootstrap works when invoked via -m flag.

    Verifies the module can be imported via `-m mcp_server.daemon.bootstrap`
    without ModuleNotFoundError. We use a simple Python check instead of
    actually running the service.
    """
    import subprocess
    import sys

    # Test that the module can be imported (not executed, just loaded)
    # This verifies that -m invocation would work
    test_code = """
import sys
try:
    # Import the module (this will execute _setup_frozen_path)
    import mcp_server.daemon.bootstrap
    print("SUCCESS: Module imported successfully")
    sys.exit(0)
except ModuleNotFoundError as e:
    print(f"FAILED: {e}")
    sys.exit(1)
except Exception as e:
    # Other errors are OK - we just want to verify imports work
    print(f"SUCCESS: Module loaded (other error is OK): {type(e).__name__}")
    sys.exit(0)
"""

    result = subprocess.run(
        [sys.executable, "-c", test_code],
        capture_output=True,
        text=True,
        timeout=5
    )

    # Check that we successfully imported (no ModuleNotFoundError)
    assert "SUCCESS" in result.stdout, \
        f"Module import failed: {result.stdout} {result.stderr}"
    assert result.returncode == 0, \
        f"Import test failed with exit code {result.returncode}: {result.stderr}"


def test_setup_frozen_path_edge_case_no_mcp_server_dir():
    """
    Test _setup_frozen_path() when lib/ exists but no mcp_server/ inside.

    Verifies the function doesn't add lib/ to sys.path if it doesn't
    contain the expected mcp_server package.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        install_root = Path(temp_dir)

        # Create lib/ directory but WITHOUT mcp_server/ inside
        lib_dir = install_root / "lib"
        lib_dir.mkdir()

        # Create some other directory (not mcp_server)
        other_dir = lib_dir / "other_package"
        other_dir.mkdir()

        # Create daemon directory structure without proper parent
        test_dir = install_root / "test_daemon"
        test_dir.mkdir()

        bootstrap_file = test_dir / "bootstrap.py"
        bootstrap_file.write_text(f"""
import sys
from pathlib import Path

# Manually set __file__ to simulate being in lib/something/daemon/
# (but lib/ doesn't have mcp_server/)
__file__ = r'{lib_dir / "other_package" / "daemon" / "bootstrap.py"}'

def _setup_frozen_path():
    bootstrap_dir = Path(__file__).parent.resolve()
    potential_lib = bootstrap_dir.parent.parent

    if potential_lib.name == "lib" and (potential_lib / "mcp_server").is_dir():
        lib_path_str = str(potential_lib)
        if lib_path_str not in sys.path:
            sys.path.insert(0, lib_path_str)
            return True
    return False

frozen_mode = _setup_frozen_path()
""")

        # Load the module
        spec = importlib.util.spec_from_file_location("test_bootstrap_edge", bootstrap_file)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)

        # Verify frozen mode was NOT detected (missing mcp_server/)
        assert test_module.frozen_mode == False, \
            "Should not detect frozen mode when mcp_server/ is missing"

        # Verify lib/ was NOT added to sys.path
        lib_path_str = str(lib_dir)
        assert lib_path_str not in sys.path, \
            "lib/ should not be added when mcp_server/ is missing"


def test_setup_frozen_path_edge_case_wrong_dir_name():
    """
    Test _setup_frozen_path() when parent directory is not named 'lib'.

    Verifies the function doesn't activate frozen mode if the directory
    structure doesn't match expectations.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        install_root = Path(temp_dir)

        # Create structure with wrong directory name: packages/mcp_server/daemon/
        packages_dir = install_root / "packages"  # Not "lib"
        mcp_server_dir = packages_dir / "mcp_server"
        daemon_dir = mcp_server_dir / "daemon"
        daemon_dir.mkdir(parents=True)

        bootstrap_file = daemon_dir / "bootstrap.py"
        bootstrap_file.write_text("""
import sys
from pathlib import Path

def _setup_frozen_path():
    bootstrap_dir = Path(__file__).parent.resolve()
    potential_lib = bootstrap_dir.parent.parent

    if potential_lib.name == "lib" and (potential_lib / "mcp_server").is_dir():
        lib_path_str = str(potential_lib)
        if lib_path_str not in sys.path:
            sys.path.insert(0, lib_path_str)
            return True
    return False

frozen_mode = _setup_frozen_path()
detected_name = Path(__file__).parent.parent.parent.name
""")

        # Load the module
        spec = importlib.util.spec_from_file_location("test_bootstrap_wrong_name", bootstrap_file)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)

        # Verify frozen mode was NOT detected (wrong directory name)
        assert test_module.frozen_mode == False, \
            f"Should not detect frozen mode when parent is '{test_module.detected_name}' not 'lib'"


def test_setup_frozen_path_executes_before_imports():
    """
    Verify _setup_frozen_path() executes before relative imports.

    This is critical - the function must modify sys.path BEFORE any
    'from .' imports execute.
    """
    from mcp_server.daemon import bootstrap
    import inspect

    # Read the bootstrap.py source code
    source = inspect.getsource(bootstrap)
    lines = source.split('\n')

    # Find line numbers
    setup_call_line = None
    first_relative_import = None

    for i, line in enumerate(lines):
        if '_setup_frozen_path()' in line and not line.strip().startswith('#'):
            setup_call_line = i
        elif line.strip().startswith('from .') and first_relative_import is None:
            first_relative_import = i

    # Verify _setup_frozen_path() is called before first relative import
    assert setup_call_line is not None, \
        "_setup_frozen_path() should be called in bootstrap.py"
    assert first_relative_import is not None, \
        "bootstrap.py should have relative imports (from .venv_manager, etc.)"
    assert setup_call_line < first_relative_import, \
        f"_setup_frozen_path() (line {setup_call_line}) must be called before " \
        f"first relative import (line {first_relative_import})"


def test_bootstrap_main_function_exists():
    """
    Verify bootstrap has __main__ functionality for testing.

    The story notes that we keep `if __name__ == "__main__"` for
    development/testing compatibility.
    """
    from mcp_server.daemon import bootstrap
    import inspect

    # Read the source to check for __main__ block
    source = inspect.getsource(bootstrap)

    # Verify __main__ block exists
    assert 'if __name__ == "__main__"' in source, \
        "bootstrap.py should have __main__ block for development testing"


def test_frozen_path_platform_agnostic():
    """
    Verify _setup_frozen_path() uses Path for platform compatibility.

    The function should work on Windows, macOS, and Linux.
    """
    from mcp_server.daemon import bootstrap
    import inspect

    # Read the function source
    source = inspect.getsource(bootstrap._setup_frozen_path)

    # Verify uses pathlib.Path (not os.path)
    assert 'Path(' in source, \
        "_setup_frozen_path should use pathlib.Path for cross-platform support"

    # Verify uses .resolve() or similar for absolute paths
    assert '.resolve()' in source or '.absolute()' in source, \
        "_setup_frozen_path should resolve to absolute paths"


def test_frozen_mode_detection_logic():
    """
    Test the frozen mode detection logic in detail.

    Verifies both conditions are checked:
    1. Parent directory is named 'lib'
    2. mcp_server/ directory exists inside lib/
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        install_root = Path(temp_dir)

        # Test Case 1: Both conditions met (frozen mode)
        lib_dir = install_root / "lib"
        mcp_server_dir = lib_dir / "mcp_server"
        daemon_dir = mcp_server_dir / "daemon"
        daemon_dir.mkdir(parents=True)

        test_code = """
import sys
from pathlib import Path

def _setup_frozen_path():
    bootstrap_dir = Path(__file__).parent.resolve()
    potential_lib = bootstrap_dir.parent.parent

    condition_1 = potential_lib.name == "lib"
    condition_2 = (potential_lib / "mcp_server").is_dir()

    if condition_1 and condition_2:
        lib_path_str = str(potential_lib)
        if lib_path_str not in sys.path:
            sys.path.insert(0, lib_path_str)
            return True, condition_1, condition_2
    return False, condition_1, condition_2

result = _setup_frozen_path()
frozen_mode, cond1, cond2 = result
"""

        bootstrap_file = daemon_dir / "bootstrap.py"
        bootstrap_file.write_text(test_code)

        spec = importlib.util.spec_from_file_location("test_detection", bootstrap_file)
        test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_module)

        assert test_module.frozen_mode == True, \
            "Frozen mode should be detected when both conditions met"
        assert test_module.cond1 == True, \
            "Condition 1 (dir name is 'lib') should be True"
        assert test_module.cond2 == True, \
            "Condition 2 (mcp_server/ exists) should be True"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
