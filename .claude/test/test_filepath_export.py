"""
Quick test script for add_memory filepath parameter.
"""
import asyncio
from pathlib import Path
from mcp_server.export_helpers import _resolve_path_pattern, _scan_for_credentials


async def test_filepath_export():
    """Test the file export functionality directly"""

    # Test data
    test_episodes = [
        {
            "name": "Test Session s001",
            "episode_body": """## Test Session s001: Initial Handoff Test

**Status**: ACTIVE
**Created**: 2025-11-09
**Objective**: Test the enhanced add_memory() filepath parameter

## Current State
- Implemented filepath parameter in graphiti MCP server
- Parameter renamed from export_path to filepath
- Supports path variable substitution: {date}, {timestamp}, {time}, {hash}
- Security scanning for credentials
- Backward compatible (filepath optional)

## Next Steps
1. Verify file export works correctly
2. Test path variable substitution
3. Create v3.7.2-experimental with handoff schema
4. Update CLAUDE.md with simplified rules

## Context
- Files: mcp_server/graphiti_mcp_server.py:1031, mcp_server/export_helpers.py
- Tests: tests/mcp/test_add_memory_export.py (22 tests, all passing)
- Commit: 64f90c9 (export infrastructure)
""",
            "filepath": ".claude/handoff/snapshots/s001-handoff-test.md"
        },
        {
            "name": "Test Session s002",
            "episode_body": """## Test Session s002: Path Variable Test

**Status**: ACTIVE
**Created**: {timestamp}
**Objective**: Test dynamic path variable substitution

## Current State
- Testing {date} variable
- Testing {timestamp} variable
- Testing {hash} variable (query-based)

## Notes
This file should have the current date and timestamp in its path.
""",
            "filepath": ".claude/handoff/snapshots/s002-{date}-variables.md"
        },
        {
            "name": "Bug Report",
            "episode_body": """# Authentication Bug

**Issue**: Login timeout after 5 minutes of inactivity

**Steps to Reproduce**:
1. Log in to application
2. Wait 5 minutes
3. Try to perform action
4. Observe timeout error

**Expected**: Session should remain active
**Actual**: User logged out

**Priority**: High
""",
            "filepath": ".claude/handoff/snapshots/bug-{date}-{time}.md"
        }
    ]

    print("Testing filepath export functionality...\n")

    for i, episode in enumerate(test_episodes, 1):
        print(f"Test {i}: {episode['name']}")
        print(f"  Pattern: {episode['filepath']}")

        try:
            # Resolve path pattern
            resolved_path = _resolve_path_pattern(
                episode['filepath'],
                query=episode['name'],
                fact_count=0,
                node_count=0,
            )
            print(f"  Resolved: {resolved_path}")

            # Security scan
            detected = _scan_for_credentials(episode['episode_body'])
            if detected:
                print(f"  [!]  Credentials detected: {', '.join(detected)}")
            else:
                print(f"  [OK] No credentials detected")

            # Write file
            output_path = Path(resolved_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(episode['episode_body'], encoding='utf-8')

            # Verify
            if output_path.exists():
                size = output_path.stat().st_size
                print(f"  [OK] File written: {size} bytes")
            else:
                print(f"  [ERROR] File not found!")

        except Exception as e:
            print(f"  [ERROR] Error: {e}")

        print()

    # Summary
    print("\nTest Summary:")
    print("=" * 60)
    snapshot_dir = Path(".claude/handoff/snapshots")
    if snapshot_dir.exists():
        files = list(snapshot_dir.glob("*.md"))
        print(f"Files created: {len(files)}")
        for f in sorted(files):
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    else:
        print("[ERROR] Snapshot directory not found!")

    print("\n[OK] Test complete. Files ready for manual verification.")
    print(f"Location: {snapshot_dir.absolute()}")


if __name__ == "__main__":
    asyncio.run(test_filepath_export())
