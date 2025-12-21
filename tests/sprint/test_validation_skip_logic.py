"""
Unit and integration tests for validation skip logic.

Tests the should_skip_check_d() function and validate_test_pass_rates() CLI
that implements smart skip logic based on reconciliation metadata.

Version: 1.0.0
Created for: Story 8.t (Testing: Validation Engine Skip Logic)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

# Add global .claude resources to path for import
global_resources = Path.home() / ".claude" / "resources" / "commands" / "sprint"
sys.path.insert(0, str(global_resources))

from validate_test_pass_rates import (
    should_skip_check_d,
    validate_test_pass_rates,
    _log_skip_decision,
)


# ============================================================================
# UNIT TESTS - SKIP DECISION LOGIC
# ============================================================================

class TestSkipDecisionLogic:
    """Test suite for should_skip_check_d() skip decision logic."""

    def test_skip_propagated_status_no_retest(self):
        """AC-8.1: Skip Check D when status='propagated' and needs_retest=False."""
        story = {
            "id": "-8.t",
            "metadata": {
                "reconciliation": {
                    "status": "propagated",
                    "needs_retest": False,
                    "source_story": "8.i",
                    "source_pass_rate": 100.0,
                    "source_test_count": 12
                }
            }
        }

        should_skip, reason, mode = should_skip_check_d(story)

        assert should_skip is True
        assert "propagated" in reason.lower()
        assert "8.i" in reason
        assert "100.0" in reason
        assert mode == "propagated"

    def test_skip_propagated_with_full_metadata(self):
        """AC-8.1: Skip decision includes all reconciliation metadata in reason."""
        story = {
            "id": "-8.t",
            "metadata": {
                "reconciliation": {
                    "status": "propagated",
                    "needs_retest": False,
                    "source_story": "8.i",
                    "source_pass_rate": 95.5,
                    "source_test_count": 20
                }
            }
        }

        should_skip, reason, mode = should_skip_check_d(story)

        assert should_skip is True
        assert "8.i" in reason
        assert "95.5" in reason
        assert "20" in reason
        assert mode == "propagated"

    def test_skip_superseded_status(self):
        """AC-8.3: Skip Check D when status='superseded'."""
        story = {
            "id": "-8.t",
            "metadata": {
                "reconciliation": {
                    "status": "superseded",
                    "source_story": "8.i2",
                    "superseded_at": "2025-12-20T10:00:00Z"
                }
            }
        }

        should_skip, reason, mode = should_skip_check_d(story)

        assert should_skip is True
        assert "superseded" in reason.lower()
        assert "8.i2" in reason
        assert "2025-12-20T10:00:00Z" in reason
        assert mode == "superseded"

    def test_run_when_needs_retest_true(self):
        """AC-8.2: Run Check D when needs_retest=True."""
        story = {
            "id": "-8.t",
            "metadata": {
                "reconciliation": {
                    "status": "pending_retest",
                    "needs_retest": True,
                    "source_story": "8.i",
                    "retest_reason": "Implementation changed significantly"
                }
            }
        }

        should_skip, reason, mode = should_skip_check_d(story)

        assert should_skip is False
        assert "retest" in reason.lower()
        assert "8.i" in reason
        assert "Implementation changed significantly" in reason
        assert mode == "pending_retest"

    def test_run_when_no_reconciliation_metadata(self):
        """AC-8.2: Run Check D when no reconciliation metadata present."""
        story = {
            "id": "-8.t",
            "metadata": {}
        }

        should_skip, reason, mode = should_skip_check_d(story)

        assert should_skip is False
        assert "no reconciliation metadata" in reason.lower()
        assert mode is None

    def test_run_when_reconciliation_missing(self):
        """Run Check D when reconciliation key is missing entirely."""
        story = {
            "id": "-8.t"
        }

        should_skip, reason, mode = should_skip_check_d(story)

        assert should_skip is False
        assert "no reconciliation metadata" in reason.lower()
        assert mode is None

    def test_run_when_status_unknown(self):
        """Edge case: Run Check D when status is unknown (safe default)."""
        story = {
            "id": "-8.t",
            "metadata": {
                "reconciliation": {
                    "status": "unknown_status",
                    "needs_retest": False
                }
            }
        }

        should_skip, reason, mode = should_skip_check_d(story)

        assert should_skip is False
        assert "unknown" in reason.lower()
        assert "safe default" in reason.lower()
        assert mode is None

    def test_propagated_overridden_by_needs_retest(self):
        """Edge case: needs_retest=True overrides propagated status."""
        story = {
            "id": "-8.t",
            "metadata": {
                "reconciliation": {
                    "status": "propagated",
                    "needs_retest": True,
                    "source_story": "8.i",
                    "retest_reason": "New test coverage required"
                }
            }
        }

        should_skip, reason, mode = should_skip_check_d(story)

        # Should NOT skip - needs_retest takes precedence
        assert should_skip is False
        assert "retest" in reason.lower()
        assert mode == "pending_retest"


# ============================================================================
# UNIT TESTS - AUDIT TRAIL LOGGING
# ============================================================================

class TestAuditTrailLogging:
    """Test suite for _log_skip_decision() audit trail logging."""

    def test_creates_audit_log_new_file(self, tmp_path):
        """AC-8.4: Audit log created when file doesn't exist."""
        sprint_dir = str(tmp_path)

        _log_skip_decision(
            story_id="-8.t",
            reason="Tests passed during remediation",
            reconciliation_mode="propagated",
            sprint_dir=sprint_dir
        )

        audit_log_path = tmp_path / "validation_audit.log"
        assert audit_log_path.exists()

        with open(audit_log_path, "r", encoding="utf-8") as f:
            audit_log = json.load(f)

        assert "entries" in audit_log
        assert len(audit_log["entries"]) == 1

        entry = audit_log["entries"][0]
        assert entry["story_id"] == "-8.t"
        assert entry["check"] == "D"
        assert entry["action"] == "skipped"
        assert "Tests passed" in entry["reason"]
        assert entry["reconciliation_mode"] == "propagated"
        assert "timestamp" in entry

    def test_appends_to_existing_audit_log(self, tmp_path):
        """AC-8.4: Audit log appends to existing entries."""
        sprint_dir = str(tmp_path)
        audit_log_path = tmp_path / "validation_audit.log"

        # Create initial log
        initial_log = {
            "entries": [
                {
                    "timestamp": "2025-12-20T09:00:00Z",
                    "story_id": "-7.t",
                    "check": "D",
                    "action": "skipped",
                    "reason": "Previous skip",
                    "reconciliation_mode": "propagated"
                }
            ]
        }
        with open(audit_log_path, "w", encoding="utf-8") as f:
            json.dump(initial_log, f)

        # Append new entry
        _log_skip_decision(
            story_id="-8.t",
            reason="Tests passed during remediation",
            reconciliation_mode="propagated",
            sprint_dir=sprint_dir
        )

        # Verify appended
        with open(audit_log_path, "r", encoding="utf-8") as f:
            audit_log = json.load(f)

        assert len(audit_log["entries"]) == 2
        assert audit_log["entries"][0]["story_id"] == "-7.t"
        assert audit_log["entries"][1]["story_id"] == "-8.t"

    def test_audit_log_failure_non_blocking(self, tmp_path, capsys):
        """Audit log write failure should not block validation (logs warning)."""
        sprint_dir = "/invalid/path/that/does/not/exist"

        # Should not raise exception
        _log_skip_decision(
            story_id="-8.t",
            reason="Test reason",
            reconciliation_mode="propagated",
            sprint_dir=sprint_dir
        )

        # Check stderr for warning
        captured = capsys.readouterr()
        assert "Warning" in captured.err or "Failed to write audit log" in captured.err


