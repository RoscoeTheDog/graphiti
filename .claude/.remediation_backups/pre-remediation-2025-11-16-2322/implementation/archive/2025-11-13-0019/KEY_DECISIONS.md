# Key Architecture Decisions - Quick Reference

## Decision Matrix

| Decision | Chosen Approach | Rejected Alternatives | Rationale | Document Reference |
|----------|----------------|----------------------|-----------|-------------------|
| **Git Operation Detection** | Hash-based comparison | Time window (5s) | Handles immediate user edits, deterministic | `git-intrinsic-detection.md` |
| **File Operation Filtering** | Source-based (`source="filesystem_watch"` vs `"git_bulk_update"`) | Operation-based (exclude all "update") | Preserves individual updates, excludes bulk noise | `source-based-filtering.md` |
| **Conversation Context** | JSONL parsing | MCP tool tracking | 0 tokens overhead vs 1k-7.5k per session | `conversation-buffer-analysis.md` |
| **Session Memory Scope** | Complete session history | Git operations only | Enable cross-session learning, workflow patterns | `comprehensive-session-memory.md` |
| **JSONL Content Filtering** | Structure + summary | Full content or structure only | 93% token reduction, preserves context | `session-tracking-solutions.md` |
| **Lazy-Load Operations** | Include: create/update/delete, Exclude: move/rename/git_bulk | Exclude all updates | Valuable context without pollution | `source-based-filtering.md` |
| **Git Context Capture** | Three-tier (metadata + conversation + files) | Binary include/exclude | Preserves WHY decisions were made | `git-rollback-solution.md` |

## Critical "Why" Decisions

### Why Hash-Based Git Detection?

**Problem Scenario**:
```bash
git reset --hard HEAD~5
vim database.py  # User edits IMMEDIATELY after rollback
```

**Time-based approach**: Fails (edits within 5-second window get misclassified)

**Hash-based approach**: Works (content hash differs from git state)

**Key Insight**: User behavior is unpredictable, content is deterministic.

### Why Source-Based Filtering?

**User Requirement**: "Create/Update/Delete are important context"

**Challenge**: Git rollback creates 47 bulk updates (noise)

**Solution**: Differentiate by source, not operation
- Individual file edit → `source="filesystem_watch"` → INCLUDE
- Git bulk operation → `source="git_bulk_update"` → EXCLUDE

**Key Insight**: Same operation type, different semantic value.

### Why JSONL Parsing Over MCP Tools?

**Token Cost Comparison**:
- JSONL parsing: 0 tokens (filesystem I/O)
- MCP tool tracking: 1k-7.5k tokens per session

**Why it works**: Claude Code already writes comprehensive logs, just read them.

**Key Insight**: Don't recreate what already exists on filesystem.

### Why Complete Session History?

**Original Scope**: Track files for lazy-loading

**User Insight**: "If we're already tracking files with watchdog, why not track JSONL too?"

**Expanded Value**:
- Workflow patterns: "Read → Grep → Edit" (successful 85%)
- Error resolution: "JWT timeout? Fix with expiry=3600"
- Decision context: "Why Redis? Serverless constraints"
- Cross-session learning: "How did we solve this before?"

**Key Insight**: Complete memory enables agent institutional knowledge.

### Why Structure-Only for Tool Outputs?

**Token Analysis**:
- Tool outputs: 190k tokens (95% of session)
- Semantic value: Low (file contents, logs, etc.)

**Solution**: Keep structure, omit content
```
Before: Read(file.py) → [2000 lines of code]  (50k tokens)
After:  Read(file.py) → File read (2000 lines) (20 tokens)
```

**Key Insight**: Tool invocation patterns matter more than tool outputs.

## Three-Tier Git Context Architecture

### Tier 1: Git Metadata (~50 tokens)
**WHAT happened**: "Git reset --hard: 47 files, commit abc→def"
**Purpose**: Agent knows git operation occurred
**Always included in lazy-load**: YES ✅

