---
description: Make sync_history MCP tool read-only (dry_run enforced)
---

# Story R3: Make sync_history MCP tool read-only (dry_run enforced)

**Type**: Remediation
**Status**: in_progress
**Parent**: None (top-level)
**Created**: 2025-12-05T16:31:07.180118
**Issue Type**: Security/Safety Enhancement

---

## Remediation Purpose

This remediation story addresses a security/safety concern with the `session_tracking_sync_history` MCP tool.

**Issue Category**: Security - Accidental Expensive Operations
**Detected By**: Sprint Review / Architecture Audit
**Affects Stories**: Story 13 (Manual Sync Command)

---

## Issue Description

The `session_tracking_sync_history` MCP tool currently exposes a `dry_run` parameter that allows AI assistants (Claude) to set `dry_run=False` and perform actual session indexing operations. This poses risks:

1. **Cost Risk**: Accidental bulk indexing can be expensive ($0.17/session)
2. **Data Risk**: Unintended modifications to the knowledge graph
3. **Control Risk**: Users lose explicit control over sync operations

**Current Behavior**:
- MCP tool: `session_tracking_sync_history(project, days, max_sessions, dry_run=True)`
- AI clients can override `dry_run=False` to perform actual sync
- CLI already has proper safeguards (`--confirm` for `--days 0`)

**Desired Behavior**:
- MCP tool: Always read-only (preview mode only)
- Actual sync operations require explicit CLI invocation
- Clear separation of concerns between AI-assisted preview and user-controlled execution

---

## Remediation Steps

1. [x] **Discovery**: Analyze current implementation (R3.d)
   - Identified MCP tool at `mcp_server/graphiti_mcp_server.py:2259-2300`
   - Backend function at `mcp_server/manual_sync.py:29-204`
   - CLI at `mcp_server/session_tracking_cli.py:211-303`

2. [ ] **Implementation**: Modify MCP tool (R3.i)
   - Remove `dry_run` parameter from MCP tool signature
   - Always pass `dry_run=True` to backend function
   - Update docstring to document read-only behavior
   - Keep backend function unchanged (CLI still uses it)

3. [ ] **Testing**: Verify changes (R3.t)
   - Test MCP tool only returns preview data
   - Test CLI still supports actual sync with `--no-dry-run`
   - Update any tests that expect `dry_run=False` via MCP

---

## Acceptance Criteria

- [x] MCP tool signature no longer exposes `dry_run` parameter
- [x] MCP tool always operates in dry_run mode (preview only)
- [x] MCP tool docstring clearly states read-only behavior
- [x] CLI retains full capability (`--no-dry-run` works)
- [x] Tests updated to reflect new behavior
- [x] Documentation updated (MCP_TOOLS.md, USER_GUIDE)

---

## Implementation Notes

### Root Cause

The original design gave MCP clients (AI assistants) full control over sync operations for convenience. However, this bypasses user consent for potentially expensive operations.

### Fix Strategy

**Minimal Change Approach**:
1. Modify only the MCP tool wrapper in `graphiti_mcp_server.py`
2. Remove `dry_run` from tool signature
3. Hardcode `dry_run=True` in the call to backend
4. Backend function unchanged (CLI compatibility)

**Files to Modify**:
- `mcp_server/graphiti_mcp_server.py` (MCP tool)
- `tests/mcp/test_session_tracking_tools.py` (test updates)
- `docs/MCP_TOOLS.md` (documentation)
- `docs/SESSION_TRACKING_USER_GUIDE.md` (user guide)

### Verification

1. MCP tool call: `session_tracking_sync_history()` → returns preview JSON
2. MCP tool call: `session_tracking_sync_history(dry_run=False)` → parameter ignored, returns preview
3. CLI call: `graphiti-mcp session-tracking sync --no-dry-run` → performs actual sync

---

## Metadata

**Blocks Stories**: None
**Priority**: HIGH (remediation)
**Estimated Tokens**: ~1,500 (implementation) + ~500 (testing)
