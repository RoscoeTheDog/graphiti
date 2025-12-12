# Story 3: Activity Detection from Messages

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Implement ActivityDetector that analyzes session messages to detect activity vector from user intent keywords, error patterns, and file patterns. This provides the signal sources for computing the activity vector without requiring tool classification.

## Acceptance Criteria

- [ ] (P0) `ActivityDetector` class with `detect(messages) -> ActivityVector` method
- [ ] (P0) User intent keyword detection (implement, fix, debug, configure, explore, etc.)
- [ ] (P0) Error pattern detection (error, exception, traceback, failed)
- [ ] (P1) File pattern detection (config files, test files, documentation)
- [ ] (P1) Integration tests with sample session messages

## Dependencies

- Story 2: Activity Vector Model

## Implementation Notes

**File to create**: `graphiti_core/session_tracking/activity_detector.py`

**Signal sources**:
1. **User intent keywords**: Match keywords in user messages to activity dimensions
   - building: implement, add, create, build, new feature, develop
   - fixing: fix, bug, error, broken, not working, debug, resolve
   - configuring: config, setup, install, environment, settings, .env
   - exploring: how does, what is, find, search, understand, explain
   - etc.

2. **Error patterns**: Count error indicators to boost "fixing" dimension
   - error, exception, failed, traceback, crash

3. **File patterns**: Detect file types to boost relevant dimensions
   - Config: .env, config., .json, .yaml, .toml, package.json
   - Testing: test_, _test., .spec., conftest.py
   - Docs: README, CHANGELOG, .md, docs/

**Signal contribution caps**:
- Keywords: max 0.5 per dimension
- Error patterns: +0.3 to fixing if count > 3
- File patterns: +0.25 per dimension if count > 2

## Related Stories

- Story 2: Activity Vector Model (dependency)
- Story 11: Summarizer Integration (uses this)
