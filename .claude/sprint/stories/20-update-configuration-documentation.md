# Story 20: Update Configuration Documentation

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 6 - Documentation

## Description

Update CONFIGURATION.md and related documentation with new v2.1 paths, directory structure, and migration notes.

## Acceptance Criteria

### (d) Discovery Phase ✅ COMPLETE
- [x] (P0) Identify all path references in CONFIGURATION.md
- [x] Document new directory structure for each platform
- [x] Identify config file location changes
- [x] Review existing path documentation accuracy

### (i) Implementation Phase ✅ COMPLETE
- [x] (P0) Update CONFIGURATION.md with v2.1 paths
- [x] Add new "Directory Structure" section
- [x] Document environment variable overrides (LOCALAPPDATA, XDG_*)
- [x] Add migration notes for config file location changes
- [x] Update any path examples in code blocks
- [x] Document VERSION and INSTALL_INFO files

**Artifact**: `CONFIGURATION.md` updated with v2.1 architecture paths

### (t) Testing Phase ✅ COMPLETE
- [x] (P0) Verify all documented paths match actual v2.1 paths
- [x] Verify environment variable documentation is accurate
- [x] Cross-reference with paths.py implementation

**Artifact**: Path documentation verified against `graphiti_mcp_installer/daemon/paths.py`

### (t2) Final Documentation Sweep ✅ COMPLETE (Session s040)
- [x] Replaced all `~/.graphiti/` references with platform-specific paths
- [x] Updated template resolution hierarchy for all platforms
- [x] Updated config file location references
- [x] Updated validator command examples with platform-specific paths

**Artifact**: All v2.0 path references removed from `CONFIGURATION.md` (except migration note)

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module
- Story 19: Update Installation Guide

## Implementation Notes

Path comparison table to add:
| Component | v2.0 Location | v2.1 Location |
|-----------|---------------|---------------|
| Python venv | ~/.graphiti/.venv/ | %LOCALAPPDATA%\Programs\Graphiti\bin\ |
| Config | ~/.graphiti/graphiti.config.json | %LOCALAPPDATA%\Graphiti\config\graphiti.config.json |
| Logs | ~/.graphiti/logs/ | %LOCALAPPDATA%\Graphiti\logs\ |
