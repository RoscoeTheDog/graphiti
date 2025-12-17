# Session Handoff: Temporal BMAD Orchestration Design

**Session ID**: s019
**Date**: 2025-12-15
**Status**: COMPLETE - All Design Questions Answered (Q1-Q8)
**Branch**: sprint/daemon-venv-isolation

---

## Session Objective

Design the integration architecture for Temporal workflow orchestration with BMAD agents, using Graphiti for cross-session context persistence. The key challenge is preventing context window exhaustion while maintaining workflow state.

---

## Decisions Made This Session

### Q1: Where should structured extraction happen in filter pipeline?

**Decision**: **Option C - Dual-Track Architecture**

| Component | Ingestion Path | Purpose |
|-----------|----------------|---------|
| Temporal Orchestrator | Direct filesystem writes (excluded from auto-tracking) | Structured checkpoints, crash recovery |
| BMAD Agents | Graphiti auto-tracking with summarization | Context memory for agent continuity |

**Implementation**: Add `excluded_paths: List[str]` to `SessionTrackingConfig`.

**Sprint Created**: Story 1 - "Session Tracking Excluded Paths" in `graphiti/.claude/sprint/`

---

### Q2: Should checkpoint data bypass summarization?

**Decision**: **N/A - Resolved by Q1**

Checkpoints don't go through auto-tracking at all. They are written directly to filesystem.

**Key Principle**: Graphiti is an enhancement, not a dependency. Orchestrator must function fully with filesystem-only storage.

---

### Q3: How should orchestrator query for checkpoints?

**Decision**: **Filesystem-only (no Graphiti integration for checkpoints)**

**Primary**: Read `latest.json` from `.temporal/checkpoints/{workflow_id}/`
**NO Graphiti**: Checkpoints are NOT written to Graphiti at all. Since Temporal server is excluded from auto-tracking, we don't want checkpoint data in the semantic graph either.

**Key Clarification**: Graphiti is for BMAD agent context memory only. Checkpoints are purely for orchestrator crash recovery on the filesystem.

**Checkpoint Directory Structure**:
```
{temporal-server-project}/
├── .temporal/
│   └── checkpoints/
│       └── {workflow_id}/
│           ├── 001.json          # Checkpoint sequence 1
│           ├── 002.json          # Checkpoint sequence 2
│           ├── latest.json       # Current state (atomic write)
│           └── metadata.json     # Workflow metadata
```

---

## Files Created/Modified

### Created
- `.claude/sprint/stories/1-session-tracking-excluded-paths.md` - Sprint story for Graphiti feature
- `.claude/sprint/.queue.json` - Fresh sprint queue with Story 1

### Modified
- `.claude/research/TEMPORAL-BMAD-ORCHESTRATION-DESIGN.md` - Updated to v0.3.1-draft with decisions (filesystem-only checkpoints)

---

## All Questions Answered

### Q4: Should JSONL tracking use different configs for orchestrator vs agents?
**Decision**: **Option C - Defer to Agent with Metadata**
- Uniform filtering across all BMAD agent types
- Agents emit structured metadata tags (e.g., `role: qa`, `role: dev`)
- Graphiti indexes metadata for filtered semantic queries

### Q5-Q6: Namespace Routing
**Decision**: **Option A - PWD-based namespace routing**
- BMAD agents run in target project directories → automatic correct namespace
- `excluded_paths` handles Temporal server isolation
- No explicit override needed

### Q7: Should tools remain fully agnostic?
**Decision**: **Option A - Fully Agnostic**
- Graphiti stays generic; no Temporal/BMAD-specific concepts
- `excluded_paths` is a generic feature usable by any project

### Q8: What happens to orphaned checkpoints?
**Decision**: **Option C - Workflow-aware with fallback**
- On success: delete/archive checkpoints
- On failure: keep for debugging
- Orphaned: age-based cleanup (30 days)

---

## Context for Next Session

### Sprint Queue (Graphiti)
- **Story 1**: Session Tracking Excluded Paths (1.d → 1.i → 1.t)
- **Status**: Ready for execution, holding pending remaining design questions

### Design Spec
- **File**: `.claude/research/TEMPORAL-BMAD-ORCHESTRATION-DESIGN.md`
- **Version**: 0.4.0-draft
- **Contains**: All decisions Q1-Q8, CheckpointManager, CheckpointRetentionPolicy, revised architecture

### User's Stated Goals
1. Create Temporal server for orchestrating BMAD agent workflows
2. Parent orchestrator delegates to BMAD agents
3. Agents return structured metadata with confidence scores
4. Block for human intervention on low confidence or core design changes
5. Automate everything else

### Technical Context
- Orchestrator: Python using forked Claude Code SDK
- Checkpoints: **Filesystem-ONLY** (`.temporal/checkpoints/`) - NO Graphiti integration
- Graphiti: Enhancement for BMAD agent context memory ONLY, not for checkpoints
- BMAD Agents: Use Graphiti auto-tracking for context memory (in target project dirs)
- Temporal Server: Excluded from Graphiti auto-tracking via `excluded_paths`

---

## Recommended Next Steps

1. ~~**Finish remaining questions** (Q4-Q8)~~ ✅ COMPLETE
2. **Execute Sprint Story 1** - Add `excluded_paths` to Graphiti
3. **Begin Temporal server implementation** in separate project

---

## Session Metrics

- **Duration**: ~3 hours (continued from previous)
- **Decisions Made**: 8 (Q1-Q8 all complete)
- **Sprint Stories Created**: 1
- **Design Spec Updated**: Yes (v0.4.0-draft)

---

**END OF HANDOFF**
