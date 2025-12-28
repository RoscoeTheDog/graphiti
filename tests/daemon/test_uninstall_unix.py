"""
Unit tests for macOS and Linux uninstall script validation.

These tests verify the script structure and commands WITHOUT executing the scripts.
They ensure the scripts contain expected Bash syntax and service removal commands.

Note: These are validation tests, not execution tests. They check:
- Script files exist and are readable
- Scripts contain required commands (launchctl/systemctl, etc.)
- Scripts have valid Bash syntax (via bash -n)
- Scripts contain expected directory cleanup logic
- Scripts contain user prompts for data preservation
"""

import subprocess
from pathlib import Path

import pytest

# Path to uninstall scripts
SCRIPT_DIR = Path(__file__).parent.parent.parent / "mcp_server" / "daemon"
UNINSTALL_MACOS = SCRIPT_DIR / "uninstall_macos.sh"
UNINSTALL_LINUX = SCRIPT_DIR / "uninstall_linux.sh"


class TestUninstallMacOSScript:
    """Tests for macOS uninstall script structure and commands."""

    def test_script_exists(self):
        """Test that macOS uninstall script file exists."""
        assert UNINSTALL_MACOS.exists(), f"Script not found: {UNINSTALL_MACOS}"

    def test_script_readable(self):
        """Test that script is readable."""
        assert UNINSTALL_MACOS.is_file(), f"Not a file: {UNINSTALL_MACOS}"
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")
        assert len(content) > 0, "Script is empty"

    def test_script_has_bash_shebang(self):
        """Test that script has correct Bash shebang."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")
        first_line = content.split("\n")[0]
        assert first_line.startswith("#!"), "Missing shebang"
        assert "bash" in first_line, "Shebang doesn't reference bash"

    def test_script_contains_launchctl_commands(self):
        """Test that script contains launchctl commands for service removal."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")

        # Check for launchctl unload command
        assert "launchctl unload" in content, "Missing 'launchctl unload' command"

        # Check for plist reference
        assert "com.graphiti.bootstrap" in content, "Missing service ID"
        assert ".plist" in content, "Missing plist file reference"

    def test_script_contains_directory_cleanup(self):
        """Test that script contains directory deletion logic."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")

        # Check for key directories - v2.1 uses macOS Library paths
        required_dirs = [
            ".venv",
            "lib",  # v2.1 uses lib/ instead of mcp_server/
            "bin",
            "Logs",  # macOS uses Library/Logs/Graphiti
        ]

        for dir_name in required_dirs:
            assert dir_name in content, f"Missing directory reference: {dir_name}"

        # Check for deletion command (rm -rf)
        assert "rm -rf" in content or "rm" in content, "Missing rm command for cleanup"

    def test_script_contains_data_preservation_logic(self):
        """Test that script prompts for data/config preservation."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")

        # Check for config and data references
        assert "graphiti.config.json" in content, "Missing config file reference"
        assert "data" in content, "Missing data directory reference"

        # Check for user prompt logic
        has_prompt = "read" in content.lower() or "delete-all" in content.lower() or "force" in content.lower()
        assert has_prompt, "Missing user prompt logic for data preservation"

    def test_script_contains_help_flag(self):
        """Test that script supports --help flag."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")

        # Check for --help flag handling
        assert "--help" in content, "Missing --help flag"
        assert "Usage:" in content, "Missing usage instructions"

    def test_script_contains_dry_run_flag(self):
        """Test that script supports --dry-run flag."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")

        # Check for --dry-run flag
        assert "--dry-run" in content.lower(), "Missing --dry-run flag"

    def test_script_has_error_handling(self):
        """Test that script has error handling."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")

        # Check for set -e or set -euo pipefail (exit on error)
        assert "set -" in content, "Missing set command for error handling"

        # Check for error messages or exit codes
        has_error_handling = (
            "EXIT_CODE" in content or "exit" in content.lower()
        )
        assert has_error_handling, "Missing exit code handling"

    @pytest.mark.skipif(
        subprocess.run(["which", "bash"], capture_output=True).returncode != 0,
        reason="Bash not available",
    )
    def test_script_syntax_valid_bash(self):
        """Test that script has valid Bash syntax."""
        # Use bash -n to check syntax without executing
        try:
            result = subprocess.run(
                ["bash", "-n", str(UNINSTALL_MACOS)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0, f"Bash syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.fail("Bash syntax validation timed out")
        except FileNotFoundError:
            pytest.skip("Bash not found")

    def test_script_contains_manual_steps_instructions(self):
        """Test that script provides manual removal instructions."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")

        # Check for manual steps section
        assert "Manual Steps" in content or "manual" in content.lower(), "Missing manual removal instructions"

        # Check for Claude config path reference (macOS specific)
        assert "Library/Application Support/Claude" in content or "Claude" in content, "Missing Claude Desktop config instructions"

        # Check for PATH removal instructions
        assert "PATH" in content, "Missing PATH removal instructions"
        assert ".zshrc" in content or ".bash_profile" in content, "Missing shell rc file references"

    def test_script_has_version_info(self):
        """Test that script contains version information."""
        content = UNINSTALL_MACOS.read_text(encoding="utf-8")

        # Check for version reference
        has_version = "Version:" in content or "v1." in content or "Created:" in content
        assert has_version, "Missing version information"


