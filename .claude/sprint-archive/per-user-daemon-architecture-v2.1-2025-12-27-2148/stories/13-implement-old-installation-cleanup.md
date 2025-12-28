# Story 13: Implement Old Installation Cleanup

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 4 - Migration

## Description

Implement cleanup of old v2.0 installation artifacts including Task Scheduler tasks, LaunchAgents, systemd services, and optionally the ~/.graphiti/ directory.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Design cleanup workflow with user prompts
- [x] Document what can be safely removed vs preserved
- [x] Design rollback mechanism if cleanup fails
- [x] Determine interactive vs non-interactive modes

**Discovery Complete**: See `.claude/sprint/plans/13-plan.yaml` for full design

### (i) Implementation Phase
- [x] (P0) Implement `cleanup_v2_0_installation()` function
- [x] Stop running v2.0 services before cleanup
- [x] Windows: Delete GraphitiBootstrap_* Task Scheduler task
- [x] macOS: Unload and remove LaunchAgent plist
- [x] Linux: Stop and disable systemd user service
- [x] Prompt user before removing ~/.graphiti/ directory
- [x] Preserve logs if user requests

**Implementation Complete**: See `mcp_server/daemon/v2_cleanup.py` (615 lines) for full implementation

### (t) Testing Phase
- [x] (P0) Verify old Task Scheduler task is removed (Windows)
- [x] Verify ~/.graphiti/ removal is prompted (not automatic)
- [x] Verify cleanup doesn't affect v2.1 installation

## Dependencies

- Story 11: Implement v2.0 Installation Detection
- Story 12: Implement Config Migration

## Implementation Notes

```python
def cleanup_v2_0_installation(keep_logs: bool = False) -> bool:
    """
    Clean up v2.0 installation after successful migration.

    Args:
        keep_logs: If True, preserve ~/.graphiti/logs/

    Returns:
        True if cleanup successful
    """
```
