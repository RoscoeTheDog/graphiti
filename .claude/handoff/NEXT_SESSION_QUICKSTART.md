# Next Session Quick Start

## What to Read First

**5-Minute Overview**:
1. `.claude/handoff/filesystem-tracking-session-2025-11-12.md` - Session summary
2. `.claude/implementation/KEY_DECISIONS.md` - Decision matrix and rationale

**Deep Dive** (if implementing):
3. `.claude/implementation/comprehensive-session-memory.md` - Complete architecture
4. `.claude/implementation/session-tracking-solutions.md` - Solutions to challenges

## The Big Idea (60 seconds)

**What we built**: Architecture for automatic agent memory via filesystem tracking

**Three components**:
1. **File tracking**: Auto-index project files to Graphiti
2. **Git-aware detection**: Smart classification of bulk vs individual operations
3. **Session memory**: Auto-index conversation logs (JSONL) to Graphiti

**Revolutionary part**: Complete session history enables agent institutional memory
- "What were we working on last session?"
- "Why did we choose approach X?"
- "How did we solve this error before?"

## What Needs Testing (Priority Order)

### 1. JSONL Parsing Proof-of-Concept (2-3 hours)

**Goal**: Verify JSONL path resolution and basic parsing work

**Steps**:
```python
# 1. Resolve JSONL path from project root
project_root = "/path/to/graphiti"
project_hash = hashlib.sha256(project_root.encode()).hexdigest()[:16]
jsonl_dir = Path.home() / ".claude" / "projects" / project_hash / "sessions"

# 2. Find active session
session_files = list(jsonl_dir.glob("*.jsonl"))
active_session = max(session_files, key=lambda p: p.stat().st_mtime)

# 3. Parse and filter
with open(active_session, 'r') as f:
    for line in f:
        entry = json.loads(line)
        if entry.get("type") in ["user", "assistant"]:
            print(entry["content"][:100])
```

**Success criteria**: Can read current session JSONL and extract user/agent messages

### 2. Token Cost Measurement (1-2 hours)

**Goal**: Validate projected costs with real data

**Steps**:
```python
# 1. Filter JSONL session (user/agent + tool structure)
filtered_tokens = count_tokens(filtered_session)

# 2. Create test episode in Graphiti
result = await graphiti.add_episode(
    name="test-session-chunk",
    episode_body=filtered_session
)

# 3. Measure actual LLM tokens used
# (Check Graphiti logs or OpenAI dashboard)
```

**Success criteria**:
- Filtered session: ~13.5k tokens (projected)
- Graphiti processing: ~34k tokens with batching (projected)
- Total cost: ~$0.05-$1.02 per session (projected)

### 3. Smart Filtering Implementation (3-4 hours)

**Goal**: Implement `JSONLFilter` class from design docs

**Reference**: `.claude/implementation/session-tracking-solutions.md` (lines 200-300)

**Key methods**:
- `filter_entry()` - Apply rules to JSONL entry
- `_summarize_output()` - Create concise tool output summaries
- `format_episode()` - Format filtered entries into episode body

**Success criteria**: 93% token reduction from raw to filtered

### 4. Hash-Based Git Detection (4-6 hours)

**Goal**: Implement git-intrinsic detection (not time-based)

**Reference**: `.claude/implementation/git-intrinsic-detection.md`

**Key components**:
```python
# 1. On git HEAD change
git_hashes = self.get_git_tracked_file_hashes()  # git ls-files -s

# 2. On file change
current_hash = self.compute_git_hash(filepath)

# 3. Compare
if current_hash == git_hashes[filepath]:
    source = "git_bulk_update"  # Git operation
else:
    source = "filesystem_watch"  # User edit
```

**Success criteria**: Immediate user edit after git operation correctly classified

## Critical Files to Reference

**Architecture**:
- `filesystem-tracking-design.md` - Complete file tracking spec
- `comprehensive-session-memory.md` - Session memory architecture

**Technical Decisions**:
- `git-intrinsic-detection.md` - Hash-based detection algorithm
- `source-based-filtering.md` - Why source, not operation
- `KEY_DECISIONS.md` - Quick decision reference

**Solutions**:
- `session-tracking-solutions.md` - Token costs, filtering, JSONL location
- `conversation-buffer-analysis.md` - Approach comparison

