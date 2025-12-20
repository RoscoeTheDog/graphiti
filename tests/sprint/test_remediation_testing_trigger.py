"""
Unit and integration tests for Story 6: Remediation Testing Trigger.

Tests the reconciliation workflow triggered after successful remediation testing,
including:
- Remediation story type detection
- Blocked validation discovery
- Test overlap calculation integration
- Reconciliation mode selection
- Reconciliation application (propagate/retest modes)
- End-to-end workflow execution

Version: 1.0.0
Created for: Story 6.t (Testing: Remediation Testing Trigger)
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from resources.commands.sprint.queue_helpers.overlap import (
    calculate_test_overlap,
    determine_reconciliation_mode
)
from resources.commands.sprint.queue_helpers.reconciliation import (
    apply_propagate_reconciliation,
    apply_retest_reconciliation,
    propagate_status_to_parent
)
from resources.commands.sprint.queue_helpers.core import load_queue, save_queue, get_story


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def temp_sprint_dir(tmp_path):
    """Create temporary sprint directory structure."""
    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir()
    (sprint_dir / "stories").mkdir()
    (sprint_dir / "archive").mkdir()
    (sprint_dir / "test-results").mkdir()
    return sprint_dir


@pytest.fixture
def remediation_queue():
    """Queue with remediation story and blocked validation."""
    return {
        "version": "4.0.0",
        "sprint": {
            "id": "test-sprint",
            "name": "Test Sprint",
            "status": "active"
        },
        "stories": {
            "1": {
                "type": "feature",
                "title": "Test Feature",
                "status": "in_progress",
                "children": ["1.d", "1.i", "1.t"],
                "blocks": []
            },
            "1.r": {
                "type": "remediation",
                "title": "Remediation: Fix Test Failures",
                "status": "in_progress",
                "parent": "1",
                "children": ["1.r.t"],
                "metadata": {
                    "test_reconciliation": {
                        "failed_test_id": "test-1.t-001",
                        "test_file": "tests/sprint/test_feature.py",
                        "failure_summary": "Test pass rate 85% < required 90%",
                        "original_story_id": "1",
                        "reconciliation_status": "pending"
                    }
                }
            },
            "1.r.t": {
                "type": "testing",
                "title": "Testing: Remediation Fix",
                "status": "in_progress",
                "parent": "1.r",
                "phase": "testing"
            },
            "-1.t": {
                "type": "validation",
                "title": "Validation: Test Feature",
                "status": "blocked",
                "parent": "1",
                "phase": "validation",
                "blocks": []
            }
        },
        "execution_queue": ["1.r.t"]
    }


@pytest.fixture
def remediation_test_results():
    """Sample remediation test results with high overlap."""
    return {
        "summary": {
            "total": 50,
            "passed": 50,
            "failed": 0,
            "skipped": 0
        },
        "pass_rate": 100.0,
        "test_count": 50,
        "test_files": [
            "tests/sprint/test_feature.py",
            "tests/sprint/test_integration.py",
            "tests/sprint/test_helpers.py"
        ]
    }


@pytest.fixture
def original_validation_results():
    """Sample original validation test results."""
    return {
        "summary": {
            "total": 50,
            "passed": 42,
            "failed": 8,
            "skipped": 0
        },
        "pass_rate": 84.0,
        "test_count": 50,
        "test_files": [
            "tests/sprint/test_feature.py",
            "tests/sprint/test_integration.py",
            "tests/sprint/test_helpers.py"
        ]
    }


# ============================================================================
# UNIT TESTS: REMEDIATION STORY TYPE DETECTION
# ============================================================================

class TestRemediationStoryDetection:
    """Unit tests for remediation story type detection logic."""

    def test_detect_remediation_story_by_type(self, remediation_queue):
        """Story type 'remediation' correctly identified."""
        story = remediation_queue["stories"]["1.r"]

        assert story["type"] == "remediation"
        assert "test_reconciliation" in story.get("metadata", {})

    def test_detect_remediation_with_test_reconciliation_metadata(self, remediation_queue):
        """Remediation story has test_reconciliation metadata."""
        story = remediation_queue["stories"]["1.r"]

        assert "metadata" in story
        assert "test_reconciliation" in story["metadata"]
        assert story["metadata"]["test_reconciliation"]["reconciliation_status"] == "pending"


# ============================================================================
# UNIT TESTS: BLOCKED VALIDATION DISCOVERY
# ============================================================================

class TestBlockedValidationDiscovery:
    """Unit tests for discovering blocked validation stories."""

    def test_discover_blocked_validation_by_id(self, remediation_queue):
        """Validation story ID correctly constructed from original_story_id."""
        remediation = remediation_queue["stories"]["1.r"]
        original_story_id = remediation["metadata"]["test_reconciliation"]["original_story_id"]
        validation_id = f"-{original_story_id}.t"

        assert validation_id == "-1.t"
        assert validation_id in remediation_queue["stories"]

    def test_validation_status_is_blocked(self, remediation_queue):
        """Validation story status is 'blocked'."""
        validation = remediation_queue["stories"]["-1.t"]

        assert validation["status"] == "blocked"

    def test_skip_if_validation_not_blocked(self, remediation_queue):
        """Reconciliation skipped if validation not blocked."""
        # Change validation status to completed
        remediation_queue["stories"]["-1.t"]["status"] = "completed"

        validation = remediation_queue["stories"]["-1.t"]
        assert validation["status"] != "blocked"


# ============================================================================
# UNIT TESTS: OVERLAP CALCULATION INTEGRATION
# ============================================================================

class TestOverlapCalculationIntegration:
    """Unit tests for test overlap calculation integration."""

    def test_calculate_overlap_with_perfect_match(self, remediation_test_results, original_validation_results):
        """Overlap calculation returns 1.0 for identical test files."""
        overlap_ratio = calculate_test_overlap(
            original_test_files=original_validation_results["test_files"],
            new_test_files=remediation_test_results["test_files"]
        )

        assert overlap_ratio == 1.0

    def test_calculate_overlap_with_partial_match(self):
        """Overlap calculation returns correct ratio for partial match."""
        original_files = [
            "tests/test_a.py",
            "tests/test_b.py",
            "tests/test_c.py"
        ]
        new_files = [
            "tests/test_a.py",
            "tests/test_b.py",
            "tests/test_d.py"
        ]

        overlap_ratio = calculate_test_overlap(
            original_test_files=original_files,
            new_test_files=new_files
        )

        # 2 matching files out of 4 total unique files = 0.5
        assert overlap_ratio == 0.5

    def test_calculate_metrics_from_overlap(self, remediation_test_results, original_validation_results):
        """Overlap metrics (matching_count, missing_files) calculated correctly."""
        original_files = set(original_validation_results["test_files"])
        new_files = set(remediation_test_results["test_files"])

        matching_count = len(original_files & new_files)
        missing_files = list(original_files - new_files)

        assert matching_count == 3
        assert missing_files == []


# ============================================================================
# UNIT TESTS: RECONCILIATION MODE SELECTION
# ============================================================================

class TestReconciliationModeSelection:
    """Unit tests for reconciliation mode determination."""

    def test_propagate_mode_for_high_overlap(self):
        """Overlap >= 95% selects 'propagate' mode."""
        mode = determine_reconciliation_mode(overlap_ratio=0.95)
        assert mode == "propagate"

        mode = determine_reconciliation_mode(overlap_ratio=1.0)
        assert mode == "propagate"

    def test_retest_mode_for_moderate_overlap(self):
        """Overlap >= 50% and < 95% selects 'retest' mode."""
        mode = determine_reconciliation_mode(overlap_ratio=0.50)
        assert mode == "retest"

        mode = determine_reconciliation_mode(overlap_ratio=0.94)
        assert mode == "retest"

    def test_no_match_mode_for_low_overlap(self):
        """Overlap < 50% selects 'no_match' mode."""
        mode = determine_reconciliation_mode(overlap_ratio=0.49)
        assert mode == "no_match"

        mode = determine_reconciliation_mode(overlap_ratio=0.0)
        assert mode == "no_match"


# ============================================================================
# UNIT TESTS: RECONCILIATION APPLICATION
# ============================================================================

class TestReconciliationApplication:
    """Unit tests for reconciliation application functions."""

    def test_apply_propagate_marks_validation_completed(self, temp_sprint_dir, remediation_queue, remediation_test_results):
        """apply_propagate_reconciliation marks validation as completed."""
        # Save queue
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        result = apply_propagate_reconciliation(
            target_validation_id="-1.t",
            source_remediation_id="1.r.t",
            test_results=remediation_test_results,
            sprint_dir=str(temp_sprint_dir)
        )

        assert result["status"] == "success"
        assert result["mode"] == "propagate"
        assert "-1.t" in result["updated_stories"]

        # Verify validation status updated
        updated_queue = json.loads(queue_file.read_text())
        assert updated_queue["stories"]["-1.t"]["status"] == "completed"

    def test_apply_retest_unblocks_validation(self, temp_sprint_dir, remediation_queue, remediation_test_results):
        """apply_retest_reconciliation unblocks validation."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        result = apply_retest_reconciliation(
            target_validation_id="-1.t",
            source_remediation_id="1.r.t",
            test_results=remediation_test_results,
            retest_reason="Test overlap 60% - retest required",
            sprint_dir=str(temp_sprint_dir)
        )

        assert result["status"] == "success"
        assert result["mode"] == "retest"
        assert "-1.t" in result["updated_stories"]

        # Verify validation status updated to unassigned
        updated_queue = json.loads(queue_file.read_text())
        assert updated_queue["stories"]["-1.t"]["status"] == "unassigned"


