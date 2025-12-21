# Execute Testing Phase

**Purpose**: Execute testing phase for stories (implementation.t, remediation.t, validation.t).

**Called by**: `story-execution-dispatch.md` when `NEXT_STORY.type` ends with `.t`

**Phase**: Testing (final validation of implementation)

---

## Prerequisites

Agent: Ensure the following are available from parent dispatch:
- `NEXT_STORY` (story object with id, type, status, file, title, parent)
- `SCRIPT_DIR` (path to queue_helpers.py)
- `STORY_CONTENT` (parsed story file content)

---

## Testing Phase Execution

### STEP 1: Extract Test Requirements

Agent: Parse test requirements from STORY_CONTENT.

Look for sections:
- `## Test Requirements` or `## Testing`
- `## Test Strategy`
- Test file paths or patterns

Store extracted requirements as TEST_REQUIREMENTS.

**IF TEST_REQUIREMENTS is empty or missing**:
```
Announce: "⚠️ No test requirements found in story file"
Announce: "   Expected section: ## Test Requirements or ## Testing"
Announce: ""
Announce: "Proceeding with default test discovery (pytest, all test files)"
```

Set TEST_REQUIREMENTS to default:
```json
{
  "test_command": "pytest",
  "test_pattern": "tests/**/*.py",
  "pass_threshold": 90.0
}
```

---

### STEP 2: Locate Test Files

Agent: Find test files based on TEST_REQUIREMENTS.

**IF TEST_REQUIREMENTS contains explicit test file paths**:
```bash
# Use explicit paths
TEST_FILES="${TEST_REQUIREMENTS.test_files}"
```

**ELSE** (use pattern-based discovery):
```bash
# Find test files matching pattern
find tests/ -name "*.py" -type f 2>/dev/null | grep -v __pycache__
```

Agent: Store result as TEST_FILES (newline-separated list).

**IF TEST_FILES is empty**:
```
Announce: "❌ No test files found"
Announce: "   Pattern: ${TEST_REQUIREMENTS.test_pattern}"
Announce: "   Please add test files or update test pattern in story file"
HALT execution
```

Count test files:
```bash
echo "${TEST_FILES}" | wc -l
```

Agent: Store as TEST_FILE_COUNT.

```
Announce: "📋 Found ${TEST_FILE_COUNT} test file(s)"
```

---

### STEP 3: Install Test Dependencies

Agent: Check if test dependencies need to be installed.

```bash
# Check if pytest is available
command -v pytest >/dev/null 2>&1 && echo "installed" || echo "missing"
```

Agent: Store as PYTEST_STATUS.

**IF PYTEST_STATUS == "missing"**:
```
Announce: "📦 Installing test dependencies..."
```

```bash
pip install pytest pytest-cov pytest-xdist
```

Agent: Verify installation succeeded (check exit code).

**IF installation failed**:
```
Announce: "❌ Failed to install test dependencies"
Announce: "   Please install manually: pip install pytest pytest-cov pytest-xdist"
HALT execution
```

---

### STEP 4: Run Tests

```
Announce: "🧪 Running tests..."
Announce: ""
```

Extract test command from TEST_REQUIREMENTS (default: pytest):
```bash
TEST_COMMAND="${TEST_REQUIREMENTS.test_command:-pytest}"
```

Run tests with coverage and JSON output:
```bash
${TEST_COMMAND} \
  --cov=. \
  --cov-report=json:.claude/sprint/test-results/${NEXT_STORY.story_id}-coverage.json \
  --json-report \
  --json-report-file=.claude/sprint/test-results/${NEXT_STORY.story_id}-results.json \
  ${TEST_FILES} \
  2>&1 | tee .claude/sprint/test-results/${NEXT_STORY.story_id}-output.log
```

Agent: Capture exit code as TEST_EXIT_CODE.

---

### STEP 5: Parse Test Results

```bash
cat .claude/sprint/test-results/${NEXT_STORY.story_id}-results.json
```

