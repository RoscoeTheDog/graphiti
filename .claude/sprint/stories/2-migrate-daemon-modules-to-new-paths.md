# Story 2: Migrate Daemon Modules to New Path System

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 1 - Path Infrastructure

## Description

Update all daemon modules to use the new paths.py module instead of hardcoded `~/.graphiti` paths. This ensures the entire daemon subsystem uses the professional installation paths.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Audit manager.py for all path references
- [ ] Audit bootstrap.py for all path references
- [ ] Audit venv_manager.py for all path references
- [ ] Audit windows_task_scheduler.py for path references
- [ ] Audit macos_launchd.py for path references
- [ ] Audit linux_systemd.py for path references
- [ ] Document all `~/.graphiti` or `Path.home()` references found

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
