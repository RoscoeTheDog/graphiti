# Turn-Based Indexing with Single-Pass LLM Processing - Specification v0.1

**Version**: 0.1.0 (Draft)
**Status**: Research / Feasibility
**Authors**: Human + Claude Agent
**Date**: 2025-12-11
**Supersedes**: SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md (pending validation)

---

## Executive Summary

This specification proposes a fundamental shift from session-based indexing to **turn-based indexing** with **single-pass LLM processing**. The goal is to eliminate session close detection complexity while reducing token overhead and improving graph relationship quality.

### Key Insights

1. **Natural atomic unit**: User request → Agent response (turn-pair), not sessions
2. **Eliminate close detection**: Turns self-close when agent response completes
3. **Single-pass LLM**: Inject preprocessing into Graphiti's extraction pass, not separate
4. **Token efficiency**: Read input once, generate output once

---

## Problem Statement

### Current Architecture Issues

**Session-Based Indexing**:
```
Session Start → [N turns] → Detect Close → Summarize → Index
```

Problems:
- Requires complex close detection (explicit signal, lazy indexing, timeout fallback)
- Late indexing = stale context for subsequent queries
- Coarse retrieval (one episode per session)
- LLM summarization loses granular relationships

**Two-Pass LLM Processing**:
```
Raw Content → [LLM #1: Summarize] → Cleaned → [LLM #2: Extract] → Graph
```

Problems:
- Input tokens read twice
- Two output generations
- Higher latency (sequential LLM calls)
- ~40-60% token overhead vs single-pass

---

## Proposed Architecture

### Turn-Based Indexing

```
User Request
    ↓
Agent Response (with tool calls, etc.)
    ↓
Turn Complete (detected automatically)
    ↓
Filter noise programmatically (no LLM)
    ↓
Index turn-pair to Graphiti
    ↓
Repeat
```

**Benefits**:
- No session close detection needed
- Real-time indexing (context immediately available)
- Granular retrieval (specific exchanges, not whole sessions)
- Natural relationship building between turns

### Single-Pass LLM Processing

```
Raw Turn Content + Preprocessing Template
    ↓
[Single LLM Call: Clean + Extract Entities + Build Relations]
    ↓
Graph Updates
```

**Benefits**:
- Input tokens read once
- Single output generation
- ~30-40% token savings
- Lower latency

---

## Research Questions

### R1: Turn Boundary Detection

**Question**: How do we reliably detect "turn complete" without waiting for next user message?

**Current understanding**:
- JSONL format has message boundaries
- File watcher sees write events
- Last assistant message before next human = turn complete (retrospective)
- Real-time: Need signal that agent stopped outputting

**To investigate**:
- [ ] JSONL structure and message delimiters
- [ ] File watcher event patterns during agent response
- [ ] Claude Code hooks that fire on response complete
- [ ] Debounce strategy for streaming outputs

### R2: Graphiti LLM Injection Points

**Question**: Can we inject preprocessing instructions into Graphiti's existing LLM calls?

**Hypothesis**: Graphiti's entity/relationship extraction uses LLM prompts. We can modify these prompts to include preprocessing instructions.

**To investigate**:
- [ ] Graphiti's `add_episode()` implementation
- [ ] LLM prompt templates in graphiti_core
- [ ] Entity extraction pipeline
- [ ] Relationship inference pipeline
- [ ] Whether prompts are configurable or hardcoded

### R3: Preprocessor Module Design

**Question**: What should the preprocessor interface look like?

**Draft interface**:
```python
@dataclass
class Preprocessor:
    name: str
    instructions: str  # Injected into LLM prompt
    noise_patterns: list[str] | None = None
    focus_areas: list[str] | None = None
```

**To investigate**:
- [ ] What preprocessing instructions improve extraction quality?
- [ ] How to handle different content types (code, errors, tool outputs)?
- [ ] Template format that works across LLM providers

### R4: Token Economics Validation

**Question**: What are the actual token savings?

**To measure**:
- [ ] Baseline: Current two-pass approach tokens per session
- [ ] Proposed: Single-pass approach tokens per turn
- [ ] Break-even point: How many turns before single-pass wins?
- [ ] Quality comparison: Retrieval accuracy before/after

### R5: Backward Compatibility

**Question**: Can turn-based indexing coexist with existing session-based data?

**Considerations**:
- Existing episodes in graph (session-granularity)
- New episodes (turn-granularity)
- Query behavior across both
- Migration path if needed

---

## Preliminary Design

### Turn Detection (Draft)

