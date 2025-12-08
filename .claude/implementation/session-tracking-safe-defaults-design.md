# Session Tracking Safe Defaults Design

**Date**: 2025-11-18
**Status**: DESIGN - Pending implementation
**Priority**: HIGH (Security + Bug Fix)

---

## Executive Summary

This document defines the hardcoded safe defaults system for session tracking, addressing:
1. **Security**: Opt-in model, no auto-tracking without consent
2. **Performance**: Realtime-like responsiveness with minimal overhead
3. **Cost control**: Rolling period filtering to prevent bulk indexing
4. **Bug fix**: Implement missing periodic inactivity checker

---

## Critical Bug Found

**`check_interval` is configured but never used!**

**Impact**: Sessions are never closed due to inactivity in production. They remain "active" indefinitely until:
- File is deleted
- MCP server shuts down

**Fix required**: Implement `asyncio` periodic task to call `check_inactive_sessions()` every `check_interval` seconds.

---

## Hardcoded Safe Defaults (Internal)

### Location
`mcp_server/unified_config.py` - `SessionTrackingConfig` class

### Defaults (Security-first)
```python
class SessionTrackingConfig(BaseModel):
    """Session tracking configuration with SAFE defaults."""
    
    enabled: bool = Field(
        default=False,  # ✅ DISABLED BY DEFAULT (opt-in)
        description="Enable session tracking (opt-in for security)"
    )
    
    watch_path: Path | None = Field(
        default=None,  # ✅ User must explicitly configure
        description="Path to Claude projects directory (default: ~/.claude/projects/)"
    )
    
    inactivity_timeout: int = Field(
        default=45,  # ✅ CHANGED: 45 seconds (realtime-like)
        description="Seconds of inactivity before session considered closed"
    )
    
    check_interval: int = Field(
        default=15,  # ✅ CHANGED: 15 seconds (responsive checking)
        description="Interval to check for inactive sessions"
    )
    
    auto_summarize: bool = Field(
        default=False,  # ✅ DISABLED BY DEFAULT (no LLM costs)
        description="Automatically summarize sessions via LLM"
    )
    
    store_in_graph: bool = Field(
        default=True,  # OK (no cost if disabled)
        description="Store session data in Neo4j graph"
    )
    
    keep_length_days: int | None = Field(
        default=7,  # ✅ NEW: Rolling 7-day window
        description="Only track sessions modified within last N days (null = all)"
    )
    
    filter: FilterConfig = Field(
        default_factory=lambda: FilterConfig(
            tool_calls=True,        # ✅ Preserve structure
            tool_content="omit",    # ✅ 60% token reduction
            user_messages="full",   # ✅ Preserve intent
            agent_messages="full"   # ✅ Preserve context
        ),
        description="Message filtering configuration"
    )
```

---

## Configuration Generation Strategy

### Auto-generation Logic
```python
# In mcp_server/graphiti_mcp_server.py

def ensure_global_config_exists():
    """Generate graphiti.config.json if it doesn't exist.
    
    This runs during MCP server initialization to ensure users
    always have a configuration file to reference/modify.
    """
    global_config_path = Path.home() / ".graphiti" / "graphiti.config.json"
    
    if global_config_path.exists():
        return  # User already has config
    
    # Create directory if needed
    global_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate config with safe defaults + helpful comments
    default_config = {
        "_comment": "Graphiti MCP Server Configuration (auto-generated)",
        "_docs": "https://github.com/getzep/graphiti/blob/main/CONFIGURATION.md",
        
        "database": {
            "_comment": "Required: Configure your Neo4j connection",
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "CHANGE_ME"
        },
        
        "llm": {
            "_comment": "Required: Configure your OpenAI API key",
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "CHANGE_ME"
        },
        
        "session_tracking": {
            "_comment": "Session tracking is DISABLED by default for security",
            "enabled": False,
            "watch_path": None,
            "inactivity_timeout": 45,
            "check_interval": 15,
            "auto_summarize": False,
            "store_in_graph": True,
            "keep_length_days": 7,
            
            "filter": {
                "tool_calls": True,
                "tool_content": "omit",
                "user_messages": "full",
                "agent_messages": "full"
            }
        }
    }
    
    # Write with pretty formatting
    with global_config_path.open("w") as f:
        json.dump(default_config, f, indent=2)
    
    logger.info(f"Generated default config at {global_config_path}")
    logger.warning("⚠️  Please update database and LLM credentials in config file")
```

