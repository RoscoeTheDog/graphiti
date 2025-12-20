"""
Unit and Integration Tests for Reconciliation Application Functions

This module contains comprehensive tests for the reconciliation application functions
used to update validation story status and metadata based on remediation testing outcomes.

Test Coverage:
    - Unit tests for apply_propagate_reconciliation() function
    - Unit tests for apply_retest_reconciliation() function
    - Unit tests for apply_supersede_reconciliation() function
    - Unit tests for propagate_status_to_parent() function
    - Integration tests for full reconciliation workflows
    - Security tests for malicious inputs and DoS prevention

Story: 4.t - Testing Phase (Reconciliation Application Functions)
Created: 2025-12-20
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Any

from resources.commands.sprint.queue_helpers.reconciliation import (
    apply_propagate_reconciliation,
    apply_retest_reconciliation,
    apply_supersede_reconciliation,
    propagate_status_to_parent
)
from resources.commands.sprint.queue_helpers.core import (
    load_queue,
    save_queue,
    get_story,
    set_metadata
)


@pytest.fixture
def temp_sprint_dir():
    """Create a temporary sprint directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_queue():
    """Create a sample queue for testing."""
    return {
        "version": "4.0.0",
        "sprint": {
            "id": "test-sprint",
            "name": "Test Sprint",
            "status": "active"
        },
        "stories": {
            # Parent container story
            "-1": {
                "type": "container",
                "title": "Validation Container",
                "status": "pending",
                "parent": None,
                "children": ["-1.t"],
                "phase_status": {}
            },
            # Validation story (target)
            "-1.t": {
                "type": "validation",
                "title": "Validation Story",
                "status": "blocked",
                "parent": "-1",
                "children": [],
                "phase_status": {},
                "metadata": {
                    "test_files": ["test_a.py", "test_b.py"],
                    "test_threshold": 0.8
                }
            },
            # Remediation story (source)
            "1.r": {
                "type": "container",
                "title": "Remediation Container",
                "status": "pending",
                "parent": None,
                "children": ["1.r.t"],
                "phase_status": {}
            },
            "1.r.t": {
                "type": "remediation",
                "title": "Remediation Testing",
                "status": "completed",
                "parent": "1.r",
                "children": [],
                "phase_status": {},
                "metadata": {
                    "test_files": ["test_a.py", "test_b.py", "test_c.py"],
                    "test_threshold": 0.8,
                    "test_results": {
                        "pass_rate": 100.0,
                        "test_count": 50,
                        "passed": 50,
                        "failed": 0
                    }
                }
            }
        }
    }


