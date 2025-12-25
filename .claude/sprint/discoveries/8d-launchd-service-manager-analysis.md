# Story 8.d Discovery: LaunchdServiceManager Analysis

**Story**: Update LaunchdServiceManager (macOS)
**Phase**: Discovery
**Date**: 2025-12-25
**Status**: Complete

## Executive Summary

The current `LaunchdServiceManager` implementation uses venv-based paths and needs to be updated to support the v2.1 frozen package architecture. The primary changes involve:

1. Updating ProgramArguments to use frozen Python executable from `{INSTALL_DIR}/bin/python`
2. Adding PYTHONPATH environment variable pointing to `{INSTALL_DIR}/lib`
3. Updating WorkingDirectory to `{INSTALL_DIR}`
4. Log paths already use `get_log_dir()` - minimal changes needed

## Current Implementation Analysis

### File Location
- Path: `mcp_server/daemon/launchd_service.py`
- Lines of code: 226
- Current dependencies: `VenvManager`, `get_log_dir()` from `paths.py`

### Current Path Usage

#### 1. Python Executable (Line 39)
```python
self.python_exe = self.venv_manager.get_python_executable()
```
**Issue**: Uses venv Python, not frozen installation Python
**Target**: Should use `{INSTALL_DIR}/bin/python`

#### 2. Bootstrap Script (Lines 44-47)
```python
def _get_bootstrap_path(self) -> Path:
    """Get path to bootstrap.py script."""
    # bootstrap.py is in mcp_server/daemon/
    return Path(__file__).parent / "bootstrap.py"
```
**Issue**: Uses relative path to source file, not frozen package location
**Target**: Should use module invocation `-m mcp_server.daemon.bootstrap`

#### 3. WorkingDirectory (Line 63)
```python
"WorkingDirectory": str(self.bootstrap_script.parent),
```
**Issue**: Points to `mcp_server/daemon/` directory
**Target**: Should use `{INSTALL_DIR}` from `get_install_dir()`

#### 4. Log Directory (Line 42)
```python
self.log_dir = get_log_dir()
```
**Status**: CORRECT - Already uses paths.py
**Behavior**: Returns `~/Library/Logs/Graphiti/` on macOS (correct per paths.py lines 85-86)

#### 5. Plist Path (Line 41)
```python
self.plist_path = Path.home() / "Library" / "LaunchAgents" / f"{self.service_id}.plist"
```
**Status**: CORRECT - Standard macOS location, no changes needed

### Current Plist Template (Lines 49-69)

```python
def _create_plist(self) -> dict:
    """Create launchd plist configuration."""
    self.log_dir.mkdir(parents=True, exist_ok=True)

    plist = {
        "Label": self.service_id,
        "ProgramArguments": [
            str(self.python_exe),           # NEEDS UPDATE
            str(self.bootstrap_script),     # NEEDS UPDATE
        ],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(self.log_dir / "bootstrap-stdout.log"),  # OK
        "StandardErrorPath": str(self.log_dir / "bootstrap-stderr.log"), # OK
        "WorkingDirectory": str(self.bootstrap_script.parent),          # NEEDS UPDATE
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        },  # NEEDS PYTHONPATH
    }

    return plist
```

## Required Changes

### 1. Import Additional Path Functions
**Current**:
```python
from .paths import get_log_dir
```

**Required**:
```python
from .paths import get_install_dir, get_log_dir
```

### 2. Update Constructor

**Current** (Lines 27-42):
```python
def __init__(self, venv_manager: Optional[VenvManager] = None):
    """Initialize launchd service manager.

    Args:
        venv_manager: Optional VenvManager instance. If None, creates default instance.

    Raises:
        VenvCreationError: If venv doesn't exist (platform-specific location from paths.py)
    """
    self.venv_manager = venv_manager or VenvManager()
    # Get venv Python executable - raise VenvCreationError if venv doesn't exist
    # (DaemonManager.install() ensures venv exists before instantiating service managers)
    self.python_exe = self.venv_manager.get_python_executable()
    self.bootstrap_script = self._get_bootstrap_path()
    self.plist_path = Path.home() / "Library" / "LaunchAgents" / f"{self.service_id}.plist"
    self.log_dir = get_log_dir()
```

**Required Changes**:
- Remove `venv_manager` parameter (no longer needed for frozen installs)
- Remove `VenvManager` dependency
- Set `self.python_exe` to `get_install_dir() / "bin" / "python"`
- Remove `self.bootstrap_script` (use module invocation instead)
- Add `self.install_dir = get_install_dir()`

### 3. Update Plist Template

**Current ProgramArguments**:
```python
"ProgramArguments": [
    str(self.python_exe),
    str(self.bootstrap_script),
],
```

