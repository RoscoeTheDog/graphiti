"""Episode metadata header generation for Graphiti session tracking.

This module provides functions to build YAML frontmatter headers for episode
content, enabling namespace-based tagging for cross-project knowledge sharing.

The metadata header is prepended to episode bodies before they are indexed
into Graphiti, allowing filtering and scoping of memories by project namespace.
"""

from datetime import datetime, timezone
from typing import Optional

import yaml


def build_episode_metadata_header(
    project_namespace: str,
    project_path: Optional[str],
    hostname: str,
    session_file: str,
    message_count: int,
    duration_minutes: int,
    include_project_path: bool = True,
) -> str:
    """Build YAML frontmatter header for episode content.

    Generates metadata header that prepends episode body with project
    namespace tagging for cross-project knowledge sharing.

    Args:
        project_namespace: Hash derived from project path (for filtering)
        project_path: Human-readable project directory path
        hostname: Machine hostname for multi-machine disambiguation
        session_file: Original JSONL filename
        message_count: Number of messages in session
        duration_minutes: Approximate session duration
        include_project_path: Whether to include project_path in output

    Returns:
        YAML frontmatter string to prepend to episode body.
        Format: "---\\n{yaml_content}---\\n\\n"

    Example:
        >>> header = build_episode_metadata_header(
        ...     project_namespace="a1b2c3d4e5f6g7h8",
        ...     project_path="/home/user/my-project",
        ...     hostname="DESKTOP-ABC123",
        ...     session_file="session-abc123.jsonl",
        ...     message_count=47,
        ...     duration_minutes=23,
        ... )
        >>> print(header)
        ---
        graphiti_session_metadata:
          version: '2.0'
          project_namespace: a1b2c3d4e5f6g7h8
          project_path: /home/user/my-project
          hostname: DESKTOP-ABC123
          indexed_at: '2025-12-08T15:30:00+00:00'
          session_file: session-abc123.jsonl
          message_count: 47
          duration_minutes: 23
        ---

    """
    # Build metadata dict with required fields
    metadata_content = {
        "version": "2.0",  # String to avoid YAML float interpretation
        "project_namespace": project_namespace,
        "hostname": hostname,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "session_file": session_file,
        "message_count": message_count,
        "duration_minutes": duration_minutes,
    }

    # Conditionally include project_path
    # Only include if flag is True AND project_path is not None
    if include_project_path and project_path is not None:
        # Insert after project_namespace for logical ordering
        ordered_content = {
            "version": metadata_content["version"],
            "project_namespace": metadata_content["project_namespace"],
            "project_path": project_path,
            "hostname": metadata_content["hostname"],
            "indexed_at": metadata_content["indexed_at"],
            "session_file": metadata_content["session_file"],
            "message_count": metadata_content["message_count"],
            "duration_minutes": metadata_content["duration_minutes"],
        }
        metadata_content = ordered_content

    # Wrap in top-level key for clear structure
    metadata = {"graphiti_session_metadata": metadata_content}

    # Generate YAML with human-readable formatting
    yaml_output = yaml.dump(
        metadata,
        default_flow_style=False,
        sort_keys=False,  # Preserve insertion order
        allow_unicode=True,  # Handle special characters in paths
    )

    # Return as YAML frontmatter with proper delimiters
    return f"---\n{yaml_output}---\n\n"
