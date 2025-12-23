"""
Tests for Requirements Generator Module

Tests cover:
- TOML parsing (valid and malformed files)
- Version spec preservation
- Optional dependencies handling
- File creation and formatting
- Error handling and edge cases
- Path traversal prevention
- Integration with real pyproject.toml
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from mcp_server.daemon.generate_requirements import (
    parse_pyproject_toml,
    generate_requirements_txt,
    write_requirements_file,
    RequirementsGenerationError,
    PyprojectParseError,
)


class TestPyprojectParsing:
    """Test pyproject.toml parsing functionality."""

    def test_parse_valid_pyproject(self, tmp_path):
        """Test parsing of valid pyproject.toml file."""
        pyproject_content = """
[project]
name = "test-package"
version = "1.0.0"
dependencies = [
    "requests>=2.28.0",
    "pydantic==2.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0"]
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        data = parse_pyproject_toml(pyproject_path)

        assert "project" in data
        assert data["project"]["name"] == "test-package"
        assert "dependencies" in data["project"]
        assert len(data["project"]["dependencies"]) == 2

    def test_parse_missing_file(self, tmp_path):
        """Test parsing raises error when file doesn't exist."""
        pyproject_path = tmp_path / "missing.toml"

        with pytest.raises(PyprojectParseError, match="not found"):
            parse_pyproject_toml(pyproject_path)

    def test_parse_non_toml_file(self, tmp_path):
        """Test parsing raises error for non-.toml files."""
        txt_path = tmp_path / "file.txt"
        txt_path.write_text("not toml")

        with pytest.raises(PyprojectParseError, match="Expected .toml file"):
            parse_pyproject_toml(txt_path)

    def test_parse_malformed_toml(self, tmp_path):
        """Test parsing raises error on malformed TOML."""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text("[project\ninvalid syntax")

        with pytest.raises(PyprojectParseError, match="Failed to parse"):
            parse_pyproject_toml(pyproject_path)

    def test_parse_missing_project_section(self, tmp_path):
        """Test parsing raises error when [project] section is missing."""
        pyproject_content = """
[tool.ruff]
line-length = 100
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        with pytest.raises(PyprojectParseError, match="missing \\[project\\] section"):
            parse_pyproject_toml(pyproject_path)


class TestRequirementsGeneration:
    """Test requirements.txt generation logic."""

    def test_generate_core_dependencies_only(self):
        """Test generating requirements with only core dependencies."""
        pyproject_data = {
            "project": {
                "dependencies": [
                    "requests>=2.28.0",
                    "pydantic==2.0.0",
                    "numpy~=1.24.0",
                ]
            }
        }

        requirements = generate_requirements_txt(pyproject_data, include_optional=False)

        assert len(requirements) == 3
        assert "requests>=2.28.0" in requirements
        assert "pydantic==2.0.0" in requirements
        assert "numpy~=1.24.0" in requirements

    def test_preserve_version_specifiers(self):
        """Test that version specifiers are preserved exactly."""
        pyproject_data = {
            "project": {
                "dependencies": [
                    "package1>=1.0.0",
                    "package2==2.0.0",
                    "package3~=3.0.0",
                    "package4",
                ]
            }
        }

        requirements = generate_requirements_txt(pyproject_data)

        assert "package1>=1.0.0" in requirements
        assert "package2==2.0.0" in requirements
        assert "package3~=3.0.0" in requirements
        assert "package4" in requirements

    def test_include_all_optional_dependencies(self):
        """Test including all optional dependencies with --include-optional."""
        pyproject_data = {
            "project": {
                "dependencies": ["core-package>=1.0.0"],
                "optional-dependencies": {
                    "dev": ["pytest>=7.0.0"],
                    "azure": ["azure-identity>=1.0.0"],
                }
            }
        }

        requirements = generate_requirements_txt(pyproject_data, include_optional=True)

        assert len(requirements) == 3
        assert "core-package>=1.0.0" in requirements
        assert "pytest>=7.0.0" in requirements
        assert "azure-identity>=1.0.0" in requirements

    def test_include_specific_optional_groups(self):
        """Test including specific optional dependency groups."""
        pyproject_data = {
            "project": {
                "dependencies": ["core-package>=1.0.0"],
                "optional-dependencies": {
                    "dev": ["pytest>=7.0.0"],
                    "azure": ["azure-identity>=1.0.0"],
                    "providers": ["google-genai>=1.0.0"],
                }
            }
        }

        requirements = generate_requirements_txt(
            pyproject_data,
            include_optional=True,
            optional_groups=["azure", "providers"]
        )

        assert len(requirements) == 3
        assert "core-package>=1.0.0" in requirements
        assert "azure-identity>=1.0.0" in requirements
        assert "google-genai>=1.0.0" in requirements
        assert "pytest>=7.0.0" not in requirements  # dev group excluded

    def test_exclude_optional_by_default(self):
        """Test that optional dependencies are excluded by default."""
        pyproject_data = {
            "project": {
                "dependencies": ["core-package>=1.0.0"],
                "optional-dependencies": {
                    "dev": ["pytest>=7.0.0"],
                }
            }
        }

        requirements = generate_requirements_txt(pyproject_data, include_optional=False)

        assert len(requirements) == 1
        assert "core-package>=1.0.0" in requirements
        assert "pytest>=7.0.0" not in requirements

    def test_missing_dependencies_section(self):
        """Test error when [project.dependencies] is missing and no optional deps."""
        pyproject_data = {
            "project": {
                "name": "test-package"
            }
        }

        with pytest.raises(RequirementsGenerationError, match="No dependencies found"):
            generate_requirements_txt(pyproject_data, include_optional=False)

    def test_remove_duplicate_dependencies(self):
        """Test that duplicate dependencies are removed."""
        pyproject_data = {
            "project": {
                "dependencies": [
                    "requests>=2.28.0",
                    "pydantic==2.0.0",
                ],
                "optional-dependencies": {
                    "dev": ["requests>=2.28.0"],  # Duplicate
                }
            }
        }

        requirements = generate_requirements_txt(pyproject_data, include_optional=True)

        # Should have only 2 unique deps (requests should not be duplicated)
        assert len(requirements) == 2
        assert requirements.count("requests>=2.28.0") == 1

    def test_strip_whitespace_from_dependencies(self):
        """Test that whitespace is stripped from dependency strings."""
        pyproject_data = {
            "project": {
                "dependencies": [
                    "  requests>=2.28.0  ",
                    "pydantic==2.0.0\n",
                ]
            }
        }

        requirements = generate_requirements_txt(pyproject_data)

        assert "requests>=2.28.0" in requirements
        assert "pydantic==2.0.0" in requirements


class TestFileWriting:
    """Test requirements.txt file writing functionality."""

    def test_write_creates_parent_directory(self, tmp_path):
        """Test that parent directories are created if missing."""
        output_path = tmp_path / "nested" / "dir" / "requirements.txt"
        requirements = ["requests>=2.28.0", "pydantic==2.0.0"]

        write_requirements_file(requirements, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_write_overwrites_existing_file(self, tmp_path):
        """Test that existing requirements.txt is overwritten."""
        output_path = tmp_path / "requirements.txt"
        output_path.write_text("old-package==1.0.0\n")

        requirements = ["new-package>=2.0.0"]
        write_requirements_file(requirements, output_path)

        content = output_path.read_text()
        assert "new-package>=2.0.0" in content
        assert "old-package==1.0.0" not in content

    def test_write_formats_one_per_line(self, tmp_path):
        """Test that requirements are written one per line."""
        output_path = tmp_path / "requirements.txt"
        requirements = ["requests>=2.28.0", "pydantic==2.0.0", "numpy~=1.24.0"]

        write_requirements_file(requirements, output_path)

        lines = output_path.read_text().strip().split('\n')
        assert len(lines) == 3
        assert lines[0] == "requests>=2.28.0"
        assert lines[1] == "pydantic==2.0.0"
        assert lines[2] == "numpy~=1.24.0"

    def test_write_file_permissions(self, tmp_path):
        """Test that created file has readable permissions."""
        output_path = tmp_path / "requirements.txt"
        requirements = ["requests>=2.28.0"]

        write_requirements_file(requirements, output_path)

        # Check file is readable
        stat_info = output_path.stat()
        assert stat_info.st_mode & 0o644

    def test_prevent_path_traversal(self, tmp_path):
        """Test that path traversal is prevented."""
        # Attempt to write to parent directory using ..
        output_path = tmp_path / ".." / ".." / "etc" / "passwd"
        requirements = ["malicious-package>=1.0.0"]

        with pytest.raises(RequirementsGenerationError, match="Path traversal detected"):
            write_requirements_file(requirements, output_path)

    def test_handle_unwritable_directory(self, tmp_path):
        """Test error handling when output directory is not writable."""
        # Skip on Windows where directory permissions work differently
        if sys.platform == "win32":
            pytest.skip("Directory permissions work differently on Windows")

        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)

        output_path = readonly_dir / "requirements.txt"
        requirements = ["requests>=2.28.0"]

        try:
            with pytest.raises(RequirementsGenerationError, match="Failed to write"):
                write_requirements_file(requirements, output_path)
        finally:
            # Cleanup: restore write permissions
            readonly_dir.chmod(0o755)


class TestIntegration:
    """Integration tests with real pyproject.toml."""

    def test_end_to_end_with_real_pyproject(self, tmp_path):
        """Test end-to-end: read real mcp_server/pyproject.toml, write requirements.txt."""
        # Get path to actual mcp_server/pyproject.toml
        script_dir = Path(__file__).parent.parent.parent
        pyproject_path = script_dir / "mcp_server" / "pyproject.toml"

        if not pyproject_path.exists():
            pytest.skip("mcp_server/pyproject.toml not found in repository")

        # Parse real pyproject.toml
        data = parse_pyproject_toml(pyproject_path)

        # Generate requirements (core only)
        requirements = generate_requirements_txt(data, include_optional=False)

        # Write to temp file
        output_path = tmp_path / "requirements.txt"
        write_requirements_file(requirements, output_path)

        # Verify file was created
        assert output_path.exists()

        # Verify content format
        content = output_path.read_text()
        lines = content.strip().split('\n')
        assert len(lines) == len(requirements)

        # Verify each line is a valid requirement
        for line in lines:
            assert line.strip()  # Not empty
            assert line == line.strip()  # No leading/trailing whitespace

    def test_generated_file_pip_compatible(self, tmp_path):
        """Test that generated requirements.txt is pip-compatible."""
        pyproject_content = """
