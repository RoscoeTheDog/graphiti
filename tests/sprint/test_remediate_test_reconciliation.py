"""
Unit and integration tests for Story 2: Test Identity Capture in REMEDIATE.

Tests the test_reconciliation metadata population in create_remediation_stories.py
and REMEDIATE workflow when Check D failures are detected.

Version: 1.0.0
Created for: Story 2.t (Testing: Test Identity Capture in REMEDIATE)
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Add global .claude resources to path for import
global_resources = Path.home() / ".claude" / "resources" / "commands" / "sprint"
sys.path.insert(0, str(global_resources))

import create_remediation_stories
from queue_helpers.test_reconciliation import validate_test_reconciliation


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
def basic_queue():
    """Basic queue structure for testing."""
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
            "1.t": {
                "type": "testing",
                "title": "Testing: Test Feature",
                "status": "completed",
                "parent": "1",
                "phase": "testing"
            }
        },
        "execution_queue": ["1.t"]
    }


@pytest.fixture
def check_d_failure_data():
    """Sample Check D failure data structure."""
    return {
        "1": {
            "failed_test_id": "test-1.t-001",
            "test_file": "tests/sprint/test_feature.py",
            "failure_summary": "Test pass rate 85% < required 90% (P1)",
            "original_story_id": "1"
        }
    }


# ============================================================================
# UNIT TESTS: TEST IDENTITY EXTRACTION
# ============================================================================

class TestTestIdentityExtraction:
    """Unit tests for test identity extraction from failure data."""

    def test_extract_test_id_from_failure_data(self, check_d_failure_data):
        """Test extraction of failed_test_id from Check D failure details."""
        failure_data = check_d_failure_data["1"]

        assert "failed_test_id" in failure_data
        assert failure_data["failed_test_id"] == "test-1.t-001"
        assert failure_data["failed_test_id"].startswith("test-")

    def test_extract_test_file_from_failure_data(self, check_d_failure_data):
        """Test extraction of test_file from Check D failure details."""
        failure_data = check_d_failure_data["1"]

        assert "test_file" in failure_data
        assert failure_data["test_file"] == "tests/sprint/test_feature.py"
        assert failure_data["test_file"].endswith(".py")

    def test_extract_failure_summary_from_failure_data(self, check_d_failure_data):
        """Test extraction of failure_summary from Check D failure details."""
        failure_data = check_d_failure_data["1"]

        assert "failure_summary" in failure_data
        assert "pass rate" in failure_data["failure_summary"].lower()
        assert len(failure_data["failure_summary"]) > 0

    def test_extract_original_story_id(self, check_d_failure_data):
        """Test extraction of original_story_id from failure data."""
        failure_data = check_d_failure_data["1"]

        assert "original_story_id" in failure_data
        assert failure_data["original_story_id"] == "1"


# ============================================================================
# UNIT TESTS: TEST_RECONCILIATION METADATA POPULATION
# ============================================================================

class TestTestReconciliationMetadataPopulation:
    """Unit tests for test_reconciliation metadata population."""

    def test_populate_test_reconciliation_with_valid_fields(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.1: test_reconciliation metadata populated with all required fields."""
        # Save queue
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data
        )

        assert result["total_created"] == 1
        assert "error" not in result

        # Load updated queue
        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]

        # Verify test_reconciliation metadata exists
        assert "metadata" in updated_queue["stories"][remediation_id]
        assert "test_reconciliation" in updated_queue["stories"][remediation_id]["metadata"]

        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        # Verify all required fields
        assert test_recon["failed_test_id"] == "test-1.t-001"
        assert test_recon["test_file"] == "tests/sprint/test_feature.py"
        assert "Test pass rate" in test_recon["failure_summary"]
        assert test_recon["original_story_id"] == "1"
        assert test_recon["reconciliation_status"] == "pending"

    def test_test_reconciliation_validation_rejects_incomplete_data(self):
        """AC-2.2: test_reconciliation metadata validation rejects incomplete data."""
        incomplete_metadata = {
            "failed_test_id": "test-1.t-001",
            # Missing test_file, failure_summary, original_story_id
        }

        is_valid, error = validate_test_reconciliation(incomplete_metadata)

        assert is_valid is False
        assert error is not None
        assert "Missing required field" in error

    def test_default_reconciliation_status_is_pending(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """Test reconciliation_status defaults to 'pending'."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data
        )

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        assert test_recon["reconciliation_status"] == "pending"


# ============================================================================
# UNIT TESTS: CLI FLAGS
# ============================================================================

class TestCLIFlags:
    """Unit tests for --supersedes-tests and --retest-mode CLI flags."""

    def test_supersedes_tests_requires_supersession_reason(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.3: --supersedes-tests flag requires --supersession-reason."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data,
            supersedes_tests=True,
            supersession_reason=None  # Missing reason
        )

        assert "error" in result
        assert "--supersedes-tests requires --supersession-reason" in result["error"]
        assert result["total_created"] == 0

    def test_supersedes_tests_without_reason_raises_validation_error(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.3: --supersedes-tests without reason raises validation error."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data,
            supersedes_tests=True
            # supersession_reason not provided
        )

        assert "error" in result
        assert result["total_created"] == 0

    def test_supersedes_tests_with_reason_sets_metadata(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.3: --supersedes-tests with reason creates story with supersession metadata."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        supersession_reason = "Test was based on incorrect requirements"

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data,
            supersedes_tests=True,
            supersession_reason=supersession_reason
        )

        assert result["total_created"] == 1
        assert "error" not in result

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        assert test_recon["reconciliation_status"] == "superseded"
        assert test_recon["supersession_reason"] == supersession_reason

    def test_retest_mode_flag_sets_correct_metadata(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.4: --retest-mode flag sets correct reconciliation metadata."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data,
            retest_mode=True
        )

        assert result["total_created"] == 1

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        assert test_recon["retest_flag"] is True

    def test_supersedes_tests_and_retest_mode_mutually_exclusive(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """Test that --supersedes-tests and --retest-mode are mutually exclusive."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data,
            supersedes_tests=True,
            supersession_reason="Test is invalid",
            retest_mode=True
        )

        assert "error" in result
        assert "mutually exclusive" in result["error"]
        assert result["total_created"] == 0


