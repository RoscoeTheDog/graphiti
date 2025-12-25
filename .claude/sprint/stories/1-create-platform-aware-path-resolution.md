# Story 1: Create Platform-Aware Path Resolution Module

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 1 - Path Infrastructure

## Description

Create the core `mcp_server/daemon/paths.py` module that provides platform-aware path resolution for all Graphiti installation directories. This is the foundation for the v2.1 professional installation architecture.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Analyze Windows LOCALAPPDATA conventions (Programs vs direct)
- [ ] Analyze macOS Library directory conventions (Application Support, Preferences, Logs)
- [ ] Analyze Linux XDG Base Directory specification (XDG_DATA_HOME, XDG_CONFIG_HOME, XDG_STATE_HOME)
- [ ] Document environment variable fallbacks for each platform

### (i) Implementation Phase
- [ ] (P0) Create `mcp_server/daemon/paths.py` module
- [ ] (P0) Implement `GraphitiPaths` NamedTuple with install_dir, config_dir, state_dir, config_file
- [ ] (P0) Implement `get_paths()` function with platform detection (sys.platform)
- [ ] Implement convenience functions: get_install_dir(), get_config_dir(), get_config_file(), get_log_dir(), get_data_dir()
- [ ] Handle environment variable overrides (LOCALAPPDATA, XDG_* variables)
- [ ] Add type hints and docstrings

### (t) Testing Phase
- [ ] (P0) Verify paths.py imports without errors
- [ ] Test get_paths() returns valid GraphitiPaths on current platform
- [ ] Verify all path functions return Path objects (not strings)

## Dependencies

None

## Implementation Notes

Reference implementation in DAEMON_ARCHITECTURE_SPEC_v2.1.md section "Path Resolution"

## Technical Details

**Windows paths**:
- Install: `%LOCALAPPDATA%\Programs\Graphiti\`
- Config: `%LOCALAPPDATA%\Graphiti\config\`
- State: `%LOCALAPPDATA%\Graphiti\`

**macOS paths**:
- Install: `~/Library/Application Support/Graphiti/`
- Config: `~/Library/Preferences/Graphiti/`
- State: `~/Library/Logs/Graphiti/`

**Linux paths (XDG)**:
- Install: `~/.local/share/graphiti/`
- Config: `~/.config/graphiti/`
- State: `~/.local/state/graphiti/`
