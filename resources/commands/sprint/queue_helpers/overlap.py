"""
Overlap Calculation Algorithm for Test Reconciliation

This module implements the overlap calculation algorithm to determine reconciliation
mode (propagate vs retest vs no_match) based on test file similarity between original
validation and new validation runs.

Functions:
    calculate_test_overlap: Calculate ratio of matching test files between two lists
    same_test_parameters: Compare test parameters between two validation runs
    determine_reconciliation_mode: Determine reconciliation mode based on overlap ratio

Author: Sprint Remediation Test Reconciliation
Created: 2025-12-20
Story: 3 - Overlap Calculation Algorithm
"""

from typing import Any, Optional
from pathlib import Path


def calculate_test_overlap(
    original_test_files: list[str],
    new_test_files: list[str]
) -> float:
    """
    Calculate ratio of matching test files between two test file lists.

    Uses set operations for efficient comparison (O(n) time complexity).
    Normalizes file paths to handle cross-platform differences.

    Args:
        original_test_files: List of test file paths from original validation run
        new_test_files: List of test file paths from new validation run

    Returns:
        Overlap ratio (0.0 to 1.0):
            - 1.0: Perfect match (identical test files)
            - 0.0: No overlap (completely different test files)
            - 0.5: 50% overlap

    Edge Cases:
        - Both lists empty: Returns 1.0 (perfect match, no tests to reconcile)
        - One list empty, other not: Returns 0.0 (no overlap)
        - Identical lists: Returns 1.0 (perfect match)
        - No common files: Returns 0.0 (no overlap)
        - Partial overlap: Returns calculated ratio

    Algorithm:
        1. Normalize file paths to handle platform differences
        2. Convert both lists to sets for efficient comparison
        3. Calculate intersection (matching files)
        4. Calculate union (all unique files)
        5. Return ratio: len(intersection) / len(union) if union not empty, else 1.0

    Examples:
        >>> calculate_test_overlap([], [])
        1.0
        >>> calculate_test_overlap(['test_a.py'], ['test_a.py'])
        1.0
        >>> calculate_test_overlap(['test_a.py'], ['test_b.py'])
        0.0
        >>> calculate_test_overlap(['test_a.py', 'test_b.py'], ['test_b.py', 'test_c.py'])
        0.3333333333333333
    """
    # Edge case: both lists empty (perfect match, no tests to reconcile)
    if not original_test_files and not new_test_files:
        return 1.0

    # Edge case: one list empty, other not (no overlap)
    if not original_test_files or not new_test_files:
        return 0.0

    # Normalize file paths for consistent comparison across platforms
    # Convert to Path objects and then to normalized strings
    # This handles forward/backslash differences and relative/absolute paths
    original_normalized = set()
    for file_path in original_test_files:
        try:
            # Normalize path (resolve to absolute, handle platform differences)
            normalized = Path(file_path).as_posix()  # Convert to forward slashes
            original_normalized.add(normalized)
        except (ValueError, OSError):
            # Invalid path - skip normalization, use as-is
            original_normalized.add(file_path)

    new_normalized = set()
    for file_path in new_test_files:
        try:
            normalized = Path(file_path).as_posix()
            new_normalized.add(normalized)
        except (ValueError, OSError):
            # Invalid path - skip normalization, use as-is
            new_normalized.add(file_path)

    # Calculate intersection (matching files)
    intersection = original_normalized & new_normalized

    # Calculate union (all unique files)
    union = original_normalized | new_normalized

    # Return ratio: len(intersection) / len(union)
    # Union is guaranteed to be non-empty at this point (checked edge cases above)
    if len(union) == 0:
        # This should never happen given our edge case checks, but handle it defensively
        return 1.0

    return len(intersection) / len(union)