# ============================================================================
# INTEGRATION TESTS - CLI EXECUTION
# ============================================================================

class TestCLIExecution:
    """Test suite for validate_test_pass_rates() CLI integration."""

    def test_cli_skip_propagated_json_output(self, tmp_path):
        """Integration: CLI skips propagated story with JSON output."""
        sprint_dir = str(tmp_path)
        queue_path = tmp_path / ".queue.json"

        # Create test queue
        queue = {
            "stories": [
                {
                    "id": "-8.t",
                    "title": "Testing: Validation Skip Logic",
                    "status": "pending",
                    "metadata": {
                        "reconciliation": {
                            "status": "propagated",
                            "needs_retest": False,
                            "source_story": "8.i",
                            "source_pass_rate": 100.0,
                            "source_test_count": 12
                        }
                    }
                }
            ]
        }
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f)

        # Run validation
        result = validate_test_pass_rates(
            story_id="-8.t",
            sprint_dir=sprint_dir,
            json_output=True
        )

        # Verify result
        assert result["check"] == "D"
        assert result["name"] == "Test Pass Rates"
        assert result["story_id"] == "-8.t"
        assert result["status"] == "skipped"
        assert "propagated" in result["skip_reason"].lower()
        assert result["reconciliation_mode"] == "propagated"
        assert "token_savings" in result
        assert "96%" in result["token_savings"]
        assert "reconciliation_metadata" in result

    def test_cli_run_needs_retest(self, tmp_path):
        """Integration: CLI runs Check D when needs_retest=True."""
        sprint_dir = str(tmp_path)
        queue_path = tmp_path / ".queue.json"

        # Create test queue
        queue = {
            "stories": [
                {
                    "id": "-8.t",
                    "title": "Testing: Validation Skip Logic",
                    "status": "pending",
                    "metadata": {
                        "reconciliation": {
                            "status": "pending_retest",
                            "needs_retest": True,
                            "source_story": "8.i",
                            "retest_reason": "Implementation changed"
                        }
                    }
                }
            ]
        }
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f)

        # Run validation
        result = validate_test_pass_rates(
            story_id="-8.t",
            sprint_dir=sprint_dir,
            json_output=True
        )

        # Verify result (should NOT skip)
        assert result["check"] == "D"
        assert result["story_id"] == "-8.t"
        assert result["status"] != "skipped"
        assert "run_reason" in result
        assert "retest" in result["run_reason"].lower()
        assert result["reconciliation_mode"] == "pending_retest"

    def test_cli_error_queue_not_found(self, tmp_path):
        """Integration: CLI raises FileNotFoundError when queue missing."""
        sprint_dir = str(tmp_path)  # No queue file created

        with pytest.raises(FileNotFoundError) as exc_info:
            validate_test_pass_rates(
                story_id="-8.t",
                sprint_dir=sprint_dir,
                json_output=True
            )

        assert "Queue file not found" in str(exc_info.value)

    def test_cli_error_story_not_found(self, tmp_path):
        """Integration: CLI raises ValueError when story not in queue."""
        sprint_dir = str(tmp_path)
        queue_path = tmp_path / ".queue.json"

        # Create queue without target story
        queue = {
            "stories": [
                {
                    "id": "-7.t",
                    "title": "Different story",
                    "status": "completed"
                }
            ]
        }
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f)

        with pytest.raises(ValueError) as exc_info:
            validate_test_pass_rates(
                story_id="-8.t",
                sprint_dir=sprint_dir,
                json_output=True
            )

        assert "Story -8.t not found in queue" in str(exc_info.value)


