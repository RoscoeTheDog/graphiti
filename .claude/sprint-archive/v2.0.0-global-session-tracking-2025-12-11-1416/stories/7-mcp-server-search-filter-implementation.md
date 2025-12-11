# Story 7: MCP Server Search Filter Implementation

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Modify search tools in `graphiti_mcp_server.py` to support namespace filtering based on config settings.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Sections 5.1-5.4, 6.3

## Acceptance Criteria

- [ ] (P0) `search_memory_nodes` uses global group_id by default
- [ ] (P0) If `cross_project_search: false`, auto-filters to current namespace
- [ ] (P1) If `trusted_namespaces` configured, filters results to trusted only
- [ ] (P1) Post-filtering implemented until Graphiti supports native metadata filtering
- [ ] (P0) Namespace metadata visible in search results

## Dependencies

- Story 1: Configuration Schema Updates
- Story 6: Session Manager Updates

## Implementation Notes

Key file: `mcp_server/graphiti_mcp_server.py`

Changes to implement:

1. **Modify search_memory_nodes**:
```python
async def search_memory_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    project_namespaces: list[str] | None = None,  # NEW: explicit filter
) -> dict:
```

2. **Determine effective group_ids**:
```python
config = get_config()
st_config = config.session_tracking

if group_ids is None:
    hostname = socket.gethostname()
    global_group = st_config.group_id or f"{hostname}__global"
    group_ids = [global_group]
```

3. **Determine namespace filter**:
```python
effective_namespaces = project_namespaces
if effective_namespaces is None:
    if not st_config.cross_project_search:
        # Filter to current project only
        effective_namespaces = [get_current_project_namespace()]
    elif st_config.trusted_namespaces:
        # Filter to trusted namespaces
        effective_namespaces = st_config.trusted_namespaces
```

4. **Post-filter results**:
```python
def filter_by_namespace(results, namespaces):
    """Filter results to only include specified namespaces."""
    filtered = []
    for result in results:
        # Parse YAML frontmatter from content
        ns = extract_namespace_from_content(result.content)
        if ns and ns in namespaces:
            filtered.append(result)
    return filtered
```

5. **Helper function to extract namespace**:
```python
def extract_namespace_from_content(content: str) -> Optional[str]:
    """Extract project_namespace from YAML frontmatter."""
    import yaml
    if content.startswith('---'):
        try:
            end = content.index('---', 3)
            frontmatter = yaml.safe_load(content[3:end])
            return frontmatter.get('graphiti_session_metadata', {}).get('project_namespace')
        except:
            return None
    return None
```

## Related Stories

- Story 1: Configuration Schema Updates (dependency)
- Story 6: Session Manager Updates (dependency)
- Story 9: Integration Tests for Cross-Project Search (tests this)
