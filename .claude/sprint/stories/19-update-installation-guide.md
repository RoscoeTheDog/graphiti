# Story 19: Update Installation Guide

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 6 - Documentation

## Description

Update the installation documentation with v2.1 instructions, including new paths, migration guide, and platform-specific setup.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Audit existing docs for v2.0 path references
- [ ] Identify all installation-related documentation files
- [ ] Document new installation flow for each platform
- [ ] Outline migration guide structure

### (i) Implementation Phase
- [ ] (P0) Update main installation guide with v2.1 paths
- [ ] Write migration section for v2.0 users
- [ ] Document platform-specific installation steps
- [ ] Add troubleshooting section for common issues
- [ ] Update CLI command documentation
- [ ] Add examples for install, upgrade, uninstall commands

### (t) Testing Phase
- [ ] (P0) Verify documented paths match actual installation
- [ ] Verify migration steps are accurate
- [ ] Test following the guide on a fresh system

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
