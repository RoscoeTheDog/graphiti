# .claude/ Index

**Last Updated:** 2025-11-06
**Project:** graphiti (STD)

## Overview

This directory contains agent-generated ephemeral files organized according to the EPHEMERAL-FS schema. All agent work products are categorized and tracked here.

---

## Categories

| Category | Purpose | Files | Last Modified |
|----------|---------|-------|---------------|
| implementation | Sprint tracking, checkpoints, implementation plans | 20 | 2025-11-05 |
| context | Discovery, analysis, troubleshooting docs | 8 | 2025-11-06 |
| test | Ephemeral test scripts and CI/CD validation | 3 | 2025-11-06 |
| research | Research reports (empty - STD uses graphiti memory) | 0 | - |

---

## Files by Category

### implementation/ (20 files, ~100KB)
Sprint-related implementation tracking and planning documents.

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| index.md | 2025-11-05 | 2025-11-05 | 13KB | Active sprint tracker (MCP Server Resilience) |
| checkpoints/CHECKPOINT_PHASE2.md | 2025-11-05 | 2025-11-05 | ~5KB | Phase 2 checkpoint |
| checkpoints/CHECKPOINT_PHASE3.md | 2025-11-05 | 2025-11-05 | ~5KB | Phase 3 checkpoint |
| checkpoints/CHECKPOINT_PHASE4.md | 2025-11-05 | 2025-11-05 | ~5KB | Phase 4 checkpoint |
| checkpoints/CHECKPOINT_PHASE5.md | 2025-11-05 | 2025-11-05 | ~5KB | Phase 5 checkpoint |
| checkpoints/CHECKPOINT_PHASE6.md | 2025-11-05 | 2025-11-05 | ~5KB | Phase 6 checkpoint |
| checkpoints/CHECKPOINT_PHASE6_COMPLETE.md | 2025-11-05 | 2025-11-05 | ~5KB | Phase 6 completion summary |
| checkpoints/TEST_TEMPLATES_PHASE6.md | 2025-11-05 | 2025-11-05 | ~3KB | Test templates for Phase 6 |
| plans/IMPLEMENTATION_PLAN_LLM_FILTER.md | 2025-11-05 | 2025-11-05 | ~8KB | LLM Filter implementation plan |
| plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md | 2025-11-05 | 2025-11-05 | ~8KB | Unified config implementation plan |
| guides/MIGRATION_GUIDE.md | 2025-11-05 | 2025-11-05 | ~6KB | Migration guide (user-facing) |
| guides/UNIFIED_CONFIG_SUMMARY.md | 2025-11-05 | 2025-11-05 | ~4KB | Config summary |

### context/ (7 files, ~76KB)
Discovery, analysis, and troubleshooting documentation.

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| AGENTS.md | 2025-11-05 | 2025-11-05 | 2.7KB | Agent guidelines and context |
| BRAINSTORMING_SESSION_MEMORY_FILTER.md | 2025-11-05 | 2025-11-05 | 32KB | Memory filter design brainstorming |
| BUGFIX_SUMMARY.md | 2025-11-05 | 2025-11-05 | 7.9KB | Bug fix documentation |
| MCP_DISCONNECT_ANALYSIS.md | 2025-11-05 | 2025-11-05 | 11KB | MCP connection issue analysis |
| PERFORMANCE_ANALYSIS_REPORT.md | 2025-11-05 | 2025-11-05 | 12KB | Performance analysis findings |
| SECURITY_SCAN_REPORT.md | 2025-11-05 | 2025-11-05 | 5.9KB | Security audit results |
| OTEL_TRACING.md | 2025-11-05 | 2025-11-05 | 1.2KB | OpenTelemetry tracing notes |

### test/ (3 files, ~6KB)
Ephemeral test scripts for development and CI/CD validation.

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| README.md | 2025-11-06 | 2025-11-06 | ~1KB | Test directory documentation |
| test_neo4j_community_connection.py | 2025-11-06 | 2025-11-06 | 4KB | Neo4j connection test script |
| docker-compose.test.yml | 2025-11-06 | 2025-11-06 | 1KB | CI/CD test docker-compose config |

### research/ (0 files)
Empty - STD projects use graphiti memory for research storage per EPHEMERAL-FS policy.

---

## Archives

| Archive | Date | Files | Description |
|---------|------|-------|-------------|
| implementation/archive/2025-11-05-0102 | 2025-11-05 | 9 | Pre-migration implementation files |
| context/archive/2025-11-05-migration | 2025-11-05 | 5 | Obsolete documentation archived during .claude/ migration |
| implementation/archive/2025-11-06-setup-files | 2025-11-06 | 11 | Old root-level setup files (replaced by claude-mcp-installer/ schema) |

---

## Notes

- **Migration Dates:**
  - 2025-11-05: Initial migration from scattered root/implementation files to .claude/ schema
  - 2025-11-06: Added test/ category, migrated ephemeral test scripts from root
- **Storage Policy:** STD project (no BMAD) - Research findings stored in graphiti memory, not files
- **Archives:** Preserved in category/archive/{timestamp}/ with restore commands in archive INDEX.md
- **Test Files:** Development/validation scripts in .claude/test/, permanent tests in tests/
