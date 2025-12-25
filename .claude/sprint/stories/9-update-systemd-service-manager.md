# Story 9: Update SystemdServiceManager (Linux)

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 3 - Service Manager Updates

## Description

Update the SystemdServiceManager to use the new v2.1 installation paths for Linux, including proper PYTHONPATH configuration for frozen packages.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Review current systemd unit template
- [x] Identify all path references that need updating
- [x] Document Environment variable for PYTHONPATH
- [x] Review XDG state directory for logs

### (i) Implementation Phase
- [x] (P0) Update ExecStart to use `{INSTALL_DIR}/bin/python -m mcp_server.daemon.bootstrap`
- [x] (P0) Update WorkingDirectory to `{INSTALL_DIR}`
- [x] Add Environment="PYTHONPATH={INSTALL_DIR}/lib"
- [x] Update StandardOutput/StandardError paths to XDG state dir (already using get_log_dir())
- [x] Import and use paths.py for path resolution
- [x] Update unit file template generation

### (t) Testing Phase
- [ ] (P0) Verify generated unit file has correct paths
- [ ] Verify Environment line sets PYTHONPATH correctly
- [ ] Verify log paths use XDG_STATE_HOME/graphiti/logs/

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module
- Story 2: Migrate Daemon Modules to New Path System

## Implementation Notes

### Changes Made (2025-12-25)

**File**: `mcp_server/daemon/systemd_service.py`

1. **Import Updates** (Line 17):
   - Added `get_install_dir` to imports from `paths.py`

2. **Constructor Cleanup** (Lines 26-48):
   - Removed `self.bootstrap_script = self._get_bootstrap_path()` (line 39)
   - Now relies solely on module invocation (no script path needed)

3. **Removed Method** (Lines 51-54):
   - Deleted `_get_bootstrap_path()` method entirely
   - No longer needed with module invocation

4. **Service Unit Generation** (Lines 50-75):
   - Added `install_dir = get_install_dir()` and `lib_dir = install_dir / "lib"`
   - Updated ExecStart: `{self.python_exe} -m mcp_server.daemon.bootstrap`
   - Updated WorkingDirectory: `{install_dir}` (from get_install_dir())
   - Added Environment: `PYTHONPATH={lib_dir}` for frozen packages
   - Log paths already correct (using `self.log_dir` from get_log_dir())

5. **Debug Output** (Lines 103-106):
   - Changed from "Bootstrap script" to "Install directory"
   - Shows install_dir instead of bootstrap_script path

**Key unit file changes**:
```ini
[Service]
ExecStart={INSTALL_DIR}/bin/python -m mcp_server.daemon.bootstrap
WorkingDirectory={INSTALL_DIR}
Environment="PYTHONPATH={INSTALL_DIR}/lib"
StandardOutput=append:{LOG_DIR}/bootstrap-stdout.log
StandardError=append:{LOG_DIR}/bootstrap-stderr.log
```

All changes align with v2.1 architecture and follow the pattern from WindowsServiceManager (Story 10).
