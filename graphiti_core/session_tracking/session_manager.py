"""Session lifecycle management for Claude Code sessions.

This module tracks active sessions, detects session close events,
and triggers summarization when sessions end.

Platform Handling:
- All file paths use pathlib.Path (automatic platform handling)
- Session IDs are platform-agnostic (UUID strings)
"""

import fnmatch
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
        excluded_paths: Optional[list[str]] = None,
        watch_path: Optional[Path] = None,
    ):
        """Initialize session manager.

        Args:
            path_resolver: Path resolver for Claude directories
            on_session_closed: Callback when session closes (session_id, file_path, context)
            excluded_paths: List of paths to exclude from tracking (supports glob patterns)
            watch_path: Watch path for relative path resolution
        """
        self.path_resolver = path_resolver
        self.on_session_closed = on_session_closed
        self.excluded_paths = excluded_paths or []
        self.watch_path = watch_path

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

        # Log excluded paths configuration
        if self.excluded_paths:
            logger.info(f"Session tracking excluded paths: {self.excluded_paths}")

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

    def _glob_match_recursive(self, path_parts: list[str], pattern_parts: list[str]) -> bool:
        """Match path parts against glob pattern parts with ** support.

        This helper implements proper recursive glob matching for ** patterns,
        which match zero or more directories.

        Args:
            path_parts: Path split into directory components (e.g., ['projects', 'temporal-server', 'logs'])
            pattern_parts: Pattern split into components (e.g., ['**', 'temporal-*', '**'])

        Returns:
            True if path matches pattern with proper ** semantics, False otherwise

        Examples:
            ['temporal-server', 'logs'] matches ['**', 'temporal-*', '**']
            ['projects', 'temporal-server', 'logs'] matches ['**', 'temporal-*', '**']
            ['temporal-server'] does NOT match ['**', 'temporal-*', '**'] (needs directory after)
        """
        # Base cases
        if not pattern_parts:
            return not path_parts  # Both empty = match
        if not path_parts:
            # Path empty but pattern remains - only matches if pattern is all **
            return all(p == '**' for p in pattern_parts)

        pattern_head = pattern_parts[0]
        pattern_tail = pattern_parts[1:]

        if pattern_head == '**':
            # ** matches zero or more directories
            # Try matching with zero directories (skip ** and continue)
            if self._glob_match_recursive(path_parts, pattern_tail):
                return True
            # Try matching with one or more directories (consume one path part and keep **)
            if path_parts:
                return self._glob_match_recursive(path_parts[1:], pattern_parts)
            return False
        else:
            # Non-** pattern: must match current path part
            if path_parts and fnmatch.fnmatch(path_parts[0], pattern_head):
                return self._glob_match_recursive(path_parts[1:], pattern_tail)
            return False

    def _is_path_excluded(self, session_path: Path) -> bool:
        """Check if session path matches any exclusion pattern.

        Uses platform-agnostic path matching with support for:
        - Absolute paths (exact match with directory boundary checking)
        - Relative paths (relative to watch_path)
        - Glob patterns with ** support (e.g., **/temporal-*/**)

        Args:
            session_path: Path to session file to check

        Returns:
            True if path matches any exclusion pattern
        """
        if not self.excluded_paths:
            return False

        # Normalize session path for comparison (convert to Path if string)
        session_path = Path(session_path)

        # Normalize paths to UNIX format for consistent comparison
        normalized_session = self.path_resolver._normalize_path_for_hash(str(session_path))

        for pattern in self.excluded_paths:
            # Check if pattern is absolute by looking at original pattern string
            # (before normalization which might add drive letters on Windows)
            is_absolute = pattern.startswith('/') or (len(pattern) > 1 and pattern[1] == ':')

            if is_absolute:
                # Normalize pattern for consistent comparison
                normalized_pattern = self.path_resolver._normalize_path_for_hash(pattern)
                # Absolute path: match with directory boundary checking
                # This prevents /projects/temporal-server from matching /projects/temporal-server-2
                pattern_with_boundary = normalized_pattern.rstrip('/') + '/'
                session_with_boundary = normalized_session.rstrip('/') + '/'

                # Check exact match or prefix match with directory boundary
                if normalized_session == normalized_pattern or session_with_boundary.startswith(pattern_with_boundary):
                    return True
            else:
                # Relative path or glob: resolve relative to watch_path
                if self.watch_path:
                    try:
                        watch_normalized = self.path_resolver._normalize_path_for_hash(str(self.watch_path))
                        if normalized_session.startswith(watch_normalized):
                            # Get relative part
                            relative_session = normalized_session[len(watch_normalized):].lstrip('/')

                            # Check if pattern contains ** (recursive wildcard)
                            if '**' in pattern:
                                # Use custom recursive matching for ** patterns
                                path_parts = relative_session.split('/')
                                pattern_parts = pattern.split('/')
                                if self._glob_match_recursive(path_parts, pattern_parts):
                                    return True
                            elif '*' in pattern or '?' in pattern:
                                # Glob pattern with wildcards - use fnmatch
                                if fnmatch.fnmatch(relative_session, pattern):
                                    return True
                            else:
                                # Simple directory name - check if it's a prefix
                                # "temporal-server" should match "temporal-server/session.jsonl"
                                pattern_with_boundary = pattern.rstrip('/') + '/'
                                relative_with_boundary = relative_session.rstrip('/') + '/'
                                if relative_session == pattern or relative_with_boundary.startswith(pattern_with_boundary):
                                    return True
                    except (ValueError, OSError):
                        # If relative path calculation fails, skip this pattern
                        pass

        return False

    def _start_tracking_session(self, file_path: Path, project_hash: str) -> None:
        """Start tracking a new session.

        Args:
            file_path: Path to session file
            project_hash: Project hash
        """
        # Check if path is excluded before processing
        if self._is_path_excluded(file_path):
            logger.debug(f"Skipping excluded path: {file_path}")
            return

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