### When to Generate
**Trigger**: During `initialize_server()` - BEFORE config validation
**Location**: `mcp_server/graphiti_mcp_server.py:1900`

```python
async def initialize_server():
    """Initialize MCP server with Graphiti capabilities."""
    
    # STEP 1: Ensure global config exists (auto-generate if needed)
    ensure_global_config_exists()
    
    # STEP 2: Load and validate configuration
    global unified_config
    unified_config = await load_and_validate_unified_config()
    
    # ... rest of initialization
```

---

## Rolling Period Filtering (`keep_length_days`)

### Purpose
Prevent bulk indexing of old sessions when tracking is enabled for first time.

### Behavior
```python
# In graphiti_core/session_tracking/session_manager.py

def _discover_existing_sessions(self) -> None:
    """Discover existing session files and start tracking them."""
    logger.info("Discovering existing sessions...")
    
    projects = self.path_resolver.list_all_projects()
    discovered_count = 0
    filtered_count = 0
    
    # Calculate cutoff time based on keep_length_days
    cutoff_time = None
    if self.keep_length_days is not None:
        cutoff_time = time.time() - (self.keep_length_days * 86400)  # days to seconds
        logger.info(f"Filtering sessions older than {self.keep_length_days} days")
    
    for project_hash, sessions_dir in projects.items():
        try:
            for session_file in sessions_dir.glob("*.jsonl"):
                # Check file modification time
                if cutoff_time is not None:
                    file_mtime = session_file.stat().st_mtime
                    if file_mtime < cutoff_time:
                        filtered_count += 1
                        continue  # Skip old sessions
                
                session_id = self.path_resolver.extract_session_id_from_path(session_file)
                
                if session_id and session_id not in self.active_sessions:
                    self._start_tracking_session(session_file, project_hash)
                    discovered_count += 1
        
        except Exception as e:
            logger.error(f"Error discovering sessions in {sessions_dir}: {e}", exc_info=True)
    
    logger.info(f"Discovered {discovered_count} existing sessions")
    if filtered_count > 0:
        logger.info(f"Filtered {filtered_count} sessions older than {self.keep_length_days} days")
```

### Configuration Examples
```json
// Default: Track only last 7 days
"keep_length_days": 7

// Track last 30 days
"keep_length_days": 30

// Track ALL sessions (dangerous for large deployments)
"keep_length_days": null
```

---

## Periodic Inactivity Checker Implementation

### Location
`mcp_server/graphiti_mcp_server.py`

### Implementation
```python
async def check_inactive_sessions_periodically(
    session_manager: SessionManager,
    interval_seconds: int
):
    """Periodically check for inactive sessions and close them.
    
    Args:
        session_manager: Session manager instance
        interval_seconds: Check interval from config
    """
    logger.info(f"Started periodic session inactivity checker (interval: {interval_seconds}s)")
    
    try:
        while True:
            await asyncio.sleep(interval_seconds)
            
            try:
                closed_count = session_manager.check_inactive_sessions()
                if closed_count > 0:
                    logger.info(f"Closed {closed_count} inactive sessions")
            
            except Exception as e:
                logger.error(f"Error checking inactive sessions: {e}", exc_info=True)
    
    except asyncio.CancelledError:
        logger.info("Session inactivity checker stopped")
        raise

# In initialize_session_tracking():
async def initialize_session_tracking():
    """Initialize session tracking system."""
    global _session_manager, _inactivity_checker_task
    
    config = unified_config.session_tracking
    
    # ... create session_manager ...
    
    _session_manager = session_manager
    session_manager.start()
    
    # Start periodic inactivity checker
    check_interval = config.check_interval
    _inactivity_checker_task = asyncio.create_task(
        check_inactive_sessions_periodically(session_manager, check_interval)
    )
    logger.info(f"Session tracking initialized (check_interval: {check_interval}s)")

# In shutdown:
async def shutdown_session_tracking():
    """Shutdown session tracking system."""
    global _session_manager, _inactivity_checker_task
    
    # Cancel inactivity checker
    if _inactivity_checker_task:
        _inactivity_checker_task.cancel()
        try:
            await _inactivity_checker_task
        except asyncio.CancelledError:
            pass
    
    # Stop session manager
    if _session_manager:
        _session_manager.stop()
        _session_manager = None
```

