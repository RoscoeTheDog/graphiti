# Story 8: Implement TemplateResolver with Hierarchy

**Status**: completed
**Created**: 2025-12-12 00:39
**Completed**: 2025-12-12

## Description

Create TemplateResolver class that loads templates from project > global > built-in hierarchy.

## Acceptance Criteria

- [x] (P0) TemplateResolver.load() searches: `./.graphiti/templates/` -> `~/.graphiti/templates/` -> built-in
- [x] (P0) Returns template content string on success
- [x] (P1) Returns None with warning log if template not found at any level
- [x] (P1) Caches resolved templates to avoid repeated file I/O
- [x] (P2) Platform-agnostic path handling (Windows/Unix)

## Dependencies

Story 1 (completed)

## Implementation Notes

### Files Created

1. **graphiti_core/template_resolver.py** - Main TemplateResolver class
   - Implements three-tier hierarchical search:
     - Project: `./.graphiti/templates/`
     - Global: `~/.graphiti/templates/`
     - Built-in: `graphiti_core/session_tracking/prompts/`
   - Template caching with `_cache` dictionary
   - `load()` method with hierarchical search
   - `exists()` method to check template availability
   - `clear_cache()` method for cache management
   - Platform-agnostic path handling using `pathlib.Path`

2. **tests/test_template_resolver.py** - Comprehensive test suite
   - 21 tests covering all acceptance criteria
   - Tests for hierarchical search order
   - Tests for caching behavior
   - Tests for platform-agnostic paths (spaces, Windows/Unix)
   - Tests for error handling and logging
   - Integration tests with ExtractionConfig

### Files Modified

1. **graphiti_core/extraction_config.py** - Updated `resolve_prompt()` method
   - Removed stub implementation
   - Added TemplateResolver integration
   - Supports both template files (.md) and inline prompts
   - Added `project_dir` parameter for project-level templates
   - Returns empty string if template not found or disabled

### Key Design Decisions

1. **Template Detection**: Files ending in `.md` or containing path separators are treated as templates; all other strings are inline prompts
2. **Caching Strategy**: Templates cached by name after first successful load
3. **Path Handling**: Uses `pathlib.Path` for cross-platform compatibility
4. **Error Handling**: Returns None with warning log instead of raising exceptions

### Test Results

All 21 tests passed successfully:
- 5 tests for hierarchical template search
- 3 tests for caching functionality
- 2 tests for platform-agnostic path handling
- 3 tests for exists() method
- 3 tests for error handling
- 5 tests for ExtractionConfig integration

## Related Stories

- [Story 1: Create ExtractionConfig Schema](1-create-extractionconfig-schema.md) (completed)
- Story 9: Add Template Validation and Error Handling (next)
