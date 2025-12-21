"""
Reconciliation Application Functions

This module implements reconciliation application functions that update validation story
status and metadata based on remediation testing outcomes.

Functions:
    apply_propagate_reconciliation: Mark validation as completed by propagating results
    apply_retest_reconciliation: Unblock validation with needs_retest flag
    apply_supersede_reconciliation: Mark validation as superseded
    propagate_status_to_parent: Update parent container status based on children

Author: Sprint Remediation Test Reconciliation
Created: 2025-12-20
Story: 4 - Reconciliation Application Functions
"""

from typing import Any
from datetime import datetime
from pathlib import Path

from .core import (
    load_queue,
    save_queue,
    set_metadata,
    get_story,
    update_story_status
)


def apply_propagate_reconciliation(
    target_validation_id: str,
    source_remediation_id: str,
    test_results: dict[str, Any],
    sprint_dir: str = ".claude/sprint"
) -> dict[str, Any]:
    """
    Mark validation as completed by propagating remediation test results (no retest needed).

    Updates validation story status to 'completed' and sets reconciliation metadata with
    audit trail. Triggers container status propagation to parent.

    Args:
        target_validation_id: Validation story ID to update (e.g., '-1.t')
        source_remediation_id: Remediation story ID that provided passing results (e.g., '1.r.t')
        test_results: Test results from remediation (pass_rate, test_count, test_files, etc.)
        sprint_dir: Sprint directory path (default: .claude/sprint)

    Returns:
        Result object with:
            - status: 'success', 'error', or 'skipped'
            - mode: 'propagate'
            - target: target_validation_id
            - source: source_remediation_id
            - message: Human-readable message
            - updated_stories: List of updated story IDs

    Raises:
        ValueError: If target validation or source remediation not found

    Example:
        >>> result = apply_propagate_reconciliation(
        ...     target_validation_id='-1.t',
        ...     source_remediation_id='1.r.t',
        ...     test_results={'pass_rate': 100.0, 'test_count': 50, 'passed': 50, 'failed': 0}
        ... )
        >>> result['status']
        'success'
        >>> result['updated_stories']
        ['-1.t', '-1']
    """
    try:
        # Load queue
        queue = load_queue(sprint_dir)

        # Validate target validation exists
        if target_validation_id not in queue.get('stories', {}):
            raise ValueError(f"Target validation story not found: {target_validation_id}")

        # Validate source remediation exists
        if source_remediation_id not in queue.get('stories', {}):
            raise ValueError(f"Source remediation story not found: {source_remediation_id}")

        # Get target validation story
        target_story = get_story(queue, target_validation_id)

        # Check if already completed or superseded (idempotency check)
        if target_story.get('status') in ['completed', 'superseded']:
            return {
                'status': 'skipped',
                'reason': f"Validation already {target_story['status']}",
                'target': target_validation_id,
                'mode': 'propagate'
            }

        # Extract test result metrics
        pass_rate = test_results.get('pass_rate', 0.0)
        test_count = test_results.get('test_count', 0)
        passed = test_results.get('passed', 0)
        total = test_results.get('total', test_count)

        # Create reconciliation metadata
        reconciliation_metadata = {
            'status': 'propagated',
            'source_story': source_remediation_id,
            'source_pass_rate': pass_rate,
            'source_test_count': test_count,
            'remediation_count': 1,  # Single remediation story triggered this reconciliation
            'applied_at': datetime.utcnow().isoformat(),
            'propagation_note': (
                f"Pass propagated from {source_remediation_id} "
                f"({pass_rate:.1f}% pass rate, {passed}/{total} tests)"
            )
        }

        # Update story status to completed
        queue = update_story_status(queue, target_validation_id, 'completed')

        # Set reconciliation metadata
        queue = set_metadata(queue, target_validation_id, 'reconciliation', reconciliation_metadata)

        # Track updated stories
        updated_stories = [target_validation_id]

        # Propagate status to parent container
        queue, parent_updated = propagate_status_to_parent(
            child_story_id=target_validation_id,
            queue=queue,
            treat_superseded_as='completed'
        )

        if parent_updated:
            parent_id = target_story.get('parent')
            if parent_id:
                updated_stories.append(parent_id)

        # Save updated queue
        save_queue(queue, sprint_dir)

        # Return success result
        return {
            'status': 'success',
            'mode': 'propagate',
            'target': target_validation_id,
            'source': source_remediation_id,
            'message': (
                f"Propagated results from {source_remediation_id} to {target_validation_id} "
                f"({pass_rate:.1f}% pass rate)"
            ),
            'updated_stories': updated_stories
        }

    except Exception as e:
        # Return error result
        return {
            'status': 'error',
            'error': str(e),
            'target': target_validation_id,
            'mode': 'propagate'
        }