Agent: Parse JSON output, store as TEST_RESULTS.

**Expected structure**:
```json
{
  "summary": {
    "total": 50,
    "passed": 47,
    "failed": 3,
    "skipped": 0
  },
  "tests": [...],
  "duration": 12.5
}
```

Extract metrics:
```bash
TOTAL_TESTS=$(echo "${TEST_RESULTS}" | jq -r '.summary.total')
PASSED_TESTS=$(echo "${TEST_RESULTS}" | jq -r '.summary.passed')
FAILED_TESTS=$(echo "${TEST_RESULTS}" | jq -r '.summary.failed')
```

---

### STEP 6: Calculate Pass Rate

```bash
# Calculate pass rate percentage
if [[ ${TOTAL_TESTS} -eq 0 ]]; then
  PASS_RATE=0.0
else
  PASS_RATE=$(echo "scale=2; (${PASSED_TESTS} * 100) / ${TOTAL_TESTS}" | bc)
fi
```

Agent: Store as PASS_RATE.

---

### STEP 7: Check Pass Threshold

Extract threshold from TEST_REQUIREMENTS (default: 90.0):
```bash
PASS_THRESHOLD="${TEST_REQUIREMENTS.pass_threshold:-90.0}"
```

Compare pass rate to threshold:
```bash
# Compare pass rate to threshold (using bc for float comparison)
THRESHOLD_MET=$(echo "${PASS_RATE} >= ${PASS_THRESHOLD}" | bc -l)
```

Agent: Store as THRESHOLD_MET (1 = met, 0 = not met).

---

### STEP 8: Generate Test Results Artifact

Create comprehensive test results file:

```bash
cat > .claude/sprint/test-results/${NEXT_STORY.story_id}-summary.md <<EOF
# Test Results: ${NEXT_STORY.story_id}

**Story**: ${NEXT_STORY.title}
**Type**: ${NEXT_STORY.type}
**Executed**: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | ${TOTAL_TESTS} |
| Passed | ${PASSED_TESTS} |
| Failed | ${FAILED_TESTS} |
| Pass Rate | ${PASS_RATE}% |
| Threshold | ${PASS_THRESHOLD}% |
| Status | $([[ ${THRESHOLD_MET} -eq 1 ]] && echo "✅ PASS" || echo "❌ FAIL") |

## Test Files

${TEST_FILES}

## Failed Tests

$([[ ${FAILED_TESTS} -gt 0 ]] && echo "${TEST_RESULTS}" | jq -r '.tests[] | select(.outcome == "failed") | "- \(.nodeid): \(.longrepr)"' || echo "None")

## Coverage

$(cat .claude/sprint/test-results/${NEXT_STORY.story_id}-coverage.json 2>/dev/null | jq -r '.totals.percent_covered // "N/A"')%

## Full Output

See: .claude/sprint/test-results/${NEXT_STORY.story_id}-output.log
EOF
```

---

### STEP 9: Update Story Status Based on Results

**IF THRESHOLD_MET == 1** (tests passed):

```
Announce: "✅ Tests Passed: ${PASSED_TESTS}/${TOTAL_TESTS} (${PASS_RATE}%)"
```

```bash
python "${SCRIPT_DIR}/queue_helpers.py" update-status \
  --story-id "${NEXT_STORY.story_id}" \
  --status completed \
  --json
```

Agent: Verify status updated successfully.

**ELSE** (tests failed):

```
Announce: "❌ Tests Failed: ${PASSED_TESTS}/${TOTAL_TESTS} (${PASS_RATE}% < ${PASS_THRESHOLD}%)"
Announce: ""
Announce: "Failed tests:"
```

Display failed tests:
```bash
echo "${TEST_RESULTS}" | jq -r '.tests[] | select(.outcome == "failed") | "  - \(.nodeid)"'
```

```bash
python "${SCRIPT_DIR}/queue_helpers.py" update-status \
  --story-id "${NEXT_STORY.story_id}" \
  --status blocked \
  --json
```