def same_test_parameters(
    original_params: dict[str, Any],
    new_params: dict[str, Any]
) -> bool:
    """
    Compare test parameters between two validation runs.

    Compares critical test parameters to determine if test results can be
    safely propagated from the original validation to the new validation.

    Args:
        original_params: Test parameters from original validation run
        new_params: Test parameters from new validation run

    Returns:
        True if all critical parameters match, False otherwise

    Compared Parameters:
        - test_threshold: Minimum pass threshold for tests
        - test_command: Command used to run tests
        - test_timeout: Timeout for test execution
        - test_environment: Environment variables or configuration

    Algorithm:
        1. Compare each critical parameter for equality
        2. Missing parameters treated as None for comparison
        3. Return True only if ALL parameters match
        4. List/dict values compared order-independently

    Examples:
        >>> params1 = {'test_threshold': 0.8, 'test_command': 'pytest'}
        >>> params2 = {'test_threshold': 0.8, 'test_command': 'pytest'}
        >>> same_test_parameters(params1, params2)
        True

        >>> params3 = {'test_threshold': 0.8, 'test_command': 'pytest'}
        >>> params4 = {'test_threshold': 0.9, 'test_command': 'pytest'}
        >>> same_test_parameters(params3, params4)
        False

        >>> params5 = {'test_threshold': 0.8}
        >>> params6 = {'test_threshold': 0.8, 'test_command': None}
        >>> same_test_parameters(params5, params6)
        True
    """
    # Define critical parameters to compare
    critical_parameters = [
        'test_threshold',
        'test_command',
        'test_timeout',
        'test_environment'
    ]

    # Compare each critical parameter
    for param_name in critical_parameters:
        # Get values from both parameter dictionaries
        # Missing parameters treated as None
        original_value = original_params.get(param_name, None)
        new_value = new_params.get(param_name, None)

        # Compare values
        # For dict/list values, we need order-independent comparison
        if isinstance(original_value, dict) and isinstance(new_value, dict):
            # Compare dictionaries (order-independent by default in Python)
            if original_value != new_value:
                return False
        elif isinstance(original_value, list) and isinstance(new_value, list):
            # Compare lists order-independently using set comparison
            # This handles cases where parameter order shouldn't matter
            if set(original_value) != set(new_value):
                return False
        else:
            # Direct comparison for primitive types (int, float, str, None, etc.)
            if original_value != new_value:
                return False

    # All critical parameters match
    return True


def determine_reconciliation_mode(overlap_ratio: float) -> str:
    """
    Determine reconciliation mode based on overlap ratio.

    Uses threshold-based decision logic to determine whether to propagate
    results, rerun tests, or skip reconciliation entirely.

    Args:
        overlap_ratio: Overlap ratio from calculate_test_overlap() (0.0 to 1.0)

    Returns:
        Reconciliation mode:
            - 'propagate': Very high overlap (>= 0.95) - propagate results
            - 'retest': Moderate overlap (>= 0.50 and < 0.95) - rerun tests
            - 'no_match': Low overlap (< 0.50) - no reconciliation possible

    Thresholds:
        - >= 0.95: propagate mode (very high overlap)
            Rationale: >95% test file overlap indicates minimal changes,
            safe to propagate existing test results

        - >= 0.50 and < 0.95: retest mode (moderate overlap)
            Rationale: 50-95% overlap indicates significant changes,
            tests should be rerun to verify results

        - < 0.50: no_match mode (low overlap)
            Rationale: <50% overlap indicates major changes,
            reconciliation not meaningful

    Examples:
        >>> determine_reconciliation_mode(1.0)
        'propagate'
        >>> determine_reconciliation_mode(0.95)
        'propagate'
        >>> determine_reconciliation_mode(0.94)
        'retest'
        >>> determine_reconciliation_mode(0.50)
        'retest'
        >>> determine_reconciliation_mode(0.49)
        'no_match'
        >>> determine_reconciliation_mode(0.0)
        'no_match'
    """
    # Threshold-based decision logic
    if overlap_ratio >= 0.95:
        # Very high overlap - propagate results from original validation
        return 'propagate'
    elif overlap_ratio >= 0.50:
        # Moderate overlap - rerun tests to verify results
        return 'retest'
    else:
        # Low overlap - no reconciliation possible
        return 'no_match'


# Module exports
__all__ = [
    'calculate_test_overlap',
    'same_test_parameters',
    'determine_reconciliation_mode'
]
