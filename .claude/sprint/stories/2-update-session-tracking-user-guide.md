# Story 2: Update SESSION_TRACKING_USER_GUIDE.md

**Priority**: P0 (Critical)
**Estimated Tokens**: ~15K read + ~5K write
**Status**: pending

---

## Objective

Update `docs/SESSION_TRACKING_USER_GUIDE.md` to reflect the v2.0 global session tracking model and turn-based indexing.

---

## Source Documents

Read these internal specs:
1. `.claude/implementation/GLOBAL_SESSION_TRACKING_SPEC_v2.0.md` - Sections 4-5 (Episode Metadata, Search Behavior)
2. `.claude/implementation/TURN_BASED_INDEXING_SPEC_v1.0.md` - Sections on turn detection and filtering

---

## Target Document

`docs/SESSION_TRACKING_USER_GUIDE.md`

---

## Key Changes Required

### 1. Overview Section
- **Current**: "Monitors your Claude Code conversation files"
- **Update to**: "Indexes conversation turns as they complete"

### 2. Architecture Flow Diagram
- **Current**: File watcher → Parser → Filter → Graphiti
- **Update to**: Turn complete → Preprocess → Graphiti add_episode (single LLM pass)

### 3. What Gets Captured
- **Current**: Implies file-based capture
- **Update to**: Turn-pair capture (user message + assistant response)

### 4. Cross-Project Knowledge
- **Add new section**: Explain global scope benefits
- Document `project_namespace` metadata
- Explain `trusted_namespaces` filtering option

### 5. Cost Section
- **Current**: "$0.17 per session with smart filtering"
- **Verify**: Still accurate with turn-based model

### 6. CLI Commands
- Verify all CLI commands still valid
- Update any deprecated commands

---

## Acceptance Criteria

- [ ] Turn-based model explained clearly
- [ ] Global scope benefits documented
- [ ] File watcher language removed
- [ ] Diagram updated to show turn flow
- [ ] CLI commands verified current
- [ ] Last Updated date set to current date
