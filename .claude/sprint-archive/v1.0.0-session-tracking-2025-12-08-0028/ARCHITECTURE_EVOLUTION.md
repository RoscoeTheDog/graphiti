# Session Tracking Integration - Architecture Evolution

**Sprint**: v1.0.0 | **Period**: Nov 13 - Dec 3, 2025

---

## System Architecture (Final State)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLAUDE CODE SESSION                                │
│                                                                             │
│  ~/.claude/projects/{hash}/sessions/*.jsonl                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        graphiti_core/session_tracking/                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐           │
│  │   watcher   │────▶│   parser    │────▶│      filter         │           │
│  │  (watchdog) │     │  (JSONL)    │     │ (93% token reduce)  │           │
│  └─────────────┘     └─────────────┘     └─────────────────────┘           │
│                                                   │                         │
│                                                   ▼                         │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    session_manager                               │       │
│  │  • Periodic checker (5-min intervals)                           │       │
│  │  • Rolling period filter (24h default)                          │       │
│  │  • Inactivity timeout detection                                 │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                              │                                              │
│              ┌───────────────┼───────────────┐                             │
│              ▼               ▼               ▼                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │  summarizer   │  │message_summar-│  │   indexer     │                   │
│  │  (session)    │  │izer (LLM)     │  │  (Graphiti)   │                   │
│  └───────────────┘  └───────────────┘  └───────────────┘                   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │               resilient_indexer (Story 19)                       │       │
│  │  • Graceful degradation (3 levels)                              │       │
│  │  • Retry queue with exponential backoff                         │       │
│  │  • Auto-recovery on LLM availability                            │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    retry_queue (Story 19)                        │       │
│  │  • Persistent queue (Neo4j)                                     │       │
│  │  • Backoff: 5m → 15m → 45m → 2h → 6h                           │       │
│  │  • Max retries: 5 (configurable)                                │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         graphiti_core/llm_client/                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │               availability.py (Story 17)                         │       │
│  │  • LLMHealthMonitor (circuit breaker pattern)                   │       │
│  │  • LLMErrorClassifier (error categorization)                    │       │
│  │  • Health check with exponential backoff                        │       │
│  │  • States: CLOSED → OPEN → HALF_OPEN                           │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      client.py                                   │       │
│  │  • llm_available property                                       │       │
│  │  • Health check integration                                     │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              mcp_server/                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │            graphiti_mcp_server.py (115KB!)                       │       │
│  │  • add_memory() with wait_for_completion (Story 18.3)           │       │
│  │  • session_tracking_start/stop/status/health                    │       │
│  │  • get_failed_episodes() (Story 19.12)                          │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                              │                                              │
│              ┌───────────────┼───────────────┐                             │
│              ▼               ▼               ▼                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │ responses.py  │  │unified_config │  │config_validator│                  │
│  │ (Story 18)    │  │  (Story 20)   │  │               │                   │
│  └───────────────┘  └───────────────┘  └───────────────┘                   │
│                                                                             │
│  responses.py exports:                                                      │
│  • SuccessResponse, DegradedResponse, QueuedResponse, ErrorResponse        │
│  • create_success(), create_degraded(), create_queued(), create_error()    │
│  • create_llm_unavailable_error(), create_llm_auth_error()                 │
│  • create_llm_rate_limit_error() (Story 18.5)                              │
│  • create_network_error(), create_quota_error() (Story 18.2)               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NEO4J                                          │
│                        (Knowledge Graph)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Development Flow & Pivots

### Phase 1: Foundation (Nov 13)

```
┌──────────────────────────────────────────────────────────────┐
│ STORY 1: Foundation Infrastructure                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CREATED:                                                    │
│  ├─ types.py          → Core type definitions               │
│  ├─ parser.py         → JSONL parsing logic                 │
│  └─ path_resolver.py  → Platform-agnostic path handling     │
│                                                              │
│  KEY DECISION: Platform-agnostic from day 1                  │
│  • Windows: C:\Users\... ↔ /c/Users/... (internal)          │
│  • Unix: /home/... (native)                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STORY 2: Smart Filtering (93% token reduction!)              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CREATED:                                                    │
│  ├─ filter.py         → Message filtering logic             │
│  └─ filter_config.py  → Filtering configuration             │
│                                                              │
│  ORIGINAL DESIGN:                                            │
│  ├─ ContentMode enum: FULL | SUMMARY | OMIT                 │
│  └─ Per-message-type filtering                               │
│                                                              │
│  ⚠️ PIVOT (Story 2.3): Config architecture was wrong!        │
│     • filter_config.py duplicated unified_config.py logic    │
│     • ContentMode.SUMMARY had no LLM backend                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STORY 2.3: Configuration Architecture Remediation            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  FIXED:                                                      │
│  ├─ 2.3.1: Unified config as single source of truth         │
│  ├─ 2.3.2: Schema mismatches between config files           │
│  ├─ 2.3.3: Added config_validator.py                        │
│  └─ 2.3.4: Implemented LLM summarization for SUMMARY mode   │
│                                                              │
│  NEW FILES:                                                  │
│  ├─ config_validator.py    → Runtime config validation      │
│  └─ message_summarizer.py  → LLM-based message summarization│
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Phase 2: Core Features (Nov 13-17)

```
┌──────────────────────────────────────────────────────────────┐
│ STORY 3: File Monitoring                                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CREATED:                                                    │
│  ├─ watcher.py         → Watchdog-based file monitoring     │
│  └─ session_manager.py → Session lifecycle management       │
│                                                              │
│  DESIGN: Event-driven with inactivity timeouts               │
│  • Default timeout: 5 minutes                                │
│  • Watches: ~/.claude/projects/*/sessions/*.jsonl            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STORY 4: Graphiti Integration                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ORIGINAL DESIGN:                                            │
│  ├─ 4.1: Session summarizer (LLM summarization layer)       │
│  └─ 4.2: Graphiti storage integration                        │
│                                                              │
│  ⚠️ MAJOR PIVOT: Redundant architecture detected!            │
│                                                              │
│  PROBLEM: Story 4.1 duplicated what Graphiti already does    │
│  • Graphiti has built-in entity extraction                   │
│  • Adding another LLM layer = wasted tokens + latency        │
│                                                              │
│  RESOLUTION:                                                 │
│  ├─ 4.1: SUPERSEDED (removed)                               │
│  ├─ 4.2: SUPERSEDED (merged into direct Graphiti calls)     │
│  └─ 4.3: Created cleanup remediation story                   │
│                                                              │
│  FINAL FILES:                                                │
│  ├─ graphiti_storage.py → Direct Graphiti integration       │
│  ├─ indexer.py          → Episode indexing logic            │
│  └─ summarizer.py       → Session-level summarization       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Phase 3: Integration & Testing (Nov 18-19)

```
┌──────────────────────────────────────────────────────────────┐
│ STORIES 5-8: Integration Layer                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Story 5 - CLI Integration:                                  │
│  └─ session_tracking_cli.py → CLI commands for tracking      │
│                                                              │
│  Story 6 - MCP Tool Integration:                             │
│  └─ session_tracking_start/stop/status in MCP server         │
│                                                              │
│  Story 7 - Testing:                                          │
│  ├─ 7.1: Integration tests ✓                                │
│  ├─ 7.2: Cost validation SUPERSEDED (premature)             │
│  ├─ 7.3: Performance testing SUPERSEDED (premature)         │
│  └─ 7.4: Documentation ✓                                    │
│                                                              │
│  Story 8 - v1.0.0 Milestone:                                 │
│  └─ Initial "complete" state (before scope expansion)        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            │
          ┌─────────────────┴─────────────────┐
          │ ⚠️ CRITICAL SCOPE EXPANSION        │
          │ Stories 9-16 added after v1.0.0   │
          │ validation revealed production    │
          │ readiness gaps                    │
          └─────────────────┬─────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STORIES 9-14: Production Hardening                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Story 9 - Periodic Checker:                                 │
│  └─ session_manager.py enhanced with 5-min polling          │
│     WHY: Watchdog alone missed some session completions      │
│                                                              │
│  Story 10 - Safe Configuration Defaults:                     │
│  └─ unified_config.py → Safe defaults that won't cost $$$   │
│     • session_tracking.enabled = false (explicit opt-in)     │
│     • inactivity_timeout = 300 (5 min)                       │
│                                                              │
│  Story 11 - Template System:                                 │
│  └─ prompts/ directory → Pluggable summarization templates  │
│     WHY: Allow customization without code changes            │
│                                                              │
│  Story 12 - Rolling Period Filter:                           │
│  └─ session_manager.py → Only process recent sessions       │
│     • rolling_period_hours = 24 (default)                    │
│     WHY: Prevent accidental bulk indexing of old sessions    │
│                                                              │
│  Story 13 - Manual Sync Command:                             │
│  └─ manual_sync.py → On-demand historical indexing          │
│     STATUS: STUB (deferred - low priority)                   │
│                                                              │
│  Story 14 - First-Run Experience:                            │
│  └─ Auto-generate graphiti.config.json with safe defaults   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Phase 4: LLM Resilience (Nov 27-28)

```
┌──────────────────────────────────────────────────────────────┐
│ ⚠️ TRIGGER: Validation revealed LLM failure handling gaps    │
│                                                              │
│ PROBLEM: If LLM goes down during session tracking:           │
│ • Episodes silently failed                                   │
│ • No retry mechanism                                         │
│ • User had no visibility                                     │
│ • MCP tools returned misleading success messages             │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STORY 20: Unified LLM Configuration (Foundation)             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CREATED/MODIFIED:                                           │
│  └─ unified_config.py expanded with:                         │
│     • llm.provider (openai|anthropic|azure|etc)             │
│     • llm.health_check_interval_seconds                      │
│     • mcp_tools.on_llm_unavailable (FAIL|STORE_RAW|QUEUE)   │
│     • mcp_tools.wait_for_completion_default                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STORY 17: LLM Availability Layer                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CREATED:                                                    │
│  └─ llm_client/availability.py:                             │
│                                                              │
│     LLMHealthMonitor:                                        │
│     ├─ Circuit breaker (CLOSED → OPEN → HALF_OPEN)          │
│     ├─ Health check polling                                  │
│     └─ llm_available property                                │
│                                                              │
│     LLMErrorClassifier:                                      │
│     ├─ Categorizes errors (auth, rate_limit, network, etc)  │
│     └─ Determines recoverability                             │
│                                                              │
│  CIRCUIT BREAKER STATES:                                     │
│  ┌────────┐ failure ┌────────┐ timeout ┌───────────┐        │
│  │ CLOSED │────────▶│  OPEN  │────────▶│ HALF_OPEN │        │
│  └────────┘         └────────┘         └───────────┘        │
│      ▲                                       │               │
│      └───────────── success ─────────────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STORY 18: MCP Tools Error Handling                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CREATED:                                                    │
│  └─ responses.py:                                            │
│                                                              │
│     Response Types:                                          │
│     ├─ SuccessResponse  → Full processing completed         │
│     ├─ DegradedResponse → Partial success (raw stored)      │
│     ├─ QueuedResponse   → Queued for retry                  │
│     └─ ErrorResponse    → Complete failure                   │
│                                                              │
│     Error Factories:                                         │
│     ├─ create_llm_unavailable_error()                       │
│     ├─ create_llm_auth_error()                              │
│     ├─ create_llm_rate_limit_error()                        │
│     ├─ create_network_error()      (Story 18.2)             │
│     └─ create_quota_error()        (Story 18.2)             │
│                                                              │
│  MODIFIED:                                                   │
│  └─ graphiti_mcp_server.py:                                 │
│     • add_memory() now has wait_for_completion param        │
│     • Proper error responses instead of silent failures     │
│                                                              │
│  REMEDIATION STORIES:                                        │
│  ├─ 18.1: Added episode_id + processing_time_ms to responses│
│  ├─ 18.2: Added network + quota error factories             │
│  └─ 18.3: Implemented wait_for_completion parameter         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STORY 19: Session Tracking Resilience                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CREATED:                                                    │
│  ├─ retry_queue.py:                                         │
│  │   • Persistent queue in Neo4j                            │
│  │   • Exponential backoff (5m→15m→45m→2h→6h)              │
│  │   • Max retries: 5 (configurable)                        │
│  │                                                          │
│  ├─ resilient_indexer.py:                                   │
│  │   • Wraps indexer with retry logic                       │
│  │   • Graceful degradation levels:                         │
│  │     Level 0: Full (LLM available)                        │
│  │     Level 1: Partial (store raw + queue retry)           │
│  │     Level 2: Raw only (LLM unavailable)                  │
│  │                                                          │
│  └─ status.py:                                              │
│      • Service status aggregation                           │
│      • Queue metrics                                        │
│      • Recent failures tracking                             │
│                                                              │
│  NEW MCP TOOLS:                                              │
│  ├─ session_tracking_health() → Dashboard view              │
│  └─ get_failed_episodes()     → Detailed failure info       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Configuration Schema Evolution

```
graphiti.config.json
├── version: "1.0.0"
│
├── neo4j:                        # Existing
│   ├── uri
│   ├── user
│   └── password (→ .env)
│
├── llm:                          # Story 20
│   ├── provider                  # openai|anthropic|azure|gemini|groq
│   ├── model
│   ├── api_key (→ .env)
│   └── health_check_interval_seconds
│
├── session_tracking:             # Stories 1-12
│   ├── enabled                   # false by default (Story 10)
│   ├── watch_path
│   ├── inactivity_timeout_seconds
│   ├── check_interval_seconds    # Story 9
│   ├── rolling_period_hours      # Story 12
│   └── filtering:                # Story 2
│       ├── tool_calls
│       ├── tool_content
│       ├── user_messages
│       └── agent_messages
│
├── mcp_tools:                    # Story 18
│   ├── on_llm_unavailable        # FAIL|STORE_RAW|QUEUE_RETRY
│   ├── wait_for_completion_default
│   └── episode_timeout_seconds
│
└── resilience:                   # Story 19
    ├── retry_max_attempts
    ├── retry_backoff_base_seconds
    └── retry_queue_max_size
```

---

## What Still Needs Production Testing

### Critical (Must test before production use)

| Component | File | What to Test | Risk |
|-----------|------|--------------|------|
| **LLM Circuit Breaker** | `availability.py` | State transitions under real API failures | HIGH - Untested with real rate limits |
| **Retry Queue** | `retry_queue.py` | Queue persistence across restarts | HIGH - Data loss risk |
| **Graceful Degradation** | `resilient_indexer.py` | Level transitions under load | MEDIUM - May miss edge cases |
| **wait_for_completion** | `graphiti_mcp_server.py:1257` | Timeout behavior with slow LLM | MEDIUM - May hang |

### Important (Should test)

| Component | File | What to Test | Risk |
|-----------|------|--------------|------|
| **Rolling Period Filter** | `session_manager.py` | Boundary conditions at 24h mark | LOW - May process extra sessions |
| **Periodic Checker** | `session_manager.py` | Race conditions with watcher | LOW - May duplicate processing |
| **Error Classification** | `availability.py` | All LLM provider error formats | MEDIUM - May misclassify |
| **Config Validation** | `config_validator.py` | Edge cases in schema validation | LOW - May accept invalid config |

### Deferred (Story 13 - Manual Sync)

| Component | Status | Notes |
|-----------|--------|-------|
| `manual_sync.py` | STUB | Historical session indexing - low priority |

---

## File Size Concerns

| File | Size | Concern |
|------|------|---------|
| `graphiti_mcp_server.py` | **115KB** | Too large - candidate for splitting |
| `unified_config.py` | 32KB | Acceptable but growing |
| `availability.py` | 25KB | Acceptable |

**Recommendation**: `graphiti_mcp_server.py` should be refactored into:
- `mcp_server/tools/memory.py`
- `mcp_server/tools/session_tracking.py`
- `mcp_server/tools/search.py`
- `mcp_server/core.py`

---

## Key Architectural Decisions Log

| Decision | Date | Rationale | Files Affected |
|----------|------|-----------|----------------|
| Platform-agnostic paths | Nov 13 | Windows support from day 1 | `path_resolver.py` |
| 93% token reduction via filtering | Nov 13 | Cost optimization | `filter.py` |
| Remove LLM summarization layer | Nov 13 | Redundant with Graphiti | `4.1`, `4.2` superseded |
| Safe defaults (tracking=off) | Nov 19 | Prevent accidental costs | `unified_config.py` |
| Rolling period filter | Nov 19 | Prevent bulk indexing | `session_manager.py` |
| Circuit breaker for LLM | Nov 27 | Production resilience | `availability.py` |
| Retry queue in Neo4j | Nov 28 | Persistence across restarts | `retry_queue.py` |
| Structured response types | Nov 27 | Better error handling UX | `responses.py` |

---

*Generated: 2025-12-03*
