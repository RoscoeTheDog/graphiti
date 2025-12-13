# Session 015: Turn-Based Indexing with Single-Pass LLM Research

**Status**: ACTIVE
**Created**: 2025-12-11 23:53
**Objective**: Pivot from session-based hybrid close to turn-based indexing with single-pass LLM preprocessing

---

## Completed

- Verified previous sprint was cleaned up (no queue.json, no active sprint)
- Read SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md fully (1300+ lines)
- Began CREATE_SPRINT workflow for 17-story hybrid close implementation
- Identified over-engineering: removed config stories (ST-H7, ST-H8) - hybrid close is architecture, not configurable
- Updated spec to reflect non-configurable architecture (Section 8 rewritten)
- **Pivoted approach**: User identified fundamental issue - session-based indexing is wrong atomic unit
- Discussed turn-based indexing (user request → agent response as atomic unit)
- Discussed single-pass LLM processing (inject preprocessing into Graphiti's extraction, not separate pass)
- Created new spec: TURN_BASED_INDEXING_SPEC_v0.1.md with research questions

---

## Blocked

- R2 (Critical Path): Need to investigate Graphiti's LLM injection points before proceeding
- Cannot finalize sprint stories until feasibility research complete

---

## Next Steps

- **R2 Research (Critical)**: Analyze Graphiti source for LLM injection points
  - Look at `add_episode()` implementation
  - Find entity extraction prompts
  - Determine if prompts are configurable or hardcoded
  - Assess: upstream PR vs wrapper approach
- **R1 Research**: Investigate turn boundary detection mechanisms
  - JSONL structure and message delimiters
  - File watcher event patterns
  - Debounce strategy for streaming outputs
- **R4 Research**: Validate token economics
  - Measure baseline (current two-pass approach)
  - Estimate single-pass savings
- After feasibility confirmed: Create new sprint with revised stories

---

## Decisions Made

- **Hybrid close is architectural, not configurable**: Removed config schema stories (old ST-H7, ST-H8). The four-layer approach is the design - adding toggles would just add complexity without value.
- **Session-based indexing is wrong abstraction**: Natural unit is turn-pair (user request → agent response), not entire sessions. This eliminates close detection complexity entirely.
- **Single-pass LLM is key optimization**: Instead of summarize-then-extract (2 passes), inject preprocessing instructions into Graphiti's extraction prompts (1 pass). Estimated 30-40% token savings.
- **Research before implementation**: Need to validate Graphiti injection feasibility before creating sprint stories.

---

## Errors Resolved

- None this session (research/design focus)

---

## Context

**Files Modified/Created**:
- `.claude/implementation/SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md` - Updated Section 8 (non-configurable), Section 9.2, 11.1, 11.2, 13.9, Appendix B
- `.claude/implementation/TURN_BASED_INDEXING_SPEC_v0.1.md` - NEW: Research spec for turn-based approach

**Documentation Referenced**:
- SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md (full read)
- Previous handoff s014

---

## Key Research Questions (from new spec)

| ID | Question | Priority |
|----|----------|----------|
| R1 | How to detect turn boundary without waiting for next user message? | High |
| R2 | Can we inject preprocessing into Graphiti's LLM calls? | **Critical** |
| R3 | What should preprocessor module interface look like? | Medium |
| R4 | What are actual token savings? | Medium |
| R5 | Can turn-based coexist with existing session-based data? | Low |

**Critical Path**: R2 must be answered first. If Graphiti prompts aren't injectable, need alternative approach.

---

**Session Duration**: ~1 hour
**Token Usage**: ~120k/200k (approaching limit, created handoff)