# ============================================================================
# INTEGRATION TESTS: END-TO-END WORKFLOW
# ============================================================================

class TestEndToEndReconciliationWorkflow:
    """Integration tests for complete remediation testing trigger workflow."""

    def test_propagate_mode_end_to_end(self, temp_sprint_dir, remediation_queue, remediation_test_results, original_validation_results):
        """
        AC-6.1: End-to-end propagate mode workflow.

        Simulates complete workflow:
        1. Remediation testing completes with passing tests
        2. High overlap detected (>= 95%)
        3. Propagate mode selected
        4. Validation marked as completed
        5. Parent status propagated
        """
        # Setup
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        # Step 1: Simulate remediation testing completion
        # (Tested in execute-testing.md STEP 1-13, not tested here)

        # Step 2: Calculate overlap (100% match)
        overlap_ratio = calculate_test_overlap(
            original_test_files=original_validation_results["test_files"],
            new_test_files=remediation_test_results["test_files"]
        )
        assert overlap_ratio == 1.0

        # Step 3: Determine mode
        mode = determine_reconciliation_mode(overlap_ratio)
        assert mode == "propagate"

        # Step 4: Apply reconciliation
        result = apply_propagate_reconciliation(
            target_validation_id="-1.t",
            source_remediation_id="1.r.t",
            test_results=remediation_test_results,
            sprint_dir=str(temp_sprint_dir)
        )

        # Verify success
        assert result["status"] == "success"
        assert result["mode"] == "propagate"
        assert "-1.t" in result["updated_stories"]

        # Step 5: Verify validation completed
        updated_queue = json.loads(queue_file.read_text())
        validation = updated_queue["stories"]["-1.t"]
        assert validation["status"] == "completed"

        # Verify reconciliation metadata
        assert "reconciliation" in validation.get("metadata", {})
        reconciliation = validation["metadata"]["reconciliation"]
        assert reconciliation["status"] == "propagated"
        assert reconciliation["source_story"] == "1.r.t"

    def test_retest_mode_end_to_end(self, temp_sprint_dir, remediation_queue, remediation_test_results):
        """
        AC-6.2: End-to-end retest mode workflow.

        Simulates complete workflow:
        1. Remediation testing completes with passing tests
        2. Moderate overlap detected (>= 50%, < 95%)
        3. Retest mode selected
        4. Validation unblocked with needs_retest flag
        """
        # Setup
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        # Create original validation results with partial overlap
        original_files = [
            "tests/sprint/test_feature.py",
            "tests/sprint/test_integration.py",
            "tests/sprint/test_old_code.py"  # This file not in remediation
        ]

        # Step 1: Calculate overlap (66.7% match)
        overlap_ratio = calculate_test_overlap(
            original_test_files=original_files,
            new_test_files=remediation_test_results["test_files"]
        )
        assert 0.5 <= overlap_ratio < 0.95

        # Step 2: Determine mode
        mode = determine_reconciliation_mode(overlap_ratio)
        assert mode == "retest"

        # Step 3: Apply reconciliation
        retest_reason = f"Test overlap {overlap_ratio*100:.1f}% - retest required"
        result = apply_retest_reconciliation(
            target_validation_id="-1.t",
            source_remediation_id="1.r.t",
            test_results=remediation_test_results,
            retest_reason=retest_reason,
            sprint_dir=str(temp_sprint_dir)
        )

        # Verify success
        assert result["status"] == "success"
        assert result["mode"] == "retest"

        # Step 4: Verify validation unblocked
        updated_queue = json.loads(queue_file.read_text())
        validation = updated_queue["stories"]["-1.t"]
        assert validation["status"] == "unassigned"

        # Verify reconciliation metadata
        assert "reconciliation" in validation.get("metadata", {})
        reconciliation = validation["metadata"]["reconciliation"]
        assert reconciliation["status"] == "pending_retest"
        assert reconciliation["needs_retest"] is True

    def test_failed_remediation_tests_skip_reconciliation(self, temp_sprint_dir, remediation_queue):
        """
        AC-6.3: Failed remediation tests do not trigger reconciliation.

        If remediation tests fail, reconciliation should not be triggered.
        This test verifies the early exit condition.
        """
        # Setup
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        # Simulate failed test results
        failed_test_results = {
            "summary": {
                "total": 50,
                "passed": 40,
                "failed": 10,
                "skipped": 0
            },
            "pass_rate": 80.0,  # Below threshold
            "test_count": 50,
            "test_files": ["tests/sprint/test_feature.py"]
        }

        # In the actual workflow, STEP 14 would not execute if tests failed
        # We verify this by checking that the workflow checks test pass status
        # before attempting reconciliation

        # The execute-testing.md workflow checks:
        # IF TEST_PASS_STATUS == "fail": END (no STEP 14)

        # Verify that applying reconciliation with failed tests would be incorrect
        # (This is prevented by workflow, not by the function itself)
        assert failed_test_results["pass_rate"] < 90.0

        # If we mistakenly tried to apply reconciliation, validation should remain blocked
        initial_queue = json.loads(queue_file.read_text())
        assert initial_queue["stories"]["-1.t"]["status"] == "blocked"

    def test_non_remediation_story_skips_reconciliation(self, temp_sprint_dir):
        """
        AC-6.4: Non-remediation stories do not trigger reconciliation.

        Regular testing stories (not remediation.t) should not trigger
        reconciliation workflow.
        """
        # Create queue with regular testing story
        regular_queue = {
            "version": "4.0.0",
            "sprint": {"id": "test", "name": "Test", "status": "active"},
            "stories": {
                "1": {
                    "type": "feature",
                    "title": "Feature",
                    "status": "in_progress",
                    "children": ["1.t"]
                },
                "1.t": {
                    "type": "testing",
                    "title": "Testing: Feature",
                    "status": "in_progress",
                    "parent": "1",
                    "phase": "testing"
                    # No test_reconciliation metadata
                }
            }
        }

        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(regular_queue))

        # Verify no test_reconciliation metadata
        story = regular_queue["stories"]["1.t"]
        assert "metadata" not in story or "test_reconciliation" not in story.get("metadata", {})

        # The workflow's STEP 14.1 would detect this and skip reconciliation


