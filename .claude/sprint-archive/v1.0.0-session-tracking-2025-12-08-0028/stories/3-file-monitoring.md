# Story 3: File Monitoring
**Status**: completed
**Created**: 2025-11-17 00:05
**Claimed**: 2025-11-13 11:00
**Completed**: 2025-11-13 12:30

**Depends on**: Story 1
**Description**: Implement watchdog-based automatic session detection and lifecycle management
**Acceptance Criteria**:
- [x] `watcher.py` extracted and refactored (database storage removed)
- [x] `session_manager.py` implemented with lifecycle detection
- [x] Offset tracking works correctly (incremental reading)
- [x] Session close detection works (inactivity timeout)
- [x] Configuration schema added to unified_config.py
- [x] Integration tests pass with mock JSONL files (9 tests passing)
- [x] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [x] Platform-agnostic path handling for file watching
  - [x] Type hints and comprehensive docstrings
  - [x] Error handling with logging (file I/O)
  - [x] >80% test coverage (integration tests cover all scenarios)
  - [x] Performance: Watchdog runs in background, minimal overhead

**Implementation Notes**:
- Created `watcher.py` with `SessionFileWatcher` class using watchdog library
- Implemented `SessionFileEventHandler` with callbacks for file events
- Created `session_manager.py` with `SessionManager` and `ActiveSession` dataclass
- Session manager tracks active sessions, detects inactivity, triggers callbacks
- Added `SessionTrackingConfig` to unified_config.py with all necessary settings
- Added watchdog>=6.0.0 dependency to pyproject.toml
- Updated __init__.py to export new classes
- 9 integration tests passing, covering:
  - File watcher detecting new/modified/deleted files
  - Session manager tracking sessions
  - Reading new messages incrementally
  - Inactivity detection and session close
  - Callback triggering on close
  - Context manager usage
  - Multiple concurrent sessions
- All cross-cutting requirements satisfied (platform-agnostic paths, error handling, type safety, logging)

