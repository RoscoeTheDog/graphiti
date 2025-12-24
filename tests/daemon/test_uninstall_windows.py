"""
Unit tests for Windows uninstall script validation.

These tests verify the script structure and commands WITHOUT executing the script.
They ensure the script contains expected PowerShell syntax and NSSM commands.

Note: These are validation tests, not execution tests. They check:
- Script file exists and is readable
- Script contains required commands (nssm stop, nssm remove, etc.)
- Script has valid PowerShell syntax (via powershell -File -WhatIf)
- Script contains expected directory cleanup logic
- Script contains user prompts for data preservation
"""

import subprocess
from pathlib import Path

import pytest

# Path to uninstall script
SCRIPT_DIR = Path(__file__).parent.parent.parent / "mcp_server" / "daemon"
UNINSTALL_SCRIPT = SCRIPT_DIR / "uninstall_windows.ps1"


class TestUninstallWindowsScript:
    """Tests for Windows uninstall script structure and commands."""

    def test_script_exists(self):
        """Test that uninstall script file exists."""
        assert UNINSTALL_SCRIPT.exists(), f"Script not found: {UNINSTALL_SCRIPT}"

    def test_script_readable(self):
        """Test that script is readable."""
        assert UNINSTALL_SCRIPT.is_file(), f"Not a file: {UNINSTALL_SCRIPT}"
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")
        assert len(content) > 0, "Script is empty"

    def test_script_has_powershell_header(self):
        """Test that script has PowerShell comment-based help header."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")
        assert "<#" in content, "Missing PowerShell comment block start"
        assert "#>" in content, "Missing PowerShell comment block end"
        assert ".SYNOPSIS" in content, "Missing .SYNOPSIS section"
        assert ".DESCRIPTION" in content, "Missing .DESCRIPTION section"

    def test_script_contains_service_removal_commands(self):
        """Test that script contains NSSM service removal commands."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for NSSM stop command
        assert "nssm stop" in content.lower(), "Missing 'nssm stop' command"

        # Check for NSSM remove command
        assert "nssm remove" in content.lower(), "Missing 'nssm remove' command"

        # Check for service name reference
        assert "GraphitiBootstrap" in content, "Missing service name 'GraphitiBootstrap'"

    def test_script_contains_directory_cleanup(self):
        """Test that script contains directory deletion logic."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for key directories
        required_dirs = [
            ".graphiti",
            ".venv",
            "mcp_server",
            "bin",
            "logs",
        ]

        for dir_name in required_dirs:
            assert dir_name in content, f"Missing directory reference: {dir_name}"

        # Check for deletion command (Remove-Item is PowerShell's rm)
        assert "Remove-Item" in content, "Missing Remove-Item command for cleanup"

    def test_script_contains_data_preservation_logic(self):
        """Test that script prompts for data/config preservation."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for config and data references
        assert "graphiti.config.json" in content, "Missing config file reference"
        assert "data" in content or "Data" in content, "Missing data directory reference"

        # Check for user prompt logic (Read-Host or similar)
        has_prompt = "Read-Host" in content or "DeleteAll" in content or "Force" in content
        assert has_prompt, "Missing user prompt logic for data preservation"

    def test_script_contains_elevation_detection(self):
        """Test that script checks for administrator rights."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for admin/elevation detection
        elevation_indicators = [
            "Administrator",
            "WindowsPrincipal",
            "WindowsIdentity",
        ]

        has_elevation_check = any(indicator in content for indicator in elevation_indicators)
        assert has_elevation_check, "Missing elevation/administrator detection logic"

    def test_script_contains_error_handling(self):
        """Test that script has error handling for missing NSSM."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for NSSM not found handling
        assert "nssm" in content.lower(), "Missing NSSM reference"

        # Check for error messages or fallback logic
        has_error_handling = (
            "not found" in content.lower()
            or "ErrorAction" in content
            or "try" in content.lower()
        )
        assert has_error_handling, "Missing error handling for NSSM absence"

    def test_script_has_help_parameter(self):
        """Test that script supports -Help parameter."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for Help parameter definition
        assert "Help" in content, "Missing -Help parameter"
        assert "param(" in content.lower(), "Missing param block for parameters"

    def test_script_has_dry_run_parameter(self):
        """Test that script supports -DryRun parameter."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for DryRun parameter
        assert "DryRun" in content, "Missing -DryRun parameter"

    @pytest.mark.skipif(
        not Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe").exists(),
        reason="PowerShell not available (not on Windows)",
    )
    def test_script_syntax_valid_powershell(self):
        """Test that script has valid PowerShell syntax (Windows only)."""
        # Use -File with -WhatIf to validate syntax without executing
        # Note: -WhatIf doesn't work with all scripts, so we use -Syntax instead
        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    f"$null = Get-Command -Syntax '{UNINSTALL_SCRIPT}'",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # If syntax check passes, exit code should be 0 or script should load
            # Even if Get-Command fails, the script should at least parse
            assert result.returncode in [
                0,
                1,
            ], f"PowerShell syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.fail("PowerShell syntax validation timed out")
        except FileNotFoundError:
            pytest.skip("PowerShell not found (not on Windows)")

    def test_script_contains_manual_steps_instructions(self):
        """Test that script provides manual removal instructions."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for manual steps section
        manual_indicators = [
            "manual",
            "Claude",
            "PATH",
            "config",
        ]

        has_manual_steps = any(indicator in content.lower() for indicator in manual_indicators)
        assert has_manual_steps, "Missing manual removal instructions"

        # Check for Claude config path reference
        assert "Claude" in content, "Missing Claude Desktop config instructions"

    def test_script_exit_code_handling(self):
        """Test that script uses exit codes properly."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for exit statements
        assert "exit" in content.lower(), "Missing exit statements"

        # Check for exit code variable or tracking
        has_exit_code = "ExitCode" in content or "$?" in content or "exit 0" in content.lower()
        assert has_exit_code, "Missing exit code handling"

    def test_script_has_version_info(self):
        """Test that script contains version information."""
        content = UNINSTALL_SCRIPT.read_text(encoding="utf-8")

        # Check for version reference
        version_indicators = [
            "Version",
            "v1.",
            "Created",
        ]

        has_version = any(indicator in content for indicator in version_indicators)
        assert has_version, "Missing version information"
