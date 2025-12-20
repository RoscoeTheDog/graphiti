#!/usr/bin/env python3
"""
Queue Helpers CLI - Reconciliation management commands

Commands:
    check-reconciliation    Check pending reconciliation status
    apply-reconciliation    Apply reconciliation to validation story
    reconciliation-status   Show sprint-wide reconciliation summary

Author: Sprint Remediation Test Reconciliation
Created: 2025-12-20
Story: 7 - queue_helpers.py Commands
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import (
    load_queue,
    save_queue,
    get_story
)
from .reconciliation import (
    apply_propagate_reconciliation,
    apply_retest_reconciliation,
    apply_supersede_reconciliation
)
from .overlap import determine_reconciliation_mode


def cmd_check_reconciliation(args: argparse.Namespace) -> None:
    """Check pending reconciliation status for a validation story."""
    try:
        # Load queue
        queue = load_queue(args.sprint_dir)

        # Get story by ID (validate exists)
        try:
            story = get_story(queue, args.story_id)
        except ValueError:
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "error": f"Story not found: {args.story_id}"
                }, indent=2))
            else:
                print(f"[ERROR] Story not found: {args.story_id}")
                print(f"  No story with ID '{args.story_id}' exists in the queue.")
                print(f"  Run 'python -m resources.commands.sprint.queue_helpers reconciliation-status' to see all validation stories.")
            sys.exit(1)

        # Check for metadata.test_reconciliation field
        metadata = story.get('metadata', {})
        test_recon = metadata.get('test_reconciliation')
        recon = metadata.get('reconciliation')

        # Determine status
        if test_recon is None:
            status = "no_reconciliation"
            if args.json:
                print(json.dumps({
                    "story_id": args.story_id,
                    "status": status,
                    "reconciliation_mode": None,
                    "source_remediation_id": None,
                    "test_overlap_ratio": None,
                    "test_files": None,
                    "remediation_test_results": None,
                    "applied_at": None,
                    "next_action": "No reconciliation data available for this story"
                }, indent=2))
            else:
                print(f"Reconciliation Status for Story: {args.story_id}")
                print("=" * 48)
                print(f"Status:                 [NO RECONCILIATION]")
                print(f"\nNo reconciliation data available for this story.")
                print(f"This story may not have been processed by REMEDIATE command.")
            return

        # Extract data from test_reconciliation
        recon_mode = test_recon.get('reconciliation_mode', 'unknown')
        source_id = test_recon.get('source_remediation_id')
        overlap_ratio = test_recon.get('test_overlap_ratio', 0.0)
        test_files = test_recon.get('test_files', [])
        pass_rate = test_recon.get('pass_rate', 0.0)

        # Calculate test file stats
        # Estimate matched files based on overlap ratio
        total_files = len(test_files)
        matched_files = int(total_files * overlap_ratio) if total_files > 0 else 0

        # Check if reconciliation has been applied
        if recon is not None:
            status = "applied"
            applied_at = recon.get('applied_at', 'unknown')

            if args.json:
                print(json.dumps({
                    "story_id": args.story_id,
                    "status": status,
                    "reconciliation_mode": recon_mode,
                    "source_remediation_id": source_id,
                    "test_overlap_ratio": overlap_ratio,
                    "test_files": {
                        "matched": matched_files,
                        "total": total_files
                    },
                    "remediation_test_results": {
                        "pass_rate": pass_rate,
                        "total": None,  # Not available in test_reconciliation
                        "passed": None,
                        "failed": None
                    },
                    "applied_at": applied_at,
                    "next_action": f"Reconciliation already applied on {applied_at}"
                }, indent=2))
            else:
                print(f"Reconciliation Status for Story: {args.story_id}")
                print("=" * 48)
                print(f"Status:                 [APPLIED]")
                print(f"Reconciliation Mode:    {recon_mode}")
                print(f"Source Remediation:     {source_id}")
                print(f"Test Overlap Ratio:     {overlap_ratio:.3f} ({overlap_ratio*100:.1f}%)")
                print(f"Test Files Matched:     {matched_files}/{total_files}")
                print(f"\nRemediation Test Results:")
                print(f"  Pass Rate:            {pass_rate:.1f}%")
                print(f"\nNext Action:")
                print(f"  Reconciliation already applied on {applied_at}")
        else:
            status = "pending"

            # Determine next action based on mode
            if recon_mode == "propagate":
                next_action = f"Run 'apply-reconciliation --story-id {args.story_id} --mode propagate' to mark validation complete"
            elif recon_mode == "retest":
                next_action = f"Run 'apply-reconciliation --story-id {args.story_id} --mode retest' to unblock validation for retest"
            elif recon_mode == "supersede":
                next_action = f"Run 'apply-reconciliation --story-id {args.story_id} --mode supersede --reason \"...\"' to supersede validation"
            elif recon_mode == "no_match":
                next_action = "No automatic reconciliation available - manual review required"
            else:
                next_action = "Unknown reconciliation mode"

            if args.json:
                print(json.dumps({
                    "story_id": args.story_id,
                    "status": status,
                    "reconciliation_mode": recon_mode,
                    "source_remediation_id": source_id,
                    "test_overlap_ratio": overlap_ratio,
                    "test_files": {
                        "matched": matched_files,
                        "total": total_files
                    },
                    "remediation_test_results": {
                        "pass_rate": pass_rate,
                        "total": None,
                        "passed": None,
                        "failed": None
                    },
                    "applied_at": None,
                    "next_action": next_action
                }, indent=2))
            else:
                print(f"Reconciliation Status for Story: {args.story_id}")
                print("=" * 48)
                print(f"Status:                 [PENDING]")
                print(f"Reconciliation Mode:    {recon_mode}")
                print(f"Source Remediation:     {source_id}")
                print(f"Test Overlap Ratio:     {overlap_ratio:.3f} ({overlap_ratio*100:.1f}%)")
                print(f"Test Files Matched:     {matched_files}/{total_files}")
                print(f"\nRemediation Test Results:")
                print(f"  Pass Rate:            {pass_rate:.1f}%")
                print(f"\nNext Action:")
                print(f"  {next_action}")

    except Exception as e:
        if args.json:
            print(json.dumps({
                "status": "error",
                "error": str(e)
            }, indent=2))
        else:
            print(f"[ERROR] {e}")
        sys.exit(1)


def cmd_apply_reconciliation(args: argparse.Namespace) -> None:
    """Apply reconciliation to validation story."""
    try:
        # Load queue
        queue = load_queue(args.sprint_dir)

        # Get story by ID (validate exists)
        try:
            story = get_story(queue, args.story_id)
        except ValueError:
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "error": f"Story not found: {args.story_id}"
                }, indent=2))
            else:
                print(f"[ERROR] Story not found: {args.story_id}")
                print(f"  No story with ID '{args.story_id}' exists in the queue.")
            sys.exit(1)

        # Get test_reconciliation metadata (validate exists)
        metadata = story.get('metadata', {})
        test_recon = metadata.get('test_reconciliation')

        if test_recon is None:
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "error": f"No reconciliation data for story: {args.story_id}"
                }, indent=2))
            else:
                print(f"[ERROR] No reconciliation data for story: {args.story_id}")
                print(f"  Story '{args.story_id}' does not have test_reconciliation metadata.")
                print(f"  This story may not have been processed by REMEDIATE command.")
            sys.exit(1)

        # Extract source_remediation_id and test_results
        source_id = test_recon.get('source_remediation_id')

        # Build test_results dict from test_reconciliation metadata
        test_results = {
            'pass_rate': test_recon.get('pass_rate', 0.0),
            'test_count': len(test_recon.get('test_files', [])),
            'test_files': test_recon.get('test_files', [])
        }

        # Validate mode argument (argparse already validates choices)
        mode = args.mode

        # For supersede mode: validate --reason provided
        if mode == 'supersede':
            if not args.reason or not args.reason.strip():
                if args.json:
                    print(json.dumps({
                        "status": "error",
                        "error": "Supersession reason required"
                    }, indent=2))
                else:
                    print(f"[ERROR] Supersession reason required")
                    print(f"  --reason is required when using --mode supersede")
                    print(f"  Example: --reason \"Remediation replaced original implementation\"")
                sys.exit(1)

        # Call appropriate reconciliation function
        result = None
        if mode == 'propagate':
            result = apply_propagate_reconciliation(
                target_validation_id=args.story_id,
                source_remediation_id=source_id,
                test_results=test_results,
                sprint_dir=args.sprint_dir
            )
        elif mode == 'retest':
            # Use overlap ratio to determine retest reason
            overlap_ratio = test_recon.get('test_overlap_ratio', 0.0)
            retest_reason = f"Test overlap {overlap_ratio*100:.1f}% - below propagation threshold (95%)"
            result = apply_retest_reconciliation(
                target_validation_id=args.story_id,
                source_remediation_id=source_id,
                test_results=test_results,
                retest_reason=retest_reason,
                sprint_dir=args.sprint_dir
            )
        elif mode == 'supersede':
            result = apply_supersede_reconciliation(
                target_validation_id=args.story_id,
                source_remediation_id=source_id,
                test_results=test_results,
                supersession_reason=args.reason,
                sprint_dir=args.sprint_dir
            )

        # Display results
        if result['status'] == 'error':
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"[ERROR] {result.get('error', 'Unknown error')}")
            sys.exit(1)
        elif result['status'] == 'skipped':
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"[SKIPPED] {result.get('reason', 'Unknown reason')}")
        else:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("Applying Reconciliation")
                print("=" * 48)
                print(f"Target Validation:      {result['target']}")
                print(f"Source Remediation:     {result['source']}")
                print(f"Mode:                   {result['mode']}")
                print(f"\n[OK] Reconciliation applied successfully")
                print(f"Updated Stories:")
                for story_id in result.get('updated_stories', []):
                    # Reload queue to get updated status
                    queue = load_queue(args.sprint_dir)
                    updated_story = queue['stories'].get(story_id, {})
                    status = updated_story.get('status', 'unknown')
                    if story_id == args.story_id:
                        print(f"  - {story_id}: -> {status}")
                    else:
                        print(f"  - {story_id}: -> {status} (parent)")
                print(f"\nMessage: {result['message']}")

    except Exception as e:
        if args.json:
            print(json.dumps({
                "status": "error",
                "error": str(e)
            }, indent=2))
        else:
            print(f"[ERROR] {e}")
        sys.exit(1)


def cmd_reconciliation_status(args: argparse.Namespace) -> None:
    """Show sprint-wide reconciliation summary."""
    try:
        # Load queue
        queue = load_queue(args.sprint_dir)

        # Get sprint metadata
        sprint_id = queue.get('sprint_id', 'unknown')
        sprint_name = queue.get('sprint_name', 'unknown')
        sprint_version = queue.get('version', 'unknown')
        sprint_status = queue.get('status', 'unknown')

        # Initialize categorization
        pending_by_mode = {
            'propagate': [],
            'retest': [],
            'supersede': [],
            'no_match': []
        }
        applied_by_status = {
            'propagated': [],
            'retest_unblocked': [],
            'superseded': []
        }
        no_reconciliation = []

        # Iterate through all stories
        for story_id, story in queue.get('stories', {}).items():
            # Check if validation story (type: 'testing' or has '.t' suffix)
            story_type = story.get('type', '')
            if story_type != 'testing' and not story_id.endswith('.t'):
                continue

            metadata = story.get('metadata', {})
            test_recon = metadata.get('test_reconciliation')
            recon = metadata.get('reconciliation')

            # Categorize
            if test_recon is None:
                no_reconciliation.append({
                    'story_id': story_id,
                    'title': story.get('title', ''),
                    'status': story.get('status', 'unknown')
                })
            elif recon is not None:
                # Applied reconciliation
                recon_status = recon.get('status', 'unknown')
                if recon_status == 'propagated':
                    applied_by_status['propagated'].append({
                        'story_id': story_id,
                        'title': story.get('title', ''),
                        'source_remediation_id': recon.get('source_story', test_recon.get('source_remediation_id')),
                        'applied_at': recon.get('applied_at', 'unknown')
                    })
                elif recon_status == 'pending_retest':
                    applied_by_status['retest_unblocked'].append({
                        'story_id': story_id,
                        'title': story.get('title', ''),
                        'source_remediation_id': recon.get('source_story', test_recon.get('source_remediation_id')),
                        'applied_at': recon.get('applied_at', 'unknown')
                    })
                elif recon_status == 'superseded':
                    applied_by_status['superseded'].append({
                        'story_id': story_id,
                        'title': story.get('title', ''),
                        'source_remediation_id': recon.get('superseded_by', test_recon.get('source_remediation_id')),
                        'applied_at': recon.get('applied_at', 'unknown')
                    })
            else:
                # Pending reconciliation
                recon_mode = test_recon.get('reconciliation_mode', 'unknown')
                overlap_ratio = test_recon.get('test_overlap_ratio', 0.0)
                source_id = test_recon.get('source_remediation_id')

                story_data = {
                    'story_id': story_id,
                    'title': story.get('title', ''),
                    'overlap_ratio': overlap_ratio,
                    'source_remediation_id': source_id
                }

                if recon_mode in pending_by_mode:
                    pending_by_mode[recon_mode].append(story_data)

        # Calculate summary statistics
        pending_total = sum(len(stories) for stories in pending_by_mode.values())
        applied_total = sum(len(stories) for stories in applied_by_status.values())

        # Output results
        if args.json:
            print(json.dumps({
                "sprint": {
                    "id": sprint_id,
                    "name": sprint_name,
                    "version": sprint_version,
                    "status": sprint_status
                },
                "summary": {
                    "pending_reconciliations": {
                        "total": pending_total,
                        "propagate": len(pending_by_mode['propagate']),
                        "retest": len(pending_by_mode['retest']),
                        "supersede": len(pending_by_mode['supersede']),
                        "no_match": len(pending_by_mode['no_match'])
                    },
                    "applied_reconciliations": {
                        "total": applied_total,
                        "propagated": len(applied_by_status['propagated']),
                        "retest_unblocked": len(applied_by_status['retest_unblocked']),
                        "superseded": len(applied_by_status['superseded'])
                    },
                    "no_reconciliation": len(no_reconciliation)
                },
                "pending": pending_by_mode,
                "applied": applied_by_status,
                "no_reconciliation": no_reconciliation
            }, indent=2))
        else:
            print("Sprint Reconciliation Status")
            print("=" * 48)
            print(f"Sprint:     {sprint_name} ({sprint_id})")
            print(f"Version:    {sprint_version}")
            print(f"Status:     {sprint_status}")
            print(f"\nSummary:")
            print(f"  Pending Reconciliations:     {pending_total}")
            print(f"    - Propagate:                {len(pending_by_mode['propagate'])}")
            print(f"    - Retest:                   {len(pending_by_mode['retest'])}")
            print(f"    - Supersede:                {len(pending_by_mode['supersede'])}")
            print(f"    - No Match:                 {len(pending_by_mode['no_match'])}")
            print(f"\n  Applied Reconciliations:     {applied_total}")
            print(f"    - Propagated:               {len(applied_by_status['propagated'])}")
            print(f"    - Retest Unblocked:         {len(applied_by_status['retest_unblocked'])}")
            print(f"    - Superseded:               {len(applied_by_status['superseded'])}")
            print(f"\n  No Reconciliation:           {len(no_reconciliation)}")

            # Show pending reconciliations by mode
            for mode, stories in pending_by_mode.items():
                if stories:
                    print(f"\nPending Reconciliations ({mode}):")
                    for story in stories:
                        print(f"  - {story['story_id']}: {story['title']} (overlap: {story['overlap_ratio']:.3f}, source: {story['source_remediation_id']})")

            # Show applied reconciliations by status
            for status, stories in applied_by_status.items():
                if stories:
                    print(f"\nApplied Reconciliations ({status}):")
                    for story in stories:
                        print(f"  - {story['story_id']}: {story['title']} (source: {story['source_remediation_id']}, applied: {story['applied_at']})")

    except Exception as e:
        if args.json:
            print(json.dumps({
                "status": "error",
                "error": str(e)
            }, indent=2))
        else:
            print(f"[ERROR] {e}")
        sys.exit(1)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Queue Helpers - Reconciliation management commands",
        prog="queue_helpers"
    )

    # Global options
    parser.add_argument(
        '--sprint-dir',
        default='.claude/sprint',
        help='Sprint directory path (default: .claude/sprint)'
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # check-reconciliation subcommand
    check_parser = subparsers.add_parser(
        'check-reconciliation',
        help='Check pending reconciliation status',
        description='Check pending reconciliation status for a validation story',
        epilog="""
