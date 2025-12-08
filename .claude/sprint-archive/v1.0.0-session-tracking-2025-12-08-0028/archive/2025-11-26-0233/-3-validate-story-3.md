# Validation Story -3: Validate Story 3

**Status**: unassigned
**Priority**: P0
**Assigned**: agent
**Created**: 2025-11-26T09:34:16.399475+00:00
**Validation Target**: Story 3

---

## Purpose

Comprehensive validation of Story 3: File Monitoring

This validation story performs all quality checks and auto-repairs issues where possible.

---

## Validation Target

**Story**: 3
**Title**: File Monitoring
**Status**: completed
**File**: stories/3-untitled.md

---

## Acceptance Criteria

- [ ] **(P0) AC--3.1**: Execute Check A: Metadata validation
  - Validate status, priority, assigned fields
  - Auto-fix: Invalid metadata formatting

- [ ] **(P0) AC--3.2**: Execute Check B: Acceptance criteria completion
  - Verify all ACs have priority tags
  - Verify all ACs have checkboxes
  - Auto-fix: Missing AC formatting

- [ ] **(P0) AC--3.3**: Execute Check C: Requirements traceability
  - Map ACs to test coverage
  - Identify coverage gaps
  - Auto-fix: Cannot auto-create tests (report only)

- [ ] **(P0) AC--3.4**: Execute Check D: Test pass rates
  - Verify P0 pass rate >= 100%
  - Verify P1 pass rate >= 90%
  - Auto-fix: Cannot fix failing tests (report + block)

- [ ] **(P0) AC--3.5**: Execute Check E: Advisory status alignment
  - Verify status matches advisory priority
  - Auto-fix: Update story status to match advisories

- [ ] **(P0) AC--3.6**: Execute Check F: Hierarchy consistency
  - Verify parent-substory relationships
  - Auto-fix: Cannot fix hierarchy (report + block)

- [ ] **(P0) AC--3.7**: Execute Check G: Advisory alignment
  - Verify substory advisory resolutions propagated to parent
  - Auto-fix: Update parent advisory status

- [ ] **(P1) AC--3.8**: Execute Check H: Dependency graph alignment
  - Verify dependencies satisfied
  - Auto-fix: Already handled by ordering (informational only)

- [ ] **(P0) AC--3.9**: Calculate quality score
  - Generate validation report
  - Determine pass/fail status

- [ ] **(P0) AC--3.10**: Auto-repair or block
  - Apply auto-fixes where possible
  - Block with user options if cannot auto-repair
  - Mark validation story: completed or blocked

---

## Validation Execution Instructions

**For /sprint:NEXT**:

When this validation story is executed, use the validation execution helper:

```bash
cat ~/.claude/resources/commands/sprint/execute-validation-story.md
```

Follow the helper's instructions to execute checks A-H sequentially.

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

---

## Success Criteria

- All P0 acceptance criteria checked
- Auto-repairs applied where possible
- Validation report generated
- Quality score calculated
- Validation story marked: completed or blocked
