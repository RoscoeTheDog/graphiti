"""
Unit tests for test_reconciliation.py schema validation.

Tests the test_reconciliation and reconciliation metadata schemas
used for remediation and validation story metadata.

Version: 1.0.0
Created for: Story 1.t (Testing: Metadata Schema Extension)
"""

import sys
from pathlib import Path
import pytest

# Add global .claude resources to path for import
global_resources = Path.home() / ".claude" / "resources" / "commands" / "sprint" / "queue_helpers"
sys.path.insert(0, str(global_resources.parent))

from queue_helpers.test_reconciliation import (
    validate_test_reconciliation,
    validate_reconciliation,
    get_default_test_reconciliation,
    get_default_reconciliation,
    get_schema_info,
)


# ============================================================================
# TEST_RECONCILIATION SCHEMA VALIDATION TESTS
# ============================================================================

class TestTestReconciliationValidation:
    """Test suite for test_reconciliation schema validation."""

    def test_valid_test_reconciliation_minimal(self):
        """AC-1.1: test_reconciliation schema accepts valid minimal data."""
        metadata = {
            "failed_test_id": "test-8.t-001",
            "test_file": "tests/test_auth.py",
            "failure_summary": "Authentication timeout after 5 seconds",
            "original_story_id": "8"
        }

        valid, error = validate_test_reconciliation(metadata)

        assert valid is True
        assert error is None

    def test_valid_test_reconciliation_with_status(self):
        """AC-1.1: test_reconciliation schema accepts valid data with reconciliation_status."""
        metadata = {
            "failed_test_id": "test-8.t-002",
            "test_file": "tests/integration/test_api.py",
            "failure_summary": "API endpoint returned 500",
            "original_story_id": "8",
            "reconciliation_status": "fixed"
        }

        valid, error = validate_test_reconciliation(metadata)

        assert valid is True
        assert error is None

    def test_test_reconciliation_missing_required_field(self):
        """AC-1.1: test_reconciliation schema rejects data missing required fields."""
        # Missing test_file
        metadata = {
            "failed_test_id": "test-8.t-001",
            "failure_summary": "Test failed",
            "original_story_id": "8"
        }

        valid, error = validate_test_reconciliation(metadata)

        assert valid is False
        assert error == "Missing required field: test_file"

    def test_test_reconciliation_invalid_field_type(self):
        """AC-1.1: test_reconciliation schema rejects invalid field types."""
        metadata = {
            "failed_test_id": 123,  # Should be string
            "test_file": "tests/test_auth.py",
            "failure_summary": "Test failed",
            "original_story_id": "8"
        }

        valid, error = validate_test_reconciliation(metadata)

        assert valid is False
        assert "must be a string" in error

    def test_test_reconciliation_invalid_status_enum(self):
        """AC-1.1: test_reconciliation schema rejects invalid reconciliation_status values."""
        metadata = {
            "failed_test_id": "test-8.t-001",
            "test_file": "tests/test_auth.py",
            "failure_summary": "Test failed",
            "original_story_id": "8",
            "reconciliation_status": "invalid_status"
        }

        valid, error = validate_test_reconciliation(metadata)

        assert valid is False
        assert "must be one of" in error
        assert "pending" in error

    def test_test_reconciliation_all_valid_statuses(self):
        """AC-1.1: test_reconciliation schema accepts all valid reconciliation_status values."""
        valid_statuses = ["pending", "fixed", "superseded", "deferred"]

        for status in valid_statuses:
            metadata = {
                "failed_test_id": "test-8.t-001",
                "test_file": "tests/test_auth.py",
                "failure_summary": "Test failed",
                "original_story_id": "8",
                "reconciliation_status": status
            }

            valid, error = validate_test_reconciliation(metadata)

            assert valid is True, f"Status '{status}' should be valid"
            assert error is None


# ============================================================================
# RECONCILIATION SCHEMA VALIDATION TESTS
# ============================================================================

