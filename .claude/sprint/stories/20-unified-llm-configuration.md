---
description: Unified LLM Configuration - Single config schema for resilience settings
---

# Story 20: Unified LLM Configuration

**Type**: Implementation
**Status**: completed
**Parent**: None (top-level)
**Created**: 2025-11-27
**Priority**: P1

---

## Description

Unify all LLM resilience configuration into a single, well-documented schema within `graphiti.config.json`. This story consolidates configuration for health checks, retry policies, circuit breaker settings, MCP tool degradation modes, and session tracking resilience into one coherent structure.

**Problem Statement**: LLM resilience features (Stories 17-19) each add configuration options. Without a unified schema, configuration becomes fragmented and hard to understand.

**Design Principle**: One place to configure all LLM resilience behavior. Sensible defaults that work out-of-the-box. Clear documentation.

---

## Acceptance Criteria

### Configuration Schema
- [x] **(P0) AC-20.1**: Define unified `llm_resilience` section in config schema
- [x] **(P0) AC-20.2**: Define `mcp_tools` section for explicit call behavior
- [x] **(P0) AC-20.3**: Define `session_tracking.resilience` section

### Sensible Defaults
- [x] **(P0) AC-20.4**: Health check enabled by default (60 second interval)
- [x] **(P0) AC-20.5**: Retry: 4 attempts, exponential backoff (5-120 seconds)
- [x] **(P0) AC-20.6**: Circuit breaker: enabled, 5 failure threshold, 300s recovery
- [x] **(P0) AC-20.7**: MCP tools: `FAIL` by default (immediate feedback)
- [x] **(P0) AC-20.8**: Session tracking: `STORE_RAW_AND_RETRY` by default (never lose data)

### Pydantic Models
- [x] **(P0) AC-20.9**: Create `LLMHealthCheckConfig` model
- [x] **(P0) AC-20.10**: Create `LLMRetryConfig` model
- [x] **(P0) AC-20.11**: Create `CircuitBreakerConfig` model
- [x] **(P0) AC-20.12**: Create `MCPToolsBehaviorConfig` model
- [x] **(P0) AC-20.13**: Create `SessionTrackingResilienceConfig` model
- [x] **(P0) AC-20.14**: Integrate all into `UnifiedConfig` (as GraphitiConfig)

### Documentation
- [x] **(P0) AC-20.15**: Update `CONFIGURATION.md` with all new options
- [x] **(P1) AC-20.16**: JSON config includes description field
- [x] **(P1) AC-20.17**: Document recommended settings (High Availability vs Cost-Sensitive)

### Validation
- [x] **(P1) AC-20.18**: Validate config on load (Pydantic)
- [x] **(P1) AC-20.19**: Warn on deprecated/invalid options (Pydantic validation)
- [x] **(P1) AC-20.20**: Log effective configuration on startup (log_effective_config method)

---

## Implementation Notes

### Approach

1. **Extend config models**: Add new Pydantic models to `graphiti_core/config/models.py`
2. **Update default config**: Add new sections to `graphiti.config.json`
3. **Document thoroughly**: Update `CONFIGURATION.md` with examples
4. **Validate on load**: Ensure configuration is valid before using

### Complete Configuration Schema

```json
{
  "llm": {
    "health_check": {
      "enabled": true,
      "interval_seconds": 60,
      "on_startup": true,
      "timeout_seconds": 10
    },
    "retry": {
      "max_attempts": 4,
      "initial_delay_seconds": 5,
      "max_delay_seconds": 120,
      "exponential_base": 2,
      "retry_on_rate_limit": true,
      "retry_on_timeout": true
    },
    "circuit_breaker": {
      "enabled": true,
      "failure_threshold": 5,
      "recovery_timeout_seconds": 300,
      "half_open_max_calls": 3
    }
  },
  
  "mcp_tools": {
    "on_llm_unavailable": "FAIL",
    "wait_for_completion_default": true,
    "timeout_seconds": 60
  },
  
  "session_tracking": {
    "enabled": false,
    "resilience": {
      "on_llm_unavailable": "STORE_RAW_AND_RETRY",
      "retry_queue": {
        "max_retries": 5,
        "retry_delays_seconds": [300, 900, 2700, 7200, 21600],
        "max_queue_size": 1000,
        "persist_to_disk": true
      },
      "notifications": {
        "on_permanent_failure": true,
        "notification_method": "log"
      }
    }
  }
}
```

### Files to Modify

- `graphiti_core/config/models.py` (add new Pydantic models)
- `graphiti_core/config/loader.py` (update config loading)
- `graphiti.config.json` (add new sections with defaults)
- `CONFIGURATION.md` (comprehensive documentation)
- `mcp_server/graphiti_mcp_server.py` (use new config)

### Testing

- Unit tests for config validation
- Test default values applied correctly
- Test config override from file
- Test deprecated option warnings
- Integration tests with various configurations

---

## 5W Completeness Check

- **Who**: Graphiti administrators and developers
- **What**: Unified configuration schema for LLM resilience
- **When**: On Graphiti startup and configuration reload
- **Where**: `graphiti.config.json` and `graphiti_core/config/`
- **Why**: Centralize configuration, provide sensible defaults, enable easy customization

---

## Metadata

**Workload Score**: 5 (configuration consolidation)
**Estimated Tokens**: ~25k
**Dependencies**: Stories 17, 18, 19 (defines config they consume)
**Blocks**: Stories 17, 18, 19 (must define schema before they use it)

---

## Execution Order Note

Although Story 20 depends on understanding what Stories 17-19 need, it should be **implemented first** to establish the configuration schema. Stories 17-19 can then consume these configuration values.

Suggested execution order:
1. **Story 20** - Define configuration schema (foundation)
2. **Story 17** - LLM Availability Layer (uses config)
3. **Story 18** - MCP Tools Error Handling (uses config)
4. **Story 19** - Session Tracking Resilience (uses config)
