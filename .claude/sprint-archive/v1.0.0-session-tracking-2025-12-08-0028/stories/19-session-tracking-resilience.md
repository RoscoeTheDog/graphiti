---
description: Session Tracking Resilience - Retry queue, status dashboard, auto-recovery
---

# Story 19: Session Tracking Resilience

**Type**: Implementation
**Status**: completed
**Parent**: None (top-level)
**Created**: 2025-11-27
**Completed**: 2025-11-28
**Priority**: P0

---

## Description

Implement resilience features for the background session tracking service. Unlike explicit MCP tool calls, session tracking runs continuously in the background - users are NOT waiting for results and cannot immediately react to errors. This requires a different error handling strategy: store what we can, queue for retry, and provide observability.

**Problem Statement**: Currently, if LLM fails during background session indexing, the error is silently swallowed. Users have no way to know their sessions aren't being indexed, and there's no retry mechanism.

**Design Principle**: For background services, gracefully degrade and automatically recover. Never lose data. Provide observability so users can check status when they want.

---

## Acceptance Criteria

### Graceful Degradation
- [x] **(P0) AC-19.1**: Always store raw episode text even if LLM extraction fails
- [x] **(P0) AC-19.2**: Mark failed episodes with `needs_reprocessing = true`
- [x] **(P0) AC-19.3**: Continue processing other sessions even if one fails
- [x] **(P1) AC-19.4**: Implement degradation levels:
  - Level 0: Full Processing (LLM available)
  - Level 1: Partial Processing (store raw + queue retry)
  - Level 2: Raw Storage Only (LLM unavailable)

### Retry Queue
- [x] **(P0) AC-19.5**: Implement persistent retry queue for failed episodes
- [x] **(P0) AC-19.6**: Exponential backoff for retries (5min, 15min, 45min, 2hr, 6hr)
- [x] **(P0) AC-19.7**: Configurable max retries (default: 5)
- [x] **(P0) AC-19.8**: Configurable max queue size (default: 1000)
- [x] **(P1) AC-19.9**: Automatic retry when LLM becomes available (health check triggers)

### Status Dashboard (MCP Tool)
- [x] **(P0) AC-19.10**: Implement `session_tracking_health()` MCP tool returning:
  - Service status (running/stopped/degraded)
  - LLM status (available/unavailable, last check time)
  - Queue status (pending, processing, completed today, failed today)
  - Retry queue (count, next retry time, oldest failure)
- [x] **(P0) AC-19.11**: Include recent failures list with error type and retry count
- [x] **(P1) AC-19.12**: Add `get_failed_episodes()` tool for detailed failure info

### Auto-Recovery
- [x] **(P1) AC-19.13**: Monitor LLM health in background
- [x] **(P1) AC-19.14**: Automatically process retry queue when LLM recovers
- [x] **(P1) AC-19.15**: Log recovery events for debugging

### Notifications (Optional)
- [ ] **(P2) AC-19.16**: Configurable notification on permanent failure
- [ ] **(P2) AC-19.17**: Notification methods: log (default), webhook (optional)
- [ ] **(P2) AC-19.18**: Notification threshold (e.g., after 3 consecutive failures)

---

## Implementation Notes

### Approach

1. **Modify session manager**: Add graceful degradation and retry queue
2. **Add status tool**: New MCP tool for observability
3. **Integrate with Story 17**: Use health monitor for auto-recovery triggers
4. **Persist retry queue**: Store in Neo4j or local file for crash recovery

### Files to Modify

- `graphiti_core/session_tracking/session_manager.py` (major changes)
- `graphiti_core/session_tracking/retry_queue.py` (NEW)
- `graphiti_core/session_tracking/status.py` (NEW)
- `mcp_server/graphiti_mcp_server.py` (add session_tracking_health tool)
- `graphiti_core/config/models.py` (add session_tracking resilience config)
- `graphiti.config.json` (add retry queue config)

### Retry Queue Schema

```python
@dataclass
class FailedEpisode:
    episode_id: str
    session_file: str
    raw_content: str
    error_type: str
    error_message: str
    failed_at: datetime
    retry_count: int
    next_retry_at: datetime
    group_id: str
```

### Status Response Example

```json
{
  "service_status": "running",
  "llm_status": {
    "available": true,
    "last_check": "2025-11-27T12:45:00Z",
    "provider": "openai",
    "error": null
  },
  "queue_status": {
    "pending": 2,
    "processing": 1,
    "completed_today": 15,
    "failed_today": 1
  },
  "retry_queue": {
    "count": 3,
    "next_retry": "2025-11-27T12:50:00Z",
    "oldest_failure": "2025-11-27T12:30:00Z"
  },
  "recent_failures": [
    {
      "episode_id": "ep_abc123",
      "error": "RateLimitError",
      "retry_count": 2,
      "next_retry": "2025-11-27T12:50:00Z"
    }
  ]
}
```

### Testing

- Unit tests for retry queue
- Unit tests for status aggregation
- Integration tests with simulated LLM failures
- Test auto-recovery flow
- Test graceful degradation levels
- Platform-specific tests

---

## 5W Completeness Check

- **Who**: Background session tracking service
- **What**: Retry queue, status dashboard, auto-recovery, graceful degradation
- **When**: Continuously during background session indexing
- **Where**: `graphiti_core/session_tracking/`
- **Why**: Background services can't rely on user to react to errors

---

## Metadata

**Workload Score**: 8 (significant new functionality)
**Estimated Tokens**: ~45k
**Dependencies**: Story 17 (LLM Availability Layer)
**Blocked By**: Story 17
