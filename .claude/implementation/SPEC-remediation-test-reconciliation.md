# Design Spec: Remediation Test Reconciliation System

**Version**: 1.0.0-draft
**Created**: 2025-12-19
**Status**: Design Phase
**Author**: Claude Code (via user collaboration)

---

## Executive Summary

When a remediation story fixes test failures in a target story, the system should automatically reconcile the validation status without requiring redundant re-testing. This spec defines the algorithm, metadata schema, and integration points for automatic propagation of remediation test results to blocked validation stories.

---

## Problem Statement

### Current Behavior (Bug)

1. Story 1.t testing phase fails with 59.26% pass rate
2. Validation -1.t runs Check D, detects failure, marks itself as BLOCKED
3. Remediation story 1.r is created to fix the test isolation issue
4. Remediation 1.r.t runs the **same tests** and achieves 100% pass rate
5. **BUG**: Validation -1.t remains BLOCKED despite the fix being verified

### Root Cause

No reconciliation logic exists between remediation testing outcomes and the validation stories they were created to address. The system treats them as independent, unrelated test executions.

### Impact

- Wasted tokens re-running already-verified tests
- Manual intervention required to unblock validation stories
- Stale status indicators in sprint queue
- User confusion about sprint completion state

---

## Scope

### In Scope

1. Remediation stories created in response to **existing implementation failures**
2. Test result propagation from remediation.t to target validation
3. Metadata schema for tracking reconciliation relationships
4. Status updates for validation stories and containers
5. Three reconciliation modes: propagate, retest, supersede

### Out of Scope

1. Remediation for not-yet-implemented stories (use story amendment instead)
2. Non-testing remediation (discovery/implementation phase fixes)
3. Cross-sprint remediation tracking
4. Historical remediation analysis

---

## Design Principles

1. **Zero Redundant Testing**: If remediation.t passes the same tests, don't re-run them
2. **Explicit Metadata**: Reconciliation mode captured at creation time, not inferred
3. **Fail-Safe Defaults**: When uncertain, require manual verification (retest mode)
4. **Audit Trail**: All propagations logged with source, timestamp, and rationale
5. **Container Consistency**: Parent status always reflects child states

---

## Reconciliation Modes

### Mode 1: PROPAGATE (Default)

**When**: Remediation tests are identical to validation Check D tests

**Behavior**:
- Remediation.t passes → Validation.t marked COMPLETED
- Test results copied/referenced from remediation
- No re-execution of tests

**Criteria**:
- `overlap_ratio >= 0.95` (95% of test files match)
- `same_test_parameters == true` (threshold, command, etc.)
- `remediation.metadata.supersedes_tests != true`

**Example**:
```
1.r.t runs: pytest tests/test_unified_config.py tests/test_project_overrides.py
-1.t Check D runs: pytest tests/test_unified_config.py tests/test_project_overrides.py
→ 95%+ overlap, same params → PROPAGATE
```

### Mode 2: RETEST

**When**: Remediation modified test approach but original tests still valid

**Behavior**:
- Remediation.t passes → Validation.t marked UNASSIGNED (unblocked)
- Original tests must be re-run to verify compatibility
- Validation.t gets `needs_retest: true` metadata

**Criteria**:
- `overlap_ratio >= 0.50 AND < 0.95`
- OR `same_test_parameters == false`
- AND `remediation.metadata.supersedes_tests != true`

**Example**:
```
1.r.t runs: pytest tests/test_unified_config.py -k "test_config_loads"
-1.t Check D runs: pytest tests/test_unified_config.py tests/test_project_overrides.py
→ Partial overlap, different scope → RETEST
```

### Mode 3: SUPERSEDE

**When**: Remediation fundamentally changes the testing approach

**Behavior**:
- Remediation.t passes → Validation.t marked SUPERSEDED
- Original tests are obsolete, no re-run needed
- Supersession reason captured in metadata

**Criteria**:
- `remediation.metadata.supersedes_tests == true`
- User explicitly marked during remediation creation

**Example**:
```
Original: Integration tests with real database
Remediation: Replaced with mocked unit tests (architectural decision)
→ Old tests obsolete → SUPERSEDE
```

### Mode 4: NO_MATCH (Fallback)

