# Story 6: Add Extraction Config to unified_config.py

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Integrate ExtractionConfig into GraphitiConfig schema with proper defaults and JSON serialization.

## Acceptance Criteria

- [ ] (P0) GraphitiConfig has `extraction: ExtractionConfig` field
- [ ] (P0) Default ExtractionConfig uses "default-session-turn.md" template
- [ ] (P1) Config validates preprocessing_prompt values correctly
- [ ] (P1) JSON config example in graphiti.config.json schema works

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 1: Create ExtractionConfig Schema](1-create-extractionconfig-schema.md)
