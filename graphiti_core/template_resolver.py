"""
Template resolver with hierarchical search and caching.

This module provides template resolution for preprocessing prompts in Graphiti.
Templates are searched in a three-tier hierarchy:
1. Project-level: ./.graphiti/templates/
2. Global user-level: ~/.graphiti/templates/
3. Built-in: graphiti_core/session_tracking/prompts/

The resolver caches resolved templates to avoid repeated file I/O operations.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TemplateResolver:
    """Resolve templates from hierarchical search paths with caching.

    This class implements a three-tier template resolution system:
    1. Project templates: ./.graphiti/templates/
    2. Global templates: ~/.graphiti/templates/
    3. Built-in templates: graphiti_core/session_tracking/prompts/

    Templates are cached after first resolution to improve performance.

    Attributes:
        _cache: Dict mapping template names to resolved content
        _project_dir: Optional project root directory for project-level templates
        _builtin_dir: Path to built-in templates directory

    Examples:
        # Basic usage with default paths
        resolver = TemplateResolver()
        content = resolver.load("default-session-turn.md")

        # With custom project directory
        resolver = TemplateResolver(project_dir=Path("/path/to/project"))
        content = resolver.load("custom-template.md")

        # Check if template exists without loading
        if resolver.exists("my-template.md"):
            content = resolver.load("my-template.md")
    """

    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize template resolver.

        Args:
            project_dir: Optional project root directory. If None, project-level
                templates will not be searched (only global and built-in).
        """
        self._cache: Dict[str, str] = {}
        self._project_dir = project_dir

        # Built-in templates are in graphiti_core/session_tracking/prompts/
        # Use Path(__file__) to get location relative to this module
        self._builtin_dir = Path(__file__).parent / "session_tracking" / "prompts"

        logger.debug(
            "TemplateResolver initialized: project_dir=%s, builtin_dir=%s",
            project_dir,
            self._builtin_dir,
        )

    def load(self, template_name: str) -> Optional[str]:
        """Load template content from hierarchical search.

        Searches for the template in the following order:
        1. Project templates: {project_dir}/.graphiti/templates/{template_name}
        2. Global templates: ~/.graphiti/templates/{template_name}
        3. Built-in templates: graphiti_core/session_tracking/prompts/{template_name}

        Results are cached after first successful load. Returns None if template
        is not found in any location.

        Args:
            template_name: Name of the template file (e.g., "default-session-turn.md")

        Returns:
            Template content as string if found, None otherwise.

        Examples:
            >>> resolver = TemplateResolver()
            >>> content = resolver.load("default-session-turn.md")
            >>> if content:
            ...     print("Template loaded successfully")
            Template loaded successfully

            >>> content = resolver.load("nonexistent.md")
            >>> content is None
            True
        """
        # Check cache first
        if template_name in self._cache:
            logger.debug("Template '%s' loaded from cache", template_name)
            return self._cache[template_name]

        # Build search paths in priority order
        search_paths = self._get_search_paths(template_name)

        # Try each path in order
        for path in search_paths:
            try:
                if path.exists() and path.is_file():
                    content = path.read_text(encoding="utf-8")
                    # Cache the result
                    self._cache[template_name] = content
                    logger.info(
                        "Template '%s' loaded from: %s",
                        template_name,
                        path,
                    )
                    return content
            except Exception as e:
                logger.warning(
                    "Failed to read template from %s: %s",
                    path,
                    e,
                )
                continue

        # Template not found in any location
        logger.warning(
            "Template '%s' not found in any search path: %s",
            template_name,
            [str(p) for p in search_paths],
        )
        return None

    def exists(self, template_name: str) -> bool:
        """Check if template exists in any search location.

        Args:
            template_name: Name of the template file

        Returns:
            True if template exists in cache or any search path, False otherwise.

        Examples:
            >>> resolver = TemplateResolver()
            >>> resolver.exists("default-session-turn.md")
            True

            >>> resolver.exists("nonexistent.md")
            False
        """
        # Check cache first
        if template_name in self._cache:
            return True

        # Check search paths
        search_paths = self._get_search_paths(template_name)
        return any(path.exists() and path.is_file() for path in search_paths)

    def clear_cache(self) -> None:
        """Clear the template cache.

        This forces templates to be reloaded from disk on next access.
        Useful for development or testing scenarios where templates change.

        Examples:
            >>> resolver = TemplateResolver()
            >>> resolver.load("template.md")  # Loads from disk
            >>> resolver.load("template.md")  # Loads from cache
            >>> resolver.clear_cache()
            >>> resolver.load("template.md")  # Loads from disk again
        """
        logger.debug("Clearing template cache (%d entries)", len(self._cache))
        self._cache.clear()

    def _get_search_paths(self, template_name: str) -> list[Path]:
        """Build list of search paths for template in priority order.

        Args:
            template_name: Name of the template file

        Returns:
            List of Path objects to search, in priority order:
            1. Project templates (if project_dir is set)
            2. Global templates (~/.graphiti/templates/)
            3. Built-in templates (graphiti_core/session_tracking/prompts/)
        """
        paths = []

        # 1. Project-level templates: ./.graphiti/templates/
        if self._project_dir:
            project_path = self._project_dir / ".graphiti" / "templates" / template_name
            paths.append(project_path)

        # 2. Global user-level templates: ~/.graphiti/templates/
        global_path = Path.home() / ".graphiti" / "templates" / template_name
        paths.append(global_path)

        # 3. Built-in templates: graphiti_core/session_tracking/prompts/
        builtin_path = self._builtin_dir / template_name
        paths.append(builtin_path)

        return paths
