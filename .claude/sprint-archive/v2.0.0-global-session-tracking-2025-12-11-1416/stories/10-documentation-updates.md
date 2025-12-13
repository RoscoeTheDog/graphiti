# Story 10: Documentation Updates

**Status**: unassigned
**Created**: 2025-12-08 00:32

## Description

Update user-facing documentation to reflect v2.0 global scope changes.

Reference: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md Sections 7, 8, Appendix A

## Acceptance Criteria

- [ ] (P0) `CONFIGURATION.md` updated with new session_tracking fields
- [ ] (P1) `docs/SESSION_TRACKING_USER_GUIDE.md` updated with global scope explanation
- [ ] (P1) Migration notes for test users documented
- [ ] (P1) Security considerations documented (path exposure, cross-project info)
- [ ] (P2) Example configs showing common use cases

## Dependencies

- Stories 1-7 (documents implemented features)

## Implementation Notes

Files to update:
- `CONFIGURATION.md` - Add new session_tracking fields to reference
- `docs/SESSION_TRACKING_USER_GUIDE.md` - Explain global scope behavior
- `docs/SESSION_TRACKING_MIGRATION.md` - Migration notes for test users

### CONFIGURATION.md Updates

Add to session_tracking section:
```markdown
### Global Scope Settings (v2.0)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `group_id` | string\|null | null | Global group ID. If null, defaults to `{hostname}__global` |
| `cross_project_search` | bool | true | Search across all project namespaces |
| `trusted_namespaces` | string[]\|null | null | Restrict search to specific project hashes |
| `include_project_path` | bool | true | Include paths in episode metadata |
```

### USER_GUIDE.md Updates

Add section explaining:
- Global knowledge graph concept
- How namespace metadata works
- How agents interpret provenance
- When to use `cross_project_search: false`
- When to use `trusted_namespaces`

### MIGRATION.md Updates

Add section for v1.0 -> v2.0 migration:
- Explain data in old group_ids won't be searched by default
- Options: keep old data, re-index, or manual migration
- Note that v1.0 was never publicly released

### Security Documentation

Add to appropriate doc:
- `include_project_path: false` to hide paths
- `cross_project_search: false` for sensitive projects
- `trusted_namespaces` to exclude known-bad projects
- Multi-user environment considerations

## Related Stories

- All implementation stories (1-7): Documents their features
- Story 8-9: Tests validate documentation accuracy
