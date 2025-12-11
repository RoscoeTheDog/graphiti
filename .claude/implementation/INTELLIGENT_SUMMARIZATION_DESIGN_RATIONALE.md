# Intelligent Session Summarization - Design Rationale

**Version**: 1.0.0
**Date**: 2025-12-11
**Sprint**: v2.0.0/global-session-tracking
**Related**: INTELLIGENT_SESSION_SUMMARIZATION_SPEC_v1.0.md

---

## Overview

This document captures the design conversation that led to the Intelligent Session Summarization specification. It serves as institutional memory for why specific design decisions were made.

---

## Conversation Timeline

### Phase 1: Template Specificity

**User Observation**: The default summarization templates (`default-agent-messages.md`, `default-user-messages.md`) were imprecise:

> "default-agent-messages and default-user-messages templates should have 'Summarize this {} response in 1 paragraph or less' to be more specific."

**Action**: Updated template language to include "or less" for brevity control.

---

### Phase 2: Core Problem Statement

**User Questions**:
1. Does `auto_summarize` allow specifying a default template?
2. How does the agent know how to save and structure metadata?
3. How do we capture key session context without useless details?

**Example Scenario Provided**:
> "We have a user eliciting the agent about a feature in a codebase. Through many back and forth elicitations, they come up with a specification. The agent implements the specification in same session. Then the agent runs tests."

**User's Context Requirements**:
| Element | Importance | Rationale |
|---------|------------|-----------|
| User elicitation | Implicit | Can be inferred, not worth storing |
| Feature specification | **High** | Core deliverable |
| How/why specification decided | **High** | Prevents repeated debates |
| Implementation status | **High** | Continuity |
| Implementation content | Low | Too granular |
| Test status | **High** | Verification |
| Test parameters | **High** | Reproducibility |
| Internal tool calls | Low | Noise (unless debugging) |

**Key Insight**: What's "noise" depends on session context. Debugging sessions need tool call details; implementation sessions don't.

---

### Phase 3: Initial Solution - Discrete Classification

**First Proposal**: Discrete `SessionType` enum:

```python
class SessionType(Enum):
    IMPLEMENTATION = "implementation"
    DEBUGGING = "debugging"
    EXPLORATION = "exploration"
    CONFIGURATION = "configuration"
    REVIEW = "review"
    MIXED = "mixed"
```

With type-specific extraction priorities:

```python
EXTRACTION_PRIORITIES = {
    SessionType.IMPLEMENTATION: {
        "high": ["completed_tasks", "files_modified", "key_decisions"],
        "low": ["tool_calls", "errors_encountered"],
    },
    SessionType.DEBUGGING: {
        "high": ["errors_resolved", "root_cause", "verification_steps"],
        "medium": ["tool_calls"],  # Important for debugging!
    },
}
```

**New Schema Fields Proposed**:
- `key_decisions: list[DecisionRecord]` - Prevents repeated debates
- `errors_resolved: list[ErrorResolution]` - Critical for debugging continuity

---

### Phase 4: User Critique - False Dichotomies

**User Challenge**:
> "Can we make the classification system for the topics any more comprehensive in scope so there is not misidentification between things like 'DEBUGGING' and 'CONFIGURATION'? What if there are two topics that are interwoven like a bug that was caused by changing the configuration, and the agent fixes the configuration to resolve the bug during debugging process?"

**Problem Identified**: Discrete categories create:
1. False dichotomies (A or B, not A and B)
2. Edge case explosion (would need DEBUG_CONFIG, IMPLEMENT_TEST, etc.)
3. Misclassification cascades (wrong type → wrong extraction → bad summary)

---

### Phase 5: Solution - Multi-Dimensional Activity Vector

**Revised Proposal**: Replace discrete enum with continuous vector:

```python
class ActivityVector(BaseModel):
    building: float = 0.0      # 0.0-1.0
    fixing: float = 0.0
    configuring: float = 0.0
    exploring: float = 0.0
    refactoring: float = 0.0
    reviewing: float = 0.0
    testing: float = 0.0
    documenting: float = 0.0
```

**Config Bug Example**:
```python
ActivityVector(
    building=0.1,      # Minor
    fixing=0.8,        # HIGH: primary goal
    configuring=0.7,   # HIGH: root cause and fix
    exploring=0.4,     # MEDIUM: investigation
    testing=0.5,       # MEDIUM: verification
)
# dominant_activities → ['fixing', 'configuring', 'testing', 'exploring']
```

**Benefits**:
- No false dichotomies (80% fixing + 70% configuring = valid)
- Weighted extraction (priority = weighted sum of affinities)
- Temporal flexibility (can compute per-segment if needed)
- Graceful degradation (imperfect detection still produces reasonable results)

---

### Phase 6: User Critique - Hard-Coded Tool Mappings

**User Challenge**:
> "What if the tooling systems are hard-coded in python yet the LLM may use MCP server extensions that are unknown in quantity? We can't possibly hard-code all the tool calls. Plus, there could be other invocations of tools called in a bash environment which are not strictly bash-commands, they could be downloaded/installed repositories, softwares, etc."

