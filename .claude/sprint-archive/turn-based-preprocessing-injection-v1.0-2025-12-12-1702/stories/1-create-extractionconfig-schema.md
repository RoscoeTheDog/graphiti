# Story 1: Create ExtractionConfig Schema

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Create new ExtractionConfig Pydantic model with `preprocessing_prompt` (bool|str) and `preprocessing_mode` (prepend|append) fields following FilterConfig patterns.

## Acceptance Criteria

- [ ] (P0) ExtractionConfig class exists in `graphiti_core/extraction_config.py`
- [ ] (P0) `preprocessing_prompt` field supports None, False, "template.md", and inline strings
- [ ] (P1) `is_enabled()` method returns correct boolean based on field value
- [ ] (P1) `resolve_prompt()` method stub exists (template resolution deferred to ST-8)
- [ ] (P2) Type hints and docstrings follow codebase conventions

## Dependencies

None

## Implementation Notes

*To be added during implementation*

## Related Stories

None
