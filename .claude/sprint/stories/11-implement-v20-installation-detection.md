# Story 11: Implement v2.0 Installation Detection

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 4 - Migration

## Description

Implement detection of existing v2.0 installations (`~/.graphiti/`) and old Task Scheduler tasks to enable migration to v2.1.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Define v2.0 detection criteria for each platform
- [ ] Document Windows: ~/.graphiti/, GraphitiBootstrap_* task
- [ ] Document macOS: ~/.graphiti/, com.graphiti.bootstrap LaunchAgent
- [ ] Document Linux: ~/.graphiti/, graphiti-bootstrap.service

### (i) Implementation Phase
- [ ] (P0) Implement `detect_v2_0_installation()` function
- [ ] Check for ~/.graphiti/ directory existence
- [ ] Windows: Query Task Scheduler for GraphitiBootstrap_* tasks
- [ ] macOS: Check for LaunchAgent plist
- [ ] Linux: Check for systemd user service
- [ ] Return detection result with details (paths, task names)

### (t) Testing Phase
- [ ] (P0) Test detection returns True when v2.0 artifacts exist
- [ ] Test detection returns False on clean system
- [ ] Verify detection works on current platform

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module

## Implementation Notes

```python
def detect_v2_0_installation() -> dict:
    """
    Detect v2.0 installation artifacts.

    Returns:
        {
            "detected": bool,
            "home_dir": Path or None,
            "config_file": Path or None,
            "service_task": str or None
        }
    """
```
