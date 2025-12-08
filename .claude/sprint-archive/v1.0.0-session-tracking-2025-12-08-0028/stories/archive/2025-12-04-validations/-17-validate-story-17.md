# Validation Story -17: Validate Story 17

**Status**: unassigned
**Priority**: P0
**Assigned**: agent
**Created**: 2025-11-28T07:16:52.093928+00:00
**Validation Target**: Story 17

---

## Purpose

Comprehensive validation of Story 17: LLM Availability Layer

This validation story performs all quality checks and auto-repairs issues where possible.

---

## Validation Target

**Story**: 17
**Title**: LLM Availability Layer
**Status**: completed
**File**: stories/17-llm-availability-layer.md

---

## Acceptance Criteria

- [ ] **(P0) AC--17.1**: Execute Check A: Metadata validation
  - Validate status, priority, assigned fields
  - Auto-fix: Invalid metadata formatting

- [ ] **(P0) AC--17.2**: Execute Check B: Acceptance criteria completion
  - Verify all ACs have priority tags
  - Verify all ACs have checkboxes
  - Auto-fix: Missing AC formatting

- [ ] **(P0) AC--17.3**: Execute Check C: Requirements traceability
  - Map ACs to test coverage
  - Identify coverage gaps
  - Auto-fix: Cannot auto-create tests (report only)

- [ ] **(P0) AC--17.4**: Execute Check D: Test pass rates
  - Verify P0 pass rate >= 100%
  - Verify P1 pass rate >= 90%
  - Auto-fix: Cannot fix failing tests (report + block)

- [ ] **(P0) AC--17.5**: Execute Check E: Advisory status alignment
  - Verify status matches advisory priority
  - Auto-fix: Update story status to match advisories

- [ ] **(P0) AC--17.6**: Execute Check F: Hierarchy consistency
  - Verify parent-substory relationships
  - Auto-fix: Cannot fix hierarchy (report + block)

- [ ] **(P0) AC--17.7**: Execute Check G: Advisory alignment
  - Verify substory advisory resolutions propagated to parent
  - Auto-fix: Update parent advisory status

- [ ] **(P1) AC--17.8**: Execute Check H: Dependency graph alignment
  - Verify dependencies satisfied
  - Auto-fix: Already handled by ordering (informational only)

- [ ] **(P0) AC--17.9**: Execute Check I: Code implementation validation
  - Verify code exists for all P0 acceptance criteria
  - Verify semantic alignment (code matches AC descriptions)
  - Verify implementation recency (code modified recently)
  - Verify test coverage references actual implementation
  - Auto-fix: Cannot fix missing code (create remediation stories)

- [ ] **(P0) AC--17.10**: Calculate quality score
  - Generate validation report
  - Determine pass/fail status

- [ ] **(P0) AC--17.11**: Auto-repair or block
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
