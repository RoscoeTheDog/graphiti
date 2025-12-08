"""File watcher for Claude Code session JSONL files.

This module uses watchdog to monitor session files and trigger callbacks
when sessions are created or modified.

Platform Handling:
- All file paths use pathlib.Path (automatic platform handling)
- Return values use native OS path format
"""

import logging
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class SessionFileEventHandler(FileSystemEventHandler):
    """Handle file system events for session JSONL files.

    This handler filters events to only process .jsonl files in sessions/
    directories and triggers callbacks for new sessions and session updates.
    """

    def __init__(
        self,
        on_session_created: Optional[Callable[[Path], None]] = None,
        on_session_modified: Optional[Callable[[Path], None]] = None,
        on_session_deleted: Optional[Callable[[Path], None]] = None,
    ):
        """Initialize session file event handler.

        Args:
            on_session_created: Callback for new session files (path)
            on_session_modified: Callback for modified session files (path)
            on_session_deleted: Callback for deleted session files (path)
        """
        super().__init__()
        self.on_session_created = on_session_created
        self.on_session_modified = on_session_modified
        self.on_session_deleted = on_session_deleted

    def _is_session_file(self, file_path: Path) -> bool:
        """Check if path is a valid session JSONL file.

        Args:
            file_path: Path to check

        Returns:
            True if path is a session JSONL file
        """
        # Must be a .jsonl file
        if file_path.suffix != ".jsonl":
            return False

        # Must be in a sessions/ directory
        if file_path.parent.name != "sessions":
            return False

        # Must be in projects/ hierarchy
        try:
            parts = file_path.parts
            return "projects" in parts
        except Exception:
            return False

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file created event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if not self._is_session_file(file_path):
            return

        logger.info(f"New session file detected: {file_path}")

        if self.on_session_created:
            try:
                self.on_session_created(file_path)
            except Exception as e:
                logger.error(f"Error in session created callback: {e}", exc_info=True)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modified event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if not self._is_session_file(file_path):
            return

        logger.debug(f"Session file modified: {file_path}")

        if self.on_session_modified:
            try:
                self.on_session_modified(file_path)
            except Exception as e:
                logger.error(f"Error in session modified callback: {e}", exc_info=True)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deleted event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if not self._is_session_file(file_path):
            return

        logger.info(f"Session file deleted: {file_path}")

        if self.on_session_deleted:
            try:
                self.on_session_deleted(file_path)
            except Exception as e:
                logger.error(f"Error in session deleted callback: {e}", exc_info=True)


class SessionFileWatcher:
    """Watch for Claude Code session JSONL file changes.

    This class uses watchdog to monitor the Claude projects directory
    for session file changes and trigger callbacks.
    """

    def __init__(
        self,
        watch_path: Path,
        on_session_created: Optional[Callable[[Path], None]] = None,
        on_session_modified: Optional[Callable[[Path], None]] = None,
        on_session_deleted: Optional[Callable[[Path], None]] = None,
    ):
        """Initialize session file watcher.

        Args:
            watch_path: Path to watch (usually ~/.claude/projects/)
            on_session_created: Callback for new session files
            on_session_modified: Callback for modified session files
            on_session_deleted: Callback for deleted session files
        """
        self.watch_path = watch_path
        self.event_handler = SessionFileEventHandler(
            on_session_created=on_session_created,
            on_session_modified=on_session_modified,
            on_session_deleted=on_session_deleted,
        )
        self.observer: Optional[Observer] = None
        self._is_running = False

    def start(self) -> None:
        """Start watching for file changes.

        This method starts the watchdog observer in a background thread.
        """
        if self._is_running:
            logger.warning("Watcher already running")
            return

        if not self.watch_path.exists():
            logger.warning(f"Watch path does not exist: {self.watch_path}")
            logger.info("Creating watch path...")
            try:
                self.watch_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create watch path: {e}", exc_info=True)
                raise

        logger.info(f"Starting file watcher on: {self.watch_path}")

        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.watch_path),
            recursive=True
        )
        self.observer.start()
        self._is_running = True

        logger.info("File watcher started successfully")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop watching for file changes.

        Args:
            timeout: Maximum time to wait for observer to stop (seconds)
        """
        if not self._is_running:
            logger.warning("Watcher not running")
            return

        logger.info("Stopping file watcher...")

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=timeout)
            self.observer = None

        self._is_running = False
        logger.info("File watcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is currently running.

        Returns:
            True if watcher is active
        """
        return self._is_running

    def __enter__(self) -> "SessionFileWatcher":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