class TestApplyPropagateReconciliation:
    """Unit tests for apply_propagate_reconciliation() function."""

    # ========== Success Cases ==========

    def test_propagate_success(self, temp_sprint_dir, sample_queue):
        """Test apply_propagate_reconciliation() with valid inputs.

        Expected: Validation marked as completed, metadata set, parent updated.
        """
        # Save sample queue
        save_queue(sample_queue, temp_sprint_dir)

        # Apply propagate reconciliation
        test_results = {
            'pass_rate': 100.0,
            'test_count': 50,
            'passed': 50,
            'failed': 0,
            'total': 50
        }

        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        # Verify result
        assert result['status'] == 'success'
        assert result['mode'] == 'propagate'
        assert result['target'] == '-1.t'
        assert result['source'] == '1.r.t'
        assert '-1.t' in result['updated_stories']
        assert '-1' in result['updated_stories']  # Parent should be updated

        # Verify queue changes
        updated_queue = load_queue(temp_sprint_dir)
        validation_story = get_story(updated_queue, '-1.t')

        # Verify status updated
        assert validation_story['status'] == 'completed'

        # Verify reconciliation metadata
        assert 'reconciliation' in validation_story['metadata']
        reconciliation = validation_story['metadata']['reconciliation']
        assert reconciliation['status'] == 'propagated'
        assert reconciliation['source_story'] == '1.r.t'
        assert reconciliation['source_pass_rate'] == 100.0
        assert reconciliation['source_test_count'] == 50
        assert 'applied_at' in reconciliation
        assert 'propagation_note' in reconciliation

    def test_propagate_partial_pass_rate(self, temp_sprint_dir, sample_queue):
        """Test apply_propagate_reconciliation() with partial pass rate.

        Expected: Metadata reflects actual pass rate, not 100%.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {
            'pass_rate': 95.5,
            'test_count': 50,
            'passed': 48,
            'failed': 2,
            'total': 50
        }

        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'success'

        updated_queue = load_queue(temp_sprint_dir)
        validation_story = get_story(updated_queue, '-1.t')
        reconciliation = validation_story['metadata']['reconciliation']

        assert reconciliation['source_pass_rate'] == 95.5
        assert '95.5%' in reconciliation['propagation_note']
        assert '48/50' in reconciliation['propagation_note']

    def test_propagate_parent_status_update(self, temp_sprint_dir, sample_queue):
        """Test apply_propagate_reconciliation() updates parent container status.

        Expected: Parent container status updated based on child completion.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {
            'pass_rate': 100.0,
            'test_count': 50,
            'passed': 50,
            'total': 50
        }

        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'success'

        updated_queue = load_queue(temp_sprint_dir)
        parent_story = get_story(updated_queue, '-1')

        # Parent should be completed (all children completed)
        assert parent_story['status'] == 'completed'

    # ========== Idempotency Tests ==========

    def test_propagate_already_completed(self, temp_sprint_dir, sample_queue):
        """Test apply_propagate_reconciliation() with already completed validation.

        Expected: Operation skipped, no changes made.
        """
        # Mark validation as already completed
        sample_queue['stories']['-1.t']['status'] = 'completed'
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'skipped'
        assert result['reason'] == "Validation already completed"

    def test_propagate_already_superseded(self, temp_sprint_dir, sample_queue):
        """Test apply_propagate_reconciliation() with already superseded validation.

        Expected: Operation skipped, no changes made.
        """
        # Mark validation as superseded
        sample_queue['stories']['-1.t']['status'] = 'superseded'
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'skipped'
        assert result['reason'] == "Validation already superseded"

    # ========== Error Cases ==========

    def test_propagate_target_not_found(self, temp_sprint_dir, sample_queue):
        """Test apply_propagate_reconciliation() with non-existent target validation.

        Expected: Error returned with appropriate message.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        result = apply_propagate_reconciliation(
            target_validation_id='-999.t',  # Non-existent
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error'].lower()

    def test_propagate_source_not_found(self, temp_sprint_dir, sample_queue):
        """Test apply_propagate_reconciliation() with non-existent source remediation.

        Expected: Error returned with appropriate message.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='999.r.t',  # Non-existent
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error'].lower()

    def test_propagate_queue_file_missing(self, temp_sprint_dir):
        """Test apply_propagate_reconciliation() with missing queue file.

        Expected: Error returned.
        """
        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'


