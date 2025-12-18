# Temporal BMAD Orchestration Design Specification

**Version**: 0.4.0-draft
**Date**: 2025-12-15
**Status**: Design Phase - All Questions Answered (Q1-Q8)
**Related Projects**:
- `temporal-bmad-server` - Temporal workflow orchestrator (forked Claude Code SDK)
- `graphiti` - Knowledge graph with JSONL session tracking

---

## Executive Summary

This document captures the design state for integrating Temporal workflow orchestration with BMAD agents, using Graphiti for cross-session context persistence. The core challenge is preventing context window exhaustion in the orchestrator while maintaining workflow state across sessions.

**Key Design Direction (Updated)**: Dual-Track Architecture with filesystem-first checkpoints.

- **Temporal Orchestrator**: Excluded from Graphiti auto-tracking, writes checkpoints directly to filesystem
- **BMAD Agents**: Use Graphiti auto-tracking with summarization for context memory
- **Graphiti**: Optional enhancement for semantic queries, not a dependency

---

## Design Decisions Made

### Q1: Where should structured extraction happen in filter pipeline?

**Decision**: **Option C - Dual-Track Architecture (Not in filter pipeline)**

Instead of modifying the Graphiti filter pipeline, we separate the ingestion paths:

| Component | Ingestion Path | Purpose |
|-----------|----------------|---------|
| Temporal Orchestrator | **Direct filesystem writes** (excluded from auto-tracking) | Structured checkpoints, crash recovery |
| BMAD Agents | **Graphiti auto-tracking** with summarization | Context memory for agent continuity |

**Implementation**: Add `excluded_paths: List[str]` to `SessionTrackingConfig` in Graphiti. The Temporal server's project path will be excluded from auto-tracking.

**Sprint Created**: Story 1 in `graphiti/.claude/sprint/` - "Session Tracking Excluded Paths"

