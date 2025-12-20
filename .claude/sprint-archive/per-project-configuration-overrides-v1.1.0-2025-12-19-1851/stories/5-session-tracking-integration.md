# Story 5: Session Tracking Integration

**Status**: unassigned
**Created**: 2025-12-18 09:23

## Description

Update session tracking to resolve and apply project-specific configuration when processing sessions.

## Acceptance Criteria

- [ ] (P0) Session tracker resolves project path from JSONL file location
- [ ] (P0) `get_effective_config(project_path)` called before processing each session
- [ ] (P0) Project-specific `session_tracking.enabled` respected (can disable per-project)
- [ ] (P1) Project-specific `extraction.preprocessing_prompt` applied
- [ ] (P1) Project-specific LLM settings used for that project's sessions
- [ ] (P2) Logging shows which project config was applied

## Dependencies

Story 2

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 2: Implement get_effective_config() Method](2-implement-get-effective-config-method.md)
