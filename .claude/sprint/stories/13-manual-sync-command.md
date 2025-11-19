# Story 13: Manual Sync Command - Historical Data Indexing

**Status**: completed
**Claimed**: 2025-11-19 07:03
**Completed**: 2025-11-19 07:23
**Created**: 2025-11-18 23:01
**Priority**: MEDIUM
**Estimated Effort**: 10 hours
**Phase**: 5 (Week 2, Days 4-5)
**Depends on**: Story 12 (rolling period filter)

## Description

Implement manual sync command for users who want to index historical sessions beyond the rolling window. Provides dry-run mode, cost estimation, and safety limits to prevent accidental expensive operations.

**Features**:
- MCP tool: `session_tracking_sync_history()`
- CLI command: `graphiti-mcp session-tracking sync`
- Dry-run mode (default: true)
- Cost estimation before sync
- Safety limits (default: max 100 sessions)
- Confirmation required for dangerous operations (--days 0 = all history)

## Acceptance Criteria

### MCP Tool Implementation
- [ ] Add `session_tracking_sync_history()` function to MCP server
- [ ] Implement session discovery with time range filter
- [ ] Implement cost estimation (sessions × $0.17 average)
- [ ] Implement dry-run mode (preview only, no indexing)
- [ ] Implement actual sync logic (parse → filter → index)
- [ ] Safety limit: default max 100 sessions
- [ ] Return JSON with session count, estimated cost, indexed count
- [ ] Test: Dry-run returns preview without indexing
- [ ] Test: Cost estimation accurate
- [ ] Test: Safety limit enforced

### CLI Command Implementation
- [ ] Add `sync` subcommand to `graphiti-mcp session-tracking`
- [ ] Add `--project <path>` flag (default: all projects)
- [ ] Add `--days <N>` flag (default: 7)
- [ ] Add `--max-sessions <N>` flag (default: 100)
- [ ] Add `--dry-run` flag (default: true)
- [ ] Add `--confirm` flag (required for --days 0)
- [ ] Format output as table view
- [ ] Show cost estimate before syncing
- [ ] Require confirmation for dangerous operations
- [ ] Test: CLI flags work correctly
- [ ] Test: Confirmation prompt appears
- [ ] Test: Table output formatted correctly

### Session Discovery & Filtering
- [ ] Discover sessions in specified project(s)
- [ ] Filter by modification time (last N days)
- [ ] Filter by max session count (safety limit)
- [ ] Sort by modification time (newest first)
- [ ] Log discovered session count
- [ ] Test: Time-based filtering works
- [ ] Test: Max session limit enforced

### Cost Estimation
- [ ] Calculate estimated cost per session (~$0.17 average)
- [ ] Calculate total estimated cost
- [ ] Display cost in user-friendly format
- [ ] Include token count estimates
- [ ] Test: Cost estimation formula accurate

## Implementation Details

### Files to Modify

**`mcp_server/graphiti_mcp_server.py`**:

Add MCP tool:

```python
async def session_tracking_sync_history(
    project: Optional[str] = None,
    days: int = 7,
    max_sessions: int = 100,
    dry_run: bool = True,
) -> str:
    """Manually sync historical sessions to Graphiti.

    Args:
        project: Project path to sync (None = all projects in watch_path)
        days: Number of days to look back (0 = all history, requires --confirm)
        max_sessions: Maximum sessions to sync (safety limit)
        dry_run: Preview mode without actual indexing

    Returns:
        JSON string with sync results
    """
    if not _session_manager:
        return json.dumps({"error": "Session tracking not initialized"})

    # Discover sessions
    sessions = _discover_sessions_for_sync(
        project=project,
        days=days,
        max_sessions=max_sessions,
    )

    # Calculate cost estimate
    estimated_cost = len(sessions) * 0.17  # $0.17 average per session
    estimated_tokens = len(sessions) * 3500  # ~3500 tokens average

    if dry_run:
        return json.dumps({
            "dry_run": True,
            "sessions_found": len(sessions),
            "estimated_cost": f"${estimated_cost:.2f}",
            "estimated_tokens": estimated_tokens,
            "sessions": [
                {
                    "path": str(s.file_path),
                    "modified": s.last_modified.isoformat(),
                    "messages": s.message_count,
                }
                for s in sessions[:10]  # Show first 10
            ],
            "message": "Run with dry_run=False to perform actual sync",
        })

    # Perform actual sync
    indexed_count = 0
    for session in sessions:
        try:
            # Parse, filter, and index session
            await _index_session(session)
            indexed_count += 1
        except Exception as e:
            logger.error(f"Failed to index session {session.file_path}: {e}")

    return json.dumps({
        "dry_run": False,
        "sessions_found": len(sessions),
        "sessions_indexed": indexed_count,
        "estimated_cost": f"${estimated_cost:.2f}",
        "actual_cost": f"${indexed_count * 0.17:.2f}",
    })


def _discover_sessions_for_sync(
    project: Optional[str],
    days: int,
    max_sessions: int,
) -> list[SessionState]:
    """Discover sessions for manual sync."""
    # Calculate cutoff time
    cutoff_time: Optional[float] = None
    if days > 0:
        cutoff_time = time.time() - (days * 24 * 60 * 60)

    # Determine watch paths
    if project:
        watch_paths = [Path(project)]
    else:
        watch_paths = [_session_manager.watch_path]

    # Discover sessions
    sessions = []
    for watch_path in watch_paths:
        for session_file in watch_path.glob("session_*.jsonl"):
            # Filter by modification time
            if cutoff_time:
                file_mtime = os.path.getmtime(session_file)
                if file_mtime < cutoff_time:
                    continue

            # Add session
            session_id = session_file.stem
            sessions.append(SessionState(
                session_id=session_id,
                file_path=session_file,
                last_modified=datetime.fromtimestamp(os.path.getmtime(session_file)),
                message_count=0,  # Will be calculated during indexing
            ))

    # Sort by modification time (newest first)
    sessions.sort(key=lambda s: s.last_modified, reverse=True)

    # Apply max session limit
    if len(sessions) > max_sessions:
        logger.warning(
            f"Found {len(sessions)} sessions, limiting to {max_sessions} (use --max-sessions to increase)"
        )
        sessions = sessions[:max_sessions]

    return sessions
```