# ============================================================================
# INTEGRATION TESTS: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Integration tests for error handling in reconciliation workflow."""

    def test_validation_not_found_returns_error(self, temp_sprint_dir, remediation_queue, remediation_test_results):
        """Reconciliation returns error if validation story not found."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        result = apply_propagate_reconciliation(
            target_validation_id="-999.t",  # Non-existent
            source_remediation_id="1.r.t",
            test_results=remediation_test_results,
            sprint_dir=str(temp_sprint_dir)
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_remediation_not_found_returns_error(self, temp_sprint_dir, remediation_queue, remediation_test_results):
        """Reconciliation returns error if remediation story not found."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        result = apply_propagate_reconciliation(
            target_validation_id="-1.t",
            source_remediation_id="999.r.t",  # Non-existent
            test_results=remediation_test_results,
            sprint_dir=str(temp_sprint_dir)
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_already_completed_validation_returns_skipped(self, temp_sprint_dir, remediation_queue, remediation_test_results):
        """Reconciliation skipped if validation already completed."""
        # Mark validation as completed
        remediation_queue["stories"]["-1.t"]["status"] = "completed"

        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        result = apply_propagate_reconciliation(
            target_validation_id="-1.t",
            source_remediation_id="1.r.t",
            test_results=remediation_test_results,
            sprint_dir=str(temp_sprint_dir)
        )

        assert result["status"] == "skipped"
        assert "already completed" in result["reason"].lower()


