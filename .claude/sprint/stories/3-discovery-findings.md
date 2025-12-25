# Story 3.d: Path Resolution Test Suite - Discovery Findings

**Status**: in_progress
**Date**: 2025-12-25
**Phase**: Discovery

## Overview

Comprehensive test scenarios for `mcp_server/daemon/paths.py` covering all three platforms (Windows, macOS, Linux) with edge cases and mocking strategies.

---

## Test Scenarios for Windows Edge Cases

### Scenario 1: Missing LOCALAPPDATA Environment Variable
**Context**: LOCALAPPDATA might be missing in minimal environments or custom shells
**Test Case**:
- Mock: `os.environ` without LOCALAPPDATA key
- Expected: Fallback to `Path.home() / "AppData" / "Local"`
- Verify paths:
  - `install_dir` = `{home}/AppData/Local/Programs/Graphiti`
  - `config_dir` = `{home}/AppData/Local/Graphiti/config`
  - `state_dir` = `{home}/AppData/Local/Graphiti`
  - `config_file` = `{home}/AppData/Local/Graphiti/config/graphiti.config.json`

### Scenario 2: LOCALAPPDATA Set to Custom Path
**Context**: Users can customize LOCALAPPDATA via environment
**Test Case**:
- Mock: `os.environ["LOCALAPPDATA"] = "C:/CustomAppData"`
- Expected: Respect custom LOCALAPPDATA
- Verify paths:
  - `install_dir` = `C:/CustomAppData/Programs/Graphiti`
  - `config_dir` = `C:/CustomAppData/Graphiti/config`
  - `state_dir` = `C:/CustomAppData/Graphiti`

### Scenario 3: Path.home() Failure
**Context**: In rare cases, Path.home() might fail (e.g., no HOME/USERPROFILE)
**Test Case**:
- Mock: `Path.home()` raises RuntimeError
- Expected: Should propagate error (no silent failure)
- Action: Document that LOCALAPPDATA fallback assumes Path.home() works

### Scenario 4: Windows Path Separators
**Context**: Verify Windows uses backslashes in Path objects
**Test Case**:
- Mock: `sys.platform = "win32"`
- Expected: All paths use Windows-native separators
- Verify: `str(install_dir)` contains backslashes (when converted to string)

### Scenario 5: get_log_dir() and get_data_dir() on Windows
**Context**: Windows uses subdirectories under state_dir
**Test Case**:
- Mock: `sys.platform = "win32"`
- Expected:
  - `get_log_dir()` = `{state_dir}/logs`
  - `get_data_dir()` = `{state_dir}/data`

---

## Test Scenarios for macOS Edge Cases

### Scenario 1: Fixed Library Paths (No Environment Overrides)
**Context**: macOS ignores XDG variables, uses fixed Library paths
**Test Case**:
- Mock: `sys.platform = "darwin"`, set XDG_* environment variables
- Expected: XDG variables ignored
- Verify paths:
  - `install_dir` = `{home}/Library/Application Support/Graphiti`
  - `config_dir` = `{home}/Library/Preferences/Graphiti`
  - `state_dir` = `{home}/Library/Logs/Graphiti`

### Scenario 2: Space in Application Support Path
**Context**: "Application Support" contains space
**Test Case**:
- Mock: `sys.platform = "darwin"`
- Expected: Path handles spaces correctly
- Verify: `install_dir` = `{home}/Library/Application Support/Graphiti` (no escaping needed in Path)

### Scenario 3: get_log_dir() Returns state_dir on macOS
**Context**: macOS state_dir already points to Logs
**Test Case**:
- Mock: `sys.platform = "darwin"`
- Expected: `get_log_dir()` == `state_dir` (no /logs subdirectory)
- Verify: `get_log_dir()` = `{home}/Library/Logs/Graphiti`

