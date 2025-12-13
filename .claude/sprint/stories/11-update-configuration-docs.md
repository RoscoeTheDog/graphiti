# Story 11: Update CONFIGURATION.md with Extraction Section

**Status**: unassigned
**Created**: 2025-12-12 00:39

## Description

Document extraction config section with examples for default, disabled, custom template, and inline prompt configurations.

## Acceptance Criteria

- [x] (P0) CONFIGURATION.md has new "Extraction Configuration" section
- [x] (P0) Documents preprocessing_prompt value patterns (null, template, inline)
- [x] (P1) Documents preprocessing_mode options with recommendations
- [x] (P1) Includes 4 configuration examples (default, disabled, custom, inline)
- [x] (P2) Documents template hierarchy and custom template creation

## Dependencies

Story 6

## Implementation Notes

Added comprehensive "Extraction Configuration" section to CONFIGURATION.md (line 303-486):
- Documented preprocessing_prompt modes: disabled (false/null), template ("*.md"), inline (string)
- Documented preprocessing_mode: "prepend" (default) and "append" options
- Included 4 configuration examples covering all use cases:
  1. Disabled (default behavior)
  2. Template-based with built-in template (default-session-turn.md)
  3. Template-based with custom template (session-turn-extraction.md)
  4. Inline prompt with append mode
- Documented template hierarchy: project → global → built-in
- Provided instructions for creating custom templates (project-level and global)
- Added use cases section with examples for session-aware, domain-specific, and inline extraction
- Documented environment variable overrides
- Added implementation notes on caching, error handling, and performance
- Updated table of contents with new section reference
- Updated version to 3.2 and last updated date to 2025-12-12

## Related Stories

- [Story 6: Add Extraction Config to unified_config.py](6-add-extraction-config-unified.md)
