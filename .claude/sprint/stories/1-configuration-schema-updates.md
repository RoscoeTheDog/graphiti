# Story 1: Configuration Schema Updates

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Add new fields to `SessionTrackingConfig` in `mcp_server/unified_config.py` for global scope settings (`group_id`, `cross_project_search`, `trusted_namespaces`, `include_project_path`). Includes validators for new fields.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Section 3.1

## Acceptance Criteria

- [ ] (P0) `group_id: Optional[str]` field added with default None (resolves to `{hostname}__global`)
- [ ] (P0) `cross_project_search: bool` field added with default True
- [ ] (P1) `trusted_namespaces: Optional[list[str]]` field added with hex hash validation
- [ ] (P1) `include_project_path: bool` field added with default True
- [ ] (P0) All fields have proper docstrings explaining behavior
- [ ] (P1) Validator for `trusted_namespaces` rejects non-hex strings

## Dependencies

None

## Implementation Notes

Key file: `mcp_server/unified_config.py` (SessionTrackingConfig class)

New fields to add (from spec Section 3.1):
```python
group_id: Optional[str] = Field(
    default=None,
    description="Global group ID for all indexed sessions. If None, defaults to '{hostname}__global'."
)

cross_project_search: bool = Field(
    default=True,
    description="Allow searching across all project namespaces."
)

trusted_namespaces: Optional[list[str]] = Field(
    default=None,
    description="List of project namespace hashes to trust for cross-project search."
)

include_project_path: bool = Field(
    default=True,
    description="Include human-readable project path in episode metadata."
)
```

Validator for trusted_namespaces:
```python
@field_validator('trusted_namespaces')
def validate_trusted_namespaces(cls, v):
    if v is not None:
        import re
        for ns in v:
            if not re.match(r'^[a-f0-9]+$', ns.lower()):
                raise ValueError(f"Invalid namespace format: {ns}")
    return v
```

## Related Stories

None - this is the foundation story
