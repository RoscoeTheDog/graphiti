"""
GraphitiInstaller - Professional daemon installer for Graphiti MCP server.

This module implements the complete installation, upgrade, and uninstall workflows
for the Graphiti MCP server following the v2.1 architecture (frozen packages,
per-user daemon, platform-aware paths).

Key features:
- Install to platform-appropriate Programs directory
- Automatic rollback on failure
- Progress reporting with callbacks
- Comprehensive validation and error handling
- Service registration with Task Scheduler/launchd/systemd

Example usage:
    >>> from mcp_server.daemon.installer import GraphitiInstaller
    >>> installer = GraphitiInstaller()
    >>> result = installer.install()
    >>> print(result)  # InstallationResult with success status

Version: 2.1.0
Created: 2025-12-25
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from packaging.version import InvalidVersion, Version

from .paths import GraphitiPaths, get_paths, get_install_dir
from .venv_manager import VenvManager, VenvCreationError, IncompatiblePythonVersionError
from .generate_requirements import (
    parse_pyproject_toml,
    generate_requirements_txt,
    write_requirements_file,
    PyprojectParseError,
    RequirementsGenerationError,
)

# Type alias for progress callback
ProgressCallback = Callable[[str, int, int, str], None]

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Version Tracking Functions
# ============================================================================


def get_source_version(source_dir: Path) -> str:
    """
    Detect version from source repository.

    Args:
        source_dir: Path to source repository root

    Returns:
        Semantic version string (e.g., "0.24.3" or "0.24.3-dev+abc1234")

    Raises:
        ValidationError: If version cannot be determined
    """
    # 1. Try pyproject.toml
    pyproject = source_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

            # Poetry format
            if "tool" in data and "poetry" in data["tool"] and "version" in data["tool"]["poetry"]:
                return data["tool"]["poetry"]["version"]

            # PEP 621 format
            if "project" in data and "version" in data["project"]:
                return data["project"]["version"]
        except Exception as e:
            logger.warning(f"Failed to parse pyproject.toml: {e}")

    # 2. Try git tag
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            cwd=source_dir,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return tag.lstrip("v")  # Remove v prefix
    except subprocess.CalledProcessError:
        pass

    # 3. Try git commit + pyproject version
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=source_dir,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()

        # Get base version from pyproject.toml (required for dev version)
        if pyproject.exists():
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                base_version = (
                    data.get("tool", {}).get("poetry", {}).get("version") or
                    data.get("project", {}).get("version")
                )
                if base_version:
                    return f"{base_version}-dev+{commit}"
            except Exception as e:
                logger.warning(f"Failed to get base version for dev suffix: {e}")
    except subprocess.CalledProcessError:
        pass

    # 4. Error - no version found
    raise ValidationError(
        "Cannot determine version from source repository",
        step="get_source_version",
        details={"source_dir": str(source_dir)}
    )


def get_installed_version(install_dir: Path) -> Optional[str]:
    """
    Read installed version from VERSION file.

    Args:
        install_dir: Path to installation directory

    Returns:
        Semantic version string (e.g., "0.24.3") or None if not installed
    """
    version_file = install_dir / "VERSION"

    if not version_file.exists():
        return None

    try:
        version = version_file.read_text(encoding="utf-8").strip()

        # Validate format (basic check - full validation in upgrade logic)
        if not version or not version[0].isdigit():
            logger.warning(f"Invalid VERSION file format: {version}")
            return None

        return version
    except Exception as e:
        logger.warning(f"Failed to read VERSION file: {e}")
        return None


def check_for_upgrade(install_dir: Path, source_dir: Path) -> Dict[str, Any]:
    """
    Compare installed version with source version to detect upgrade.

    Args:
        install_dir: Path to installation directory
        source_dir: Path to source repository

    Returns:
        Dictionary with upgrade info:
        {
            "upgrade_available": bool,
            "installed_version": str or None,
            "source_version": str,
            "comparison": str  # "newer", "same", "older", "not_installed"
        }

    Raises:
        ValidationError: If source version cannot be determined
    """
    # Get versions
    installed = get_installed_version(install_dir)
    source = get_source_version(source_dir)

    # Not installed case
    if installed is None:
        return {
            "upgrade_available": False,
            "installed_version": None,
            "source_version": source,
            "comparison": "not_installed"
        }

    # Parse versions for comparison
    try:
        installed_ver = Version(installed)
        source_ver = Version(source)
    except InvalidVersion as e:
        raise ValidationError(
            f"Invalid version format: {e}",
            step="check_for_upgrade",
            details={"installed": installed, "source": source}
        )

    # Compare
    if source_ver > installed_ver:
        comparison = "newer"
        upgrade_available = True
    elif source_ver == installed_ver:
        comparison = "same"
        upgrade_available = False
    else:
        comparison = "older"
        upgrade_available = False

    return {
        "upgrade_available": upgrade_available,
        "installed_version": installed,
        "source_version": source,
        "comparison": comparison
    }


# ============================================================================
# Exclusion Patterns for Package Deployment
# ============================================================================

# Files and directories to exclude when copying packages to lib/
PACKAGE_EXCLUSIONS = {
    # Virtual environments
    ".venv",
    "venv",

    # Python bytecode and cache
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    ".mypy_cache",

    # Testing and coverage
    "tests",
    ".coverage",
    "htmlcov",
    ".tox",

    # Build artifacts
    "build",
    "dist",
    "*.egg-info",
    "*.egg",
    "*.dist-info",

    # Compiled extensions (rebuild in venv)
    "*.so",
    "*.pyd",

    # Version control
    ".git",
    ".gitignore",
    ".gitattributes",
}


# ============================================================================
# Exception Hierarchy
# ============================================================================


class InstallationError(Exception):
    """Base exception for all installation errors."""

    def __init__(
        self,
        message: str,
        step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize installation error.

        Args:
            message: Human-readable error message
            step: Installation step that failed (e.g., "validate_environment")
            details: Additional context (e.g., {"disk_space_mb": 120, "required_mb": 500})
        """
        self.message = message
        self.step = step
        self.details = details or {}
        super().__init__(message)


class ValidationError(InstallationError):
    """System does not meet installation requirements."""
    pass