**Required ProgramArguments**:
```python
"ProgramArguments": [
    str(self.install_dir / "bin" / "python"),
    "-m",
    "mcp_server.daemon.bootstrap",
],
```

**Current EnvironmentVariables**:
```python
"EnvironmentVariables": {
    "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
},
```

**Required EnvironmentVariables**:
```python
"EnvironmentVariables": {
    "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    "PYTHONPATH": str(self.install_dir / "lib"),
},
```

**Current WorkingDirectory**:
```python
"WorkingDirectory": str(self.bootstrap_script.parent),
```

**Required WorkingDirectory**:
```python
"WorkingDirectory": str(self.install_dir),
```

### 4. Remove Obsolete Method

The `_get_bootstrap_path()` method (lines 44-47) should be removed as it's no longer needed with module invocation.

## PYTHONPATH Requirements

### Purpose
The PYTHONPATH environment variable ensures frozen packages in `{INSTALL_DIR}/lib/` are importable when the bootstrap service starts.

### Frozen Package Layout
```
~/Library/Application Support/Graphiti/    (INSTALL_DIR)
├── bin/
│   └── python                             (Python executable)
├── lib/
│   ├── mcp_server/                        (Frozen Graphiti code)
│   │   └── daemon/
│   │       └── bootstrap.py
│   └── graphiti/                          (Frozen graphiti-core)
└── ...
```

### Why PYTHONPATH is Critical

From `bootstrap.py` lines 23-58, the bootstrap service has a `_setup_frozen_path()` function that detects frozen mode:

```python
def _setup_frozen_path():
    """
    Ensure frozen packages in lib/ are importable.

    Detection:
    - Frozen mode: bootstrap.py is in {INSTALL}/lib/mcp_server/daemon/
    - Development mode: bootstrap.py is in {REPO}/mcp_server/daemon/
    """
    bootstrap_dir = Path(__file__).parent.resolve()
    potential_lib = bootstrap_dir.parent.parent  # Go up 2 levels

    if potential_lib.name == "lib" and (potential_lib / "mcp_server").is_dir():
        # Frozen installation detected
        lib_path = potential_lib
        if str(lib_path) not in sys.path:
            sys.path.insert(0, str(lib_path))
```

However, this detection happens **AFTER** the Python interpreter starts. Setting PYTHONPATH in the plist ensures:
1. The lib directory is available from process start
2. Consistent import behavior across all platforms
3. No reliance on runtime path detection

### macOS Specifics

macOS's launchd services:
- Don't inherit user shell environment
- Require explicit PATH and PYTHONPATH in plist
- Use standard `/usr/bin:/usr/local/bin` for PATH
- Need PYTHONPATH for custom package locations

## Log File Paths

### Current Behavior
```python
"StandardOutPath": str(self.log_dir / "bootstrap-stdout.log"),
"StandardErrorPath": str(self.log_dir / "bootstrap-stderr.log"),
```

Where `self.log_dir = get_log_dir()` returns `~/Library/Logs/Graphiti/` on macOS (per `paths.py` lines 85-86).

### Status
**No changes needed** - Already follows macOS conventions:
- macOS convention: `~/Library/Logs/{AppName}/`
- Current implementation: Uses `get_log_dir()` which returns correct path
- File names: `bootstrap-stdout.log` and `bootstrap-stderr.log` are appropriate

## Comparison with Other Service Managers

### SystemdServiceManager (Linux)
Similar changes required (Story 9):
- ExecStart: `{INSTALL_DIR}/bin/python -m mcp_server.daemon.bootstrap`
- Environment: `PYTHONPATH={INSTALL_DIR}/lib`
- WorkingDirectory: `{INSTALL_DIR}`

### WindowsServiceManager
Already updated in recent commits:
- Uses module invocation: `-m mcp_server.daemon.bootstrap`
- Sets WorkingDirectory to `get_install_dir()`
- Uses NSSM for service management

**Key Difference**: Windows service manager doesn't explicitly set PYTHONPATH because:
1. Windows uses different Python lookup mechanisms
2. NSSM handles environment differently
3. The frozen path detection in bootstrap.py works reliably on Windows

## Dependencies

### Story 1: Platform-Aware Path Resolution
**Status**: Completed
**Provides**: `get_install_dir()`, `get_log_dir()` functions
**Location**: `mcp_server/daemon/paths.py`

### Story 2: Migrate Daemon Modules
**Status**: Completed
**Impact**: Other daemon modules already use paths.py, LaunchdServiceManager is the last to migrate

## Risks and Considerations

