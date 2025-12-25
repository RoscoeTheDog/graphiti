# Story 3: Path Resolution Test Suite

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 1 - Path Infrastructure

## Description

Create a comprehensive test suite for the paths.py module that validates path resolution across all supported platforms using mocking and platform simulation.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Define test scenarios for Windows edge cases (missing LOCALAPPDATA)
- [x] Define test scenarios for macOS edge cases
- [x] Define test scenarios for Linux XDG edge cases (missing XDG vars)
- [x] Identify how to mock sys.platform for cross-platform testing

**Discovery Findings**: See `.claude/sprint/stories/3-discovery-findings.md`
- 19 distinct test scenarios identified (5 Windows + 5 macOS + 6 Linux + 3 general)
- Comprehensive mocking strategy documented
- Test file structure designed (~23 tests)
- Coverage targets: >90% line coverage, >85% branch coverage

### (i) Implementation Phase
- [ ] (P0) Create tests/test_daemon_paths.py
- [ ] Implement Windows path tests with sys.platform mock
- [ ] Implement macOS path tests with sys.platform mock
- [ ] Implement Linux path tests with sys.platform mock
- [ ] Test environment variable override behavior
- [ ] Test fallback paths when env vars missing

### (t) Testing Phase
- [ ] (P0) Achieve >90% code coverage on paths.py
- [ ] All tests pass on current platform
- [ ] Verify mocked platform tests correctly simulate other OSes

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module

## Implementation Notes

Use `unittest.mock.patch` for sys.platform and os.environ mocking.
