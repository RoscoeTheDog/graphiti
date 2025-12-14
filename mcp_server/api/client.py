"""
GraphitiClient - HTTP client for Graphiti MCP daemon.

This client provides a simple interface for CLI tools and other Python applications
to communicate with a running Graphiti MCP daemon over HTTP.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None  # Will raise helpful error if used without httpx installed

logger = logging.getLogger(__name__)


class GraphitiClient:
    """HTTP client for Graphiti MCP daemon.

    Provides methods to interact with the Management API endpoints.
    Includes auto-discovery of daemon URL and actionable error messages.

    Example:
        ```python
        from mcp_server.api.client import GraphitiClient

        # Auto-discover daemon URL
        client = GraphitiClient()

        # Or specify URL explicitly
        client = GraphitiClient(base_url="http://localhost:8321")

        # Check if daemon is running
        if client.health_check():
            # Get server status
            status = client.get_status()
            print(f"Server uptime: {status['uptime_seconds']}s")

            # Sync sessions
            result = client.sync_sessions(days=7, dry_run=True)
            print(f"Found {result['sessions_found']} sessions")
        ```
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """Initialize the GraphitiClient.

        Args:
            base_url: Base URL of the daemon (e.g., "http://127.0.0.1:8321").
                     If None, uses auto-discovery (env var → config file → default).
            timeout: Request timeout in seconds (default: 30.0)

        Raises:
            ImportError: If httpx is not installed
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for GraphitiClient. Install with: pip install httpx"
            )

        self.config_path = self._get_config_path()
        self.base_url = base_url or self._get_url_from_discovery()
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def _get_config_path(self) -> Path:
        """Get path to graphiti config file."""
        # Check environment override
        if env_path := os.environ.get("GRAPHITI_CONFIG"):
            return Path(env_path)

        # Default location
        return Path.home() / ".graphiti" / "graphiti.config.json"

    def _get_url_from_discovery(self) -> str:
        """Auto-discover daemon URL with fallback chain.

        Priority:
        1. GRAPHITI_URL environment variable
        2. Config file (daemon.host + daemon.port)
        3. Default (http://127.0.0.1:8321)

        Returns:
            str: Base URL for the daemon
        """
        # 1. Environment variable
        if url := os.environ.get("GRAPHITI_URL"):
            logger.debug(f"Using daemon URL from GRAPHITI_URL: {url}")
            return url

        # 2. Config file
        if self.config_path.exists():
            try:
                config = json.loads(self.config_path.read_text())
                daemon_config = config.get("daemon", {})

                # Check for explicit URL
                if url := daemon_config.get("url"):
                    logger.debug(f"Using daemon URL from config: {url}")
                    return url

                # Build from host + port
                host = daemon_config.get("host", "127.0.0.1")
                port = daemon_config.get("port", 8321)
                url = f"http://{host}:{port}"
                logger.debug(f"Using daemon URL from config (host:port): {url}")
                return url
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read config file: {e}")

        # 3. Default
        default_url = "http://127.0.0.1:8321"
        logger.debug(f"Using default daemon URL: {default_url}")
        return default_url

    def _check_daemon_enabled(self) -> bool:
        """Check if daemon is enabled in config file.

        Returns:
            bool: True if daemon.enabled is true, False otherwise
        """
        if not self.config_path.exists():
            return False

        try:
            config = json.loads(self.config_path.read_text())
            return config.get("daemon", {}).get("enabled", False)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to check daemon.enabled: {e}")
            return False

    def _handle_connection_error(self, operation: str) -> None:
        """Provide actionable error message when daemon is unreachable.

        Args:
            operation: Description of the operation that failed (for error message)
        """
        if not self._check_daemon_enabled():
            # Daemon is disabled in config
            print(f"[ERROR] Graphiti daemon is disabled.", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"   To enable, edit: {self.config_path}", file=sys.stderr)
            print(f"   Set: \"daemon\": {{ \"enabled\": true }}", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"   The daemon will start automatically within 5 seconds.", file=sys.stderr)
            print(f"   (Requires bootstrap service to be installed)", file=sys.stderr)
        else:
            # Daemon enabled but not responding
            print(f"[ERROR] Cannot connect to Graphiti daemon at {self.base_url}", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"   Config shows daemon.enabled: true", file=sys.stderr)
            print(f"   But server is not responding.", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"   Check if bootstrap service is running:", file=sys.stderr)
            print(f"     graphiti-mcp daemon status", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"   View logs:", file=sys.stderr)
            print(f"     graphiti-mcp daemon logs", file=sys.stderr)

        sys.exit(1)

    # Public API methods

    def health_check(self) -> bool:
        """Check if daemon is running and responding.

        Returns:
            bool: True if daemon is healthy, False otherwise
        """
        try:
            response = self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except httpx.ConnectError:
            return False
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get server status and health information.

        Returns:
            dict: Status information including uptime, database status, etc.

        Raises:
            SystemExit: If daemon is unreachable (prints actionable error)
        """
        try:
            response = self.client.get(f"{self.base_url}/api/v1/status")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            self._handle_connection_error("get status")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting status: {e}")
            raise

    def sync_sessions(
        self,
        days: int = 7,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Trigger session sync via HTTP API.

        Args:
            days: Number of days of history to sync (1-365)
            dry_run: If True, preview mode (don't commit changes)

        Returns:
            dict: Sync results including sessions found and estimated cost

        Raises:
            SystemExit: If daemon is unreachable (prints actionable error)
        """
        try:
            response = self.client.post(
                f"{self.base_url}/api/v1/session/sync",
                json={"days": days, "dry_run": dry_run}
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            self._handle_connection_error("sync sessions")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error syncing sessions: {e}")
            raise

    def get_session_history(self, days: int = 7) -> Dict[str, Any]:
        """Get session tracking history.

        Args:
            days: Number of days of history to retrieve

        Returns:
            dict: Session history data

        Raises:
            SystemExit: If daemon is unreachable (prints actionable error)
        """
        try:
            response = self.client.get(
                f"{self.base_url}/api/v1/session/history",
                params={"days": days}
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            self._handle_connection_error("get session history")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting session history: {e}")
            raise

    def get_config(self) -> Dict[str, Any]:
        """Get current non-sensitive configuration.

        Returns:
            dict: Configuration data (non-sensitive fields only)

        Raises:
            SystemExit: If daemon is unreachable (prints actionable error)
        """
        try:
            response = self.client.get(f"{self.base_url}/api/v1/config")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            self._handle_connection_error("get config")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting config: {e}")
            raise

    def reload_config(self) -> Dict[str, Any]:
        """Hot-reload configuration from file.

        Returns:
            dict: Reload results including changes detected

        Raises:
            SystemExit: If daemon is unreachable (prints actionable error)
        """
        try:
            response = self.client.post(f"{self.base_url}/api/v1/config/reload")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            self._handle_connection_error("reload config")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error reloading config: {e}")
            raise

    def get_metrics(self) -> str:
        """Get Prometheus-format metrics.

        Returns:
            str: Metrics in Prometheus text format

        Raises:
            SystemExit: If daemon is unreachable (prints actionable error)
        """
        try:
            response = self.client.get(f"{self.base_url}/api/v1/metrics")
            response.raise_for_status()
            return response.text
        except httpx.ConnectError:
            self._handle_connection_error("get metrics")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting metrics: {e}")
            raise

    def close(self):
        """Close the HTTP client connection."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