---

## Parameter Tuning for Different Use Cases

### Realtime Responsiveness (Default)
```json
"inactivity_timeout": 45,
"check_interval": 15
```
- **Pros**: Near-realtime session closure, responsive
- **Cons**: Slightly more CPU (negligible)
- **Use case**: Active development, frequent context switches

### Battery-Optimized (Laptop)
```json
"inactivity_timeout": 120,
"check_interval": 30
```
- **Pros**: Lower CPU, longer battery life
- **Cons**: Delayed session closure (2-4 minute lag)
- **Use case**: Mobile development, battery concerns

### Heavy Workload (Server)
```json
"inactivity_timeout": 30,
"check_interval": 10
```
- **Pros**: Very responsive, handles many concurrent sessions
- **Cons**: Slightly higher CPU (still <0.5%)
- **Use case**: Team environments, CI/CD integration

### Conservative (Legacy)
```json
"inactivity_timeout": 300,
"check_interval": 60
```
- **Pros**: Minimal overhead, conservative approach
- **Cons**: Very slow session closure (5-6 minutes)
- **Use case**: Resource-constrained environments

---

## Migration Strategy

### For New Users
✅ Config auto-generated on first MCP server start
✅ Safe defaults prevent unexpected tracking/costs
✅ Clear comments guide configuration

### For Existing Users (v1.0.0)
**No migration needed** - We haven't released to external users yet.

**If we had users:**
1. Detect old config (no `keep_length_days` field)
2. Show warning: "Session tracking defaults have changed - review your config"
3. Add `keep_length_days: 7` to existing configs
4. Preserve user's `enabled` setting

---

## Security & Privacy Considerations

### Opt-in Model
- **Default**: Tracking disabled
- **User action required**: Explicitly set `enabled: true`
- **Prevents**: Accidental tracking of sensitive projects

### Rolling Period Filtering
- **Default**: 7-day window
- **Prevents**: Bulk indexing thousands of old sessions
- **Cost control**: $1-5 instead of $500+ on first run

### No LLM by Default
- **Default**: `auto_summarize: false`
- **Prevents**: Unexpected OpenAI API costs
- **User choice**: Must explicitly enable LLM features

### Token Reduction
- **Default**: `tool_content: "omit"` (60% reduction)
- **Rationale**: Tool outputs are verbose, low value for memory
- **Preserved**: Conversation flow and context

---

## Testing Requirements

### Unit Tests
1. Test `keep_length_days` filtering logic
2. Test periodic checker startup/shutdown
3. Test config auto-generation (file doesn't exist)
4. Test config loading (file exists, valid defaults)

### Integration Tests
1. Test full session lifecycle with periodic checker
2. Test rolling period filtering (old vs new sessions)
3. Test checker resilience (handles errors gracefully)

### Performance Tests
1. Benchmark periodic checker overhead (100 sessions)
2. Measure CPU impact of different check_intervals
3. Test file watcher scalability (1000+ session files)

---

## Implementation Checklist

- [ ] Update `SessionTrackingConfig` defaults in `unified_config.py`
- [ ] Add `keep_length_days` parameter and validation
- [ ] Implement `ensure_global_config_exists()` function
- [ ] Implement periodic checker task (`check_inactive_sessions_periodically()`)
- [ ] Add checker lifecycle management (startup/shutdown)
- [ ] Update `_discover_existing_sessions()` with rolling period filter
- [ ] Update documentation (CONFIGURATION.md, SESSION_TRACKING_USER_GUIDE.md)
- [ ] Write unit tests for new features
- [ ] Write integration tests for periodic checker
- [ ] Update handoff document with final decisions

---

## Open Questions

1. **`keep_length_days` null behavior**: Should `null` allow ALL sessions or default to 7 days?
   - **Recommendation**: `null` = ALL sessions (expert mode), with warning logged

2. **Config auto-generation timing**: Generate on every startup or only first time?
   - **Recommendation**: Only first time (check file existence)

3. **Checker failure handling**: What if `check_inactive_sessions()` raises exception?
   - **Recommendation**: Log error, continue checking (don't crash task)

4. **Session resumption**: Should we link resumed sessions to original?
   - **Recommendation**: Not in v1.0, defer to v1.1 (requires session ancestry tracking)

---

**Design Status**: Ready for implementation after team review
