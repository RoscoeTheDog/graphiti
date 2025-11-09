"""
Filesystem Export Module for Graphiti

Provides export capabilities to write memory graph data to files with:
- Flexible path pattern substitution
- Template-based rendering
- INDEX.md integration
- Security scanning for credentials
"""

import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Path Pattern Resolution
# ============================================================================


class PathResolver:
    """Resolves path patterns with variable substitution"""

    # Security: Prevent path traversal attacks (relative patterns only)
    DANGEROUS_PATTERNS = re.compile(r'\.\.')

    @staticmethod
    def get_builtin_variables(
        fact_count: int = 0,
        node_count: int = 0,
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> dict[str, str]:
        """Generate builtin path pattern variables

        Args:
            fact_count: Number of facts in export
            node_count: Number of nodes in export
            query: Search query (for hash generation)
            session_id: Session identifier
            group_id: Group identifier

        Returns:
            Dict of builtin variables for substitution
        """
        now = datetime.now()

        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid4())[:8]

        # Generate query hash if query provided
        query_hash = ""
        if query:
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]

        return {
            "date": now.strftime("%Y-%m-%d"),
            "timestamp": now.strftime("%Y-%m-%d-%H%M"),
            "time": now.strftime("%H%M"),
            "session_id": session_id,
            "group_id": group_id or "default",
            "query_hash": query_hash,
            "fact_count": str(fact_count),
            "node_count": str(node_count),
        }

    @staticmethod
    def resolve_path(
        pattern: str,
        fact_count: int = 0,
        node_count: int = 0,
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        group_id: Optional[str] = None,
        path_variables: Optional[dict[str, str]] = None,
    ) -> Path:
        """Resolve path pattern with variable substitution

        Args:
            pattern: Path pattern with {variable} placeholders
            fact_count: Number of facts in export
            node_count: Number of nodes in export
            query: Search query
            session_id: Session identifier
            group_id: Group identifier
            path_variables: Custom variables for substitution

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path contains dangerous patterns (path traversal)
        """
        # Get builtin variables
        variables = PathResolver.get_builtin_variables(
            fact_count=fact_count,
            node_count=node_count,
            query=query,
            session_id=session_id,
            group_id=group_id,
        )

        # Merge with custom variables (custom takes precedence)
        if path_variables:
            variables.update(path_variables)

        # Substitute variables
        resolved = pattern
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            resolved = resolved.replace(placeholder, value)

        # Security check: Detect path traversal attempts
        if PathResolver.DANGEROUS_PATTERNS.search(resolved):
            raise ValueError(
                f"Path contains dangerous patterns (path traversal detected): {resolved}"
            )

        return Path(resolved)


# ============================================================================
# Security Scanning
# ============================================================================