**When**: Remediation doesn't address the validation failure

**Behavior**:
- Validation.t remains BLOCKED
- No status change
- Log indicates remediation didn't resolve Check D

**Criteria**:
- `overlap_ratio < 0.50`
- OR remediation targets different phase (not testing)

---

## Metadata Schema

### Remediation Story Schema Extension

```yaml
# Added to remediation story metadata
test_reconciliation:
  # Required fields
  mode: "propagate" | "retest" | "supersede"
  target_validation_phase: "-{story_id}.t"  # e.g., "-1.t"

  # Test identity (for propagate/retest modes)
  test_files:
    - "tests/test_unified_config.py"
    - "tests/test_project_overrides.py"
  test_command: "pytest tests/test_project_overrides.py tests/test_unified_config.py -v"
  test_threshold: 90  # Percentage

  # Original failure context
  original_pass_rate: 59.26
  original_failed_tests: 11
  original_total_tests: 27

  # Supersession (for supersede mode only)
  supersedes_tests: false
  supersession_reason: null  # Required if supersedes_tests=true

  # Computed at remediation.t completion
  reconciliation_applied: false
  reconciliation_timestamp: null
```

### Validation Story Schema Extension

```yaml
# Added to validation story metadata when reconciled
reconciliation:
  status: "propagated" | "retested" | "superseded" | "pending"
  source_story: "1.r.t"
  source_pass_rate: 100
  source_test_count: 77
  applied_at: "2025-12-19T07:30:00Z"

  # For retest mode
  needs_retest: false
  retest_reason: null

  # For supersede mode
  superseded_by: null
  supersession_reason: null

  # Audit trail
  propagation_note: "Pass propagated from remediation 1.r.t (100% pass rate, 77/77 tests)"
```

---

## Algorithm

### Phase 1: Remediation Creation

```python
def create_remediation_for_test_failure(
    target_story_id: str,
    validation_story_id: str,
    failure_details: TestFailureDetails
) -> RemediationStory:
    """
    Called by /sprint:REMEDIATE when creating remediation for Check D failure.
    """
    remediation = create_story(
        type="remediation",
        remediation_type="bug_fix",
        parent=target_story_id,
        # ... standard fields ...
    )

    # Capture test identity for reconciliation
    remediation.metadata["test_reconciliation"] = {
        "mode": "propagate",  # Default assumption
        "target_validation_phase": f"{validation_story_id}",
        "test_files": failure_details.test_files,
        "test_command": failure_details.test_command,
        "test_threshold": failure_details.threshold,
        "original_pass_rate": failure_details.pass_rate,
        "original_failed_tests": failure_details.failed_count,
        "original_total_tests": failure_details.total_count,
        "supersedes_tests": False,
        "reconciliation_applied": False
    }

    return remediation
```

### Phase 2: Remediation Testing Completion

```python
def on_remediation_testing_complete(
    remediation_story_id: str,
    test_results: TestResults
) -> ReconciliationResult:
    """
    Called when remediation.t phase completes.
    Triggers automatic reconciliation with target validation.
    """
    remediation = get_story(remediation_story_id)
    parent_remediation = get_story(remediation.parent)  # e.g., "1.r"

    reconciliation_config = parent_remediation.metadata.get("test_reconciliation")
    if not reconciliation_config:
        return ReconciliationResult(status="skipped", reason="No reconciliation config")

    # Check if remediation testing passed
    if test_results.pass_rate < reconciliation_config["test_threshold"]:
        return ReconciliationResult(
            status="failed",
            reason=f"Remediation tests failed ({test_results.pass_rate}% < {reconciliation_config['test_threshold']}%)"
        )

    target_validation = reconciliation_config["target_validation_phase"]
    mode = reconciliation_config["mode"]

    # Apply reconciliation based on mode
    if mode == "supersede":
        return apply_supersede_reconciliation(
            target_validation,
            remediation_story_id,
            reconciliation_config,
            test_results
        )

    elif mode == "propagate":
        # Verify test overlap before propagating
        overlap = calculate_test_overlap(
            remediation_tests=test_results.test_files,
            target_tests=reconciliation_config["test_files"]
        )

        if overlap >= 0.95 and same_test_parameters(test_results, reconciliation_config):
            return apply_propagate_reconciliation(
                target_validation,
                remediation_story_id,
                reconciliation_config,
                test_results
            )
        else:
            # Downgrade to retest mode
            return apply_retest_reconciliation(
                target_validation,
                remediation_story_id,
                reconciliation_config,
                test_results,
                reason="Test overlap below threshold"
            )

    elif mode == "retest":
        return apply_retest_reconciliation(
            target_validation,
            remediation_story_id,
            reconciliation_config,
            test_results
        )

    else:
        return ReconciliationResult(status="error", reason=f"Unknown mode: {mode}")
```