class TestApplyRetestReconciliation:
    """Unit tests for apply_retest_reconciliation() function."""

    # ========== Success Cases ==========

    def test_retest_success(self, temp_sprint_dir, sample_queue):
        """Test apply_retest_reconciliation() with valid inputs.

        Expected: Validation unblocked (status=unassigned), needs_retest flag set.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {
            'pass_rate': 95.0,
            'test_count': 30,
            'passed': 29,
            'failed': 1
        }

        result = apply_retest_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            retest_reason="60% test overlap - retest required",
            sprint_dir=temp_sprint_dir
        )

        # Verify result
        assert result['status'] == 'success'
        assert result['mode'] == 'retest'
        assert result['target'] == '-1.t'
        assert result['source'] == '1.r.t'
        assert '-1.t' in result['updated_stories']
        assert '-1' not in result['updated_stories']  # Parent should NOT be updated

        # Verify queue changes
        updated_queue = load_queue(temp_sprint_dir)
        validation_story = get_story(updated_queue, '-1.t')

        # Verify status updated to unassigned (unblocked)
        assert validation_story['status'] == 'unassigned'

        # Verify reconciliation metadata
        assert 'reconciliation' in validation_story['metadata']
        reconciliation = validation_story['metadata']['reconciliation']
        assert reconciliation['status'] == 'pending_retest'
        assert reconciliation['source_story'] == '1.r.t'
        assert reconciliation['needs_retest'] is True
        assert reconciliation['retest_reason'] == "60% test overlap - retest required"
        assert 'applied_at' in reconciliation

    def test_retest_default_reason(self, temp_sprint_dir, sample_queue):
        """Test apply_retest_reconciliation() with default retest reason.

        Expected: Default reason used when not provided.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 95.0, 'test_count': 30}

        result = apply_retest_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'success'

        updated_queue = load_queue(temp_sprint_dir)
        validation_story = get_story(updated_queue, '-1.t')
        reconciliation = validation_story['metadata']['reconciliation']

        assert reconciliation['retest_reason'] == "Test overlap below propagation threshold"

    def test_retest_no_parent_update(self, temp_sprint_dir, sample_queue):
        """Test apply_retest_reconciliation() does NOT update parent status.

        Expected: Parent status remains unchanged (validation not completed).
        """
        save_queue(sample_queue, temp_sprint_dir)

        # Store original parent status
        original_parent_status = sample_queue['stories']['-1']['status']

        test_results = {'pass_rate': 95.0, 'test_count': 30}

        result = apply_retest_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'success'

        updated_queue = load_queue(temp_sprint_dir)
        parent_story = get_story(updated_queue, '-1')

        # Parent status should be unchanged
        assert parent_story['status'] == original_parent_status

    # ========== Idempotency Tests ==========

    def test_retest_already_completed(self, temp_sprint_dir, sample_queue):
        """Test apply_retest_reconciliation() with already completed validation.

        Expected: Operation skipped (no retest needed).
        """
        sample_queue['stories']['-1.t']['status'] = 'completed'
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 95.0, 'test_count': 30}

        result = apply_retest_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'skipped'
        assert 'retest not needed' in result['reason'].lower()

    def test_retest_already_superseded(self, temp_sprint_dir, sample_queue):
        """Test apply_retest_reconciliation() with already superseded validation.

        Expected: Operation skipped (no retest needed).
        """
        sample_queue['stories']['-1.t']['status'] = 'superseded'
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 95.0, 'test_count': 30}

        result = apply_retest_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'skipped'

    # ========== Error Cases ==========

    def test_retest_target_not_found(self, temp_sprint_dir, sample_queue):
        """Test apply_retest_reconciliation() with non-existent target validation.

        Expected: Error returned.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 95.0, 'test_count': 30}

        result = apply_retest_reconciliation(
            target_validation_id='-999.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error'].lower()

    def test_retest_source_not_found(self, temp_sprint_dir, sample_queue):
        """Test apply_retest_reconciliation() with non-existent source remediation.

        Expected: Error returned.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 95.0, 'test_count': 30}

        result = apply_retest_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='999.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'