examples:
  python -m resources.commands.sprint.queue_helpers check-reconciliation --story-id 1.t
  python -m resources.commands.sprint.queue_helpers check-reconciliation --story-id 1.t --json

exit codes:
  0  Success
  1  Error (story not found, invalid JSON, etc.)
        """
    )
    check_parser.add_argument(
        '--story-id',
        required=True,
        help='Validation story ID to check (required)'
    )
    check_parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON format'
    )
    check_parser.set_defaults(func=cmd_check_reconciliation)

    # apply-reconciliation subcommand
    apply_parser = subparsers.add_parser(
        'apply-reconciliation',
        help='Apply reconciliation to validation story',
        description='Manually apply reconciliation to a validation story',
        epilog="""
examples:
  python -m resources.commands.sprint.queue_helpers apply-reconciliation --story-id 1.t --mode propagate
  python -m resources.commands.sprint.queue_helpers apply-reconciliation --story-id 1.t --mode retest
  python -m resources.commands.sprint.queue_helpers apply-reconciliation --story-id 1.t --mode supersede --reason "Remediation replaced original implementation"

exit codes:
  0  Success
  1  Error (story not found, invalid mode, etc.)
        """
    )
    apply_parser.add_argument(
        '--story-id',
        required=True,
        help='Validation story ID (required)'
    )
    apply_parser.add_argument(
        '--mode',
        required=True,
        choices=['propagate', 'retest', 'supersede'],
        help='Reconciliation mode (required)'
    )
    apply_parser.add_argument(
        '--reason',
        help='Supersession reason (required for supersede mode)'
    )
    apply_parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON format'
    )
    apply_parser.set_defaults(func=cmd_apply_reconciliation)

    # reconciliation-status subcommand
    status_parser = subparsers.add_parser(
        'reconciliation-status',
        help='Show sprint-wide reconciliation summary',
        description='Show sprint-wide reconciliation summary',
        epilog="""
examples:
  python -m resources.commands.sprint.queue_helpers reconciliation-status
  python -m resources.commands.sprint.queue_helpers reconciliation-status --json

exit codes:
  0  Success
  1  Error (queue file not found, etc.)
        """
    )
    status_parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON format'
    )
    status_parser.set_defaults(func=cmd_reconciliation_status)

    # Parse and execute
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
