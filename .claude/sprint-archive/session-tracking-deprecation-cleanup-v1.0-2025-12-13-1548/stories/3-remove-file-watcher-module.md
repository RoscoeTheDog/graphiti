# Story 3: Remove File Watcher Module

**Status**: unassigned
**Created**: 2025-12-12 17:46

## Description

Remove or deprecate `watcher.py` which implements file system watching for session files. This module is superseded by turn-based processing where each conversation turn is indexed immediately rather than watching for file changes over time.

## Acceptance Criteria

- [ ] (P0) Remove `watcher.py` from `graphiti_core/session_tracking/`
- [ ] (P0) Remove watcher imports from `__init__.py`
- [ ] (P1) Remove watcher initialization from `graphiti_mcp_server.py`
- [ ] (P1) Update any tests referencing the watcher

## Dependencies

Story 2

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Remove Deprecated Config Parameters
- Story 2: Remove Session Manager Time-Based Logic