### Tier 2: Conversation Context (~500 tokens)
**WHY it happened**: "User: Won't work with serverless, Agent: Should rollback"
**Purpose**: Preserve decision reasoning
**Always included in lazy-load**: YES ✅

### Tier 3: File State Changes (~50k tokens if included)
**HOW files changed**: 47 individual file contents
**Purpose**: Queryable history
**Always included in lazy-load**: NO ❌ (excluded by source filter)

**Key Insight**: Separate WHAT/WHY (valuable) from HOW (queryable but noisy).

## Token Cost Projections

### Per-Session Costs

**Filesystem Tracking** (5-10 file updates):
- Individual updates: 10 × 12k = 120k tokens
- Cost: ~$0.02-$0.36 per session

**Git Operations** (1-2 per session):
- Tier 1 metadata: ~5k tokens
- Tier 2 context: ~5.5k tokens
- Tier 3 files: 0 tokens (not indexed)
- Cost: ~$0.02 per git operation

**Session Memory** (1 hour, 20 exchanges):
- Raw JSONL: 205k tokens
- After filtering: 13.5k tokens
- Graphiti processing: ~34k tokens (with batching)
- Cost: ~$0.05-$1.02 per session

**Total per session**: ~$0.10-$1.50

**Monthly** (60 sessions): ~$6-$90/month

### Optimization Levers

1. **Batching**: Reduce episodes from 20→4 (66% savings)
2. **Filtering**: Keep structure, omit outputs (93% reduction)
3. **Incremental**: Only index new content (avoids re-processing)
4. **Selective**: Track high-value sessions only (50%+ savings)

## Configuration Philosophy

**Global vs Project**:
- Session tracking: Global config (`~/.graphiti/`)
- File patterns: Project-specific
- Permissions: Explicit user grant

**Why**: Clean separation, no project pollution, user control.

**Incremental by Default**:
- Track last indexed position
- Only process new content
- Avoid re-indexing entire history

**Why**: Token efficiency, performance.

**Filtering First**:
- Default: Structure-only for tool outputs
- User can opt-in to full content
- Conservative cost management

**Why**: Predictable costs, user control.

## Success Metrics

**Technical**:
- [ ] Token costs within $0.05-$1/session
- [ ] 93%+ token reduction from filtering
- [ ] Hash-based detection 100% accurate
- [ ] Incremental indexing works reliably

**Value**:
- [ ] Agents answer "why did we do X?" queries
- [ ] Cross-session continuity improves
- [ ] Error resolution time decreases
- [ ] Workflow patterns emerge in graph

## Implementation Phases

**Phase 1: File Tracking MVP**
- Hash-based git detection
- Source-based filtering
- Basic file tracking

**Phase 2: Session Memory Core**
- JSONL parsing
- Smart filtering (user/agent + structure)
- Incremental indexing

**Phase 3: Optimization**
- Chunking strategies
- Advanced filtering rules
- Query interface

**Phase 4: Intelligence**
- Workflow pattern recognition
- Auto-suggestions from history
- Cross-project learning

## Risk Mitigation

**Risk**: Token costs exceed projections
**Mitigation**: More aggressive filtering, selective tracking

**Risk**: JSONL format changes
**Mitigation**: Version detection, graceful degradation

**Risk**: Performance issues with large sessions
**Mitigation**: Batching, async processing, queue management

**Risk**: Privacy concerns with conversation tracking
**Mitigation**: Explicit permission model, opt-out available

## The Big Picture

**From**: Sparse, manual agent memories
**To**: Complete, automatic institutional memory

**From**: "Agent forgets what happened last session"
**To**: "Agent remembers workflow patterns across weeks"

**From**: "Same errors repeated multiple times"
**To**: "Agent learns from past error resolutions"

**From**: "User explains context every session"
**To**: "Agent knows project history and decisions"

This is **institutional memory** for AI agents.
