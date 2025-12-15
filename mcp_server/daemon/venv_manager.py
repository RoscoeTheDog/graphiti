"""
Graphiti Venv Manager

Dedicated module for creating and managing isolated virtual environments
for the Graphiti MCP daemon.

This module provides:
- Venv creation using uv (preferred) or python -m venv (fallback)
- Detection and validation of existing venvs
- Python version compatibility checks (>=3.10)
- Idempotent operations (safe to run multiple times)
- Platform-agnostic path handling

Design Principle: The daemon uses a dedicated venv at ~/.graphiti/.venv/
to isolate its dependencies from the user's Python environment.

See: .claude/sprint/stories/1-dedicated-venv-creation.md
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class VenvCreationError(Exception):
    """Raised when venv creation fails."""
    pass


class IncompatiblePythonVersionError(Exception):
    """Raised when Python version is incompatible."""
    pass


class VenvManager:
    """Manager for creating and validating dedicated virtual environments."""

    # Minimum Python version required (3.10)
    MIN_PYTHON_VERSION = (3, 10)

    def __init__(self, venv_path: Optional[Path] = None):
        """
        Initialize VenvManager.

        Args:
            venv_path: Path to venv directory. Defaults to ~/.graphiti/.venv/
        """
        if venv_path is None:
            venv_path = Path.home() / ".graphiti" / ".venv"
        self.venv_path = venv_path

    def validate_python_version(self) -> bool:
        """
        Validate that current Python version meets requirements.

        Returns:
            True if Python version >= 3.10

        Raises:
            IncompatiblePythonVersionError: If Python version < 3.10
        """
        current_version = sys.version_info[:2]
        if current_version < self.MIN_PYTHON_VERSION:
            raise IncompatiblePythonVersionError(
                f"Python {self.MIN_PYTHON_VERSION[0]}.{self.MIN_PYTHON_VERSION[1]}+ required, "
                f"but running Python {current_version[0]}.{current_version[1]}"
            )
        return True

    def check_uv_available(self) -> bool:
        """
        Check if uv is available in PATH.

        Returns:
            True if uv is available, False otherwise
        """
        uv_path = shutil.which("uv")
        if uv_path:
            logger.debug(f"uv found at: {uv_path}")
            return True
        logger.debug("uv not found in PATH")
        return False

    def detect_venv(self) -> bool:
        """
        Detect if a valid venv exists at the configured path.

        A venv is considered valid if:
        - The directory exists
        - Contains pyvenv.cfg (marker file for venvs)
        - Contains activate script (platform-specific)

        Returns:
            True if valid venv exists, False otherwise
        """
        if not self.venv_path.exists():
            logger.debug(f"Venv path does not exist: {self.venv_path}")
            return False

        # Check for pyvenv.cfg (standard venv marker)
        pyvenv_cfg = self.venv_path / "pyvenv.cfg"
        if not pyvenv_cfg.exists():
            logger.debug(f"Missing pyvenv.cfg in {self.venv_path}")
            return False

        # Check for activate script (platform-specific)
        if sys.platform == "win32":
            activate_script = self.venv_path / "Scripts" / "activate.bat"
        else:
            activate_script = self.venv_path / "bin" / "activate"

        if not activate_script.exists():
            logger.debug(f"Missing activate script: {activate_script}")
            return False

        logger.debug(f"Valid venv detected at: {self.venv_path}")
        return True

    def create_venv(self, force: bool = False) -> Tuple[bool, str]:
        """
        Create a dedicated venv at the configured path.

        Uses uv if available (faster), falls back to python -m venv.
        Idempotent: skips creation if venv already exists unless force=True.

        Args:
            force: If True, remove existing venv and recreate

        Returns:
            Tuple of (success: bool, message: str)

        Raises:
            VenvCreationError: If venv creation fails
            IncompatiblePythonVersionError: If Python version < 3.10
        """
        # Validate Python version first
        try:
            self.validate_python_version()
        except IncompatiblePythonVersionError as e:
            logger.error(f"Python version incompatible: {e}")
            raise

        # Check if venv already exists
        if not force and self.detect_venv():
            msg = f"Venv already exists at {self.venv_path}, skipping creation"
            logger.info(msg)
            return True, msg

        # Remove existing venv if force=True
        if force and self.venv_path.exists():
            logger.info(f"Removing existing venv at {self.venv_path} (force=True)")
            try:
                import shutil as shutil_rm
                shutil_rm.rmtree(self.venv_path)
            except Exception as e:
                raise VenvCreationError(f"Failed to remove existing venv: {e}")

        # Ensure parent directory exists
        self.venv_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine which tool to use
        use_uv = self.check_uv_available()
        tool_name = "uv" if use_uv else "python -m venv"
        logger.info(f"Creating venv using {tool_name} at {self.venv_path}")

        try:
            if use_uv:
                # Use uv venv (faster)
                result = subprocess.run(
                    ["uv", "venv", str(self.venv_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            else:
                # Fallback to python -m venv
                result = subprocess.run(
                    [sys.executable, "-m", "venv", str(self.venv_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )

            # Check result
            if result.returncode != 0:
                error_output = result.stderr.strip() or result.stdout.strip()
                raise VenvCreationError(
                    f"{tool_name} failed with exit code {result.returncode}\n"
                    f"Error: {error_output}"
                )

            # Verify venv was created successfully
            if not self.detect_venv():
                raise VenvCreationError(
                    f"Venv creation reported success but validation failed. "
                    f"Expected venv at {self.venv_path}"
                )

            msg = f"Successfully created venv at {self.venv_path} using {tool_name}"
            logger.info(msg)
            return True, msg

        except subprocess.SubprocessError as e:
            raise VenvCreationError(f"Subprocess error during venv creation: {e}")
        except Exception as e:
            raise VenvCreationError(f"Unexpected error during venv creation: {e}")

    def get_python_executable(self) -> Path:
        """
        Get path to Python executable in the venv.

        Returns:
            Path to python executable

        Raises:
            VenvCreationError: If venv does not exist
        """
        if not self.detect_venv():
            raise VenvCreationError(
                f"Venv does not exist at {self.venv_path}. "
                "Call create_venv() first."
            )

        if sys.platform == "win32":
            python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            python_exe = self.venv_path / "bin" / "python"

        if not python_exe.exists():
            raise VenvCreationError(
                f"Python executable not found in venv: {python_exe}"
            )

        return python_exe

    def get_pip_executable(self) -> Path:
        """
        Get path to pip executable in the venv.

        Returns:
            Path to pip executable

        Raises:
            VenvCreationError: If venv does not exist
        """
        if not self.detect_venv():
            raise VenvCreationError(
                f"Venv does not exist at {self.venv_path}. "
                "Call create_venv() first."
            )

        if sys.platform == "win32":
            pip_exe = self.venv_path / "Scripts" / "pip.exe"
        else:
            pip_exe = self.venv_path / "bin" / "pip"

        if not pip_exe.exists():
            raise VenvCreationError(
                f"Pip executable not found in venv: {pip_exe}"
            )

        return pip_exe
