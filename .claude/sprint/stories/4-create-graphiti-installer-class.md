# Story 4: Create GraphitiInstaller Class

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 2 - Installer Overhaul

## Description

Create the main `GraphitiInstaller` class in `mcp_server/daemon/installer.py` that orchestrates the complete installation, upgrade, and uninstall workflows.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Design installer API (install, upgrade, uninstall method signatures)
- [x] Design error handling strategy (InstallationError class)
- [x] Design progress reporting mechanism
- [x] Review existing DaemonManager for code reuse opportunities

**Discovery Output**: `.claude/sprint/discoveries/4.d-graphiti-installer-api-design.md`

### (i) Implementation Phase
- [ ] (P0) Create `mcp_server/daemon/installer.py`
- [ ] (P0) Implement `GraphitiInstaller` class with `__init__` using paths.py
- [ ] (P0) Implement `install()` method skeleton with step orchestration
- [ ] Implement `upgrade()` method skeleton
- [ ] Implement `uninstall()` method skeleton
- [ ] Implement `_validate_environment()` (Python version, disk space)
- [ ] Implement `_create_directories()` for all platform paths
- [ ] Implement `_cleanup_on_failure()` for rollback
- [ ] Add `InstallationError` exception class

### (t) Testing Phase
- [ ] (P0) Verify installer.py imports without errors
- [ ] Verify GraphitiInstaller instantiates correctly
- [ ] Test _validate_environment() catches bad Python version

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module

## Implementation Notes

Reference implementation structure in DAEMON_ARCHITECTURE_SPEC_v2.1.md section "Installer Code Structure"
