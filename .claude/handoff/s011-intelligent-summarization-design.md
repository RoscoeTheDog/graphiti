# Session Handoff: Intelligent Session Summarization Design

**Session ID**: 2025-12-11-intelligent-summarization
**Status**: DESIGN COMPLETE - READY FOR IMPLEMENTATION
**Branch**: `sprint/v2.0.0/global-session-tracking`
**Date**: 2025-12-11

---

## Executive Summary

Designed a comprehensive enhancement to Graphiti's session summarization system that replaces discrete session type classification with a **multi-dimensional activity vector** (8 dimensions) and introduces **LLM-inferred tool classification** for unknown MCP servers and arbitrary bash commands.

**Key Deliverables Created**:
1. `INTELLIGENT_SESSION_SUMMARIZATION_SPEC_v1.0.md` (55KB) - Full specification
2. `INTELLIGENT_SUMMARIZATION_DESIGN_RATIONALE.md` (10KB) - Design conversation history

---

## Context: Why This Change

### Problem 1: Discrete Classification Fails

Original proposal used `SessionType` enum (DEBUGGING, CONFIGURATION, etc.), but user identified critical flaw:

> "What if there are two topics that are interwoven like a bug that was caused by changing the configuration, and the agent fixes the configuration to resolve the bug during debugging process?"

**Solution**: Replace discrete enum with continuous `ActivityVector`:
```python
ActivityVector(
    building=0.1, fixing=0.8, configuring=0.7,
    exploring=0.4, testing=0.5, ...
)
# Session can be 80% fixing + 70% configuring simultaneously
```

### Problem 2: Hard-Coded Tool Mappings

Original tool detection hard-coded known tools, but user identified:

> "We can't possibly hard-code all the tool calls. The LLM may use MCP server extensions that are unknown in quantity. Plus bash commands could be downloaded/installed repositories, softwares, etc."

**Solution**: LLM-inferred classification with multi-level caching:
```
Tool → Exact Cache → Pattern Cache → Heuristic → LLM (cached after)
```

---

## Design Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Classification model | 8-dimensional ActivityVector | No false dichotomies, handles blended sessions |
| Tool classification | LLM inference + 4-level cache | Handles unknown MCP servers and arbitrary CLIs |
| New schema fields | `key_decisions`, `errors_resolved` | Prevents repeated debates, debugging continuity |
| Extraction algorithm | Affinity-weighted priorities | Dynamic field inclusion based on activity |
| Template updates | "1 paragraph or less" | User requested more specificity |

---

## Specification Overview

### ActivityVector (8 Dimensions)

| Dimension | Description |
|-----------|-------------|
| `building` | Creating new functionality, features |
| `fixing` | Resolving errors, bugs, issues |
| `configuring` | Setup, environment, settings |
| `exploring` | Research, learning, discovery |
| `refactoring` | Restructuring without new features |
| `reviewing` | Analysis, code review, audit |
| `testing` | Writing/running tests |
| `documenting` | Writing docs, comments |

### Tool Classification Schema

```python
class ToolClassification(BaseModel):
    tool_name: str
    intent: ToolIntent      # create, modify, search, validate, etc.
    domain: ToolDomain      # filesystem, code, testing, memory, etc.
    confidence: float
    reasoning: str
    activity_signals: dict[str, float]
```

### Enhanced Summary Schema (New Fields)

```python
class DecisionRecord(BaseModel):
    decision: str      # "Used RS256 over HS256"
    rationale: str     # "More secure for production"
    alternatives: list[str] | None

class ErrorResolution(BaseModel):
    error: str         # "ImportError: No module named 'foo'"
    root_cause: str    # "Missing dependency"
    fix: str           # "Added foo==1.2.3"
    verification: str  # "Tests passing"
```

---

## Implementation Plan

### Phase 1: Quick Wins (Recommended First)
- [ ] Add `key_decisions` and `errors_resolved` to `SessionSummarySchema`
- [ ] Update `SUMMARIZATION_PROMPT` to extract these fields
- [ ] Fix template wording ("1 paragraph or less")

### Phase 2: Core Infrastructure
- [ ] Implement `ActivityVector` model (`activity_vector.py`)
- [ ] Implement activity detection from messages
- [ ] Add extraction priority algorithm

### Phase 3: Tool Classification
- [ ] Implement `ToolClassifier` with heuristic matching
- [ ] Add LLM classification for unknown tools
- [ ] Implement caching layer with persistence

### Phase 4: Integration
- [ ] Wire activity detection into `SessionSummarizer`
- [ ] Dynamic prompt generation based on activity
- [ ] Tool classification cache persistence

