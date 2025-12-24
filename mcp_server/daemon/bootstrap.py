#!/usr/bin/env python3
"""
Graphiti Bootstrap Service

Lightweight service that watches graphiti.config.json and manages
the MCP server lifecycle based on the daemon.enabled flag.

This is installed as an OS service (systemd/launchd/Windows Service)
and runs continuously, even when daemon.enabled is false.

Design Principle: Config-primary control. The bootstrap service is the
ONLY thing that starts/stops the MCP server. Users control state via
daemon.enabled in config, not via CLI commands.

See: .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from .venv_manager import (
    VenvManager,
    VenvCreationError,
    IncompatiblePythonVersionError,
)

logger = logging.getLogger("graphiti.bootstrap")


def validate_environment() -> bool:
    """
    Validate that the daemon environment is properly set up.

    Checks:
    - Venv exists at ~/.graphiti/.venv/
    - Python version compatibility

    Returns:
        True if environment is valid

    Raises:
        VenvCreationError: If venv is missing or invalid
        IncompatiblePythonVersionError: If Python version incompatible
    """
    # Check venv exists
    venv_manager = VenvManager()

    # Validate Python version
    try:
        venv_manager.validate_python_version()
    except IncompatiblePythonVersionError as e:
        logger.error(f"Python version check failed: {e}")
        raise

    # Check venv exists
    if not venv_manager.detect_venv():
        logger.error(f"Venv not found at {venv_manager.venv_path}")
        raise VenvCreationError(
            f"Dedicated venv not found at {venv_manager.venv_path}. "
            "Run 'graphiti-mcp daemon install' first."
        )

    logger.info(f"Environment validation passed (venv: {venv_manager.venv_path})")
    return True


class BootstrapService:
    """Watches config and manages MCP server lifecycle."""

    def __init__(self):
        self.config_path = self._get_config_path()
        self.venv_manager = VenvManager()  # Dedicated venv manager
        self.mcp_process: Optional[subprocess.Popen] = None
        self.last_config_mtime: float = 0
        self.last_enabled_state: Optional[bool] = None
        self.poll_interval: int = 5  # seconds
        self.health_check_interval: int = 30  # seconds
        self.last_health_check: float = 0
        self.running: bool = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Validate venv exists on startup (defensive check)
        self._validate_venv_on_startup()

    def _get_config_path(self) -> Path:
        """Get config path (platform-aware)."""
        # Check environment override first
        if env_path := os.environ.get("GRAPHITI_CONFIG"):
            return Path(env_path)

        # Default locations
        if sys.platform == "win32":
            return Path.home() / ".graphiti" / "graphiti.config.json"
        else:
            # Unix: ~/.graphiti/ or XDG_CONFIG_HOME
            xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
            if xdg_config:
                return Path(xdg_config) / "graphiti" / "graphiti.config.json"
            return Path.home() / ".graphiti" / "graphiti.config.json"

    def _validate_venv_on_startup(self):
        """Validate venv exists before starting MCP server (defensive check)."""
        if not self.venv_manager.detect_venv():
            logger.warning(
                f"Venv not found at {self.venv_manager.venv_path}. "
                "MCP server may fail to start. Run: graphiti-mcp daemon install"
            )
            # Note: We log warning but don't fail startup. The bootstrap
            # service should stay running even if venv is missing, to allow
            # recovery via daemon install without service restart.

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self._stop_mcp_server()

    def _read_config(self) -> dict:
        """Read and parse config file."""
        try:
            if self.config_path.exists():
                return json.loads(self.config_path.read_text())
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {e}")
        except Exception as e:
            logger.error(f"Error reading config: {e}")
        return {}

    def _config_changed(self) -> bool:
        """Check if config file was modified."""
        try:
            if self.config_path.exists():
                mtime = self.config_path.stat().st_mtime
                if mtime != self.last_config_mtime:
                    self.last_config_mtime = mtime
                    return True
        except Exception as e:
            logger.warning(f"Error checking config mtime: {e}")
        return False

    def _start_mcp_server(self, config: dict) -> None:
        """Start the MCP server subprocess."""
        if self.mcp_process and self.mcp_process.poll() is None:
            logger.debug("MCP server already running")
            return

        daemon_config = config.get("daemon", {})
        host = daemon_config.get("host", "127.0.0.1")
        port = daemon_config.get("port", 8321)

        # SECURITY: Warn if binding to non-localhost
        if host not in ("127.0.0.1", "localhost", "::1"):
            logger.warning(
                f"SECURITY WARNING: Binding to {host} exposes the server to network. "
                "Set daemon.host to '127.0.0.1' for local-only access."
            )

        # Determine the MCP server script path
        mcp_server_path = self._get_mcp_server_path()

        cmd = [
            sys.executable,
            str(mcp_server_path),
            "--transport", "http",
            "--host", host,
            "--port", str(port),
        ]

        logger.info(f"Starting MCP server on {host}:{port}")
        try:
            # Platform-specific subprocess creation
            if sys.platform == "win32":
                # Don't create new console window on Windows
                self.mcp_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                # Unix platforms
                self.mcp_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            logger.info(f"MCP server started (PID: {self.mcp_process.pid})")
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")

    def _stop_mcp_server(self) -> None:
        """Stop the MCP server subprocess."""
        if self.mcp_process is None:
            return

        if self.mcp_process.poll() is None:
            logger.info("Stopping MCP server...")
            self.mcp_process.terminate()

            # Wait for graceful shutdown
            try:
                self.mcp_process.wait(timeout=10)
                logger.info("MCP server stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("MCP server didn't stop, killing...")
                self.mcp_process.kill()
                self.mcp_process.wait()

        self.mcp_process = None

    def _get_mcp_server_path(self) -> Path:
        """
        Get path to MCP server script.

        Detection order:
        1. GRAPHITI_MCP_SERVER environment variable (explicit override)
        2. Deployed location (~/.graphiti/mcp_server/graphiti_mcp_server.py)
        3. Relative path (development fallback)
        """
        # 1. Check environment override
        if env_path := os.environ.get("GRAPHITI_MCP_SERVER"):
            logger.debug(f"Using MCP server path from env: {env_path}")
            return Path(env_path)

        # 2. Check deployed location (production)
        deployed_path = Path.home() / ".graphiti" / "mcp_server" / "graphiti_mcp_server.py"
        if deployed_path.exists():
            logger.info(f"Using deployed MCP server: {deployed_path}")
            return deployed_path

        # 3. Fallback to relative path (development)
        # bootstrap.py is in mcp_server/daemon/
        # graphiti_mcp_server.py is in mcp_server/
        bootstrap_dir = Path(__file__).parent  # mcp_server/daemon/
        mcp_server_dir = bootstrap_dir.parent  # mcp_server/
        relative_path = mcp_server_dir / "graphiti_mcp_server.py"
        logger.info(f"Using relative MCP server path (development): {relative_path}")
        return relative_path

    def _check_mcp_health(self) -> bool:
        """Check if MCP server process is still running."""
        if self.mcp_process is None:
            return False
        return self.mcp_process.poll() is None

    def run(self) -> None:
        """Main loop: watch config and manage MCP server."""
        logger.info(f"Bootstrap service starting, watching: {self.config_path}")
        logger.info(f"Poll interval: {self.poll_interval}s")

        while self.running:
            try:
                current_time = time.time()

                # Check for config changes
                if self._config_changed() or self.last_enabled_state is None:
                    config = self._read_config()
                    daemon_config = config.get("daemon", {})
                    enabled = daemon_config.get("enabled", False)

                    # Update intervals from config
                    self.poll_interval = daemon_config.get("config_poll_seconds", 5)
                    self.health_check_interval = daemon_config.get("health_check_interval", 30)

                    # State change detected
                    if enabled != self.last_enabled_state:
                        if enabled:
                            logger.info("=" * 60)
                            logger.info("Daemon state changed: ENABLED")
                            logger.info("=" * 60)
                            logger.info(f"Starting MCP server from config: {self.config_path}")
                            logger.info("The server will be available within 5 seconds")
                            self._start_mcp_server(config)
                        else:
                            logger.info("=" * 60)
                            logger.info("Daemon state changed: DISABLED")
                            logger.info("=" * 60)
                            logger.info(f"Stopping MCP server (config: {self.config_path})")
                            logger.info("To re-enable: Set daemon.enabled: true in config")
                            self._stop_mcp_server()

                        self.last_enabled_state = enabled

                # Check if MCP server crashed (restart if enabled)
                if self.last_enabled_state and (current_time - self.last_health_check >= self.health_check_interval):
                    if not self._check_mcp_health():
                        logger.warning("MCP server crashed, restarting...")
                        config = self._read_config()
                        self._start_mcp_server(config)
                    self.last_health_check = current_time

                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in bootstrap loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)

        logger.info("Bootstrap service stopped")


def main():
    """Entry point for bootstrap service."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 60)
    logger.info("Graphiti Bootstrap Service v1.0")
    logger.info("=" * 60)

    service = BootstrapService()
    service.run()


if __name__ == "__main__":
    main()
