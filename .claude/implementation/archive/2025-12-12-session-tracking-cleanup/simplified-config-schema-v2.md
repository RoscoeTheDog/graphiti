# Simplified Configuration Schema v2

**Purpose**: Radically simplified filter configuration using true/false/template pattern instead of enum-based modes.

---

## Design Philosophy

**Before (Complex)**:
- Enum values: `"full"`, `"summary"`, `"omit"`
- Separate `SummaryPromptsConfig` dictionary
- Mapping layer between keywords and behavior

**After (Simple)**:
- `true` = capture everything
- `false` = capture nothing
- `string` = template path OR inline prompt

**Benefits**:
- Intuitive: boolean for on/off, string for "how"
- No keyword confusion (`"summary"` → what kind of summary?)
- Direct template specification (no indirection)
- Fewer concepts to learn

---

## Simplified Filter Schema

### Configuration Definition

```python
class FilterConfig(BaseModel):
    """Simplified filtering configuration.
    
    Each field accepts:
    - true: Capture full content (no filtering)
    - false: Omit content entirely (structure only)
    - str: Path to .md template OR inline prompt string
    
    Templates use variables: {content}, {context}, {max_chars}
    """
    
    tool_calls: bool = Field(
        default=True,
        description="Preserve tool call structure (names, parameters). Recommended: true"
    )
    
    tool_content: bool | str = Field(
        default="default_tool_content.md",
        description=(
            "Tool result filtering:\n"
            "  true = full content\n"
            "  false = omit entirely\n"
            "  'path/to/template.md' = use template\n"
            "  'inline prompt...' = use string as prompt"
        )
    )
    
    user_messages: bool | str = Field(
        default=True,
        description=(
            "User message filtering:\n"
            "  true = full content\n"
            "  false = omit entirely\n"
            "  'path/to/template.md' = use template\n"
            "  'inline prompt...' = use string as prompt"
        )
    )
    
    agent_messages: bool | str = Field(
        default=True,
        description=(
            "Agent response filtering:\n"
            "  true = full content\n"
            "  false = omit entirely\n"
            "  'path/to/template.md' = use template\n"
            "  'inline prompt...' = use string as prompt"
        )
    )
    
    max_summary_chars: int = Field(
        default=500,
        description="Maximum characters for summaries (used in {max_chars} template variable)"
    )
```

---

## Type Resolution Logic

```python
def resolve_filter_value(value: bool | str) -> FilterMode:
    """Resolve filter value to processing mode.
    
    Args:
        value: Config value (bool or str)
    
    Returns:
        FilterMode enum: FULL, OMIT, or TEMPLATE
    """
    if isinstance(value, bool):
        return FilterMode.FULL if value else FilterMode.OMIT
    
    # String = template path or inline prompt
    return FilterMode.TEMPLATE

class FilterMode(Enum):
    """Internal processing mode (not exposed to user)."""
    FULL = "full"
    OMIT = "omit"
    TEMPLATE = "template"
```

---

## Template Resolution (Same as Before)

```python
def resolve_template(value: str, message_type: str) -> str:
    """Resolve template from string value.
    
    Args:
        value: Template path or inline prompt
        message_type: "tool_content", "user_messages", or "agent_messages"
    
    Returns:
        Resolved prompt template string
    
    Resolution order:
        1. If starts with "default_" -> load from built-in templates
        2. If file exists (absolute or relative to ~/.graphiti/) -> load file
        3. Otherwise -> treat as inline prompt string
    """
    # Built-in template
    if value.startswith("default_"):
        builtin_path = Path(__file__).parent / "prompts" / value
        if builtin_path.exists():
            return builtin_path.read_text()
    
    # Try as file path
    path = Path(value)
    if not path.is_absolute():
        path = Path.home() / ".graphiti" / "prompts" / value
    
    if path.exists():
        return path.read_text()
    
    # Treat as inline prompt
    return value
```

---

## Configuration Examples

### Example 1: Safe Defaults (Auto-generated)
```json
{
  "filter": {
    "tool_calls": true,
    "tool_content": "default_tool_content.md",
    "user_messages": true,
    "agent_messages": true,
    "max_summary_chars": 500
  }
}
```

**Behavior**:
- Tools: Summarized using built-in template (~35% reduction)
- Users: Full content preserved
- Agent: Full content preserved

---

### Example 2: Maximum Token Reduction
```json
{
  "filter": {
    "tool_calls": true,
    "tool_content": false,
    "user_messages": true,
    "agent_messages": false,
    "max_summary_chars": 500
  }
}
```