**Rationale**:
1. Single ingestion path per component (no conflicts)
2. Checkpoints are always structured (no LLM variance)
3. Auto-tracking does what it was designed for (agent context)
4. Graphiti remains tool-agnostic (doesn't know about Temporal)

---

### Q2: Should checkpoint data bypass summarization?

**Decision**: **N/A - Checkpoints don't go through Graphiti at all**

With the Dual-Track decision (Q1), orchestrator checkpoints are written directly to the filesystem only. No Graphiti integration for checkpoints.

**Checkpoint Storage Strategy**:

| Storage | Purpose | Availability |
|---------|---------|--------------|
| **Filesystem (Only)** | Crash recovery, authoritative state | Always available |
| ~~Graphiti~~ | ~~Semantic queries~~ | **NOT USED for checkpoints** |

**Key Principle**: Graphiti is an enhancement for BMAD agent context memory, not for orchestrator checkpoints. The Temporal server path is excluded from Graphiti auto-tracking, so we don't write checkpoints to Graphiti either. This avoids noise/conflicts in the semantic graph.

---

### Q3: How should orchestrator query for checkpoints?

**Decision**: **Filesystem-only (no Graphiti integration for checkpoints)**

Since the Temporal server path is excluded from Graphiti auto-tracking (Q1 decision), checkpoints should NOT be written to Graphiti at all. This prevents noise/conflicts in the semantic graph and keeps the checkpoint system simple and reliable.

**Query Path (Filesystem)**:
```python
def get_latest_checkpoint(workflow_id: str) -> Optional[OrchestratorCheckpoint]:
    checkpoint_dir = Path(f".temporal/checkpoints/{workflow_id}")
    latest = checkpoint_dir / "latest.json"
    if latest.exists():
        return OrchestratorCheckpoint.from_json(latest.read_text())
    return None
```

**Checkpoint Directory Structure**:
```
{temporal-server-project}/
├── .temporal/
│   └── checkpoints/
│       └── {workflow_id}/
│           ├── 001.json          # Checkpoint sequence 1
│           ├── 002.json          # Checkpoint sequence 2
│           ├── latest.json       # Copy of most recent (atomic write)
│           └── metadata.json     # Workflow metadata
```

**Query Scenarios**:

| Scenario | Source | Method |
|----------|--------|--------|
| Crash recovery | Filesystem | Read `latest.json` from checkpoint dir |
| Resume workflow | Filesystem | Same as crash recovery |
| Checkpoint history | Filesystem | Read `{NNN}.json` files in sequence |
| Cross-workflow analysis | Filesystem | Glob across workflow dirs (manual) |

**Key Principle**: Checkpoints are purely for orchestrator crash recovery. Cross-workflow semantic queries should use BMAD agent context (which IS tracked by Graphiti), not checkpoint data.

---

## Problem Statement

### Context Accumulation Challenge

When using Claude Code's `Task()` tool to delegate to BMAD agents in batch sequences:

1. **Task summaries accumulate** - Even minimal metadata responses fill the context window
2. **Auto-compaction triggers** - Session context is lost, leading to unpredictable behavior
3. **Cross-session state loss** - New sessions start fresh without workflow context

### Original Vision

The `graphiti` enhancement project aims to:
- Monitor JSONL conversation logs automatically
- Summarize user/agent call/response patterns
- Upload summaries to the knowledge graph
- Enable cross-session and cross-project context retrieval via semantic/temporal search

### Orchestration Requirements

For Temporal BMAD automation:
1. **Fire-and-forget epic execution** - Start script, walk away, come back to completed work
2. **Human-in-the-loop for strategic decisions** - Block on low confidence or core design changes
3. **Crash recovery** - Resume from exact state after failures
4. **Project isolation** - Temporal server works on multiple projects without cross-contamination

---

## Revised Architecture (Post-Decisions)

### Component Hierarchy

```
TEMPORAL SERVER (Python - Forked Claude Code SDK)
├── Temporal Workflows (EpicWorkflow, DevQALoopWorkflow)
├── Temporal Activities (invoke_bmad_agent, etc.)
├── Checkpoint Manager (filesystem-only, NO Graphiti)  ← UPDATED
├── Session Boundary Manager (prevents auto-compaction)
└── JSONL Logger (for BMAD agents, NOT orchestrator)

GRAPHITI AUTO-TRACKING (Reads from BMAD agent JSONL only)
├── Conversation Monitor (watches JSONL files)
├── Path Exclusion Filter (skips Temporal server path)  ← NEW
├── Filter Pipeline (configurable per message type)
├── Graph Upload (episodes to Neo4j)
└── Namespace Routing (project namespaces)

BMAD AGENTS (Per-Project, Delegated)
├── SM Agent (Sprint Management)
├── Dev Agent (Implementation)
├── QA Agent (Quality Assurance)
├── PO Agent (Product Owner)
└── Architect Agent
```

### Revised Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ TEMPORAL ORCHESTRATOR                                            │
│                                                                 │
│ 1. Read latest checkpoint from filesystem                       │
│ 2. Determine next agent action                                  │
│ 3. Delegate to BMAD agent (agent logs to JSONL in target proj) │
│ 4. Agent returns response                                       │
│ 5. Write checkpoint to filesystem ONLY (no Graphiti)            │
│ 6. Check session boundary → continue-as-new if needed          │
│ 7. Repeat until epic complete or human intervention            │
└─────────────────────────────────────────────────────────────────┘
        │                              │
        │ Checkpoint                   │ Agent JSONL (in target project)
        ▼                              ▼
┌───────────────────┐    ┌─────────────────────────────────────────┐
│ FILESYSTEM        │    │ GRAPHITI AUTO-TRACKING                   │
│ .temporal/        │    │                                         │
│   checkpoints/    │    │ - Path exclusion: Temporal server       │
│     {workflow}/   │    │ - Monitors: BMAD agent JSONL only       │
│       latest.json │    │ - Summarizes agent work for context     │
│                   │    │ - NO checkpoint data in Graphiti        │
│ (NO GRAPHITI)     │    │                                         │
└───────────────────┘    └─────────────────────────────────────────┘
```

---

## Identity & Namespace Architecture

### UID Generation

```python
@dataclass
class WorkflowIdentity:
    """Unique identity for orchestration workflow"""
    workflow_id: str           # Temporal workflow ID
    timestamp: int             # Unix timestamp at workflow start
    hostname: str              # Machine running workflow

    @property
    def workflow_uid(self) -> str:
        return f"temporal__{self.workflow_id}__{self.timestamp}"

    @property
    def graphiti_group_id(self) -> str:
        return f"temporal__{self.workflow_id}"

@dataclass
class AgentIdentity:
    """Unique identity for delegated agent"""
    workflow_uid: str          # Parent workflow
    agent_type: str            # "dev", "qa", "sm", etc.
    sequence_num: int          # N-th agent of this type

    @property
    def agent_uid(self) -> str:
        return f"{self.workflow_uid}__agent__{self.agent_type}__{self.sequence_num:04d}"

@dataclass
class ProjectIdentity:
    """Unique identity for target project"""
    project_path: str          # Absolute path
    hostname: str              # Machine where project lives

    @property
    def project_hash(self) -> str:
        normalized = self.project_path.replace("\\", "/").lower()
        return sha256(normalized.encode()).hexdigest()[:8]

    @property
    def graphiti_group_id(self) -> str:
        return f"project__{self.project_hash}"
```

### Namespace Hierarchy

```
FILESYSTEM (Temporal Server - Checkpoints Only):
├── .temporal/
│   └── checkpoints/
│       └── {workflow_id}/
│           ├── {sequence}.json      # Checkpoint history
│           ├── latest.json          # Current state
│           └── metadata.json        # Workflow info

GRAPHITI (BMAD Agents - Context Memory Only):
├── project__{project_hash}/
│   ├── work/{agent_type}/{story_id}           # Agent work (summarized)
│   ├── decision/{agent_type}/{story_id}/{key} # Agent decisions
│   └── qa/{story_id}/gate                     # QA gate decisions

# NOTE: NO Graphiti namespace for Temporal checkpoints
# Temporal server path is excluded from auto-tracking
# Checkpoints are filesystem-only
```

---

## Checkpoint Architecture

### OrchestratorCheckpoint Schema

```python
@dataclass
class OrchestratorCheckpoint:
    """Minimal state for orchestrator resume - ~170 tokens"""

    # Identity
    workflow_uid: str
    checkpoint_id: str
    checkpoint_sequence: int

    # Workflow state
    epic_id: str
    current_phase: str  # "elicitation", "sprint_planning", "dev_qa_loop", "complete"
    current_story_id: Optional[str]

    # Progress tracking (IDs only, not content)
    stories_completed: List[str]  # ["story-2.1", "story-2.2"]
    stories_pending: List[str]

    # Loop counters
    dev_qa_iterations: Dict[str, int]  # {"story-2.3": 2}
    sm_po_iterations: int

    # Human intervention queue
    blocked_decisions: List[Dict[str, Any]]

    # Retry state
    retry_count: int
    last_failed_agent: Optional[str]

    # Directives (persistent rules)
    confidence_threshold: float
    human_escalation_triggers: List[str]

    # Timestamps
    created_at: str
    updated_at: str

    def to_json(self) -> str:
        """Serialize for filesystem storage"""
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "OrchestratorCheckpoint":
        """Deserialize from filesystem"""
        return cls(**json.loads(json_str))
```

### Checkpoint Manager

```python
class CheckpointManager:
    """Filesystem-only checkpoint management (no Graphiti integration)

    Design Decision: Checkpoints are stored exclusively on the filesystem.
    Since the Temporal server path is excluded from Graphiti auto-tracking,
    we avoid any Graphiti writes for checkpoints to prevent noise/conflicts
    in the semantic/temporal graph search.

    BMAD agents write to their own JSONL logs (in target project directories),
    which ARE tracked by Graphiti for context memory. Checkpoints are purely
    for orchestrator crash recovery.
    """

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir

    def save_checkpoint(
        self,
        workflow_id: str,
        checkpoint: OrchestratorCheckpoint
    ) -> None:
        """Save checkpoint to filesystem only"""
        workflow_dir = self.checkpoint_dir / workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=True)

        # Sequence file for history
        sequence_file = workflow_dir / f"{checkpoint.checkpoint_sequence:03d}.json"
        sequence_file.write_text(checkpoint.to_json())

        # latest.json for fast crash recovery (atomic write via temp file)
        latest_file = workflow_dir / "latest.json"
        temp_file = workflow_dir / "latest.json.tmp"
        temp_file.write_text(checkpoint.to_json())
        temp_file.replace(latest_file)  # Atomic rename

    def get_latest_checkpoint(
        self,
        workflow_id: str
    ) -> Optional[OrchestratorCheckpoint]:
        """Load latest checkpoint from filesystem"""
        latest_file = self.checkpoint_dir / workflow_id / "latest.json"
        if latest_file.exists():
            return OrchestratorCheckpoint.from_json(latest_file.read_text())
        return None

    def get_checkpoint_history(
        self,
        workflow_id: str
    ) -> List[OrchestratorCheckpoint]:
        """Load all checkpoints for a workflow (for debugging/analysis)"""
        workflow_dir = self.checkpoint_dir / workflow_id
        if not workflow_dir.exists():
            return []

        checkpoints = []
        for checkpoint_file in sorted(workflow_dir.glob("[0-9][0-9][0-9].json")):
            checkpoints.append(
                OrchestratorCheckpoint.from_json(checkpoint_file.read_text())
            )
        return checkpoints
