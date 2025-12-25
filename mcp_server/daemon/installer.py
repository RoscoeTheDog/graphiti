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

import logging
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .paths import GraphitiPaths, get_paths

# Type alias for progress callback
ProgressCallback = Callable[[str, int, int, str], None]

# Configure logging
logger = logging.getLogger(__name__)


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
            return f"✓ Installation successful (version {self.version})"
        else:
            return f"✗ Installation failed: {self.error}"


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
        self._report(f"✓ {message}")

    def error(self, message: str) -> None:
        """Report error."""
        self._report(f"✗ {message}")

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
            3. _create_venv() - Create virtual environment in install_dir/bin
            4. _install_dependencies() - Install pip packages from requirements.txt
            5. _freeze_packages() - Copy mcp_server and graphiti_core to lib/
            6. _create_wrappers() - Generate platform executables (graphiti-mcp.exe, etc.)
            7. _write_version_info() - Write VERSION and INSTALL_INFO files
            8. _create_default_config() - Generate graphiti.config.json in config_dir
            9. _register_service() - Register with Task Scheduler/launchd/systemd
            10. _start_service() - Start bootstrap service
            11. _verify_installation() - Health check via MCP connection

        Rollback:
            On failure at any step, calls _cleanup_on_failure() to remove partial install
        """
        try:
            self.progress.start("Installing Graphiti MCP Server", total_steps=11)

            self.progress.step(1, "Validating environment")
            self._validate_environment()

            self.progress.step(2, "Creating directories")
            self._create_directories()

            # TODO: Implement remaining steps in Story 5 (Frozen Package Deployment)
            # self.progress.step(3, "Creating virtual environment")
            # self._create_venv()
            #
            # self.progress.step(4, "Installing dependencies")
            # self._install_dependencies(source_dir)
            #
            # self.progress.step(5, "Freezing packages")
            # self._freeze_packages(source_dir)
            #
            # self.progress.step(6, "Creating wrapper executables")
            # self._create_wrappers()
            #
            # self.progress.step(7, "Writing version information")
            # version = self._write_version_info()
            #
            # self.progress.step(8, "Creating default configuration")
            # self._create_default_config()
            #
            # self.progress.step(9, "Registering service")
            # self._register_service()
            #
            # self.progress.step(10, "Starting service")
            # self._start_service()
            #
            # self.progress.step(11, "Verifying installation")
            # self._verify_installation()

            # For now, return skeleton result
            self.progress.complete("Installation skeleton created (pending Stories 5-10)")
            return InstallationResult(
                success=True,
                version="2.1.0-skeleton",
                paths=self.paths,
                details={"status": "skeleton", "pending": "Stories 5-10"}
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
