"""
Graphiti PATH Integration

Handles PATH detection and provides platform-specific instructions for adding
~/.graphiti/bin/ to the user's PATH.

This module provides:
- Detection of ~/.graphiti/bin/ in current PATH
- Platform-specific PATH configuration instructions
- Optional Windows registry modification (with user consent)
- Unix shell rc file snippet generation
- Shell detection (bash/zsh) on Unix systems

Design Principle: Provide clear, actionable PATH instructions after daemon install,
with optional automation on Windows and copy-pastable snippets on Unix.

See: .claude/sprint/stories/4-path-integration.md
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class PathIntegrationError(Exception):
    """Raised when PATH integration operations fail."""
    pass


class PathIntegration:
    """Manager for PATH detection and configuration."""

    def __init__(self, bin_path: Optional[Path] = None):
        """
        Initialize PathIntegration.

        Args:
            bin_path: Path to bin directory. Defaults to ~/.graphiti/bin/
        """
        if bin_path is None:
            bin_path = Path.home() / ".graphiti" / "bin"
        self.bin_path = bin_path

    def detect_in_path(self) -> bool:
        """
        Detect if ~/.graphiti/bin/ is in the current PATH.

        Normalizes paths for comparison to handle:
        - Symlinks (resolved to real paths)
        - Tilde expansion (~/ -> /home/user/)
        - Case sensitivity on Windows

        Returns:
            True if bin_path is in PATH, False otherwise
        """
        path_env = os.environ.get("PATH", "")
        if not path_env:
            logger.debug("PATH environment variable is empty or missing")
            return False

        # Platform-specific path delimiter
        delimiter = ";" if sys.platform == "win32" else ":"

        # Split PATH and normalize each entry
        path_entries = path_env.split(delimiter)

        # Normalize our target bin path
        try:
            target_path = self.bin_path.resolve()
        except Exception as e:
            logger.warning(f"Failed to resolve bin_path {self.bin_path}: {e}")
            # If we can't resolve, compare strings directly
            target_path_str = str(self.bin_path.expanduser())
            for entry in path_entries:
                if entry.strip() == target_path_str:
                    logger.debug(f"bin_path found in PATH (string match): {entry}")
                    return True
            return False

        # Check each PATH entry
        for entry in path_entries:
            if not entry.strip():
                continue

            try:
                entry_path = Path(entry).resolve()
                if entry_path == target_path:
                    logger.debug(f"bin_path found in PATH: {entry}")
                    return True
            except Exception:
                # Skip invalid path entries
                continue

        logger.debug(f"bin_path not found in PATH: {self.bin_path}")
        return False

    def detect_shell(self) -> str:
        """
        Detect user's shell on Unix systems.

        Checks $SHELL environment variable, falls back to /etc/passwd entry.
        Defaults to bash if detection fails.

        Returns:
            Shell name (e.g., "bash", "zsh")
        """
        # Check $SHELL environment variable
        shell_env = os.environ.get("SHELL", "")
        if shell_env:
            shell_name = Path(shell_env).name
            logger.debug(f"Detected shell from $SHELL: {shell_name}")
            return shell_name

        # Fallback: try /etc/passwd
        try:
            import pwd
            user_info = pwd.getpwuid(os.getuid())
            shell_path = user_info.pw_shell
            shell_name = Path(shell_path).name
            logger.debug(f"Detected shell from /etc/passwd: {shell_name}")
            return shell_name
        except Exception as e:
            logger.debug(f"Failed to detect shell from /etc/passwd: {e}")

        # Default to bash
        logger.debug("Shell detection failed, defaulting to bash")
        return "bash"

    def generate_unix_snippet(self) -> Tuple[str, str]:
        """
        Generate Unix shell rc file snippet for adding bin_path to PATH.

        Detects user's shell and generates appropriate rc file snippet.

        Returns:
            Tuple of (rc_file: str, snippet: str)
            - rc_file: Path to shell rc file (e.g., ~/.bashrc)
            - snippet: Copy-pastable export command
        """
        shell = self.detect_shell()

        # Determine rc file based on shell
        if shell == "zsh":
            rc_file = "~/.zshrc"
        else:
            # Default to bash (covers bash, sh, etc.)
            rc_file = "~/.bashrc"

        # Generate export snippet
        snippet = f'export PATH="$HOME/.graphiti/bin:$PATH"'

        logger.debug(f"Generated Unix snippet for {shell}: {snippet}")
        return rc_file, snippet

    def configure_windows_path(self, consent: bool = False) -> Tuple[bool, str]:
        """
        Optionally modify Windows user PATH via registry (requires user consent).

        This method adds ~/.graphiti/bin/ to the user PATH environment variable
        via registry modification. Requires explicit user consent.

        Args:
            consent: User consent for registry modification (default: False)

        Returns:
            Tuple of (success: bool, message: str)

        Raises:
            PathIntegrationError: If registry modification fails
        """
        if not consent:
            msg = "Registry modification requires explicit user consent"
            logger.debug(msg)
            return False, msg

        if sys.platform != "win32":
            msg = "Windows registry modification only available on Windows"
            logger.warning(msg)
            return False, msg

        # Check if already in PATH
        if self.detect_in_path():
            msg = f"{self.bin_path} already in PATH, skipping registry modification"
            logger.info(msg)
            return True, msg

        try:
            import winreg

            # Open HKEY_CURRENT_USER\Environment
            key_path = r"Environment"
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_READ | winreg.KEY_WRITE
            )

            try:
                # Read current PATH value
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                # PATH doesn't exist in user environment (rare)
                current_path = ""

            # Add our bin path if not present
            bin_path_str = str(self.bin_path)
            if bin_path_str in current_path:
                winreg.CloseKey(key)
                msg = f"{self.bin_path} already in registry PATH"
                logger.info(msg)
                return True, msg

            # Append to PATH (use semicolon separator)
            if current_path and not current_path.endswith(";"):
                new_path = f"{current_path};{bin_path_str}"
            else:
                new_path = f"{current_path}{bin_path_str}"

            # Write updated PATH
            winreg.SetValueEx(
                key,
                "Path",
                0,
                winreg.REG_EXPAND_SZ,
                new_path
            )
            winreg.CloseKey(key)

            msg = f"Successfully added {self.bin_path} to user PATH via registry"
            logger.info(msg)

            # Notify user about restart requirement
            msg += "\nNote: Restart terminal/IDE for PATH changes to take effect"
            return True, msg

        except PermissionError:
            error_msg = (
                "Permission denied: Cannot modify registry.\n"
                "Try running with administrator privileges."
            )
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Registry modification failed: {e}"
            logger.error(error_msg)
            return False, error_msg

    def display_instructions(self) -> None:
        """
        Display platform-specific PATH configuration instructions.

        Output format varies by platform:
        - Windows: GUI instructions + PowerShell command
        - Unix: Shell rc snippet + source command

        If PATH is already configured, displays confirmation message.
        """
        print()
        print("=" * 60)
        print("PATH Configuration")
        print("=" * 60)
        print()

        # Check if PATH is already configured
        if self.detect_in_path():
            print(f"[OK] {self.bin_path} is already in your PATH")
            print()
            print("You can now use Graphiti commands directly:")
            print("  graphiti-mcp")
            print("  graphiti-mcp-daemon")
            print("  graphiti-bootstrap")
            return

        # Platform-specific instructions
        if sys.platform == "win32":
            self._display_windows_instructions()
        else:
            self._display_unix_instructions()

    def _display_windows_instructions(self) -> None:
        """Display Windows-specific PATH instructions."""
        print(f"[ACTION REQUIRED] Add {self.bin_path} to your PATH")
        print()
        print("Option 1: GUI (Manual)")
        print("  1. Open System Properties > Advanced > Environment Variables")
        print("  2. Under 'User variables', select 'Path' and click 'Edit'")
        print(f"  3. Click 'New' and add: {self.bin_path}")
        print("  4. Click 'OK' to save")
        print()
        print("Option 2: PowerShell (Automatic)")
        print(f"  Run this command in PowerShell (as Administrator):")
        print()
        print(f'  $env:Path += ";{self.bin_path}"')
        print(f'  [Environment]::SetEnvironmentVariable("Path", $env:Path, "User")')
        print()
        print("Option 3: Let this installer do it (requires consent)")
        print()

        # Prompt for consent
        try:
            response = input("  Modify registry to add PATH? (y/n): ").strip().lower()
            if response == 'y':
                print()
                print("  Modifying registry...")
                success, msg = self.configure_windows_path(consent=True)
                if success:
                    print(f"  [OK] {msg}")
                else:
                    print(f"  [FAILED] {msg}")
                    print()
                    print("  Please use Option 1 or 2 above to configure PATH manually")
            else:
                print()
                print("  [SKIPPED] Registry modification declined")
                print("  Please use Option 1 or 2 above to configure PATH manually")
        except EOFError:
            # Non-interactive environment (e.g., piped input)
            print()
            print("  [SKIPPED] Non-interactive environment, cannot prompt for consent")
            print("  Please use Option 1 or 2 above to configure PATH manually")

        print()
        print("After configuring PATH, restart your terminal/IDE")

    def _display_unix_instructions(self) -> None:
        """Display Unix-specific PATH instructions."""
        rc_file, snippet = self.generate_unix_snippet()

        print(f"[ACTION REQUIRED] Add {self.bin_path} to your PATH")
        print()
        print(f"Add this line to {rc_file}:")
        print()
        print(f"  {snippet}")
        print()
        print("Then reload your shell:")
        print()
        print(f"  source {rc_file}")
        print()
        print("Or restart your terminal")