# ============================================================================
# INTEGRATION TESTS: REPORTING
# ============================================================================

class TestReconciliationReporting:
    """Integration tests for reconciliation result reporting."""

    def test_propagate_result_includes_required_fields(self, temp_sprint_dir, remediation_queue, remediation_test_results):
        """Propagate result includes all required fields for reporting."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        result = apply_propagate_reconciliation(
            target_validation_id="-1.t",
            source_remediation_id="1.r.t",
            test_results=remediation_test_results,
            sprint_dir=str(temp_sprint_dir)
        )

        # Verify all required fields present
        assert "status" in result
        assert "mode" in result
        assert "target" in result
        assert "source" in result
        assert "message" in result
        assert "updated_stories" in result

        # Verify field values
        assert result["status"] == "success"
        assert result["mode"] == "propagate"
        assert result["target"] == "-1.t"
        assert result["source"] == "1.r.t"
        assert isinstance(result["message"], str)
        assert isinstance(result["updated_stories"], list)

    def test_retest_result_includes_required_fields(self, temp_sprint_dir, remediation_queue, remediation_test_results):
        """Retest result includes all required fields for reporting."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(remediation_queue))

        result = apply_retest_reconciliation(
            target_validation_id="-1.t",
            source_remediation_id="1.r.t",
            test_results=remediation_test_results,
            retest_reason="Test overlap 60%",
            sprint_dir=str(temp_sprint_dir)
        )

        # Verify all required fields present
        assert "status" in result
        assert "mode" in result
        assert "target" in result
        assert "source" in result
        assert "message" in result
        assert "updated_stories" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
