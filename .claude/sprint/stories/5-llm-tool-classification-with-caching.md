# Story 5: LLM Tool Classification with Caching

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Implement LLM-based classification for unknown tools with multi-level caching (exact match, pattern match, persistent storage). This enables automatic classification of any MCP server or CLI tool, with zero LLM cost after first encounter.

## Acceptance Criteria

- [ ] (P0) `ToolClassifier.classify_batch()` uses cache hierarchy: exact -> pattern -> heuristic -> LLM
- [ ] (P0) LLM classification prompt follows spec format
- [ ] (P0) Cache key generation using tool_name + params hash
- [ ] (P1) `save_cache()` and `_load_cache()` for persistence to JSON file
- [ ] (P1) Integration test: first call uses LLM, second call uses cache

## Dependencies

- Story 4: Tool Classification Heuristics

## Implementation Notes

**File to modify**: `graphiti_core/session_tracking/tool_classifier.py`

**Cache hierarchy**:
1. **Exact cache**: tool_name + params hash -> instant
2. **Pattern cache**: tool_name only -> instant
3. **Heuristic**: Name pattern matching -> instant, ~0.7 confidence
4. **LLM inference**: Full classification -> ~1-2s, cached permanently after

**Cache key format**: `{tool_name}::{md5(normalized_params)[:8]}`

**LLM prompt template**:
```
Classify these tool invocations by their intent and domain.

For each tool call, determine:
1. Intent: create, modify, delete, read, search, execute, configure, validate, transform
2. Domain: filesystem, code, database, network, process, version_control, package, testing, memory
3. Activity Signals: Rate 0.0-1.0 contribution to each dimension

## Tool Invocations to Classify:
{tool_calls_json}
```

**Persistence format**: JSON with "exact" and "pattern" cache sections

## Related Stories

- Story 4: Tool Classification Heuristics (dependency)
- Story 7: Unified Tool Classifier (uses this)
