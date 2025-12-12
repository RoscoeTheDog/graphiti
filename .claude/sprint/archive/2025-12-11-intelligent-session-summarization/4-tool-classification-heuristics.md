# Story 4: Tool Classification Heuristics

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Implement heuristic-based tool classification that matches tool names to intents and domains without LLM calls. This provides instant classification for known tools (Read, Write, Edit, git, npm, pytest) with zero LLM cost.

## Acceptance Criteria

- [ ] (P0) `ToolIntent` and `ToolDomain` enums as specified
- [ ] (P0) `ToolClassification` Pydantic model with intent, domain, confidence, activity_signals
- [ ] (P0) `ToolClassifier._try_heuristic()` matches name patterns to classifications
- [ ] (P0) Heuristics cover common tools: Read, Write, Edit, Grep, Glob, Bash commands (git, npm, pytest)
- [ ] (P1) Activity signals mapping from intent+domain to vector contributions

## Dependencies

- Story 2: Activity Vector Model

## Implementation Notes

**File to create**: `graphiti_core/session_tracking/tool_classifier.py`

**ToolIntent enum**:
- CREATE, MODIFY, DELETE, READ, SEARCH, EXECUTE, CONFIGURE, COMMUNICATE, VALIDATE, TRANSFORM

**ToolDomain enum**:
- FILESYSTEM, CODE, DATABASE, NETWORK, PROCESS, VERSION_CONTROL, PACKAGE, DOCUMENTATION, TESTING, MEMORY, UNKNOWN

**Heuristic patterns**:
```python
INTENT_PATTERNS = {
    ('read', 'get', 'fetch', 'list', 'show'): (ToolIntent.READ, 0.7),
    ('write', 'create', 'add', 'new', 'insert'): (ToolIntent.CREATE, 0.7),
    ('edit', 'update', 'modify', 'replace'): (ToolIntent.MODIFY, 0.7),
    ('search', 'find', 'grep', 'query'): (ToolIntent.SEARCH, 0.8),
    ('test', 'check', 'validate', 'verify'): (ToolIntent.VALIDATE, 0.7),
    # ...
}

DOMAIN_PATTERNS = {
    ('file', 'dir', 'path', 'folder'): ToolDomain.FILESYSTEM,
    ('symbol', 'code', 'ast', 'serena'): ToolDomain.CODE,
    ('git', 'commit', 'branch', 'merge'): ToolDomain.VERSION_CONTROL,
    # ...
}
```

**Activity signals mapping**: Convert intent+domain to activity vector contributions

## Related Stories

- Story 2: Activity Vector Model (dependency)
- Story 5: LLM Tool Classification with Caching (builds on this)
- Story 7: Unified Tool Classifier (uses this)
