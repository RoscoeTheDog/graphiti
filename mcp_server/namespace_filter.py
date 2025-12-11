"""Namespace filtering utilities for Graphiti MCP server search operations.

This module provides functions to extract project namespace metadata from episode
content and filter search results based on namespace constraints. Used by
search_memory_nodes and search_memory_facts to implement namespace-scoped
knowledge retrieval.

The namespace metadata is embedded as YAML frontmatter in episode content
by the session tracking system (see graphiti_core/session_tracking/metadata.py).
"""

import socket
from typing import TYPE_CHECKING, Any, Optional

import yaml

if TYPE_CHECKING:
    from mcp_server.unified_config import SessionTrackingConfig


def extract_namespace_from_content(content: str) -> Optional[str]:
    """Extract project_namespace from YAML frontmatter in episode content.

    Parses the YAML frontmatter at the start of episode content to extract
    the project_namespace field from graphiti_session_metadata.

    Args:
        content: Episode content string, potentially with YAML frontmatter

    Returns:
        Project namespace string (hexadecimal hash), or None if not found
        or parsing fails

    Example:
        >>> content = '''---
        ... graphiti_session_metadata:
        ...   version: '2.0'
        ...   project_namespace: a1b2c3d4e5f6g7h8
        ...   hostname: DESKTOP-ABC
        ... ---
        ...
        ... Session content here...
        ... '''
        >>> extract_namespace_from_content(content)
        'a1b2c3d4e5f6g7h8'
    """
    if not content or not content.startswith("---"):
        return None

    try:
        # Find end of frontmatter (second occurrence of ---)
        end_idx = content.index("---", 3)
        frontmatter_str = content[3:end_idx]

        # Parse YAML using safe_load (prevents arbitrary code execution)
        frontmatter = yaml.safe_load(frontmatter_str)

        # Extract namespace from the expected structure
        if frontmatter and "graphiti_session_metadata" in frontmatter:
            return frontmatter["graphiti_session_metadata"].get("project_namespace")

        return None
    except (ValueError, yaml.YAMLError):
        # ValueError: '---' not found (malformed frontmatter)
        # YAMLError: Invalid YAML syntax
        return None


def filter_by_namespace(
    results: list[Any],
    namespaces: list[str],
    content_attr: str = "content",
) -> list[Any]:
    """Filter search results to only include specified namespaces.

    Post-filters search results by extracting project_namespace from each
    result's content and checking against the allowed namespaces list.
    Results without namespace metadata are included for backward compatibility.

    Args:
        results: List of search result objects
        namespaces: List of allowed namespace hashes (hexadecimal strings)
        content_attr: Attribute name containing content (default: 'content')

    Returns:
        Filtered list containing only results from specified namespaces
        or results without namespace metadata (backward compat)

    Example:
        >>> class Result:
        ...     def __init__(self, content):
        ...         self.content = content
        >>> r1 = Result("---\\ngraphiti_session_metadata:\\n  project_namespace: abc123\\n---\\n")
        >>> r2 = Result("---\\ngraphiti_session_metadata:\\n  project_namespace: def456\\n---\\n")
        >>> filtered = filter_by_namespace([r1, r2], ["abc123"])
        >>> len(filtered)
        1
    """
    if not namespaces:
        # Empty namespace list means no filtering
        return results

    filtered = []
    for result in results:
        # Get content from result object
        content = getattr(result, content_attr, None)
        if content is None:
            # No content attribute - skip this result
            continue

        # Extract namespace from content
        ns = extract_namespace_from_content(content)

        # Include if namespace matches OR no namespace found (backward compat)
        if ns is None or ns in namespaces:
            filtered.append(result)

    return filtered


def get_effective_group_id(config: "SessionTrackingConfig") -> str:
    """Get the effective global group ID from config.

    Returns the configured group_id if set, otherwise computes a default
    based on the machine hostname following the pattern: '{hostname}__global'.

    Args:
        config: SessionTrackingConfig instance with optional group_id field

    Returns:
        Group ID string (e.g., 'DESKTOP-ABC123__global')

    Example:
        >>> class Config:
        ...     group_id = None
        >>> get_effective_group_id(Config())  # Returns hostname-based ID
        'DESKTOP-...__global'
    """
    if config.group_id:
        return config.group_id

    hostname = socket.gethostname()
    return f"{hostname}__global"
