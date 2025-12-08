# Session Tracking User Guide

## Overview

Graphiti MCP server includes automatic session tracking that captures your conversations with Claude Code and indexes them into the knowledge graph. This enables your AI assistant to remember past work, understand project context, and provide better assistance over time.

**What is Session Tracking?**

Session tracking automatically:
- Monitors your Claude Code conversation files (`~/.claude/projects/{hash}/sessions/*.jsonl`)
- Filters and processes conversation content (93% token reduction)
- Indexes sessions into Graphiti's knowledge graph
- Links related sessions for context continuity
- Enables semantic search across past work

**Key Benefits:**

✅ **Cross-Session Memory** - Claude remembers what you worked on previously
✅ **Decision Tracking** - Understand why choices were made in past sessions  
✅ **Pattern Recognition** - Learn from repeated tasks and solutions
✅ **Cost-Effective** - ~$0.17 per session with smart filtering
✅ **Automatic** - No manual intervention required once enabled

---

## Quick Start

### Prerequisites

- Graphiti MCP server installed (v0.4.0+)
- Neo4j database configured
- OpenAI API key configured (for entity extraction)

### Enabling Session Tracking

Session tracking is **disabled by default** for security and privacy (opt-in model). You must explicitly enable it.


**Enable globally:**
```bash
graphiti-mcp-session-tracking enable
```

**Check status:**
```bash
graphiti-mcp-session-tracking status
```

### Disabling Session Tracking

If you want to disable session tracking after enabling:

```bash
# Disable globally
graphiti-mcp-session-tracking disable

```

---

## How It Works

### Architecture Flow

```
Claude Code Session
    ↓ (writes to)
~/.claude/projects/{hash}/sessions/{session-id}.jsonl
    ↓ (monitored by)
Graphiti MCP Server - File Watcher
    ↓ (processes)
JSONL Parser + Smart Filter (93% token reduction)
    ↓ (indexes to)
Graphiti Knowledge Graph
    ↓ (enables)
Semantic Search & Context Retrieval
```

### What Gets Captured

**Included:**
- User messages (full content)
- Assistant responses (full text)
- Tool calls (structure, no outputs)
- MCP tools used
- Files modified
- Session timing and metadata

**Excluded (for token efficiency):**
- Tool result outputs (replaced with 1-line summaries)
- Large file contents
- Redundant system messages

---

## Configuration

### Global Settings

Session tracking configuration is stored in `graphiti.config.json`:

```json
{
  "session_tracking": {
    "enabled": false,
    "watch_path": null,
    "inactivity_timeout": 900,
    "check_interval": 60,
    "auto_summarize": false,
    "keep_length_days": 7
  }
}
```

**Configuration Options:**

- `enabled` - Enable/disable session tracking (default: `false`)
- `watch_path` - Directories to monitor for JSONL files
- `inactivity_timeout` - Seconds of inactivity before session is considered closed (default: 900)
- `check_interval` - How often to check for file changes in seconds (default: 60)

### Checking Status

Session tracking is controlled via configuration (`graphiti.config.json`). Use the status tool to check current state:

**Check status:**
```json
// MCP tool call
{
  "tool": "session_tracking_status"
}
```

> **Note**: Session tracking control is configuration-based only. To enable/disable tracking,
> modify `graphiti.config.json -> session_tracking.enabled` and restart the MCP server.

---

## Cost Management

### Expected Costs

**Per Session:**
- Average: $0.17 per session
- Range: $0.03 - $0.50 depending on session length
- Components:
  - Token filtering: 93% reduction (free)
  - Entity extraction: ~$0.17 (OpenAI gpt-4o-mini)

**Monthly Estimate:**
- Light usage (10 sessions/month): ~$1.70/month
- Regular usage (50 sessions/month): ~$8.50/month
- Heavy usage (100 sessions/month): ~$17.00/month

### Cost Optimization Tips

1. **Use Default Filtering**: The built-in smart filter reduces tokens by 93%
2. **Session Cleanup**: Archive old sessions you don't need indexed
3. **Opt-Out When Not Needed**: Disable tracking for experimental/test sessions
4. **Monitor Usage**: Check token usage in session metadata


