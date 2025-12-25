# Story 20: Update Configuration Documentation

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 6 - Documentation

## Description

Update CONFIGURATION.md and related documentation with new v2.1 paths, directory structure, and migration notes.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Identify all path references in CONFIGURATION.md
- [ ] Document new directory structure for each platform
- [ ] Identify config file location changes
- [ ] Review existing path documentation accuracy

### (i) Implementation Phase
- [ ] (P0) Update CONFIGURATION.md with v2.1 paths
- [ ] Add new "Directory Structure" section
- [ ] Document environment variable overrides (LOCALAPPDATA, XDG_*)
- [ ] Add migration notes for config file location changes
- [ ] Update any path examples in code blocks
- [ ] Document VERSION and INSTALL_INFO files

### (t) Testing Phase
- [ ] (P0) Verify all documented paths match actual v2.1 paths
- [ ] Verify environment variable documentation is accurate
- [ ] Cross-reference with paths.py implementation

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
