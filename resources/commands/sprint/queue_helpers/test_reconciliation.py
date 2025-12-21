"""
Test reconciliation schema definitions and validation.

Defines metadata schemas for remediation and validation stories that track
test reconciliation workflows. Provides validation functions for schema compliance.

Schemas:
- test_reconciliation: Metadata for remediation stories linking to test failures
- reconciliation: Metadata for validation stories tracking test reconciliation

Version: 1.0.0
"""

from typing import Any, Optional, TypedDict


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

class TestReconciliationMetadata(TypedDict, total=False):
    """
    Metadata schema for remediation stories created from test failures.

    Required fields:
    - failed_test_id: ID of the test that failed (e.g., test-8.t-001)
    - test_file: Path to test file relative to project root
    - failure_summary: Brief summary of test failure
    - original_story_id: ID of story that introduced the failing test

    Optional fields:
    - reconciliation_status: Status of test reconciliation
    """
    failed_test_id: str
    test_file: str
    failure_summary: str
    original_story_id: str
    reconciliation_status: str  # "pending" | "fixed" | "superseded" | "deferred"


class ReconciliationMetadata(TypedDict, total=False):
    """
    Metadata schema for validation stories tracking test reconciliation.

    Required fields:
    - remediation_count: Number of remediation stories created for this validation

    Optional fields:
    - resolved_count: Number of remediation stories resolved
    - pending_tests: List of test IDs still pending reconciliation
    """
    remediation_count: int
    resolved_count: int
    pending_tests: list[str]


# ============================================================================
# SCHEMA VALIDATION
# ============================================================================

def validate_test_reconciliation(metadata: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate test_reconciliation metadata schema.

    Args:
        metadata: Metadata dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_test_reconciliation({
        ...     "failed_test_id": "test-8.t-001",
        ...     "test_file": "tests/test_auth.py",
        ...     "failure_summary": "Auth timeout",
        ...     "original_story_id": "8"
        ... })
        (True, None)

        >>> validate_test_reconciliation({"failed_test_id": "test-001"})
        (False, "Missing required field: test_file")
    """
    # Check required fields
    required_fields = ["failed_test_id", "test_file", "failure_summary", "original_story_id"]

    for field in required_fields:
        if field not in metadata:
            return False, f"Missing required field: {field}"

        # Type check: all required fields must be strings
        if not isinstance(metadata[field], str):
            return False, f"Field {field} must be a string, got {type(metadata[field]).__name__}"

    # Validate optional reconciliation_status enum
    if "reconciliation_status" in metadata:
        status = metadata["reconciliation_status"]
        if not isinstance(status, str):
            return False, f"reconciliation_status must be a string, got {type(status).__name__}"

        valid_statuses = ["pending", "fixed", "superseded", "deferred"]
        if status not in valid_statuses:
            return False, f"reconciliation_status must be one of {valid_statuses}, got '{status}'"

    return True, None


def validate_reconciliation(metadata: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate reconciliation metadata schema.

    Args:
        metadata: Metadata dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_reconciliation({"remediation_count": 3})
        (True, None)

        >>> validate_reconciliation({
        ...     "remediation_count": 3,
        ...     "resolved_count": 2,
        ...     "pending_tests": ["test-8.t-001"]
        ... })
        (True, None)

        >>> validate_reconciliation({"resolved_count": 2})
        (False, "Missing required field: remediation_count")

        >>> validate_reconciliation({"remediation_count": "3"})
        (False, "Field remediation_count must be an integer")
    """
    # Check required fields
    if "remediation_count" not in metadata:
        return False, "Missing required field: remediation_count"

    # Type check: remediation_count must be integer
    if not isinstance(metadata["remediation_count"], int):
        return False, "Field remediation_count must be an integer"

    # Validate value: remediation_count must be non-negative
    if metadata["remediation_count"] < 0:
        return False, "Field remediation_count must be non-negative"

    # Validate optional resolved_count
    if "resolved_count" in metadata:
        resolved = metadata["resolved_count"]

        if not isinstance(resolved, int):
            return False, "Field resolved_count must be an integer"

        if resolved < 0:
            return False, "Field resolved_count must be non-negative"

        # resolved_count should not exceed remediation_count
        if resolved > metadata["remediation_count"]:
            return False, "Field resolved_count cannot exceed remediation_count"

    # Validate optional pending_tests
    if "pending_tests" in metadata:
        pending = metadata["pending_tests"]

        if not isinstance(pending, list):
            return False, "Field pending_tests must be a list"

        # All elements must be strings
        for i, test_id in enumerate(pending):
            if not isinstance(test_id, str):
                return False, f"pending_tests[{i}] must be a string, got {type(test_id).__name__}"

    return True, None


def get_default_test_reconciliation() -> dict[str, Any]:
    """
    Get default test_reconciliation metadata structure.

    Returns:
        Dictionary with reconciliation_status set to "pending"

    Example:
        >>> meta = get_default_test_reconciliation()
        >>> meta["reconciliation_status"]
        "pending"
    """
    return {
        "reconciliation_status": "pending"
    }


def get_default_reconciliation() -> dict[str, Any]:
    """
    Get default reconciliation metadata structure.

    Returns:
        Dictionary with resolved_count=0 and empty pending_tests list

    Example:
        >>> meta = get_default_reconciliation()
        >>> meta["resolved_count"]
        0
        >>> meta["pending_tests"]
        []
    """
    return {
        "resolved_count": 0,
        "pending_tests": []
    }


# ============================================================================
# SCHEMA INFORMATION
# ============================================================================

def get_schema_info(schema_name: str) -> Optional[dict[str, Any]]:
    """
    Get schema information for a given schema name.

    Args:
        schema_name: Name of schema ("test_reconciliation" or "reconciliation")

    Returns:
        Schema info dict or None if schema not found

    Example:
        >>> info = get_schema_info("test_reconciliation")
        >>> info["description"]
        "Metadata for remediation stories linking to test failures"
        >>> len(info["fields"])
        5
    """
    if schema_name == "test_reconciliation":
        return {
            "name": "test_reconciliation",
            "description": "Metadata for remediation stories linking to test failures",
            "fields": {
                "failed_test_id": {
                    "type": "string",
                    "required": True,
                    "description": "ID of the test that failed (e.g., test-8.t-001)"
                },
                "test_file": {
                    "type": "string",
                    "required": True,
                    "description": "Path to test file relative to project root"
                },
                "failure_summary": {
                    "type": "string",
                    "required": True,
                    "description": "Brief summary of test failure"
                },
                "original_story_id": {
                    "type": "string",
                    "required": True,
                    "description": "ID of story that introduced the failing test"
                },
                "reconciliation_status": {
                    "type": "string",
                    "required": False,
                    "enum": ["pending", "fixed", "superseded", "deferred"],
                    "default": "pending",
                    "description": "Status of test reconciliation"
                }
            }
        }
    elif schema_name == "reconciliation":
        return {
            "name": "reconciliation",
            "description": "Metadata for validation stories tracking test reconciliation",
            "fields": {
                "remediation_count": {
                    "type": "integer",
                    "required": True,
                    "description": "Number of remediation stories created for this validation"
                },
                "resolved_count": {
                    "type": "integer",
                    "required": False,
                    "default": 0,
                    "description": "Number of remediation stories resolved"
                },
                "pending_tests": {
                    "type": "array of strings",
                    "required": False,
                    "default": [],
                    "description": "List of test IDs still pending reconciliation"
                }
            }
        }
    return None