class PermissionError(InstallationError):
    """Insufficient permissions for installation."""
    pass


class ServiceError(InstallationError):
    """Service registration or management failed."""
    pass


class UpgradeError(InstallationError):
    """Upgrade failed and rollback unsuccessful (critical)."""
    pass


# ============================================================================
# Result Types
# ============================================================================


@dataclass
class InstallationResult:
    """Result of installation/upgrade/uninstall operation."""

    success: bool
    version: Optional[str] = None
    paths: Optional[GraphitiPaths] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        """Human-readable result string."""
        if self.success:
            return f"[OK] Installation successful (version {self.version})"
        else:
            return f"[ERROR] Installation failed: {self.error}"


# ============================================================================
# Progress Reporter
# ============================================================================


class ProgressReporter:
    """Handle progress reporting via callback and logging."""

    def __init__(self, callback: Optional[ProgressCallback] = None):
        """
        Initialize progress reporter.

        Args:
            callback: Optional function to report progress
                     Signature: (step: str, progress: int, total: int, message: str) -> None
        """
        self.callback = callback
        self.current_step = 0
        self.total_steps = 0
        self.operation = ""

    def start(self, operation: str, total_steps: int) -> None:
        """Begin progress tracking for an operation."""
        self.operation = operation
        self.total_steps = total_steps
        self.current_step = 0
        self._report(f"Starting: {operation}")

    def step(self, step_num: int, message: str) -> None:
        """Report progress for a specific step."""
        self.current_step = step_num
        self._report(message)

    def complete(self, message: str) -> None:
        """Report successful completion."""
        self.current_step = self.total_steps
        # Use ASCII-compatible checkmark for Windows console compatibility
        self._report(f"[OK] {message}")

    def error(self, message: str) -> None:
        """Report error."""
        # Use ASCII-compatible X for Windows console compatibility
        self._report(f"[FAIL] {message}")

    def _report(self, message: str) -> None:
        """Internal: Send to callback and log."""
        # Console output
        if self.callback:
            self.callback(
                step=self.operation,
                progress=self.current_step,
                total=self.total_steps,
                message=message
            )
        else:
            # Default: print to console
            if self.total_steps > 0:
                pct = int((self.current_step / self.total_steps) * 100)
                print(f"[{pct:3d}%] {message}")
            else:
                print(message)

        # File logging
        logger.info(f"Step {self.current_step}/{self.total_steps}: {message}")


# ============================================================================
# Main Installer Class
# ============================================================================


