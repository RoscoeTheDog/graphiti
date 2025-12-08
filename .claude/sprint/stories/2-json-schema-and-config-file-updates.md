# Story 2: JSON Schema and Config File Updates

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Update `graphiti.config.schema.json` with new session_tracking fields and update `graphiti.config.json` with example values.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Section 3.2

## Acceptance Criteria

- [ ] (P0) JSON schema updated with all new session_tracking fields
- [ ] (P0) Field descriptions match Pydantic model docstrings
- [ ] (P1) Example config file shows sensible defaults
- [ ] (P1) Schema validates correctly against updated config

## Dependencies

Story 1 (Configuration Schema Updates)

## Implementation Notes

Files to update:
- `graphiti.config.schema.json`
- `graphiti.config.json`

New schema properties for session_tracking:
```json
{
  "group_id": {
    "type": ["string", "null"],
    "default": null,
    "description": "Global group ID for all indexed sessions. If null, defaults to '{hostname}__global'."
  },
  "cross_project_search": {
    "type": "boolean",
    "default": true,
    "description": "Allow searching across all project namespaces."
  },
  "trusted_namespaces": {
    "type": ["array", "null"],
    "items": { "type": "string", "pattern": "^[a-f0-9]+$" },
    "default": null,
    "description": "List of project namespace hashes to trust for cross-project search."
  },
  "include_project_path": {
    "type": "boolean",
    "default": true,
    "description": "Include human-readable project path in episode metadata."
  }
}
```

## Related Stories

- Story 1: Configuration Schema Updates (dependency)