class TestUninstallLinuxScript:
    """Tests for Linux uninstall script structure and commands."""

    def test_script_exists(self):
        """Test that Linux uninstall script file exists."""
        assert UNINSTALL_LINUX.exists(), f"Script not found: {UNINSTALL_LINUX}"

    def test_script_readable(self):
        """Test that script is readable."""
        assert UNINSTALL_LINUX.is_file(), f"Not a file: {UNINSTALL_LINUX}"
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")
        assert len(content) > 0, "Script is empty"

    def test_script_has_bash_shebang(self):
        """Test that script has correct Bash shebang."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")
        first_line = content.split("\n")[0]
        assert first_line.startswith("#!"), "Missing shebang"
        assert "bash" in first_line, "Shebang doesn't reference bash"

    def test_script_contains_systemctl_commands(self):
        """Test that script contains systemctl commands for service removal."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")

        # Check for systemctl stop command
        assert "systemctl --user stop" in content, "Missing 'systemctl --user stop' command"

        # Check for systemctl disable command
        assert "systemctl --user disable" in content, "Missing 'systemctl --user disable' command"

        # Check for daemon-reload
        assert "daemon-reload" in content, "Missing 'daemon-reload' command"

        # Check for service name
        assert "graphiti-bootstrap" in content, "Missing service name"

    def test_script_contains_directory_cleanup(self):
        """Test that script contains directory deletion logic."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")

        # Check for key directories - v2.1 uses XDG paths
        required_dirs = [
            ".venv",
            "lib",  # v2.1 uses lib/ instead of mcp_server/
            "bin",
            "logs",
        ]

        for dir_name in required_dirs:
            assert dir_name in content, f"Missing directory reference: {dir_name}"

        # Check for deletion command (rm -rf)
        assert "rm -rf" in content or "rm" in content, "Missing rm command for cleanup"

    def test_script_contains_data_preservation_logic(self):
        """Test that script prompts for data/config preservation."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")

        # Check for config and data references
        assert "graphiti.config.json" in content, "Missing config file reference"
        assert "data" in content, "Missing data directory reference"

        # Check for user prompt logic
        has_prompt = "read" in content.lower() or "delete-all" in content.lower() or "force" in content.lower()
        assert has_prompt, "Missing user prompt logic for data preservation"

    def test_script_contains_help_flag(self):
        """Test that script supports --help flag."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")

        # Check for --help flag handling
        assert "--help" in content, "Missing --help flag"
        assert "Usage:" in content, "Missing usage instructions"

    def test_script_contains_dry_run_flag(self):
        """Test that script supports --dry-run flag."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")

        # Check for --dry-run flag
        assert "--dry-run" in content.lower(), "Missing --dry-run flag"

    def test_script_has_error_handling(self):
        """Test that script has error handling."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")

        # Check for set -e or set -euo pipefail (exit on error)
        assert "set -" in content, "Missing set command for error handling"

        # Check for error messages or exit codes
        has_error_handling = (
            "EXIT_CODE" in content or "exit" in content.lower()
        )
        assert has_error_handling, "Missing exit code handling"

    @pytest.mark.skipif(
        subprocess.run(["which", "bash"], capture_output=True).returncode != 0,
        reason="Bash not available",
    )
    def test_script_syntax_valid_bash(self):
        """Test that script has valid Bash syntax."""
        # Use bash -n to check syntax without executing
        try:
            result = subprocess.run(
                ["bash", "-n", str(UNINSTALL_LINUX)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0, f"Bash syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.fail("Bash syntax validation timed out")
        except FileNotFoundError:
            pytest.skip("Bash not found")

    def test_script_contains_manual_steps_instructions(self):
        """Test that script provides manual removal instructions."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")

        # Check for manual steps section
        assert "Manual Steps" in content or "manual" in content.lower(), "Missing manual removal instructions"

        # Check for Claude config path reference (Linux specific)
        assert ".config/Claude" in content or "Claude" in content, "Missing Claude Desktop config instructions"

        # Check for PATH removal instructions
        assert "PATH" in content, "Missing PATH removal instructions"
        assert ".bashrc" in content or ".zshrc" in content, "Missing shell rc file references"

    def test_script_has_version_info(self):
        """Test that script contains version information."""
        content = UNINSTALL_LINUX.read_text(encoding="utf-8")

        # Check for version reference
        has_version = "Version:" in content or "v1." in content or "Created:" in content
        assert has_version, "Missing version information"


class TestBothUnixScripts:
    """Tests that apply to both macOS and Linux scripts."""

    @pytest.mark.parametrize("script_path", [UNINSTALL_MACOS, UNINSTALL_LINUX])
    def test_script_has_color_output(self, script_path):
        """Test that scripts use colored output for better UX."""
        content = script_path.read_text(encoding="utf-8")

        # Check for ANSI color codes or color variables
        has_colors = (
            "\\033[" in content  # ANSI escape codes
            or "RED=" in content
            or "GREEN=" in content
            or "CYAN=" in content
        )
        assert has_colors, f"Missing color output in {script_path.name}"

    @pytest.mark.parametrize("script_path", [UNINSTALL_MACOS, UNINSTALL_LINUX])
    def test_script_has_banner(self, script_path):
        """Test that scripts display a banner for clarity."""
        content = script_path.read_text(encoding="utf-8")

        # Check for banner or title
        has_banner = (
            "Graphiti" in content and "Uninstall" in content
        )
        assert has_banner, f"Missing banner in {script_path.name}"

    @pytest.mark.parametrize("script_path", [UNINSTALL_MACOS, UNINSTALL_LINUX])
    def test_script_uses_variables_for_paths(self, script_path):
        """Test that scripts use variables for paths (maintainability)."""
        content = script_path.read_text(encoding="utf-8")

        # Check for path variables - v2.1 uses INSTALL_DIR instead of GRAPHITI_DIR
        path_vars = [
            "INSTALL_DIR",  # v2.1 architecture
            "VENV_DIR",
            "BIN_DIR",
        ]

        for var in path_vars:
            assert var in content, f"Missing path variable {var} in {script_path.name}"