# ============================================================================
# TOKEN SAVINGS VALIDATION
# ============================================================================

class TestTokenSavings:
    """Test suite for token savings calculation and reporting."""

    def test_token_savings_reported_for_skip(self, tmp_path):
        """AC-8.5: Token savings reported when Check D is skipped."""
        sprint_dir = str(tmp_path)
        queue_path = tmp_path / ".queue.json"

        queue = {
            "stories": [
                {
                    "id": "-8.t",
                    "metadata": {
                        "reconciliation": {
                            "status": "propagated",
                            "needs_retest": False
                        }
                    }
                }
            ]
        }
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f)

        result = validate_test_pass_rates(
            story_id="-8.t",
            sprint_dir=sprint_dir,
            json_output=True
        )

        assert result["status"] == "skipped"
        assert "token_savings" in result
        assert "2000" in result["token_savings"]  # Expected savings range
        assert "96%" in result["token_savings"]

    def test_no_token_savings_when_running(self, tmp_path):
        """Token savings not reported when Check D runs."""
        sprint_dir = str(tmp_path)
        queue_path = tmp_path / ".queue.json"

        queue = {
            "stories": [
                {
                    "id": "-8.t",
                    "metadata": {
                        "reconciliation": {
                            "status": "pending_retest",
                            "needs_retest": True
                        }
                    }
                }
            ]
        }
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f)

        result = validate_test_pass_rates(
            story_id="-8.t",
            sprint_dir=sprint_dir,
            json_output=True
        )

        assert result["status"] != "skipped"
        assert "token_savings" not in result


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