```bash
# Set metadata indicating test failure
python "${SCRIPT_DIR}/queue_helpers.py" set-metadata \
  --story-id "${NEXT_STORY.story_id}" \
  --key "test_failure" \
  --value "{\"pass_rate\": ${PASS_RATE}, \"threshold\": ${PASS_THRESHOLD}, \"failed_count\": ${FAILED_TESTS}}" \
  --json
```

```
Announce: ""
Announce: "Story ${NEXT_STORY.story_id} marked as blocked (test failure)"
Announce: "   Review test results: .claude/sprint/test-results/${NEXT_STORY.story_id}-summary.md"
Announce: "   Create remediation: /sprint:REMEDIATE"
```

---

### STEP 10: Create Testing Advisory

Generate advisory file with test results and recommendations:

```bash
cat > .claude/sprint/${NEXT_STORY.story_id}-testing-advisory.md <<EOF
# Testing Advisory: ${NEXT_STORY.story_id}

**Generated**: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
**Status**: $([[ ${THRESHOLD_MET} -eq 1 ]] && echo "Completed" || echo "Blocked (Test Failure)")

## Test Results Summary

- **Pass Rate**: ${PASS_RATE}% (threshold: ${PASS_THRESHOLD}%)
- **Total Tests**: ${TOTAL_TESTS}
- **Passed**: ${PASSED_TESTS}
- **Failed**: ${FAILED_TESTS}

## Recommendations

$([[ ${THRESHOLD_MET} -eq 1 ]] && cat <<PASS_REC
✅ **All tests passed**

Next steps:
1. Review test coverage report
2. Consider adding edge case tests
3. Proceed to next story: /sprint:NEXT
PASS_REC
|| cat <<FAIL_REC
❌ **Tests failed below threshold**

Next steps:
1. Review failed tests in: .claude/sprint/test-results/${NEXT_STORY.story_id}-summary.md
2. Debug failures using output log: .claude/sprint/test-results/${NEXT_STORY.story_id}-output.log
3. Create remediation story: /sprint:REMEDIATE
4. Or manually fix and re-run: /sprint:NEXT --story ${NEXT_STORY.story_id}
FAIL_REC
)

## Test Files Executed

${TEST_FILES}

## Related Artifacts

- Summary: .claude/sprint/test-results/${NEXT_STORY.story_id}-summary.md
- JSON Results: .claude/sprint/test-results/${NEXT_STORY.story_id}-results.json
- Coverage: .claude/sprint/test-results/${NEXT_STORY.story_id}-coverage.json
- Output Log: .claude/sprint/test-results/${NEXT_STORY.story_id}-output.log
EOF
```

---

### STEP 11: Update Queue State

Regenerate index from queue:
```bash
python "${SCRIPT_DIR}/generate_index_from_queue.py" --sprint-dir .claude/sprint
```

---

### STEP 12: Commit Test Results

```bash
git add .claude/sprint/test-results/${NEXT_STORY.story_id}-*
git add .claude/sprint/${NEXT_STORY.story_id}-testing-advisory.md
git add .claude/sprint/.queue.json
git add .claude/sprint/index.md
```

```bash
git commit -m "test(sprint): Story ${NEXT_STORY.story_id} - Testing phase $([[ ${THRESHOLD_MET} -eq 1 ]] && echo "completed" || echo "failed")

Pass rate: ${PASS_RATE}% (threshold: ${PASS_THRESHOLD}%)
Tests: ${PASSED_TESTS}/${TOTAL_TESTS} passed

$([[ ${THRESHOLD_MET} -eq 1 ]] && echo "✅ All acceptance criteria met" || echo "❌ Tests failed - remediation required")"
```

---

### STEP 13: Announce Completion

**IF THRESHOLD_MET == 1** (success):