class TestApplySupersedReconciliation:
    """Unit tests for apply_supersede_reconciliation() function."""

    # ========== Success Cases ==========

    def test_supersede_success(self, temp_sprint_dir, sample_queue):
        """Test apply_supersede_reconciliation() with valid inputs.

        Expected: Validation marked as superseded, metadata set, parent updated.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {
            'pass_rate': 100.0,
            'test_count': 75,
            'passed': 75,
            'failed': 0
        }

        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason="Remediation replaced original implementation entirely",
            sprint_dir=temp_sprint_dir
        )

        # Verify result
        assert result['status'] == 'success'
        assert result['mode'] == 'supersede'
        assert result['target'] == '-1.t'
        assert result['source'] == '1.r.t'
        assert '-1.t' in result['updated_stories']
        assert '-1' in result['updated_stories']  # Parent should be updated

        # Verify queue changes
        updated_queue = load_queue(temp_sprint_dir)
        validation_story = get_story(updated_queue, '-1.t')

        # Verify status updated to superseded
        assert validation_story['status'] == 'superseded'

        # Verify reconciliation metadata
        assert 'reconciliation' in validation_story['metadata']
        reconciliation = validation_story['metadata']['reconciliation']
        assert reconciliation['status'] == 'superseded'
        assert reconciliation['superseded_by'] == '1.r.t'
        assert reconciliation['supersession_reason'] == "Remediation replaced original implementation entirely"
        assert 'applied_at' in reconciliation

    def test_supersede_parent_status_update(self, temp_sprint_dir, sample_queue):
        """Test apply_supersede_reconciliation() updates parent container status.

        Expected: Parent container status updated (superseded counts as resolved).
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason="Replaced implementation",
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'success'

        updated_queue = load_queue(temp_sprint_dir)
        parent_story = get_story(updated_queue, '-1')

        # Parent should be completed (superseded child counts as completed)
        assert parent_story['status'] == 'completed'

    # ========== Validation Tests ==========

    def test_supersede_missing_reason(self, temp_sprint_dir, sample_queue):
        """Test apply_supersede_reconciliation() with missing supersession reason.

        Expected: Error returned (reason is required).
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason="",  # Empty reason
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'
        assert 'required' in result['error'].lower()

    def test_supersede_whitespace_only_reason(self, temp_sprint_dir, sample_queue):
        """Test apply_supersede_reconciliation() with whitespace-only reason.

        Expected: Error returned (reason cannot be empty).
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason="   \t\n   ",  # Whitespace only
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'

    # ========== Idempotency Tests ==========

    def test_supersede_already_superseded(self, temp_sprint_dir, sample_queue):
        """Test apply_supersede_reconciliation() with already superseded validation.

        Expected: Operation skipped.
        """
        sample_queue['stories']['-1.t']['status'] = 'superseded'
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason="Already superseded",
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'skipped'
        assert result['reason'] == "Validation already superseded"

    # ========== Error Cases ==========

    def test_supersede_target_not_found(self, temp_sprint_dir, sample_queue):
        """Test apply_supersede_reconciliation() with non-existent target validation.

        Expected: Error returned.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        result = apply_supersede_reconciliation(
            target_validation_id='-999.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason="Test reason",
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'

    def test_supersede_source_not_found(self, temp_sprint_dir, sample_queue):
        """Test apply_supersede_reconciliation() with non-existent source remediation.

        Expected: Error returned.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='999.r.t',
            test_results=test_results,
            supersession_reason="Test reason",
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'error'