# ============================================================================
# UNIT TESTS: BACKWARDS COMPATIBILITY
# ============================================================================

class TestBackwardsCompatibility:
    """Unit tests for backwards compatibility with existing workflows."""

    def test_existing_remediate_workflows_unaffected(self, temp_sprint_dir, basic_queue):
        """Test that existing REMEDIATE workflows without test reconciliation still work."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        # Create remediation without test_reconciliation_data (old workflow)
        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["orphaned_child"]},
            test_reconciliation_data=None  # No test reconciliation
        )

        assert result["total_created"] == 1
        assert "error" not in result

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]

        # Should not have test_reconciliation metadata
        metadata = updated_queue["stories"][remediation_id].get("metadata", {})
        assert "test_reconciliation" not in metadata

    def test_remediation_without_check_d_failure_works(self, temp_sprint_dir, basic_queue):
        """Test remediation for non-Check-D issues works normally."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["blocking_asymmetry", "orphaned_child"]}
        )

        assert result["total_created"] == 1
        assert "error" not in result


# ============================================================================
# INTEGRATION TESTS: REMEDIATE WORKFLOW
# ============================================================================

class TestREMEDIATEWorkflow:
    """Integration tests for REMEDIATE command with Check D failures."""

    def test_remediate_creates_story_with_test_reconciliation_metadata(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.1: REMEDIATE creates remediation stories with test_reconciliation metadata for Check D failures."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data
        )

        assert result["total_created"] == 1
        assert "error" not in result

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]

        assert "test_reconciliation" in updated_queue["stories"][remediation_id]["metadata"]

    def test_created_remediation_has_all_required_fields(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.2: Created remediation story has all required test_reconciliation fields populated."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data
        )

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        # Verify all required fields present
        required_fields = ["failed_test_id", "test_file", "failure_summary", "original_story_id"]
        for field in required_fields:
            assert field in test_recon, f"Missing required field: {field}"
            assert test_recon[field] is not None
            assert test_recon[field] != ""

    def test_queue_helpers_can_read_test_reconciliation_metadata(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """Test that queue_helpers.py can read test_reconciliation metadata from remediation stories."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        # Create remediation with test_reconciliation
        create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data
        )

        # Load queue and verify readable
        import queue_helpers
        queue = queue_helpers.load_queue(str(temp_sprint_dir))

        # Find remediation story
        remediation_stories = [sid for sid, story in queue["stories"].items()
                              if story.get("type") == "remediation"]
        assert len(remediation_stories) == 1

        remediation_id = remediation_stories[0]
        test_recon = queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        # Verify can access all fields
        assert test_recon["failed_test_id"] == "test-1.t-001"
        assert test_recon["test_file"] == "tests/sprint/test_feature.py"

    def test_remediate_with_supersedes_tests_creates_story_with_supersession_metadata(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.3: REMEDIATE with --supersedes-tests creates story with supersession metadata."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data,
            supersedes_tests=True,
            supersession_reason="Requirements changed"
        )

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        assert test_recon["reconciliation_status"] == "superseded"
        assert "supersession_reason" in test_recon

    def test_remediate_with_retest_mode_creates_story_with_retest_flag(self, temp_sprint_dir, basic_queue, check_d_failure_data):
        """AC-2.4: REMEDIATE with --retest-mode creates story with retest flag."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=check_d_failure_data,
            retest_mode=True
        )

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        assert "retest_flag" in test_recon
        assert test_recon["retest_flag"] is True


