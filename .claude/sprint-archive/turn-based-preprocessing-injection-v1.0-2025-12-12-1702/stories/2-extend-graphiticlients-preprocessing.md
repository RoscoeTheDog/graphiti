# Story 2: Extend GraphitiClients with Preprocessing Fields

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Add `preprocessing_prompt: str | None` and `preprocessing_mode: str` fields to GraphitiClients dataclass and wire through Graphiti.__init__.

## Acceptance Criteria

- [ ] (P0) GraphitiClients has `preprocessing_prompt` field (default: None)
- [ ] (P0) GraphitiClients has `preprocessing_mode` field (default: "prepend")
- [ ] (P0) Graphiti.__init__ accepts and passes preprocessing params to GraphitiClients
- [ ] (P1) Existing Graphiti instantiation patterns continue to work (backward compatible)

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 1: Create ExtractionConfig Schema](1-create-extractionconfig-schema.md)