**Behavior**:
- Tools: Omitted entirely (~60% reduction)
- Users: Full content preserved
- Agent: Omitted entirely (~85% total reduction)

---

### Example 3: Custom Inline Prompt
```json
{
  "filter": {
    "tool_calls": true,
    "tool_content": "Summarize this tool result in 2-3 sentences focusing on key findings: {content}",
    "user_messages": true,
    "agent_messages": true,
    "max_summary_chars": 300
  }
}
```

**Behavior**:
- Tools: Summarized using inline prompt
- Users: Full content
- Agent: Full content

---

### Example 4: Custom Template Files
```json
{
  "filter": {
    "tool_calls": true,
    "tool_content": "~/.graphiti/prompts/brief_tool_summary.md",
    "user_messages": "~/.graphiti/prompts/preserve_user_intent.md",
    "agent_messages": "~/.graphiti/prompts/detailed_agent_reasoning.md",
    "max_summary_chars": 800
  }
}
```

**Behavior**: All three message types use custom templates

---

### Example 5: No Filtering (Full Preservation)
```json
{
  "filter": {
    "tool_calls": true,
    "tool_content": true,
    "user_messages": true,
    "agent_messages": true
  }
}
```

**Behavior**: Everything preserved (0% reduction, archival mode)

---

## Built-in Template Files

**Location**: `graphiti_core/session_tracking/prompts/`

**Files**:
- `default_tool_content.md`
- `default_user_messages.md` (optional, if we add user message summarization later)
- `default_agent_messages.md` (optional, if we add agent summarization later)

**Example: `default_tool_content.md`**:
```markdown
Summarize this tool result in 1 paragraph (max {max_chars} characters).

**Tool**: {context}

**Focus on**:
- What operation was performed
- Key findings or outputs
- Errors/warnings
- Relevant file paths or data values

**Content**:
{content}

**Summary** (1 paragraph):
```

---

## Manual Sync Command for Historical Sessions

### Purpose
Allow users to manually sync old session files to build/update the graph when:
- Tracking was previously disabled
- User wants to index historical sessions
- Recovering from database loss

### MCP Tool: `session_tracking_sync_history`

```python
@mcp.tool()
async def session_tracking_sync_history(
    project_path: str | None = None,
    keep_length_days: int | None = 7,
    dry_run: bool = False,
    max_sessions: int | None = 100
) -> dict:
    """Manually sync historical session files to Graphiti graph.
    
    Args:
        project_path: Path to specific project (null = all projects in watch_path)
        keep_length_days: Only sync sessions modified within last N days (null = all)
        dry_run: Preview what would be synced without actually indexing
        max_sessions: Maximum sessions to sync (safety limit, null = unlimited)
    
    Returns:
        {
            "preview": bool,
            "sessions_found": int,
            "sessions_filtered": int,
            "sessions_to_sync": int,
            "estimated_cost": float (in USD),
            "sessions": [{"path": str, "modified": str, "size_kb": float}],
            "message": str
        }
    
    Examples:
        # Preview sync for last 7 days
        session_tracking_sync_history(dry_run=true)
        
        # Sync specific project, last 30 days
        session_tracking_sync_history(
            project_path="/home/user/my-project",
            keep_length_days=30
        )
        
        # Sync all historical sessions (CAUTION)
        session_tracking_sync_history(
            keep_length_days=null,
            max_sessions=null
        )
    """
    # Implementation below
```

### Implementation

