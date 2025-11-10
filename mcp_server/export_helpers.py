"""
Helper functions for filesystem export in MCP server.

Extracted from graphiti_core.export for use in add_memory() tool.
Provides simplified path resolution, security scanning, and INDEX.md updates.
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path


def _resolve_path_pattern(
    filepath: str,
    query: str | None = None,
    fact_count: int = 0,
    node_count: int = 0,
) -> str:
    """Resolve path pattern variables.

    Supported variables:
    - {date} -> 2025-11-09
    - {timestamp} -> 2025-11-09-1430
    - {time} -> 1430
    - {hash} -> MD5 hash of query (8 chars)
    - {fact_count} -> Number of facts
    - {node_count} -> Number of nodes

    Args:
        filepath: Path pattern with {variable} placeholders
        query: Optional query string (used for hash generation)
        fact_count: Number of facts (for substitution)
        node_count: Number of nodes (for substitution)

    Returns:
        Resolved path string

    Raises:
        ValueError: If path contains dangerous patterns (..)

    Example:
        >>> _resolve_path_pattern("bugs/{date}-auth.md", query="login bug")
        'bugs/2025-11-09-auth.md'
    """
    now = datetime.now()

    # Build substitution map
    variables = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.strftime("%Y-%m-%d-%H%M"),
        "time": now.strftime("%H%M"),
        "fact_count": str(fact_count),
        "node_count": str(node_count),
    }

    # Add query hash if query provided
    if query:
        variables["hash"] = hashlib.md5(query.encode()).hexdigest()[:8]
    else:
        variables["hash"] = ""

    # Substitute variables
    resolved = filepath
    for key, value in variables.items():
        resolved = resolved.replace(f"{{{key}}}", value)

    # Security: Check for path traversal
    if ".." in resolved:
        raise ValueError("Path traversal detected (.. not allowed)")

    return resolved


def _scan_for_credentials(content: str) -> list[str]:
    """Scan content for credentials and sensitive data.

    Pattern detection for:
    - API keys
    - Secrets
    - Passwords
    - Tokens (bearer, auth)

    Args:
        content: Text content to scan

    Returns:
        List of detected credential types (empty if none found)

    Example:
        >>> _scan_for_credentials("api_key=abc123def456")
        ['api_key']
    """
    # Pattern for detecting credentials
    CREDENTIAL_PATTERNS = [
        (re.compile(r'api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "api_key"),
        (re.compile(r'secret\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "secret"),
        (re.compile(r'password\s*[:=]\s*["\']?[^\s]{8,}', re.IGNORECASE), "password"),
        (re.compile(r'token\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "token"),
        (re.compile(r'bearer\s+[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "bearer_token"),
        (re.compile(r'auth[_-]?token\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "auth_token"),
    ]

    detected = []
    for pattern, cred_type in CREDENTIAL_PATTERNS:
        if pattern.search(content):
            detected.append(cred_type)

    return list(set(detected))  # Remove duplicates




def _resolve_absolute_path(filepath: str, client_root: str | None = None) -> Path:
    """Resolve filepath to absolute path, relative to client root if needed.
    
    This function handles the Claude Code roots capability bug (issue #3315)
    by using PWD environment variable to detect client working directory.
    
    Args:
        filepath: Path pattern (may be relative or absolute)
        client_root: Client's working directory (typically from PWD env var)
        
    Returns:
        Absolute Path object
        
    Example:
        >>> _resolve_absolute_path(".claude/handoff/s001.md", "/home/user/project")
        Path('/home/user/project/.claude/handoff/s001.md')
        
        >>> _resolve_absolute_path("/tmp/output.md", "/home/user/project")
        Path('/tmp/output.md')
    """
    path = Path(filepath)
    
    # Already absolute - use as-is
    if path.is_absolute():
        return path
    
    # Relative path - resolve to client root if available
    if client_root:
        root = Path(client_root)
        return root / path
    
    # Fallback - relative to current working directory
    # (This happens when MCP server cwd != client cwd)
    return Path.cwd() / path
