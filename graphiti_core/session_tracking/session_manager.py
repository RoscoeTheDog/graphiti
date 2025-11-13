"""Session lifecycle management for Claude Code sessions.

This module tracks active sessions, detects session close events,
and triggers summarization when sessions end.

Platform Handling:
- All file paths use pathlib.Path (automatic platform handling)
- Session IDs are platform-agnostic (UUID strings)
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

from .parser import JSONLParser
from .path_resolver import ClaudePathResolver
from .types import ConversationContext, SessionMessage, TokenUsage
from .watcher import SessionFileWatcher

logger = logging.getLogger(__name__)


@dataclass
class ActiveSession:
    """Represents an active session being tracked.

    Attributes:
        session_id: Unique session ID (from filename)
        file_path: Path to session JSONL file
        project_hash: Project hash (from directory structure)
        offset: Current read offset in file (bytes)
        last_modified: Last modification timestamp
        last_activity: Last activity timestamp (for inactivity detection)
        message_count: Total messages processed
    """

    session_id: str
    file_path: Path
    project_hash: str
    offset: int = 0
    last_modified: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    message_count: int = 0


class SessionManager:
    """Manage Claude Code session lifecycle.

    This class orchestrates session tracking:
    - Maintains registry of active sessions
    - Detects new sessions and session updates
    - Tracks inactivity and triggers session close
    - Handles auto-compaction (new JSONL = continuation)
    - Triggers summarization on session close
    """

    def __init__(
        self,
        path_resolver: ClaudePathResolver,
        inactivity_timeout: int = 300,  # 5 minutes
        on_session_closed: Optional[Callable[[str, Path, ConversationContext], None]] = None,
    ):
        """Initialize session manager.

        Args:
            path_resolver: Path resolver for Claude directories
            inactivity_timeout: Seconds of inactivity before closing session
            on_session_closed: Callback when session closes (session_id, file_path, context)
        """
        self.path_resolver = path_resolver
        self.inactivity_timeout = inactivity_timeout
        self.on_session_closed = on_session_closed

        # Active session registry
        self.active_sessions: Dict[str, ActiveSession] = {}

        # Parser for reading JSONL files
        self.parser = JSONLParser()

        # File watcher
        watch_path = path_resolver.watch_all_projects()
        self.watcher = SessionFileWatcher(
            watch_path=watch_path,
            on_session_created=self._handle_session_created,
            on_session_modified=self._handle_session_modified,
            on_session_deleted=self._handle_session_deleted,
        )

        self._is_running = False

    def start(self) -> None:
        """Start session monitoring.

        This starts the file watcher and begins tracking sessions.
        """
        if self._is_running:
            logger.warning("Session manager already running")
            return

        logger.info("Starting session manager...")

        # Start file watcher
        self.watcher.start()

        # Discover existing sessions
        self._discover_existing_sessions()

        self._is_running = True
        logger.info("Session manager started successfully")

    def stop(self) -> None:
        """Stop session monitoring.

        This stops the file watcher and closes all active sessions.
        """
        if not self._is_running:
            logger.warning("Session manager not running")
            return

        logger.info("Stopping session manager...")

        # Stop file watcher
        self.watcher.stop()

        # Close all active sessions
        for session_id in list(self.active_sessions.keys()):
            self._close_session(session_id, reason="shutdown")

        self._is_running = False
        logger.info("Session manager stopped")

    def check_inactive_sessions(self) -> int:
        """Check for inactive sessions and close them.

        Returns:
            Number of sessions closed due to inactivity
        """
        current_time = time.time()
        closed_count = 0

        for session_id, session in list(self.active_sessions.items()):
            inactive_duration = current_time - session.last_activity

            if inactive_duration > self.inactivity_timeout:
                logger.info(
                    f"Session {session_id} inactive for {inactive_duration:.0f}s, closing..."
                )
                self._close_session(session_id, reason="inactivity")
                closed_count += 1

        return closed_count

    def get_active_session_count(self) -> int:
        """Get number of active sessions.

        Returns:
            Number of sessions currently being tracked
        """
        return len(self.active_sessions)

    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is currently active.

        Args:
            session_id: Session ID to check

        Returns:
            True if session is active
        """
        return session_id in self.active_sessions

    def _discover_existing_sessions(self) -> None:
        """Discover existing session files and start tracking them.

        This scans the projects directory for existing .jsonl files.
        """
        logger.info("Discovering existing sessions...")

        projects = self.path_resolver.list_all_projects()
        discovered_count = 0

        for project_hash, sessions_dir in projects.items():
            try:
                for session_file in sessions_dir.glob("*.jsonl"):
                    session_id = self.path_resolver.extract_session_id_from_path(session_file)

                    if session_id and session_id not in self.active_sessions:
                        self._start_tracking_session(session_file, project_hash)
                        discovered_count += 1

            except Exception as e:
                logger.error(
                    f"Error discovering sessions in {sessions_dir}: {e}",
                    exc_info=True
                )

        logger.info(f"Discovered {discovered_count} existing sessions")

    def _handle_session_created(self, file_path: Path) -> None:
        """Handle new session file created.

        Args:
            file_path: Path to new session file
        """
        session_id = self.path_resolver.extract_session_id_from_path(file_path)
        if not session_id:
            logger.warning(f"Could not extract session ID from: {file_path}")
            return

        # Check if this is a compaction continuation
        # (new JSONL file created = Claude Code compaction)
        # In this case, we treat it as a continuation, not a new session
        # For now, we just start tracking it as a new session
        # Future: detect parent session and link them

        project_hash = self.path_resolver.resolve_project_from_session_file(file_path)
        if not project_hash:
            logger.warning(f"Could not resolve project hash from: {file_path}")
            return

        logger.info(f"New session created: {session_id} (project: {project_hash})")
        self._start_tracking_session(file_path, project_hash)

    def _handle_session_modified(self, file_path: Path) -> None:
        """Handle session file modified.

        Args:
            file_path: Path to modified session file
        """
        session_id = self.path_resolver.extract_session_id_from_path(file_path)
        if not session_id:
            return

        session = self.active_sessions.get(session_id)
        if not session:
            # Session not tracked yet, start tracking
            project_hash = self.path_resolver.resolve_project_from_session_file(file_path)
            if project_hash:
                self._start_tracking_session(file_path, project_hash)
            return

        # Read new messages from file
        try:
            self._read_new_messages(session)
        except Exception as e:
            logger.error(f"Error reading messages from {file_path}: {e}", exc_info=True)

    def _handle_session_deleted(self, file_path: Path) -> None:
        """Handle session file deleted.

        Args:
            file_path: Path to deleted session file
        """
        session_id = self.path_resolver.extract_session_id_from_path(file_path)
        if not session_id:
            return

        logger.info(f"Session file deleted: {session_id}")

        if session_id in self.active_sessions:
            self._close_session(session_id, reason="deleted")

    def _start_tracking_session(self, file_path: Path, project_hash: str) -> None:
        """Start tracking a new session.

        Args:
            file_path: Path to session file
            project_hash: Project hash
        """
        session_id = self.path_resolver.extract_session_id_from_path(file_path)
        if not session_id:
            return

        session = ActiveSession(
            session_id=session_id,
            file_path=file_path,
            project_hash=project_hash,
            offset=0,
            last_modified=time.time(),
            last_activity=time.time(),
            message_count=0,
        )

        self.active_sessions[session_id] = session

        # Read initial messages
        try:
            self._read_new_messages(session)
        except Exception as e:
            logger.error(f"Error reading initial messages from {file_path}: {e}", exc_info=True)

    def _read_new_messages(self, session: ActiveSession) -> None:
        """Read new messages from a session file.

        Args:
            session: Active session to read from
        """
        if not session.file_path.exists():
            logger.warning(f"Session file does not exist: {session.file_path}")
            return

        try:
            # Read new messages from offset
            new_messages, new_offset = self.parser.parse_file(
                str(session.file_path),
                start_offset=session.offset
            )

            if new_messages:
                session.offset = new_offset
                session.last_modified = time.time()
                session.last_activity = time.time()
                session.message_count += len(new_messages)

                logger.debug(
                    f"Session {session.session_id}: read {len(new_messages)} new messages "
                    f"(total: {session.message_count})"
                )

        except Exception as e:
            logger.error(f"Error parsing messages from {session.file_path}: {e}", exc_info=True)
            raise

    def _close_session(self, session_id: str, reason: str = "unknown") -> None:
        """Close a session and trigger summarization.

        Args:
            session_id: Session ID to close
            reason: Reason for closing (for logging)
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"Attempted to close non-existent session: {session_id}")
            return

        logger.info(
            f"Closing session {session_id} (reason: {reason}, "
            f"messages: {session.message_count})"
        )

        # Read final state
        try:
            self._read_new_messages(session)
        except Exception as e:
            logger.error(f"Error reading final state for {session_id}: {e}")

        # Build conversation context
        try:
            # Re-parse entire file to build context
            all_messages, _ = self.parser.parse_file(str(session.file_path), start_offset=0)

            # Calculate total tokens
            total_tokens = TokenUsage(
                input_tokens=sum(msg.tokens.input_tokens for msg in all_messages),
                output_tokens=sum(msg.tokens.output_tokens for msg in all_messages),
                cache_read_tokens=sum(msg.tokens.cache_read_tokens for msg in all_messages),
                cache_creation_tokens=sum(msg.tokens.cache_creation_tokens for msg in all_messages)
            )

            # Build context
            context = ConversationContext(
                session_id=session_id,
                messages=all_messages,
                total_tokens=total_tokens
            )

            # Trigger summarization callback
            if self.on_session_closed:
                try:
                    self.on_session_closed(session_id, session.file_path, context)
                except Exception as e:
                    logger.error(
                        f"Error in session closed callback for {session_id}: {e}",
                        exc_info=True
                    )

        except Exception as e:
            logger.error(f"Error building context for {session_id}: {e}", exc_info=True)

        # Remove from active sessions
        del self.active_sessions[session_id]

    def __enter__(self) -> "SessionManager":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
