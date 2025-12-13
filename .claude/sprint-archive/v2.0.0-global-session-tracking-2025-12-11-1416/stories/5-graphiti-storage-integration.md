# Story 5: Graphiti Storage Integration

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Modify `store_session()` in `graphiti_storage.py` to embed namespace metadata in episode content and use global group_id.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Section 6.4

## Acceptance Criteria

- [ ] (P0) `store_session()` accepts new parameters: `project_namespace`, `project_path`, `hostname`, `include_project_path`
- [ ] (P0) Metadata header prepended to episode body
- [ ] (P0) `source_description` prefixed with `[{namespace[:8]}]`
- [ ] (P1) Episodes stored with global `group_id` (not project-specific)
- [ ] (P1) Backward compatibility: function works if new params not provided

## Dependencies

- Story 4: Episode Metadata Builder

## Implementation Notes

Key file: `graphiti_core/session_tracking/graphiti_storage.py`

Update `store_session()` signature:
```python
async def store_session(
    self,
    summary: SessionSummary,
    group_id: str,
    project_namespace: str,  # NEW
    project_path: Optional[str] = None,  # NEW
    hostname: Optional[str] = None,  # NEW
    include_project_path: bool = True,  # NEW
    previous_session_uuid: str | None = None,
    handoff_file_path: Path | None = None,
) -> str:
```

Changes to implement:
1. Import `build_episode_metadata_header` from metadata module
2. Build metadata header with provided parameters
3. Prepend header to episode body: `episode_body = metadata_header + summary.to_markdown()`
4. Update source_description format: `f"[{project_namespace[:8]}] Session with {summary.message_count} messages..."`
5. Ensure group_id parameter is used (will be global group_id)

Backward compatibility:
- If `project_namespace` not provided, omit metadata header (legacy behavior)
- Log warning if new params missing

## Related Stories

- Story 4: Episode Metadata Builder (dependency)
- Story 6: Session Manager Updates (calls this function)