```

### Session Boundary Strategy

```python
class SessionBoundaryManager:
    """Determines when to checkpoint and restart"""

    MAX_DELEGATIONS_PER_SESSION = 10
    TOKEN_THRESHOLD_PERCENT = 0.6  # 60% of context

    def should_checkpoint_and_restart(
        self,
        delegation_count: int,
        estimated_token_usage: float,
        last_result: AgentMetadataResponse,
        phase_complete: bool
    ) -> tuple[bool, str]:

        # Rule 1: Max delegations reached
        if delegation_count >= self.MAX_DELEGATIONS_PER_SESSION:
            return True, "max_delegations_reached"

        # Rule 2: Token threshold exceeded
        if estimated_token_usage >= self.TOKEN_THRESHOLD_PERCENT:
            return True, "token_threshold_exceeded"

        # Rule 3: Human intervention occurred
        if last_result.requires_human:
            return True, "human_intervention"

        # Rule 4: Major phase completed
        if phase_complete:
            return True, "phase_complete"

        # Rule 5: Agent failed, will retry
        if last_result.status == "failed" and last_result.retry_eligible:
            return True, "retry_in_fresh_session"

        return False, ""
```

---

## Agent Response Schema

### Minimal Metadata Response (~100 tokens)

```python
@dataclass
class AgentMetadataResponse:
    """Minimal response - NO SUMMARIES"""

    # Status
    status: Literal["success", "failed", "blocked"]
    confidence: float  # 0.0-1.0

    # File changes (paths only)
    changes_made: List[str]
    files_read: List[str]

    # Routing hints
    next_suggested_action: Optional[str]

    # Human intervention
    requires_human: bool
    human_decision_prompt: Optional[str]

    # Agent-specific fields
    gate_decision: Optional[Literal["PASS", "FAIL", "CONCERNS"]]  # QA
    stories_created: Optional[List[str]]  # SM

    # Error handling
    error_type: Optional[str]
    error_message: Optional[str]
    retry_eligible: bool = True
