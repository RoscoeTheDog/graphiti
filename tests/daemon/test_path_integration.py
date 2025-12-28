"""
Tests for PATH Integration Module

Tests cover:
- PATH detection on various platforms
- Shell detection on Unix
- Unix rc snippet generation
- Windows registry modification (mocked)
- Error handling and edge cases
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from mcp_server.daemon.path_integration import (
    PathIntegration,
    PathIntegrationError,
)


class TestPathDetection:
    """Test PATH detection functionality."""

    def test_detect_in_path_when_present(self, tmp_path):
        """Test PATH detection returns True when bin path is in PATH."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        # Add bin_path to PATH
        original_path = os.environ.get("PATH", "")
        delimiter = ";" if sys.platform == "win32" else ":"
        os.environ["PATH"] = f"{bin_path}{delimiter}{original_path}"

        try:
            integration = PathIntegration(bin_path=bin_path)
            assert integration.detect_in_path() is True
        finally:
            os.environ["PATH"] = original_path

    def test_detect_in_path_when_absent(self, tmp_path):
        """Test PATH detection returns False when bin path is not in PATH."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        # Ensure bin_path is NOT in PATH
        original_path = os.environ.get("PATH", "")
        if str(bin_path) in original_path:
            # Remove it for this test
            delimiter = ";" if sys.platform == "win32" else ":"
            path_entries = original_path.split(delimiter)
            filtered = [e for e in path_entries if str(bin_path) not in e]
            os.environ["PATH"] = delimiter.join(filtered)

        try:
            integration = PathIntegration(bin_path=bin_path)
            assert integration.detect_in_path() is False
        finally:
            os.environ["PATH"] = original_path

    def test_detect_in_path_with_empty_path(self, tmp_path):
        """Test PATH detection handles empty PATH environment variable."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        original_path = os.environ.get("PATH", "")
        os.environ["PATH"] = ""

        try:
            integration = PathIntegration(bin_path=bin_path)
            assert integration.detect_in_path() is False
        finally:
            os.environ["PATH"] = original_path

    def test_detect_in_path_idempotent(self, tmp_path):
        """Test PATH detection is idempotent (multiple calls return same result)."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        integration = PathIntegration(bin_path=bin_path)
        result1 = integration.detect_in_path()
        result2 = integration.detect_in_path()
        result3 = integration.detect_in_path()

        assert result1 == result2 == result3

    def test_detect_in_path_with_symlink(self, tmp_path):
        """Test PATH detection handles symlinks correctly."""
        real_bin = tmp_path / "real_bin"
        real_bin.mkdir()

        # Create symlink
        symlink_bin = tmp_path / "symlink_bin"
        try:
            symlink_bin.symlink_to(real_bin)
        except OSError:
            pytest.skip("Symlink creation not supported on this platform")

        # Add symlink to PATH
        original_path = os.environ.get("PATH", "")
        delimiter = ";" if sys.platform == "win32" else ":"
        os.environ["PATH"] = f"{symlink_bin}{delimiter}{original_path}"

        try:
            # Should detect real_bin even though symlink is in PATH
            integration = PathIntegration(bin_path=real_bin)
            assert integration.detect_in_path() is True
        finally:
            os.environ["PATH"] = original_path


class TestShellDetection:
    """Test Unix shell detection."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_detect_shell_from_env(self):
        """Test shell detection uses $SHELL environment variable."""
        original_shell = os.environ.get("SHELL", "")
        os.environ["SHELL"] = "/bin/bash"

        try:
            integration = PathIntegration()
            shell = integration.detect_shell()
            assert shell == "bash"
        finally:
            if original_shell:
                os.environ["SHELL"] = original_shell
            else:
                os.environ.pop("SHELL", None)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_detect_shell_zsh(self):
        """Test shell detection identifies zsh."""
        original_shell = os.environ.get("SHELL", "")
        os.environ["SHELL"] = "/usr/bin/zsh"

        try:
            integration = PathIntegration()
            shell = integration.detect_shell()
            assert shell == "zsh"
        finally:
            if original_shell:
                os.environ["SHELL"] = original_shell
            else:
                os.environ.pop("SHELL", None)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    @patch("os.environ", {})
    @patch("mcp_server.daemon.path_integration.pwd")
    def test_detect_shell_from_passwd(self, mock_pwd):
        """Test shell detection falls back to /etc/passwd."""
        # Mock pwd module
        mock_user_info = MagicMock()
        mock_user_info.pw_shell = "/bin/zsh"
        mock_pwd.getpwuid.return_value = mock_user_info

        integration = PathIntegration()
        shell = integration.detect_shell()
        assert shell == "zsh"

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    @patch("os.environ", {})
    @patch("os.getuid", side_effect=AttributeError("getuid not available"))
    def test_detect_shell_defaults_to_bash(self, mock_getuid):
        """Test shell detection defaults to bash when detection fails."""
        integration = PathIntegration()
        shell = integration.detect_shell()
        assert shell == "bash"


