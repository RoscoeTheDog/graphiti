---
description: Update docs: retroactive sync capability in FAQ
---

# Story R1: Update docs: retroactive sync capability in FAQ

**Type**: Remediation
**Status**: completed
**Parent**: None (top-level)
**Created**: 2025-12-05T16:30:38.815018
**Issue Type**: Documentation Inconsistency

---

## Remediation Purpose

This remediation story addresses a documentation inconsistency discovered during sprint audit.

**Issue Category**: Documentation
**Detected By**: Sprint v1.0.0 Audit (session s009)
**Affects Stories**: Story 13 (Manual Sync)

---

## Issue Description

The FAQ in `docs/SESSION_TRACKING_USER_GUIDE.md` (line 357) states:
> "Can I track sessions retroactively? A: No. Only sessions created while tracking is enabled are indexed."

However, the `session_tracking_sync_history` MCP tool (implemented in Story 13) explicitly enables retroactive session indexing with:
- Configurable lookback period (`days` parameter, default 7)
- All history option (`days=0`)
- Preview mode (`dry_run=True`) for cost estimation
- Actual sync (`dry_run=False`)

This creates user confusion - the FAQ incorrectly tells users they cannot do something the tool explicitly supports.

---

## Remediation Steps

1. [x] **Discovery**: Locate and verify the inconsistency (R1.d - completed)
2. [x] **Implementation**: Update FAQ answer to accurately reflect the capability (R1.i - completed)
3. [x] **Testing**: Verify documentation renders correctly and cross-references are valid (R1.t - completed)

---

## Acceptance Criteria

- [x] FAQ question "Can I track sessions retroactively?" updated to say "Yes"
- [x] Answer references `session_tracking_sync_history` tool
- [x] Cross-reference to MCP_TOOLS.md is accurate and working
- [x] Documentation renders correctly in markdown preview

---

## Implementation Notes

### Root Cause

FAQ was written before Story 13 (Manual Sync) was implemented. When the sync_history tool was added, the FAQ was not updated.

### Fix Strategy

Update the single FAQ entry (lines 357-358) to:
1. Change "No" to "Yes!"
2. Mention the `session_tracking_sync_history` tool
3. Briefly explain dry_run vs actual sync
4. Reference MCP_TOOLS.md for details

### Verification

1. Check markdown preview renders correctly
2. Verify cross-reference link to MCP_TOOLS.md is accurate
3. Ensure answer is concise but informative

---

## Metadata

**Blocks Stories**: None
**Priority**: P2 (documentation consistency)
**Estimated Tokens**: 500
**Plan File**: .claude/sprint/plans/R1-plan.yaml
