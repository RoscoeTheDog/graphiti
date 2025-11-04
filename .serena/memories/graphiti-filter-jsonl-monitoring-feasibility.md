# Graphiti Memory Filter: JSONL Log Monitoring Feasibility Analysis

**Date**: 2025-11-03
**Question**: Can we monitor Claude Code JSONL logs to auto-store memories without Claude directives?

---

## The Core Problem You Identified

**Paradox of Integrated Filtering:**
- If filter is in `add_memory()`, Claude must still decide WHEN to call it
- Claude needs directives about what's memory-worthy
- Filter becomes redundant - Claude already made the decision
- **No reduction in Claude's cognitive overhead**

**Your Vision:**
- Server monitors session passively (zero Claude awareness)
- LLM analyzes events autonomously in background
- Auto-stores valuable patterns to Graphiti
- Claude lazy-loads memories via `search_memory_facts()` when needed
- **True zero-overhead memory system**

---

## Claude Code JSONL Log Structure

### Location
```
~/.claude/projects/<project-path>/<session-id>.jsonl
```

### Log Entry Schema (Discovered)

```json
{
  "type": "user|assistant|tool_use|tool_result",
  "parentUuid": "<parent-message-uuid>",
  "sessionId": "<session-uuid>",
  "agentId": "<agent-id>",
  "cwd": "<working-directory>",
  "gitBranch": "<current-branch>",
  "timestamp": "ISO-8601",
  "message": {
    "role": "user|assistant",
    "content": "..." // or array of content blocks
  },
  "uuid": "<message-uuid>"
}
```

### What's Available

**User Messages:**
- Full user prompts
- Timestamp and session context

**Assistant Messages:**
- Full responses (text)
- Tool calls (name, parameters)
- Model used, token usage
- Stop reason

**Tool Results:**
- Tool name and parameters
- Tool output (file contents, command results, etc.)
- Success/failure status

**Session Context:**
- Working directory
- Git branch
- Session ID (for grouping)
- Parent/child message relationships

---

## Feasibility: Can This Work?

### ✅ **Technical Feasibility: YES**

**What We Can Monitor:**

1. **File Operations**
   - Read/Write/Edit operations
   - Which files were modified
   - Error patterns (file not found, permission denied)

2. **Command Execution**
   - Bash commands run
   - Success/failure status
   - Error messages (rate limits, timeouts, etc.)

3. **Error Patterns**
   - Repeated errors (env-quirk indicators)
   - Workarounds applied
   - Configuration changes

4. **User Preferences**
   - Explicit statements in prompts
   - Correction patterns (user says "no, do X instead")

5. **Architectural Decisions**
   - User explains "why" legacy code exists
   - Discussion about tradeoffs

### ❌ **Practical Feasibility: MAJOR CHALLENGES**

#### Challenge 1: **Context Window Problem**
- Logs are append-only, unbounded
- Need sliding window (last N messages?)
- Risk missing context across window boundaries
- How to know when a "memory-worthy event" completes?

**Example:**
```
Message 1: "Fix the bug in parser.py"
Message 2-10: Multiple file reads, attempts
Message 11: "Actually, keep the old behavior for v1 compatibility"
```
- Memory-worthy event is Message 11 (historical-context)
- But requires context from Messages 1-10
- How does LLM filter know this is complete?

#### Challenge 2: **Event Boundary Detection**
- When does a "memory-worthy event" start/end?
- User asks 5 questions in one session - are they related?
- Tool calls span multiple log entries - how to group them?

**Example:**
```
Read file A → Error → Edit .env → Retry → Success
```
- Should store: "Env quirk: Need X=Y in .env for A to work"
- But spread across 10+ log entries
- How to detect this pattern and group it?

#### Challenge 3: **False Positives**
- Every error looks like env-quirk initially
- Need to distinguish:
  - Typo (user corrects, move on) ❌ Don't store
  - Env quirk (user edits .env, works) ✅ Store
  - Bug (user edits code, commits) ❌ Don't store

- LLM would need to see resolution to classify
- Resolution might be 50 messages later

#### Challenge 4: **Latency vs Completeness Tradeoff**
- **Real-time monitoring**: Low latency, but incomplete context
- **Batch analysis**: Complete context, but high latency
- Need to wait for "event completion" but how to detect?

#### Challenge 5: **Cost**
- Analyzing every message → Expensive
- Analyzing every N messages → Miss short events
- Analyzing on heuristic triggers → Complex logic

**Example Cost:**
- Session: 100 messages
- Average message: 500 tokens context
- Filter prompt: 300 tokens
- Analysis per message: ~800 tokens
- Total: 80k tokens per session
- Cost: ~$0.08/session (gpt-4o-mini)
- If 10 sessions/day: $0.80/day = $24/month