### Phase 3: Reconciliation Application

```python
def apply_propagate_reconciliation(
    target_validation: str,
    source_story: str,
    config: dict,
    results: TestResults
) -> ReconciliationResult:
    """
    Direct pass propagation - no retest needed.
    """
    # Update validation story status
    update_story(
        story_id=target_validation,
        status="completed",
        metadata={
            "reconciliation": {
                "status": "propagated",
                "source_story": source_story,
                "source_pass_rate": results.pass_rate,
                "source_test_count": results.total_tests,
                "applied_at": datetime.utcnow().isoformat(),
                "propagation_note": f"Pass propagated from {source_story} ({results.pass_rate}% pass rate, {results.passed}/{results.total_tests} tests)"
            }
        }
    )

    # Update parent validation container
    propagate_status_to_parent(target_validation)

    # Mark reconciliation as applied on remediation
    update_remediation_reconciliation_status(
        config["target_validation_phase"].replace(".t", ""),  # Get parent remediation
        applied=True
    )

    return ReconciliationResult(
        status="success",
        mode="propagate",
        target=target_validation,
        source=source_story,
        message=f"Validation {target_validation} marked completed via propagation"
    )


def apply_retest_reconciliation(
    target_validation: str,
    source_story: str,
    config: dict,
    results: TestResults,
    reason: str = None
) -> ReconciliationResult:
    """
    Unblock but require verification.
    """
    update_story(
        story_id=target_validation,
        status="unassigned",  # Ready for execution
        metadata={
            "reconciliation": {
                "status": "pending_retest",
                "source_story": source_story,
                "needs_retest": True,
                "retest_reason": reason or "Remediation modified test approach",
                "applied_at": datetime.utcnow().isoformat()
            }
        }
    )

    return ReconciliationResult(
        status="success",
        mode="retest",
        target=target_validation,
        source=source_story,
        message=f"Validation {target_validation} unblocked, requires retest"
    )


def apply_supersede_reconciliation(
    target_validation: str,
    source_story: str,
    config: dict,
    results: TestResults
) -> ReconciliationResult:
    """
    Mark original tests as obsolete.
    """
    update_story(
        story_id=target_validation,
        status="superseded",
        metadata={
            "reconciliation": {
                "status": "superseded",
                "superseded_by": source_story,
                "supersession_reason": config.get("supersession_reason", "Test approach replaced by remediation"),
                "applied_at": datetime.utcnow().isoformat()
            }
        }
    )

    # Propagate completed to parent (superseded counts as resolved)
    propagate_status_to_parent(target_validation, treat_superseded_as="completed")

    return ReconciliationResult(
        status="success",
        mode="supersede",
        target=target_validation,
        source=source_story,
        message=f"Validation {target_validation} superseded by {source_story}"
    )
```

### Phase 4: Container Status Propagation

```python
def propagate_status_to_parent(
    child_story_id: str,
    treat_superseded_as: str = "completed"
) -> None:
    """
    Recalculate parent container status based on children.
    """
    child = get_story(child_story_id)
    parent_id = child.parent

    if not parent_id:
        return

    parent = get_story(parent_id)
    children = [get_story(cid) for cid in parent.children]

    # Map statuses
    status_map = {
        "completed": "resolved",
        "superseded": treat_superseded_as,
        "blocked": "blocked",
        "in_progress": "in_progress",
        "unassigned": "pending"
    }

    resolved_statuses = ["completed", "superseded"] if treat_superseded_as == "completed" else ["completed"]

    # Calculate parent status
    all_resolved = all(c.status in resolved_statuses for c in children)
    any_blocked = any(c.status == "blocked" for c in children)
    any_in_progress = any(c.status == "in_progress" for c in children)

    if all_resolved:
        new_status = "completed"
    elif any_blocked:
        new_status = "blocked"
    elif any_in_progress:
        new_status = "in_progress"
    else:
        new_status = parent.status  # No change

    if new_status != parent.status:
        update_story(parent_id, status=new_status)

        # Recurse to grandparent if exists
        if parent.parent:
            propagate_status_to_parent(parent_id, treat_superseded_as)
```

