# Story 5: Implement Frozen Package Deployment

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 2 - Installer Overhaul

## Description

Implement the frozen package deployment system that copies `mcp_server/` and `graphiti_core/` packages to the installation `lib/` directory instead of using pip editable installs.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Analyze package copy strategy (what to include/exclude)
- [x] Document files to exclude: .pyc, __pycache__, .git, .pytest_cache
- [x] Determine how to find source packages (from repo or installed location)
- [x] Design package verification mechanism (ensure all __init__.py present)

### (i) Implementation Phase
- [x] (P0) Implement `_freeze_packages()` method in GraphitiInstaller
- [x] Copy mcp_server/ package to {INSTALL}/lib/mcp_server/
- [x] Copy graphiti_core/ package to {INSTALL}/lib/graphiti_core/
- [x] Implement exclusion filters (.pyc, __pycache__, .git, etc.)
- [x] Ensure all __init__.py files are preserved
- [x] Implement source package discovery (find repo root)

### (t) Testing Phase
- [ ] (P0) Verify frozen packages are complete (no missing files)
- [ ] Verify excluded files are not copied
- [ ] Test frozen packages are importable with PYTHONPATH set

## Dependencies

- Story 4: Create GraphitiInstaller Class

## Implementation Notes

Use shutil.copytree with ignore parameter for exclusions.