class SecurityScanner:
    """Scans content for credentials and sensitive data"""

    # Pattern for detecting credentials
    CREDENTIAL_PATTERNS = [
        (re.compile(r'api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "api_key"),
        (re.compile(r'secret\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "secret"),
        (re.compile(r'password\s*[:=]\s*["\']?[^\s]{8,}', re.IGNORECASE), "password"),
        (re.compile(r'token\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "token"),
        (re.compile(r'bearer\s+[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "bearer_token"),
        (re.compile(r'auth[_-]?token\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE), "auth_token"),
    ]

    @staticmethod
    def scan(content: str) -> list[str]:
        """Scan content for credentials

        Args:
            content: Text content to scan

        Returns:
            List of detected credential types (empty if none found)
        """
        detected = []
        for pattern, cred_type in SecurityScanner.CREDENTIAL_PATTERNS:
            if pattern.search(content):
                detected.append(cred_type)
        return detected


# ============================================================================
# Memory Exporter
# ============================================================================


class ExportMetadata(BaseModel):
    """Metadata for exported memory"""

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    fact_count: int = 0
    node_count: int = 0
    query: Optional[str] = None
    session_id: Optional[str] = None
    group_id: Optional[str] = None
    template: str = "handoff"
    format: str = "markdown"


class ExportResult(BaseModel):
    """Result of export operation"""

    success: bool
    output_path: str
    fact_count: int = 0
    node_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class MemoryExporter:
    """Exports memory graph data to filesystem"""

    def __init__(
        self,
        base_path: Optional[str] = None,
        auto_index: bool = True,
        security_scan_enabled: bool = True,
        security_scan_enforce: bool = False,
    ):
        """Initialize MemoryExporter

        Args:
            base_path: Base directory for exports (default: .claude/context)
            auto_index: Automatically update INDEX.md after export
            security_scan_enabled: Enable credential scanning
            security_scan_enforce: Halt on credential detection (vs warn)
        """
        self.base_path = Path(base_path or ".claude/context")
        self.auto_index = auto_index
        self.security_scan_enabled = security_scan_enabled
        self.security_scan_enforce = security_scan_enforce

    def export_to_file(
        self,
        content: str,
        output_path: str,
        metadata: Optional[ExportMetadata] = None,
        path_variables: Optional[dict[str, str]] = None,
    ) -> ExportResult:
        """Export content to file with security scanning and INDEX.md updates

        Args:
            content: Rendered content to write
            output_path: Path pattern (e.g., "{date}-handoff.md")
            metadata: Export metadata
            path_variables: Custom path variables

        Returns:
            ExportResult with success status and details
        """
        result = ExportResult(success=False, output_path="")

        if metadata is None:
            metadata = ExportMetadata()

        try:
            # Security scan
            if self.security_scan_enabled:
                detected = SecurityScanner.scan(content)
                if detected:
                    warning = f"Detected credentials in export: {', '.join(detected)}"
                    result.warnings.append(warning)
                    logger.warning(warning)

                    if self.security_scan_enforce:
                        result.errors.append(
                            "Export blocked by security scan (enforce mode). "
                            "Obfuscate credentials before exporting."
                        )
                        return result

            # Resolve path pattern
            resolved_path = PathResolver.resolve_path(
                pattern=str(self.base_path / output_path),
                fact_count=metadata.fact_count,
                node_count=metadata.node_count,
                query=metadata.query,
                session_id=metadata.session_id,
                group_id=metadata.group_id,
                path_variables=path_variables,
            )

            # Create parent directories
            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            resolved_path.write_text(content, encoding="utf-8")
            logger.info(f"Exported memory to: {resolved_path}")

            # Update INDEX.md if enabled
            if self.auto_index:
                self._update_index(resolved_path, metadata)

            result.success = True
            result.output_path = str(resolved_path)
            result.fact_count = metadata.fact_count
            result.node_count = metadata.node_count

        except ValueError as e:
            result.errors.append(f"Path resolution error: {str(e)}")
            logger.error(f"Path resolution failed: {e}")
        except Exception as e:
            result.errors.append(f"Export failed: {str(e)}")
            logger.error(f"Export failed: {e}", exc_info=True)

        return result

    def _update_index(self, file_path: Path, metadata: ExportMetadata) -> None:
        """Update INDEX.md in the export directory

        Args:
            file_path: Path to exported file
            metadata: Export metadata
        """
        try:
            index_path = file_path.parent / "INDEX.md"

            # Get file stats
            stats = file_path.stat()
            size_kb = stats.st_size / 1024
            created = datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M")
            modified = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")

            # Extract description from metadata or filename
            description = f"{metadata.template} export"
            if metadata.query:
                description += f": {metadata.query[:50]}"

            # Create or append to INDEX.md
            if not index_path.exists():
                # Create new INDEX.md
                header = (
                    f"# Index - {file_path.parent.name}\n\n"
                    f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    "| File | Created | Modified | Size | Description |\n"
                    "|------|---------|----------|------|-------------|\n"
                )
                index_path.write_text(header, encoding="utf-8")

            # Append entry
            entry = (
                f"| {file_path.name} | {created} | {modified} | "
                f"{size_kb:.1f} KB | {description} |\n"
            )

            with open(index_path, "a", encoding="utf-8") as f:
                f.write(entry)

            logger.info(f"Updated INDEX.md: {index_path}")

        except Exception as e:
            logger.warning(f"Failed to update INDEX.md: {e}")
