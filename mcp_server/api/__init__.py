"""
Graphiti MCP Server API Package

This package contains HTTP API endpoints and clients for daemon mode:
- management.py: Management API endpoints for daemon control (requires fastapi)
- client.py: HTTP client for CLI and other tools to communicate with daemon
"""

# Import GraphitiClient directly (no fastapi dependency)
from mcp_server.api.client import GraphitiClient

# Lazy imports for management API (requires fastapi - only needed by server)
def get_router():
    """Lazy import of management router (requires fastapi)."""
    from mcp_server.api.management import router
    return router

def get_set_server_state():
    """Lazy import of set_server_state (requires fastapi)."""
    from mcp_server.api.management import set_server_state
    return set_server_state

__all__ = [
    "GraphitiClient",
    "get_router",
    "get_set_server_state",
]
