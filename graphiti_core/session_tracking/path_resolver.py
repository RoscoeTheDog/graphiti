"""Path resolution for Claude Code JSONL files.

This module handles mapping between Claude Code's project hash-based
directory structure and actual project paths.
"""

import hashlib
import logging
import os
import platform
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ClaudePathResolver:
    """Resolve Claude Code JSONL file paths.

    Claude Code stores session files in:
    ~/.claude/projects/{hash}/sessions/{session-id}.jsonl

    Where {hash} is a hash derived from the project path.
    """

    def __init__(self, claude_dir: Optional[Path] = None):
        """Initialize path resolver.

        Args:
            claude_dir: Path to Claude directory (defaults to ~/.claude)
        """
        self.claude_dir = claude_dir or self._default_claude_dir()
        self.projects_dir = self.claude_dir / "projects"
        self._hash_cache: Dict[str, str] = {}  # project_path -> hash

    def _default_claude_dir(self) -> Path:
        """Get default Claude directory path.

        Returns:
            Path to ~/.claude directory
        """
        home = Path.home()
        return home / ".claude"

    def get_project_hash(self, project_path: str) -> str:
        """Calculate project hash from project path.

        Claude Code uses a hash of the project path to create
        unique directory names for each project.

        Args:
            project_path: Absolute path to project directory

        Returns:
            8-character hash string
        """
        # Check cache first
        if project_path in self._hash_cache:
            return self._hash_cache[project_path]

        # Normalize path for consistent hashing
        normalized_path = self._normalize_path(project_path)

        # Calculate hash (using SHA256, taking first 8 chars)
        hash_obj = hashlib.sha256(normalized_path.encode("utf-8"))
        hash_str = hash_obj.hexdigest()[:8]

        # Cache result
        self._hash_cache[project_path] = hash_str

        return hash_str

    def _normalize_path(self, path: str) -> str:
        """Normalize path for cross-platform consistency.

        Args:
            path: Path to normalize

        Returns:
            Normalized path string
        """
        # Convert to Path object
        p = Path(path)

        # Resolve to absolute path
        try:
            p = p.resolve()
        except (OSError, RuntimeError):
            # If resolve fails, just make it absolute
            p = p.absolute()

        # Convert to POSIX format (forward slashes) for consistency
        path_str = p.as_posix()

        # Handle Windows paths - convert drive letters
        # C:/Users/... -> /c/Users/... (Git Bash style)
        if platform.system() == "Windows" and ":" in path_str:
            drive, rest = path_str.split(":", 1)
            path_str = f"/{drive.lower()}{rest}"

        return path_str

    def get_sessions_dir(self, project_path: str) -> Path:
        """Get sessions directory for a project.

        Args:
            project_path: Absolute path to project directory

        Returns:
            Path to sessions directory
        """
        project_hash = self.get_project_hash(project_path)
        return self.projects_dir / project_hash / "sessions"

    def get_session_file(self, project_path: str, session_id: str) -> Path:
        """Get path to a specific session JSONL file.

        Args:
            project_path: Absolute path to project directory
            session_id: Session ID (UUID)

        Returns:
            Path to session JSONL file
        """
        sessions_dir = self.get_sessions_dir(project_path)
        return sessions_dir / f"{session_id}.jsonl"

    def find_project_sessions(self, project_path: str) -> list[Path]:
        """Find all session files for a project.

        Args:
            project_path: Absolute path to project directory

        Returns:
            List of paths to session JSONL files
        """
        sessions_dir = self.get_sessions_dir(project_path)

        if not sessions_dir.exists():
            logger.debug(f"Sessions directory does not exist: {sessions_dir}")
            return []

        try:
            return sorted(sessions_dir.glob("*.jsonl"))
        except Exception as e:
            logger.error(f"Error finding session files in {sessions_dir}: {e}")
            return []

    def list_all_projects(self) -> Dict[str, Path]:
        """List all projects with sessions in Claude directory.

        Returns:
            Dictionary mapping project hash to sessions directory path
        """
        projects = {}

        if not self.projects_dir.exists():
            logger.warning(f"Projects directory does not exist: {self.projects_dir}")
            return projects

        try:
            for project_dir in self.projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                sessions_dir = project_dir / "sessions"
                if sessions_dir.exists():
                    projects[project_dir.name] = sessions_dir

        except Exception as e:
            logger.error(f"Error listing projects: {e}", exc_info=True)

        return projects

    def watch_all_projects(self) -> Path:
        """Get path to watch for all project sessions.

        Returns:
            Path to projects directory (for recursive watching)
        """
        return self.projects_dir

    def extract_session_id_from_path(self, file_path: Path) -> Optional[str]:
        """Extract session ID from a JSONL file path.

        Args:
            file_path: Path to session JSONL file

        Returns:
            Session ID (filename without .jsonl extension), or None if invalid
        """
        if file_path.suffix != ".jsonl":
            return None

        return file_path.stem

    def is_session_file(self, file_path: Path) -> bool:
        """Check if a path is a valid session JSONL file.

        Args:
            file_path: Path to check

        Returns:
            True if path appears to be a session file
        """
        # Must be a .jsonl file
        if file_path.suffix != ".jsonl":
            return False

        # Must be in a sessions/ subdirectory
        if file_path.parent.name != "sessions":
            return False

        # Must be in projects/ hierarchy
        try:
            # Check if 'projects' is in the path
            parts = file_path.parts
            return "projects" in parts
        except Exception:
            return False

    def resolve_project_from_session_file(self, file_path: Path) -> Optional[str]:
        """Attempt to resolve project hash from session file path.

        Args:
            file_path: Path to session JSONL file

        Returns:
            Project hash, or None if cannot be determined
        """
        try:
            parts = file_path.parts
            # Find 'projects' in path
            for i, part in enumerate(parts):
                if part == "projects" and i + 1 < len(parts):
                    # Next part should be the project hash
                    return parts[i + 1]
        except Exception as e:
            logger.warning(f"Error resolving project from path {file_path}: {e}")

        return None
