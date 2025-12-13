"""Path resolution for Claude Code JSONL files.

This module handles mapping between Claude Code's project hash-based
directory structure and actual project paths.

Platform Handling:
- Hashing: Always uses normalized UNIX-style paths for consistency
- Return values: Uses native OS path format (Windows: C:\\..., Unix: /...)
"""

import hashlib
import logging
import os
import platform
import re
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
        self._reverse_hash_cache: Dict[str, str] = {}  # hash -> project_path

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
            project_path: Absolute path to project directory (any format)

        Returns:
            8-character hash string
        """
        # Check cache first
        if project_path in self._hash_cache:
            return self._hash_cache[project_path]

        # Normalize path for consistent hashing (always UNIX format)
        normalized_path = self._normalize_path_for_hash(project_path)

        # Calculate hash (using SHA256, taking first 8 chars)
        hash_obj = hashlib.sha256(normalized_path.encode("utf-8"))
        hash_str = hash_obj.hexdigest()[:8]

        # Cache result
        self._hash_cache[project_path] = hash_str

        return hash_str

    def _normalize_path_for_hash(self, path: str) -> str:
        """Normalize path to UNIX format for consistent hashing.

        This method always returns UNIX-style paths (/c/Users/... on Windows)
        to ensure hash consistency across different path representations.

        Args:
            path: Path to normalize (any format)

        Returns:
            UNIX-style normalized path string
        """
        if not path:
            return path

        # Convert to Path object and resolve to absolute
        p = Path(path)
        try:
            p = p.resolve()
        except (OSError, RuntimeError):
            # If resolve fails, just make it absolute
            p = p.absolute()

        # Convert to POSIX format (forward slashes)
        path_str = p.as_posix()

        # Handle Windows paths - convert drive letters to MSYS format
        # C:/Users/... -> /c/Users/... (Git Bash style)
        if platform.system() == "Windows" and ":" in path_str:
            drive, rest = path_str.split(":", 1)
            path_str = f"/{drive.lower()}{rest}"

        # Remove trailing slashes (but keep root slash)
        path_str = path_str.rstrip('/')
        if not path_str:
            path_str = '/'

        return path_str

    def _to_native_path(self, unix_path: str) -> Path:
        """Convert UNIX-style path to native OS path format.

        Args:
            unix_path: UNIX-style path (e.g., /c/Users/Admin)

        Returns:
            Path object in native OS format
        """
        if not unix_path:
            return Path(unix_path)

        # On Windows, convert MSYS format back to Windows format
        if platform.system() == "Windows":
            # Match: /[drive-letter]/rest/of/path
            drive_pattern = r'^/([a-zA-Z])(/.*)?$'
            match = re.match(drive_pattern, unix_path)

            if match:
                drive_letter = match.group(1).upper()
                rest_of_path = match.group(2) or ''
                # Convert to Windows format: C:\Users\...
                windows_path = f"{drive_letter}:{rest_of_path}"
                return Path(windows_path)

        # On Unix or if pattern doesn't match, use as-is
        return Path(unix_path)

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

    def get_global_group_id(self, hostname: str) -> str:
        """Generate the global group ID for this machine.

        The global group ID is used for machine-wide memories that are not
        tied to a specific project, following the naming convention used
        by Claude Code for cross-project session tracking.

        Args:
            hostname: Machine hostname

        Returns:
            Global group ID in format '{hostname}__global'
        """
        return f"{hostname}__global"

    def get_project_path_from_hash(self, project_hash: str) -> Optional[str]:
        """Reverse-lookup project path from hash by scanning known projects.

        This method scans known project directories and computes hashes to find
        a matching project path. Results are cached for subsequent lookups.

        Note: This is an O(n) operation where n is the number of known projects.
        For typical usage (< 10 projects), this is negligible.

        Args:
            project_hash: The 8-character hash to look up

        Returns:
            Project directory path in native OS format, or None if not found
        """
        # Check cache first
        if project_hash in self._reverse_hash_cache:
            return self._reverse_hash_cache[project_hash]

        # Build/update reverse cache by scanning known projects
        try:
            projects = self.list_all_projects()

            for hash_key, sessions_dir in projects.items():
                # Already in reverse cache? Skip
                if hash_key in self._reverse_hash_cache:
                    continue

                # Try to find a project path that hashes to this key
                # The sessions_dir is: ~/.claude/projects/{hash}/sessions
                # We need to find the original project path that produced this hash

                # Store the hash -> path mapping (path is unknown, but we know the hash exists)
                # Since we can't reverse the hash, we can only match against forward lookups
                # For now, record that this hash exists but path is unknown
                # The hash will be matched when a project path is explicitly provided

            # Check if the requested hash exists in our projects
            if project_hash in projects:
                # The hash exists but we don't know the original path
                # without additional information (like watching which paths are opened)
                logger.debug(f"Hash {project_hash} exists but original path unknown")

        except Exception as e:
            logger.error(f"Error building reverse hash cache: {e}", exc_info=True)

        # Also check our forward cache to see if we've seen this hash before
        for path, cached_hash in self._hash_cache.items():
            if cached_hash == project_hash:
                # Found it! Cache the reverse mapping and return
                self._reverse_hash_cache[project_hash] = path
                return path

        return None

    def register_project_path(self, project_path: str) -> str:
        """Register a project path and return its hash.

        This populates both the forward and reverse hash caches,
        enabling subsequent reverse lookups via get_project_path_from_hash.

        Args:
            project_path: Absolute path to project directory

        Returns:
            8-character hash string for the project
        """
        project_hash = self.get_project_hash(project_path)
        self._reverse_hash_cache[project_hash] = project_path
        return project_hash
