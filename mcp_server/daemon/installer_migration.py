"""
Config Migration Extension for GraphitiInstaller (Story 12).

This module extends GraphitiInstaller with config migration functionality,
providing methods to migrate v2.0 config to v2.1 location.

Integration: Import and use as mixin or standalone functions.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def migrate_config(
    installer,
    interactive: bool = True,
    force_overwrite: bool = False,
    backup: bool = True
) -> Dict[str, Any]:
    """
    Migrate v2.0 config to v2.1 location.

    Strategy: COPY with optional merge (preserves v2.0 config completely)

    Args:
        installer: GraphitiInstaller instance (provides self.paths)
        interactive: If True, prompt user on conflicts. If False, skip on conflict.
        force_overwrite: If True, overwrite v2.1 config without prompting.
        backup: If True, create backup before migration.

    Returns:
        dict: Migration result
            {
                "migrated": bool,
                "source": Path or None,
                "destination": Path or None,
                "backup_path": Path or None,
                "action": "copied" | "merged" | "skipped" | "overwritten",
                "errors": list[str]
            }

    Raises:
        FileNotFoundError: If v2.0 config doesn't exist
        PermissionError: If cannot write to v2.1 config location
        ValueError: If v2.0 config is invalid JSON

    Example usage:
        >>> installer = GraphitiInstaller()
        >>> result = migrate_config(installer)
        >>> if result["migrated"]:
        ...     print(f"Config migrated: {result['action']}")
    """
    from mcp_server.daemon.v2_detection import detect_v2_0_installation
    from mcp_server.daemon.installer import InstallationError, PermissionError as InstPermError

    logger.info("Starting config migration (v2.0 -> v2.1)")

    # Detect v2.0 installation
    v2_0_install = detect_v2_0_installation()

    if not v2_0_install["detected"] or not v2_0_install["config_file"]:
        logger.info("No v2.0 config found - skipping migration")
        return {
            "migrated": False,
            "source": None,
            "destination": None,
            "backup_path": None,
            "action": "skipped",
            "errors": ["No v2.0 config file found"]
        }

    v2_0_config_path = v2_0_install["config_file"]
    v2_1_config_path = installer.paths.config_file

    logger.info(f"Source config: {v2_0_config_path}")
    logger.info(f"Destination config: {v2_1_config_path}")

    # Validate v2.0 config is valid JSON
    try:
        v2_0_config_content = v2_0_config_path.read_text(encoding="utf-8")
        v2_0_config = json.loads(v2_0_config_content)
        logger.info("v2.0 config validated (valid JSON)")
    except json.JSONDecodeError as e:
        logger.error(f"v2.0 config is invalid JSON: {e}")
        raise ValueError(f"v2.0 config is corrupted (invalid JSON): {e}") from e
    except Exception as e:
        logger.error(f"Cannot read v2.0 config: {e}")
        raise FileNotFoundError(f"Cannot read v2.0 config at {v2_0_config_path}: {e}") from e

    # Create timestamped backup of v2.0 config (before any operations)
    backup_path = None
    if backup:
        backup_path = _create_backup(v2_0_config_path, "v2.0-config")
        logger.info(f"Created v2.0 config backup: {backup_path}")

    # Check if v2.1 config already exists
    if v2_1_config_path.exists():
        logger.info("v2.1 config already exists - conflict detected")

        # Handle conflict based on mode
        if force_overwrite:
            logger.info("Force overwrite enabled - replacing v2.1 config")
            action = _overwrite_config(
                v2_0_config_path,
                v2_1_config_path,
                v2_0_config_content,
                backup=backup
            )
            return {
                "migrated": True,
                "source": v2_0_config_path,
                "destination": v2_1_config_path,
                "backup_path": backup_path,
                "action": action,
                "errors": []
            }

        elif interactive:
            # Prompt user for action
            logger.info("Interactive mode - prompting user")
            choice = _prompt_user_conflict(v2_0_config_path, v2_1_config_path)

            if choice == "1":  # Overwrite
                logger.info("User chose: Overwrite v2.1 config")
                action = _overwrite_config(
                    v2_0_config_path,
                    v2_1_config_path,
                    v2_0_config_content,
                    backup=backup
                )
                return {
                    "migrated": True,
                    "source": v2_0_config_path,
                    "destination": v2_1_config_path,
                    "backup_path": backup_path,
                    "action": action,
                    "errors": []
                }

            elif choice == "2":  # Merge
                logger.info("User chose: Merge configs")
                action = _merge_configs(
                    v2_0_config_path,
                    v2_1_config_path,
                    v2_0_config,
                    backup=backup
                )
                return {
                    "migrated": True,
                    "source": v2_0_config_path,
                    "destination": v2_1_config_path,
                    "backup_path": backup_path,
                    "action": action,
                    "errors": []
                }

            else:  # Skip (choice == "3" or invalid)
                logger.info("User chose: Skip migration")
                return {
                    "migrated": False,
                    "source": v2_0_config_path,
                    "destination": v2_1_config_path,
                    "backup_path": backup_path,
                    "action": "skipped",
                    "errors": ["User chose to skip migration"]
                }

        else:
            # Non-interactive mode with conflict -> skip
            logger.info("Non-interactive mode with conflict - skipping migration")
            return {
                "migrated": False,
                "source": v2_0_config_path,
                "destination": v2_1_config_path,
                "backup_path": backup_path,
                "action": "skipped",
                "errors": ["v2.1 config exists (use --force to overwrite)"]
            }

    # No conflict - perform clean copy
    logger.info("No conflict - performing clean copy")
    try:
        # Ensure destination directory exists
        v2_1_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy config file (preserves content verbatim)
        shutil.copy2(v2_0_config_path, v2_1_config_path)
        logger.info(f"Config copied successfully to {v2_1_config_path}")

        return {
            "migrated": True,
            "source": v2_0_config_path,
            "destination": v2_1_config_path,
            "backup_path": backup_path,
            "action": "copied",
            "errors": []
        }

    except PermissionError as e:
        logger.error(f"Permission denied writing to {v2_1_config_path}: {e}")
        raise InstPermError(
            f"Cannot write to {v2_1_config_path} (insufficient permissions)",
            step="migrate_config",
            details={"path": str(v2_1_config_path)}
        ) from e
    except Exception as e:
        logger.error(f"Error copying config: {e}")
        raise InstallationError(
            f"Failed to copy config: {e}",
            step="migrate_config",
            details={"source": str(v2_0_config_path), "destination": str(v2_1_config_path)}
        ) from e


def _create_backup(file_path: Path, label: str) -> Path:
    """
    Create timestamped backup of a file.

    Args:
        file_path: Path to file to backup
        label: Label for backup (e.g., "v2.0-config", "v2.1-config")

    Returns:
        Path to backup file

    Raises:
        InstallationError: If backup creation fails

    Example:
        backup_path = _create_backup(
            Path("~/.graphiti/graphiti.config.json"),
            "v2.0-config"
        )
        # Returns: ~/.graphiti/graphiti.config.json.backup-v2.0-config-20251225-143022
    """
    from mcp_server.daemon.installer import InstallationError

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = file_path.parent / f"{file_path.name}.backup-{label}-{timestamp}"

    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

        # Verify backup
        if not backup_path.exists() or backup_path.stat().st_size == 0:
            raise InstallationError(
                f"Backup verification failed (file empty or missing)",
                step="create_backup",
                details={"backup_path": str(backup_path)}
            )

        return backup_path

    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise InstallationError(
            f"Cannot create backup of {file_path}: {e}",
            step="create_backup",
            details={"file_path": str(file_path), "backup_path": str(backup_path)}
        ) from e


def _prompt_user_conflict(v2_0_path: Path, v2_1_path: Path) -> str:
    """
    Prompt user to resolve config conflict.

    Args:
        v2_0_path: Path to v2.0 config
        v2_1_path: Path to v2.1 config

    Returns:
        str: User choice ("1", "2", or "3")

    Note:
        Validates input and loops until valid choice provided
    """
    print("\n" + "=" * 70)
    print("Config Migration Conflict Detected")
    print("=" * 70)
    print()
    print("A v2.1 configuration file already exists at:")
    print(f"  {v2_1_path}")
    print()
    print("You also have a v2.0 configuration at:")
    print(f"  {v2_0_path}")
    print()
    print("Choose an option:")
    print("  1. Overwrite - Replace v2.1 config with v2.0 config")
    print("                 (v2.1 config will be backed up)")
    print("  2. Merge     - Keep v2.1 settings, add missing settings from v2.0")
    print("                 (v2.1 config will be backed up)")
    print("  3. Skip      - Keep existing v2.1 config, do not migrate")
    print()
    print("=" * 70)

    while True:
        try:
            choice = input("Your choice (1/2/3): ").strip()
            if choice in ("1", "2", "3"):
                return choice
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print("\nMigration cancelled by user")
            return "3"  # Default to skip on interrupt


def _overwrite_config(
    source_path: Path,
    dest_path: Path,
    source_content: str,
    backup: bool = True
) -> str:
    """
    Overwrite v2.1 config with v2.0 config.

    Args:
        source_path: Path to v2.0 config (source)
        dest_path: Path to v2.1 config (destination)
        source_content: Content of v2.0 config (pre-read)
        backup: If True, backup v2.1 config before overwriting

    Returns:
        str: "overwritten"

    Raises:
        InstallationError: On backup or write failure
    """
    from mcp_server.daemon.installer import InstallationError

    logger.info(f"Overwriting {dest_path} with {source_path}")

    # Backup existing v2.1 config
    if backup:
        v2_1_backup = _create_backup(dest_path, "v2.1-config")
        logger.info(f"Created v2.1 backup: {v2_1_backup}")

    # Write v2.0 content to v2.1 location
    try:
        dest_path.write_text(source_content, encoding="utf-8")
        logger.info(f"Successfully overwrote v2.1 config")
        return "overwritten"
    except Exception as e:
        logger.error(f"Failed to overwrite config: {e}")
        raise InstallationError(
            f"Cannot write to {dest_path}: {e}",
            step="overwrite_config",
            details={"dest_path": str(dest_path)}
        ) from e


def _merge_configs(
    v2_0_path: Path,
    v2_1_path: Path,
    v2_0_config: Dict[str, Any],
    backup: bool = True
) -> str:
    """
    Merge v2.0 config into v2.1 config (v2.1 takes precedence).

    Args:
        v2_0_path: Path to v2.0 config
        v2_1_path: Path to v2.1 config
        v2_0_config: Parsed v2.0 config dict
        backup: If True, backup v2.1 config before merge

    Returns:
        str: "merged"

    Raises:
        InstallationError: On read, merge, or write failure

    Merge logic:
        - v2.1 keys always win on conflict
        - v2.0 keys added if missing in v2.1
        - Deep merge for nested dicts
    """
    from mcp_server.daemon.installer import InstallationError

    logger.info("Merging v2.0 config into v2.1 config")

    # Backup existing v2.1 config
    if backup:
        v2_1_backup = _create_backup(v2_1_path, "v2.1-config")
        logger.info(f"Created v2.1 backup: {v2_1_backup}")

    # Read v2.1 config
    try:
        v2_1_config_content = v2_1_path.read_text(encoding="utf-8")
        v2_1_config = json.loads(v2_1_config_content)
        logger.info("Loaded v2.1 config for merging")
    except json.JSONDecodeError as e:
        logger.warning(f"v2.1 config is invalid JSON - treating as empty: {e}")
        v2_1_config = {}
    except Exception as e:
        logger.error(f"Cannot read v2.1 config: {e}")
        raise InstallationError(
            f"Cannot read v2.1 config at {v2_1_path}: {e}",
            step="merge_configs",
            details={"path": str(v2_1_path)}
        ) from e

    # Deep merge (v2.1 wins on conflicts)
    merged_config = _deep_merge(v2_1_config, v2_0_config)
    logger.info("Config merge complete")

    # Write merged config
    try:
        v2_1_config_path.write_text(
            json.dumps(merged_config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        logger.info(f"Merged config written to {v2_1_path}")
        return "merged"
    except Exception as e:
        logger.error(f"Failed to write merged config: {e}")
        raise InstallationError(
            f"Cannot write merged config to {v2_1_path}: {e}",
            step="merge_configs",
            details={"path": str(v2_1_path)}
        ) from e


def _deep_merge(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries (primary takes precedence).

    Args:
        primary: Dict with higher priority (v2.1 config)
        secondary: Dict with lower priority (v2.0 config)

    Returns:
        Dict: Merged result (primary keys win, secondary fills gaps)

    Example:
        >>> primary = {"a": 1, "b": {"x": 10}}
        >>> secondary = {"b": {"x": 20, "y": 30}, "c": 3}
        >>> _deep_merge(primary, secondary)
        {"a": 1, "b": {"x": 10, "y": 30}, "c": 3}
    """
    result = secondary.copy()

    for key, value in primary.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Both are dicts - merge recursively
            result[key] = _deep_merge(value, result[key])
        else:
            # Primary wins (overwrite or new key)
            result[key] = value

    return result