---

## Proposed Architecture (If We Proceed)

### Component 1: Log Monitor (Background Service)

```python
class JSONLMonitor:
    def __init__(self, project_path: str):
        self.log_files = self._find_log_files(project_path)
        self.tail_position = {}  # Track read position per file
        
    async def monitor_loop(self):
        while True:
            for log_file in self.log_files:
                new_entries = self._read_new_entries(log_file)
                await self._process_entries(new_entries)
            await asyncio.sleep(5)  # Poll every 5 seconds
```

### Component 2: Event Detector

```python
class EventDetector:
    """Detects memory-worthy event patterns"""
    
    def __init__(self):
        self.sliding_window = []  # Last N messages
        self.pending_events = {}  # Events awaiting resolution
        
    def add_message(self, log_entry):
        self.sliding_window.append(log_entry)
        
        # Detect patterns
        if self._is_error_pattern(log_entry):
            event_id = self._create_pending_event("error", log_entry)
            self.pending_events[event_id] = {
                "start": log_entry,
                "context": self.sliding_window[-10:],
                "status": "pending"
            }
            
    def _is_error_pattern(self, entry):
        """Heuristics for error detection"""
        if entry["type"] == "tool_result":
            if "error" in str(entry.get("message", "")).lower():
                return True
        return False
        
    def resolve_event(self, event_id, resolution):
        """Mark event as resolved (success/failure)"""
        event = self.pending_events[event_id]
        event["resolution"] = resolution
        event["status"] = "resolved"
        return event
```

### Component 3: LLM Filter (Batch Analysis)

```python
class BatchFilter:
    """Analyzes resolved events for memory-worthiness"""
    
    async def analyze_event(self, event_context):
        # Build prompt from event context
        prompt = self._build_event_prompt(
            start=event_context["start"],
            context=event_context["context"],
            resolution=event_context["resolution"]
        )
        
        # Call LLM
        result = await self.llm.complete(prompt)
        
        if result["should_store"]:
            await self._store_to_graphiti(event_context, result)
```

### Component 4: Storage

```python
async def _store_to_graphiti(self, event, filter_result):
    await graphiti.add_episode(
        name=filter_result["summary"],
        episode_body=self._format_event(event),
        source="session_monitor",
        group_id=event["sessionId"]
    )
```

---

## The Killer Question

**How do you detect "event completion"?**

Options:

1. **Time-based**: Event complete after N seconds of inactivity
   - ❌ Arbitrary timeout, might truncate ongoing work
   
2. **Heuristic-based**: Detect resolution patterns
   - ✅ "git commit" = bug fix complete
   - ✅ ".env edited + retry success" = env quirk resolved
   - ❌ Complex pattern matching, many edge cases
   
3. **Session-end**: Analyze entire session at end
   - ✅ Complete context
   - ❌ High latency, large context windows
   - ❌ No real-time benefits

4. **Hybrid**: Heuristics + time-based fallback
   - ✅ Best of both worlds
   - ❌ Most complex to implement

---

## Recommendation

### Option A: **Don't Do JSONL Monitoring** (Recommended)

**Why:**
1. High complexity, many edge cases
2. Claude Code specific (won't work in Cursor/Cline)
3. Event boundary detection is unsolved
4. Costly to run LLM on every event
5. Latency vs completeness tradeoff unsolvable

**Alternative:**
- Keep manual `should_store()` tool
- Update CLAUDE.md with clear guidelines on WHEN to call it
- Rely on Claude's judgment (it's quite good at this)
- Accept the "directives overhead" as unavoidable

### Option B: **Implement Simplified JSONL Monitoring** (Experimental)

**Scope:**
- Session-end batch analysis only (not real-time)
- Analyze entire session for patterns
- Store to graphiti at session close
- Claude lazy-loads next session

**Pros:**
- Simpler (no event boundary detection)
- Complete context
- Works as intended (zero Claude overhead)

**Cons:**
- Only useful across sessions (not intra-session)
- High token cost per session analysis
- Still Claude Code specific

---

## Conclusion

**Your vision is noble but impractical for real-time monitoring.**

The fundamental problems:
1. **Event boundary detection** - Unsolvable without domain-specific heuristics
2. **Context window management** - Tradeoff between completeness and latency
3. **Framework lock-in** - Claude Code specific, won't generalize

**Best path forward:**
- Accept that Claude needs directives
- Make `should_store()` as simple as possible
- Provide excellent CLAUDE.md guidance
- Consider session-end batch analysis as future enhancement

**The paradox remains:** 
If you want automatic memory, you need event detection. But event detection requires understanding "what's worth remembering", which is the filter's job. Circular dependency.

**Bottom line:** Manual `should_store()` + good directives is the pragmatic solution.
