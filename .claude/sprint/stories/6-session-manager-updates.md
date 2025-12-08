# Story 6: Session Manager Updates

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Update `session_manager.py` to extract project info and pass to storage with global group_id.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Section 6.1

## Acceptance Criteria

- [ ] (P0) Session manager extracts `project_namespace` from session path
- [ ] (P0) Session manager extracts `project_path` (if config allows)
- [ ] (P0) Passes namespace metadata to `store_session()`
- [ ] (P0) Uses global group_id from config (not project-specific)
- [ ] (P1) Logs namespace information at DEBUG level

## Dependencies

- Story 3: Path Resolver Enhancements
- Story 5: Graphiti Storage Integration

## Implementation Notes

Key file: `graphiti_core/session_tracking/session_manager.py`

Changes to implement:

1. **Extract project info from session path**:
```python
# Get project hash (namespace) from session file path
project_namespace = self.path_resolver.resolve_project_from_session_file(session_path)

# Get human-readable project path (if configured)
project_path = None
if config.include_project_path:
    project_path = self.path_resolver.get_project_path_from_hash(project_namespace)
```

2. **Compute global group_id**:
```python
import socket
hostname = socket.gethostname()

# Use configured group_id or default to global
if config.group_id:
    group_id = config.group_id
else:
    group_id = self.path_resolver.get_global_group_id(hostname)
```

3. **Pass to storage**:
```python
await self.storage.store_session(
    summary=summary,
    group_id=group_id,  # Now global
    project_namespace=project_namespace,
    project_path=project_path,
    hostname=hostname,
    include_project_path=config.include_project_path,
    ...
)
```

4. **Logging**:
```python
logger.debug(f"Indexing session from namespace {project_namespace[:8]} to group {group_id}")
```

## Related Stories

- Story 3: Path Resolver Enhancements (dependency)
- Story 5: Graphiti Storage Integration (dependency)
- Story 7: MCP Server Search Filter Implementation (related)
