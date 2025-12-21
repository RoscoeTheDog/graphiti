# Sprint: Documentation Architecture Sync

**Version**: 1.0.0
**Status**: ACTIVE
**Created**: 2025-12-20
**Branch**: `sprint/docs-architecture-sync`
**Base**: `dev`

---

## Objective

Synchronize public documentation (`/docs/`) with internal architectural specifications (`.claude/implementation/`) to ensure external documentation accurately reflects the current system design.

---

## Background

Multiple architectural changes have been implemented since November 2025 that are documented in internal specs but not reflected in public documentation:

1. **Global Session Tracking v2.0** - Migrated from project-scoped to global with namespace tagging
2. **Turn-Based Indexing** - Replaced file watcher + session manager with turn-pair detection
3. **Intelligent Summarization** - Replaced discrete SessionType with ActivityVector model
4. **Daemon Architecture** - Added persistent background service (partially documented)
5. **Per-Project Config Overrides** - Added project-level config customization

---

## Stories

| # | Story | Priority | Est. Tokens | Status |
|---|-------|----------|-------------|--------|
| 1 | Update ARCHITECTURE.md with global scope + turn-based indexing | P0 | ~15K | pending |
| 2 | Update SESSION_TRACKING_USER_GUIDE.md for v2.0 model | P0 | ~15K | pending |
| 3 | Update API_REFERENCE.md with current module structure | P1 | ~12K | pending |
| 4 | Verify/update MCP_TOOLS.md for current tool signatures | P1 | ~8K | pending |
| 5 | Create CHANGELOG.md summarizing architectural evolution | P2 | ~5K | pending |

---

## Source Documents (Internal Specs)

- `.claude/implementation/GLOBAL_SESSION_TRACKING_SPEC_v2.0.md` (34.6K)
- `.claude/implementation/TURN_BASED_INDEXING_SPEC_v1.0.md` (18.7K)
- `.claude/implementation/INTELLIGENT_SESSION_SUMMARIZATION_SPEC_v1.0.md` (55K)
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` (41.3K)
- `.claude/implementation/PROJECT_CONFIG_OVERRIDES_SPEC_v1.0.md` (30.6K)

---

## Target Documents (Public Docs)

- `docs/ARCHITECTURE.md` (18.8K) - Last updated 2025-11-18
- `docs/SESSION_TRACKING_USER_GUIDE.md` (18.4K) - Last updated 2025-12-14
- `docs/API_REFERENCE.md` (12K) - Last updated 2025-11-18
- `docs/MCP_TOOLS.md` (25.3K) - Last updated 2025-12-14

---

## Execution Notes

- Each story should be executed in a **fresh session** to avoid context overflow
- Stories are independent and can be parallelized
- Read source spec → Update target doc → Verify cross-references
