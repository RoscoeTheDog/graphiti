# Story 19: Update Installation Guide

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 6 - Documentation

## Description

Update the installation documentation with v2.1 instructions, including new paths, migration guide, and platform-specific setup.

## Acceptance Criteria

### (d) Discovery Phase ✅ COMPLETE
- [x] (P0) Audit existing docs for v2.0 path references
- [x] Identify all installation-related documentation files
- [x] Document new installation flow for each platform
- [x] Outline migration guide structure

### (i) Implementation Phase ✅ COMPLETE
- [x] (P0) Update main installation guide with v2.1 paths
- [x] Write migration section for v2.0 users
- [x] Document platform-specific installation steps
- [x] Add troubleshooting section for common issues
- [x] Update CLI command documentation
- [x] Add examples for install, upgrade, uninstall commands

**Artifact**: `claude-mcp-installer/instance/CLAUDE_INSTALL.md`, `tests/daemon/README_E2E.md`

### (t) Testing Phase ✅ COMPLETE
- [x] (P0) Verify documented paths match actual installation
- [x] Verify migration steps are accurate
- [x] Test following the guide on a fresh system

**Artifact**: Documentation verified against v2.1 architecture paths

## Dependencies

- Story 14: Windows Fresh Install Test
- Story 15: macOS Fresh Install Test
- Story 16: Linux Fresh Install Test

## Implementation Notes

Files to update:
- README.md (quick start section)
- claude-mcp-installer/instance/CLAUDE_INSTALL.md
- docs/ (if applicable)

New sections needed:
- v2.1 Directory Structure
- Migration from v2.0
- Platform-Specific Notes
