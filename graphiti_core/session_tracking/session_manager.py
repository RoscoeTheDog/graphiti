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
        message_count: Total messages processed
    """

    session_id: str
    file_path: Path
    project_hash: str
    offset: int = 0
    last_modified: float = field(default_factory=time.time)
    message_count: int = 0


class SessionManager:
    """Manage Claude Code session lifecycle.

    This class orchestrates session tracking:
    - Maintains registry of active sessions
    - Detects new sessions and session updates
    - Handles auto-compaction (new JSONL = continuation)
    - Triggers summarization on session close
    """

    def __init__(
        self,
        path_resolver: ClaudePathResolver,
        on_session_closed: Optional[Callable[[str, Path, ConversationContext], None]] = None,
    ):
        """Initialize session manager.

        Args:
            path_resolver: Path resolver for Claude directories
            on_session_closed: Callback when session closes (session_id, file_path, context)
        """
        self.path_resolver = path_resolver
        self.on_session_closed = on_session_closed

        # Active session registry
        self.active_sessions: Dict[str, ActiveSession] = {}

        # Parser for reading JSONL files
        self.parser = JSONLParser()

        self._is_running = False

    def start(self) -> None:
        """Start session monitoring.

        This starts session tracking without file watcher.
        Sessions are tracked via turn-based processing.
        """
        if self._is_running:
            logger.warning("Session manager already running")
            return

        logger.info("Starting session manager...")

        self._is_running = True
        logger.info("Session manager started successfully")

    def stop(self) -> None:
        """Stop session monitoring.

        This closes all active sessions.
        """
        if not self._is_running:
            logger.warning("Session manager not running")
            return

        logger.info("Stopping session manager...")

        # Close all active sessions
        for session_id in list(self.active_sessions.keys()):
            self._close_session(session_id, reason="shutdown")

        self._is_running = False
        logger.info("Session manager stopped")

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
