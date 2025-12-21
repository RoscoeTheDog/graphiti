# Story 1: Update ARCHITECTURE.md

**Priority**: P0 (Critical)
**Estimated Tokens**: ~15K read + ~5K write
**Status**: pending

---

## Objective

Update `docs/ARCHITECTURE.md` to reflect the current system architecture including global session tracking, turn-based indexing, and daemon architecture.

---

## Source Documents

Read these internal specs:
1. `.claude/implementation/GLOBAL_SESSION_TRACKING_SPEC_v2.0.md` - Sections 1-2 (Design Rationale, Architecture Overview)
2. `.claude/implementation/TURN_BASED_INDEXING_SPEC_v1.0.md` - Executive Summary, Architecture Summary
3. `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` - Problem Statement, Desired Architecture

---

## Target Document

`docs/ARCHITECTURE.md`

---

## Key Changes Required

### 1. System Overview Section
- **Current**: Describes "Automatic Session Detection" via file watcher
- **Update to**: Turn-based indexing triggered by role transitions (user→assistant)

### 2. Component Architecture Diagram
- **Current**: Shows Watcher → Parser → Filter → Session Manager → Indexer
- **Update to**: Turn Detector → Preprocessor → Graphiti add_episode (single-pass)

### 3. Data Flow Section
- **Current**: Describes file watcher detecting .jsonl changes
- **Update to**: Turn completion triggers indexing, no file monitoring

### 4. Session Scope Model
- **Current**: "Project-level group_id isolation"
- **Update to**: Global scope with namespace tagging (`hostname__global` group_id, `project_namespace` metadata)

### 5. Add Daemon Architecture Section
- Reference `/docs/DAEMON_ARCHITECTURE.md` for details
- Explain HTTP transport vs stdio

---

## Acceptance Criteria

- [ ] Architecture diagram reflects turn-based flow
- [ ] Global scope model documented
- [ ] File watcher references removed or marked deprecated
- [ ] Cross-references to DAEMON_ARCHITECTURE.md added
- [ ] Version updated to v2.0.0
- [ ] Last Updated date set to current date