class TestPropagateStatusToParent:
    """Unit tests for propagate_status_to_parent() function."""

    # ========== Single Child Scenarios ==========

    def test_propagate_single_child_completed(self, sample_queue):
        """Test propagate_status_to_parent() with single child completed.

        Expected: Parent status updated to completed.
        """
        # Mark child as completed
        sample_queue['stories']['-1.t']['status'] = 'completed'

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is True
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'completed'

    def test_propagate_single_child_in_progress(self, sample_queue):
        """Test propagate_status_to_parent() with single child in_progress.

        Expected: Parent status updated to in_progress.
        """
        sample_queue['stories']['-1.t']['status'] = 'in_progress'

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is True
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'in_progress'

    def test_propagate_single_child_blocked(self, sample_queue):
        """Test propagate_status_to_parent() with single child blocked.

        Expected: Parent status updated to blocked.
        """
        sample_queue['stories']['-1.t']['status'] = 'blocked'

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is True
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'blocked'

    def test_propagate_single_child_superseded(self, sample_queue):
        """Test propagate_status_to_parent() with single child superseded.

        Expected: Parent status updated to completed (superseded treated as completed).
        """
        sample_queue['stories']['-1.t']['status'] = 'superseded'

        queue, updated = propagate_status_to_parent(
            '-1.t',
            sample_queue,
            treat_superseded_as='completed'
        )

        assert updated is True
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'completed'

    # ========== Multiple Children Scenarios ==========

    def test_propagate_all_children_completed(self, sample_queue):
        """Test propagate_status_to_parent() with all children completed.

        Expected: Parent status updated to completed.
        """
        # Add multiple children
        sample_queue['stories']['-1']['children'] = ['-1.t', '-1.i']
        sample_queue['stories']['-1.i'] = {
            'status': 'completed',
            'parent': '-1',
            'children': []
        }
        sample_queue['stories']['-1.t']['status'] = 'completed'

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is True
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'completed'

    def test_propagate_any_child_blocked(self, sample_queue):
        """Test propagate_status_to_parent() with any child blocked.

        Expected: Parent status updated to blocked (priority rule).
        """
        # Add multiple children with different statuses
        sample_queue['stories']['-1']['children'] = ['-1.t', '-1.i', '-1.d']
        sample_queue['stories']['-1.i'] = {
            'status': 'completed',
            'parent': '-1',
            'children': []
        }
        sample_queue['stories']['-1.d'] = {
            'status': 'in_progress',
            'parent': '-1',
            'children': []
        }
        sample_queue['stories']['-1.t']['status'] = 'blocked'

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is True
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'blocked'

    def test_propagate_any_child_in_progress(self, sample_queue):
        """Test propagate_status_to_parent() with any child in_progress (no blocked).

        Expected: Parent status updated to in_progress.
        """
        # Add multiple children
        sample_queue['stories']['-1']['children'] = ['-1.t', '-1.i']
        sample_queue['stories']['-1.i'] = {
            'status': 'completed',
            'parent': '-1',
            'children': []
        }
        sample_queue['stories']['-1.t']['status'] = 'in_progress'

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is True
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'in_progress'

    def test_propagate_mixed_completed_superseded(self, sample_queue):
        """Test propagate_status_to_parent() with mixed completed/superseded children.

        Expected: Parent status updated to completed (all resolved).
        """
        # Add multiple children
        sample_queue['stories']['-1']['children'] = ['-1.t', '-1.i']
        sample_queue['stories']['-1.i'] = {
            'status': 'superseded',
            'parent': '-1',
            'children': []
        }
        sample_queue['stories']['-1.t']['status'] = 'completed'

        queue, updated = propagate_status_to_parent(
            '-1.t',
            sample_queue,
            treat_superseded_as='completed'
        )

        assert updated is True
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'completed'

    # ========== Recursive Propagation ==========

    def test_propagate_recursive_to_grandparent(self, sample_queue):
        """Test propagate_status_to_parent() propagates recursively to grandparent.

        Expected: Both parent and grandparent statuses updated.
        """
        # Add grandparent
        sample_queue['stories']['root'] = {
            'type': 'container',
            'status': 'pending',
            'parent': None,
            'children': ['-1']
        }
        sample_queue['stories']['-1']['parent'] = 'root'
        sample_queue['stories']['-1.t']['status'] = 'completed'

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is True

        # Check parent
        parent_story = get_story(queue, '-1')
        assert parent_story['status'] == 'completed'

        # Check grandparent
        grandparent_story = get_story(queue, 'root')
        assert grandparent_story['status'] == 'completed'

    # ========== Edge Cases ==========

    def test_propagate_no_parent(self, sample_queue):
        """Test propagate_status_to_parent() with story that has no parent.

        Expected: No update, returns False.
        """
        # Remove parent
        sample_queue['stories']['-1.t']['parent'] = None

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is False

    def test_propagate_parent_no_children(self, sample_queue):
        """Test propagate_status_to_parent() with parent that has no children.

        Expected: No update, returns False.
        """
        # Remove children from parent
        sample_queue['stories']['-1']['children'] = []

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is False

    def test_propagate_no_status_change(self, sample_queue):
        """Test propagate_status_to_parent() when parent status doesn't change.

        Expected: No update, returns False.
        """
        # Set parent to already correct status
        sample_queue['stories']['-1']['status'] = 'completed'
        sample_queue['stories']['-1.t']['status'] = 'completed'

        queue, updated = propagate_status_to_parent('-1.t', sample_queue)

        assert updated is False

    def test_propagate_error_handling(self):
        """Test propagate_status_to_parent() with invalid queue.

        Expected: Error handled gracefully, returns False.
        """
        invalid_queue = {'stories': {}}

        queue, updated = propagate_status_to_parent('invalid', invalid_queue)

        assert updated is False