[project]
name = "test-package"
dependencies = [
    "requests>=2.28.0",
    "pydantic==2.0.0",
]
"""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        # Generate requirements
        data = parse_pyproject_toml(pyproject_path)
        requirements = generate_requirements_txt(data)

        # Write to file
        output_path = tmp_path / "requirements.txt"
        write_requirements_file(requirements, output_path)

        # Verify pip can parse it (dry-run)
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--dry-run", "-r", str(output_path)],
            capture_output=True,
            text=True
        )

        # pip should parse the file without errors (may fail to install, but parsing should work)
        assert "Syntax error" not in result.stderr
        assert "invalid requirement" not in result.stderr.lower()


class TestCLIArgumentParsing:
    """Test CLI argument parsing (via main function)."""

    @patch('mcp_server.daemon.generate_requirements.parse_pyproject_toml')
    @patch('mcp_server.daemon.generate_requirements.write_requirements_file')
    def test_default_paths(self, mock_write, mock_parse, tmp_path):
        """Test CLI with default input/output paths."""
        mock_parse.return_value = {
            "project": {"dependencies": ["requests>=2.28.0"]}
        }

        # Import main after mocking
        from mcp_server.daemon.generate_requirements import main

        with patch('sys.argv', ['generate_requirements.py']):
            exit_code = main()

        assert exit_code == 0
        assert mock_parse.called
        assert mock_write.called

    @patch('mcp_server.daemon.generate_requirements.parse_pyproject_toml')
    @patch('mcp_server.daemon.generate_requirements.write_requirements_file')
    def test_custom_input_output(self, mock_write, mock_parse, tmp_path):
        """Test CLI with custom --input and --output paths."""
        input_path = tmp_path / "custom.toml"
        output_path = tmp_path / "custom-requirements.txt"

        mock_parse.return_value = {
            "project": {"dependencies": ["requests>=2.28.0"]}
        }

        from mcp_server.daemon.generate_requirements import main

        with patch('sys.argv', [
            'generate_requirements.py',
            '--input', str(input_path),
            '--output', str(output_path)
        ]):
            exit_code = main()

        assert exit_code == 0
        mock_parse.assert_called_once()
        call_args = mock_parse.call_args[0]
        assert str(call_args[0]) == str(input_path)