---

## Integration Points

### 1. /sprint:REMEDIATE

**Location**: `~/.claude/commands/sprint/REMEDIATE.md`

**Changes**:
- Add `test_reconciliation` metadata block when creating remediation for Check D failures
- Capture test identity from original failure details
- Allow user to specify `--supersedes-tests` flag for supersession mode

**New Parameters**:
```bash
/sprint:REMEDIATE --target "1" --reason "Fix test isolation"
  [--supersedes-tests]           # Mark as superseding original tests
  [--supersession-reason "..."]  # Required with --supersedes-tests
  [--retest-mode]                # Force retest mode instead of propagate
```

### 2. /sprint:NEXT (Testing Phase Completion)

**Location**: `~/.claude/commands/sprint/NEXT.md` → testing phase handler

**Changes**:
- After remediation.t completes successfully, trigger reconciliation
- Call `on_remediation_testing_complete()` algorithm
- Report reconciliation result to user

**New Output**:
```
✅ Story 1.r.t: Testing phase complete (100% pass rate)

🔄 Reconciliation Applied:
   → Validation -1.t: PROPAGATED (was: blocked)
   → Source: 1.r.t (100%, 77/77 tests)
   → Parent -1: COMPLETED
```

### 3. queue_helpers.py

**Location**: `~/.claude/resources/commands/sprint/queue_helpers.py`

**New Commands**:
```bash
# Check if reconciliation is pending for a validation story
queue_helpers.py check-reconciliation --story-id "-1.t" --json

# Apply reconciliation manually (for edge cases)
queue_helpers.py apply-reconciliation \
  --validation-story "-1.t" \
  --source-story "1.r.t" \
  --mode "propagate" \
  --json

# Get reconciliation status for sprint
queue_helpers.py reconciliation-status --json
```

### 4. Validation Engine

**Location**: `~/.claude/resources/commands/sprint/validation_engine.py`

**Changes**:
- Before running Check D, check for pending reconciliation
- If reconciliation exists and mode=propagate, skip test execution
- Honor retest flag to force re-execution

---

## User Experience

### Automatic (Default) Flow

```
User: /sprint:REMEDIATE --target "1" --reason "Fix test isolation"

Agent: Created remediation story 1.r
       → 1.r.d: Discovery phase
       → 1.r.i: Implementation phase
       → 1.r.t: Testing phase

       Reconciliation configured:
         Mode: propagate (default)
         Target: -1.t
         Will auto-propagate if 1.r.t passes with same tests

User: /sprint:NEXT  # Executes 1.r.d, 1.r.i, 1.r.t

Agent: ✅ Story 1.r.t complete (100% pass rate)

       🔄 Automatic Reconciliation:
          → -1.t: blocked → completed (propagated)
          → -1: blocked → completed
          → Reason: Same tests, same parameters, 100% pass
```

### Manual Override Flow

```
User: /sprint:REMEDIATE --target "1" --reason "Replace integration with unit tests" --supersedes-tests --supersession-reason "Architectural decision to use mocks"

Agent: Created remediation story 1.r
       Reconciliation configured:
         Mode: supersede
         Target: -1.t
         Original tests will be marked obsolete after 1.r.t passes
```

### Retest Required Flow

```
Agent: ⚠️ Story 1.r.t complete (95% pass rate)

       🔄 Partial Reconciliation:
          → -1.t: blocked → unassigned (unblocked)
          → Reason: Test overlap 78% (below 95% threshold)
          → Action required: Re-run -1.t to verify original test params
```

---

## Edge Cases

### 1. Multiple Remediations for Same Target

**Scenario**: Two remediation stories (1.r and 1.r2) both target Story 1 testing failures.

