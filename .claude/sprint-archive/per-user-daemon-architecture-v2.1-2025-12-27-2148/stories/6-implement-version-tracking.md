# Story 6: Implement Version Tracking

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 2 - Installer Overhaul

## Description

Implement VERSION and INSTALL_INFO file generation for tracking installed versions and enabling upgrade detection.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Design VERSION file format (semantic version string)
- [x] Design INSTALL_INFO JSON schema
- [x] Design upgrade detection algorithm (version comparison)
- [x] Determine how to get source version from repo

### (i) Implementation Phase
- [x] (P0) Implement `_write_version_info()` method in GraphitiInstaller
- [x] Create VERSION file with semantic version (e.g., "2.1.0")
- [x] Create INSTALL_INFO JSON with metadata (version, installed_at, source_commit, python_version, platform)
- [x] Implement `get_installed_version()` function to read VERSION
- [x] Implement `get_source_version()` function to read from repo
- [x] Implement `check_for_upgrade()` function using packaging.version

### (t) Testing Phase
- [x] (P0) Verify VERSION file is created correctly
- [x] Verify INSTALL_INFO JSON is valid and contains all fields
- [x] Test upgrade detection (installed < available)
- [x] Test no upgrade needed (installed >= available)

## Dependencies

- Story 4: Create GraphitiInstaller Class

## Implementation Notes

```json
{
  "version": "2.1.0",
  "installed_at": "2025-12-25T10:30:00Z",
  "installed_from": "C:\\Users\\Admin\\Documents\\GitHub\\graphiti",
  "source_commit": "abc123def456",
  "python_version": "3.10.18",
  "platform": "Windows-10-10.0.26100-SP0",
  "installer_version": "1.0.0"
}
```