### Manual Sync Command

Manual session sync is a two-step process for safety:

1. **Preview** (via MCP tool or CLI): See what would be indexed
2. **Execute** (via CLI only): Perform actual indexing

#### Step 1: Preview Sessions (MCP Tool or CLI)

The `session_tracking_sync_history` MCP tool provides a **read-only preview**:

```python
# Via MCP tool - always preview only
session_tracking_sync_history()           # Preview last 7 days
session_tracking_sync_history(days=30)    # Preview last 30 days
```

Or use the CLI for preview:
```bash
graphiti-mcp session-tracking sync --days 7    # Preview (default)
```

#### Step 2: Execute Sync (CLI Only)

To actually index sessions, use the CLI with `--no-dry-run`:

```bash
# Actually sync last 7 days
graphiti-mcp session-tracking sync --no-dry-run

# Sync specific date range
graphiti-mcp session-tracking sync --days 30 --no-dry-run

# Sync ALL sessions (requires confirmation)
graphiti-mcp session-tracking sync --days 0 --no-dry-run --confirm
```

> **Why CLI Only?** The MCP tool is intentionally read-only to prevent AI assistants from accidentally triggering expensive sync operations. Actual sync requires explicit user action via CLI.

**Use Cases:**
- Migrate pre-existing sessions from earlier versions
- Re-index sessions after configuration changes
- Recover from indexing failures

**Cost Warning:**

⚠️ **`--days 0` can be very expensive!** This syncs ALL unindexed sessions in your history. For large backlogs, this can cost $10-$50+ in API fees.

**Recommendations:**
- Always preview first (MCP tool or CLI without `--no-dry-run`)
- Start with small date ranges (7-30 days)
- Monitor costs in OpenAI dashboard
- Use `keep_length_days` config to limit retention (see Configuration section)

---

## Querying Session History

### Using Graphiti MCP Tools

**Search for past sessions:**
```json
{
  "tool": "search_memory_nodes",
  "arguments": {
    "query": "authentication implementation",
    "group_ids": ["your-project-group-id"],
    "max_nodes": 10
  }
}
```

**Find specific relationships:**
```json
{
  "tool": "search_memory_facts",
  "arguments": {
    "query": "why did we choose approach X",
    "group_ids": ["your-project-group-id"],
    "max_facts": 10
  }
}
```

**Get recent sessions:**
```json
{
  "tool": "get_episodes",
  "arguments": {
    "group_id": "your-project-group-id",
    "last_n": 10
  }
}
```

### Understanding Group IDs

Group IDs isolate sessions by project:
- Format: `{hostname}__{project_hash}`
- Example: `devmachine__a1b2c3d4`
- Automatically calculated from project directory path
- Ensures cross-session context stays project-specific

---

## Privacy & Security

### What's Safe

✅ Session content stored locally in your Neo4j database
✅ No data sent to third parties (except OpenAI for entity extraction)
✅ Full control over what gets tracked (opt-in by default)
✅ Group isolation prevents cross-project data leakage

### Best Practices

1. **Review Sensitive Sessions**: Disable tracking when working with credentials
2. **Use Environment Variables**: Never hardcode secrets in session content
3. **Regular Cleanup**: Delete old/sensitive episodes when no longer needed
4. **Audit Configuration**: Periodically review `graphiti.config.json`

### Deleting Session Data

**Delete a specific episode:**
```json
{
  "tool": "delete_episode",
  "arguments": {
    "uuid": "episode-uuid-here"
  }
}
```

**Clear all data (nuclear option):**
```json
{
  "tool": "clear_graph"
}
```

⚠️ **Warning**: `clear_graph` deletes ALL knowledge graph data, not just sessions!

---

## Troubleshooting

### Sessions Not Being Tracked

**Check 1: Verify tracking is enabled**
```bash
graphiti-mcp-session-tracking status
```

