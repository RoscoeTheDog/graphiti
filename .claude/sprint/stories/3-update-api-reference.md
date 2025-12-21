# Story 3: Update API_REFERENCE.md

**Priority**: P1
**Estimated Tokens**: ~12K read + ~4K write
**Status**: pending

---

## Objective

Update `docs/API_REFERENCE.md` to reflect the current module structure, removing deprecated components and adding new ones.

---

## Source Documents

1. Inspect actual code structure in `mcp_server/` and `graphiti_core/`
2. `.claude/implementation/TURN_BASED_INDEXING_SPEC_v1.0.md` - Implementation Requirements section

---

## Target Document

`docs/API_REFERENCE.md`

---

## Key Changes Required

### 1. Verify Module Structure
Current docs reference:
- `graphiti_core.session_tracking.parser`
- `graphiti_core.session_tracking.filter`
- `graphiti_core.session_tracking.indexer`
- `graphiti_core.session_tracking.session_manager`
- `graphiti_core.session_tracking.watcher`

**Action**: Verify these still exist and document any new modules

### 2. Remove/Deprecate File Watcher
- If `watcher.py` removed, remove from docs
- If deprecated, mark as deprecated

### 3. Add Turn-Based Components
Document any new modules:
- Turn detector
- Preprocessing prompt builder
- Custom prompt injection

### 4. Update Type Definitions
Verify these types still accurate:
- `SessionMessage`
- `ConversationContext`
- `SessionMetadata`
- `FilterConfig`
- `ContentMode`

### 5. MCP Tools API Section
- Verify tool signatures match implementation
- Add any new tools
- Remove any deprecated tools

---

## Acceptance Criteria

- [x] All documented modules verified to exist
- [x] Deprecated modules marked or removed (no watcher.py found, not referenced)
- [x] New modules documented (ActivityDetector, ToolClassifier, BashAnalyzer, UnifiedClassifier, ExtractionConfig)
- [x] Type definitions match implementation (kept existing types, added ExtractionPriority)
- [x] Example code tested/verified (syntax verified)
- [x] Last Updated date set to current date (2025-12-20)
