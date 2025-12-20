# Story 1: Add ProjectOverride Schema and Deep Merge Logic

**Status**: unassigned
**Created**: 2025-12-18 09:23

## Description

Add the `ProjectOverride` Pydantic model and `project_overrides` field to `GraphitiConfig`. Implement path normalization (cross-platform) and deep merge algorithm.

## Acceptance Criteria

- [ ] (P0) `ProjectOverride` model defined with overridable sections (llm, embedder, extraction, session_tracking)
- [ ] (P0) `project_overrides: Dict[str, ProjectOverride]` added to `GraphitiConfig`
- [ ] (P0) `normalize_project_path()` function handles Windows (`C:\` → `/c/`), Unix, and MSYS paths
- [ ] (P1) `deep_merge()` function correctly merges nested dicts, replaces scalars, inherits None
- [ ] (P1) Unit tests for path normalization on all platforms
- [ ] (P1) Unit tests for deep merge edge cases

## Dependencies

None

## Implementation Notes

*To be added during implementation*

## Related Stories

None