```
Announce: ""
Announce: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Announce: "✅ Story ${NEXT_STORY.story_id} Testing Complete"
Announce: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Announce: ""
Announce: "Test Results: ${PASSED_TESTS}/${TOTAL_TESTS} passed (${PASS_RATE}%)"
Announce: "Status: Completed"
Announce: ""
Announce: "Artifacts:"
Announce: "  - Summary: .claude/sprint/test-results/${NEXT_STORY.story_id}-summary.md"
Announce: "  - Advisory: .claude/sprint/${NEXT_STORY.story_id}-testing-advisory.md"
Announce: ""
```

**ELSE** (failure):

```
Announce: ""
Announce: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Announce: "❌ Story ${NEXT_STORY.story_id} Testing Failed"
Announce: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Announce: ""
Announce: "Test Results: ${PASSED_TESTS}/${TOTAL_TESTS} passed (${PASS_RATE}% < ${PASS_THRESHOLD}%)"
Announce: "Status: Blocked"
Announce: ""
Announce: "Next Steps:"
Announce: "  1. Review failures: .claude/sprint/test-results/${NEXT_STORY.story_id}-summary.md"
Announce: "  2. Create remediation: /sprint:REMEDIATE"
Announce: ""
```

---

### STEP 14: Trigger Reconciliation (Conditional - Remediation Stories Only)

**Purpose**: After successful remediation.t completion, reconcile with blocked validation story.

Agent: Check if this is a remediation story that passed testing.

#### STEP 14.1: Detect Remediation Story Type

```bash
# Get parent story ID
PARENT_ID="${NEXT_STORY.parent}"

# Check if parent ID indicates remediation story
# Patterns: starts with 'R' or contains '.r.'
echo "${PARENT_ID}" | grep -qE '^R[0-9]|\.r\.'
IS_REMEDIATION=$?
```

Agent: Store as IS_REMEDIATION (0 = is remediation, 1 = not remediation).

**IF IS_REMEDIATION == 1** (not a remediation story):
```
Skip STEP 14 - reconciliation only applies to remediation stories
END testing phase execution
```

**IF IS_REMEDIATION == 0 AND THRESHOLD_MET == 0** (remediation tests failed):
```
Announce: "ℹ️ Reconciliation skipped - remediation tests did not pass threshold"
END testing phase execution
```

**IF IS_REMEDIATION == 0 AND THRESHOLD_MET == 1** (remediation story with passing tests):

```
Announce: ""
Announce: "🔄 Initiating Test Reconciliation..."
Continue to STEP 14.2
```

---

#### STEP 14.2: Discover Blocked Validation Story

Extract original story ID from remediation metadata:

```bash
# Get remediation metadata from parent story
REMEDIATION_METADATA=$(python "${SCRIPT_DIR}/queue_helpers.py" get-story \
  --story-id "${PARENT_ID}" --json | jq -r '.metadata.test_reconciliation // empty')
```

Agent: Store as REMEDIATION_METADATA.

**IF REMEDIATION_METADATA is empty**:
```
Announce: "ℹ️ Reconciliation Skipped"
Announce: "   Reason: No test_reconciliation metadata found in parent story ${PARENT_ID}"
Announce: "   This may not be a remediation story created by REMEDIATE command"
END testing phase execution
```

Extract original story ID:
```bash
ORIGINAL_STORY_ID=$(echo "${REMEDIATION_METADATA}" | jq -r '.original_story_id // empty')
```

Agent: Store as ORIGINAL_STORY_ID.

**IF ORIGINAL_STORY_ID is empty**:
```
Announce: "ℹ️ Reconciliation Skipped"
Announce: "   Reason: No original_story_id in test_reconciliation metadata"
END testing phase execution
```

Construct validation testing story ID:
```bash
VALIDATION_ID="-${ORIGINAL_STORY_ID}.t"
```

Agent: Store as VALIDATION_ID.

Verify validation story exists and get its status:
```bash
python "${SCRIPT_DIR}/queue_helpers.py" get-story \
  --story-id "${VALIDATION_ID}" --json
```

Agent: Store result as VALIDATION_STORY.

