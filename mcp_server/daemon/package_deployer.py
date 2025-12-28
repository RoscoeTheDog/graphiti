"""
Graphiti Package Deployer

Deploys the mcp_server package to the platform-specific install directory during
daemon installation.

v2.1 Architecture Paths:
- Windows: %LOCALAPPDATA%\\Programs\\Graphiti\\lib\\
- macOS: ~/Library/Application Support/Graphiti/lib/
- Linux: ~/.local/share/graphiti/lib/

This module provides:
- Package deployment to standalone location
- Version tracking via .version file
- Idempotent operations (safe to run multiple times)
- Backup of existing deployments
- Platform-agnostic path handling

Design Principle: Deploy a standalone copy of mcp_server/ to the platform-specific
install directory so the bootstrap service can run independent of the repository location.

See: .claude/sprint/plans/2-plan.yaml
"""

import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .paths import get_install_dir

logger = logging.getLogger(__name__)


class PackageDeploymentError(Exception):
    """Raised when package deployment fails."""
    pass


class PackageDeployer:
    """Manager for deploying mcp_server package to standalone location."""

    # Exclusion patterns for deployment (don't copy these)
    EXCLUSIONS = {
        ".venv",
        "__pycache__",
        "*.pyc",
        "tests",
        ".pytest_cache",
        "*.egg-info",
        ".git",
        ".gitignore",
        "*.dist-info",
    }

    def __init__(self, deploy_path: Optional[Path] = None):
        """
        Initialize PackageDeployer.

        Args:
            deploy_path: Path to deployment directory. Defaults to install_dir/lib/
        """
        if deploy_path is None:
            # v2.1 architecture: deploy to lib/ under install_dir
            deploy_path = get_install_dir() / "lib"
        self.deploy_path = deploy_path
        self.version_file = self.deploy_path / ".version"

    def _get_repo_root(self) -> Path:
        """
        Detect the repository root containing mcp_server/ and graphiti_core/.

        Detection order:
        1. GRAPHITI_REPO_PATH environment variable
        2. Current working directory
        3. Relative to this file (__file__)

        Returns:
            Path to repository root

        Raises:
            PackageDeploymentError: If repository root cannot be found
        """
        import os

        def _check_path(path: Path, source: str) -> Optional[Path]:
            """Check if path contains mcp_server/ and graphiti_core/."""
            try:
                resolved = path.resolve()
                mcp_server_dir = resolved / "mcp_server"
                graphiti_core_dir = resolved / "graphiti_core"
                mcp_pyproject = mcp_server_dir / "pyproject.toml"
                graphiti_init = graphiti_core_dir / "__init__.py"
                if mcp_pyproject.exists() and graphiti_init.exists():
                    logger.debug(f"Repository root found at: {resolved} (via {source})")
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

        # 2. Check current working directory
        result = _check_path(Path.cwd(), "current directory")
        if result:
            return result

        # 3. Check relative to this file
        try:
            # Go up from package_deployer.py: daemon/ -> mcp_server/ -> repo_root
            file_path = Path(__file__).resolve()
            repo_root = file_path.parent.parent.parent
            if _check_path(repo_root, "__file__ location"):
                return repo_root
        except Exception:
            pass

        raise PackageDeploymentError(
            "Cannot find Graphiti repository root. "
            "Expected to find mcp_server/pyproject.toml and graphiti_core/__init__.py."
        )

    def _get_source_path(self) -> Path:
        """
        Get the mcp_server source directory.

        Returns:
            Path to mcp_server source directory
        """
        return self._get_repo_root() / "mcp_server"

    def _get_graphiti_core_path(self) -> Path:
        """
        Get the graphiti_core source directory.

        Returns:
            Path to graphiti_core source directory
        """
        return self._get_repo_root() / "graphiti_core"

    def _get_version_from_pyproject(self, source_path: Path) -> str:
        """
        Extract version from pyproject.toml.

        Args:
            source_path: Path to mcp_server source directory

        Returns:
            Version string (e.g., "1.0.1")

        Raises:
            PackageDeploymentError: If version cannot be extracted
        """
        pyproject_path = source_path / "pyproject.toml"
        if not pyproject_path.exists():
            raise PackageDeploymentError(f"pyproject.toml not found at {pyproject_path}")

        try:
            # Parse pyproject.toml (simple text parsing, no TOML library needed)
            content = pyproject_path.read_text()
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("version") and "=" in line:
                    # Extract version: version = "1.0.1"
                    version = line.split("=", 1)[1].strip().strip('"').strip("'")
                    logger.debug(f"Extracted version: {version}")
                    return version

            raise PackageDeploymentError("Version field not found in pyproject.toml")

        except Exception as e:
            raise PackageDeploymentError(f"Error reading pyproject.toml: {e}")

    def _should_ignore(self, path: Path, root: Path) -> bool:
        """
        Check if a path should be ignored during deployment.

        Args:
            path: Path to check
            root: Root source directory

        Returns:
            True if path should be ignored
        """
        # Get relative path for pattern matching
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            # Path not relative to root, ignore it
            return True

        # Check each part of the path against exclusion patterns
        for part in rel_path.parts:
            for pattern in self.EXCLUSIONS:
                if pattern.startswith("*"):
                    # Wildcard pattern (e.g., *.pyc)
                    if part.endswith(pattern[1:]):
                        return True
                else:
                    # Exact match (e.g., __pycache__)
                    if part == pattern:
                        return True

        return False

    def backup_existing(self) -> Optional[Path]:
        """
        Backup existing deployment before replacement.

        Creates a timestamped backup: {install_dir}/lib.backup.YYYYMMDD-HHMMSS/

        Returns:
            Path to backup directory if created, None if no existing deployment

        Raises:
            PackageDeploymentError: If backup fails
        """
        if not self.deploy_path.exists():
            logger.debug("No existing deployment to backup")
            return None

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = self.deploy_path.parent / f"mcp_server.backup.{timestamp}"

        logger.info(f"Backing up existing deployment to: {backup_path}")
        try:
            shutil.copytree(self.deploy_path, backup_path)
            logger.info(f"Backup created successfully: {backup_path}")
            return backup_path
        except Exception as e:
            raise PackageDeploymentError(f"Failed to create backup: {e}")

    def verify_deployment(self) -> bool:
        """
        Verify that deployment is valid.

        Checks:
        - Deployment directory exists
        - Version file exists and is readable
        - Key packages present (mcp_server/, graphiti_core/)
        - Key files are present within packages

        Returns:
            True if deployment is valid
        """
        if not self.deploy_path.exists():
            logger.debug(f"Deployment path does not exist: {self.deploy_path}")
            return False

        # Check version file
        if not self.version_file.exists():
            logger.debug(f"Version file missing: {self.version_file}")
            return False

        # Check key directories and files
        key_files = [
            # mcp_server package
            self.deploy_path / "mcp_server",
            self.deploy_path / "mcp_server" / "graphiti_mcp_server.py",
            self.deploy_path / "mcp_server" / "daemon",
            self.deploy_path / "mcp_server" / "config",
            # graphiti_core package
            self.deploy_path / "graphiti_core",
            self.deploy_path / "graphiti_core" / "__init__.py",
        ]

        for key_file in key_files:
            if not key_file.exists():
                logger.debug(f"Key file missing: {key_file}")
                return False

        logger.debug(f"Deployment verified: {self.deploy_path}")
        return True

    def _deploy_single_package(
        self, source_path: Path, dest_path: Path, package_name: str
    ) -> None:
        """
        Deploy a single package to destination.

        Args:
            source_path: Source package directory
            dest_path: Destination directory
            package_name: Name for logging
        """
        def ignore_patterns(dir_path, names):
            """Custom ignore function for shutil.copytree."""
            ignored = []
            dir_path_obj = Path(dir_path)
            for name in names:
                full_path = dir_path_obj / name
                if self._should_ignore(full_path, source_path):
                    ignored.append(name)
                    logger.debug(f"Excluding from {package_name}: {name}")
            return ignored

        logger.info(f"Deploying {package_name} from {source_path} to {dest_path}")
        shutil.copytree(
            source_path,
            dest_path,
            ignore=ignore_patterns,
            dirs_exist_ok=False,
        )

    def deploy_package(self, force: bool = False) -> Tuple[bool, str]:
        """
        Deploy mcp_server and graphiti_core packages to standalone location.

        Idempotent: skips deployment if already deployed and version matches,
        unless force=True.

        Args:
            force: If True, always redeploy even if deployment exists

        Returns:
            Tuple of (success: bool, message: str)

        Raises:
            PackageDeploymentError: If deployment fails
        """
        # Get source package locations
        try:
            mcp_server_path = self._get_source_path()
            graphiti_core_path = self._get_graphiti_core_path()
        except PackageDeploymentError as e:
            logger.error(f"Cannot find source packages: {e}")
            raise

        # Get version from pyproject.toml
        version = self._get_version_from_pyproject(mcp_server_path)

        # Check if deployment already exists and is current
        if not force and self.verify_deployment():
            try:
                existing_version = self.version_file.read_text().strip()
                if existing_version == version:
                    msg = f"Deployment already exists at {self.deploy_path} (version {version}), skipping"
                    logger.info(msg)
                    return True, msg
                else:
                    logger.info(
                        f"Existing deployment version {existing_version} != current {version}, "
                        "will update"
                    )
            except Exception as e:
                logger.warning(f"Error reading version file: {e}, will redeploy")

        # Backup existing deployment if present
        if self.deploy_path.exists():
            try:
                backup_path = self.backup_existing()
                if backup_path:
                    logger.info(f"Backup created at: {backup_path}")
            except PackageDeploymentError as e:
                logger.error(f"Backup failed: {e}")
                raise

        # Ensure parent directory exists
        self.deploy_path.parent.mkdir(parents=True, exist_ok=True)

        # Deploy packages
        try:
            # Remove existing deployment if present (after backup)
            if self.deploy_path.exists():
                logger.debug(f"Removing existing deployment: {self.deploy_path}")
                shutil.rmtree(self.deploy_path)

            # Create deployment directory
            self.deploy_path.mkdir(parents=True, exist_ok=True)

            # Deploy mcp_server to lib/mcp_server/
            mcp_dest = self.deploy_path / "mcp_server"
            self._deploy_single_package(mcp_server_path, mcp_dest, "mcp_server")

            # Deploy graphiti_core to lib/graphiti_core/
            graphiti_dest = self.deploy_path / "graphiti_core"
            self._deploy_single_package(graphiti_core_path, graphiti_dest, "graphiti_core")

            # Create version file
            self.version_file.write_text(version)
            logger.info(f"Version file created: {self.version_file} ({version})")

            # Verify deployment succeeded
            if not self.verify_deployment():
                raise PackageDeploymentError(
                    "Deployment verification failed. Package may be incomplete."
                )

            msg = f"Successfully deployed package to {self.deploy_path} (version {version})"
            logger.info(msg)
            return True, msg

        except Exception as e:
            raise PackageDeploymentError(f"Deployment failed: {e}")

    def get_deployed_version(self) -> Optional[str]:
        """
        Get version of deployed package.

        Returns:
            Version string if deployed, None if not deployed
        """
        if not self.version_file.exists():
            return None

        try:
            return self.version_file.read_text().strip()
        except Exception as e:
            logger.warning(f"Error reading version file: {e}")
            return None