def apply_retest_reconciliation(
    target_validation_id: str,
    source_remediation_id: str,
    test_results: dict[str, Any],
    retest_reason: str = "Test overlap below propagation threshold",
    sprint_dir: str = ".claude/sprint"
) -> dict[str, Any]:
    """
    Unblock validation with needs_retest flag (test overlap insufficient for propagation).

    Updates validation story status to 'unassigned' (unblocked, ready for execution) and
    sets reconciliation metadata with needs_retest flag. Does NOT propagate to parent
    since validation still needs execution.

    Args:
        target_validation_id: Validation story ID to update (e.g., '-1.t')
        source_remediation_id: Remediation story ID that triggered retest (e.g., '1.r.t')
        test_results: Test results from remediation
        retest_reason: Reason why retest is required (default: overlap threshold)
        sprint_dir: Sprint directory path (default: .claude/sprint)

    Returns:
        Result object with:
            - status: 'success', 'error', or 'skipped'
            - mode: 'retest'
            - target: target_validation_id
            - source: source_remediation_id
            - message: Human-readable message
            - updated_stories: List of updated story IDs

    Raises:
        ValueError: If target validation or source remediation not found

    Example:
        >>> result = apply_retest_reconciliation(
        ...     target_validation_id='-1.t',
        ...     source_remediation_id='1.r.t',
        ...     test_results={'pass_rate': 95.0, 'test_count': 30},
        ...     retest_reason="60% test overlap - retest required"
        ... )
        >>> result['status']
        'success'
        >>> result['updated_stories']
        ['-1.t']
    """
    try:
        # Load queue
        queue = load_queue(sprint_dir)

        # Validate target validation exists
        if target_validation_id not in queue.get('stories', {}):
            raise ValueError(f"Target validation story not found: {target_validation_id}")

        # Validate source remediation exists
        if source_remediation_id not in queue.get('stories', {}):
            raise ValueError(f"Source remediation story not found: {source_remediation_id}")

        # Get target validation story
        target_story = get_story(queue, target_validation_id)

        # Check if already completed or superseded (skip retest in these cases)
        if target_story.get('status') in ['completed', 'superseded']:
            return {
                'status': 'skipped',
                'reason': f"Validation already {target_story['status']} - retest not needed",
                'target': target_validation_id,
                'mode': 'retest'
            }

        # Create reconciliation metadata
        reconciliation_metadata = {
            'status': 'pending_retest',
            'source_story': source_remediation_id,
            'needs_retest': True,
            'retest_reason': retest_reason,
            'remediation_count': 1,  # Single remediation story triggered this reconciliation
            'applied_at': datetime.utcnow().isoformat()
        }

        # Update story status to unassigned (unblocked, ready for execution)
        queue = update_story_status(queue, target_validation_id, 'unassigned')

        # Set reconciliation metadata
        queue = set_metadata(queue, target_validation_id, 'reconciliation', reconciliation_metadata)

        # Track updated stories (no parent propagation for retest mode)
        updated_stories = [target_validation_id]

        # Save updated queue
        save_queue(queue, sprint_dir)

        # Return success result
        return {
            'status': 'success',
            'mode': 'retest',
            'target': target_validation_id,
            'source': source_remediation_id,
            'message': (
                f"Unblocked {target_validation_id} for retest - {retest_reason}"
            ),
            'updated_stories': updated_stories
        }

    except Exception as e:
        # Return error result
        return {
            'status': 'error',
            'error': str(e),
            'target': target_validation_id,
            'mode': 'retest'
        }


