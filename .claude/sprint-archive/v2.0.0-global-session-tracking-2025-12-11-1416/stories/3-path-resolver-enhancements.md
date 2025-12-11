# Story 3: Path Resolver Enhancements

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Add helper methods to `ClaudePathResolver` for global group ID generation and project path reverse-lookup.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Section 6.2

## Acceptance Criteria

- [ ] (P0) `get_global_group_id(hostname: str) -> str` method returns `{hostname}__global`
- [ ] (P1) `get_project_path_from_hash(project_hash: str) -> Optional[str]` method implemented
- [ ] (P0) Methods follow existing code patterns in `path_resolver.py`
- [ ] (P1) Unit tests cover both methods

## Dependencies

None

## Implementation Notes

Key file: `graphiti_core/session_tracking/path_resolver.py`

New methods to add:
```python
def get_global_group_id(self, hostname: str) -> str:
    """Generate the global group ID for this machine.

    Args:
        hostname: Machine hostname

    Returns:
        Global group ID in format '{hostname}__global'
    """
    return f"{hostname}__global"

def get_project_path_from_hash(self, project_hash: str) -> Optional[str]:
    """Reverse-lookup project path from hash.

    Note: Claude Code stores a mapping file we can read, or we can
    scan known project directories to find matches.

    Args:
        project_hash: The hash to look up

    Returns:
        Project directory path, or None if cannot be determined
    """
    # Implementation options:
    # 1. Read Claude Code's project mapping (if available)
    # 2. Scan watch_path directories and compute hashes to match
    # 3. Return None if cannot determine (graceful degradation)
    pass
```

## Related Stories

- Story 6: Session Manager Updates (uses these methods)
