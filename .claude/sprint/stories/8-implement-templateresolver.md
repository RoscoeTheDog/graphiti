# Story 8: Implement TemplateResolver with Hierarchy

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Create TemplateResolver class that loads templates from project > global > built-in hierarchy.

## Acceptance Criteria

- [ ] (P0) TemplateResolver.load() searches: `./.graphiti/templates/` -> `~/.graphiti/templates/` -> built-in
- [ ] (P0) Returns template content string on success
- [ ] (P1) Returns None with warning log if template not found at any level
- [ ] (P1) Caches resolved templates to avoid repeated file I/O
- [ ] (P2) Platform-agnostic path handling (Windows/Unix)

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 1: Create ExtractionConfig Schema](1-create-extractionconfig-schema.md)