**IF VALIDATION_STORY is null or not found**:
```
Announce: "ℹ️ Reconciliation Skipped"
Announce: "   Reason: Validation story ${VALIDATION_ID} not found"
Announce: "   Validation may have been manually resolved or deleted"
END testing phase execution
```

Extract validation status:
```bash
VALIDATION_STATUS=$(echo "${VALIDATION_STORY}" | jq -r '.status')
```

**IF VALIDATION_STATUS != "blocked"**:
```
Announce: "ℹ️ Reconciliation Skipped"
Announce: "   Reason: Validation ${VALIDATION_ID} status is '${VALIDATION_STATUS}' (not blocked)"
Announce: "   Validation is not awaiting reconciliation"
END testing phase execution
```

```
Announce: "   Found blocked validation: ${VALIDATION_ID}"
Continue to STEP 14.3
```

---

#### STEP 14.3: Calculate Test Overlap

Load test results from both remediation and original validation:

```bash
# Remediation test results (this story)
REMEDIATION_RESULTS_FILE=".claude/sprint/test-results/${NEXT_STORY.story_id}-results.json"
REMEDIATION_RESULTS=$(cat "${REMEDIATION_RESULTS_FILE}")

# Original validation test results
VALIDATION_RESULTS_FILE=".claude/sprint/test-results/${ORIGINAL_STORY_ID}-results.json"

if [[ -f "${VALIDATION_RESULTS_FILE}" ]]; then
  VALIDATION_RESULTS=$(cat "${VALIDATION_RESULTS_FILE}")
else
  # No test results for original validation (new tests added by remediation)
  VALIDATION_RESULTS='{"summary": {"total": 0}, "test_files": []}'
fi
```

Extract test file lists and calculate overlap using Python:

```bash
OVERLAP_RESULT=$(python -c "
from resources.commands.sprint.queue_helpers.overlap import calculate_test_overlap
import json
import sys

remediation = json.loads('''${REMEDIATION_RESULTS}''')
original = json.loads('''${VALIDATION_RESULTS}''')

# Extract test file paths from results
remediation_files = remediation.get('test_files', [])
original_files = original.get('test_files', [])

# Calculate overlap
overlap_ratio = calculate_test_overlap(
    original_test_files=original_files,
    new_test_files=remediation_files
)

# Calculate metrics
matching_count = len(set(original_files) & set(remediation_files))
total_original = len(original_files)
missing_files = list(set(original_files) - set(remediation_files))

result = {
    'overlap_pct': round(overlap_ratio * 100, 1),
    'matching_tests': matching_count,
    'total_original_tests': total_original,
    'missing_tests': missing_files,
    'overlap_ratio': overlap_ratio
}

print(json.dumps(result))
")
```

Agent: Parse JSON output, store as OVERLAP_RESULT.

```
Announce: "   Test overlap: ${OVERLAP_RESULT.overlap_pct}% (${OVERLAP_RESULT.matching_tests}/${OVERLAP_RESULT.total_original_tests} tests)"
```

---

#### STEP 14.4: Determine Reconciliation Mode

Use overlap ratio to determine mode:

```bash
RECONCILIATION_MODE=$(python -c "
from resources.commands.sprint.queue_helpers.overlap import determine_reconciliation_mode
import json
import sys

overlap_ratio = ${OVERLAP_RESULT.overlap_ratio}
mode = determine_reconciliation_mode(overlap_ratio)
print(mode)
")
```

Agent: Store as RECONCILIATION_MODE (one of: 'propagate', 'retest', 'no_match').

**IF RECONCILIATION_MODE == 'no_match'**:
```
Announce: "ℹ️ Reconciliation Skipped"
Announce: "   Reason: Test overlap ${OVERLAP_RESULT.overlap_pct}% too low for reconciliation (< 50%)"
Announce: "   Validation ${VALIDATION_ID} remains blocked - manual intervention required"
END testing phase execution
```

---

#### STEP 14.5: Apply Reconciliation

Apply the determined reconciliation mode using Python functions:

**IF RECONCILIATION_MODE == 'propagate'**:

