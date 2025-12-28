# Story 11: Implement v2.0 Installation Detection

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 4 - Migration

## Description

Implement detection of existing v2.0 installations (`~/.graphiti/`) and old Task Scheduler tasks to enable migration to v2.1.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Define v2.0 detection criteria for each platform
- [x] Document Windows: ~/.graphiti/, GraphitiBootstrap_* task
- [x] Document macOS: ~/.graphiti/, com.graphiti.bootstrap LaunchAgent
- [x] Document Linux: ~/.graphiti/, graphiti-bootstrap.service

### (i) Implementation Phase
- [x] (P0) Implement `detect_v2_0_installation()` function
- [x] Check for ~/.graphiti/ directory existence
- [x] Windows: Query Task Scheduler for GraphitiBootstrap_* tasks
- [x] macOS: Check for LaunchAgent plist
- [x] Linux: Check for systemd user service
- [x] Return detection result with details (paths, task names)

**Implementation Complete**: See `mcp_server/daemon/v2_detection.py` (430 lines) for full implementation

### (t) Testing Phase
- [x] (P0) Test detection returns True when v2.0 artifacts exist
- [x] Test detection returns False on clean system
- [x] Verify detection works on current platform

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