**Check 2: Verify MCP server is running**
```bash
# Check process
ps aux | grep graphiti

# Check logs
tail -f ~/.local/state/graphiti/logs/mcp-server.log
```

**Check 3: Verify file watcher is active**
```bash
# Look for watcher logs
grep "SessionFileWatcher" ~/.local/state/graphiti/logs/mcp-server.log
```

### High Costs

**Problem**: Session indexing costs more than expected

**Solutions**:
1. Verify smart filtering is enabled (should be automatic)
2. Check OpenAI API key is using correct model (gpt-4o-mini)
3. Review session length - very long sessions cost more
4. Consider opting out for experimental work

### Missing Session Context

**Problem**: Claude doesn't remember past work

**Solutions**:
1. Verify sessions are being indexed (check `get_episodes`)
2. Check group ID matches between sessions
3. Ensure MCP server has been running continuously
4. Query with more specific terms

### File Watcher Not Detecting Changes

**Problem**: New session files not being processed

**Solutions**:
1. Check watch directory configuration in `graphiti.config.json`
2. Verify permissions on `~/.claude/projects/` directory
3. Check `check_interval` setting (default: 60 seconds)
4. Restart MCP server if watcher is stuck

## FAQ

**Q: Does session tracking slow down Claude Code?**
A: No. File watching runs in background, with minimal overhead (<5%).

**Q: Can I track sessions retroactively?**
A: Yes! Use a two-step process:
1. **Preview**: Use the `session_tracking_sync_history` MCP tool to see available sessions
2. **Sync**: Use CLI command `graphiti-mcp session-tracking sync --no-dry-run` to actually index

The MCP tool is read-only (preview only) for safety. See [MCP_TOOLS.md](MCP_TOOLS.md#session_tracking_sync_history) for details.

**Q: What happens if I delete a JSONL file?**
A: The episode remains in the graph. Delete episodes explicitly via MCP tools.

**Q: Can I export session data?**
A: Yes. Use `HandoffExporter` to generate markdown files from episodes.

**Q: Is session linking automatic?**
A: Yes. Sequential sessions in the same project are automatically linked via `previous_episode_uuid`.

**Q: What's the difference between nodes and facts?**
A: Nodes are entities (files, tools, patterns). Facts are relationships between entities.

**Q: Can I search across multiple projects?**
A: Yes. Provide multiple group IDs in `search_memory_nodes` or `search_memory_facts`.

---

## Advanced Usage

### Custom Filtering (Developer Extension)

Session filtering is implemented in `graphiti_core/session_tracking/filter.py`. Advanced users can extend filtering rules:

```python
from graphiti_core.session_tracking import SessionFilter

# Custom filter extension
filter = SessionFilter()
custom_filtered = filter.filter_messages(messages, custom_rules={
    "keep_tool_outputs": ["Read", "Grep"],  # Customize
    "summarize_tools": ["Bash", "Write"]
})
```

### Manual Episode Addition

You can manually add episodes without session tracking:

```python
from graphiti_core.session_tracking import SessionIndexer

indexer = SessionIndexer(graphiti_instance)
episode_uuid = await indexer.index_session(
    session_id="manual-session-1",
    filtered_content="Session content here...",
    group_id="hostname__hash",
    session_number=1
)
```

### Handoff Export (Optional)

Generate markdown handoff files for human review:

```python
from graphiti_core.session_tracking import HandoffExporter

exporter = HandoffExporter(graphiti_instance)
markdown = await exporter.export_handoff(
    episode_uuid="uuid-here",
    output_path=".claude/handoff/session-123.md"
)
```

---

## Support

**Documentation:**
- Developer Guide: `docs/SESSION_TRACKING_DEV_GUIDE.md`
- Troubleshooting: `docs/SESSION_TRACKING_TROUBLESHOOTING.md`
- Configuration Reference: `CONFIGURATION.md`

**Community:**
- GitHub Issues: https://github.com/getzep/graphiti/issues
- Discord: https://discord.com/invite/W8Kw6bsgXQ

**Feedback:**

Session tracking is a new feature (v0.4.0). We welcome feedback and bug reports!