```

---

## Human Intervention Triggers

### Escalation Rules

| Trigger | Condition | Action |
|---------|-----------|--------|
| Low confidence | `confidence < threshold` (default 0.85) | Block, await human signal |
| Core design change | Changes to PRD, architecture | Block, await approval |
| Max iterations | Dev-QA loop > 3 times | Block, human review needed |
| Retry exhausted | 3 failures on same task | Block, human intervention |
| Agent explicit | `requires_human = True` | Block with prompt |

### Temporal Signal Pattern

```python
@workflow.signal
async def approve_continue(self, decision_id: str, approved: bool, feedback: str = ""):
    """Human approves/rejects blocked decision"""
    self.user_approved_continue = approved

@workflow.query
def get_progress(self) -> dict:
    """Query workflow progress without blocking"""
    return {
        "epic_id": self.checkpoint.epic_id,
        "phase": self.checkpoint.current_phase,
        "stories_completed": len(self.checkpoint.stories_completed),
        "blocked": len(self.checkpoint.blocked_decisions) > 0
    }
```

---

## BMAD Workflow Mapping

### Phase Transitions

```
Phase 1: Sprint Planning
├── SM creates sprint plan with story list
├── Human approves/rejects plan
└── Transition to Phase 2 on approval

Phase 2: Dev-QA Loop (per story)
├── Dev implements story
├── QA reviews story
├── If PASS: Mark complete, next story
├── If FAIL: Dev fixes, re-review (max 3 iterations)
├── If max iterations: Block for human
└── If all stories done: Transition to Phase 3

