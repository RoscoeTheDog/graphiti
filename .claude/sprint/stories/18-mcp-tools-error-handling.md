---
description: MCP Tools Error Handling - Immediate feedback for explicit tool invocations
---

# Story 18: MCP Tools Error Handling

**Type**: Implementation
**Status**: completed
**Parent**: None (top-level)
**Created**: 2025-11-27
**Completed**: 2025-11-28
**Priority**: P0

**Completion Notes**: Core implementation completed. Gaps found during validation led to remediation stories 18.1, 18.2, 18.3 which have all been implemented.

---

## Description

Implement proper error handling for explicit MCP tool invocations (`add_memory`, `search_memory_nodes`, etc.). When users explicitly call these tools, they expect immediate, actionable feedback about success or failure - not silent failures or false success messages.

**Problem Statement**: Currently, `add_memory()` returns "Episode queued successfully" immediately, then processes in background. If LLM fails, the error is silently swallowed and the user never knows their data wasn't indexed.

**Design Principle**: For explicit tool calls, users are actively waiting and can react to errors. Provide immediate feedback with clear, actionable error messages.

---

## Acceptance Criteria

### Response Types
- [x] **(P0) AC-18.1**: Define structured response types:
  - `SuccessResponse`: Full processing completed
  - `DegradedResponse`: Partial success (raw stored, entities not extracted)
  - `QueuedResponse`: Queued for retry when LLM available
  - `ErrorResponse`: Complete failure with actionable message
- [x] **(P0) AC-18.2**: All responses include: status, message, episode_id, processing_time_ms *(Remediation 18.1)*

### Configurable Degradation Modes
- [x] **(P0) AC-18.3**: Add `on_llm_unavailable` config option for MCP tools:
  - `FAIL` (default): Return error immediately, don't store
  - `STORE_RAW`: Store raw episode without entities, return degraded success
  - `QUEUE_RETRY`: Queue for background retry, return queued status
- [x] **(P0) AC-18.4**: Implement each degradation mode in `add_memory()`

### Error Messages
- [x] **(P0) AC-18.5**: Provide actionable error messages: *(Remediation 18.2)*
  - Invalid API key: "LLM API key is invalid. Check your OPENAI_API_KEY."
  - Rate limit: "LLM rate limit exceeded. Retry in {seconds} seconds."
  - Network error: "Cannot reach LLM provider. Check network connection."
  - Quota exceeded: "LLM quota exceeded. Check billing at {provider_url}."
- [x] **(P0) AC-18.6**: Include `recoverable` boolean and `suggestion` field in errors
- [x] **(P1) AC-18.7**: Include `retry_after_seconds` for transient errors

### Synchronous Processing Option
- [x] **(P1) AC-18.8**: Add `wait_for_completion` parameter to `add_memory()` *(Remediation 18.3)*
  - `true`: Block until processing complete (current behavior for other tools)
  - `false`: Return immediately after queueing (current behavior)
- [x] **(P1) AC-18.9**: Default to `true` for better UX (explicit calls expect results)

### Integration with Availability Layer
- [x] **(P0) AC-18.10**: Use `LLMErrorClassifier` from Story 17 for error classification
- [x] **(P0) AC-18.11**: Check `llm_available` before attempting extraction
- [x] **(P1) AC-18.12**: Respect circuit breaker state (don't attempt if OPEN)

---

## Implementation Notes

### Approach

1. **Modify add_memory()**: Remove background-only processing, add sync option
2. **Add response types**: Define Pydantic models for structured responses
3. **Add config option**: Extend `graphiti.config.json` schema
4. **Integrate with Story 17**: Use availability layer for error handling

### Files to Modify

- `mcp_server/graphiti_mcp_server.py` (major changes to add_memory)
- `mcp_server/models.py` (NEW - response type definitions)
- `graphiti_core/config/models.py` (add mcp_tools config section)
- `graphiti.config.json` (add on_llm_unavailable option)
- `CONFIGURATION.md` (document new options)

### Response Examples

**Success**:
```json
{
  "status": "success",
  "message": "Episode 'meeting notes' indexed successfully",
  "episode_id": "ep_abc123",
  "entities_extracted": 5,
  "relationships_extracted": 3,
  "processing_time_ms": 1250
}
```

**Error**:
```json
{
  "status": "error",
  "error_type": "llm_unavailable",
  "error_code": "INVALID_API_KEY",
  "message": "LLM API key is invalid or revoked",
  "recoverable": false,
  "suggestion": "Verify API key at https://platform.openai.com/api-keys"
}
```

**Degraded**:
```json
{
  "status": "degraded",
  "message": "Episode stored but entities not extracted (LLM unavailable)",
  "episode_id": "ep_abc123",
  "raw_stored": true,
  "entities_extracted": 0,
  "reprocess_available": true
}
```

### Testing

- Unit tests for each response type
- Integration tests with mocked LLM failures
- Test each degradation mode (FAIL, STORE_RAW, QUEUE_RETRY)
- Test wait_for_completion behavior
- Platform-specific tests

---

## 5W Completeness Check

- **Who**: Users explicitly calling MCP tools (add_memory, etc.)
- **What**: Immediate, actionable error feedback with configurable degradation
- **When**: On every explicit MCP tool invocation
- **Where**: `mcp_server/graphiti_mcp_server.py`
- **Why**: Users expect feedback when they explicitly call a tool

---

## Metadata

**Workload Score**: 7 (significant changes to MCP server)
**Estimated Tokens**: ~40k
**Dependencies**: Story 17 (LLM Availability Layer)
**Blocked By**: Story 17
