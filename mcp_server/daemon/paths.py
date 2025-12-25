"""
Platform-aware path resolution for Graphiti MCP server installation.

This module provides platform-specific paths for the professional per-user daemon
architecture (v2.1), following industry conventions (Ollama, VS Code, Discord pattern).

Key features:
- Frozen installation in platform-appropriate Programs directory
- Complete separation of executables, config, and runtime data
- Repository-independent (deleting source repo doesn't break daemon)
- No admin privileges required
- Clean uninstall by removing two directories

Platform conventions:
- Windows: %LOCALAPPDATA%\\Programs\\Graphiti\\ (install), %LOCALAPPDATA%\\Graphiti\\ (config/state)
- macOS: ~/Library/Application Support/Graphiti/ (install), ~/Library/Preferences/Graphiti/ (config), ~/Library/Logs/Graphiti/ (state)
- Linux: XDG Base Directory spec (~/.local/share/graphiti/, ~/.config/graphiti/, ~/.local/state/graphiti/)

Example usage:
    >>> from mcp_server.daemon.paths import get_paths
    >>> paths = get_paths()
    >>> print(paths.install_dir)  # Platform-specific install directory
    >>> print(paths.config_file)  # Platform-specific config file path

Version: 2.1.0
Created: 2025-12-25
"""

import os
import sys
from pathlib import Path
from typing import NamedTuple


class GraphitiPaths(NamedTuple):
    """Platform-specific paths for Graphiti installation.

    Attributes:
        install_dir: Directory containing executables and libraries (frozen installation)
        config_dir: Directory for user configuration files
        state_dir: Directory for logs, data, and runtime state
        config_file: Full path to the main configuration file (graphiti.config.json)
    """
    install_dir: Path
    config_dir: Path
    state_dir: Path
    config_file: Path


def get_paths() -> GraphitiPaths:
    """Get platform-appropriate Graphiti paths.

    Determines the correct installation, configuration, and state directories
    based on the current platform (Windows, macOS, or Linux). Respects
    platform-specific environment variables for customization.

    Environment variable overrides:
    - Windows: LOCALAPPDATA (defaults to %USERPROFILE%\\AppData\\Local)
    - Linux: XDG_DATA_HOME, XDG_CONFIG_HOME, XDG_STATE_HOME (XDG Base Directory spec)
    - macOS: No environment overrides (uses fixed Library paths)

    Returns:
        GraphitiPaths: NamedTuple with install_dir, config_dir, state_dir, config_file

    Example:
        >>> paths = get_paths()
        >>> paths.install_dir  # WindowsPath('C:/Users/user/AppData/Local/Programs/Graphiti')
        >>> paths.config_file  # WindowsPath('C:/Users/user/AppData/Local/Graphiti/config/graphiti.config.json')
    """

    if sys.platform == "win32":
        # Windows: Use LOCALAPPDATA (C:\Users\{user}\AppData\Local)
        local_app_data = Path(os.environ.get(
            "LOCALAPPDATA",
            Path.home() / "AppData" / "Local"
        ))
        install_dir = local_app_data / "Programs" / "Graphiti"
        config_dir = local_app_data / "Graphiti" / "config"
        state_dir = local_app_data / "Graphiti"

    elif sys.platform == "darwin":
        # macOS: Use Library directories (no environment variable overrides)
        install_dir = Path.home() / "Library" / "Application Support" / "Graphiti"
        config_dir = Path.home() / "Library" / "Preferences" / "Graphiti"
        state_dir = Path.home() / "Library" / "Logs" / "Graphiti"

    else:
        # Linux and others: Follow XDG Base Directory specification
        xdg_data = Path(os.environ.get(
            "XDG_DATA_HOME",
            Path.home() / ".local" / "share"
        ))
        xdg_config = Path(os.environ.get(
            "XDG_CONFIG_HOME",
            Path.home() / ".config"
        ))
        xdg_state = Path(os.environ.get(
            "XDG_STATE_HOME",
            Path.home() / ".local" / "state"
        ))

        install_dir = xdg_data / "graphiti"
        config_dir = xdg_config / "graphiti"
        state_dir = xdg_state / "graphiti"

    return GraphitiPaths(
        install_dir=install_dir,
        config_dir=config_dir,
        state_dir=state_dir,
        config_file=config_dir / "graphiti.config.json"
    )


# Convenience accessors for common paths

def get_install_dir() -> Path:
    """Get the installation directory (executables and libraries).

    Returns:
        Path: Platform-specific install directory

    Example:
        >>> get_install_dir()  # WindowsPath('C:/Users/user/AppData/Local/Programs/Graphiti')
    """
    return get_paths().install_dir


def get_config_dir() -> Path:
    """Get the configuration directory.

    Returns:
        Path: Platform-specific config directory

    Example:
        >>> get_config_dir()  # WindowsPath('C:/Users/user/AppData/Local/Graphiti/config')
    """
    return get_paths().config_dir


def get_config_file() -> Path:
    """Get the main configuration file path.

    Returns:
        Path: Full path to graphiti.config.json

    Example:
        >>> get_config_file()  # WindowsPath('C:/Users/user/AppData/Local/Graphiti/config/graphiti.config.json')
    """
    return get_paths().config_file


def get_log_dir() -> Path:
    """Get the log directory.

    Platform-specific behavior:
    - macOS: Returns state_dir (which points to Library/Logs/Graphiti)
    - Windows/Linux: Returns state_dir/logs subdirectory

    Returns:
        Path: Platform-specific log directory

    Example:
        >>> get_log_dir()  # WindowsPath('C:/Users/user/AppData/Local/Graphiti/logs')
    """
    paths = get_paths()
    if sys.platform == "darwin":
        return paths.state_dir  # Already points to Logs on macOS
    return paths.state_dir / "logs"


def get_data_dir() -> Path:
    """Get the runtime data directory.

    Platform-specific behavior:
    - macOS: Uses Library/Caches/Graphiti (separate from state_dir)
    - Windows/Linux: Returns state_dir/data subdirectory

    Returns:
        Path: Platform-specific data directory

    Example:
        >>> get_data_dir()  # WindowsPath('C:/Users/user/AppData/Local/Graphiti/data')
    """
    paths = get_paths()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "Graphiti"
    return paths.state_dir / "data"
