"""Tests for export module"""

import tempfile
from pathlib import Path

import pytest

from graphiti_core.export import (
    ExportMetadata,
    MemoryExporter,
    PathResolver,
    SecurityScanner,
)


class TestPathResolver:
    """Test path pattern resolution"""

    def test_builtin_variables(self):
        """Test builtin variable generation"""
        variables = PathResolver.get_builtin_variables(
            fact_count=42,
            node_count=15,
            query="test query",
            session_id="abc123",
            group_id="test-group",
        )

        assert "date" in variables
        assert "timestamp" in variables
        assert "time" in variables
        assert variables["session_id"] == "abc123"
        assert variables["group_id"] == "test-group"
        assert variables["fact_count"] == "42"
        assert variables["node_count"] == "15"
        assert len(variables["query_hash"]) == 8

    def test_builtin_variables_auto_session_id(self):
        """Test automatic session ID generation"""
        variables = PathResolver.get_builtin_variables()

        assert "session_id" in variables
        assert len(variables["session_id"]) == 8

    def test_resolve_path_simple(self):
        """Test simple path resolution"""
        path = PathResolver.resolve_path(
            pattern="{date}-handoff.md",
            fact_count=10,
            node_count=5,
        )

        assert isinstance(path, Path)
        assert path.name.endswith("-handoff.md")

    def test_resolve_path_nested(self):
        """Test nested path resolution"""
        path = PathResolver.resolve_path(
            pattern="investigations/{date}-{query_hash}.md",
            query="authentication bug",
        )

        assert path.parent.name == "investigations"
        assert path.suffix == ".md"

    def test_resolve_path_custom_variables(self):
        """Test custom variable substitution"""
        path = PathResolver.resolve_path(
            pattern="{category}/{name}.md",
            path_variables={"category": "bugs", "name": "auth-issue"},
        )

        # Use Path comparison to handle platform-specific separators
        assert path == Path("bugs/auth-issue.md")

    def test_resolve_path_custom_overrides_builtin(self):
        """Test custom variables override builtins"""
        path = PathResolver.resolve_path(
            pattern="{session_id}.md",
            session_id="original",
            path_variables={"session_id": "override"},
        )

        assert path.name == "override.md"

    def test_resolve_path_security_path_traversal(self):
        """Test path traversal protection"""
        with pytest.raises(ValueError, match="path traversal"):
            PathResolver.resolve_path(pattern="../../../etc/passwd")

        with pytest.raises(ValueError, match="path traversal"):
            PathResolver.resolve_path(pattern="docs/../../../etc/passwd")

    def test_resolve_path_allows_absolute_paths(self):
        """Test that absolute paths are allowed (for export_to_file)"""
        # Absolute paths are allowed since base_path may be absolute
        # Only .. is dangerous for path traversal
        path = PathResolver.resolve_path(pattern="/tmp/test.md")
        assert isinstance(path, Path)


class TestSecurityScanner:
    """Test security scanning"""

    def test_scan_no_credentials(self):
        """Test scanning clean content"""
        content = "This is a normal document with no credentials."
        detected = SecurityScanner.scan(content)
        assert detected == []

    def test_scan_api_key(self):
        """Test API key detection"""
        content = "api_key: sk-1234567890abcdefgh"
        detected = SecurityScanner.scan(content)
        assert "api_key" in detected

    def test_scan_password(self):
        """Test password detection"""
        content = "password: mySecretPass123"
        detected = SecurityScanner.scan(content)
        assert "password" in detected

    def test_scan_token(self):
        """Test token detection"""
        content = "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        detected = SecurityScanner.scan(content)
        assert "token" in detected

    def test_scan_bearer_token(self):
        """Test bearer token detection"""
        content = "Authorization: Bearer eyJhbGciOiJIUzI1NiI"
        detected = SecurityScanner.scan(content)
        assert "bearer_token" in detected

    def test_scan_multiple_credentials(self):
        """Test multiple credential detection"""
        content = """
        api_key: sk-1234567890abcdef
        password: secret123456
        """
        detected = SecurityScanner.scan(content)
        assert len(detected) >= 2