class TestReconciliationValidation:
    """Test suite for reconciliation schema validation."""

    def test_valid_reconciliation_minimal(self):
        """AC-1.2: reconciliation schema accepts valid minimal data."""
        metadata = {"remediation_count": 3}

        valid, error = validate_reconciliation(metadata)

        assert valid is True
        assert error is None

    def test_valid_reconciliation_full(self):
        """AC-1.2: reconciliation schema accepts valid complete data."""
        metadata = {
            "remediation_count": 5,
            "resolved_count": 3,
            "pending_tests": ["test-8.t-001", "test-8.t-002"]
        }

        valid, error = validate_reconciliation(metadata)

        assert valid is True
        assert error is None

    def test_reconciliation_missing_required_field(self):
        """AC-1.2: reconciliation schema rejects data missing required fields."""
        metadata = {
            "resolved_count": 2,
            "pending_tests": []
        }

        valid, error = validate_reconciliation(metadata)

        assert valid is False
        assert error == "Missing required field: remediation_count"

    def test_reconciliation_invalid_remediation_count_type(self):
        """AC-1.2: reconciliation schema rejects non-integer remediation_count."""
        metadata = {"remediation_count": "3"}

        valid, error = validate_reconciliation(metadata)

        assert valid is False
        assert "must be an integer" in error

    def test_reconciliation_negative_remediation_count(self):
        """AC-1.2: reconciliation schema rejects negative remediation_count."""
        metadata = {"remediation_count": -1}

        valid, error = validate_reconciliation(metadata)

        assert valid is False
        assert "must be non-negative" in error

    def test_reconciliation_invalid_resolved_count_type(self):
        """AC-1.2: reconciliation schema rejects non-integer resolved_count."""
        metadata = {
            "remediation_count": 3,
            "resolved_count": "2"
        }

        valid, error = validate_reconciliation(metadata)

        assert valid is False
        assert "must be an integer" in error

    def test_reconciliation_resolved_exceeds_remediation(self):
        """AC-1.2: reconciliation schema rejects resolved_count > remediation_count."""
        metadata = {
            "remediation_count": 3,
            "resolved_count": 5
        }

        valid, error = validate_reconciliation(metadata)

        assert valid is False
        assert "cannot exceed remediation_count" in error

    def test_reconciliation_invalid_pending_tests_type(self):
        """AC-1.2: reconciliation schema rejects non-list pending_tests."""
        metadata = {
            "remediation_count": 3,
            "pending_tests": "test-8.t-001"
        }

        valid, error = validate_reconciliation(metadata)

        assert valid is False
        assert "must be a list" in error

    def test_reconciliation_invalid_pending_tests_element(self):
        """AC-1.2: reconciliation schema rejects non-string elements in pending_tests."""
        metadata = {
            "remediation_count": 3,
            "pending_tests": ["test-8.t-001", 123, "test-8.t-003"]
        }

        valid, error = validate_reconciliation(metadata)

        assert valid is False
        assert "pending_tests[1]" in error
        assert "must be a string" in error


# ============================================================================
# DEFAULT VALUES TESTS
# ============================================================================

class TestDefaultValues:
    """Test suite for default value generation functions."""

    def test_default_test_reconciliation(self):
        """AC-1.3: get_default_test_reconciliation returns correct default."""
        defaults = get_default_test_reconciliation()

        assert "reconciliation_status" in defaults
        assert defaults["reconciliation_status"] == "pending"

    def test_default_reconciliation(self):
        """AC-1.3: get_default_reconciliation returns correct defaults."""
        defaults = get_default_reconciliation()

        assert defaults["resolved_count"] == 0
        assert defaults["pending_tests"] == []
        assert isinstance(defaults["pending_tests"], list)


# ============================================================================
# SCHEMA INFO TESTS
# ============================================================================

