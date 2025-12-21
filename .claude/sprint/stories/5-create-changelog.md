# Story 5: Create CHANGELOG.md

**Priority**: P2
**Estimated Tokens**: ~5K write
**Status**: pending

---

## Objective

Create a public `docs/CHANGELOG.md` documenting the architectural evolution from v1.0 to v2.0.

---

## Source Documents

1. Git history: `git log --oneline --since="2025-11-01" -- docs/ mcp_server/ graphiti_core/`
2. Internal specs in `.claude/implementation/`
3. Handoff documents in `.claude/handoff/`

---

## Target Document

`docs/CHANGELOG.md` (new file)

---

## Content Structure

```markdown
# Changelog

All notable architectural changes to Graphiti.

## [2.0.0] - 2025-12-XX

### Added
- Global session tracking with namespace tagging
- Turn-based indexing with single-pass LLM processing
- Daemon architecture for persistent background service
- Per-project configuration overrides
- ActivityVector model for intelligent summarization

### Changed
- Session scope: project-isolated → global with `project_namespace` metadata
- Indexing trigger: file watcher → turn completion detection
- LLM processing: dual-pass → single-pass with preprocessing injection

### Removed
- File watcher module (replaced by turn detection)
- Session manager time-based logic
- `session_tracking_start` / `session_tracking_stop` MCP tools

### Deprecated
- stdio transport (use HTTP daemon instead)

## [1.0.0] - 2025-11-18

### Added
- Initial session tracking implementation
- Project-scoped group_id isolation
- File watcher with JSONL parsing
- Configurable content filtering
- MCP tool integration
```

---

## Acceptance Criteria

- [ ] All major architectural changes documented
- [ ] Breaking changes clearly marked
- [ ] Deprecations noted with alternatives
- [ ] Dates accurate
- [ ] Links to relevant documentation