**Resolution**:
- Each remediation tracks its own reconciliation config
- First passing remediation applies propagation
- Subsequent remediations skip reconciliation (already resolved)
- Log: "Reconciliation skipped - target already resolved by 1.r"

### 2. Remediation Fails

**Scenario**: 1.r.t fails with 80% pass rate (below threshold).

**Resolution**:
- No reconciliation applied
- -1.t remains blocked
- Log: "Reconciliation not applied - remediation tests failed"

### 3. Partial Test Overlap

**Scenario**: Remediation only fixed some of the failing tests.

**Resolution**:
- If overlap < 95%, downgrade to retest mode
- Unblock validation but require re-execution
- Log: "Partial fix detected - validation unblocked, retest required"

### 4. Validation Already Completed

**Scenario**: User manually completed -1.t before reconciliation triggered.

**Resolution**:
- Skip reconciliation
- Log: "Reconciliation skipped - target already completed"

### 5. Superseded Target Story

**Scenario**: Story 1 was superseded while remediation was in progress.

**Resolution**:
- Skip reconciliation
- Mark remediation as obsolete
- Log: "Reconciliation skipped - target story superseded"

---

## Performance Considerations

### Token Savings

| Scenario | Without Reconciliation | With Reconciliation | Savings |
|----------|------------------------|---------------------|---------|
| Same tests, propagate | ~2,500t (re-run Check D) | ~100t (status update) | **96%** |
| Partial overlap, retest | ~2,500t | ~2,500t | 0% |
| Supersede mode | ~2,500t | ~100t | **96%** |

### Execution Time

- Propagate mode: ~2-5 seconds (metadata update only)
- Retest mode: ~30-120 seconds (full test execution)
- Supersede mode: ~2-5 seconds (metadata update only)

---

## Testing Requirements

### Unit Tests

1. `test_reconciliation_mode_detection` - Verify correct mode selection
2. `test_overlap_calculation` - Verify test file overlap math
3. `test_propagate_application` - Verify status updates for propagate mode
4. `test_retest_application` - Verify unblocking for retest mode
5. `test_supersede_application` - Verify supersession handling
6. `test_container_propagation` - Verify parent status updates

### Integration Tests

1. `test_full_remediation_flow_propagate` - End-to-end propagate scenario
2. `test_full_remediation_flow_retest` - End-to-end retest scenario
3. `test_full_remediation_flow_supersede` - End-to-end supersede scenario
4. `test_multiple_remediations` - Concurrent remediation handling
5. `test_edge_case_already_completed` - Skip if already resolved

### Manual Validation

1. Create remediation for real test failure
2. Complete remediation testing
3. Verify validation story status updated
4. Verify container status propagated
5. Verify audit trail in metadata

---

## Rollout Plan

### Phase 1: Metadata Schema (Non-Breaking)

- Add reconciliation fields to story metadata schema
- No behavioral changes
- Backwards compatible

### Phase 2: Creation-Time Capture

- Update /sprint:REMEDIATE to capture test identity
- Populate `test_reconciliation` metadata block
- Still requires manual reconciliation

### Phase 3: Automatic Reconciliation

- Add reconciliation trigger to testing phase completion
- Implement propagate/retest/supersede logic
- Full automation enabled

### Phase 4: Validation Engine Integration

- Skip Check D if reconciliation already applied
- Honor retest flags
- Performance optimization complete

---

## Open Questions

1. **Threshold Configurability**: Should the 95% overlap threshold be configurable per-project?

2. **Partial Propagation**: If remediation fixes 80% of failures, should we propagate partial results?

3. **Cross-Story Reconciliation**: If remediation 2.r fixes tests that also affect Story 1, should we propagate?

4. **Audit Retention**: How long should reconciliation audit data be retained?

5. **Manual Override**: Should users be able to force re-execution even after propagation?

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **Reconciliation** | Process of synchronizing remediation results with validation status |
| **Propagation** | Direct transfer of pass status from remediation to validation |
| **Supersession** | Marking original tests as obsolete in favor of new approach |
| **Overlap Ratio** | Percentage of test files common between remediation and validation |
| **Target Validation** | The validation story that remediation was created to address |

---

**End of Specification**