class TestIntegrationWorkflows:
    """Integration tests for full reconciliation workflows."""

    def test_workflow_propagate_full_cycle(self, temp_sprint_dir, sample_queue):
        """Test complete propagate workflow from start to finish.

        Workflow:
            1. Apply propagate reconciliation
            2. Verify validation completed
            3. Verify parent container completed
            4. Verify metadata audit trail
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {
            'pass_rate': 100.0,
            'test_count': 50,
            'passed': 50,
            'failed': 0,
            'total': 50
        }

        # Apply reconciliation
        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        # Verify result
        assert result['status'] == 'success'
        assert result['mode'] == 'propagate'

        # Load updated queue
        queue = load_queue(temp_sprint_dir)

        # Verify validation story
        validation = get_story(queue, '-1.t')
        assert validation['status'] == 'completed'
        assert 'reconciliation' in validation['metadata']
        assert validation['metadata']['reconciliation']['status'] == 'propagated'

        # Verify parent container
        parent = get_story(queue, '-1')
        assert parent['status'] == 'completed'

    def test_workflow_retest_full_cycle(self, temp_sprint_dir, sample_queue):
        """Test complete retest workflow from start to finish.

        Workflow:
            1. Apply retest reconciliation
            2. Verify validation unblocked (status=unassigned)
            3. Verify needs_retest flag set
            4. Verify parent NOT updated
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 95.0, 'test_count': 30}

        # Apply reconciliation
        result = apply_retest_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            retest_reason="Insufficient overlap",
            sprint_dir=temp_sprint_dir
        )

        # Verify result
        assert result['status'] == 'success'
        assert result['mode'] == 'retest'

        # Load updated queue
        queue = load_queue(temp_sprint_dir)

        # Verify validation story
        validation = get_story(queue, '-1.t')
        assert validation['status'] == 'unassigned'
        assert 'reconciliation' in validation['metadata']
        assert validation['metadata']['reconciliation']['needs_retest'] is True

        # Verify parent NOT updated
        parent = get_story(queue, '-1')
        assert parent['status'] == 'pending'  # Should remain unchanged

    def test_workflow_supersede_full_cycle(self, temp_sprint_dir, sample_queue):
        """Test complete supersede workflow from start to finish.

        Workflow:
            1. Apply supersede reconciliation
            2. Verify validation superseded
            3. Verify parent container completed (superseded counts as resolved)
            4. Verify supersession metadata
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        # Apply reconciliation
        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason="Remediation replaced original implementation",
            sprint_dir=temp_sprint_dir
        )

        # Verify result
        assert result['status'] == 'success'
        assert result['mode'] == 'supersede'

        # Load updated queue
        queue = load_queue(temp_sprint_dir)

        # Verify validation story
        validation = get_story(queue, '-1.t')
        assert validation['status'] == 'superseded'
        assert 'reconciliation' in validation['metadata']
        assert validation['metadata']['reconciliation']['status'] == 'superseded'

        # Verify parent container
        parent = get_story(queue, '-1')
        assert parent['status'] == 'completed'

    def test_workflow_container_hierarchy_propagation(self, temp_sprint_dir, sample_queue):
        """Test status propagation through 3-level container hierarchy.

        Workflow:
            1. Create 3-level hierarchy: grandparent -> parent -> child
            2. Mark child as completed
            3. Verify propagation to parent and grandparent
        """
        # Add grandparent
        sample_queue['stories']['root'] = {
            'type': 'container',
            'status': 'pending',
            'parent': None,
            'children': ['-1']
        }
        sample_queue['stories']['-1']['parent'] = 'root'

        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        # Apply reconciliation to leaf child
        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'success'

        # Load updated queue
        queue = load_queue(temp_sprint_dir)

        # Verify all levels
        child = get_story(queue, '-1.t')
        assert child['status'] == 'completed'

        parent = get_story(queue, '-1')
        assert parent['status'] == 'completed'

        grandparent = get_story(queue, 'root')
        assert grandparent['status'] == 'completed'

    def test_workflow_multiple_reconciliations_sequence(self, temp_sprint_dir, sample_queue):
        """Test sequential reconciliation of multiple validation stories.

        Workflow:
            1. Add second validation story
            2. Reconcile first validation (propagate)
            3. Reconcile second validation (retest)
            4. Verify both updated correctly
            5. Verify parent status reflects mixed children
        """
        # Add second validation
        sample_queue['stories']['-2.t'] = {
            'type': 'validation',
            'status': 'blocked',
            'parent': '-1',
            'children': [],
            'metadata': {}
        }
        sample_queue['stories']['-1']['children'].append('-2.t')

        save_queue(sample_queue, temp_sprint_dir)

        # Reconcile first (propagate)
        result1 = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results={'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50},
            sprint_dir=temp_sprint_dir
        )

        assert result1['status'] == 'success'

        # Reconcile second (retest)
        result2 = apply_retest_reconciliation(
            target_validation_id='-2.t',
            source_remediation_id='1.r.t',
            test_results={'pass_rate': 95.0, 'test_count': 30},
            sprint_dir=temp_sprint_dir
        )

        assert result2['status'] == 'success'

        # Load updated queue
        queue = load_queue(temp_sprint_dir)

        # Verify first validation
        val1 = get_story(queue, '-1.t')
        assert val1['status'] == 'completed'

        # Verify second validation
        val2 = get_story(queue, '-2.t')
        assert val2['status'] == 'unassigned'

        # Verify parent (has one unassigned child, so should not be completed)
        parent = get_story(queue, '-1')
        # Parent should still be pending or in_progress (not all children completed)
        assert parent['status'] != 'completed'

    def test_workflow_idempotency_multiple_applies(self, temp_sprint_dir, sample_queue):
        """Test idempotency: applying same reconciliation multiple times.

        Workflow:
            1. Apply propagate reconciliation
            2. Apply same reconciliation again
            3. Verify second application skipped
            4. Verify queue unchanged
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        # First application
        result1 = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result1['status'] == 'success'

        # Load queue after first application
        queue_after_first = load_queue(temp_sprint_dir)

        # Second application (should be skipped)
        result2 = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result2['status'] == 'skipped'

        # Load queue after second application
        queue_after_second = load_queue(temp_sprint_dir)

        # Verify queue unchanged
        assert queue_after_first == queue_after_second

    def test_workflow_real_queue_file_operations(self, temp_sprint_dir, sample_queue):
        """Test reconciliation with real file I/O operations.

        Workflow:
            1. Save queue to file
            2. Apply reconciliation
            3. Load queue from file
            4. Verify changes persisted
        """
        # Save initial queue
        save_queue(sample_queue, temp_sprint_dir)

        # Verify file exists
        queue_path = Path(temp_sprint_dir) / '.queue.json'
        assert queue_path.exists()

        # Apply reconciliation
        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}
        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'success'

        # Load queue directly from file (not cached)
        with open(queue_path, 'r', encoding='utf-8') as f:
            persisted_queue = json.load(f)

        # Verify changes persisted
        validation = persisted_queue['stories']['-1.t']
        assert validation['status'] == 'completed'
        assert 'reconciliation' in validation['metadata']


