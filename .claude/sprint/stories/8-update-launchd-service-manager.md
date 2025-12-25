# Story 8: Update LaunchdServiceManager (macOS)

**Status**: in_progress
**Created**: 2025-12-25 02:02
**Phase**: 3 - Service Manager Updates

## Description

Update the LaunchdServiceManager to use the new v2.1 installation paths for macOS, including proper PYTHONPATH configuration for frozen packages.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Review current launchd plist template
- [x] Identify all path references that need updating
- [x] Document PYTHONPATH requirements for frozen lib
- [x] Review log file path conventions (~/Library/Logs/)

### (i) Implementation Phase
- [x] (P0) Update ProgramArguments to use `{INSTALL_DIR}/bin/python`
- [x] (P0) Update WorkingDirectory to `{INSTALL_DIR}`
- [x] Add EnvironmentVariables with PYTHONPATH={INSTALL_DIR}/lib
- [x] Update StandardOutPath/StandardErrorPath to new log paths (already using get_log_dir())
- [x] Import and use paths.py for path resolution
- [x] Update plist template generation

**Implementation Summary**:
- Removed VenvManager dependency (no longer needed for frozen installs)
- Updated imports to use get_install_dir() and get_log_dir() from paths.py
- Removed obsolete _get_bootstrap_path() method
- Updated __init__() to use frozen package paths
- Updated _create_plist() to use module invocation (-m mcp_server.daemon.bootstrap)
- Added PYTHONPATH environment variable pointing to {INSTALL_DIR}/lib
- Updated WorkingDirectory to use install directory
- Updated all docstrings to reflect frozen package architecture

### (t) Testing Phase
- [ ] (P0) Verify generated plist has correct paths
- [ ] Verify PYTHONPATH is set correctly in plist
- [ ] Verify log paths point to ~/Library/Logs/Graphiti/

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module
- Story 2: Migrate Daemon Modules to New Path System

## Implementation Notes

Key plist changes:
```xml
<key>ProgramArguments</key>
<array>
    <string>{INSTALL_DIR}/bin/python</string>
    <string>-m</string>
    <string>mcp_server.daemon.bootstrap</string>
</array>
<key>EnvironmentVariables</key>
<dict>
    <key>PYTHONPATH</key>
    <string>{INSTALL_DIR}/lib</string>
</dict>
```
