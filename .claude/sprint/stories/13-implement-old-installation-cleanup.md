# Story 13: Implement Old Installation Cleanup

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 4 - Migration

## Description

Implement cleanup of old v2.0 installation artifacts including Task Scheduler tasks, LaunchAgents, systemd services, and optionally the ~/.graphiti/ directory.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Design cleanup workflow with user prompts
- [ ] Document what can be safely removed vs preserved
- [ ] Design rollback mechanism if cleanup fails
- [ ] Determine interactive vs non-interactive modes

### (i) Implementation Phase
- [ ] (P0) Implement `cleanup_v2_0_installation()` function
- [ ] Stop running v2.0 services before cleanup
- [ ] Windows: Delete GraphitiBootstrap_* Task Scheduler task
- [ ] macOS: Unload and remove LaunchAgent plist
- [ ] Linux: Stop and disable systemd user service
- [ ] Prompt user before removing ~/.graphiti/ directory
- [ ] Preserve logs if user requests

### (t) Testing Phase
- [ ] (P0) Verify old Task Scheduler task is removed (Windows)
- [ ] Verify ~/.graphiti/ removal is prompted (not automatic)
- [ ] Verify cleanup doesn't affect v2.1 installation

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