def apply_supersede_reconciliation(
    target_validation_id: str,
    source_remediation_id: str,
    test_results: dict[str, Any],
    supersession_reason: str,
    sprint_dir: str = ".claude/sprint"
) -> dict[str, Any]:
    """
    Mark validation as superseded (original tests obsolete, replaced by remediation approach).

    Updates validation story status to 'superseded' and sets reconciliation metadata with
    supersession reason. Triggers container status propagation to parent (superseded counts
    as resolved).

    Args:
        target_validation_id: Validation story ID to mark as superseded (e.g., '-1.t')
        source_remediation_id: Remediation story ID that supersedes (e.g., '1.r.t')
        test_results: Test results from remediation
        supersession_reason: Reason why original tests are obsolete (required, user-provided)
        sprint_dir: Sprint directory path (default: .claude/sprint)

    Returns:
        Result object with:
            - status: 'success', 'error', or 'skipped'
            - mode: 'supersede'
            - target: target_validation_id
            - source: source_remediation_id
            - message: Human-readable message
            - updated_stories: List of updated story IDs

    Raises:
        ValueError: If target validation or source remediation not found, or reason not provided

    Example:
        >>> result = apply_supersede_reconciliation(
        ...     target_validation_id='-1.t',
        ...     source_remediation_id='1.r.t',
        ...     test_results={'pass_rate': 100.0, 'test_count': 75},
        ...     supersession_reason="Remediation replaced original implementation entirely"
        ... )
        >>> result['status']
        'success'
        >>> result['updated_stories']
        ['-1.t', '-1']
    """
    try:
        # Validate supersession reason is provided
        if not supersession_reason or not supersession_reason.strip():
            raise ValueError("supersession_reason is required and cannot be empty")

        # Load queue
        queue = load_queue(sprint_dir)

        # Validate target validation exists
        if target_validation_id not in queue.get('stories', {}):
            raise ValueError(f"Target validation story not found: {target_validation_id}")

        # Validate source remediation exists
        if source_remediation_id not in queue.get('stories', {}):
            raise ValueError(f"Source remediation story not found: {source_remediation_id}")

        # Get target validation story
        target_story = get_story(queue, target_validation_id)

        # Check if already superseded (idempotency check)
        if target_story.get('status') == 'superseded':
            return {
                'status': 'skipped',
                'reason': "Validation already superseded",
                'target': target_validation_id,
                'mode': 'supersede'
            }

        # Create reconciliation metadata
        reconciliation_metadata = {
            'status': 'superseded',
            'superseded_by': source_remediation_id,
            'supersession_reason': supersession_reason,
            'remediation_count': 1,  # Single remediation story supersedes this validation
            'applied_at': datetime.utcnow().isoformat()
        }

        # Update story status to superseded
        queue = update_story_status(queue, target_validation_id, 'superseded')

        # Set reconciliation metadata
        queue = set_metadata(queue, target_validation_id, 'reconciliation', reconciliation_metadata)

        # Track updated stories
        updated_stories = [target_validation_id]

        # Propagate status to parent container (superseded counts as resolved)
        queue, parent_updated = propagate_status_to_parent(
            child_story_id=target_validation_id,
            queue=queue,
            treat_superseded_as='completed'
        )

        if parent_updated:
            parent_id = target_story.get('parent')
            if parent_id:
                updated_stories.append(parent_id)

        # Save updated queue
        save_queue(queue, sprint_dir)

        # Return success result
        return {
            'status': 'success',
            'mode': 'supersede',
            'target': target_validation_id,
            'source': source_remediation_id,
            'message': (
                f"Superseded {target_validation_id} with {source_remediation_id} - "
                f"{supersession_reason}"
            ),
            'updated_stories': updated_stories
        }

    except Exception as e:
        # Return error result
        return {
            'status': 'error',
            'error': str(e),
            'target': target_validation_id,
            'mode': 'supersede'
        }


def propagate_status_to_parent(
    child_story_id: str,
    queue: dict[str, Any],
    treat_superseded_as: str = "completed"
) -> tuple[dict[str, Any], bool]:
    """
    Update parent container status based on child states.

    Implements recursive propagation up the container hierarchy. Parent status is
    updated based on aggregate child states using the following rules:
        - All children completed/superseded -> parent 'completed'
        - Any child blocked -> parent 'blocked'
        - Any child in_progress -> parent 'in_progress'
        - Otherwise -> parent status unchanged

    Args:
        child_story_id: Child story ID that changed
        queue: Queue dictionary
        treat_superseded_as: How to treat superseded status (default: 'completed')

    Returns:
        Tuple of (updated_queue, parent_was_updated)
            - updated_queue: Queue dictionary with updated parent status
            - parent_was_updated: True if parent status changed, False otherwise

    Example:
        >>> queue = load_queue()
        >>> queue, updated = propagate_status_to_parent('-1.t', queue)
        >>> updated
        True
    """
    try:
        # Get child story
        child_story = get_story(queue, child_story_id)

        # Get parent ID
        parent_id = child_story.get('parent')

        # If no parent, return queue unchanged
        if not parent_id:
            return queue, False

        # Get parent story
        parent_story = get_story(queue, parent_id)

        # Get all children of parent
        children_ids = parent_story.get('children', [])

        if not children_ids:
            return queue, False

        # Collect child statuses
        child_statuses = []
        for child_id in children_ids:
            child = queue['stories'].get(child_id)
            if child:
                status = child.get('status', 'pending')
                # Treat superseded as specified (default: completed)
                if status == 'superseded':
                    status = treat_superseded_as
                child_statuses.append(status)

        # Determine parent status based on children
        new_parent_status = None

        # Priority 1: Any child blocked -> parent blocked
        if 'blocked' in child_statuses:
            new_parent_status = 'blocked'

        # Priority 2: Any child in_progress -> parent in_progress
        elif 'in_progress' in child_statuses:
            new_parent_status = 'in_progress'

        # Priority 3: All children completed -> parent completed
        elif all(s == 'completed' for s in child_statuses):
            new_parent_status = 'completed'

        # Otherwise: Keep parent status unchanged
        else:
            new_parent_status = parent_story.get('status')

        # Check if parent status changed
        current_parent_status = parent_story.get('status')
        parent_changed = new_parent_status != current_parent_status

        if parent_changed:
            # Update parent status
            queue = update_story_status(queue, parent_id, new_parent_status)

            # Recursively propagate to grandparent
            queue, _ = propagate_status_to_parent(
                child_story_id=parent_id,
                queue=queue,
                treat_superseded_as=treat_superseded_as
            )

        return queue, parent_changed

    except Exception:
        # If propagation fails, return queue unchanged
        # This prevents propagation errors from breaking reconciliation
        return queue, False


# Module exports
__all__ = [
    'apply_propagate_reconciliation',
    'apply_retest_reconciliation',
    'apply_supersede_reconciliation',
    'propagate_status_to_parent'
]