---

## Files to Create

| File | Purpose |
|------|---------|
| `graphiti_core/session_tracking/activity_vector.py` | ActivityVector model |
| `graphiti_core/session_tracking/tool_classifier.py` | Tool classification system |
| `graphiti_core/session_tracking/extraction_priority.py` | Priority algorithm |
| `graphiti_core/session_tracking/enhanced_summary.py` | EnhancedSessionSummary model |

## Files to Modify

| File | Changes |
|------|---------|
| `graphiti_core/session_tracking/summarizer.py` | Use ActivityVector, dynamic prompts |
| `graphiti_core/session_tracking/prompts/*.md` | Update templates |
| `mcp_server/unified_config.py` | Add summarization config |
| `graphiti.config.schema.json` | Add new config fields |

---

## Configuration Schema Addition

```json
{
  "session_tracking": {
    "summarization": {
      "template": null,
      "type_detection": "auto",
      "extraction_threshold": 0.3,
      "include_decisions": true,
      "include_errors_resolved": true,
      "tool_classification_cache": null
    }
  }
}
```

---

## Key Code Patterns

### Activity Detection

```python
async def detect(self, messages: list[dict]) -> ActivityVector:
    signals = {}

    # Signal 1: User intent keywords
    # Signal 2: Tool usage (via classifier)
    # Signal 3: Error patterns
    # Signal 4: File patterns

    return ActivityVector.from_signals(signals)
```

### Extraction Priority

```python
def compute_extraction_priority(field: str, activity: ActivityVector) -> float:
    affinities = EXTRACTION_AFFINITIES[field]
    priority = sum(
        getattr(activity, dim) * affinity
        for dim, affinity in affinities.items()
    )
    return priority / sum(affinities.values())
```

### Tool Classification Cache Hierarchy

```
1. Exact match (tool_name + params hash) → instant
2. Pattern match (tool_name only) → instant
3. Heuristic (name patterns) → instant, ~0.7 confidence
4. LLM inference → ~1-2s, cached permanently
```

---

## Open Questions for Implementation

1. **Temporal segmentation**: Should we compute activity vectors per-segment for long sessions?

2. **Cache sharing**: Could tool classification cache be shared across machines?

3. **Correction feedback**: How to capture user corrections to improve future summaries?

4. **Threshold tuning**: Is 0.3 optimal for "dominant activities"?

---

## Testing Strategy

### Unit Tests Required

- `test_activity_vector_from_signals()` - Normalization
- `test_activity_vector_dominant_activities()` - Threshold filtering
- `test_tool_classifier_heuristic()` - Name pattern matching
- `test_tool_classifier_caching()` - Cache hit behavior
- `test_extraction_priority_*()` - Priority calculations

### Integration Tests Required

- `test_unified_classifier_session()` - Full session classification
- `test_enhanced_summary_generation()` - End-to-end summarization

---

## Story Creation Guidance

Recommend breaking into stories:

### Story A: Schema Enhancements (Phase 1)
- Add `key_decisions`, `errors_resolved` fields
- Update extraction prompt
- Update templates

### Story B: Activity Vector (Phase 2)
- Implement ActivityVector model
- Activity detection algorithm
- Extraction priority algorithm

### Story C: Tool Classification (Phase 3)
- ToolClassifier implementation
- BashAnalyzer implementation
- Cache layer with persistence

### Story D: Integration (Phase 4)
- Wire into SessionSummarizer
- Dynamic prompt generation
- Configuration schema

---

## Related Documents

| Document | Location |
|----------|----------|
| Full Specification | `.claude/implementation/INTELLIGENT_SESSION_SUMMARIZATION_SPEC_v1.0.md` |
| Design Rationale | `.claude/implementation/INTELLIGENT_SUMMARIZATION_DESIGN_RATIONALE.md` |
| Global Session Tracking Spec | `.claude/implementation/GLOBAL_SESSION_TRACKING_SPEC_v2.0.md` |

---

## Session Metadata

- **Duration**: ~45 minutes
- **Messages**: ~20 exchanges
- **Primary Activity**: Design specification (exploring: 0.7, documenting: 0.8)
- **Outcome**: Design complete, implementation ready
- **MCP Tools Used**: serena (activate, list_dir), Bash, Read, Write
- **Graphiti Status**: Server unavailable (handoff written locally)

---

**Next Agent Action**: Create sprint stories from Phase 1-4 implementation plan above. Recommend starting with Phase 1 (quick wins) for immediate value.
