# Story 9: Add Template Validation and Error Handling

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Enhance config validation to check template existence and provide clear error messages.

## Acceptance Criteria

- [ ] (P0) Config validation warns if specified template file doesn't exist
- [ ] (P1) Validation distinguishes template files (.md) from inline prompts
- [ ] (P1) Error message includes template search paths for debugging
- [ ] (P2) Graceful degradation: missing template -> disable preprocessing with warning

## Dependencies

Story 6, Story 8

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 6: Add Extraction Config to unified_config.py](6-add-extraction-config-unified.md)
- [Story 8: Implement TemplateResolver with Hierarchy](8-implement-templateresolver.md)