**`mcp_server/session_tracking_cli.py`**:

Add CLI command:

```python
@cli.command()
@click.option("--project", type=str, default=None, help="Specific project path (default: all)")
@click.option("--days", type=int, default=7, help="Days to look back (0 = all history)")
@click.option("--max-sessions", type=int, default=100, help="Maximum sessions to sync")
@click.option("--dry-run", is_flag=True, default=True, help="Preview mode (default)")
@click.option("--confirm", is_flag=True, help="Required for --days 0 (all history)")
def sync(project: Optional[str], days: int, max_sessions: int, dry_run: bool, confirm: bool):
    """Manually sync historical sessions to Graphiti."""
    # Validate dangerous operations
    if days == 0 and not confirm:
        click.echo("❌ Error: --days 0 (all history) requires --confirm flag")
        click.echo("   This could index thousands of sessions and cost hundreds of dollars!")
        sys.exit(1)

    # Call MCP tool
    import asyncio
    result = asyncio.run(
        session_tracking_sync_history(
            project=project,
            days=days,
            max_sessions=max_sessions,
            dry_run=dry_run,
        )
    )

    # Parse and display results
    data = json.loads(result)

    if "error" in data:
        click.echo(f"❌ Error: {data['error']}")
        sys.exit(1)

    # Display table
    click.echo("\n📊 Session Sync Summary\n")
    click.echo(f"  Mode:             {'DRY RUN (preview)' if data['dry_run'] else 'ACTUAL SYNC'}")
    click.echo(f"  Sessions found:   {data['sessions_found']}")
    click.echo(f"  Estimated cost:   {data['estimated_cost']}")
    if not data['dry_run']:
        click.echo(f"  Sessions indexed: {data['sessions_indexed']}")
        click.echo(f"  Actual cost:      {data['actual_cost']}")

    if data['dry_run']:
        click.echo("\n💡 Tip: Run with --no-dry-run to perform actual sync")

    # Show sample sessions
    if "sessions" in data:
        click.echo("\n📄 Sample Sessions (first 10):\n")
        for session in data["sessions"]:
            click.echo(f"  {session['path']}")
            click.echo(f"    Modified: {session['modified']}, Messages: {session['messages']}")
```

### Testing Requirements

**Create**: `tests/session_tracking/test_manual_sync.py`

Test cases:
1. **Dry-run Mode**:
   - Returns preview without indexing
   - Shows session count and cost estimate
   - No sessions indexed

2. **Actual Sync**:
   - Indexes sessions correctly
   - Returns indexed count
   - Calculates actual cost

3. **Time Filtering**:
   - --days 7 filters correctly
   - --days 0 discovers all
   - Sessions sorted by modification time

4. **Safety Limits**:
   - max_sessions enforced
   - Warning logged when limit hit

5. **CLI Integration**:
   - Flags work correctly
   - Confirmation required for --days 0
   - Table output formatted

## Dependencies

- Story 12 (rolling period filter) - uses similar time-based logic

## Related Documents

- `.claude/handoff/session-tracking-complete-overhaul-2025-11-18.md` (Section: New Features - Feature 2)

## Cross-Cutting Requirements

See parent sprint `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`:
- Platform-agnostic paths: Use pathlib.Path
- Error handling: Comprehensive error handling for indexing
- Type hints: All parameters properly typed
- Testing: >80% coverage with CLI tests
- Performance: Efficient session discovery
- Security: Confirmation required for dangerous operations
