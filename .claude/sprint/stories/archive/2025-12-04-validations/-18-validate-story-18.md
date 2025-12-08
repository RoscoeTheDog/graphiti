# Validation Story -18: Validate Story 18

**Status**: unassigned
**Priority**: P0
**Assigned**: agent
**Created**: 2025-11-28T07:02:29.507101+00:00
**Validation Target**: Story 18

---

## Purpose

Comprehensive validation of Story 18: MCP Tools Error Handling

This validation story performs all quality checks and auto-repairs issues where possible.

---

## Validation Target

**Story**: 18
**Title**: MCP Tools Error Handling
**Status**: completed
**File**: stories/18-mcp-tools-error-handling.md

---

## Acceptance Criteria

- [ ] **(P0) AC--18.1**: Execute Check A: Metadata validation
  - Validate status, priority, assigned fields
  - Auto-fix: Invalid metadata formatting

- [ ] **(P0) AC--18.2**: Execute Check B: Acceptance criteria completion
  - Verify all ACs have priority tags
  - Verify all ACs have checkboxes
  - Auto-fix: Missing AC formatting

- [ ] **(P0) AC--18.3**: Execute Check C: Requirements traceability
  - Map ACs to test coverage
  - Identify coverage gaps
  - Auto-fix: Cannot auto-create tests (report only)

- [ ] **(P0) AC--18.4**: Execute Check D: Test pass rates
  - Verify P0 pass rate >= 100%
  - Verify P1 pass rate >= 90%
  - Auto-fix: Cannot fix failing tests (report + block)

- [ ] **(P0) AC--18.5**: Execute Check E: Advisory status alignment
  - Verify status matches advisory priority
  - Auto-fix: Update story status to match advisories

- [ ] **(P0) AC--18.6**: Execute Check F: Hierarchy consistency
  - Verify parent-substory relationships
  - Auto-fix: Cannot fix hierarchy (report + block)

- [ ] **(P0) AC--18.7**: Execute Check G: Advisory alignment
  - Verify substory advisory resolutions propagated to parent
  - Auto-fix: Update parent advisory status

- [ ] **(P1) AC--18.8**: Execute Check H: Dependency graph alignment
  - Verify dependencies satisfied
  - Auto-fix: Already handled by ordering (informational only)

- [ ] **(P0) AC--18.9**: Execute Check I: Code implementation validation
  - Verify code exists for all P0 acceptance criteria
  - Verify semantic alignment (code matches AC descriptions)
  - Verify implementation recency (code modified recently)
  - Verify test coverage references actual implementation
  - Auto-fix: Cannot fix missing code (create remediation stories)

- [ ] **(P0) AC--18.10**: Calculate quality score
  - Generate validation report
  - Determine pass/fail status

- [ ] **(P0) AC--18.11**: Auto-repair or block
  - Apply auto-fixes where possible
  - Create remediation stories for code implementation failures
  - Block with user options if cannot auto-repair
  - Mark validation story: completed or blocked

---

## Validation Execution Instructions

**For /sprint:NEXT**:

When this validation story is executed, use the validation execution helper:

```bash
cat ~/.claude/resources/commands/sprint/execute-validation-story.md
```

Follow the helper's instructions to execute checks A-I sequentially.

**Two-Phase Validation**:
- **Phase 1**: Structure validation (Checks A-H)
- **Phase 2**: Code implementation validation (Check I) - only runs if Phase 1 passes

---

## Auto-Repair Actions

| Check | Auto-Repairable | Action |
|-------|-----------------|--------|
| A: Metadata | ✅ Yes | Fix invalid status/priority/assigned formatting |
| B: ACs | ✅ Yes | Add missing priority tags and checkboxes |
| C: Coverage | ❌ No | Report gaps, suggest test files |
| D: Pass Rates | ❌ No | Report failures, block for manual fix |
| E: Advisory Status | ✅ Yes | Update story status to match advisory priority |
| F: Hierarchy | ❌ No | Report issues, block for manual fix |
| G: Advisory Alignment | ✅ Yes | Propagate advisory resolutions to parent |
| H: Dependencies | ℹ️ Info | Already fixed in ordering (informational) |
| I: Code Implementation | 🔧 Remediation | Create remediation stories for missing/misaligned code |

---

## Success Criteria

- All P0 acceptance criteria checked
- Auto-repairs applied where possible
- Validation report generated
- Quality score calculated
- Validation story marked: completed or blocked