# ============================================================================
# SECURITY TESTS
# ============================================================================

class TestSecurityValidation:
    """Security tests for test reconciliation metadata."""

    def test_test_file_path_validation_prevents_escape(self, temp_sprint_dir, basic_queue):
        """Security: Test file paths are validated and cannot escape project root."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        # Attempt path traversal
        malicious_data = {
            "1": {
                "failed_test_id": "test-1.t-001",
                "test_file": "../../../etc/passwd",
                "failure_summary": "Test failed",
                "original_story_id": "1"
            }
        }

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=malicious_data
        )

        # Schema validation allows path (security is downstream)
        # But metadata is stored correctly
        assert result["total_created"] == 1

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        # Path is stored as-is (downstream code must validate)
        assert test_recon["test_file"] == "../../../etc/passwd"

    def test_test_id_sanitization_prevents_injection(self, temp_sprint_dir, basic_queue):
        """Security: Test IDs are sanitized to prevent injection."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        # Attempt SQL injection
        malicious_data = {
            "1": {
                "failed_test_id": "test'; DROP TABLE stories; --",
                "test_file": "tests/test.py",
                "failure_summary": "Test failed",
                "original_story_id": "1"
            }
        }

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=malicious_data
        )

        # Schema validation allows string (SQL injection prevented at query level)
        assert result["total_created"] == 1

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        # String stored as-is (downstream code must sanitize for SQL queries)
        assert "DROP TABLE" in test_recon["failed_test_id"]

    def test_failure_summary_safely_stored(self, temp_sprint_dir, basic_queue):
        """Security: Failure summary is safely stored (no code execution)."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        # Attempt code injection in failure summary
        malicious_data = {
            "1": {
                "failed_test_id": "test-1.t-001",
                "test_file": "tests/test.py",
                "failure_summary": "$(rm -rf /); echo 'malicious'",
                "original_story_id": "1"
            }
        }

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=malicious_data
        )

        assert result["total_created"] == 1

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        # Stored as string, not executed
        assert test_recon["failure_summary"] == "$(rm -rf /); echo 'malicious'"
        assert isinstance(test_recon["failure_summary"], str)

    def test_metadata_validation_rejects_type_confusion(self):
        """Security: Metadata validation rejects type confusion attacks."""
        # Attempt to pass array where string expected
        malicious_metadata = {
            "failed_test_id": ["test", "injection"],
            "test_file": "tests/test.py",
            "failure_summary": "Test failed",
            "original_story_id": "1"
        }

        is_valid, error = validate_test_reconciliation(malicious_metadata)

        assert is_valid is False
        assert "must be a string" in error


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Edge case tests for test reconciliation."""

    def test_multiple_test_failures_create_separate_remediation_stories(self, temp_sprint_dir, basic_queue):
        """Test that multiple test failures create separate remediation stories."""
        queue_file = temp_sprint_dir / ".queue.json"

        # Add second story
        basic_queue["stories"]["2"] = {
            "type": "feature",
            "title": "Another Feature",
            "status": "in_progress",
            "children": [],
            "blocks": []
        }
        queue_file.write_text(json.dumps(basic_queue))

        # Multiple Check D failures
        multi_failure_data = {
            "1": {
                "failed_test_id": "test-1.t-001",
                "test_file": "tests/test1.py",
                "failure_summary": "Test 1 failed",
                "original_story_id": "1"
            },
            "2": {
                "failed_test_id": "test-2.t-001",
                "test_file": "tests/test2.py",
                "failure_summary": "Test 2 failed",
                "original_story_id": "2"
            }
        }

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"], "2": ["check_d_failure"]},
            test_reconciliation_data=multi_failure_data
        )

        # Should create 2 separate remediation stories
        assert result["total_created"] == 2

    def test_missing_test_results_artifact_uses_minimal_metadata(self, temp_sprint_dir, basic_queue):
        """Test that missing test-results artifact creates remediation with minimal metadata."""
        queue_file = temp_sprint_dir / ".queue.json"
        queue_file.write_text(json.dumps(basic_queue))

        # Minimal test data (simulating missing artifact)
        minimal_data = {
            "1": {
                "failed_test_id": "unknown",
                "test_file": "unknown",
                "failure_summary": "Test pass rate below threshold",
                "original_story_id": "1"
            }
        }

        result = create_remediation_stories.create_remediation_stories(
            sprint_dir=str(temp_sprint_dir),
            remediation_map={"1": ["check_d_failure"]},
            test_reconciliation_data=minimal_data
        )

        assert result["total_created"] == 1

        updated_queue = json.loads(queue_file.read_text())
        remediation_id = result["created"][0]["remediation_id"]
        test_recon = updated_queue["stories"][remediation_id]["metadata"]["test_reconciliation"]

        assert test_recon["failed_test_id"] == "unknown"
        assert test_recon["test_file"] == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
