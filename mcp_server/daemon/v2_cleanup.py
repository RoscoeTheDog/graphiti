#!/usr/bin/env python3
"""
V2.0 Installation Cleanup

Safely removes v2.0 installation artifacts after successful migration to v2.1.
Includes service cleanup, directory cleanup, backup creation, and rollback capabilities.

Story: 13 - Implement Old Installation Cleanup
"""

import json
import logging
import platform
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CleanupError(Exception):
    """Raised when cleanup fails critically."""
    pass


class V21NotInstalledError(Exception):
    """Raised when v2.1 installation is not detected or not working."""
    pass


class V2Cleanup:
    """Handles cleanup of v2.0 installation artifacts."""

    def __init__(self):
        """Initialize cleanup manager."""
        self.platform = platform.system()
        self.home_dir = Path.home() / ".graphiti"
        self.backup_dir: Optional[Path] = None
        self.rollback_data: Dict = {}

    def cleanup_v2_0_installation(
        self,
        interactive: bool = True,
        force_delete: bool = False,
        keep_logs: bool = False
    ) -> Dict:
        """
        Clean up v2.0 installation after successful migration to v2.1.

        Args:
            interactive: If True, prompt user for cleanup decisions.
                        If False, use safe defaults (skip directory deletion).
            force_delete: If True (non-interactive only), actually delete directories.
                         Requires explicit opt-in to prevent accidents.
            keep_logs: If True, preserve ~/.graphiti/logs/ during deletion.

        Returns:
            dict: Cleanup result
                {
                    "success": bool,
                    "actions_taken": list[str],
                    "backup_location": Path or None,
                    "rollback_performed": bool,
                    "errors": list[str]
                }

        Raises:
            V21NotInstalledError: If v2.1 installation not detected
            CleanupError: If critical cleanup step fails and rollback fails
        """
        result = {
            "success": False,
            "actions_taken": [],
            "backup_location": None,
            "rollback_performed": False,
            "errors": []
        }

        try:
            # Stage 1: Pre-cleanup validation
            self._validate_v2_1_installation()
            result["actions_taken"].append("Validated v2.1 installation")

            # Check if v2.0 exists
            if not self.home_dir.exists():
                result["success"] = True
                result["actions_taken"].append("No v2.0 installation found - nothing to clean")
                return result

            # Create backup directory
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.backup_dir = Path.home() / f".graphiti.cleanup-backup-{timestamp}"
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            result["backup_location"] = self.backup_dir
            result["actions_taken"].append(f"Created backup directory: {self.backup_dir}")

            # Stage 2: Service cleanup
            try:
                service_removed = self._cleanup_service()
                if service_removed:
                    result["actions_taken"].append("Removed v2.0 service/task")
            except Exception as e:
                logger.warning(f"Service cleanup failed (non-critical): {e}")
                result["actions_taken"].append(f"Service cleanup skipped: {e}")

            # Stage 3: Directory cleanup
            if interactive:
                delete_choice = self._prompt_directory_cleanup()
                if delete_choice == "delete_all":
                    self._cleanup_directory(keep_logs=False)
                    result["actions_taken"].append("Removed ~/.graphiti/ (full deletion)")
                elif delete_choice == "delete_except_logs":
                    self._cleanup_directory(keep_logs=True)
                    result["actions_taken"].append("Removed ~/.graphiti/ (kept logs)")
                else:
                    result["actions_taken"].append("Skipped directory cleanup (user choice)")
            else:
                # Non-interactive mode
                if force_delete:
                    self._cleanup_directory(keep_logs=keep_logs)
                    if keep_logs:
                        result["actions_taken"].append("Removed ~/.graphiti/ (kept logs, non-interactive)")
                    else:
                        result["actions_taken"].append("Removed ~/.graphiti/ (full deletion, non-interactive)")
                else:
                    result["actions_taken"].append("Skipped directory cleanup (non-interactive, no --force)")

            # Stage 4: Verification
            self._verify_cleanup()
            result["actions_taken"].append("Verified cleanup completed successfully")

            result["success"] = True
            return result

        except V21NotInstalledError as e:
            result["errors"].append(f"V2.1 not installed: {e}")
            return result

        except KeyboardInterrupt:
            # User cancelled - attempt rollback
            logger.info("Cleanup cancelled by user - attempting rollback")
            result["actions_taken"].append("Cleanup cancelled by user")
            try:
                self._rollback()
                result["rollback_performed"] = True
                result["actions_taken"].append("Rollback completed successfully")
            except Exception as rollback_error:
                result["errors"].append(f"Rollback failed: {rollback_error}")
                raise CleanupError(f"Cleanup cancelled and rollback failed: {rollback_error}")
            return result

        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)
            result["errors"].append(str(e))

            # Attempt rollback
            try:
                self._rollback()
                result["rollback_performed"] = True
                result["actions_taken"].append("Rollback completed after error")
            except Exception as rollback_error:
                result["errors"].append(f"Rollback failed: {rollback_error}")
                raise CleanupError(f"Cleanup failed and rollback failed: {rollback_error}")

            return result

    def _validate_v2_1_installation(self) -> None:
        """
        Verify v2.1 installation is working before cleanup.

        Raises:
            V21NotInstalledError: If v2.1 not detected or not working
        """
        # Import here to avoid circular dependency
        from .paths import get_install_dir, get_config_file
        from .v2_detection import detect_v2_1_installation

        v21_result = detect_v2_1_installation()

        if not v21_result["detected"]:
            raise V21NotInstalledError(
                "V2.1 installation not detected. Cannot safely remove v2.0 without working v2.1."
            )

        # Verify config exists
        config_file = get_config_file()
        if not config_file.exists():
            raise V21NotInstalledError(
                f"V2.1 config not found at {config_file}. Installation may be incomplete."
            )

        logger.info("V2.1 installation validated successfully")

    def _cleanup_service(self) -> bool:
        """
        Remove v2.0 service/task based on platform.

        Returns:
            bool: True if service was removed, False if no service found

        Raises:
            CleanupError: If service cleanup fails critically
        """
        if self.platform == "Windows":
            return self._cleanup_windows_task()
        elif self.platform == "Darwin":
            return self._cleanup_macos_launchagent()
        elif self.platform == "Linux":
            return self._cleanup_linux_systemd()
        else:
            logger.warning(f"Unknown platform: {self.platform} - skipping service cleanup")
            return False

    def _cleanup_windows_task(self) -> bool:
        """
        Remove Windows Task Scheduler task (GraphitiBootstrap_*).

        Returns:
            bool: True if task was removed, False if no task found
        """
        logger.info("Checking for Windows Task Scheduler task...")

        try:
            # Find GraphitiBootstrap_* tasks
            result = subprocess.run(
                ["powershell", "-Command", "Get-ScheduledTask -TaskName 'GraphitiBootstrap*' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty TaskName"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0 or not result.stdout.strip():
                logger.info("No GraphitiBootstrap task found - nothing to remove")
                return False

            task_names = result.stdout.strip().split('\n')

            # Backup task XML before deletion
            for task_name in task_names:
                task_name = task_name.strip()
                if not task_name:
                    continue

                logger.info(f"Found task: {task_name}")

                # Export task XML to backup
                export_path = self.backup_dir / f"{task_name}.xml"
                try:
                    subprocess.run(
                        ["schtasks", "/Query", "/TN", task_name, "/XML"],
                        capture_output=True,
                        check=False,
                        timeout=10
                    )
                    logger.info(f"Task definition backed up (attempted)")
                except Exception as e:
                    logger.warning(f"Could not export task XML: {e}")

                # Stop task if running
                try:
                    subprocess.run(
                        ["schtasks", "/End", "/TN", task_name],
                        capture_output=True,
                        check=False,
                        timeout=10
                    )
                    logger.info(f"Stopped task: {task_name}")
                    time.sleep(1)  # Give it time to stop
                except Exception as e:
                    logger.warning(f"Could not stop task (may not be running): {e}")

                # Delete task
                delete_result = subprocess.run(
                    ["schtasks", "/Delete", "/TN", task_name, "/F"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if delete_result.returncode == 0:
                    logger.info(f"Deleted task: {task_name}")
                    self.rollback_data["windows_task"] = task_name
                else:
                    logger.error(f"Failed to delete task {task_name}: {delete_result.stderr}")
                    raise CleanupError(f"Failed to delete Windows task: {delete_result.stderr}")

            return True

        except subprocess.TimeoutExpired:
            raise CleanupError("Windows task cleanup timed out")
        except Exception as e:
            raise CleanupError(f"Windows task cleanup failed: {e}")

    def _cleanup_macos_launchagent(self) -> bool:
        """
        Remove macOS LaunchAgent (com.graphiti.bootstrap.plist).

        Returns:
            bool: True if LaunchAgent was removed, False if not found
        """
        logger.info("Checking for macOS LaunchAgent...")

        plist_path = Path.home() / "Library" / "LaunchAgents" / "com.graphiti.bootstrap.plist"

        if not plist_path.exists():
            logger.info("No LaunchAgent plist found - nothing to remove")
            return False

        try:
            # Backup plist
            backup_plist = self.backup_dir / "com.graphiti.bootstrap.plist"
            shutil.copy2(plist_path, backup_plist)
            logger.info(f"Backed up plist to {backup_plist}")

            # Unload LaunchAgent
            try:
                subprocess.run(
                    ["launchctl", "unload", str(plist_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False
                )
                logger.info("Unloaded LaunchAgent")
                time.sleep(2)  # Give it time to unload
            except Exception as e:
                logger.warning(f"Could not unload LaunchAgent (may not be loaded): {e}")

            # Remove plist file
            plist_path.unlink()
            logger.info(f"Removed plist: {plist_path}")
            self.rollback_data["macos_plist"] = backup_plist

            return True

        except Exception as e:
            raise CleanupError(f"macOS LaunchAgent cleanup failed: {e}")

    def _cleanup_linux_systemd(self) -> bool:
        """
        Remove Linux systemd user service (graphiti-bootstrap.service).

        Returns:
            bool: True if service was removed, False if not found
        """
        logger.info("Checking for Linux systemd service...")

        service_file = Path.home() / ".config" / "systemd" / "user" / "graphiti-bootstrap.service"

        if not service_file.exists():
            logger.info("No systemd service file found - nothing to remove")
            return False

        try:
            # Backup service file
            backup_service = self.backup_dir / "graphiti-bootstrap.service"
            shutil.copy2(service_file, backup_service)
            logger.info(f"Backed up service file to {backup_service}")

            # Stop service
            try:
                subprocess.run(
                    ["systemctl", "--user", "stop", "graphiti-bootstrap"],
                    capture_output=True,
                    timeout=30,
                    check=False
                )
                logger.info("Stopped systemd service")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Could not stop service (may not be running): {e}")

            # Disable service
            try:
                subprocess.run(
                    ["systemctl", "--user", "disable", "graphiti-bootstrap"],
                    capture_output=True,
                    timeout=30,
                    check=False
                )
                logger.info("Disabled systemd service")
            except Exception as e:
                logger.warning(f"Could not disable service: {e}")

            # Remove service file
            service_file.unlink()
            logger.info(f"Removed service file: {service_file}")

            # Reload daemon
            try:
                subprocess.run(
                    ["systemctl", "--user", "daemon-reload"],
                    capture_output=True,
                    timeout=30,
                    check=False
                )
                logger.info("Reloaded systemd daemon")
            except Exception as e:
                logger.warning(f"Could not reload daemon: {e}")

            self.rollback_data["linux_service"] = backup_service

            return True

        except Exception as e:
            raise CleanupError(f"Linux systemd service cleanup failed: {e}")

    def _prompt_directory_cleanup(self) -> str:
        """
        Prompt user for directory cleanup decision.

        Returns:
            str: One of 'delete_all', 'delete_except_logs', 'skip_cleanup'
        """
        print()
        print("=" * 70)
        print("V2.0 Directory Cleanup")
        print("=" * 70)
        print()
        print(f"The v2.0 installation directory exists: {self.home_dir}")
        print()
        print("Options:")
        print("  1. Remove everything (~/.graphiti/)")
        print("  2. Keep logs only (remove ~/.graphiti/ but preserve logs/)")
        print("  3. Skip cleanup (keep ~/.graphiti/ - you can remove it manually later)")
        print()

        while True:
            choice = input("Enter choice (1/2/3) [3]: ").strip()

            if not choice:
                choice = "3"

            if choice == "1":
                print()
                confirm = input("[WARN]  This will DELETE all v2.0 data. Continue? (yes/no) [no]: ").strip().lower()
                if confirm == "yes":
                    return "delete_all"
                else:
                    print("Cancelled - please choose again")
                    continue
            elif choice == "2":
                return "delete_except_logs"
            elif choice == "3":
                return "skip_cleanup"
            else:
                print(f"Invalid choice: {choice}. Please enter 1, 2, or 3.")

    def _cleanup_directory(self, keep_logs: bool = False) -> None:
        """
        Remove ~/.graphiti/ directory with optional log preservation.

        Args:
            keep_logs: If True, preserve ~/.graphiti/logs/

        Raises:
            CleanupError: If directory cleanup fails
        """
        if not self.home_dir.exists():
            logger.info("~/.graphiti/ does not exist - nothing to clean")
            return

        logger.info(f"Cleaning up directory: {self.home_dir} (keep_logs={keep_logs})")

        try:
            # Full backup before deletion
            backup_home = self.backup_dir / "graphiti"
            shutil.copytree(self.home_dir, backup_home, symlinks=True)
            logger.info(f"Backed up ~/.graphiti/ to {backup_home}")
            self.rollback_data["home_dir_backup"] = backup_home

            if keep_logs:
                # Delete everything except logs
                logs_dir = self.home_dir / "logs"
                temp_logs = None

                if logs_dir.exists():
                    # Move logs to temp location
                    temp_logs = self.backup_dir / "logs_temp"
                    shutil.move(str(logs_dir), str(temp_logs))
                    logger.info("Temporarily moved logs")

                # Delete entire directory
                shutil.rmtree(self.home_dir)
                logger.info(f"Removed {self.home_dir}")

                # Restore logs
                if temp_logs:
                    self.home_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(temp_logs), str(logs_dir))
                    logger.info(f"Restored logs to {logs_dir}")
            else:
                # Delete everything
                shutil.rmtree(self.home_dir)
                logger.info(f"Removed {self.home_dir} (full deletion)")

        except Exception as e:
            raise CleanupError(f"Directory cleanup failed: {e}")

    def _verify_cleanup(self) -> None:
        """
        Verify cleanup completed as expected.

        Raises:
            CleanupError: If verification fails
        """
        logger.info("Verifying cleanup...")

        # Verify v2.1 still working
        try:
            self._validate_v2_1_installation()
        except V21NotInstalledError as e:
            raise CleanupError(f"V2.1 installation broken after cleanup: {e}")

        logger.info("Cleanup verification passed")

    def _rollback(self) -> None:
        """
        Rollback cleanup changes using backup.

        Raises:
            CleanupError: If rollback fails
        """
        logger.info("Rolling back cleanup changes...")

        if not self.backup_dir or not self.backup_dir.exists():
            raise CleanupError("Cannot rollback: backup directory not found")

        errors = []

        try:
            # Restore home directory if backed up
            if "home_dir_backup" in self.rollback_data:
                backup_home = self.rollback_data["home_dir_backup"]
                if backup_home.exists():
                    if self.home_dir.exists():
                        shutil.rmtree(self.home_dir)
                    shutil.copytree(backup_home, self.home_dir, symlinks=True)
                    logger.info(f"Restored ~/.graphiti/ from {backup_home}")

            # Restore Windows task
            if "windows_task" in self.rollback_data and self.platform == "Windows":
                # Note: Cannot easily restore Windows tasks from XML via CLI
                # Manual intervention required
                logger.warning("Windows task removed - manual restoration required")
                errors.append("Windows task requires manual restoration")

            # Restore macOS plist
            if "macos_plist" in self.rollback_data and self.platform == "Darwin":
                backup_plist = self.rollback_data["macos_plist"]
                target_plist = Path.home() / "Library" / "LaunchAgents" / "com.graphiti.bootstrap.plist"
                if backup_plist.exists():
                    shutil.copy2(backup_plist, target_plist)
                    subprocess.run(
                        ["launchctl", "load", str(target_plist)],
                        capture_output=True,
                        check=False
                    )
                    logger.info("Restored macOS LaunchAgent")

            # Restore Linux service
            if "linux_service" in self.rollback_data and self.platform == "Linux":
                backup_service = self.rollback_data["linux_service"]
                target_service = Path.home() / ".config" / "systemd" / "user" / "graphiti-bootstrap.service"
                if backup_service.exists():
                    target_service.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_service, target_service)
                    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, check=False)
                    subprocess.run(["systemctl", "--user", "enable", "graphiti-bootstrap"], capture_output=True, check=False)
                    subprocess.run(["systemctl", "--user", "start", "graphiti-bootstrap"], capture_output=True, check=False)
                    logger.info("Restored Linux systemd service")

            if errors:
                raise CleanupError(f"Partial rollback completed with errors: {'; '.join(errors)}")

            logger.info("Rollback completed successfully")

        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            raise CleanupError(f"Rollback failed: {e}")


def cleanup_v2_0_installation(
    interactive: bool = True,
    force_delete: bool = False,
    keep_logs: bool = False
) -> Dict:
    """
    Clean up v2.0 installation after successful migration to v2.1.

    This is a convenience function that wraps V2Cleanup.cleanup_v2_0_installation().

    Args:
        interactive: If True, prompt user for cleanup decisions.
        force_delete: If True (non-interactive only), actually delete directories.
        keep_logs: If True, preserve ~/.graphiti/logs/ during deletion.

    Returns:
        dict: Cleanup result with success status, actions taken, and errors

    Example:
        >>> result = cleanup_v2_0_installation()
        >>> if result["success"]:
        ...     print(f"Cleanup complete. Backup: {result['backup_location']}")
    """
    cleanup_manager = V2Cleanup()
    return cleanup_manager.cleanup_v2_0_installation(
        interactive=interactive,
        force_delete=force_delete,
        keep_logs=keep_logs
    )