### Risk 1: VenvManager Removal
**Impact**: Medium
**Description**: Constructor currently requires VenvManager for Python executable path
**Mitigation**: Replace with direct path from `get_install_dir()`, no venv needed in frozen mode

### Risk 2: Bootstrap Script Path
**Impact**: Low
**Description**: Current implementation uses file path, need to switch to module invocation
**Mitigation**: Use `-m mcp_server.daemon.bootstrap` pattern (proven in Windows/systemd)

### Risk 3: Backward Compatibility
**Impact**: Low
**Description**: Users with existing v2.0 installations may have old plist files
**Mitigation**:
- v2.0 cleanup handled by Story 13
- Fresh v2.1 install creates new plist with correct paths
- Migration from v2.0 to v2.1 is a full reinstall

### Risk 4: PYTHONPATH Priority
**Impact**: Low
**Description**: PYTHONPATH might conflict with system Python packages
**Mitigation**:
- Frozen Python is isolated in INSTALL_DIR
- No system site-packages pollution
- PYTHONPATH only adds frozen lib directory

## Implementation Plan

### Phase 1: Update Imports
- Add `get_install_dir` to imports from `paths.py`
- Remove `VenvManager` import (if not used elsewhere in file)

### Phase 2: Refactor Constructor
- Remove `venv_manager` parameter
- Replace `self.python_exe` with `self.install_dir / "bin" / "python"`
- Remove `self.bootstrap_script` assignment
- Add `self.install_dir = get_install_dir()`

### Phase 3: Update Plist Template
- Modify `_create_plist()` method:
  - Update ProgramArguments to use frozen Python + module invocation
  - Add PYTHONPATH to EnvironmentVariables
  - Update WorkingDirectory to use install_dir

### Phase 4: Remove Obsolete Code
- Delete `_get_bootstrap_path()` method

### Phase 5: Update Docstrings
- Update class docstring to reflect frozen package architecture
- Update `__init__` docstring to remove VenvManager references
- Update `_create_plist` docstring if needed

## Testing Considerations

### Unit Tests
- Mock `get_install_dir()` to return test path
- Verify plist contains correct ProgramArguments
- Verify PYTHONPATH is set in EnvironmentVariables
- Verify WorkingDirectory uses install_dir

### Integration Tests
- Fresh v2.1 install on macOS
- Verify plist file created in ~/Library/LaunchAgents/
- Verify service loads successfully with `launchctl load`
- Verify bootstrap service starts and logs to correct location
- Verify PYTHONPATH allows imports from frozen lib/

### Manual Testing Checklist
- [ ] Plist created at correct path: `~/Library/LaunchAgents/com.graphiti.bootstrap.plist`
- [ ] ProgramArguments contains: `["{INSTALL_DIR}/bin/python", "-m", "mcp_server.daemon.bootstrap"]`
- [ ] EnvironmentVariables contains: `PYTHONPATH={INSTALL_DIR}/lib`
- [ ] WorkingDirectory set to: `{INSTALL_DIR}`
- [ ] Log files created at: `~/Library/Logs/Graphiti/bootstrap-stdout.log`
- [ ] Service loads with: `launchctl load ~/Library/LaunchAgents/com.graphiti.bootstrap.plist`
- [ ] Service starts successfully
- [ ] Bootstrap service can import frozen packages

## Estimated Effort

- Discovery (this document): 1 hour - **COMPLETE**
- Implementation: 1-2 hours
  - Code changes: 30 minutes
  - Docstring updates: 15 minutes
  - Local testing: 30 minutes
  - Review and refinement: 15-30 minutes
- Testing: 1-2 hours
  - Unit tests: 30 minutes
  - Integration tests: 30 minutes
  - Manual verification: 30-60 minutes

**Total**: 3-5 hours

## References

- Story file: `.claude/sprint/stories/8-update-launchd-service-manager.md`
- Current implementation: `mcp_server/daemon/launchd_service.py`
- Path module: `mcp_server/daemon/paths.py`
- Bootstrap service: `mcp_server/daemon/bootstrap.py`
- Systemd comparison: `.claude/sprint/stories/9-update-systemd-service-manager.md`
- Windows comparison: `mcp_server/daemon/windows_service.py`

## Conclusion

The LaunchdServiceManager requires straightforward updates to support v2.1 frozen package architecture:

1. Replace venv-based paths with `get_install_dir()` paths
2. Use module invocation (`-m mcp_server.daemon.bootstrap`) instead of file paths
3. Add PYTHONPATH environment variable for frozen package imports
4. Update WorkingDirectory to install directory

The changes are low-risk and follow proven patterns from SystemdServiceManager and WindowsServiceManager implementations. Log paths already use the correct `get_log_dir()` function and require no changes.
