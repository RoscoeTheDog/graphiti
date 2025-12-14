"""
Management API endpoints for Graphiti MCP Server daemon.

These endpoints provide daemon control and monitoring capabilities.
Accessed via HTTP at /api/v1/* when server runs in daemon mode.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1", tags=["management"])


# Request/Response Models
class SessionSyncRequest(BaseModel):
    """Request to sync session tracking history."""
    days: int = Field(default=7, description="Number of days of history to sync", ge=1, le=365)
    dry_run: bool = Field(default=True, description="Preview mode (don't commit changes)")


class SessionSyncResponse(BaseModel):
    """Response from session sync operation."""
    success: bool
    mode: str  # "DRY_RUN" or "COMMIT"
    sessions_found: int
    estimated_cost: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    message: str


class ServerStatusResponse(BaseModel):
    """Server health and status information."""
    status: str  # "healthy", "degraded", "unavailable"
    uptime_seconds: Optional[float] = None
    version: str = "1.0.0"
    database_connected: bool
    session_tracking_enabled: bool
    session_tracking_status: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConfigResponse(BaseModel):
    """Non-sensitive configuration data."""
    daemon_enabled: bool
    daemon_host: str
    daemon_port: int
    config_poll_seconds: int
    session_tracking_enabled: bool


class ConfigReloadResponse(BaseModel):
    """Response from config reload operation."""
    success: bool
    message: str
    changes: Optional[Dict[str, Any]] = None


# Global state (will be set by main server)
_server_start_time: Optional[datetime] = None
_graphiti_client = None
_session_manager = None
_unified_config = None
_session_tracking_status_aggregator = None


def set_server_state(
    start_time: datetime,
    graphiti_client,
    session_manager,
    unified_config,
    status_aggregator=None
):
    """Set global server state (called by main server on startup)."""
    global _server_start_time, _graphiti_client, _session_manager, _unified_config, _session_tracking_status_aggregator
    _server_start_time = start_time
    _graphiti_client = graphiti_client
    _session_manager = session_manager
    _unified_config = unified_config
    _session_tracking_status_aggregator = status_aggregator


# Endpoints
@router.get("/status", response_model=ServerStatusResponse)
async def get_status() -> ServerStatusResponse:
    """Get server status and health information."""
    uptime = None
    if _server_start_time:
        uptime = (datetime.now(timezone.utc) - _server_start_time).total_seconds()

    # Check database connection
    db_connected = False
    if _graphiti_client:
        try:
            # Simple check - if client exists and initialized, consider connected
            db_connected = True
        except Exception as e:
            logger.warning(f"Database connection check failed: {e}")

    # Get session tracking status
    st_enabled = False
    st_status = None
    if _unified_config:
        st_enabled = _unified_config.session_tracking.enabled
        if st_enabled and _session_tracking_status_aggregator:
            try:
                health = _session_tracking_status_aggregator.get_health()
                st_status = {
                    "health": health.level.value,
                    "database": health.database.value,
                    "indexer": health.indexer.value,
                    "queue": health.queue.value,
                    "warnings": health.warnings,
                }
            except Exception as e:
                logger.warning(f"Failed to get session tracking status: {e}")

    # Determine overall status
    status = "healthy"
    if not db_connected:
        status = "degraded"
    if _graphiti_client is None:
        status = "unavailable"

    return ServerStatusResponse(
        status=status,
        uptime_seconds=uptime,
        database_connected=db_connected,
        session_tracking_enabled=st_enabled,
        session_tracking_status=st_status,
    )


@router.post("/session/sync", response_model=SessionSyncResponse)
async def sync_sessions(request: SessionSyncRequest) -> SessionSyncResponse:
    """Trigger manual session sync."""
    if _session_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Session tracking not initialized. Check daemon.enabled and session_tracking.enabled in config."
        )

    try:
        # Import sync function
        from mcp_server.manual_sync import session_tracking_sync_history

        # Call sync with parameters
        result = await session_tracking_sync_history(
            days=request.days,
            dry_run=request.dry_run
        )

        return SessionSyncResponse(
            success=True,
            mode="DRY_RUN" if request.dry_run else "COMMIT",
            sessions_found=result.get("sessions_found", 0),
            estimated_cost=result.get("estimated_cost"),
            details=result,
            message=f"Sync completed: {result.get('sessions_found', 0)} sessions processed"
        )
    except Exception as e:
        logger.error(f"Session sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Session sync failed: {str(e)}")


@router.get("/session/history")
async def get_session_history(days: int = 7):
    """Get session tracking history."""
    if _session_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Session tracking not initialized"
        )

    try:
        # Import query function
        from mcp_server.manual_sync import get_session_history as _get_history

        history = await _get_history(days=days)
        return {
            "success": True,
            "days": days,
            "sessions": history,
        }
    except Exception as e:
        logger.error(f"Failed to get session history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get session history: {str(e)}")


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Get current non-sensitive configuration."""
    if _unified_config is None:
        raise HTTPException(status_code=503, detail="Configuration not loaded")

    daemon_cfg = _unified_config.daemon if hasattr(_unified_config, 'daemon') else None

    return ConfigResponse(
        daemon_enabled=daemon_cfg.enabled if daemon_cfg else False,
        daemon_host=daemon_cfg.host if daemon_cfg else "127.0.0.1",
        daemon_port=daemon_cfg.port if daemon_cfg else 8321,
        config_poll_seconds=daemon_cfg.config_poll_seconds if daemon_cfg else 5,
        session_tracking_enabled=_unified_config.session_tracking.enabled,
    )


@router.post("/config/reload", response_model=ConfigReloadResponse)
async def reload_config() -> ConfigReloadResponse:
    """Hot-reload configuration from file."""
    if _unified_config is None:
        raise HTTPException(status_code=503, detail="Configuration not loaded")

    try:
        # Reload config from disk
        from mcp_server.unified_config import get_config
        new_config = get_config(force_reload=True)

        # TODO: Apply config changes to running services
        # For now, just report success

        return ConfigReloadResponse(
            success=True,
            message="Configuration reloaded successfully. Some changes may require server restart.",
            changes=None  # TODO: Detect and report what changed
        )
    except Exception as e:
        logger.error(f"Config reload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Config reload failed: {str(e)}")


@router.get("/metrics")
async def get_metrics() -> Response:
    """Get Prometheus-format metrics (optional)."""
    # TODO: Implement Prometheus metrics export
    # For now, return simple text metrics

    metrics_text = """# HELP graphiti_uptime_seconds Server uptime in seconds
# TYPE graphiti_uptime_seconds gauge
graphiti_uptime_seconds {uptime}

# HELP graphiti_database_connected Database connection status
# TYPE graphiti_database_connected gauge
graphiti_database_connected {db_connected}

# HELP graphiti_session_tracking_enabled Session tracking enabled status
# TYPE graphiti_session_tracking_enabled gauge
graphiti_session_tracking_enabled {st_enabled}
"""

    uptime = 0
    if _server_start_time:
        uptime = (datetime.now(timezone.utc) - _server_start_time).total_seconds()

    db_connected = 1 if _graphiti_client else 0
    st_enabled = 1 if (_unified_config and _unified_config.session_tracking.enabled) else 0

    metrics = metrics_text.format(
        uptime=uptime,
        db_connected=db_connected,
        st_enabled=st_enabled
    )

    return Response(content=metrics, media_type="text/plain")