```bash
RECONCILIATION_RESULT=$(python -c "
from resources.commands.sprint.queue_helpers.reconciliation import apply_propagate_reconciliation
import json

result = apply_propagate_reconciliation(
    target_validation_id='${VALIDATION_ID}',
    source_remediation_id='${NEXT_STORY.story_id}',
    test_results=${REMEDIATION_RESULTS},
    sprint_dir='.claude/sprint'
)

print(json.dumps(result))
")
```

Agent: Parse JSON output, store as RECONCILIATION_RESULT.

---

**IF RECONCILIATION_MODE == 'retest'**:

Construct retest reason with overlap details:
```bash
RETEST_REASON="Test overlap ${OVERLAP_RESULT.overlap_pct}% (${OVERLAP_RESULT.matching_tests}/${OVERLAP_RESULT.total_original_tests} tests) - retest required (threshold: 95%)"
```

```bash
RECONCILIATION_RESULT=$(python -c "
from resources.commands.sprint.queue_helpers.reconciliation import apply_retest_reconciliation
import json

result = apply_retest_reconciliation(
    target_validation_id='${VALIDATION_ID}',
    source_remediation_id='${NEXT_STORY.story_id}',
    test_results=${REMEDIATION_RESULTS},
    retest_reason='${RETEST_REASON}',
    sprint_dir='.claude/sprint'
)

print(json.dumps(result))
")
```

Agent: Parse JSON output, store as RECONCILIATION_RESULT.

---

#### STEP 14.6: Announce Reconciliation Outcome

Parse reconciliation result:
```bash
RECONCILIATION_STATUS=$(echo "${RECONCILIATION_RESULT}" | jq -r '.status')
RECONCILIATION_MESSAGE=$(echo "${RECONCILIATION_RESULT}" | jq -r '.message')
UPDATED_STORIES=$(echo "${RECONCILIATION_RESULT}" | jq -r '.updated_stories | join(", ")')
```

**IF RECONCILIATION_STATUS == 'success' AND RECONCILIATION_MODE == 'propagate'**:

```
Announce: ""
Announce: "✅ Reconciliation: Propagated Results"
Announce: ""
Announce: "Remediation: ${NEXT_STORY.story_id} (${PARENT_ID})"
Announce: "Validation: ${VALIDATION_ID} → COMPLETED"
Announce: "Overlap: ${OVERLAP_RESULT.overlap_pct}% (${OVERLAP_RESULT.matching_tests}/${OVERLAP_RESULT.total_original_tests} tests)"
Announce: ""
Announce: "Result: Validation ${VALIDATION_ID} marked as completed"
Announce: "        Pass results propagated from ${NEXT_STORY.story_id}"
Announce: "        ${RECONCILIATION_MESSAGE}"
Announce: ""
Announce: "Updated stories: ${UPDATED_STORIES}"
Announce: ""
Announce: "Next: Run /sprint:NEXT to continue sprint execution"
```

---

**IF RECONCILIATION_STATUS == 'success' AND RECONCILIATION_MODE == 'retest'**:

```
Announce: ""
Announce: "⚠️ Reconciliation: Retest Required"
Announce: ""
Announce: "Remediation: ${NEXT_STORY.story_id} (${PARENT_ID})"
Announce: "Validation: ${VALIDATION_ID} → UNBLOCKED (needs retest)"
Announce: "Overlap: ${OVERLAP_RESULT.overlap_pct}% (${OVERLAP_RESULT.matching_tests}/${OVERLAP_RESULT.total_original_tests} tests)"
Announce: ""
```

**IF OVERLAP_RESULT.missing_tests is not empty**:
```bash
MISSING_TESTS=$(echo "${OVERLAP_RESULT}" | jq -r '.missing_tests | join(", ")')
```

```
Announce: "Missing tests: ${MISSING_TESTS}"
Announce: ""
```

