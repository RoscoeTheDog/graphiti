"""Manual session sync functionality for Graphiti MCP server.

This module provides tools for manually syncing historical sessions to Graphiti,
beyond the automatic rolling window discovery.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from graphiti_core.session_tracking.filter import SessionFilter
from graphiti_core.session_tracking.indexer import SessionIndexer
from graphiti_core.session_tracking.parser import JSONLParser
from graphiti_core.session_tracking.session_manager import ActiveSession
from graphiti_core.session_tracking.types import ConversationContext, TokenUsage

logger = logging.getLogger(__name__)


async def session_tracking_sync_history(
    session_manager,
    graphiti_client,
    unified_config,
    project: str | None = None,
    days: int = 7,
    max_sessions: int = 100,
    dry_run: bool = True,
) -> str:
    """Manually sync historical sessions to Graphiti.

    This tool allows users to index historical sessions beyond the automatic
    rolling window. Useful for one-time imports or catching up on missed sessions.

    Args:
        session_manager: SessionManager instance
        graphiti_client: Graphiti client instance
        unified_config: Unified configuration
        project: Project path to sync (None = all projects in watch_path)
        days: Number of days to look back (0 = all history, use with caution)
        max_sessions: Maximum sessions to sync (safety limit, default 100)
        dry_run: Preview mode without actual indexing (default: True)

    Returns:
        JSON string with sync results:
        - dry_run mode: Preview with session list and cost estimate
        - actual sync: Indexed count and actual cost

    Examples:
        # Preview last 7 days (default)
        result = await session_tracking_sync_history(...)

        # Preview last 30 days
        result = await session_tracking_sync_history(days=30, ...)

        # Actually sync last 7 days
        result = await session_tracking_sync_history(dry_run=False, ...)
    """
    try:
        if session_manager is None:
            return json.dumps({
                "status": "error",
                "error": "Session tracking not initialized. Enable session tracking first."
            })

        # Discover sessions for sync
        sessions = discover_sessions_for_sync(
            session_manager=session_manager,
            project=project,
            days=days,
            max_sessions=max_sessions,
        )

        # Calculate cost estimates
        estimated_cost = len(sessions) * 0.17  # $0.17 average per session
        estimated_tokens = len(sessions) * 3500  # ~3500 tokens average

        # Dry-run mode: return preview without indexing
        if dry_run:
            session_previews = []
            for session in sessions[:10]:  # Show first 10
                try:
                    # Get message count by parsing session
                    parser = JSONLParser()
                    messages, _ = parser.parse_file(session.file_path)
                    message_count = len(messages)
                except Exception as e:
                    logger.warning(f"Could not parse {session.file_path} for preview: {e}")
                    message_count = 0

                session_previews.append({
                    "path": str(session.file_path),
                    "modified": datetime.fromtimestamp(session.last_modified).isoformat(),
                    "messages": message_count,
                })

            return json.dumps({
                "status": "success",
                "dry_run": True,
                "sessions_found": len(sessions),
                "estimated_cost": f"${estimated_cost:.2f}",
                "estimated_tokens": estimated_tokens,
                "sessions": session_previews,
                "message": "Run with dry_run=False to perform actual sync"
            }, indent=2)

        # Actual sync mode: parse, filter, and index sessions
        indexed_count = 0
        for session in sessions:
            try:
                await index_session_sync(
                    session=session,
                    graphiti_client=graphiti_client,
                    unified_config=unified_config,
                )
                indexed_count += 1
            except Exception as e:
                logger.error(f"Failed to index session {session.file_path}: {e}", exc_info=True)

        actual_cost = indexed_count * 0.17

        return json.dumps({
            "status": "success",
            "dry_run": False,
            "sessions_found": len(sessions),
            "sessions_indexed": indexed_count,
            "estimated_cost": f"${estimated_cost:.2f}",
            "actual_cost": f"${actual_cost:.2f}",
        }, indent=2)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error syncing session history: {error_msg}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Failed to sync sessions: {error_msg}"
        })


def discover_sessions_for_sync(
    session_manager,
    project: str | None,
    days: int,
    max_sessions: int,
) -> list[ActiveSession]:
    """Discover sessions for manual sync.

    Args:
        session_manager: SessionManager instance
        project: Specific project path to sync (None = all projects)
        days: Days to look back (0 = all history)
        max_sessions: Maximum number of sessions to return

    Returns:
        List of ActiveSession objects sorted by modification time (newest first)
    """
    if session_manager is None:
        return []

    # Calculate cutoff time
    cutoff_time: float | None = None
    if days > 0:
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        cutoff_dt = datetime.fromtimestamp(cutoff_time)
        logger.info(f"Discovering sessions from last {days} days (cutoff: {cutoff_dt})")
    else:
        logger.info("Discovering ALL historical sessions (no time filter)")

    # Determine watch paths
    if project:
        # Specific project: find its hash
        project_path = Path(project)
        project_hash = session_manager.path_resolver.get_project_hash(project_path)
        projects = {project_hash: session_manager.path_resolver.get_sessions_dir(project_hash)}
    else:
        # All projects
        projects = session_manager.path_resolver.list_all_projects()

    # Discover sessions
    sessions: list[ActiveSession] = []
    for project_hash, sessions_dir in projects.items():
        try:
            for session_file in sessions_dir.glob("*.jsonl"):
                # Filter by modification time
                try:
                    file_mtime = os.path.getmtime(session_file)
                    if cutoff_time is not None and file_mtime < cutoff_time:
                        continue  # Skip old sessions
                except OSError as e:
                    logger.warning(f"Could not get modification time for {session_file}: {e}")
                    continue

                # Create ActiveSession
                session_id = session_manager.path_resolver.extract_session_id_from_path(session_file)
                if session_id:
                    sessions.append(ActiveSession(
                        session_id=session_id,
                        file_path=session_file,
                        project_hash=project_hash,
                        offset=0,
                        last_modified=file_mtime,
                        last_activity=file_mtime,
                        message_count=0,
                    ))
        except Exception as e:
            logger.error(f"Error discovering sessions in {sessions_dir}: {e}", exc_info=True)

    # Sort by modification time (newest first)
    sessions.sort(key=lambda s: s.last_modified, reverse=True)

    # Apply max session limit
    if len(sessions) > max_sessions:
        logger.warning(
            f"Found {len(sessions)} sessions, limiting to {max_sessions} "
            f"(increase --max-sessions to sync more)"
        )
        sessions = sessions[:max_sessions]

    logger.info(f"Discovered {len(sessions)} sessions for sync")
    return sessions


async def index_session_sync(
    session: ActiveSession,
    graphiti_client,
    unified_config,
) -> None:
    """Index a single session to Graphiti.

    Args:
        session: ActiveSession to index
        graphiti_client: Graphiti client instance
        unified_config: Unified configuration

    Raises:
        Exception: If parsing, filtering, or indexing fails
    """
    if graphiti_client is None:
        raise RuntimeError("Graphiti client not initialized")

    # Parse session file
    parser = JSONLParser()
    messages, last_offset = parser.parse_file(session.file_path, offset=0)

    if not messages:
        logger.warning(f"No messages found in {session.file_path}")
        return

    # Filter messages
    filter_config = unified_config.session_tracking.filter if unified_config.session_tracking.filter else None
    session_filter = SessionFilter(config=filter_config)
    filtered_messages = await session_filter.filter_conversation(messages)

    # Create conversation context
    context = ConversationContext(
        session_id=session.session_id,
        project_path=str(session.file_path.parent.parent),  # Go up from sessions/hash/ to project root
        messages=filtered_messages,
        total_tokens=TokenUsage(input_tokens=0, output_tokens=0),
        mcp_tools_used=[],
        files_modified=[],
    )

    # Index to Graphiti
    indexer = SessionIndexer(graphiti_client)
    await indexer.index_session(context)

    logger.info(
        f"Indexed session {session.session_id}: "
        f"{len(filtered_messages)} messages from {session.file_path}"
    )
