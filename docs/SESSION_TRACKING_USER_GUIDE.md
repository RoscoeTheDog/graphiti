# Session Tracking User Guide

## Overview

Graphiti MCP server includes automatic session tracking that captures your conversations with Claude Code and indexes them into the knowledge graph. This enables your AI assistant to remember past work, understand project context, and provide better assistance over time.

**What is Session Tracking?**

Session tracking automatically:
- Indexes conversation turns as they complete (user message + assistant response pairs)
- Preprocesses content programmatically before LLM extraction
- Extracts entities and relationships using single-pass LLM processing
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
Turn Complete (user→assistant pair)
    ↓
Preprocessor (filter noise programmatically, no LLM)
    ↓
Build context with preprocessing prompt
    ↓
Graphiti add_episode() with custom_prompt injection
    ↓
Single LLM pass: preprocessing + entity extraction
    ↓
Graph updated with entities and relationships
    ↓
Semantic Search & Context Retrieval enabled
```

### What Gets Captured

Session tracking operates on **turn-pairs** (one user message + one assistant response). Each turn-pair is captured when the next user message arrives, confirming the previous turn is complete.

**Turn-Pair Components:**
- **User message**: Full content with intent and requests
- **Assistant response**: Full text including rationale and decisions
- **Tool executions**: Commands used and their outcomes
- **Files modified**: Paths and change descriptions
- **Turn metadata**: Timing, duration, message counts

**Preprocessing Strategy:**
- **Programmatic filtering**: Noise removed before LLM processing (no cost)
- **Custom prompt injection**: Context-specific extraction instructions
- **Single-pass LLM**: Preprocessing + entity extraction in one call
- **Token efficiency**: ~13% savings vs dual-pass summarization

---

## Global Knowledge Graph (v2.0)

**New in v2.0** - Session tracking now uses a unified global knowledge graph with cross-project learning capabilities.

### What Changed in v2.0

Previously, sessions were isolated by project - knowledge from Project A was invisible when working on Project B. Starting in v2.0, all sessions are indexed to a **single global graph** with project namespace metadata embedded for provenance tracking.

**Benefits:**
- **Cross-Project Learning**: Knowledge gained in one project informs work in others
- **Pattern Recognition**: Agents learn from corrections across all your projects
- **Institutional Memory**: Solutions discovered once can be applied everywhere
- **Self-Correcting**: When you correct an agent, that correction is indexed too

### How Namespace Metadata Works

Each indexed session includes a YAML frontmatter header with provenance information:

```yaml
---
graphiti_session_metadata:
  version: "2.0"
  project_namespace: "a1b2c3d4"
  project_path: "/home/user/my-project"
  hostname: "DESKTOP-ABC123"
  indexed_at: "2025-12-08T15:30:00Z"