```python
class TurnDetector:
    """Detect complete turn-pairs from JSONL stream."""

    def __init__(self, debounce_ms: int = 2000):
        self.debounce_ms = debounce_ms
        self.pending_turn: Turn | None = None
        self.last_write_time: datetime | None = None

    def on_file_change(self, file_path: Path) -> Turn | None:
        """
        Called on file modification.
        Returns complete Turn if detected, None if still accumulating.
        """
        # Parse latest messages from JSONL
        # Detect if we have complete user→assistant pair
        # Debounce to handle streaming writes
        pass

    def on_debounce_timeout(self) -> Turn | None:
        """
        Called when no writes for debounce_ms.
        Flush pending turn if exists.
        """
        pass
```

### Preprocessor Injection (Draft)

```python
# In Graphiti's extraction pipeline (conceptual)
async def extract_with_preprocessing(
    content: str,
    preprocessor: Preprocessor | None = None
) -> ExtractionResult:

    if preprocessor:
        prompt = f"""
{preprocessor.instructions}

---
RAW CONTENT:
{content}
---

After applying the cleaning instructions above, extract:
1. Entities (people, concepts, tools, files, etc.)
2. Relationships between entities
3. Temporal markers

Output format: ...
"""
    else:
        prompt = DEFAULT_EXTRACTION_PROMPT.format(content=content)

    return await llm.generate(prompt, output_schema=ExtractionResult)
```

### Default Session Turn Preprocessor (Draft)

```python
SESSION_TURN_PREPROCESSOR = Preprocessor(
    name="session_turn",
    instructions="""
You are preprocessing an agent conversation turn before entity extraction.

CLEANING RULES:
1. IGNORE completely:
   - Tool call JSON blobs (function names, parameters)
   - Raw file contents dumped by tools
   - Stack traces and error dumps (keep only error message)
   - System/metadata messages

2. SUMMARIZE to semantic meaning:
   - "Read file X, found Y" → "Discovered Y in file X"
   - "Ran command, got output..." → "Executed command, result was..."
   - Long code blocks → "Implemented [description]"

3. PRESERVE fully:
   - User intent and requests
   - Agent decisions and reasoning
   - Outcomes and conclusions
   - Entity names (files, functions, concepts)

4. FOCUS extraction on:
   - What the user wanted
   - What the agent did
   - What was learned/decided
   - Relationships between concepts
""",
    noise_patterns=[
        r"<tool_call>.*?</tool_call>",
        r"```json\n\{.*?\}\n```",
        r"Traceback \(most recent call last\):.*?(?=\n\n)",
    ],
    focus_areas=[
        "user_intent",
        "agent_decisions",
        "outcomes",
        "learned_concepts",
    ]
)
```

---

## Implementation Phases (Tentative)

### Phase 1: Feasibility Research
- [ ] R1: Investigate turn boundary detection
- [ ] R2: Analyze Graphiti LLM injection points
- [ ] Document findings in this spec

### Phase 2: Prototype
- [ ] Implement basic turn detector
- [ ] Test preprocessor injection in Graphiti (fork or PR)
- [ ] Measure token savings

### Phase 3: Integration
- [ ] Replace session-based indexing with turn-based
- [ ] Add preprocessor configuration
- [ ] Update MCP tools

### Phase 4: Optimization
- [ ] Tune preprocessor instructions
- [ ] Add content-type-specific preprocessors
- [ ] Performance benchmarking

---

## Comparison: Session vs Turn Approach

| Aspect | Session-Based (Current) | Turn-Based (Proposed) |
|--------|------------------------|----------------------|
| Atomic unit | Entire session | Single turn-pair |
| Close detection | Complex (4-layer hybrid) | Automatic (turn boundary) |
| Indexing latency | End of session | Real-time per turn |
| LLM passes | 2 (summarize + extract) | 1 (combined) |
| Token overhead | ~40-60% higher | Baseline |
| Retrieval granularity | Coarse (session) | Fine (turn) |
| Implementation complexity | High (state machine, hooks) | Lower (stream processing) |

---

## Open Questions

1. **Graphiti upstream**: Should this be a PR to Graphiti core, or a wrapper?
2. **Existing data**: How to handle mixed granularity in graph?
3. **Turn grouping**: Should related turns be linked? How?
4. **Partial turns**: What if agent crashes mid-response?
5. **Multi-agent**: How to handle concurrent agents in same project?

---

## Next Steps

1. **Research R2 first**: Graphiti LLM injection is the critical path
2. Create research notes as sub-documents
3. Prototype preprocessor injection
4. Validate token savings hypothesis
5. Decide: upstream PR vs wrapper approach

---

## References

- SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md (previous approach)
- Graphiti source: https://github.com/getzep/graphiti
- INTELLIGENT_SESSION_SUMMARIZATION_SPEC_v1.0.md (existing summarization)

---

**Status**: Draft - Awaiting feasibility research

*This spec will be updated as research progresses.*