### Scenario 4: get_data_dir() Uses Caches on macOS
**Context**: macOS uses separate Caches directory for data
**Test Case**:
- Mock: `sys.platform = "darwin"`
- Expected: `get_data_dir()` != `state_dir` subdirectory
- Verify: `get_data_dir()` = `{home}/Library/Caches/Graphiti`

### Scenario 5: Path.home() on macOS
**Context**: Verify macOS uses forward slashes
**Test Case**:
- Mock: `sys.platform = "darwin"`
- Expected: All paths use POSIX-style separators
- Verify: `str(install_dir)` contains forward slashes

---

## Test Scenarios for Linux XDG Edge Cases

### Scenario 1: All XDG Variables Missing
**Context**: Minimal Linux environment without XDG variables
**Test Case**:
- Mock: `os.environ` without XDG_DATA_HOME, XDG_CONFIG_HOME, XDG_STATE_HOME
- Expected: Fallback to XDG Base Directory defaults
- Verify paths:
  - `install_dir` = `{home}/.local/share/graphiti`
  - `config_dir` = `{home}/.config/graphiti`
  - `state_dir` = `{home}/.local/state/graphiti`

### Scenario 2: Partial XDG Variables Set
**Context**: User sets only some XDG variables
**Test Case**:
- Mock: `XDG_CONFIG_HOME = "/custom/config"`, others missing
- Expected: Use custom config, fallback for others
- Verify:
  - `install_dir` = `{home}/.local/share/graphiti`
  - `config_dir` = `/custom/config/graphiti`
  - `state_dir` = `{home}/.local/state/graphiti`

### Scenario 3: All XDG Variables Custom
**Context**: User fully customizes XDG Base Directory
**Test Case**:
- Mock: All XDG_* variables set to custom paths
- Expected: Respect all custom paths
- Verify:
  - `install_dir` = `{XDG_DATA_HOME}/graphiti`
  - `config_dir` = `{XDG_CONFIG_HOME}/graphiti`
  - `state_dir` = `{XDG_STATE_HOME}/graphiti`

### Scenario 4: XDG Variables with Trailing Slashes
**Context**: User sets XDG variables with trailing slashes
**Test Case**:
- Mock: `XDG_DATA_HOME = "/custom/data/"` (trailing slash)
- Expected: Path handles trailing slashes correctly
- Verify: `install_dir` = `/custom/data/graphiti` (not `/custom/data//graphiti`)

### Scenario 5: get_log_dir() and get_data_dir() on Linux
**Context**: Linux uses subdirectories under state_dir
**Test Case**:
- Mock: `sys.platform = "linux"`
- Expected:
  - `get_log_dir()` = `{state_dir}/logs`
  - `get_data_dir()` = `{state_dir}/data`

### Scenario 6: Non-Standard sys.platform (FreeBSD, etc.)
**Context**: Code uses `else` clause for non-Windows/macOS platforms
**Test Case**:
- Mock: `sys.platform = "freebsd12"`
- Expected: Treated like Linux (XDG spec)
- Verify: Same behavior as Linux test scenarios

---

## Mocking Strategy for Cross-Platform Testing

### Primary Mock: sys.platform

**Approach**: Use `unittest.mock.patch` to mock `sys.platform`

**Implementation Pattern**:
```python
from unittest.mock import patch

@patch('sys.platform', 'win32')
def test_windows_paths():
    # sys.platform is now 'win32' for this test
    from mcp_server.daemon.paths import get_paths
    paths = get_paths()
    # assertions here
```

**Key Insight**: Patch `sys.platform` at the module level where it's used, not globally.

