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

Design Principle: The daemon uses a dedicated venv at the platform-specific
install directory to isolate its dependencies from the user's Python environment.

See: .claude/sprint/stories/1-dedicated-venv-creation.md
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from .paths import get_install_dir

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
            venv_path: Path to venv directory. Defaults to platform-specific install dir from paths.py
        """
        if venv_path is None:
            venv_path = get_install_dir() / ".venv"
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
            VenvCreationError: If venv does not exist or pip not found
        """
        if not self.detect_venv():
            raise VenvCreationError(
                f"Venv does not exist at {self.venv_path}. "
                "Call create_venv() first."
            )

        if sys.platform == "win32":
            # Try multiple pip executable names (pip.exe, pip3.exe)
            scripts_dir = self.venv_path / "Scripts"
            for pip_name in ["pip.exe", "pip3.exe"]:
                pip_exe = scripts_dir / pip_name
                if pip_exe.exists():
                    return pip_exe
            raise VenvCreationError(
                f"Pip executable not found in venv Scripts: {scripts_dir}"
            )
        else:
            # Unix: try pip, pip3
            bin_dir = self.venv_path / "bin"
            for pip_name in ["pip", "pip3"]:
                pip_exe = bin_dir / pip_name
                if pip_exe.exists():
                    return pip_exe
            raise VenvCreationError(
                f"Pip executable not found in venv bin: {bin_dir}"
            )

    def get_uv_executable(self) -> Optional[Path]:
        """
        Get path to uv executable in the venv (if uv was used to create it).

        Returns:
            Path to uv executable if found, None otherwise
        """
        if not self.detect_venv():
            return None

        if sys.platform == "win32":
            uv_exe = self.venv_path / "Scripts" / "uv.exe"
        else:
            uv_exe = self.venv_path / "bin" / "uv"

        if uv_exe.exists():
            logger.debug(f"uv found in venv: {uv_exe}")
            return uv_exe

        logger.debug("uv not found in venv")
        return None

    def detect_repo_location(self) -> Optional[Path]:
        """
        Dynamically detect the repository location.

        Searches for a directory containing mcp_server/pyproject.toml.

        Detection order:
        1. GRAPHITI_REPO_PATH environment variable (explicit override)
        2. Current working directory (covers most dev/test scenarios)
        3. __file__ location search (for installed package scenarios)
        4. Upward from venv path (legacy fallback)

        Note: This method is used for development/installation scenarios.
        At runtime, the bootstrap service uses the deployed package at the
        platform-specific install directory (see package_deployer.py and bootstrap.py).

        Returns:
            Path to repository root if found, None otherwise
        """
        import os

        def _check_path(path: Path, source: str) -> Optional[Path]:
            """Check if path contains mcp_server/pyproject.toml."""
            try:
                resolved = path.resolve()
                pyproject = resolved / "mcp_server" / "pyproject.toml"
                if pyproject.exists():
                    logger.debug(f"Repository found at: {resolved} (via {source})")
                    return resolved
            except Exception:
                pass
            return None

        # 1. Check environment variable override
        env_path = os.environ.get("GRAPHITI_REPO_PATH")
        if env_path:
            result = _check_path(Path(env_path), "GRAPHITI_REPO_PATH env")
            if result:
                return result
            logger.warning(f"GRAPHITI_REPO_PATH set but invalid: {env_path}")

        # 2. Check current working directory (most common for tests and dev)
        result = _check_path(Path.cwd(), "current directory")
        if result:
            return result

        # 3. Check __file__ location (for when running as installed package)
        try:
            # Go up from venv_manager.py: daemon/ -> mcp_server/ -> repo_root/
            file_path = Path(__file__).resolve()
            repo_candidate = file_path.parent.parent.parent
            result = _check_path(repo_candidate, "__file__ location")
            if result:
                return result
        except Exception:
            pass

        # 4. Legacy: Search upward from venv path
        current = self.venv_path.resolve()
        for _ in range(5):
            result = _check_path(current, "venv upward search")
            if result:
                return result
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent

        logger.warning(
            f"Repository not found. Checked: CWD ({Path.cwd()}), "
            f"venv upward ({self.venv_path})"
        )
        return None

    def validate_installation(self, package_name: str = "mcp_server") -> bool:
        """
        Validate that a package was installed successfully by attempting to import it.

        Args:
            package_name: Name of package to validate (default: mcp_server)

        Returns:
            True if package is importable, False otherwise
        """
        if not self.detect_venv():
            logger.error("Cannot validate installation: venv does not exist")
            return False

        python_exe = self.get_python_executable()

        # Try to import the package using venv's Python
        try:
            result = subprocess.run(
                [str(python_exe), "-c", f"import {package_name}"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )

            if result.returncode == 0:
                logger.debug(f"Package '{package_name}' is importable")
                return True
            else:
                logger.warning(
                    f"Package '{package_name}' not importable: {result.stderr.strip()}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"Import validation timed out for '{package_name}'")
            return False
        except Exception as e:
            logger.error(f"Error validating installation: {e}")
            return False

    def install_package(self) -> Tuple[bool, str]:
        """
        Install mcp_server package into the venv from requirements.txt.

        Installs dependencies from requirements.txt in platform-specific install directory.
        Uses uvx (preferred), then uv pip, then standard pip.

        Returns:
            Tuple of (success: bool, message: str)

        Raises:
            VenvCreationError: If venv does not exist
        """
        if not self.detect_venv():
            raise VenvCreationError(
                f"Venv does not exist at {self.venv_path}. "
                "Call create_venv() first."
            )

        # Validate requirements.txt exists
        requirements_path = get_install_dir() / "requirements.txt"
        if not requirements_path.exists():
            error_msg = (
                f"Requirements file not found at {requirements_path}. "
                "Please run the daemon installation process first."
            )
            logger.error(error_msg)
            return False, error_msg

        logger.debug(f"Using requirements file: {requirements_path}")

        # Determine which tool to use (prefer uvx, then uv pip, then pip)
        # Check for uvx in PATH first
        uvx_path = shutil.which("uvx")
        if uvx_path:
            pip_command = [uvx_path, "pip", "install"]
            tool_name = "uvx"
        else:
            # Check for uv in venv
            uv_exe = self.get_uv_executable()
            if uv_exe:
                pip_command = [str(uv_exe), "pip", "install"]
                tool_name = "uv pip"
            else:
                # Fallback to standard pip
                pip_exe = self.get_pip_executable()
                pip_command = [str(pip_exe), "install"]
                tool_name = "pip"

        # Build install command (install from requirements.txt)
        install_command = pip_command + ["-r", str(requirements_path), "--quiet"]

        logger.info(f"Installing dependencies from {requirements_path} using {tool_name}")
        logger.debug(f"Install command: {' '.join(install_command)}")

        try:
            result = subprocess.run(
                install_command,
                # No cwd needed - requirements.txt has absolute path
                capture_output=True,
                text=True,
                check=False,
                timeout=300,  # 5 minute timeout for package installation
            )

            if result.returncode != 0:
                error_output = result.stderr.strip() or result.stdout.strip()
                error_msg = (
                    f"Package installation failed with exit code {result.returncode}\n"
                    f"Error: {error_output}"
                )
                logger.error(error_msg)
                return False, error_msg

            # Validate installation succeeded
            if not self.validate_installation("mcp_server"):
                error_msg = (
                    "Package installation reported success but validation failed. "
                    "Package is not importable."
                )
                logger.error(error_msg)
                return False, error_msg

            msg = f"Successfully installed mcp_server package using {tool_name}"
            logger.info(msg)
            return True, msg

        except subprocess.TimeoutExpired:
            error_msg = "Package installation timed out (exceeded 5 minutes)"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during package installation: {e}"
            logger.error(error_msg)
            return False, error_msg