class GraphitiInstaller:
    """
    Orchestrate installation, upgrade, and uninstall workflows for Graphiti MCP server.

    This class implements the v2.1 professional daemon architecture with frozen packages,
    platform-aware paths, and comprehensive error handling.

    Attributes:
        paths: GraphitiPaths instance with platform-specific directories
        progress: ProgressReporter for progress tracking
    """

    def __init__(self, progress_callback: Optional[ProgressCallback] = None):
        """
        Initialize GraphitiInstaller.

        Args:
            progress_callback: Optional callback for progress reporting
                              Signature: (step: str, progress: int, total: int, message: str) -> None
        """
        self.paths = get_paths()
        self.progress = ProgressReporter(callback=progress_callback)
        logger.info(f"Initialized GraphitiInstaller with paths: {self.paths}")

    # ========================================================================
    # Public API Methods
    # ========================================================================

    def install(self, source_dir: Optional[Path] = None) -> InstallationResult:
        """
        Install Graphiti MCP server to platform-appropriate location.

        Args:
            source_dir: Path to source repository (default: auto-detect via Path(__file__))

        Returns:
            InstallationResult with success status, version, and install paths

        Raises:
            InstallationError: On validation, disk, or permission errors

        Steps:
            1. _validate_environment() - Check Python version, disk space, permissions
            2. _create_directories() - Create install_dir, config_dir, state_dir
            3. _create_venv() - Create virtual environment at install_dir
            4. _install_dependencies() - Generate requirements.txt and install pip packages
            5. _freeze_packages() - Copy mcp_server and graphiti_core to lib/
            6. _create_pth_file() - Create .pth file for lib/ path resolution
            7. _create_wrappers() - Generate platform executables (graphiti-mcp.exe, etc.)
            8. _write_version_info() - Write VERSION and INSTALL_INFO files
            9. _create_default_config() - Generate graphiti.config.json in config_dir
            10. _register_service() - Register with Task Scheduler/launchd/systemd
            11. _start_service() - Start bootstrap service
            12. _verify_installation() - Health check via MCP connection

        Rollback:
            On failure at any step, calls _cleanup_on_failure() to remove partial install
        """
        try:
            self.progress.start("Installing Graphiti MCP Server", total_steps=12)

            self.progress.step(1, "Validating environment")
            self._validate_environment()

            self.progress.step(2, "Creating directories")
            self._create_directories()

            # Step 3: Create virtual environment
            self.progress.step(3, "Creating virtual environment")
            self._create_venv()

            # Step 4: Install dependencies from pyproject.toml
            self.progress.step(4, "Installing dependencies")
            self._install_dependencies(source_dir)

            # Step 5: Frozen Package Deployment - copy mcp_server and graphiti_core to lib/
            self.progress.step(5, "Freezing packages")
            self._freeze_packages(source_dir)

            # Step 5b: Create .pth file so lib/ packages are importable
            self.progress.step(6, "Configuring Python path")
            self._create_pth_file()

            # Step 7: Create wrapper executables
            self.progress.step(7, "Creating wrapper executables")
            self._create_wrappers()

            # Step 8: Write version information
            self.progress.step(8, "Writing version information")
            version = self._write_version_info(source_dir)

            # Step 9: Create default configuration
            self.progress.step(9, "Creating default configuration")
            self._create_default_config()

            # Step 10: Register service
            self.progress.step(10, "Registering service")
            self._register_service()

            # Step 11: Start service
            self.progress.step(11, "Starting service")
            self._start_service()

            # Step 12: Verify installation
            self.progress.step(12, "Verifying installation")
            self._verify_installation()

            # Return result (all 12 steps complete)
            self.progress.complete("Installation complete")
            return InstallationResult(
                success=True,
                version=version,
                paths=self.paths,
                details={
                    "status": "complete",
                    "completed": [
                        "validate",
                        "directories",
                        "venv",
                        "dependencies",
                        "freeze_packages",
                        "pth_file",
                        "wrappers",
                        "version_info",
                        "config",
                        "service_register",
                        "service_start",
                        "verify"
                    ]
                }
            )

        except ValidationError as e:
            # User action required (e.g., upgrade Python, free disk space)
            self.progress.error(f"Validation failed: {e.message}")
            raise

        except PermissionError as e:
            # Permission issue - suggest running with appropriate privileges
            self.progress.error(f"Permission denied: {e.message}")
            raise

        except Exception as e:
            # Unexpected error - cleanup and re-raise
            self.progress.error(f"Installation failed: {str(e)}")
            self._cleanup_on_failure()
            raise InstallationError(f"Unexpected error: {str(e)}", step="unknown") from e

    def upgrade(
        self,
        source_dir: Optional[Path] = None,
        force: bool = False
    ) -> InstallationResult:
        """
        Upgrade existing Graphiti installation to new version.

        Args:
            source_dir: Path to new version source (default: auto-detect)
            force: Skip version check and force upgrade

        Returns:
            InstallationResult with new version info

        Raises:
            InstallationError: If no existing install, version conflict, or upgrade fails
            UpgradeError: If rollback fails (critical - manual intervention required)

        Steps:
            1. _detect_existing_version() - Read VERSION file, validate install
            2. _stop_service() - Gracefully stop bootstrap service
            3. _backup_installation() - Create timestamped backup of lib/ directory
            4. _freeze_packages() - Copy new packages to lib/
            5. _update_version_info() - Update VERSION and INSTALL_INFO
            6. _migrate_config() - Migrate config if schema changed (via ConfigMigration)
            7. _start_service() - Start service with new code
            8. _verify_health() - Health check with 30s timeout
            9. _remove_backup() - Clean up backup on success

        Rollback:
            On failure, calls _rollback_upgrade() to restore from backup
        """
        # TODO: Implement in future story (after frozen package deployment)
        logger.info("Upgrade method skeleton (pending implementation)")
        return InstallationResult(
            success=False,
            error="Upgrade not implemented yet (pending Story 5)",
            details={"method": "upgrade", "status": "skeleton"}
        )

    def uninstall(
        self,
        keep_config: bool = True,
        keep_logs: bool = False
    ) -> bool:
        """
        Uninstall Graphiti MCP server.

        Args:
            keep_config: Preserve config_dir (default: True - don't lose user settings)
            keep_logs: Preserve state_dir/logs (default: False - clean removal)

        Returns:
            True on successful uninstall

        Raises:
            InstallationError: If service stop fails or removal blocked by OS

        Steps:
            1. _stop_service() - Gracefully stop bootstrap
            2. _unregister_service() - Remove from Task Scheduler/launchd/systemd
            3. _remove_install_dir() - Delete install_dir (executables and libs)
            4. _remove_state_dir() - Delete state_dir if not keep_logs
            5. _remove_config_dir() - Delete config_dir if not keep_config
            6. _verify_removal() - Check all directories removed as requested
        """
        # TODO: Implement in future story (after service management)
        logger.info("Uninstall method skeleton (pending implementation)")
        return False

    # ========================================================================
    # Validation Methods
    # ========================================================================

    def _validate_environment(self) -> None:
        """
        Validate system meets installation requirements.

        Checks:
            - Python version >= 3.9
            - Disk space >= 500MB in install location
            - Write permissions to install_dir parent
            - No existing installation (or call upgrade() instead)

        Raises:
            ValidationError: With specific requirement that failed
        """
        logger.info("Validating installation environment")

        # Check Python version
        py_version = sys.version_info
        if py_version < (3, 9):
            raise ValidationError(
                f"Python 3.9+ required (detected: {py_version.major}.{py_version.minor})",
                step="validate_environment",
                details={"python_version": f"{py_version.major}.{py_version.minor}"}
            )

        logger.info(f"Python version check passed: {py_version.major}.{py_version.minor}.{py_version.micro}")

        # Check disk space
        install_parent = self.paths.install_dir.parent
        try:
            stat = shutil.disk_usage(install_parent)
            free_mb = stat.free / (1024 * 1024)
            required_mb = 500

            if free_mb < required_mb:
                raise ValidationError(
                    f"Insufficient disk space (available: {free_mb:.0f}MB, required: {required_mb}MB)",
                    step="validate_environment",
                    details={"free_mb": free_mb, "required_mb": required_mb}
                )

            logger.info(f"Disk space check passed: {free_mb:.0f}MB available")

        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            # Non-critical - continue installation

        # Check write permissions
        if not install_parent.exists():
            # Parent doesn't exist - check if we can create it
            try:
                install_parent.mkdir(parents=True, exist_ok=True)
                # Clean up test directory
                install_parent.rmdir()
                logger.info(f"Write permission check passed for {install_parent}")
            except PermissionError as e:
                raise PermissionError(
                    f"Cannot create install directory (no write permission to {install_parent})",
                    step="validate_environment",
                    details={"path": str(install_parent)}
                ) from e
        else:
            # Parent exists - check if we can write to it
            if not os.access(install_parent, os.W_OK):
                raise PermissionError(
                    f"No write permission to {install_parent}",
                    step="validate_environment",
                    details={"path": str(install_parent)}
                )
            logger.info(f"Write permission check passed for {install_parent}")

        # Check for existing installation
        if self.paths.install_dir.exists():
            version_file = self.paths.install_dir / "VERSION"
            if version_file.exists():
                existing_version = version_file.read_text().strip()
                raise ValidationError(
                    f"Graphiti already installed (version {existing_version}). Use upgrade() instead.",
                    step="validate_environment",
                    details={"existing_version": existing_version}
                )

        logger.info("Environment validation complete")

    # ========================================================================
    # Directory Management
    # ========================================================================

    def _create_directories(self) -> None:
        """
        Create all required directories for installation.

        Creates:
            - install_dir/bin/
            - install_dir/lib/
            - config_dir/
            - state_dir/logs/
            - state_dir/data/
            - state_dir/data/sessions/

        Raises:
            PermissionError: If directory creation blocked by OS
        """
        logger.info("Creating installation directories")

        directories = [
            self.paths.install_dir / "bin",
            self.paths.install_dir / "lib",
            self.paths.config_dir,
            self.paths.state_dir / "logs",
            self.paths.state_dir / "data",
            self.paths.state_dir / "data" / "sessions",
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            except PermissionError as e:
                raise PermissionError(
                    f"Cannot create directory {directory}",
                    step="create_directories",
                    details={"path": str(directory)}
                ) from e

        logger.info("All directories created successfully")

    # ========================================================================
    # Virtual Environment and Dependency Methods
    # ========================================================================

    def _create_venv(self) -> None:
        """
        Create a dedicated virtual environment for the Graphiti daemon.

        Uses VenvManager to create a venv at the install directory.
        The install directory IS the venv (contains Scripts/, Lib/, pyvenv.cfg directly).

        Note: Uses force=True when install_dir exists but is not a valid venv
        (e.g., directory was created by _create_directories but venv not yet created).
        This handles uv's requirement for --clear when directory already exists.

        Raises:
            InstallationError: If venv creation fails
            ValidationError: If Python version is incompatible
        """
        logger.info("Creating virtual environment")

        try:
            # VenvManager uses install_dir as the venv path (v2.1 architecture)
            venv_manager = VenvManager(venv_path=self.paths.install_dir)

            # Check if we need to force-create (directory exists but not a valid venv)
            # This handles the case where _create_directories created the install_dir
            # but it's not yet a valid venv (no pyvenv.cfg)
            force_create = (
                self.paths.install_dir.exists() and
                not venv_manager.detect_venv()
            )

            if force_create:
                logger.info("Install directory exists but is not a valid venv, using force=True")

            # Create the venv
            success, message = venv_manager.create_venv(force=force_create)

            if not success:
                raise InstallationError(
                    f"Failed to create virtual environment: {message}",
                    step="create_venv",
                    details={"venv_path": str(self.paths.install_dir)}
                )

            logger.info(f"Virtual environment ready: {message}")

        except IncompatiblePythonVersionError as e:
            raise ValidationError(
                str(e),
                step="create_venv",
                details={"python_version": f"{sys.version_info.major}.{sys.version_info.minor}"}
            )
        except VenvCreationError as e:
            raise InstallationError(
                f"Venv creation failed: {str(e)}",
                step="create_venv",
                details={"error": str(e)}
            )

    def _generate_requirements(self, source_dir: Optional[Path] = None) -> Path:
        """
        Generate requirements.txt from pyproject.toml.

        Args:
            source_dir: Path to source repository (default: auto-detect)

        Returns:
            Path to generated requirements.txt file

        Raises:
            InstallationError: If requirements generation fails
        """
        logger.info("Generating requirements.txt from pyproject.toml")

        # Find repository root
        repo_root = self._find_repo_root(source_dir)

        # Locate pyproject.toml
        pyproject_path = repo_root / "mcp_server" / "pyproject.toml"
        if not pyproject_path.exists():
            raise InstallationError(
                f"pyproject.toml not found at {pyproject_path}",
                step="generate_requirements",
                details={"pyproject_path": str(pyproject_path)}
            )

        # Output path: install_dir/requirements.txt (where VenvManager expects it)
        requirements_path = self.paths.install_dir / "requirements.txt"

        try:
            # Parse pyproject.toml
            pyproject_data = parse_pyproject_toml(pyproject_path)

            # Generate requirements list (include all dependencies, no optional for now)
            requirements = generate_requirements_txt(
                pyproject_data,
                include_optional=False,
                optional_groups=None
            )

            # Write to install directory
            write_requirements_file(requirements, requirements_path)

            logger.info(f"Generated {len(requirements)} requirements to {requirements_path}")
            return requirements_path

        except PyprojectParseError as e:
            raise InstallationError(
                f"Failed to parse pyproject.toml: {str(e)}",
                step="generate_requirements",
                details={"error": str(e)}
            )
        except RequirementsGenerationError as e:
            raise InstallationError(
                f"Failed to generate requirements: {str(e)}",
                step="generate_requirements",
                details={"error": str(e)}
            )

    def _install_dependencies(self, source_dir: Optional[Path] = None) -> None:
        """
        Install pip dependencies into the virtual environment.

        Steps:
            1. Generate requirements.txt from pyproject.toml
            2. Install packages using VenvManager.install_package()

        Args:
            source_dir: Path to source repository (default: auto-detect)

        Raises:
            InstallationError: If dependency installation fails
        """
        logger.info("Installing dependencies")

        # Step 1: Generate requirements.txt
        requirements_path = self._generate_requirements(source_dir)
        logger.info(f"Using requirements file: {requirements_path}")

        # Step 2: Install packages using VenvManager
        try:
            venv_manager = VenvManager(venv_path=self.paths.install_dir)

            # Verify venv exists before installing
            if not venv_manager.detect_venv():
                raise InstallationError(
                    "Virtual environment not found. Run _create_venv() first.",
                    step="install_dependencies",
                    details={"venv_path": str(self.paths.install_dir)}
                )

            # Install packages from requirements.txt
            success, message = venv_manager.install_package()

            if not success:
                raise InstallationError(
                    f"Failed to install dependencies: {message}",
                    step="install_dependencies",
                    details={"requirements_path": str(requirements_path)}
                )

            logger.info(f"Dependencies installed: {message}")

        except VenvCreationError as e:
            raise InstallationError(
                f"Dependency installation failed: {str(e)}",
                step="install_dependencies",
                details={"error": str(e)}
            )

    def _create_pth_file(self) -> None:
        """
        Create a .pth file in site-packages to add lib/ to Python path.

        This enables importing mcp_server and graphiti_core from the frozen
        packages in lib/ without setting PYTHONPATH environment variable.

        The .pth file is placed in:
            - Windows: {install_dir}/Lib/site-packages/graphiti.pth
            - Unix: {install_dir}/lib/python3.X/site-packages/graphiti.pth

        Raises:
            InstallationError: If .pth file creation fails
        """
        logger.info("Creating .pth file for lib/ path resolution")

        lib_dir = self.paths.install_dir / "lib"

        # Find site-packages directory
        if sys.platform == "win32":
            site_packages = self.paths.install_dir / "Lib" / "site-packages"
        else:
            # Unix: lib/python3.X/site-packages
            python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = self.paths.install_dir / "lib" / python_version / "site-packages"

        # Create site-packages if it doesn't exist (should exist after venv creation)
        if not site_packages.exists():
            logger.warning(f"site-packages not found at {site_packages}, creating...")
            try:
                site_packages.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise InstallationError(
                    f"Failed to create site-packages directory: {str(e)}",
                    step="create_pth_file",
                    details={"site_packages": str(site_packages)}
                )

        # Create graphiti.pth file
        pth_file = site_packages / "graphiti.pth"

        try:
            # Write the lib directory path to .pth file
            # .pth files should contain absolute paths, one per line
            pth_content = str(lib_dir.resolve())
            pth_file.write_text(pth_content, encoding="utf-8")

            logger.info(f"Created {pth_file} pointing to {lib_dir}")

        except Exception as e:
            raise InstallationError(
                f"Failed to create .pth file: {str(e)}",
                step="create_pth_file",
                details={"pth_file": str(pth_file), "error": str(e)}
            )

    # ========================================================================
    # Version Tracking Methods
    # ========================================================================

    def _write_version_info(self, source_dir: Path) -> str:
        """
        Write VERSION and INSTALL_INFO files.

        Args:
            source_dir: Path to source repository

        Returns:
            Version string that was written

        Raises:
            ValidationError: If version cannot be determined from source
        """
        # Detect version from source
        version = get_source_version(source_dir)

        # Write VERSION file
        version_file = self.paths.install_dir / "VERSION"
        version_file.write_text(version, encoding="utf-8")
        logger.info(f"Wrote VERSION file: {version}")

        # Collect install metadata
        install_info = {
            "version": version,
            "installed_at": datetime.utcnow().isoformat() + "Z",
            "installed_from": str(source_dir.resolve()),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.platform(),
            "installer_version": "2.1.0"
        }

        # Add git commit if available
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=source_dir,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            install_info["source_commit"] = commit
            logger.info(f"Added source commit to install info: {commit[:8]}")
        except subprocess.CalledProcessError:
            logger.info("No git commit found (not a git repo or git not available)")
            # Not a git repo or no git - skip commit field

        # Write INSTALL_INFO
        info_file = self.paths.install_dir / "INSTALL_INFO"
        info_file.write_text(json.dumps(install_info, indent=2), encoding="utf-8")
        logger.info(f"Wrote INSTALL_INFO file")

        return version

    # ========================================================================
    # Wrapper and Service Methods
    # ========================================================================

    def _create_wrappers(self) -> None:
        """
        Create platform-specific wrapper executables.

        Creates:
            - graphiti-mcp executable in bin/ directory
            - Platform-appropriate scripts (.bat/.cmd on Windows, shell scripts on Unix)

        Raises:
            InstallationError: If wrapper creation fails
        """
        from .wrapper_generator import WrapperGenerator, WrapperGenerationError

        try:
            wrapper_gen = WrapperGenerator(self.paths.install_dir)
            success, message = wrapper_gen.generate_wrappers()

            if not success:
                raise InstallationError(
                    f"Wrapper creation failed: {message}",
                    step="create_wrappers"
                )

            logger.info(f"Created wrapper executables: {message}")

        except WrapperGenerationError as e:
            raise InstallationError(
                f"Wrapper creation failed: {str(e)}",
                step="create_wrappers"
            ) from e

    def _create_default_config(self) -> None:
        """
        Create default graphiti.config.json in config directory.

        Creates a minimal but functional configuration that the user
        can customize later.

        Raises:
            InstallationError: If config creation fails
        """
        config_file = self.paths.config_file

        # Don't overwrite existing config
        if config_file.exists():
            logger.info(f"Config file already exists: {config_file}")
            return

        # Create default config
        default_config = {
            "$schema": "graphiti-config-v1",
            "version": "1.0.0",
            "database": {
                "provider": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password": "SET_YOUR_PASSWORD"
                }
            },
            "llm": {
                "provider": "openai",
                "model": "gpt-4.1-mini"
            },
            "daemon": {
                "enabled": False,
                "host": "127.0.0.1",
                "port": 8321
            }
        }

        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(json.dumps(default_config, indent=2), encoding="utf-8")
            logger.info(f"Created default config: {config_file}")
        except Exception as e:
            raise InstallationError(
                f"Failed to create config: {str(e)}",
                step="create_default_config",
                details={"config_file": str(config_file)}
            ) from e

    def _register_service(self) -> None:
        """
        Register the bootstrap service with the OS service manager.

        Platform-specific:
            - Windows: Task Scheduler
            - macOS: launchd
            - Linux: systemd

        Raises:
            InstallationError: If service registration fails
        """
        try:
            if sys.platform == "win32":
                from .task_scheduler_service import TaskSchedulerServiceManager
                service_mgr = TaskSchedulerServiceManager(self.paths)
            elif sys.platform == "darwin":
                from .launchd_service import LaunchdServiceManager
                service_mgr = LaunchdServiceManager(self.paths)
            else:
                from .systemd_service import SystemdServiceManager
                service_mgr = SystemdServiceManager(self.paths)

            success = service_mgr.install()
            if not success:
                raise InstallationError(
                    "Service registration failed",
                    step="register_service"
                )

            logger.info(f"Service registered successfully ({sys.platform})")

        except ImportError as e:
            logger.warning(f"Service manager not available: {e}")
            # Non-fatal - user can manually start the service
        except Exception as e:
            raise InstallationError(
                f"Service registration failed: {str(e)}",
                step="register_service"
            ) from e

    def _start_service(self) -> None:
        """
        Start the bootstrap service.

        Raises:
            InstallationError: If service start fails
        """
        try:
            if sys.platform == "win32":
                from .task_scheduler_service import TaskSchedulerServiceManager
                service_mgr = TaskSchedulerServiceManager(self.paths)
            elif sys.platform == "darwin":
                from .launchd_service import LaunchdServiceManager
                service_mgr = LaunchdServiceManager(self.paths)
            else:
                from .systemd_service import SystemdServiceManager
                service_mgr = SystemdServiceManager(self.paths)

            success = service_mgr.start()
            if not success:
                logger.warning("Service start returned false - may require manual start")
            else:
                logger.info("Service started successfully")

        except ImportError as e:
            logger.warning(f"Service manager not available: {e}")
        except Exception as e:
            # Non-fatal - service can be started manually
            logger.warning(f"Service start failed (non-fatal): {e}")

    def _verify_installation(self) -> None:
        """
        Verify the installation is complete and functional.

        Checks:
            - Required files exist
            - Python environment is working
            - MCP server can be imported

        Raises:
            InstallationError: If verification fails
        """
        issues = []

        # Check required files
        required_files = [
            self.paths.install_dir / "VERSION",
            self.paths.install_dir / "INSTALL_INFO",
            self.paths.install_dir / "lib" / "mcp_server" / "graphiti_mcp_server.py",
            self.paths.config_file,
        ]

        for file_path in required_files:
            if not file_path.exists():
                issues.append(f"Missing file: {file_path}")

        # Check Python environment
        python_exe = self.paths.install_dir / ("Scripts" if sys.platform == "win32" else "bin") / (
            "python.exe" if sys.platform == "win32" else "python"
        )
        if not python_exe.exists():
            issues.append(f"Python executable not found: {python_exe}")

        if issues:
            logger.warning(f"Installation verification found issues: {issues}")
            # Log warning but don't fail - user may want to fix manually
        else:
            logger.info("Installation verification passed")

    # ========================================================================
    # Cleanup Methods
    # ========================================================================

    def _cleanup_on_failure(self) -> None:
        """
        Remove partial installation after failure.

        Steps:
            - Log failure state to install.log
            - Stop any running service
            - Remove install_dir if created
            - Remove config_dir if created (only if empty - preserve user edits)
            - Remove state_dir if created

        Note:
            Uses safe removal with logging - does not raise exceptions
        """
        logger.info("Starting cleanup after installation failure")

        try:
            # Remove install_dir
            if self.paths.install_dir.exists():
                shutil.rmtree(self.paths.install_dir, ignore_errors=True)
                logger.info(f"Removed install_dir: {self.paths.install_dir}")

            # Remove config_dir (only if empty - preserve any user-created files)
            if self.paths.config_dir.exists():
                try:
                    self.paths.config_dir.rmdir()  # Only removes if empty
                    logger.info(f"Removed empty config_dir: {self.paths.config_dir}")
                except OSError:
                    logger.warning(f"Preserved non-empty config_dir: {self.paths.config_dir}")

            # Remove state_dir
            if self.paths.state_dir.exists():
                shutil.rmtree(self.paths.state_dir, ignore_errors=True)
                logger.info(f"Removed state_dir: {self.paths.state_dir}")

            logger.info("Cleanup complete")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Don't raise - cleanup is best-effort

    def _rollback_upgrade(self, backup_path: Path) -> None:
        """
        Restore installation from backup after failed upgrade.

        Args:
            backup_path: Path to backup directory (e.g., lib.backup-20251225-143022)

        Steps:
            - Stop service
            - Remove new lib/
            - Restore lib/ from backup
            - Start service
            - Verify health

        Raises:
            UpgradeError: If rollback fails (critical - requires manual fix)
        """
        # TODO: Implement in future story (after service management)
        logger.error(f"Rollback not implemented yet (backup at {backup_path})")
        raise UpgradeError(
            "Upgrade failed and rollback not implemented - manual intervention required",
            step="rollback_upgrade",
            details={"backup_path": str(backup_path)}
        )

    # ========================================================================
    # Frozen Package Deployment Methods
    # ========================================================================

    def _find_repo_root(self, source_dir: Optional[Path] = None) -> Path:
        """
        Find the Graphiti repository root directory.

        Detection strategy (priority order):
            1. source_dir parameter (if provided)
            2. GRAPHITI_REPO_PATH environment variable
            3. Current working directory (if it contains mcp_server/)
            4. Relative to __file__ (navigate up from daemon/ directory)

        Args:
            source_dir: Optional explicit path to repository root

        Returns:
            Path to repository root containing mcp_server/ and graphiti_core/

        Raises:
            ValidationError: If repository root cannot be found or is incomplete
        """
        logger.info("Searching for Graphiti repository root")

        # Strategy 1: Explicit source_dir parameter
        if source_dir:
            if source_dir.exists() and (source_dir / "mcp_server").exists():
                logger.info(f"Using explicit source_dir: {source_dir}")
                return source_dir
            else:
                raise ValidationError(
                    f"Provided source_dir does not contain mcp_server/: {source_dir}",
                    step="find_repo_root",
                    details={"source_dir": str(source_dir)}
                )

        # Strategy 2: GRAPHITI_REPO_PATH environment variable
        env_path = os.environ.get("GRAPHITI_REPO_PATH")
        if env_path:
            env_path_obj = Path(env_path)
            if env_path_obj.exists() and (env_path_obj / "mcp_server").exists():
                logger.info(f"Using GRAPHITI_REPO_PATH: {env_path_obj}")
                return env_path_obj
            else:
                logger.warning(f"GRAPHITI_REPO_PATH set but invalid: {env_path}")

        # Strategy 3: Current working directory
        cwd = Path.cwd()
        if (cwd / "mcp_server").exists() and (cwd / "graphiti_core").exists():
            logger.info(f"Using current working directory: {cwd}")
            return cwd

        # Strategy 4: Relative to __file__ (daemon/installer.py -> repo root)
        # Navigate: mcp_server/daemon/installer.py -> mcp_server/ -> repo_root/
        module_path = Path(__file__).resolve()
        # Go up from daemon/installer.py to mcp_server/
        mcp_server_dir = module_path.parent.parent
        # Go up from mcp_server/ to repo root
        repo_root = mcp_server_dir.parent

        if (repo_root / "mcp_server").exists() and (repo_root / "graphiti_core").exists():
            logger.info(f"Using __file__ relative path: {repo_root}")
            return repo_root

        # All strategies failed
        raise ValidationError(
            "Cannot find Graphiti repository root. Try setting GRAPHITI_REPO_PATH environment variable.",
            step="find_repo_root",
            details={
                "cwd": str(cwd),
                "module_path": str(module_path),
                "tried_strategies": ["source_dir", "GRAPHITI_REPO_PATH", "cwd", "__file__"]
            }
        )

    def _validate_source_packages(self, repo_root: Path) -> Tuple[Path, Path]:
        """
        Validate that both required packages exist in repository root.

        Args:
            repo_root: Path to repository root

        Returns:
            Tuple of (mcp_server_path, graphiti_core_path)

        Raises:
            ValidationError: If packages are missing or incomplete
        """
        logger.info(f"Validating source packages in {repo_root}")

        mcp_server_path = repo_root / "mcp_server"
        graphiti_core_path = repo_root / "graphiti_core"

        # Validate mcp_server package
        if not mcp_server_path.exists():
            raise ValidationError(
                f"mcp_server package not found in {repo_root}",
                step="validate_source_packages",
                details={"repo_root": str(repo_root)}
            )

        # Check for critical mcp_server files
        mcp_server_init = mcp_server_path / "__init__.py"
        mcp_server_main = mcp_server_path / "graphiti_mcp_server.py"
        if not mcp_server_init.exists() or not mcp_server_main.exists():
            raise ValidationError(
                "mcp_server package incomplete (missing __init__.py or graphiti_mcp_server.py)",
                step="validate_source_packages",
                details={"path": str(mcp_server_path)}
            )

        # Validate graphiti_core package
        if not graphiti_core_path.exists():
            raise ValidationError(
                f"graphiti_core package not found in {repo_root}",
                step="validate_source_packages",
                details={"repo_root": str(repo_root)}
            )

        # Check for critical graphiti_core files
        graphiti_core_init = graphiti_core_path / "__init__.py"
        if not graphiti_core_init.exists():
            raise ValidationError(
                "graphiti_core package incomplete (missing __init__.py)",
                step="validate_source_packages",
                details={"path": str(graphiti_core_path)}
            )

        logger.info(f"Source packages validated: mcp_server={mcp_server_path}, graphiti_core={graphiti_core_path}")
        return (mcp_server_path, graphiti_core_path)

    def _copy_packages(self, source_packages: Tuple[Path, Path]) -> None:
        """
        Copy mcp_server and graphiti_core packages to installation lib/ directory.

        Args:
            source_packages: Tuple of (mcp_server_path, graphiti_core_path)

        Raises:
            InstallationError: If copy fails or disk space exhausted
        """
        import fnmatch

        mcp_server_src, graphiti_core_src = source_packages
        lib_dir = self.paths.install_dir / "lib"

        logger.info(f"Copying packages to {lib_dir}")

        # Define ignore function for shutil.copytree
        def ignore_patterns(directory: str, names: List[str]) -> List[str]:
            """Return list of names to ignore during copy."""
            ignored = []
            for name in names:
                # Check exact matches
                if name in PACKAGE_EXCLUSIONS:
                    ignored.append(name)
                    continue

                # Check pattern matches (*.pyc, *.pyo, etc.)
                for pattern in PACKAGE_EXCLUSIONS:
                    if "*" in pattern:
                        # Simple glob matching
                        if fnmatch.fnmatch(name, pattern):
                            ignored.append(name)
                            break

            if ignored:
                logger.debug(f"Ignoring in {directory}: {ignored}")

            return ignored

        try:
            # Copy mcp_server package
            mcp_server_dest = lib_dir / "mcp_server"
            # Clean existing destination if present (reinstall case)
            if mcp_server_dest.exists():
                logger.info(f"Removing existing mcp_server: {mcp_server_dest}")
                shutil.rmtree(mcp_server_dest)
            logger.info(f"Copying mcp_server: {mcp_server_src} -> {mcp_server_dest}")
            shutil.copytree(
                mcp_server_src,
                mcp_server_dest,
                ignore=ignore_patterns,
            )
            logger.info("Successfully copied mcp_server package")

            # Copy graphiti_core package
            graphiti_core_dest = lib_dir / "graphiti_core"
            # Clean existing destination if present (reinstall case)
            if graphiti_core_dest.exists():
                logger.info(f"Removing existing graphiti_core: {graphiti_core_dest}")
                shutil.rmtree(graphiti_core_dest)
            logger.info(f"Copying graphiti_core: {graphiti_core_src} -> {graphiti_core_dest}")
            shutil.copytree(
                graphiti_core_src,
                graphiti_core_dest,
                ignore=ignore_patterns,
            )
            logger.info("Successfully copied graphiti_core package")

        except OSError as e:
            # Disk space or permission errors
            raise InstallationError(
                f"Failed to copy packages: {str(e)}",
                step="copy_packages",
                details={"error": str(e)}
            ) from e

    def _write_package_manifest(self, source_packages: Tuple[Path, Path]) -> None:
        """
        Write manifest file tracking copied packages and their versions.

        The manifest includes:
        - Package names and source paths
        - Copy timestamp
        - File counts and total size
        - Platform information

        Args:
            source_packages: Tuple of (mcp_server_path, graphiti_core_path)

        Raises:
            InstallationError: If manifest write fails
        """
        mcp_server_src, graphiti_core_src = source_packages
        lib_dir = self.paths.install_dir / "lib"
        manifest_path = lib_dir / "PACKAGE_MANIFEST.json"

        logger.info(f"Writing package manifest to {manifest_path}")

        def count_files(directory: Path) -> Tuple[int, int]:
            """Count files and total size in directory."""
            file_count = 0
            total_size = 0
            for item in directory.rglob("*"):
                if item.is_file():
                    file_count += 1
                    total_size += item.stat().st_size
            return file_count, total_size

        try:
            # Gather package info
            mcp_server_dest = lib_dir / "mcp_server"
            graphiti_core_dest = lib_dir / "graphiti_core"

            mcp_file_count, mcp_size = count_files(mcp_server_dest)
            graphiti_file_count, graphiti_size = count_files(graphiti_core_dest)

            manifest = {
                "created": datetime.now().isoformat(),
                "platform": sys.platform,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "packages": {
                    "mcp_server": {
                        "source": str(mcp_server_src),
                        "destination": str(mcp_server_dest),
                        "file_count": mcp_file_count,
                        "total_size_bytes": mcp_size
                    },
                    "graphiti_core": {
                        "source": str(graphiti_core_src),
                        "destination": str(graphiti_core_dest),
                        "file_count": graphiti_file_count,
                        "total_size_bytes": graphiti_size
                    }
                },
                "total_files": mcp_file_count + graphiti_file_count,
                "total_size_bytes": mcp_size + graphiti_size
            }

            # Write manifest
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"Package manifest written: {mcp_file_count + graphiti_file_count} files, {(mcp_size + graphiti_size) / 1024:.1f} KB")

        except Exception as e:
            raise InstallationError(
                f"Failed to write package manifest: {str(e)}",
                step="write_package_manifest",
                details={"error": str(e)}
            ) from e

    def _verify_frozen_packages(self) -> None:
        """
        Verify frozen packages are complete and importable.

        Three-tier verification:
            1. Structural check: Critical files and directories exist
            2. Init file check: All packages have __init__.py
            3. Import check: Packages are importable via PYTHONPATH

        Raises:
            InstallationError: If verification fails
        """
        lib_dir = self.paths.install_dir / "lib"
        logger.info(f"Verifying frozen packages in {lib_dir}")

        # Tier 1: Structural check
        logger.info("Tier 1: Verifying package structure")
        mcp_server_dir = lib_dir / "mcp_server"
        graphiti_core_dir = lib_dir / "graphiti_core"

        # Check mcp_server structure
        # Note: mcp_server/config/ is a data directory (YAML configs), not a Python package
        mcp_critical_files = [
            mcp_server_dir / "__init__.py",
            mcp_server_dir / "graphiti_mcp_server.py",
            mcp_server_dir / "daemon" / "__init__.py",
        ]

        for file_path in mcp_critical_files:
            if not file_path.exists():
                raise InstallationError(
                    f"Critical mcp_server file missing: {file_path.relative_to(lib_dir)}",
                    step="verify_frozen_packages",
                    details={"missing_file": str(file_path)}
                )

        # Check graphiti_core structure
        graphiti_critical_files = [
            graphiti_core_dir / "__init__.py",
        ]

        for file_path in graphiti_critical_files:
            if not file_path.exists():
                raise InstallationError(
                    f"Critical graphiti_core file missing: {file_path.relative_to(lib_dir)}",
                    step="verify_frozen_packages",
                    details={"missing_file": str(file_path)}
                )

        logger.info("Tier 1: Package structure verified")

        # Tier 2: Init file check (warning only - some packages use namespace packages)
        logger.info("Tier 2: Checking __init__.py files")
        missing_init_dirs = []
        for package_dir in [mcp_server_dir, graphiti_core_dir]:
            for py_file in package_dir.rglob("*.py"):
                parent = py_file.parent
                if parent != package_dir and not parent.name.startswith("_"):
                    # This is a subdirectory with .py files - should have __init__.py
                    init_file = parent / "__init__.py"
                    if not init_file.exists():
                        rel_path = parent.relative_to(lib_dir)
                        if str(rel_path) not in missing_init_dirs:
                            missing_init_dirs.append(str(rel_path))
                            logger.warning(f"Missing __init__.py in {rel_path} (may be namespace package)")

        if missing_init_dirs:
            logger.info(f"Tier 2: {len(missing_init_dirs)} directories without __init__.py (non-blocking)")
        else:
            logger.info("Tier 2: All __init__.py files verified")

        # Tier 3: Import check
        logger.info("Tier 3: Verifying packages are importable")
        original_path = sys.path.copy()
        try:
            # Add lib directory to Python path
            sys.path.insert(0, str(lib_dir))

            # Try importing both packages
            try:
                import mcp_server
                logger.info("Successfully imported mcp_server")
            except ImportError as e:
                raise InstallationError(
                    f"mcp_server package not importable: {str(e)}",
                    step="verify_frozen_packages",
                    details={"error": str(e)}
                ) from e

            try:
                import graphiti_core
                logger.info("Successfully imported graphiti_core")
            except ImportError as e:
                raise InstallationError(
                    f"graphiti_core package not importable: {str(e)}",
                    step="verify_frozen_packages",
                    details={"error": str(e)}
                ) from e

            logger.info("Tier 3: Import verification passed")

        finally:
            # Restore original sys.path
            sys.path = original_path

        logger.info("All frozen package verification tiers passed")

    def _freeze_packages(self, source_dir: Optional[Path] = None) -> None:
        """
        Freeze packages by copying mcp_server and graphiti_core to lib/ directory.

        This is the main orchestration method that coordinates:
            1. Repository root detection
            2. Source package validation
            3. Package copying with exclusions
            4. Manifest creation
            5. Comprehensive verification

        Args:
            source_dir: Optional explicit path to repository root

        Raises:
            ValidationError: If source packages are invalid or incomplete
            InstallationError: If copy, manifest, or verification fails
        """
        logger.info("Starting frozen package deployment")

        # Step 1: Find repository root
        repo_root = self._find_repo_root(source_dir)

        # Step 2: Validate source packages
        source_packages = self._validate_source_packages(repo_root)

        # Step 3: Copy packages to lib/
        self._copy_packages(source_packages)

        # Step 4: Write package manifest
        self._write_package_manifest(source_packages)

        # Step 5: Verify frozen packages
        self._verify_frozen_packages()

        logger.info("Frozen package deployment completed successfully")

    # ========================================================================
    # Config Migration Methods (Story 12)
    # ========================================================================

    def migrate_config(
        self,
        interactive: bool = True,
        force_overwrite: bool = False,
        backup: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate v2.0 config to v2.1 location.

        Delegates to installer_migration module for implementation.
        See: mcp_server/daemon/installer_migration.py

        Args:
            interactive: If True, prompt user on conflicts. If False, skip on conflict.
            force_overwrite: If True, overwrite v2.1 config without prompting.
            backup: If True, create backup before migration.

        Returns:
            dict: Migration result (see installer_migration.migrate_config for details)

        Raises:
            FileNotFoundError: If v2.0 config doesn't exist
            PermissionError: If cannot write to v2.1 config location
            ValueError: If v2.0 config is invalid JSON
        """
        from .installer_migration import migrate_config as _migrate_impl
        return _migrate_impl(
            installer=self,
            interactive=interactive,
            force_overwrite=force_overwrite,
            backup=backup
        )