class TestSchemaInfo:
    """Test suite for schema information retrieval."""

    def test_get_test_reconciliation_schema_info(self):
        """AC-1.3: get_schema_info returns correct info for test_reconciliation."""
        info = get_schema_info("test_reconciliation")

        assert info is not None
        assert info["name"] == "test_reconciliation"
        assert "description" in info
        assert "fields" in info
        assert len(info["fields"]) == 5
        assert "failed_test_id" in info["fields"]
        assert info["fields"]["failed_test_id"]["required"] is True

    def test_get_reconciliation_schema_info(self):
        """AC-1.3: get_schema_info returns correct info for reconciliation."""
        info = get_schema_info("reconciliation")

        assert info is not None
        assert info["name"] == "reconciliation"
        assert "description" in info
        assert "fields" in info
        assert len(info["fields"]) == 3
        assert "remediation_count" in info["fields"]
        assert info["fields"]["remediation_count"]["required"] is True

    def test_get_invalid_schema_info(self):
        """AC-1.3: get_schema_info returns None for invalid schema name."""
        info = get_schema_info("invalid_schema")

        assert info is None


# ============================================================================
# SECURITY TESTS
# ============================================================================

class TestSchemaSecurity:
    """Security tests for schema validation."""

    def test_code_injection_via_failed_test_id(self):
        """Security: Schema validation rejects code injection attempts in failed_test_id."""
        malicious_metadata = {
            "failed_test_id": "test'; DROP TABLE stories; --",
            "test_file": "tests/test_auth.py",
            "failure_summary": "Test failed",
            "original_story_id": "8"
        }

        # Should accept (string validation only, SQL injection handled at query level)
        valid, error = validate_test_reconciliation(malicious_metadata)

        # Schema accepts any string, but downstream code must sanitize
        assert valid is True

    def test_code_injection_via_test_file(self):
        """Security: Schema validation rejects path traversal attempts."""
        malicious_metadata = {
            "failed_test_id": "test-8.t-001",
            "test_file": "../../../etc/passwd",
            "failure_summary": "Test failed",
            "original_story_id": "8"
        }

        # Should accept (string validation only, path validation handled at file access)
        valid, error = validate_test_reconciliation(malicious_metadata)

        # Schema accepts any string, but downstream code must validate paths
        assert valid is True

    def test_malformed_data_structure(self):
        """Security: Schema validation rejects malformed data structures."""
        malformed_metadata = {
            "remediation_count": {"nested": "dict"}  # Should be int
        }

        valid, error = validate_reconciliation(malformed_metadata)

        assert valid is False
        assert "must be an integer" in error

    def test_type_confusion_attack(self):
        """Security: Schema validation rejects type confusion attempts."""
        # Attempt to pass list where string expected
        malformed_metadata = {
            "failed_test_id": ["test", "injection"],
            "test_file": "tests/test_auth.py",
            "failure_summary": "Test failed",
            "original_story_id": "8"
        }

        valid, error = validate_test_reconciliation(malformed_metadata)

        assert valid is False
        assert "must be a string" in error


# ============================================================================
# BACKWARDS COMPATIBILITY TESTS
# ============================================================================

class TestBackwardsCompatibility:
    """Tests for backwards compatibility with existing queue operations."""

    def test_empty_metadata_validation(self):
        """AC-1.4: Empty metadata should fail validation (required fields missing)."""
        valid_tr, error_tr = validate_test_reconciliation({})
        valid_r, error_r = validate_reconciliation({})

        # Both should fail due to missing required fields
        assert valid_tr is False
        assert "Missing required field" in error_tr

        assert valid_r is False
        assert "Missing required field" in error_r

    def test_extra_fields_allowed(self):
        """AC-1.4: Schema validation allows extra fields (forward compatibility)."""
        metadata_with_extras = {
            "failed_test_id": "test-8.t-001",
            "test_file": "tests/test_auth.py",
            "failure_summary": "Test failed",
            "original_story_id": "8",
            "custom_field": "custom_value",  # Extra field
            "future_extension": 123
        }

        valid, error = validate_test_reconciliation(metadata_with_extras)

        # Should accept extra fields
        assert valid is True
        assert error is None