```python
async def session_tracking_sync_history(
    project_path: str | None = None,
    keep_length_days: int | None = 7,
    dry_run: bool = False,
    max_sessions: int | None = 100
) -> dict:
    """Manually sync historical sessions."""
    
    if not unified_config.session_tracking.enabled:
        return {
            "error": "Session tracking is disabled in configuration",
            "message": "Enable session tracking first: session_tracking.enabled = true"
        }
    
    # Get path resolver
    path_resolver = ClaudePathResolver(
        watch_path=unified_config.session_tracking.watch_path
    )
    
    # Discover sessions
    if project_path:
        # Specific project
        project_hash = path_resolver.resolve_project_hash(Path(project_path))
        sessions_dir = path_resolver.get_sessions_dir_for_project(project_hash)
        projects = {project_hash: sessions_dir}
    else:
        # All projects in watch_path
        projects = path_resolver.list_all_projects()
    
    # Filter by modification time
    cutoff_time = None
    if keep_length_days is not None:
        cutoff_time = time.time() - (keep_length_days * 86400)
    
    sessions_found = []
    sessions_filtered = 0
    
    for project_hash, sessions_dir in projects.items():
        for session_file in sessions_dir.glob("*.jsonl"):
            # Check modification time
            file_mtime = session_file.stat().st_mtime
            
            if cutoff_time and file_mtime < cutoff_time:
                sessions_filtered += 1
                continue
            
            sessions_found.append({
                "path": str(session_file),
                "modified": datetime.fromtimestamp(file_mtime).isoformat(),
                "size_kb": session_file.stat().st_size / 1024,
                "project_hash": project_hash
            })
    
    # Sort by modification time (newest first)
    sessions_found.sort(key=lambda s: s["modified"], reverse=True)
    
    # Apply max_sessions limit
    sessions_to_sync = sessions_found[:max_sessions] if max_sessions else sessions_found
    
    # Estimate cost (rough)
    total_size_kb = sum(s["size_kb"] for s in sessions_to_sync)
    estimated_tokens = total_size_kb * 250  # ~250 tokens per KB
    estimated_cost = (estimated_tokens / 1_000_000) * 0.50  # $0.50 per 1M tokens (rough)
    
    result = {
        "preview": dry_run,
        "sessions_found": len(sessions_found),
        "sessions_filtered": sessions_filtered,
        "sessions_to_sync": len(sessions_to_sync),
        "estimated_cost": round(estimated_cost, 2),
        "sessions": sessions_to_sync[:10],  # First 10 for preview
        "message": ""
    }
    
    if dry_run:
        result["message"] = (
            f"Would sync {len(sessions_to_sync)} sessions "
            f"(estimated cost: ${estimated_cost:.2f}). "
            f"Run with dry_run=false to proceed."
        )
        return result
    
    # Actually sync sessions
    if not _session_manager:
        result["error"] = "Session manager not initialized"
        return result
    
    synced_count = 0
    for session_info in sessions_to_sync:
        try:
            session_file = Path(session_info["path"])
            project_hash = session_info["project_hash"]
            
            # Parse and index session
            # (Reuse existing _close_session logic but for historical files)
            await _index_historical_session(session_file, project_hash)
            synced_count += 1
            
        except Exception as e:
            logger.error(f"Failed to sync {session_file}: {e}", exc_info=True)
    
    result["message"] = (
        f"Synced {synced_count}/{len(sessions_to_sync)} sessions successfully. "
        f"Actual cost: ${estimated_cost:.2f} (estimated)."
    )
    
    return result
```

---

### CLI Command: `graphiti-mcp session-sync`

```bash
# Preview sync for last 7 days (safe default)
graphiti-mcp session-sync --dry-run

# Sync specific project, last 30 days
graphiti-mcp session-sync \
    --project /home/user/my-project \
    --days 30

# Sync all projects, last 14 days, limit 50 sessions
graphiti-mcp session-sync \
    --days 14 \
    --max-sessions 50

# Sync ALL historical sessions (DANGEROUS - confirm prompt required)
graphiti-mcp session-sync \
    --days 0 \
    --max-sessions 0 \
    --confirm
```

**CLI Implementation** (`mcp_server/session_tracking_cli.py`):
```python
@session_tracking_cli.command("sync")
def sync_history(
    project: str | None = None,
    days: int = 7,
    max_sessions: int = 100,
    dry_run: bool = False,
    confirm: bool = False
):
    """Manually sync historical session files to graph.
    
    Examples:
        # Preview sync
        graphiti-mcp session-tracking sync --dry-run
        
        # Sync last 30 days
        graphiti-mcp session-tracking sync --days 30
        
        # Sync all (requires confirmation)
        graphiti-mcp session-tracking sync --days 0 --max-sessions 0 --confirm
    """
    # Call MCP tool via async runner
    result = asyncio.run(
        session_tracking_sync_history(
            project_path=project,
            keep_length_days=days if days > 0 else None,
            dry_run=dry_run,
            max_sessions=max_sessions if max_sessions > 0 else None
        )
    )
    
    # Display results
    print(f"\n{'=' * 60}")
    print(f"Session Sync Report")
    print(f"{'=' * 60}")
    print(f"Sessions found:     {result['sessions_found']}")
    print(f"Sessions filtered:  {result['sessions_filtered']}")
    print(f"Sessions to sync:   {result['sessions_to_sync']}")
    print(f"Estimated cost:     ${result['estimated_cost']:.2f}")
    print(f"\n{result['message']}")
    
    if dry_run:
        print(f"\nℹ️  This was a dry run. Use --no-dry-run to actually sync.")
    
    # Show sample sessions
    if result['sessions']:
        print(f"\nSample sessions (first 10):")
        for session in result['sessions'][:10]:
            print(f"  - {session['path']} ({session['size_kb']:.1f} KB, {session['modified']})")
```