Phase 3: Epic Complete
├── Notify human
├── Await approval for next epic
└── If approved: New workflow for next epic
```

### Agent Routing Logic

```python
def _determine_next_action(self) -> tuple[str, str]:
    phase = self.checkpoint.current_phase

    if phase == "sprint_planning":
        if not self.checkpoint.stories_pending:
            return "sm", "create_sprint_plan"
        else:
            self.checkpoint.current_phase = "dev_qa_loop"
            return "dev", f"implement_story:{self.checkpoint.stories_pending[0]}"

    if phase == "dev_qa_loop":
        story = self.checkpoint.current_story_id
        iterations = self.checkpoint.dev_qa_iterations.get(story, 0)

        if iterations >= 3:
            return "pause", "max_dev_qa_iterations"

        # Simplified: track last agent to determine next
        return "qa", f"review_story:{story}"  # After dev

    return "pause", "unknown_state"
```

---

## Design Decisions (Q4-Q8)

### Q4: Should JSONL tracking use different configs for orchestrator vs agents?

**Decision**: **Option C - Defer to Agent with Metadata**

With Dual-Track Architecture:
- Orchestrator: Excluded from auto-tracking entirely (via `excluded_paths`)
- Agents: Use uniform default summarization config

**Agent Metadata Strategy**:
- All BMAD agent types use identical filter settings (no per-role configs)
- Agents emit structured metadata tags (e.g., `role: qa`, `role: dev`, `story_id: 2.1`)
- Graphiti indexes metadata for filtered semantic queries
- No config proliferation or complexity

---

### Q5-Q6: Namespace Routing Questions

**Decision**: **Option A - PWD-based namespace routing (current approach)**

**Q5: How should auto-tracking route content to different namespaces?**
- Uses `project__{hash}` based on PWD where JSONL is created
- BMAD agents run in target project directories → automatic correct namespace
- No explicit override needed

**Q6: Can existing namespace metadata embedding handle this?**
- Yes, with `excluded_paths` for Temporal server
- BMAD agents get correct namespace via PWD detection

---

### Q7: Should tools remain fully agnostic?

**Decision**: **Option A - Fully Agnostic**

- Graphiti stays generic; no Temporal/BMAD-specific concepts
- All Temporal-specific logic lives in the Temporal server
- `excluded_paths` is a generic feature usable by any project
- Graphiti doesn't know about "orchestrators", "checkpoints", or "BMAD agents"

---

### Q8: What happens to orphaned checkpoints?

**Decision**: **Option C - Workflow-aware with fallback**

| Scenario | Action |
|----------|--------|
| Workflow completes successfully | Delete checkpoints (or archive) |
| Workflow fails | Keep for debugging |
| Orphaned (no workflow state) | Age-based cleanup (e.g., 30 days) |

**Implementation** (in Temporal server):
```python
class CheckpointRetentionPolicy:
    ARCHIVE_ON_SUCCESS = True
    KEEP_ON_FAILURE = True
    ORPHAN_TTL_DAYS = 30

    def cleanup_workflow(self, workflow_id: str, status: str) -> None:
        checkpoint_dir = self.checkpoint_dir / workflow_id
        if status == "completed" and self.ARCHIVE_ON_SUCCESS:
            self._archive_checkpoints(checkpoint_dir)
        elif status == "failed" and self.KEEP_ON_FAILURE:
            pass  # Keep for debugging
        # Orphan cleanup runs as scheduled job

    def cleanup_orphaned(self) -> None:
        """Remove checkpoints older than TTL with no active workflow"""
        cutoff = datetime.now() - timedelta(days=self.ORPHAN_TTL_DAYS)
        for workflow_dir in self.checkpoint_dir.iterdir():
            if self._is_orphaned(workflow_dir, cutoff):
                shutil.rmtree(workflow_dir)
