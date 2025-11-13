# .claude/ Index

**Last Updated:** 2025-11-13
**Project:** graphiti (STD)

## Overview

This directory contains agent-generated ephemeral files organized according to the EPHEMERAL-FS schema. All agent work products are categorized and tracked here.

---

## Categories

| Category | Purpose | Files | Last Modified |
|----------|---------|-------|---------------|
| implementation | Sprint tracking, checkpoints, implementation plans | 4 | 2025-11-13 |
| context | Discovery, analysis, troubleshooting docs | 8 | 2025-11-06 |
| test | Ephemeral test scripts and CI/CD validation | 3 | 2025-11-06 |
| research | Research reports (empty - STD uses graphiti memory) | 0 | - |

---

## Files by Category

### implementation/ (4 files, ~49KB)
Sprint-related implementation tracking and planning documents.

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| index.md | 2025-11-13 | 2025-11-13 | 27KB | Active sprint tracker (Session Tracking Integration v1.0.0) - Audit remediation applied |
| CROSS_CUTTING_REQUIREMENTS.md | 2025-11-13 | 2025-11-13 | 13KB | Cross-cutting requirements for all stories (platform-agnostic paths, error handling, testing, etc.) |
| PLATFORM_AGNOSTIC_PATHS.md | 2025-11-13 | 2025-11-13 | 2.5KB | Platform-agnostic path handling guide |
| AUDIT_REPORT.md | 2025-11-13 | 2025-11-13 | 6.2KB | Sprint audit report with findings and recommendations |

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
| implementation/archive/2025-11-06-setup-files | 2025-11-06 | 11 | Old root-level setup files (replaced by claude-mcp-installer/ schema) |
| implementation/archive/2025-11-09-0122 | 2025-11-09 | 4 | Completed MCP Server Resilience sprint (checkpoints, guides, plans) |
| implementation/archive/2025-11-13-0930 | 2025-11-13 | 12 | Pre-sprint files archived before Session Tracking Integration sprint |
| context/archive/2025-11-05-migration | 2025-11-05 | 5 | Obsolete documentation archived during .claude/ migration |

---

## Notes

- **Migration Dates:**
  - 2025-11-05: Initial migration from scattered root/implementation files to .claude/ schema
  - 2025-11-06: Added test/ category, migrated ephemeral test scripts from root
  - 2025-11-09: Sprint completed (MCP Server Resilience), archived to implementation/archive/2025-11-09-0122
  - 2025-11-13: New sprint started (Session Tracking Integration v1.0.0), audit remediation applied
- **Storage Policy:** STD project (no BMAD) - Research findings stored in graphiti memory, not files
- **Archives:** Preserved in category/archive/{timestamp}/ with restore commands in archive INDEX.md
- **Test Files:** Development/validation scripts in .claude/test/, permanent tests in tests/
- **Current Sprint:** Session Tracking Integration v1.0.0 (active on branch sprint/v1.0.0/session-tracking-integration)
  - 4 stories completed (1-4), 4 stories remaining (5-8)
  - Audit completed 2025-11-13, remediation applied (7 issues resolved, 1 new story created)