class TestMemoryExporter:
    """Test MemoryExporter class"""

    def test_export_to_file_basic(self, tmp_path):
        """Test basic file export"""
        exporter = MemoryExporter(base_path=str(tmp_path), auto_index=False)

        content = "# Test Export\n\nThis is test content."
        metadata = ExportMetadata(fact_count=5, node_count=3)

        result = exporter.export_to_file(
            content=content,
            output_path="test.md",
            metadata=metadata,
        )

        assert result.success
        assert result.fact_count == 5
        assert result.node_count == 3

        # Verify file exists
        output_file = Path(result.output_path)
        assert output_file.exists()
        assert output_file.read_text() == content

    def test_export_to_file_nested_path(self, tmp_path):
        """Test export with nested directories"""
        exporter = MemoryExporter(base_path=str(tmp_path), auto_index=False)

        result = exporter.export_to_file(
            content="Test content",
            output_path="investigations/{date}-test.md",
            metadata=ExportMetadata(),
        )

        assert result.success

        output_file = Path(result.output_path)
        assert output_file.exists()
        assert "investigations" in str(output_file)

    def test_export_to_file_security_scan_warn(self, tmp_path):
        """Test security scan warning mode"""
        exporter = MemoryExporter(
            base_path=str(tmp_path),
            auto_index=False,
            security_scan_enabled=True,
            security_scan_enforce=False,
        )

        content = "api_key: sk-1234567890abcdef"
        result = exporter.export_to_file(
            content=content,
            output_path="test.md",
            metadata=ExportMetadata(),
        )

        assert result.success
        assert len(result.warnings) > 0
        assert "credentials" in result.warnings[0].lower()

    def test_export_to_file_security_scan_enforce(self, tmp_path):
        """Test security scan enforce mode"""
        exporter = MemoryExporter(
            base_path=str(tmp_path),
            auto_index=False,
            security_scan_enabled=True,
            security_scan_enforce=True,
        )

        content = "password: secret123456"
        result = exporter.export_to_file(
            content=content,
            output_path="test.md",
            metadata=ExportMetadata(),
        )

        assert not result.success
        assert len(result.errors) > 0
        assert "blocked by security scan" in result.errors[0].lower()

    def test_export_to_file_with_index(self, tmp_path):
        """Test INDEX.md generation"""
        exporter = MemoryExporter(base_path=str(tmp_path), auto_index=True)

        metadata = ExportMetadata(
            fact_count=10,
            node_count=5,
            query="test query",
        )

        result = exporter.export_to_file(
            content="Test content",
            output_path="test.md",
            metadata=metadata,
        )

        assert result.success

        # Verify INDEX.md exists
        index_path = tmp_path / "INDEX.md"
        assert index_path.exists()

        index_content = index_path.read_text()
        assert "test.md" in index_content
        assert "| File | Created | Modified | Size | Description |" in index_content

    def test_export_to_file_path_traversal_blocked(self, tmp_path):
        """Test path traversal attack blocked"""
        exporter = MemoryExporter(base_path=str(tmp_path), auto_index=False)

        result = exporter.export_to_file(
            content="Malicious content",
            output_path="../../../etc/passwd",
            metadata=ExportMetadata(),
        )

        assert not result.success
        assert len(result.errors) > 0
        assert "path resolution error" in result.errors[0].lower()


class TestExportMetadata:
    """Test ExportMetadata model"""

    def test_default_timestamp(self):
        """Test automatic timestamp generation"""
        metadata = ExportMetadata()
        assert metadata.timestamp is not None

    def test_custom_fields(self):
        """Test custom field assignment"""
        metadata = ExportMetadata(
            fact_count=42,
            node_count=15,
            query="test query",
            session_id="abc123",
            group_id="test-group",
            template="handoff",
            format="markdown",
        )

        assert metadata.fact_count == 42
        assert metadata.node_count == 15
        assert metadata.query == "test query"
        assert metadata.session_id == "abc123"
        assert metadata.group_id == "test-group"
        assert metadata.template == "handoff"
        assert metadata.format == "markdown"