```
Announce: "Result: Validation ${VALIDATION_ID} unblocked and ready for execution"
Announce: "        Retest required due to insufficient overlap (< 95%)"
Announce: "        ${RECONCILIATION_MESSAGE}"
Announce: ""
Announce: "Next: Run /sprint:NEXT --story ${VALIDATION_ID} to execute validation tests"
```

---

**IF RECONCILIATION_STATUS == 'error'**:

```bash
RECONCILIATION_ERROR=$(echo "${RECONCILIATION_RESULT}" | jq -r '.error')
```

```
Announce: ""
Announce: "❌ Reconciliation Failed"
Announce: ""
Announce: "Error: ${RECONCILIATION_ERROR}"
Announce: "Target: ${VALIDATION_ID}"
Announce: "Source: ${NEXT_STORY.story_id}"
Announce: ""
Announce: "Manual intervention required."
Announce: "Check queue state: /sprint:QUEUE"
```

---

**IF RECONCILIATION_STATUS == 'skipped'**:

```bash
SKIP_REASON=$(echo "${RECONCILIATION_RESULT}" | jq -r '.reason')
```

```
Announce: ""
Announce: "ℹ️ Reconciliation Skipped"
Announce: ""
Announce: "Reason: ${SKIP_REASON}"
Announce: "Validation: ${VALIDATION_ID}"
Announce: "Remediation: ${NEXT_STORY.story_id}"
Announce: ""
Announce: "No action taken."
```

---

## Completion

Agent: Testing phase execution complete. Return to NEXT command for final commit and workflow.

**Exit Status**:
- Success: THRESHOLD_MET == 1 (tests passed, story completed)
- Failure: THRESHOLD_MET == 0 (tests failed, story blocked)
- Reconciliation: Applied when remediation.t passes and validation blocked

---

## Error Handling

**IF test file discovery fails**:
- Announce error with pattern used
- Suggest adding test files or updating pattern
- HALT execution

**IF test execution fails (non-zero exit code)**:
- Capture error output
- Mark story as blocked
- Create advisory with error details
- Do NOT trigger reconciliation

**IF reconciliation fails**:
- Log error details
- Announce failure to user
- Validation remains in blocked state
- Manual intervention required

---

## Rules

✅ **ALWAYS check if remediation story before triggering reconciliation** (STEP 14.1)
✅ **ALWAYS require passing tests for reconciliation** (THRESHOLD_MET == 1)
✅ **ALWAYS verify validation exists and is blocked** (STEP 14.2)
✅ **ALWAYS calculate test overlap before determining mode** (STEP 14.3-14.4)
✅ **ALWAYS use Python functions for reconciliation** (not bash logic)
✅ **ALWAYS announce reconciliation outcome clearly** (propagate vs retest vs error)
✅ **ALWAYS handle reconciliation errors gracefully** (no silent failures)
❌ **NEVER trigger reconciliation for non-remediation stories**
❌ **NEVER propagate results if tests failed** (THRESHOLD_MET == 0)
❌ **NEVER skip validation discovery** (must verify blocked state)
❌ **NEVER apply reconciliation without overlap calculation**

---

## Token Efficiency

**Typical execution** (successful tests, no reconciliation):
- STEP 1-13: ~2,000-3,000t
- No reconciliation: ~0t
- **Total**: ~2,000-3,000t

**With reconciliation** (remediation story):
- STEP 1-13: ~2,000-3,000t
- STEP 14 (reconciliation trigger): ~1,500-2,500t
- **Total**: ~3,500-5,500t

**Key Optimizations**:
- Early exit for non-remediation stories (saves ~2,000t)
- Skip reconciliation if tests failed (saves ~2,000t)
- Python function invocation (saves ~500t vs bash logic)
- Conditional execution (only when needed)

---

## Version Notes

**v1.0.0** (Story 6 Implementation):
- Initial implementation with 14-step workflow
- STEP 14: Reconciliation trigger for remediation stories
- Propagate and retest modes supported
- Supersede mode not implemented (requires user intervention)
- Integration with overlap.py and reconciliation.py functions