```

---

## Implementation Phases (Revised)

### Phase 1: Graphiti excluded_paths Feature
- [x] Create sprint story
- [ ] Add `excluded_paths` to `SessionTrackingConfig`
- [ ] Implement path matching in `SessionManager`
- [ ] Update schema and documentation

### Phase 2: Temporal SDK Fork + Checkpoint Manager
- [ ] Fork Claude Code SDK for Temporal
- [ ] Implement CheckpointManager (filesystem-only, no Graphiti)
- [ ] Implement JSONL logging for BMAD agents (not orchestrator)
- [ ] Configure Graphiti exclusion for Temporal server path

### Phase 3: Temporal Workflows
- [ ] EpicWorkflow implementation
- [ ] DevQALoopWorkflow implementation
- [ ] Session boundary manager
- [ ] Signal/query handlers for human intervention

### Phase 4: Testing & Validation
- [ ] Crash recovery testing (filesystem checkpoints)
- [ ] Session boundary testing
- [ ] Human intervention flow testing
- [ ] Cross-project isolation testing
- [ ] Graphiti auto-tracking testing (BMAD agent context only)

---

## Appendix: Token Budget Analysis

### Per-Checkpoint Cost
- Checkpoint schema: ~170 tokens
- Filesystem overhead: 0 (no LLM, no Graphiti)
- **Total per checkpoint: ~170 tokens** (filesystem-only)

### Per-Delegation Cost
- Agent metadata response: ~100 tokens
- Orchestrator routing logic: ~50 tokens
- **Total per delegation: ~150 tokens**

### Session Budget (200K context)
- CLAUDE.md overhead: ~2,000 tokens
- System prompt: ~500 tokens
- Available for work: ~197,500 tokens
- At 60% threshold: ~118,500 tokens
- **Max delegations before restart: ~790** (in theory)
- **Conservative limit: 10 delegations** (accounts for tool calls, responses)

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-15 | 0.1.0-draft | Initial design capture from session |
| 2025-12-15 | 0.2.0-draft | Added JSONL integration strategy, clarified architecture, updated questions |
| 2025-12-15 | 0.3.0-draft | **Decisions made**: Q1 (Dual-Track), Q2 (filesystem-first), Q3 (filesystem query). Updated architecture, added CheckpointManager, revised data flow. |
| 2025-12-15 | 0.3.1-draft | **Clarification**: Checkpoints are filesystem-ONLY (no Graphiti integration at all). Removed optional Graphiti enhancement from CheckpointManager. Temporal server excluded from auto-tracking, so checkpoints shouldn't be in Graphiti either. |
| 2025-12-15 | 0.4.0-draft | **All questions answered**: Q4 (uniform config + agent metadata), Q5-Q6 (PWD-based routing), Q7 (fully agnostic), Q8 (workflow-aware cleanup). Added CheckpointRetentionPolicy. |

---

**END OF DOCUMENT**
