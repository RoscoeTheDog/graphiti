"""
Unit and Integration Tests for Queue Helpers CLI Commands

Tests the queue_helpers CLI commands:
- check-reconciliation --story-id <id> [--json]
- apply-reconciliation --story-id <id> --mode <mode> [--reason] [--json]
- reconciliation-status [--json]

Story: 7.t - Testing phase for queue_helpers.py Commands
Author: Sprint Remediation Test Reconciliation
Created: 2025-12-20
"""

import argparse
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest

# Import CLI functions
from resources.commands.sprint.queue_helpers.cli import (
    cmd_check_reconciliation,
    cmd_apply_reconciliation,
    cmd_reconciliation_status,
    main
)


# Test Fixtures

@pytest.fixture
def mock_queue_minimal():
    """Minimal queue data for basic tests."""
    return {
        'sprint_id': 'test-sprint',
        'sprint_name': 'Test Sprint',
        'version': '1.0.0',
        'status': 'active',
        'stories': {}
    }


@pytest.fixture
def mock_queue_with_pending():
    """Queue with pending reconciliation."""
    return {
        'sprint_id': 'test-sprint',
        'sprint_name': 'Test Sprint',
        'version': '1.0.0',
        'status': 'active',
        'stories': {
            '1.t': {
                'id': '1.t',
                'title': 'Test Story',
                'type': 'testing',
                'status': 'blocked',
                'metadata': {
                    'test_reconciliation': {
                        'reconciliation_mode': 'propagate',
                        'source_remediation_id': '1.r',
                        'test_overlap_ratio': 0.98,
                        'test_files': ['test_a.py', 'test_b.py'],
                        'pass_rate': 95.0
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_queue_with_applied():
    """Queue with applied reconciliation."""
    return {
        'sprint_id': 'test-sprint',
        'sprint_name': 'Test Sprint',
        'version': '1.0.0',
        'status': 'active',
        'stories': {
            '1.t': {
                'id': '1.t',
                'title': 'Test Story',
                'type': 'testing',
                'status': 'completed',
                'metadata': {
                    'test_reconciliation': {
                        'reconciliation_mode': 'propagate',
                        'source_remediation_id': '1.r',
                        'test_overlap_ratio': 0.98,
                        'test_files': ['test_a.py', 'test_b.py'],
                        'pass_rate': 95.0
                    },
                    'reconciliation': {
                        'status': 'propagated',
                        'source_story': '1.r',
                        'applied_at': '2025-12-20T10:00:00'
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_queue_with_multiple():
    """Queue with multiple reconciliation scenarios."""
    return {
        'sprint_id': 'test-sprint',
        'sprint_name': 'Test Sprint',
        'version': '1.0.0',
        'status': 'active',
        'stories': {
            '1.t': {
                'id': '1.t',
                'title': 'Propagate Test',
                'type': 'testing',
                'status': 'blocked',
                'metadata': {
                    'test_reconciliation': {
                        'reconciliation_mode': 'propagate',
                        'source_remediation_id': '1.r',
                        'test_overlap_ratio': 0.98,
                        'test_files': ['test_a.py'],
                        'pass_rate': 95.0
                    }
                }
            },
            '2.t': {
                'id': '2.t',
                'title': 'Retest Test',
                'type': 'testing',
                'status': 'blocked',
                'metadata': {
                    'test_reconciliation': {
                        'reconciliation_mode': 'retest',
                        'source_remediation_id': '2.r',
                        'test_overlap_ratio': 0.85,
                        'test_files': ['test_b.py'],
                        'pass_rate': 80.0
                    }
                }
            },
            '3.t': {
                'id': '3.t',
                'title': 'Applied Test',
                'type': 'testing',
                'status': 'completed',
                'metadata': {
                    'test_reconciliation': {
                        'reconciliation_mode': 'propagate',
                        'source_remediation_id': '3.r',
                        'test_overlap_ratio': 0.99,
                        'test_files': ['test_c.py'],
                        'pass_rate': 100.0
                    },
                    'reconciliation': {
                        'status': 'propagated',
                        'source_story': '3.r',
                        'applied_at': '2025-12-20T10:00:00'
                    }
                }
            },
            '4.t': {
                'id': '4.t',
                'title': 'No Reconciliation Test',
                'type': 'testing',
                'status': 'pending'
            }
        }
    }


# Unit Tests: check-reconciliation

class TestCheckReconciliation:
    """Unit tests for check-reconciliation command."""

    def test_check_pending_reconciliation_text_output(self, mock_queue_with_pending, capsys):
        """Test check-reconciliation with pending reconciliation (text output)."""
        args = argparse.Namespace(
            story_id='1.t',
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_pending):
            cmd_check_reconciliation(args)

        captured = capsys.readouterr()
        assert '[PENDING]' in captured.out
        assert 'propagate' in captured.out
        assert '1.r' in captured.out
        assert '0.980' in captured.out
        assert 'Next Action:' in captured.out

    def test_check_pending_reconciliation_json_output(self, mock_queue_with_pending, capsys):
        """Test check-reconciliation with pending reconciliation (JSON output)."""
        args = argparse.Namespace(
            story_id='1.t',
            json=True,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_pending):
            cmd_check_reconciliation(args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result['status'] == 'pending'
        assert result['reconciliation_mode'] == 'propagate'
        assert result['source_remediation_id'] == '1.r'
        assert result['test_overlap_ratio'] == 0.98
        assert result['test_files']['matched'] == 1  # int(2 * 0.98) = 1
        assert result['test_files']['total'] == 2
        assert result['applied_at'] is None

    def test_check_applied_reconciliation(self, mock_queue_with_applied, capsys):
        """Test check-reconciliation with applied reconciliation."""
        args = argparse.Namespace(
            story_id='1.t',
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_applied):
            cmd_check_reconciliation(args)

        captured = capsys.readouterr()
        assert '[APPLIED]' in captured.out
        assert '2025-12-20T10:00:00' in captured.out

    def test_check_invalid_story_id(self, mock_queue_minimal, capsys):
        """Test check-reconciliation with invalid story ID."""
        args = argparse.Namespace(
            story_id='999.t',
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_minimal):
            with pytest.raises(SystemExit) as exc_info:
                cmd_check_reconciliation(args)

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert '[ERROR]' in captured.out
        assert '999.t' in captured.out

    def test_check_no_reconciliation_data(self, mock_queue_with_multiple, capsys):
        """Test check-reconciliation with story that has no reconciliation data."""
        args = argparse.Namespace(
            story_id='4.t',
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_multiple):
            cmd_check_reconciliation(args)

        captured = capsys.readouterr()
        assert '[NO RECONCILIATION]' in captured.out


# Unit Tests: apply-reconciliation

class TestApplyReconciliation:
    """Unit tests for apply-reconciliation command."""

    def test_apply_propagate_mode(self, mock_queue_with_pending, capsys):
        """Test apply-reconciliation with propagate mode."""
        args = argparse.Namespace(
            story_id='1.t',
            mode='propagate',
            reason=None,
            json=False,
            sprint_dir='.claude/sprint'
        )

        mock_result = {
            'status': 'success',
            'target': '1.t',
            'source': '1.r',
            'mode': 'propagate',
            'message': 'Propagation applied successfully',
            'updated_stories': ['1.t']
        }

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_pending):
            with patch('resources.commands.sprint.queue_helpers.cli.apply_propagate_reconciliation', return_value=mock_result):
                cmd_apply_reconciliation(args)

        captured = capsys.readouterr()
        assert '[OK]' in captured.out
        assert 'propagate' in captured.out
        assert '1.t' in captured.out

    def test_apply_retest_mode(self, mock_queue_with_pending, capsys):
        """Test apply-reconciliation with retest mode."""
        # Modify queue for retest scenario
        queue = mock_queue_with_pending.copy()
        queue['stories']['1.t']['metadata']['test_reconciliation']['reconciliation_mode'] = 'retest'

        args = argparse.Namespace(
            story_id='1.t',
            mode='retest',
            reason=None,
            json=False,
            sprint_dir='.claude/sprint'
        )

        mock_result = {
            'status': 'success',
            'target': '1.t',
            'source': '1.r',
            'mode': 'retest',
            'message': 'Retest reconciliation applied',
            'updated_stories': ['1.t']
        }

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=queue):
            with patch('resources.commands.sprint.queue_helpers.cli.apply_retest_reconciliation', return_value=mock_result):
                cmd_apply_reconciliation(args)

        captured = capsys.readouterr()
        assert '[OK]' in captured.out
        assert 'retest' in captured.out

    def test_apply_supersede_mode_with_reason(self, mock_queue_with_pending, capsys):
        """Test apply-reconciliation with supersede mode and reason."""
        args = argparse.Namespace(
            story_id='1.t',
            mode='supersede',
            reason='Remediation replaced original implementation',
            json=False,
            sprint_dir='.claude/sprint'
        )

        mock_result = {
            'status': 'success',
            'target': '1.t',
            'source': '1.r',
            'mode': 'supersede',
            'message': 'Supersession applied',
            'updated_stories': ['1.t']
        }

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_pending):
            with patch('resources.commands.sprint.queue_helpers.cli.apply_supersede_reconciliation', return_value=mock_result):
                cmd_apply_reconciliation(args)

        captured = capsys.readouterr()
        assert '[OK]' in captured.out
        assert 'supersede' in captured.out

    def test_apply_supersede_without_reason_fails(self, mock_queue_with_pending, capsys):
        """Test apply-reconciliation with supersede mode but no reason (validation error)."""
        args = argparse.Namespace(
            story_id='1.t',
            mode='supersede',
            reason='',
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_pending):
            with pytest.raises(SystemExit) as exc_info:
                cmd_apply_reconciliation(args)

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert '[ERROR]' in captured.out
        assert 'reason required' in captured.out.lower()

    def test_apply_invalid_story_id(self, mock_queue_minimal, capsys):
        """Test apply-reconciliation with invalid story ID."""
        args = argparse.Namespace(
            story_id='999.t',
            mode='propagate',
            reason=None,
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_minimal):
            with pytest.raises(SystemExit) as exc_info:
                cmd_apply_reconciliation(args)

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert '[ERROR]' in captured.out
        assert '999.t' in captured.out

    def test_apply_no_reconciliation_data(self, mock_queue_with_multiple, capsys):
        """Test apply-reconciliation with story that has no reconciliation data."""
        args = argparse.Namespace(
            story_id='4.t',
            mode='propagate',
            reason=None,
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_multiple):
            with pytest.raises(SystemExit) as exc_info:
                cmd_apply_reconciliation(args)

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert '[ERROR]' in captured.out
        assert 'No reconciliation data' in captured.out


# Unit Tests: reconciliation-status

class TestReconciliationStatus:
    """Unit tests for reconciliation-status command."""

    def test_status_empty_queue(self, mock_queue_minimal, capsys):
        """Test reconciliation-status with empty queue."""
        args = argparse.Namespace(
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_minimal):
            cmd_reconciliation_status(args)

        captured = capsys.readouterr()
        assert 'Sprint Reconciliation Status' in captured.out
        assert 'Test Sprint' in captured.out
        assert 'Pending Reconciliations:     0' in captured.out

    def test_status_with_multiple_scenarios(self, mock_queue_with_multiple, capsys):
        """Test reconciliation-status with multiple scenarios."""
        args = argparse.Namespace(
            json=False,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_multiple):
            cmd_reconciliation_status(args)

        captured = capsys.readouterr()
        assert 'Sprint Reconciliation Status' in captured.out
        assert 'Pending Reconciliations:     2' in captured.out
        assert 'Propagate:                1' in captured.out
        assert 'Retest:                   1' in captured.out
        assert 'Applied Reconciliations:     1' in captured.out
        assert 'No Reconciliation:           1' in captured.out

    def test_status_json_output(self, mock_queue_with_multiple, capsys):
        """Test reconciliation-status with JSON output."""
        args = argparse.Namespace(
            json=True,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_multiple):
            cmd_reconciliation_status(args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result['sprint']['id'] == 'test-sprint'
        assert result['summary']['pending_reconciliations']['total'] == 2
        assert result['summary']['pending_reconciliations']['propagate'] == 1
        assert result['summary']['pending_reconciliations']['retest'] == 1
        assert result['summary']['applied_reconciliations']['total'] == 1
        assert result['summary']['no_reconciliation'] == 1

        # Check detailed data
        assert len(result['pending']['propagate']) == 1
        assert len(result['pending']['retest']) == 1
        assert len(result['applied']['propagated']) == 1
        assert len(result['no_reconciliation']) == 1


# Integration Tests

class TestFullWorkflow:
    """Integration tests for complete workflows."""

    def test_check_then_apply_then_verify(self, mock_queue_with_pending, capsys):
        """Test full workflow: check → apply → verify."""
        # Step 1: Check reconciliation status
        check_args = argparse.Namespace(
            story_id='1.t',
            json=True,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_pending):
            cmd_check_reconciliation(check_args)

        check_output = capsys.readouterr()
        check_result = json.loads(check_output.out)
        assert check_result['status'] == 'pending'

        # Step 2: Apply reconciliation
        apply_args = argparse.Namespace(
            story_id='1.t',
            mode='propagate',
            reason=None,
            json=True,
            sprint_dir='.claude/sprint'
        )

        mock_apply_result = {
            'status': 'success',
            'target': '1.t',
            'source': '1.r',
            'mode': 'propagate',
            'message': 'Propagation applied successfully',
            'updated_stories': ['1.t']
        }

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_pending):
            with patch('resources.commands.sprint.queue_helpers.cli.apply_propagate_reconciliation', return_value=mock_apply_result):
                cmd_apply_reconciliation(apply_args)

        apply_output = capsys.readouterr()
        apply_result = json.loads(apply_output.out)
        assert apply_result['status'] == 'success'

        # Step 3: Verify applied status
        verify_args = argparse.Namespace(
            story_id='1.t',
            json=True,
            sprint_dir='.claude/sprint'
        )

        # Update queue to show applied reconciliation
        queue_with_applied = mock_queue_with_pending.copy()
        queue_with_applied['stories']['1.t']['metadata']['reconciliation'] = {
            'status': 'propagated',
            'source_story': '1.r',
            'applied_at': '2025-12-20T10:00:00'
        }

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=queue_with_applied):
            cmd_check_reconciliation(verify_args)

        verify_output = capsys.readouterr()
        verify_result = json.loads(verify_output.out)
        assert verify_result['status'] == 'applied'

    def test_sprint_wide_summary_accuracy(self, mock_queue_with_multiple, capsys):
        """Test sprint-wide summary counts accurately."""
        args = argparse.Namespace(
            json=True,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_multiple):
            cmd_reconciliation_status(args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        # Verify counts match expectations
        pending_total = result['summary']['pending_reconciliations']['total']
        applied_total = result['summary']['applied_reconciliations']['total']
        no_recon = result['summary']['no_reconciliation']

        assert pending_total == 2  # 1.t (propagate) + 2.t (retest)
        assert applied_total == 1  # 3.t (propagated)
        assert no_recon == 1  # 4.t (no reconciliation)

    def test_error_handling_with_real_queue_structure(self, tmp_path):
        """Test error handling with realistic queue file operations."""
        # Create temporary sprint directory
        sprint_dir = tmp_path / ".claude" / "sprint"
        sprint_dir.mkdir(parents=True)

        # Write invalid JSON to queue file
        queue_file = sprint_dir / "queue.json"
        queue_file.write_text("{ invalid json }")

        args = argparse.Namespace(
            story_id='1.t',
            json=True,
            sprint_dir=str(sprint_dir)
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd_check_reconciliation(args)

        assert exc_info.value.code == 1


# JSON Output Format Tests

class TestJSONOutput:
    """Test JSON output format consistency."""

    def test_check_reconciliation_json_schema(self, mock_queue_with_pending, capsys):
        """Test check-reconciliation JSON output has required fields."""
        args = argparse.Namespace(
            story_id='1.t',
            json=True,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_pending):
            cmd_check_reconciliation(args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        # Required fields
        required_fields = [
            'story_id', 'status', 'reconciliation_mode',
            'source_remediation_id', 'test_overlap_ratio',
            'test_files', 'remediation_test_results',
            'applied_at', 'next_action'
        ]

        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_reconciliation_status_json_schema(self, mock_queue_with_multiple, capsys):
        """Test reconciliation-status JSON output has required fields."""
        args = argparse.Namespace(
            json=True,
            sprint_dir='.claude/sprint'
        )

        with patch('resources.commands.sprint.queue_helpers.cli.load_queue', return_value=mock_queue_with_multiple):
            cmd_reconciliation_status(args)

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        # Required top-level fields
        assert 'sprint' in result
        assert 'summary' in result
        assert 'pending' in result
        assert 'applied' in result
        assert 'no_reconciliation' in result

        # Sprint fields
        assert 'id' in result['sprint']
        assert 'name' in result['sprint']
        assert 'version' in result['sprint']
        assert 'status' in result['sprint']

        # Summary fields
        assert 'pending_reconciliations' in result['summary']
        assert 'applied_reconciliations' in result['summary']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
