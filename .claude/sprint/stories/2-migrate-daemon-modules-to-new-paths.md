# Story 2: Migrate Daemon Modules to New Path System

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 1 - Path Infrastructure

## Description

Update all daemon modules to use the new paths.py module instead of hardcoded `~/.graphiti` paths. This ensures the entire daemon subsystem uses the professional installation paths.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Audit manager.py for all path references
- [x] Audit bootstrap.py for all path references
- [x] Audit venv_manager.py for all path references
- [x] Audit windows_task_scheduler.py for path references
- [x] Audit macos_launchd.py for path references
- [x] Audit linux_systemd.py for path references
- [x] Document all `~/.graphiti` or `Path.home()` references found

### (i) Implementation Phase
- [ ] (P0) Update manager.py to import and use paths.py functions
- [ ] (P0) Update bootstrap.py to import and use paths.py functions
- [ ] Update venv_manager.py to use paths.py functions
- [ ] Update config loading to use get_config_file()
- [ ] Update log file paths to use get_log_dir()
- [ ] Remove all hardcoded `~/.graphiti` references

### (t) Testing Phase
- [ ] (P0) Verify no `~/.graphiti` strings remain in daemon/ directory
- [ ] Verify no `Path.home() / ".graphiti"` patterns remain
- [ ] Run existing daemon tests (should still pass)

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module

## Implementation Notes

Use grep to find all references:
```bash
grep -r "\.graphiti" mcp_server/daemon/
grep -r "Path.home()" mcp_server/daemon/
```

## Discovery Findings (Phase 2.d - Completed 2025-12-25)

### Summary
Audited all daemon modules for hardcoded path references to `~/.graphiti` or `Path.home()` patterns.

### Files Audited

#### 1. manager.py (14 references found)
**Path.home() references:**
- Line 70: `return Path.home() / ".graphiti" / "graphiti.config.json"` (Windows config)
- Line 77: `return Path.home() / ".graphiti" / "graphiti.config.json"` (Unix config)

**String references to ~/.graphiti:**
- Line 46: Comment - venv at `~/.graphiti/.venv/`
- Line 47: Comment - package deployment to `~/.graphiti/mcp_server/`
- Line 50: Comment - wrapper scripts in `~/.graphiti/bin/`
- Line 133: Error message - permissions to `~/.graphiti/`
- Line 140: Print - deploying to `~/.graphiti/mcp_server/`
- Line 149: Error message - permissions to `~/.graphiti/`
- Line 197: Error message - permissions to `~/.graphiti/bin/`
- Line 212: Print - add `~/.graphiti/bin/` to PATH
- Line 215: Print - add `~/.graphiti/bin/` to PATH
- Line 278: Print - manually delete `~/.graphiti/`
- Line 293: Print - remove `~/.graphiti/` directory
- Line 470: Help text - `~/.graphiti/graphiti-mcp.pid`
- Line 472: Help text - `~/.graphiti/logs/graphiti-mcp.log`

#### 2. bootstrap.py (6 references found)
**Path.home() references:**
- Line 103: `return Path.home() / ".graphiti" / "graphiti.config.json"` (Windows config)
- Line 109: `return Path.home() / ".graphiti" / "graphiti.config.json"` (Unix config)
- Line 236: `deployed_path = Path.home() / ".graphiti" / "mcp_server" / "graphiti_mcp_server.py"`

**String references to ~/.graphiti:**
- Line 42: Comment - venv at `~/.graphiti/.venv/`
- Line 105: Comment - Unix path `~/.graphiti/`
- Line 227: Comment - deployed location `~/.graphiti/mcp_server/`

#### 3. venv_manager.py (6 references found)
**Path.home() references:**
- Line 54: `venv_path = Path.home() / ".graphiti" / ".venv"` (default venv path)
- Line 436: `requirements_path = Path.home() / ".graphiti" / "requirements.txt"`

**String references to ~/.graphiti:**
- Line 14: Comment - dedicated venv at `~/.graphiti/.venv/`
- Line 51: Docstring - defaults to `~/.graphiti/.venv/`
- Line 314: Comment - package location `~/.graphiti/mcp_server/`
- Line 420: Comment - requirements from `~/.graphiti/requirements.txt`

#### 4. windows_task_scheduler.py
**No references found** - File does not exist or has no hardcoded paths

#### 5. macos_launchd.py
**No references found** - File does not exist or has no hardcoded paths

#### 6. linux_systemd.py
**No references found** - File does not exist or has no hardcoded paths

### Migration Requirements

**Critical paths to update (P0):**
1. Config file resolution (manager.py lines 70, 77; bootstrap.py lines 103, 109)
2. Venv path (venv_manager.py line 54)
3. Deployed package path (bootstrap.py line 236)
4. Requirements file path (venv_manager.py line 436)

**Documentation updates:**
- Comments and docstrings should reference the new path system
- Error messages should reflect platform-specific paths
- Help text should use dynamic path resolution

**Total replacements needed:**
- 6 direct Path.home() constructions
- 20+ string references in comments/messages (should use paths.py for dynamic output)