---
```

**Key Fields:**
- `project_namespace`: 8-character hash identifying the source project
- `project_path`: Human-readable path (optional, can be disabled for privacy)
- `hostname`: Machine identifier for multi-machine disambiguation

### How Agents Interpret Provenance

When searching the knowledge graph, agents see results from all projects along with their namespace metadata. This allows agents to:

1. **Recognize cross-project context**: "This result is from a different project (namespace: e5f6g7h8)"
2. **Weigh relevance**: Apply context appropriately based on project similarity
3. **Learn from corrections**: If a session says "X didn't work", agents avoid repeating that mistake
4. **Ask when uncertain**: Query the user if cross-project context seems inapplicable

**Example agent response:**
> "Based on a session from the `auth-service` project (namespace a1b2c3d4), JWT authentication was implemented using RS256 signing. I also found an earlier session from `old-prototype` that used HS256 but was later marked as insecure. I'll follow the RS256 approach."

### When to Use cross_project_search: false

Set `cross_project_search: false` when:
- Working on **sensitive projects** that shouldn't inform other work
- Projects have **fundamentally different architectures** that would cause confusion
- You want **complete isolation** for compliance or security reasons

```json
{
  "session_tracking": {
    "enabled": true,
    "cross_project_search": false
  }
}
```

### When to Use trusted_namespaces

Use `trusted_namespaces` to create an "allowlist" of projects whose context should be included:

```json
{
  "session_tracking": {
    "enabled": true,
    "trusted_namespaces": ["a1b2c3d4", "e5f6g7h8"]
  }
}
```

**Use cases:**
- **Exclude known-bad projects**: Projects with outdated or incorrect patterns
- **Multi-team environments**: Only trust projects from your team
- **Legacy exclusion**: Prevent old archived projects from influencing new work

**Finding your namespace hash:**
The namespace is derived from your project path. Check your indexed sessions to find the namespace for each project.

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
    "keep_length_days": 1
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

**Per Turn-Pair:**
- Average: ~$0.03 - $0.10 per turn
- Varies based on: Turn content length, tool usage, complexity
- Components:
  - Programmatic preprocessing: Free (no LLM)
  - Entity extraction: ~$0.03 - $0.10 (OpenAI gpt-4o-mini, single-pass)
  - Embedding generation: Negligible cost

**Session Estimates** (typical 10-20 turns per session):
- Short session (5-10 turns): ~$0.15 - $0.50
- Medium session (10-20 turns): ~$0.30 - $1.00
- Long session (20+ turns): ~$0.60 - $2.00+

**Monthly Estimate:**
- Light usage (10 sessions/month, ~15 turns avg): ~$3.00 - $7.00/month
- Regular usage (50 sessions/month, ~15 turns avg): ~$15.00 - $35.00/month
- Heavy usage (100 sessions/month, ~15 turns avg): ~$30.00 - $70.00/month

**Note**: Turn-based indexing provides real-time context at the cost of more frequent LLM calls compared to session-based batching. The single-pass architecture saves ~13% per turn vs dual-pass summarization.

### Cost Optimization Tips

1. **Leverage Programmatic Preprocessing**: Built-in filters remove noise before LLM (no cost)
2. **Use Default Extraction Templates**: Optimized prompts for session content
3. **Configure Rolling Window**: Use `keep_length_days` to limit historical indexing
4. **Monitor Turn Frequency**: Long conversations with many turns cost more
5. **Disable for Testing**: Turn off tracking for experimental/throwaway sessions


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

**v2.0 (Global Scope)**:
- Format: `{hostname}__global`
- Example: `devmachine__global`
- All projects share a single global group ID
- Project isolation via `project_namespace` metadata in episodes
- Cross-project learning enabled by default

**v1.x (Project Scope - Legacy)**:
- Format: `{hostname}__{project_hash}`
- Example: `devmachine__a1b2c3d4`
- Each project had its own isolated group ID
- No cross-project learning

**Note**: v2.0 uses global group IDs with namespace tagging for provenance. Project-specific group IDs from v1.x won't be searched by default. See the Migration Guide for options.

---

## Privacy & Security

### What's Safe

✅ Session content stored locally in your Neo4j database
✅ No data sent to third parties (except OpenAI for entity extraction)
✅ Full control over what gets tracked (opt-in by default)
✅ Namespace metadata enables filtering when needed
✅ Project paths can be redacted (`include_project_path: false`)

### Security Considerations (v2.0 Global Scope)

**Project Path Exposure:**
- By default, `project_path` is included in episode metadata
- This reveals your directory structure to anyone with graph access
- **Mitigation**: Set `include_project_path: false` if paths contain sensitive information

**Cross-Project Information Leakage:**
- With `cross_project_search: true` (default), information from any project can appear in searches
- Sensitive work patterns from Project A may surface when working on Project B
- **Mitigations**:
  - Set `cross_project_search: false` for sensitive projects
  - Use `trusted_namespaces` to exclude specific projects
  - Use session filtering to reduce stored content

**Multi-User Environments:**
- On shared machines, users might see each other's project data if sharing Neo4j
- Session files are in user-specific `~/.claude/` directory (private)
- Global group_id includes hostname (not shared across machines)
- **For shared Neo4j**: Use separate databases or group_id prefixes per user

### Best Practices

1. **Review Sensitive Sessions**: Disable tracking when working with credentials
2. **Use Environment Variables**: Never hardcode secrets in session content
3. **Regular Cleanup**: Delete old/sensitive episodes when no longer needed
4. **Audit Configuration**: Periodically review `graphiti.config.json`
5. **Isolate Sensitive Projects**: Use `cross_project_search: false` for compliance-sensitive work
6. **Hide Paths When Needed**: Set `include_project_path: false` for projects with sensitive directory structures

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
A: Yes! In v2.0, cross-project search is enabled by default. All projects are indexed to a single global graph with namespace metadata for provenance. Set `cross_project_search: false` to disable, or use `trusted_namespaces` to limit which projects are included.

**Q: How do I prevent a project's context from affecting other projects?**
A: Two options:
1. Set `cross_project_search: false` in that project's config (isolates it completely)
2. Add the project's namespace to other projects' `trusted_namespaces` exclusion (blocks it from searches)

**Q: Will cross-project search give me incorrect context?**
A: The namespace metadata helps agents weigh relevance appropriately. Agents can see which project context came from and apply it judiciously. When you correct an agent, that correction is also indexed, creating a self-correcting system.

**Q: How do I find a project's namespace hash?**
A: The namespace is an 8-character hex hash derived from the project path. Check indexed sessions for your project to find its namespace in the `project_namespace` field.

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

---

**Last Updated:** 2025-12-20