**Problems Identified**:
1. MCP server explosion (serena, context7, gptr-mcp, custom servers)
2. Bash command diversity (any installed CLI, scripts, pip packages)
3. Maintenance burden (constant updates for new tools)
4. Zero-shot failure (unknown tools contribute no signal)

---

### Phase 7: Solution - LLM-Inferred Tool Classification

**Final Proposal**: Multi-level classification system:

```
Tool Call → Classification Pipeline:

Level 1: Exact Cache (tool_name + params hash)
    ↓ miss
Level 2: Pattern Cache (tool_name only)
    ↓ miss
Level 3: Heuristic (name pattern matching)
    ↓ uncertain (confidence < 0.7)
Level 4: LLM Inference (expensive, cached after)
```

**Classification Schema**:
```python
class ToolClassification(BaseModel):
    tool_name: str
    intent: ToolIntent      # create, modify, search, validate, etc.
    domain: ToolDomain      # filesystem, code, testing, memory, etc.
    confidence: float
    reasoning: str
    activity_signals: dict[str, float]
```

**Bash-Specific Analysis**:
```python
class BashCommandClassification(BaseModel):
    raw_command: str
    base_command: str       # "pytest", "npm", "git"
    subcommand: str | None  # "install", "commit"
    flags: list[str]
    targets: list[str]
    intent: ToolIntent
    domain: ToolDomain
    activity_signals: dict[str, float]
```

**Cost Analysis**:
| Scenario | LLM Calls |
|----------|-----------|
| Known tools (Read, Write, Edit) | 0 (heuristic) |
| Known bash (git, npm, pytest) | 0 (heuristic) |
| New MCP server | 1 per unique tool |
| Unknown CLI | 1 per unique command |
| Repeat sessions | ~0 (cached) |

---

## Key Design Decisions

### Decision 1: Continuous vs Discrete Classification

**Question**: Use discrete `SessionType` or continuous `ActivityVector`?

**Decision**: ActivityVector with 8 continuous dimensions

**Rationale**:
- Real sessions blend multiple activities
- Weighted extraction works better than categorical mapping
- Handles edge cases gracefully (config-caused bug = high fixing + high configuring)
- Extensible without combinatorial explosion

### Decision 2: LLM vs Hard-Coded Tool Classification

**Question**: Pre-define tool mappings or infer at runtime?

**Decision**: LLM inference with multi-level caching

**Rationale**:
- MCP ecosystem is open-ended (can't predict all servers)
- Bash commands include arbitrary installed software
- Cache makes repeated use free
- Heuristics handle common cases without LLM

### Decision 3: Extraction Priority Algorithm

**Question**: How to decide which fields to extract?

**Decision**: Affinity-weighted priority scores

**Rationale**:
- Each field has "affinity" to activity dimensions
- Priority = weighted sum of (activity_intensity × field_affinity)
- Threshold filtering removes irrelevant fields
- Dynamic prompts based on calculated priorities

### Decision 4: Schema Enhancements

**Question**: What new fields to add?

**Decision**:
- `key_decisions: list[DecisionRecord]` with structured rationale
- `errors_resolved: list[ErrorResolution]` with root cause + fix + verification
- `config_changes: list[ConfigChange]` with before/after values
- `test_results: TestSummary` with pass/fail/coverage

**Rationale**:
- `key_decisions` prevents next agent from re-debating settled choices
- `errors_resolved` provides debugging continuity
- Both identified as critical by user for session memory

---

## Implementation Priority

Based on conversation, recommended implementation order:

### Phase 1: Quick Wins (Low effort, high value)
1. Add `key_decisions` and `errors_resolved` to `SessionSummarySchema`
2. Update `SUMMARIZATION_PROMPT` to extract these fields
3. Fix template wording ("1 paragraph or less")

### Phase 2: Core Infrastructure
1. Implement `ActivityVector` model
2. Implement activity detection from messages
3. Add extraction priority algorithm

### Phase 3: Tool Classification
1. Implement `ToolClassifier` with heuristic matching
2. Add LLM classification for unknown tools
3. Implement caching layer

### Phase 4: Integration
1. Wire activity detection into `SessionSummarizer`
2. Dynamic prompt generation based on activity
3. Tool classification cache persistence

---

## Open Questions

These may require future refinement:

1. **Temporal segmentation**: Should we compute activity vectors per-segment for long sessions with multiple phases?

2. **Cross-session learning**: Could the tool classification cache be shared across machines/users?

3. **Correction feedback**: How do we capture when users correct agent mistakes to improve future summaries?

4. **Activity threshold tuning**: Is 0.3 the right threshold for "dominant activities"?

---

## Files Created

| File | Purpose |
|------|---------|
| `INTELLIGENT_SESSION_SUMMARIZATION_SPEC_v1.0.md` | Full specification |
| `INTELLIGENT_SUMMARIZATION_DESIGN_RATIONALE.md` | This file - design rationale |

---

## Related Context

- **Sprint**: v2.0.0/global-session-tracking
- **Related Spec**: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md
- **Branch**: sprint/v2.0.0/global-session-tracking

---

**Last Updated**: 2025-12-11