---

## Use Case: Manual Sync After Enabling Tracking

**Scenario**: User had tracking disabled for months, now wants to build historical graph.

**Workflow**:
```bash
# 1. Enable tracking in config
vim ~/.graphiti/graphiti.config.json
# Set: "enabled": true

# 2. Preview what would be synced (last 7 days safe default)
graphiti-mcp session-tracking sync --dry-run

# Output:
# =========================================================
# Session Sync Report
# =========================================================
# Sessions found:     45
# Sessions filtered:  123 (older than 7 days)
# Sessions to sync:   45
# Estimated cost:     $2.25
# 
# Would sync 45 sessions (estimated cost: $2.25). Run with --no-dry-run to proceed.

# 3. Adjust time window if needed
graphiti-mcp session-tracking sync --days 30 --dry-run

# 4. Actually sync
graphiti-mcp session-tracking sync --days 7

# 5. Resume normal tracking (file watcher picks up new sessions automatically)
```

---

## Relationship: `keep_length_days` vs Manual Sync

### `keep_length_days` (Config)
- **Purpose**: Filter sessions during normal file watcher discovery
- **When used**: MCP server startup, when `_discover_existing_sessions()` runs
- **Prevents**: Automatic bulk indexing of old sessions on first run
- **Default**: 7 days (rolling window)

### `session_tracking_sync_history` (Manual)
- **Purpose**: Intentional bulk sync of historical sessions
- **When used**: User explicitly requests to index old data
- **Requires**: User confirmation (dry-run shows cost estimate)
- **Default**: 7 days (safe), but user can override

**Both use the same filtering logic, but different triggers**:
- `keep_length_days`: Automatic, passive, background
- `sync_history`: Manual, active, foreground

---

## Updated Configuration Schema (Final)

```json
{
  "session_tracking": {
    "enabled": false,
    "watch_path": null,
    "inactivity_timeout": 45,
    "check_interval": 15,
    "auto_summarize": false,
    "store_in_graph": true,
    "keep_length_days": 7,
    
    "filter": {
      "tool_calls": true,
      "tool_content": "default_tool_content.md",
      "user_messages": true,
      "agent_messages": true,
      "max_summary_chars": 500
    }
  }
}
```

**Key changes**:
- ✅ `tool_content`: `"summary"` → `"default_tool_content.md"`
- ✅ Removed `SummaryPromptsConfig` (redundant)
- ✅ Simplified: `bool | str` instead of enum
- ✅ Direct template specification (no keyword mapping)

---

## Migration from Old Schema

### Old Config (v1)
```json
{
  "filter": {
    "tool_content": "summary"
  }
}
```

### New Config (v2)
```json
{
  "filter": {
    "tool_content": "default_tool_content.md"
  }
}
```

**Migration logic**:
```python
def migrate_filter_config(old_config: dict) -> dict:
    """Migrate old enum-based config to new bool|str config."""
    filter_config = old_config.get("filter", {})
    
    # Map old enum values to new values
    mapping = {
        "full": True,
        "omit": False,
        "summary": "default_tool_content.md"  # Default template
    }
    
    for field in ["tool_content", "user_messages", "agent_messages"]:
        old_value = filter_config.get(field)
        if old_value in mapping:
            filter_config[field] = mapping[old_value]
    
    return old_config
```

---

## Implementation Checklist

- [ ] Update `FilterConfig` to use `bool | str` type
- [ ] Remove `ContentMode` enum (internal `FilterMode` only)
- [ ] Implement `resolve_filter_value()` function
- [ ] Update `resolve_template()` to handle `default_` prefix
- [ ] Create `default_tool_content.md` template
- [ ] Implement `session_tracking_sync_history` MCP tool
- [ ] Add CLI command `graphiti-mcp session-tracking sync`
- [ ] Update config auto-generation with new defaults
- [ ] Write migration logic for old configs
- [ ] Update documentation (CONFIGURATION.md, user guide)
- [ ] Write tests for new filter resolution logic
- [ ] Write tests for manual sync command

---

**Design Status**: Ready for implementation
**Breaking Change**: Yes (enum → bool|str), but migration provided
