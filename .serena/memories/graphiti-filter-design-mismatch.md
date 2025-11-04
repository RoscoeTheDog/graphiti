# Graphiti Memory Filter: Original Plan vs Current Implementation

**Date**: 2025-11-03
**Issue**: Critical design mismatch between original plan and implementation

---

## Original Plan (IMPLEMENTATION_PLAN_LLM_FILTER.md)

### Objective 1 (Line 9):
> "**Automatic filter detection** - Determine if memory should be stored without explicit user confirmation"

### Objective 5 (Line 13):
> "**Minimal agent overhead** - Agent just calls `should_store()`, server handles filtering"

### Flow Description (Lines 41-46):
```
1. Agent calls `should_store(event_description, context)`
2. FilterManager checks session-scoped LLM
3. LLM analyzes event against filter criteria
4. Returns {"should_store": bool, "category": str, "reason": str}
5. Agent conditionally calls `add_memory()` based on response
```

### Key Problem:
**Step 5 requires Claude to manually check the response and conditionally call `add_memory()`**

This means:
- NOT automatic
- NOT minimal overhead
- Requires Claude to:
  1. Call `should_store()`
  2. Read the result
  3. Make a decision
  4. Conditionally call `add_memory()`

---

## Current Implementation

### What We Built:
- `should_store()` - Manual MCP tool that returns a decision
- `add_memory()` - Separate tool with no filtering
- No automatic integration
- No session monitoring

### The Gap:
The plan says "automatic" but the implementation is completely manual and opt-in.

---

## User's Expectation (from conversation)

> "The MCP server is supposed to monitor each session automatically leveraging an LLM to filter and identify when it meets the filter criteria"

This implies:
- **Automatic monitoring** - Server watches session activity
- **Zero Claude overhead** - No manual calls to `should_store()`
- **Integrated filtering** - Filter runs automatically when `add_memory()` is called

---

## Feasibility Analysis

### Approach 1: Integrate Filter into `add_memory()` ✅ FEASIBLE

**How it works:**
```python
@mcp.tool()
async def add_memory(
    name: str,
    episode_body: str,
    group_id: str | None = None,
    source: str = "text",
    source_description: str = "",
    skip_filter: bool = False  # Optional bypass
) -> dict:
    # Step 1: Run filter automatically (unless skip_filter=True)
    if not skip_filter and filter_manager:
        filter_result = await filter_manager.should_store(
            event_description=name,
            context=f"source={source}, body_preview={episode_body[:200]}"
        )
        
        if not filter_result["should_store"]:
            # Rejected by filter
            return {
                "status": "filtered_out",
                "reason": filter_result["reason"],
                "category": filter_result["category"]
            }
    
    # Step 2: Store if passed filter
    await graphiti_client.add_episode(...)
    return {"status": "stored", "episode_id": "..."}
```

**Pros:**
- ✅ Truly automatic
- ✅ Can't be bypassed accidentally
- ✅ Single tool call from Claude
- ✅ `should_store()` becomes optional "preview" tool
- ✅ Easy to implement

**Cons:**
- ❌ Breaking change (but we can make it opt-in with `skip_filter` param)

---

### Approach 2: Monitor JSONL Logs ❌ NOT FEASIBLE

**Why it fails:**
1. **Claude Code specific** - Won't work in Cursor, Cline, etc.
2. **Race conditions** - Async log parsing vs real-time decisions
3. **Complex parsing** - Need to interpret tool calls, results, context
4. **No control over storage** - Can't prevent `add_memory()` from being called
5. **High latency** - Monitoring loop delays vs immediate filtering

**User's insight:**
> "We could read the streamed JSONL logs for claude code, but then it wouldn't work for other agentic coding frameworks like Cursor."

Exactly right. This approach is:
- Framework-specific
- Fragile
- Doesn't prevent redundant storage (only logs it after the fact)

---

## Recommendation

**Implement Approach 1: Integrate filter into `add_memory()`**

This achieves the original objective:
- ✅ Automatic filtering
- ✅ Minimal Claude overhead (single tool call)
- ✅ Works across all MCP clients (Claude Code, Cursor, Cline, etc.)
- ✅ Can't be bypassed accidentally
- ✅ Keep `should_store()` as optional "preview" tool

---

## Action Items

1. Modify `add_memory()` to run filter automatically
2. Add `skip_filter` parameter for trusted/urgent content
3. Update CLAUDE.md to reflect automatic behavior
4. Keep `should_store()` as a "dry-run" preview tool
5. Add tests for automatic filtering

---

## Conclusion

**Original plan was ambiguous.** It said "automatic" but described a manual workflow.

**User expectation is clear:** Truly automatic monitoring with zero Claude overhead.

**Only feasible approach:** Integrate filter into `add_memory()` as the default behavior.

**Current implementation:** Completely manual, defeats the purpose of intelligent filtering.
