# Story 4: Episode Metadata Builder

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Create `build_episode_metadata_header()` function that generates YAML frontmatter with namespace metadata for episode content.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Sections 4.1, 4.2, 6.2

## Acceptance Criteria

- [ ] (P0) Function generates valid YAML frontmatter with version "2.0"
- [ ] (P0) Includes required fields: `project_namespace`, `hostname`, `indexed_at`, `session_file`, `message_count`, `duration_minutes`
- [ ] (P1) `project_path` included only when `include_project_path=True`
- [ ] (P0) Output parseable as YAML with standard library
- [ ] (P1) Unit tests verify header format and field presence

## Dependencies

None

## Implementation Notes

New file: `graphiti_core/session_tracking/metadata.py` (or add to existing module)

Function signature:
```python
def build_episode_metadata_header(
    project_namespace: str,
    project_path: Optional[str],
    hostname: str,
    session_file: str,
    message_count: int,
    duration_minutes: int,
    include_project_path: bool = True
) -> str:
    """Build YAML frontmatter header for episode content.

    Returns:
        YAML frontmatter string to prepend to episode body
    """
```

Expected output format:
```markdown
---
graphiti_session_metadata:
  version: "2.0"
  project_namespace: "a1b2c3d4e5f6g7h8"
  project_path: "/home/user/my-awesome-project"
  hostname: "DESKTOP-ABC123"
  indexed_at: "2025-12-08T15:30:00Z"
  session_file: "session-abc123.jsonl"
  message_count: 47
  duration_minutes: 23
---

```

Notes:
- Use `yaml.dump()` with `default_flow_style=False` for human-readable output
- Remove None values before serializing
- ISO8601 format for `indexed_at` with UTC timezone

## Related Stories

- Story 5: Graphiti Storage Integration (uses this function)
