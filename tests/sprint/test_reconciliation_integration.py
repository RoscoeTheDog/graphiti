"""
Integration tests for test_reconciliation schema integration with queue_helpers.py.

Tests the set-metadata command integration and queue operations with
test_reconciliation and reconciliation metadata.

Version: 1.0.0
Created for: Story 1.t (Testing: Metadata Schema Extension)
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

# This file tests integration with the global queue_helpers.py command
# It creates a temporary sprint directory and validates metadata operations


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_sprint_dir(tmp_path):
    """Create a temporary sprint directory with a minimal queue."""
    sprint_dir = tmp_path / ".claude" / "sprint"
    sprint_dir.mkdir(parents=True)

    # Create minimal queue.json
    queue_data = {
        "version": "4.0.0",
        "sprint": {
            "id": "test-sprint",
            "name": "Test Sprint",
            "version": "1.0.0",
            "status": "active",
            "branch": "test",
            "created": "2025-12-20",
            "queue_version": "2.0.0",
            "queue_strategy": "interleaved"
        },
        "stories": {
            "1": {
                "type": "feature",
                "story_type": "feature",
                "title": "Test Feature",
                "status": "unassigned",
                "parent": None,
                "children": [],
                "phase_status": {},
                "blocks": [],
                "file": "stories/1-test-feature.md",
                "advisories": []
            },
            "R1": {
                "type": "remediation",
                "story_type": "remediation",
                "title": "Test Remediation",
                "status": "unassigned",
                "parent": "1",
                "children": [],
                "blocks": [],
                "file": "stories/R1-test-remediation.md",
                "metadata": {}
            },
            "V1": {
                "type": "validation",
                "story_type": "validation",
                "title": "Test Validation",
                "status": "unassigned",
                "parent": None,
                "children": [],
                "blocks": [],
                "file": "stories/V1-test-validation.md",
                "metadata": {}
            }
        },
        "execution_queue": ["1"]
    }

    queue_file = sprint_dir / ".queue.json"
    queue_file.write_text(json.dumps(queue_data, indent=2))

    return sprint_dir


@pytest.fixture
def queue_helpers_script():
    """Get path to queue_helpers.py script."""
    global_resources = Path.home() / ".claude" / "resources" / "commands" / "sprint"
    script = global_resources / "queue_helpers.py"

    if not script.exists():
        pytest.skip(f"queue_helpers.py not found at {script}")

    return script


# ============================================================================
# SET-METADATA INTEGRATION TESTS
# ============================================================================

class TestSetMetadataIntegration:
    """Integration tests for set-metadata command with new schemas."""

    def test_set_metadata_test_reconciliation_valid(self, temp_sprint_dir, queue_helpers_script):
        """AC-1.3: set-metadata accepts valid test_reconciliation schema."""
        metadata = json.dumps({
            "failed_test_id": "test-8.t-001",
            "test_file": "tests/test_auth.py",
            "failure_summary": "Authentication timeout",
            "original_story_id": "8"
        })

        result = subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "set-metadata",
                "--story-id", "R1",
                "--key", "test_reconciliation",
                "--value", metadata
            ],
            capture_output=True,
            text=True
        )

        # Command should succeed
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify metadata was set
        output = json.loads(result.stdout)
        assert output["success"] is True

    def test_set_metadata_reconciliation_valid(self, temp_sprint_dir, queue_helpers_script):
        """AC-1.3: set-metadata accepts valid reconciliation schema."""
        metadata = json.dumps({
            "remediation_count": 3,
            "resolved_count": 1,
            "pending_tests": ["test-8.t-001", "test-8.t-002"]
        })

        result = subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "set-metadata",
                "--story-id", "V1",
                "--key", "reconciliation",
                "--value", metadata
            ],
            capture_output=True,
            text=True
        )

        # Command should succeed
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify metadata was set
        output = json.loads(result.stdout)
        assert output["success"] is True

    def test_set_metadata_test_reconciliation_invalid(self, temp_sprint_dir, queue_helpers_script):
        """AC-1.3: set-metadata rejects invalid test_reconciliation schema."""
        # Missing required field: test_file
        metadata = json.dumps({
            "failed_test_id": "test-8.t-001",
            "failure_summary": "Test failed",
            "original_story_id": "8"
        })

        result = subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "set-metadata",
                "--story-id", "R1",
                "--key", "test_reconciliation",
                "--value", metadata
            ],
            capture_output=True,
            text=True
        )

        # Command should fail with validation error
        assert result.returncode != 0
        assert "Missing required field" in result.stderr or "validation" in result.stderr.lower()

    def test_set_metadata_reconciliation_invalid(self, temp_sprint_dir, queue_helpers_script):
        """AC-1.3: set-metadata rejects invalid reconciliation schema."""
        # remediation_count is string instead of int
        metadata = json.dumps({
            "remediation_count": "3"
        })

        result = subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "set-metadata",
                "--story-id", "V1",
                "--key", "reconciliation",
                "--value", metadata
            ],
            capture_output=True,
            text=True
        )

        # Command should fail with validation error
        assert result.returncode != 0
        assert "integer" in result.stderr or "validation" in result.stderr.lower()


# ============================================================================
# QUEUE OPERATIONS INTEGRATION TESTS
# ============================================================================

class TestQueueOperationsIntegration:
    """Integration tests for queue operations with new metadata."""

    def test_get_next_with_test_reconciliation_metadata(self, temp_sprint_dir, queue_helpers_script):
        """AC-1.4: get-next works with stories containing test_reconciliation metadata."""
        # First set the metadata
        metadata = json.dumps({
            "failed_test_id": "test-8.t-001",
            "test_file": "tests/test_auth.py",
            "failure_summary": "Test failed",
            "original_story_id": "8"
        })

        subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "set-metadata",
                "--story-id", "R1",
                "--key", "test_reconciliation",
                "--value", metadata
            ],
            capture_output=True,
            text=True
        )

        # Now call get-next
        result = subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "get-next"
            ],
            capture_output=True,
            text=True
        )

        # Should succeed and return a story
        assert result.returncode == 0, f"get-next failed: {result.stderr}"
        output = json.loads(result.stdout)
        assert "story_id" in output

    def test_update_status_with_reconciliation_metadata(self, temp_sprint_dir, queue_helpers_script):
        """AC-1.4: update-status works with stories containing reconciliation metadata."""
        # First set the metadata
        metadata = json.dumps({
            "remediation_count": 5,
            "resolved_count": 2,
            "pending_tests": ["test-8.t-001"]
        })

        subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "set-metadata",
                "--story-id", "V1",
                "--key", "reconciliation",
                "--value", metadata
            ],
            capture_output=True,
            text=True
        )

        # Now update status
        result = subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "update-status",
                "--story-id", "V1",
                "--status", "in_progress"
            ],
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0, f"update-status failed: {result.stderr}"
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["new_status"] == "in_progress"

    def test_backwards_compatibility_existing_stories(self, temp_sprint_dir, queue_helpers_script):
        """AC-1.4: Existing stories without metadata continue to work."""
        # Call get-next without any metadata set
        result = subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "get-next"
            ],
            capture_output=True,
            text=True
        )

        # Should succeed even without new metadata
        assert result.returncode == 0, f"get-next failed for story without metadata: {result.stderr}"

        # Update status for story without metadata
        result = subprocess.run(
            [
                sys.executable,
                str(queue_helpers_script),
                "--sprint-dir", str(temp_sprint_dir),
                "--json",
                "update-status",
                "--story-id", "1",
                "--status", "in_progress"
            ],
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0, f"update-status failed for story without metadata: {result.stderr}"
