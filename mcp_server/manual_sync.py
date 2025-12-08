"""Manual session sync functionality for Graphiti MCP server.

This module provides tools for manually syncing historical sessions to Graphiti,
beyond the automatic rolling window discovery.

Supports resilience integration (Story 13.3) for graceful degradation when LLM
is unavailable - sessions are queued for retry instead of being lost.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from graphiti_core.session_tracking.filter import SessionFilter
from graphiti_core.session_tracking.indexer import SessionIndexer
from graphiti_core.session_tracking.parser import JSONLParser
from graphiti_core.session_tracking.session_manager import ActiveSession
from graphiti_core.session_tracking.types import ConversationContext, TokenUsage

if TYPE_CHECKING:
    from graphiti_core.session_tracking.resilient_indexer import ResilientSessionIndexer

logger = logging.getLogger(__name__)


async def session_tracking_sync_history(
    session_manager,
    graphiti_client,
    unified_config,
    project: str | None = None,
    days: int = 7,
    max_sessions: int = 100,
    dry_run: bool = True,
    resilient_indexer: Optional["ResilientSessionIndexer"] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> str:
    """Manually sync historical sessions to Graphiti.

    This tool allows users to index historical sessions beyond the automatic
    rolling window. Useful for one-time imports or catching up on missed sessions.

    Supports resilience integration (Story 13.3): when resilient_indexer is provided,
    sessions are indexed with graceful degradation - failed sessions are queued for
    retry instead of being lost.

    Args:
        session_manager: SessionManager instance
        graphiti_client: Graphiti client instance
        unified_config: Unified configuration
        project: Project path to sync (None = all projects in watch_path)
        days: Number of days to look back (0 = all history, use with caution)
        max_sessions: Maximum sessions to sync (safety limit, default 100)
        dry_run: Preview mode without actual indexing (default: True)
        resilient_indexer: Optional ResilientSessionIndexer for graceful degradation.
            When provided, failed sessions are queued for retry instead of lost.
        progress_callback: Optional callback(current, total) for progress tracking.
            Called after each session is processed.

    Returns:
        JSON string with sync results:
        - dry_run mode: Preview with session list and cost estimate
        - actual sync: Indexed count, actual cost, and degradation status

    Examples:
        # Preview last 7 days (default)
        result = await session_tracking_sync_history(...)

        # Preview last 30 days
        result = await session_tracking_sync_history(days=30, ...)

        # Actually sync last 7 days
        result = await session_tracking_sync_history(dry_run=False, ...)

        # Sync with resilience (graceful degradation)
        result = await session_tracking_sync_history(
            dry_run=False,
            resilient_indexer=resilient_indexer,
            progress_callback=lambda cur, total: print(f"{cur}/{total}"),
        )
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
        queued_for_retry = 0
        failed_count = 0
        degradation_level = "full"  # Default if no resilient_indexer

        # Get initial degradation level if using resilient indexer
        if resilient_indexer is not None:
            degradation_level = resilient_indexer.get_degradation_level().name.lower()

        total_sessions = len(sessions)
        for idx, session in enumerate(sessions):
            try:
                result = await index_session_sync(
                    session=session,
                    graphiti_client=graphiti_client,
                    unified_config=unified_config,
                    resilient_indexer=resilient_indexer,
                )

                # Track results based on resilient indexer response
                if result.get("success"):
                    indexed_count += 1
                if result.get("queued_for_retry"):
                    queued_for_retry += 1
                if result.get("degraded"):
                    degradation_level = result.get("degradation_level", degradation_level)

            except Exception as e:
                logger.error(f"Failed to index session {session.file_path}: {e}", exc_info=True)
                failed_count += 1

            # Progress callback
            if progress_callback:
                try:
                    progress_callback(idx + 1, total_sessions)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")

        actual_cost = indexed_count * 0.17

        # Get final degradation level
        if resilient_indexer is not None:
            degradation_level = resilient_indexer.get_degradation_level().name.lower()

        response = {
            "status": "success",
            "dry_run": False,
            "sessions_found": total_sessions,
            "sessions_indexed": indexed_count,
            "sessions_failed": failed_count,
            "estimated_cost": f"${estimated_cost:.2f}",
            "actual_cost": f"${actual_cost:.2f}",
        }

        # Add resilience-specific fields when using resilient indexer
        if resilient_indexer is not None:
            response["resilience_enabled"] = True
            response["degradation_level"] = degradation_level
            response["sessions_queued_for_retry"] = queued_for_retry
            response["llm_available"] = degradation_level == "full"
        else:
            response["resilience_enabled"] = False

        return json.dumps(response, indent=2)

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
    resilient_indexer: Optional["ResilientSessionIndexer"] = None,
) -> dict[str, Any]:
    """Index a single session to Graphiti.

    Supports resilience integration: when resilient_indexer is provided, uses it
    for graceful degradation. Failed sessions are queued for retry instead of lost.

    Args:
        session: ActiveSession to index
        graphiti_client: Graphiti client instance
        unified_config: Unified configuration
        resilient_indexer: Optional ResilientSessionIndexer for graceful degradation

    Returns:
        Dict with indexing result:
            - success: bool - Whether indexing succeeded
            - degraded: bool - Whether degraded mode was used
            - queued_for_retry: bool - Whether queued for retry
            - degradation_level: str - Current degradation level
            - error: str | None - Error message if failed

    Raises:
        RuntimeError: If neither graphiti_client nor resilient_indexer is available
    """
    if graphiti_client is None and resilient_indexer is None:
        raise RuntimeError("Either graphiti_client or resilient_indexer must be provided")

    # Default result
    result: dict[str, Any] = {
        "success": False,
        "degraded": False,
        "queued_for_retry": False,
        "degradation_level": "full",
        "error": None,
    }

    # Parse session file
    parser = JSONLParser()
    messages, last_offset = parser.parse_file(session.file_path, offset=0)

    if not messages:
        logger.warning(f"No messages found in {session.file_path}")
        result["success"] = True  # Empty session is not an error
        return result

    # Filter messages
    filter_config = unified_config.session_tracking.filter if unified_config.session_tracking.filter else None
    session_filter = SessionFilter(config=filter_config)
    filtered_messages = await session_filter.filter_conversation(messages)

    # Build filtered content string for resilient indexer
    filtered_content = "\n\n".join([
        f"[{msg.role}]: {msg.content}" for msg in filtered_messages if msg.content
    ])

    # Use resilient indexer if available
    if resilient_indexer is not None:
        # Get group_id from session path (project hash)
        group_id = session.project_hash

        indexer_result = await resilient_indexer.index_session(
            session_id=session.session_id,
            filtered_content=filtered_content,
            group_id=group_id,
            session_file=str(session.file_path),
        )

        result["success"] = indexer_result.get("success", False)
        result["degraded"] = indexer_result.get("degraded", False)
        result["queued_for_retry"] = indexer_result.get("queued_for_retry", False)
        result["degradation_level"] = resilient_indexer.get_degradation_level().name.lower()
        result["error"] = indexer_result.get("error")

        logger.info(
            f"Indexed session {session.session_id} via resilient indexer: "
            f"success={result['success']}, degraded={result['degraded']}, "
            f"queued={result['queued_for_retry']}"
        )
        return result

    # Fallback to direct SessionIndexer
    # Create conversation context
    context = ConversationContext(
        session_id=session.session_id,
        project_path=str(session.file_path.parent.parent),  # Go up from sessions/hash/ to project root
        messages=filtered_messages,
        total_tokens=TokenUsage(input_tokens=0, output_tokens=0),
        mcp_tools_used=[],
        files_modified=[],
    )

    # Index to Graphiti using direct SessionIndexer
    indexer = SessionIndexer(graphiti_client)
    await indexer.index_session(context)

    result["success"] = True
    logger.info(
        f"Indexed session {session.session_id}: "
        f"{len(filtered_messages)} messages from {session.file_path}"
    )
    return result
