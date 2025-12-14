"""
Graphiti MCP Server API Package

This package contains HTTP API endpoints and clients for daemon mode:
- management.py: Management API endpoints for daemon control
- client.py: HTTP client for CLI and other tools to communicate with daemon
"""

from mcp_server.api.client import GraphitiClient
from mcp_server.api.management import router, set_server_state

__all__ = [
    "GraphitiClient",
    "router",
    "set_server_state",
]
