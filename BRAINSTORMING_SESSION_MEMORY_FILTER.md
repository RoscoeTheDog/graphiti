# Graphiti Memory Filter - Brainstorming Session

**Date**: 2025-11-03
**Participants**: User + Claude Code Agent
**Topic**: How to leverage Graphiti for agent session memory without excessive overhead

---

## Executive Summary

**Problem**: The original memory filter implementation requires Claude to manually call `should_store()` before every `add_memory()`, creating overhead and defeating the purpose of "automatic" filtering.

**Solution (Phased Approach)**:
1. **Phase 1 (Immediate)**: Client-side token threshold summaries
   - Simple to implement and test
   - Validates the concept
   - Minimal overhead

2. **Phase 2 (Future)**: Autonomous background analysis with Gemini
   - Zero client overhead
   - Better analysis quality
   - Scales across sessions

---

## The Core Problem Identified

### Original Plan Contradiction

The implementation plan said:
- **"Automatic filter detection"** (Objective 1)
- **"Minimal agent overhead"** (Objective 5)

But described a **manual workflow**:
1. Agent calls `should_store(event_description, context)`
2. Agent reads response
3. Agent decides
4. Agent conditionally calls `add_memory()`

**This is NOT automatic and has MAXIMUM overhead.**

### The Fundamental Paradox

**If filtering is integrated into `add_memory()`:**
- ✅ Filtering happens automatically
- ❌ But Claude still needs directives about WHEN to call `add_memory()`
- ❌ So Claude is already deciding what's memory-worthy
- ❌ The filter becomes redundant

**User's Insight:**
> "It would be impractical for the server to use add_memory() with a filter built in simply because there would have to be some directives embedded into the agent on when to add a memory. If directives have to be embedded into the agent anyway, then the client would have to understand what is to be filtered and what isn't-- not the server."

**Conclusion**: You can't have automatic filtering without automatic detection of memory-worthy events. But detecting events IS the filtering. It's circular.

---

## Solution Evolution

### Approach 1: JSONL Log Streaming (Explored & Rejected)

**Concept**: Server monitors Claude Code's JSONL session logs in real-time

**What's Available in Logs**:
- Location: `~/.claude/projects/<project>/<session-id>.jsonl`
- User messages (full prompts)
- Assistant responses (full text)
- Tool calls (Read, Edit, Bash, etc.)
- Tool results (outputs, errors)
- Session context (cwd, git branch, timestamps)

**Why We Rejected It**:

1. **Event Boundary Detection** (Unsolvable)
   - When does a "memory-worthy event" start/end?
   - Example: Error → 5 file reads → edit .env → retry → success = 20+ log entries
   - How to know it's "complete"?

2. **Context Window Management**
   - Need last N messages for context
   - Events span variable lengths (5-50+ messages)
   - Miss context = misclassify event

