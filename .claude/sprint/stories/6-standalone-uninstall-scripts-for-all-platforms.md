---
description: Standalone uninstall scripts for all platforms
---

# Feature 6: Standalone uninstall scripts for all platforms

**Type**: Feature (Container)
**Status**: unassigned
**Parent**: None (top-level)
**Created**: 2025-12-23T15:08:46.325765

---

## Phase Status

| Phase | Story ID | Status | Artifact |
|-------|----------|--------|----------|
| Discovery | 6.d | pending | plans/6-plan.yaml |
| Implementation | 6.i | pending | Code changes |
| Testing | 6.t | pending | test-results/6-results.json |

---

## Description

Create platform-agnostic uninstall scripts deployed to `~/.graphiti/` that allow users to completely uninstall the daemon and all global resources without requiring the cloned repository. Scripts must be native to each platform (no bash on Windows).

---

## Acceptance Criteria

- [ ] (P0) Windows `uninstall.bat` script using native cmd.exe (no bash/sh dependency)
- [ ] (P0) Unix/macOS `uninstall.sh` script using bash
- [ ] (P0) Both scripts invoke deployed `manager.py` CLI for uninstall logic
- [ ] (P0) Scripts work without cloned repo present on filesystem
- [ ] (P1) Prompt user for data preservation options:
  - Keep config only (`graphiti.config.json`)
  - Keep config and logs
  - Full removal (everything in `~/.graphiti/`)
- [ ] (P1) Windows: Remove NSSM service cleanly
- [ ] (P1) Unix: Remove launchd (macOS) or systemd (Linux) service
- [ ] (P1) Scripts are deployed during installation (Story 2) alongside the package
- [ ] (P2) Graceful error handling if service doesn't exist
- [ ] (P2) Clear user feedback during uninstall process

---

## Implementation Notes

### Approach

1. Create `uninstall.bat` for Windows using native batch scripting
2. Create `uninstall.sh` for Unix/macOS using bash
3. Both scripts delegate to `python -m mcp_server.daemon.manager uninstall [options]`
4. Enhance `manager.py` uninstall command to support preservation options
5. Deploy scripts during installation phase (integrate with Story 2)

### Files to Create

- `mcp_server/daemon/scripts/uninstall.bat` (Windows native)
- `mcp_server/daemon/scripts/uninstall.sh` (Unix/macOS)

### Files to Modify

- `mcp_server/daemon/manager.py` - Add preservation options to uninstall command

### Testing Requirements

- Test uninstall on Windows without cloned repo
- Test uninstall on Unix/macOS without cloned repo
- Test each preservation option
- Test when service doesn't exist (graceful handling)

---

## 5W Completeness Check

- **Who**: End users who installed the Graphiti daemon
- **What**: Platform-native uninstall scripts that work independently of cloned repo
- **When**: When user wants to remove daemon, service, or all global resources
- **Where**: `~/.graphiti/uninstall.bat` (Windows), `~/.graphiti/uninstall.sh` (Unix)
- **Why**: Enable clean uninstall without requiring the source repository

---

## Metadata

**Workload Score**: 5.0
**Estimated Tokens**: ~2000
**Dependencies**: Story 2 (deployment), Story 4 (service configuration)
**Phase Children**: 6.d, 6.i, 6.t