class TestUnixSnippetGeneration:
    """Test Unix shell rc snippet generation."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_generate_unix_snippet_bash(self):
        """Test Unix snippet generation for bash."""
        original_shell = os.environ.get("SHELL", "")
        os.environ["SHELL"] = "/bin/bash"

        try:
            integration = PathIntegration()
            rc_file, snippet = integration.generate_unix_snippet()

            assert rc_file == "~/.bashrc"
            assert snippet == 'export PATH="$HOME/.graphiti/bin:$PATH"'
        finally:
            if original_shell:
                os.environ["SHELL"] = original_shell
            else:
                os.environ.pop("SHELL", None)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_generate_unix_snippet_zsh(self):
        """Test Unix snippet generation for zsh."""
        original_shell = os.environ.get("SHELL", "")
        os.environ["SHELL"] = "/bin/zsh"

        try:
            integration = PathIntegration()
            rc_file, snippet = integration.generate_unix_snippet()

            assert rc_file == "~/.zshrc"
            assert snippet == 'export PATH="$HOME/.graphiti/bin:$PATH"'
        finally:
            if original_shell:
                os.environ["SHELL"] = original_shell
            else:
                os.environ.pop("SHELL", None)


class TestWindowsRegistry:
    """Test Windows registry modification (mocked)."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_configure_windows_path_with_consent(self, tmp_path):
        """Test Windows registry modification with user consent."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        # Mock winreg at import level
        with patch("winreg.OpenKey") as mock_open_key, \
             patch("winreg.QueryValueEx") as mock_query, \
             patch("winreg.SetValueEx") as mock_set, \
             patch("winreg.CloseKey") as mock_close:

            mock_key = MagicMock()
            mock_open_key.return_value = mock_key
            mock_query.return_value = (r"C:\existing\path", None)

            integration = PathIntegration(bin_path=bin_path)
            success, msg = integration.configure_windows_path(consent=True)

            assert success is True
            assert "Successfully added" in msg
            mock_set.assert_called_once()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_configure_windows_path_without_consent(self, tmp_path):
        """Test Windows registry modification skipped without consent."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        integration = PathIntegration(bin_path=bin_path)
        success, msg = integration.configure_windows_path(consent=False)

        assert success is False
        assert "consent" in msg.lower()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_configure_windows_path_already_present(self, tmp_path):
        """Test Windows registry modification skipped if PATH already configured."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        integration = PathIntegration(bin_path=bin_path)

        # Mock detect_in_path to return True
        with patch.object(integration, 'detect_in_path', return_value=True):
            success, msg = integration.configure_windows_path(consent=True)

        assert success is True
        assert "already in PATH" in msg

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_configure_windows_path_permission_error(self, tmp_path):
        """Test Windows registry modification handles permission errors."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        # Mock winreg.OpenKey to raise PermissionError
        with patch("winreg.OpenKey", side_effect=PermissionError("Access denied")):
            integration = PathIntegration(bin_path=bin_path)
            success, msg = integration.configure_windows_path(consent=True)

            assert success is False
            assert "Permission denied" in msg


class TestInstructionDisplay:
    """Test PATH instruction display."""

    @patch("builtins.print")
    def test_display_instructions_when_already_configured(self, mock_print, tmp_path):
        """Test display_instructions shows OK message when PATH configured."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        integration = PathIntegration(bin_path=bin_path)

        # Mock detect_in_path to return True
        with patch.object(integration, 'detect_in_path', return_value=True):
            integration.display_instructions()

        # Verify OK message was printed
        printed_text = " ".join(
            str(call[0][0]) if call[0] else ""
            for call in mock_print.call_args_list
        )
        assert "[OK]" in printed_text
        assert "already in your PATH" in printed_text

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    @patch("builtins.print")
    @patch("builtins.input", return_value="n")
    def test_display_windows_instructions_consent_declined(self, mock_input, mock_print, tmp_path):
        """Test Windows instructions when user declines consent."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        integration = PathIntegration(bin_path=bin_path)

        # Mock detect_in_path to return False
        with patch.object(integration, 'detect_in_path', return_value=False):
            integration.display_instructions()

        # Verify Windows-specific instructions were shown
        printed_text = " ".join(
            str(call[0][0]) if call[0] else ""
            for call in mock_print.call_args_list
        )
        assert "PowerShell" in printed_text or "System Properties" in printed_text

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    @patch("builtins.print")
    def test_display_unix_instructions(self, mock_print, tmp_path):
        """Test Unix instructions are displayed correctly."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        integration = PathIntegration(bin_path=bin_path)

        # Mock detect_in_path to return False
        with patch.object(integration, 'detect_in_path', return_value=False):
            integration.display_instructions()

        # Verify Unix-specific instructions were shown
        printed_text = " ".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "export PATH" in printed_text
        assert "source" in printed_text


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_path_integration_default_bin_path(self):
        """Test PathIntegration uses default bin path when not specified (v2.1 paths)."""
        from mcp_server.daemon.paths import get_install_dir
        integration = PathIntegration()
        expected_path = get_install_dir() / "bin"
        assert integration.bin_path == expected_path

    def test_path_integration_custom_bin_path(self, tmp_path):
        """Test PathIntegration uses custom bin path when specified."""
        custom_path = tmp_path / "custom_bin"
        integration = PathIntegration(bin_path=custom_path)
        assert integration.bin_path == custom_path

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_configure_windows_path_on_unix_fails(self, tmp_path):
        """Test Windows registry modification fails gracefully on Unix."""
        bin_path = tmp_path / "bin"
        bin_path.mkdir()

        integration = PathIntegration(bin_path=bin_path)
        success, msg = integration.configure_windows_path(consent=True)

        assert success is False
        assert "Windows" in msg

    def test_detect_in_path_with_nonexistent_bin_path(self, tmp_path):
        """Test PATH detection handles non-existent bin path gracefully."""
        bin_path = tmp_path / "nonexistent_bin"
        # Don't create the directory

        integration = PathIntegration(bin_path=bin_path)
        # Should not crash, should return False
        result = integration.detect_in_path()
        assert result is False