**Correct Target**: `'mcp_server.daemon.paths.sys.platform'` (where it's imported in paths.py)

### Secondary Mock: os.environ

**Approach**: Use `patch.dict` to temporarily modify environment variables

**Implementation Pattern**:
```python
from unittest.mock import patch

@patch('sys.platform', 'win32')
@patch.dict('os.environ', {}, clear=True)  # Clear all env vars
def test_windows_missing_localappdata():
    from mcp_server.daemon.paths import get_paths
    paths = get_paths()
    # assertions here
```

**Key Features**:
- `clear=True`: Remove all environment variables
- `{}`: Empty dict means no variables set
- Can also use `{'KEY': 'value'}` to set specific variables

### Tertiary Mock: Path.home()

**Approach**: Mock `pathlib.Path.home()` for home directory control

**Implementation Pattern**:
```python
from unittest.mock import patch, MagicMock
from pathlib import Path

@patch('sys.platform', 'win32')
@patch('pathlib.Path.home')
def test_custom_home(mock_home):
    mock_home.return_value = Path('C:/Users/TestUser')
    from mcp_server.daemon.paths import get_paths
    paths = get_paths()
    # assertions here
```

**Key Insight**: Mock at `pathlib.Path.home`, not `Path.home()` (method vs call).

### Module Reload Strategy

**Problem**: Once `paths.py` is imported, `sys.platform` is already evaluated
**Solution**: Use `importlib.reload()` or mock before import

**Pattern 1: Mock Before Import** (Preferred)
```python
@patch('sys.platform', 'darwin')
def test_macos_paths():
    # Import happens INSIDE test, after mock is active
    from mcp_server.daemon.paths import get_paths
    paths = get_paths()
    # assertions
```

**Pattern 2: Module Reload** (If needed)
```python
import importlib
from mcp_server.daemon import paths

@patch('sys.platform', 'linux')
def test_linux_paths():
    importlib.reload(paths)  # Reload module with mocked platform
    result = paths.get_paths()
    # assertions
```

**Recommendation**: Use Pattern 1 (mock before import) for cleaner tests.

### Test Isolation Strategy

**Approach**: Each test should be independent

**Implementation**:
1. Use `@patch` decorators to isolate each test
2. Import `get_paths` inside each test (after mocks active)
3. Avoid global state between tests
4. Use `setUp`/`tearDown` for cleanup if needed

**Example Template**:
```python
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

class TestWindowsPaths(unittest.TestCase):

    @patch('sys.platform', 'win32')
    @patch.dict('os.environ', {'LOCALAPPDATA': 'C:/CustomAppData'})
    def test_custom_localappdata(self):
        from mcp_server.daemon.paths import get_paths
        paths = get_paths()
        self.assertEqual(paths.install_dir, Path('C:/CustomAppData/Programs/Graphiti'))
        self.assertEqual(paths.config_dir, Path('C:/CustomAppData/Graphiti/config'))
```

---

## Coverage Targets

### Primary Functions (Must Test):
- `get_paths()` - 100% coverage across all platforms
- `get_install_dir()` - Verify delegation to `get_paths()`
- `get_config_dir()` - Verify delegation to `get_paths()`
- `get_config_file()` - Verify delegation to `get_paths()`
- `get_log_dir()` - Platform-specific logic (macOS vs others)
- `get_data_dir()` - Platform-specific logic (macOS vs others)

### Branching Coverage:
- `sys.platform == "win32"` branch
- `sys.platform == "darwin"` branch
- `else` branch (Linux and others)
- Environment variable presence/absence for each platform

### Edge Case Coverage:
- Missing environment variables (LOCALAPPDATA, XDG_*)
- Custom environment variable values
- Path.home() behavior
- Trailing slashes in paths
- Special characters in paths (spaces, unicode)

### Target Metrics:
- Line coverage: >90%
- Branch coverage: >85%
- All 6 public functions tested
- All 3 platforms tested

---

## Test File Structure

### Proposed Test Organization:
```
tests/
└── test_daemon_paths.py
    ├── TestWindowsPaths (TestCase)
    │   ├── test_default_paths
    │   ├── test_missing_localappdata
    │   ├── test_custom_localappdata
    │   ├── test_log_dir
    │   ├── test_data_dir
    │   └── test_convenience_functions
    ├── TestMacOSPaths (TestCase)
    │   ├── test_fixed_library_paths
    │   ├── test_ignores_xdg_variables
    │   ├── test_application_support_space
    │   ├── test_log_dir_is_state_dir
    │   ├── test_data_dir_uses_caches
    │   └── test_convenience_functions
    ├── TestLinuxPaths (TestCase)
    │   ├── test_default_xdg_paths
    │   ├── test_missing_xdg_variables
    │   ├── test_partial_xdg_variables
    │   ├── test_all_custom_xdg_variables
    │   ├── test_trailing_slashes
    │   ├── test_log_dir
    │   ├── test_data_dir
    │   └── test_convenience_functions
    └── TestPathTypes (TestCase)
        ├── test_returns_path_objects
        ├── test_paths_are_absolute
        └── test_graphiti_paths_namedtuple
```

### Estimated Test Count:
- Windows: 6 tests
- macOS: 6 tests
- Linux: 8 tests
- Path types: 3 tests
- **Total**: ~23 tests

---

## Implementation Recommendations

### Test Framework: pytest or unittest
**Recommendation**: Use `unittest` (Python standard library)
**Rationale**:
- No external dependencies
- Built-in mocking support (`unittest.mock`)
- Familiar to most Python developers
- Matches Graphiti's existing test style

### Assertion Style:
```python
# Use assertEqual for path comparison
self.assertEqual(paths.install_dir, expected_path)

# Use assertTrue/assertFalse for boolean checks
self.assertTrue(paths.install_dir.is_absolute())

# Use assertIsInstance for type checks
self.assertIsInstance(paths, GraphitiPaths)
```

### Mock Verification:
```python
# Verify environment variable reads
with patch.dict('os.environ', {'LOCALAPPDATA': 'test'}, clear=True):
    paths = get_paths()
    # os.environ.get() was called with 'LOCALAPPDATA'
```

### Parameterized Tests (Optional):
Consider using `@unittest.parameterized` for similar test cases:
```python
from parameterized import parameterized

@parameterized.expand([
    ('win32', 'LOCALAPPDATA', 'C:/Users/Test/AppData/Local'),
    ('darwin', None, '/Users/Test/Library'),
    ('linux', 'XDG_DATA_HOME', '/home/test/.local/share'),
])
def test_platform_detection(self, platform, env_var, expected_substring):
    # Test with different platforms
    pass
```

---

## Risk Analysis

### Low Risk:
- Path concatenation (Path object handles this)
- Platform detection (sys.platform is reliable)

### Medium Risk:
- Environment variable handling (need thorough edge case testing)
- Path.home() in minimal environments (rare but possible)

### High Risk:
- Mock leakage between tests (must ensure isolation)
- Platform-specific path separator assumptions (Path handles this)

### Mitigation:
- Use `@patch` decorators for automatic cleanup
- Import inside tests to avoid module caching issues
- Test with both string and Path comparisons
- Verify Path objects, not string representations

---

## Acceptance Criteria Mapping

### (d) Discovery Phase ✓
- [x] Define test scenarios for Windows edge cases → 5 scenarios defined
- [x] Define test scenarios for macOS edge cases → 5 scenarios defined
- [x] Define test scenarios for Linux XDG edge cases → 6 scenarios defined
- [x] Identify how to mock sys.platform for cross-platform testing → Mocking strategy documented

### Next Phase: (i) Implementation
Ready to proceed with test file creation based on these findings.

---

## Summary

**Total Test Scenarios**: 16 edge cases + 3 platform defaults = 19 distinct test scenarios

**Mocking Tools**:
1. `@patch('sys.platform', '<platform>')` - Platform simulation
2. `@patch.dict('os.environ', {...}, clear=True)` - Environment control
3. `@patch('pathlib.Path.home')` - Home directory control

**Coverage Strategy**:
- All 6 public functions
- All 3 platforms (Windows, macOS, Linux)
- All environment variable branches
- All edge cases documented

**Estimated Implementation Time**: 2-3 hours for 23 tests + fixtures

**Next Step**: Create `tests/test_daemon_paths.py` implementing all scenarios