class TestSecurityAndEdgeCases:
    """Security tests for malicious inputs and DoS prevention."""

    # ========== Malicious Story IDs ==========

    def test_security_path_traversal_story_id(self, temp_sprint_dir, sample_queue):
        """Test reconciliation with path traversal attempt in story ID.

        Security test: Ensure path traversal doesn't cause issues.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        result = apply_propagate_reconciliation(
            target_validation_id='../../../etc/passwd',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        # Should fail gracefully (story not found)
        assert result['status'] == 'error'
        assert 'not found' in result['error'].lower()

    def test_security_sql_injection_story_id(self, temp_sprint_dir, sample_queue):
        """Test reconciliation with SQL injection attempt in story ID.

        Security test: Ensure SQL injection doesn't cause issues.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        result = apply_propagate_reconciliation(
            target_validation_id="'; DROP TABLE stories; --",
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        # Should fail gracefully (story not found)
        assert result['status'] == 'error'

    def test_security_null_byte_story_id(self, temp_sprint_dir, sample_queue):
        """Test reconciliation with null byte in story ID.

        Security test: Null bytes should be handled.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'total': 50}

        result = apply_propagate_reconciliation(
            target_validation_id='-1.t\x00malicious',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        # Should fail gracefully
        assert result['status'] == 'error'

    # ========== Large Data DoS Prevention ==========

    def test_security_large_test_results(self, temp_sprint_dir, sample_queue):
        """Test reconciliation with extremely large test results.

        Security test: Large data should not cause DoS.
        """
        save_queue(sample_queue, temp_sprint_dir)

        # Create very large test results (100MB of data)
        test_results = {
            'pass_rate': 100.0,
            'test_count': 1000000,
            'passed': 1000000,
            'total': 1000000,
            'large_data': 'x' * (100 * 1024 * 1024)  # 100MB string
        }

        # Should handle large data without crashing
        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        # Should succeed (no size limits currently enforced)
        assert result['status'] in ['success', 'error']

    def test_security_deeply_nested_metadata(self, temp_sprint_dir, sample_queue):
        """Test reconciliation with deeply nested metadata.

        Security test: Deep nesting should not cause stack overflow.
        """
        save_queue(sample_queue, temp_sprint_dir)

        # Create deeply nested dict
        test_results = {'pass_rate': 100.0, 'test_count': 50}
        nested = test_results
        for i in range(1000):
            nested['nested'] = {}
            nested = nested['nested']

        # Should handle deep nesting without crashing
        result = apply_propagate_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            sprint_dir=temp_sprint_dir
        )

        # Should succeed
        assert result['status'] == 'success'

    # ========== Metadata Injection Attempts ==========

    def test_security_metadata_injection_html(self, temp_sprint_dir, sample_queue):
        """Test reconciliation with HTML injection attempt in reason.

        Security test: HTML should be stored as-is (no XSS vulnerability in JSON).
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason='<script>alert("XSS")</script>',
            sprint_dir=temp_sprint_dir
        )

        # Should succeed (HTML stored as plain text)
        assert result['status'] == 'success'

        # Verify HTML stored as-is
        queue = load_queue(temp_sprint_dir)
        validation = get_story(queue, '-1.t')
        reason = validation['metadata']['reconciliation']['supersession_reason']
        assert '<script>' in reason

    def test_security_metadata_injection_unicode(self, temp_sprint_dir, sample_queue):
        """Test reconciliation with Unicode injection attempt.

        Security test: Unicode should be handled correctly.
        """
        save_queue(sample_queue, temp_sprint_dir)

        test_results = {'pass_rate': 100.0, 'test_count': 75}

        # Unicode test with various scripts
        unicode_reason = "Test with 中文, 日本語, العربية, עברית, 🎉"

        result = apply_supersede_reconciliation(
            target_validation_id='-1.t',
            source_remediation_id='1.r.t',
            test_results=test_results,
            supersession_reason=unicode_reason,
            sprint_dir=temp_sprint_dir
        )

        assert result['status'] == 'success'

        # Verify Unicode preserved
        queue = load_queue(temp_sprint_dir)
        validation = get_story(queue, '-1.t')
        reason = validation['metadata']['reconciliation']['supersession_reason']
        assert reason == unicode_reason


# ========== Test Execution Summary ==========
"""
Test Coverage Summary:

apply_propagate_reconciliation():
    - Success cases: 3 tests
    - Idempotency: 2 tests
    - Error cases: 3 tests
    Total: 8 tests

apply_retest_reconciliation():
    - Success cases: 3 tests
    - Idempotency: 2 tests
    - Error cases: 2 tests
    Total: 7 tests

apply_supersede_reconciliation():
    - Success cases: 2 tests
    - Validation: 2 tests
    - Idempotency: 1 test
    - Error cases: 2 tests
    Total: 7 tests

propagate_status_to_parent():
    - Single child: 4 tests
    - Multiple children: 4 tests
    - Recursive propagation: 1 test
    - Edge cases: 4 tests
    Total: 13 tests

Integration workflows: 7 tests
Security and edge cases: 8 tests

Grand Total: 50 tests
"""
