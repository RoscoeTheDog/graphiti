---
description: LLM Availability Layer - Health checks, error classification, circuit breaker
---

# Story 17: LLM Availability Layer

**Type**: Implementation
**Status**: unassigned
**Parent**: None (top-level)
**Created**: 2025-11-27
**Priority**: P0

---

## Description

Implement a foundational LLM availability layer that provides health monitoring, error classification, and circuit breaker patterns. This layer will be shared by both explicit MCP tool invocations and background session tracking to ensure consistent handling of LLM unavailability scenarios.

**Problem Statement**: Currently, Graphiti has no unified handling for LLM unavailability. Authentication errors, rate limits, and network failures propagate uncaught through the stack, causing silent failures in background tasks and poor user experience in explicit tool calls.

---

## Acceptance Criteria

### Health Monitoring
- [ ] **(P0) AC-17.1**: Implement `LLMHealthMonitor` class with periodic health checks
- [ ] **(P0) AC-17.2**: Validate LLM credentials on Graphiti client initialization
- [ ] **(P0) AC-17.3**: Add `health_check()` method to all LLM clients (OpenAI, Anthropic, Gemini, Groq)
- [ ] **(P1) AC-17.4**: Track health check history (last N checks, success rate)

### Error Classification
- [ ] **(P0) AC-17.5**: Create `LLMErrorClassifier` that distinguishes transient vs permanent errors
- [ ] **(P0) AC-17.6**: Classify errors by type:
  - `PERMANENT`: Invalid API key (401), account suspended, model not available
  - `TRANSIENT`: Rate limit (429), network timeout, server error (5xx), connection refused
- [ ] **(P0) AC-17.7**: Add structured error types: `LLMUnavailableError`, `LLMAuthenticationError`, `LLMRateLimitError`

### Circuit Breaker
- [ ] **(P1) AC-17.8**: Implement circuit breaker pattern to prevent cascading failures
- [ ] **(P1) AC-17.9**: Configurable failure threshold (default: 5 consecutive failures)
- [ ] **(P1) AC-17.10**: Configurable recovery timeout (default: 300 seconds)
- [ ] **(P1) AC-17.11**: Circuit states: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)

### Integration
- [ ] **(P0) AC-17.12**: Wrap all extraction operations (extract_nodes, extract_edges) with error handling
- [ ] **(P0) AC-17.13**: Expose `llm_available` property on Graphiti client
- [ ] **(P1) AC-17.14**: Add MCP tool `llm_health_check()` for explicit health queries

---

## Implementation Notes

### Approach

1. **New module**: `graphiti_core/llm_client/availability.py`
2. **Modify existing**: Update all LLM clients to use new error types
3. **Wrap extraction**: Add try/except in `node_operations.py` and `edge_operations.py`

### Files to Modify

- `graphiti_core/llm_client/availability.py` (NEW)
- `graphiti_core/llm_client/errors.py` (extend)
- `graphiti_core/llm_client/client.py` (add health check)
- `graphiti_core/llm_client/openai_base_client.py` (catch auth errors)
- `graphiti_core/llm_client/anthropic_client.py` (catch auth errors)
- `graphiti_core/llm_client/gemini_client.py` (catch auth errors)
- `graphiti_core/llm_client/groq_client.py` (catch auth errors)
- `graphiti_core/utils/maintenance/node_operations.py` (wrap with error handling)
- `graphiti_core/utils/maintenance/edge_operations.py` (wrap with error handling)
- `graphiti_core/graphiti.py` (add llm_available property)

### Testing

- Unit tests for `LLMHealthMonitor`
- Unit tests for `LLMErrorClassifier`
- Unit tests for circuit breaker state transitions
- Integration tests with mocked LLM failures
- Platform-specific tests (Windows + Unix)

---

## 5W Completeness Check

- **Who**: Graphiti users and background services
- **What**: LLM availability monitoring, error classification, circuit breaker
- **When**: On every LLM call, with periodic health checks
- **Where**: `graphiti_core/llm_client/` and extraction operations
- **Why**: Prevent silent failures, enable graceful degradation, improve reliability

---

## Metadata

**Workload Score**: 8 (substantial new functionality)
**Estimated Tokens**: ~50k
**Dependencies**: None (foundational layer)
**Blocks**: Stories 18, 19