3. **Latency vs Completeness Tradeoff**
   - Real-time = incomplete context (can't classify yet)
   - Batch = complete context but no intra-session benefit

4. **Classification Accuracy**
   - Every error looks like "env-quirk" initially
   - Need to see resolution to classify properly
   - Resolution might be 50 messages later

5. **Cost**
   - ~80k tokens per session analysis
   - $0.08/session × 10 sessions/day = $24/month

6. **Framework Lock-In**
   - Claude Code specific
   - Won't work in Cursor, Cline, etc.

**Conclusion**: Real-time JSONL monitoring is technically possible but practically problematic.

---

### Approach 2: Token Threshold Session Summaries (CHOSEN - Phase 1)

**Concept**: Client agent tracks its own token usage and writes a session summary when threshold is hit.

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Session 1 (Claude Sonnet)                                    │
│ - Token counter MCP tracks usage                             │
│ - When threshold hit (e.g., 150k tokens):                    │
│   → Agent summarizes session                                 │
│   → Writes summary to Graphiti via add_memory()             │
│   → Summary includes:                                        │
│     • Errors encountered + solutions                         │
│     • Files modified                                         │
│     • User preferences revealed                              │
│     • Architectural decisions made                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Session 2 (New Claude Agent)                                 │
│ - On startup: Lazy load recent memories                      │
│ - search_memory_facts("recent session errors", max_facts=10)│
│ - Gets compressed summary (~500-1k tokens)                   │
│ - Understands what went wrong in last session                │
│ - Context window preserved!                                  │
└─────────────────────────────────────────────────────────────┘
```

#### Why This Works

1. **Simple to Implement**
   - Token counter MCP already exists
   - Just add summary prompt at threshold
   - Use existing `add_memory()` tool

2. **Easy to Test**
   - Run session until threshold
   - Check if summary is useful
   - Iterate on summary prompt

3. **Validates Concept**
   - Proves lazy-loading is valuable
   - Tests if Graphiti provides benefit
   - Low risk

4. **Minimal Overhead**
   - Only ~2k tokens for summary generation
   - Happens at natural breakpoint (threshold)
   - No continuous monitoring needed

5. **Framework Agnostic**
   - Works in any MCP-compatible client
   - No log parsing needed
   - No client-specific code

#### Cost Analysis

**Session 1 (150k tokens + 2k summary):**
- Work: 150k tokens @ $3/1M = $0.45
- Summary: 2k tokens @ $3/1M = $0.006
- **Total: $0.456**

**Session 2 (lazy load 500 tokens):**
- Load summary: 500 tokens @ $3/1M = $0.0015
- Work: 150k tokens = $0.45
- **Total: $0.4515**

**Net cost: ~$0.01 per session pair** (negligible)

#### Session Summary Prompt Template

```python
SUMMARY_PROMPT = """This session is ending (token threshold reached).

Summarize the following for the next agent:

1. **Errors Encountered**
   - What failed and why
   - Solutions that worked (if any)
   - Ongoing issues (unresolved)

2. **Files Modified**
   - Key changes made
   - Purpose of changes

3. **User Preferences Revealed**
   - Coding style preferences
   - Communication preferences
   - Tool preferences

4. **Architectural Decisions**
   - Why certain approaches were chosen
   - Historical context provided

5. **Important Context**
   - PRD location (if mentioned)
   - Implementation plan location (if mentioned)
   - Next steps

Format as concise bullet points. Focus on NON-REDUNDANT information:
- ✅ Store: Env quirks, user prefs, workarounds, historical context
- ❌ Skip: Bug fixes in code, config in repo, docs added

Keep summary under 800 words."""
```

#### Implementation Steps

1. **Monitor Token Usage**
   - Use existing token counter MCP
   - Set threshold (e.g., 150k tokens)

2. **Generate Summary**
   - At threshold, prompt Claude to summarize
   - Use template above

3. **Write to Graphiti**
   ```python
   add_memory(
       name=f"Session {date} {time}: {project_name}",
       episode_body=summary_text,
       source="text",
       group_id=f"project-{project_name}:machine-{hostname}"
   )
   ```

4. **Lazy Load on Startup**
   ```python
   # Next session starts
   recent_memories = search_memory_facts(
       query="recent session errors and important context",
       max_facts=10,
       group_ids=[f"project-{project_name}:machine-{hostname}"]
   )
   ```

#### Filter Criteria (What to Store)

**✅ STORE** (Non-redundant):
- **env-quirk**: Machine/OS-specific issues (can't fix in code)
  - Example: "Neo4j timeout fixed by setting NEO4J_TIMEOUT=60 in .env"
- **user-pref**: User preferences revealed (subjective)
  - Example: "User prefers concise responses with explicit type hints"
- **external-api**: 3rd party service quirks
  - Example: "GitHub API rate limit workaround: batch requests every 5min"
- **historical-context**: Why legacy code exists
  - Example: "Old parser kept for v1 data file compatibility"
- **cross-project**: General learnings/heuristics
  - Example: "Always validate JWT before database queries"
- **workaround**: Non-obvious solutions
  - Example: "Use setTimeout(0) to fix React setState race condition"

**❌ SKIP** (Redundant):
- **bug-in-code**: Fixed in codebase (now in git)
- **config-in-repo**: Config changes (now committed)
- **docs-added**: Documentation (now in README/docs)
- **first-success**: No learning occurred

---

### Approach 3: Autonomous Background Analysis (Future - Phase 2)

**Concept**: Background service monitors session close events, analyzes entire session with Gemini, writes to Graphiti automatically.

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Session 1 (Claude Sonnet - Primary Agent)                    │
│ - Works on tasks                                              │
│ - Token counter MCP tracks usage                             │
│ - Session ends (timeout, completion, or token threshold)     │
│ - Writes JSONL log: ~/.claude/projects/.../session-1.jsonl   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Background Analyzer (Gemini 2.0 Flash 1M - Thinking Mode)    │
│ - Detects session close event                                │
│ - Reads entire JSONL log (~50-200k tokens)                   │
│ - Analyzes for: errors, solutions, patterns, preferences     │
│ - Writes summary to Graphiti                                 │
│ - Sets LOCK during analysis                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Session 2 (Claude Sonnet - New Agent)                        │
│ - Spawns, attempts to read memories                          │
│ - Waits for LOCK release (if analyzer still running)        │
│ - Lazy loads: search_memory_facts("recent session")         │
│ - Gets compressed summary (~500-1k tokens)                   │
│ - Context window preserved!                                  │
│ - Zero overhead during session                               │
└─────────────────────────────────────────────────────────────┘
```

#### Why This Is Better (Long-Term)

1. **Zero Client Overhead**
   - Client agent doesn't know about memory system
   - No summary generation during session
   - More tokens available for actual work

2. **Better Analysis Quality**
   - Fresh perspective (not fatigued agent)
   - Specialized prompt for pattern detection
   - Thinking mode for deeper analysis
   - Can take 30-60 seconds (not rushed)

3. **Async = No Latency**
   - Session ends immediately
   - Analysis happens in parallel
   - Lock rarely blocks (analysis finishes before Session 2 starts)

4. **Context Window Preservation**
   - Phase 1: 150k work + 2k summary = 152k used
   - Phase 2: 150k work = 150k used
   - **Net gain: +2k tokens per session**
   - Over 10 sessions: +20k tokens = ~1 extra session

#### Cost Analysis

**Session 1 (Claude Sonnet):**
- Task work: 150k tokens @ $3/1M = $0.45
- No summary overhead
- **Cost: $0.45**

**Background Analyzer (Gemini 2.0 Flash):**
- Read JSONL: 150k tokens input (cached after first read)
- Generate summary: 1k tokens output
- Input: FREE (context caching)
- Output: $0.30/1M × 1k = $0.0003
- **Cost: $0.0003** (negligible)

**Session 2 (Claude Sonnet):**
- Load summary: 500 tokens @ $3/1M = $0.0015
- Task work: 150k tokens = $0.45
- **Cost: $0.4515**

**Total: $0.45 + $0.0003 + $0.4515 = $0.902**

**Savings vs Phase 1: ~$0.01 per session pair** (negligible difference)

**BUT: Context window preservation is the real benefit, not cost.**

#### The Lock Mechanism

**Problem**: Session 2 might start before Session 1 analysis completes (race condition)

**Solution**: Simple lock

```python
class SessionAnalysisLock:
    """Prevents reading memories during analysis"""

    def __init__(self):
        self.analyzing_sessions = set()  # Session IDs being analyzed

    async def wait_for_analysis(self, session_id: str):
        """Wait if previous session is still being analyzed"""
        while session_id in self.analyzing_sessions:
            await asyncio.sleep(0.5)

    def acquire(self, session_id: str):
        """Mark session as being analyzed"""
        self.analyzing_sessions.add(session_id)

    def release(self, session_id: str):
        """Mark session analysis complete"""
        self.analyzing_sessions.discard(session_id)
```

**Usage**:
```python
# Session 2 starts
previous_session_id = get_previous_session_id()
await lock.wait_for_analysis(previous_session_id)

# Now safe to read memories
memories = search_memory_facts("recent session")
```

**Typical Timing**:
- Session 1 ends: 0:00
- Background analyzer starts: 0:00
- Background analyzer finishes: 0:30-0:60
- Session 2 starts: 0:05+ (user types new prompt)
- **Result: Lock rarely blocks** (analysis finishes first)

#### Component Architecture

**1. Session Monitor (Watches for Close Events)**
```python
class SessionMonitor:
    """Watches for session close events"""

    def __init__(self):
        self.watcher = FileSystemWatcher("~/.claude/projects/")
        self.analyzer = BackgroundAnalyzer()

    async def monitor_loop(self):
        """Watch for new/modified JSONL files"""
        async for event in self.watcher.watch():
            if event.type == "file_closed" and event.path.endswith(".jsonl"):
                session_id = extract_session_id(event.path)
                await self.analyzer.queue_analysis(session_id, event.path)
```

**2. Background Analyzer (Gemini-based)**
```python
class BackgroundAnalyzer:
    """Gemini-based session analyzer"""

    def __init__(self):
        self.gemini = GeminiClient(
            model="gemini-2.0-flash-thinking",
            context_window=1_000_000
        )
        self.queue = asyncio.Queue()
        self.lock = SessionAnalysisLock()

    async def queue_analysis(self, session_id: str, log_path: str):
        """Queue session for analysis"""
        await self.queue.put((session_id, log_path))

    async def worker_loop(self):
        """Process analysis queue (runs continuously)"""
        while True:
            session_id, log_path = await self.queue.get()

            # Acquire lock
            self.lock.acquire(session_id)

            try:
                # Read JSONL log
                log_data = read_jsonl_log(log_path)

                # Analyze with Gemini (thinking mode)
                summary = await self.gemini.analyze_session(
                    log_data=log_data,
                    prompt=ANALYZER_PROMPT
                )

                # Write to Graphiti
                await graphiti.add_memory(
                    name=f"Session {session_id} Summary",
                    episode_body=summary["text"],
                    source="session_analyzer",
                    group_id=get_project_group_id(log_path)
                )

                logger.info(f"✅ Analyzed session {session_id}")

            except Exception as e:
                logger.error(f"❌ Failed to analyze session {session_id}: {e}")

            finally:
                # Always release lock
                self.lock.release(session_id)
                self.queue.task_done()
```

**3. Specialized Analyzer Prompt**
```python
ANALYZER_PROMPT = """You are a session analyzer for coding agents. Your job is to extract MEMORY-WORTHY information from session logs.

Analyze this session and extract:

1. **Errors Encountered** (env-quirk, external-api)
   - Error description
   - Root cause
   - Solution applied (if any)
   - Success/failure status
   - ✅ STORE if: Can't fix in code (env-specific, API quirks)
   - ❌ SKIP if: Bug fixed in code (now in git)

2. **User Preferences Revealed**
   - Coding style (type hints, conciseness, etc.)
   - Communication style (verbose vs concise)
   - Tool preferences (which tools they prefer)
   - ✅ STORE if: Subjective preference (varies by user)
   - ❌ SKIP if: Standard practice (not user-specific)

3. **Architectural Decisions**
   - Why certain approaches chosen
   - Why legacy code preserved
   - Historical context provided
   - ✅ STORE if: Non-obvious rationale (prevents future breakage)
   - ❌ SKIP if: Obvious from code comments

4. **Workarounds Applied**
   - Non-obvious solutions
   - Hidden knowledge
   - Tricks that worked
   - ✅ STORE if: Not documented elsewhere
   - ❌ SKIP if: Standard pattern

5. **Files Modified**
   - Key changes made
   - Purpose of changes
   - ✅ STORE if: Major refactor or architectural change
   - ❌ SKIP if: Bug fix (redundant with git)

6. **Context for Next Session**
   - PRD location (if mentioned)
   - Implementation plan location (if mentioned)
   - Next steps planned
   - Blockers identified

Use thinking mode to deeply analyze patterns. Output concise JSON:

{
  "errors": [
    {
      "description": "...",
      "solution": "...",
      "category": "env-quirk|external-api|bug-in-code",
      "should_store": true|false,
      "reason": "..."
    }
  ],
  "preferences": [...],
  "decisions": [...],
  "workarounds": [...],
  "files_modified": [...],
  "next_session_context": "...",
  "summary": "Brief 2-3 sentence summary of session"
}
"""
```

**4. MCP Integration**
```python
# mcp_server/graphiti_mcp_server.py

# Add global instances
session_monitor: SessionMonitor | None = None

async def initialize_graphiti():
    """Initialize Graphiti + Session Monitor"""
    global graphiti_client, session_monitor

    # ... existing initialization ...

    # Initialize session monitor (optional)
    if config.get("session_monitor.enabled", False):
        try:
            session_monitor = SessionMonitor(
                project_root=os.getcwd()
            )
            asyncio.create_task(session_monitor.monitor_loop())
            logger.info("✅ Session monitoring enabled")
        except Exception as e:
            logger.warning(f"⚠️  Session monitoring disabled: {e}")
```

#### Configuration

```json
// graphiti.config.json
{
  "session_monitor": {
    "enabled": false,  // Phase 1: disabled, Phase 2: enable
    "analyzer": {
      "provider": "gemini",
      "model": "gemini-2.0-flash-thinking",
      "api_key_env": "GOOGLE_API_KEY"
    },
    "watch_paths": [
      "~/.claude/projects/"
    ],
    "analysis_delay": 5  // seconds after session close before analyzing
  }
}
```

#### Drawbacks & Mitigations

**❌ Drawback 1: Token Duplication**
- Session content analyzed twice (once by client, once by analyzer)
- **Mitigation**: Gemini Flash is cheap ($0.15/1M), context caching makes it nearly free

**❌ Drawback 2: Missed Real-Time Insights**
- Client can't use insights during its own session
- **Mitigation**: Most insights apply to *next* session anyway

**❌ Drawback 3: Claude Code Specific**
- JSONL format is Claude Code specific
- **Mitigation**: Adapter pattern for other formats, fallback to Phase 1

**❌ Drawback 4: Race Condition**
- Session 2 might start before analysis completes
- **Mitigation**: Lock mechanism (already designed), rarely blocks in practice

---

## Why Graphiti > Filesystem

**User's Question**:
> "I still do not understand how graphiti benefits me at all then if it can be done locally on a file system instead."

### 1. Automatic Relationship Discovery

**Filesystem (JSON/Text):**
```
session-2025-11-03-morning.json
session-2025-11-03-afternoon.json
```
- No connections between sessions
- Manual grep to find related issues

**Graphiti (Knowledge Graph):**
```
Session A → encountered → Neo4j Timeout Error
Session B → encountered → Neo4j Timeout Error  (automatic link!)
Session C → solved → Neo4j Timeout Error → used → "Set NEO4J_TIMEOUT=60"
```
- **Automatic entity resolution**: "Neo4j Timeout Error" becomes single node
- **Pattern detection**: This error happened 3x, solution found in Session C
- **Temporal tracking**: Facts have timestamps

### 2. Semantic Search (Not Keyword Matching)

**Filesystem:**
```bash
grep -r "timeout" session-logs/
# Returns: 500 matches, you read each one
```

**Graphiti:**
```python
search_memory_facts("database connection issues", max_facts=5)
# Returns: Top 5 most relevant facts (ranked)
# - Neo4j timeout (Session C, solved)
# - FalkorDB config error (Session A, solved)
```
- **Semantic understanding**: "timeout" ≈ "connection issues" ≈ "db hangs"
- **Ranked results**: Most relevant first

### 3. Automatic Fact Invalidation

**Filesystem:**
```json
// session-2025-11-03.json
{"solution": "Set NEO4J_TIMEOUT=30"}

// session-2025-11-04.json
{"solution": "Actually need timeout=60"}
```
- Old solution is WRONG but still in logs

**Graphiti:**
```
Fact 1: "Neo4j requires timeout=30" (INVALID - superseded)
Fact 2: "Neo4j requires timeout=60" (VALID - current)
```
- Search returns only valid facts
- History preserved but not surfaced

### 4. Cross-Session Entity Tracking

**Filesystem:**
```bash
# How many times did we modify unified_config.py?
# Need custom script to grep, parse, count, deduplicate
```

**Graphiti:**
```python
search_memory_nodes("unified_config.py file")
# Returns:
# - 5 sessions modified it
# - 3 bugs found and fixed
# - Related to: Neo4j config, LLM provider, Filter system
```
- **Entity-centric view**: All activity for a file
- **Automatic aggregation**: Graph handles counting

### 5. User Preferences Accumulate

**Filesystem:**
```json
// Need to read ALL sessions to collect all preferences
session-1.json: {"pref": "dark mode"}
session-2.json: {"pref": "concise responses"}
session-3.json: {"pref": "markdown tables"}
```

**Graphiti:**
```
User Node
├─ prefers → Dark Mode
├─ prefers → Concise Responses
└─ prefers → Markdown Tables

search_memory_nodes("user preferences")
# Returns: ALL preferences in one query
```

### 6. Cross-Project Learning

**Filesystem:**
- Logs are project-scoped
- Can't share learnings

**Graphiti:**
```python
# Project A: "Always validate JWT before DB queries"
# Stored with: group_id="cross-project"

# Project B starts
search_memory_facts("authentication best practices",
                    group_ids=["cross-project", "project-b"])
# Returns: Lesson from Project A automatically!
```

### Concrete Example

**Session 1:**
```python
add_memory(
    name="Session 2025-11-03: Neo4j Integration",
    episode_body="""
    Errors: Neo4j timeout (solved: NEO4J_TIMEOUT=60)
    Files: mcp_server/graphiti_mcp_server.py
    Prefs: User prefers concise errors
    """
)
```

**Graphiti Creates (Automatic):**
```
Nodes:
- Neo4j Timeout Error (entity)
- mcp_server/graphiti_mcp_server.py (entity)
- User (entity)

Edges:
- Session → encountered → Neo4j Timeout Error
- Neo4j Timeout Error → solved_by → "NEO4J_TIMEOUT=60"
- Session → modified → graphiti_mcp_server.py
- User → prefers → Concise Error Messages

Timestamps: All facts dated 2025-11-03
```

**Session 2 (Same Error):**
```python
search_memory_facts("Neo4j timeout solutions")
# Returns: "Set NEO4J_TIMEOUT=60 (worked in Session 1)"
# Agent applies solution immediately
# Doesn't waste 20 minutes re-discovering
```

**Bottom Line**: Filesystem = dumb storage. Graphiti = intelligent memory that learns and connects.

---

## Implementation Roadmap

### Phase 1: Client-Side Summaries (IMMEDIATE)

**Goal**: Validate the concept with minimal implementation

**Tasks**:
1. Integrate token counter MCP
2. Add summary generation at threshold
3. Write summary prompt template
4. Test with real sessions
5. Measure usefulness of lazy-loaded summaries

**Success Criteria**:
- Summaries are helpful for next session
- Context window preserved (2k+ tokens)
- No significant overhead
- Positive user feedback

**Timeline**: 1-2 days

---

### Phase 2: Autonomous Background Analysis (FUTURE)

**Goal**: Zero client overhead, better analysis

**Prerequisites**:
- Phase 1 validated (summaries are useful)
- Gemini API key available
- Session monitoring is valuable

**Tasks**:
1. Build Session Monitor (file watcher)
2. Build Background Analyzer (Gemini integration)
3. Implement lock mechanism
4. Add MCP server integration
5. Test race conditions
6. Measure performance vs Phase 1

**Success Criteria**:
- Zero client overhead (no summary generation)
- Analysis completes before Session 2 starts (lock rarely blocks)
- Better quality summaries (fresh perspective)
- Cost remains negligible (<$0.01/session)

**Timeline**: 3-5 days

---

### Phase 3: Enhancements (OPTIONAL)

**Possible additions**:
1. **Multi-format support**: Cursor, Cline log formats
2. **Progressive analysis**: Analyze while session running
3. **Cross-project patterns**: Detect common issues across projects
4. **Confidence scoring**: Track solution success rates
5. **Memory consolidation**: Merge similar facts automatically
6. **Visualization**: Graph view of session relationships

---

## Key Insights from Discussion

### 1. The Paradox of Automatic Filtering

You can't have automatic memory storage without automatic event detection. But detecting memory-worthy events IS the filtering logic. It's circular.

**Implication**: Some client awareness is unavoidable. The goal is to minimize it.

### 2. Context Window Preservation > Cost Savings

The main benefit isn't cost (negligible difference between approaches) but **preserving client context window** for actual work.

**Numbers**:
- Phase 1: -2k tokens per session (summary generation)
- Phase 2: -0 tokens per session (background analysis)
- Over 10 sessions: 20k tokens saved = ~1 extra session

### 3. Session Boundaries Are Natural Breakpoints

Instead of trying to detect events within a session (complex), analyze entire session at boundaries (simple).

**Benefits**:
- Complete context
- No event boundary detection needed
- Natural summary point
- Aligns with user workflow

### 4. Graphiti's Value Is In Relationships

The graph structure provides:
- Automatic entity resolution
- Relationship discovery
- Semantic search
- Temporal fact tracking
- Cross-session/project learning

**This can't be replicated with flat files.**

### 5. Gemini 2.0 Flash Is The Secret Weapon

**Why Gemini for background analysis**:
- 1M token context window (handles long sessions)
- Thinking mode (better pattern detection)
- Free context caching (subsequent analyses nearly free)
- $0.30/1M output (cheap)
- Fast response time

**Cost**: ~$0.0003 per session (negligible)

### 6. The Lock Mechanism Is Simple

Race condition where Session 2 starts before Session 1 analysis completes is solved with:
- Simple set-based lock
- Wait loop (checks every 500ms)
- Rarely blocks in practice (analysis finishes first)

---

## Open Questions

1. **Token Threshold**: What's the optimal threshold?
   - Too low (50k): Summaries too frequent, fragmented context
   - Too high (200k): Might hit budget limit before summary
   - **Suggested**: 150k tokens (75% of typical 200k budget)

2. **Summary Granularity**: How detailed should summaries be?
   - Too detailed: Defeats purpose (context window not preserved)
   - Too concise: Miss important context
   - **Suggested**: 500-800 words (~1k tokens)

3. **Lazy Load Query**: What query to use on session startup?
   - "recent session errors" - Too narrow?
   - "recent session summary" - Too vague?
   - **Suggested**: "recent errors, solutions, and important context"

4. **Group ID Strategy**: How to scope memories?
   - Project-only: `project-graphiti:machine-desktop`
   - Project + global: `["project-graphiti", "global-learnings"]`
   - **Suggested**: Start project-only, expand to global in Phase 2

5. **Fact Invalidation**: How to mark outdated solutions?
   - Manual: Agent explicitly says "old solution was wrong"
   - Automatic: Graphiti detects conflicting facts
   - **Suggested**: Rely on Graphiti's temporal tracking

---

## Next Steps

1. **Immediate**: Implement Phase 1 (client-side summaries)
   - Token counter integration
   - Summary prompt template
   - Test with real sessions

2. **Validation**: Measure usefulness
   - Are summaries helpful for next session?
   - Is context window preserved?
   - Any overhead issues?

3. **Decision Point**: Phase 2 or iterate Phase 1?
   - If Phase 1 works well → Proceed to Phase 2
   - If Phase 1 has issues → Refine prompt, test more

4. **Phase 2 (if validated)**: Background analyzer
   - Session monitor implementation
   - Gemini integration
   - Lock mechanism
   - Performance testing

---

## Conclusion

**We've evolved from:**
- ❌ Manual `should_store()` filter (high overhead, defeats purpose)
- ❌ Real-time JSONL monitoring (complex, unsolvable event boundaries)

**To:**
- ✅ **Phase 1**: Client-side token threshold summaries (simple, testable, validates concept)
- ✅ **Phase 2**: Autonomous background analysis (zero overhead, better quality, scales)

**Key Insight**: Graphiti's value is in its graph structure (relationships, semantic search, temporal tracking), not just storage. This can't be replicated with flat files.

**Pragmatic Approach**: Start simple (Phase 1), validate concept, expand if valuable (Phase 2).

---

**End of Brainstorming Session**

**Status**: Phase 1 ready to implement
**Next Action**: Integrate token counter MCP and test client-side summaries