## Configuration to Use

```json
{
  "version": "2.0",
  "session_tracking": {
    "enabled": true,
    "mode": "claude_code_jsonl",
    "filtering": {
      "keep_user_messages": true,
      "keep_agent_responses": true,
      "keep_tool_structure": true,
      "omit_tool_outputs": true
    }
  },
  "projects": {
    "DESKTOP-BBGIAP4__f38d6ab5": {
      "project_root": "C:\\Users\\Admin\\Documents\\GitHub\\graphiti",
      "jsonl_path": "~/.claude/projects/{hash}/sessions"
    }
  }
}
```

## Expected Outcomes

**If token costs match projections** (~$0.05-$1/session):
- ✅ Proceed with full implementation
- Build incremental indexing
- Add to MCP server
- Enable by default

**If token costs exceed projections** (>$2/session):
- ⚠️ More aggressive filtering needed
- Consider batching larger chunks
- Make session tracking opt-in
- Provide cost warnings to users

**If JSONL parsing fails**:
- ❌ Fall back to MCP tool approach
- Document limitations
- Provide alternative for non-Claude Code clients

## Questions to Answer

1. **Does JSONL path resolution work reliably?**
   - Test on Windows vs Unix
   - Handle symlinks, network drives?

2. **Are token costs acceptable?**
   - Measure with real session data
   - Compare projected vs actual
   - User willingness to pay?

3. **Does filtering preserve enough context?**
   - Test query quality with filtered episodes
   - Can agent answer "why did we do X?" queries?
   - Need more/less filtering?

4. **Is incremental indexing necessary?**
   - Performance with full session re-processing?
   - Token waste from re-indexing?
   - Complexity vs benefit?

## Success Criteria (Go/No-Go Decision)

**GO** (proceed with full implementation):
- ✅ JSONL parsing works reliably
- ✅ Token costs <$1 per session
- ✅ Filtered episodes preserve context
- ✅ Hash-based detection is accurate

**NO-GO** (need more work):
- ❌ Token costs >$2 per session
- ❌ JSONL path resolution fails
- ❌ Filtered episodes lose too much context
- ❌ Performance issues with large sessions

## Implementation Timeline (If GO)

**Week 1**: Core components
- JSONLSessionTracker
- JSONLFilter
- Basic integration with MCP server

**Week 2**: Git detection
- GitAwareWatcher with hash-based detection
- Source-based filtering
- Test with real git workflows

**Week 3**: Optimization
- Incremental indexing
- Chunking strategies
- Performance tuning

**Week 4**: Testing & iteration
- Real-world usage
- Cost monitoring
- Filter refinement

## Quick Commands for Testing

```bash
# Find JSONL directory for current project
cd ~/Documents/GitHub/graphiti
python -c "
import hashlib
from pathlib import Path
project = '$(pwd)'
hash = hashlib.sha256(project.encode()).hexdigest()[:16]
print(Path.home() / '.claude' / 'projects' / hash / 'sessions')
"

# Count tokens in JSONL session (rough estimate)
wc -w ~/.claude/projects/{hash}/sessions/*.jsonl
# Divide by 0.75 to get approximate tokens

# Test Graphiti add_episode cost
# (Use Graphiti playground or create test script)
```

## Key Contacts/Resources

**Documentation**:
- Graphiti docs: https://github.com/getzep/graphiti
- Claude Code JSONL format: (infer from existing files)
- Watchdog library: https://python-watchdog.readthedocs.io/

**Testing**:
- Use this Graphiti project as test case
- Session logs already exist in `~/.claude/projects/`
- Real git operations to test detection

## One-Line Summary for Next Agent

**"Test JSONL parsing + token costs to validate session memory architecture - if costs <$1/session, proceed with full implementation of agent institutional memory system."**

---

## Appendix: File Locations

**Design Documents**:
- `.claude/implementation/` - All architecture docs
- `.claude/handoff/` - This handoff and session summary

**Key Code References** (for implementation):
- `mcp_server/graphiti_mcp_server.py` - MCP server entry point
- `graphiti_core/graphiti.py` - Core Graphiti class
- Look for `add_episode` method signature

**Configuration**:
- `~/.graphiti/tracking-config.json` (to be created)
- Project config in Graphiti (group_id based)

Good luck! This is genuinely revolutionary work. 🚀
