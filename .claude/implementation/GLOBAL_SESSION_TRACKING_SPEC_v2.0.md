# Global Session Tracking with Namespace Tagging - Specification v2.0

**Version**: 2.0.0-draft
**Status**: Design Specification
**Authors**: Human + Claude Agent
**Date**: 2025-12-08
**Supersedes**: Session Tracking v1.0.0 (project-scoped design)

---

## Executive Summary

This specification defines a fundamental architectural change to Graphiti's session tracking system: migrating from **project-scoped isolation** to **global indexing with namespace tagging**. This enables cross-project knowledge sharing while preserving provenance tracking and providing mechanisms to filter potentially incorrect context.

### Key Changes
- Single global knowledge graph instead of per-project isolation
- Project namespace metadata embedded in all indexed episodes
- Cross-project search enabled by default with optional filtering
- Simplified configuration (global-only, no project-scope option)

---

## Table of Contents

1. [Design Rationale](#1-design-rationale)
2. [Architecture Overview](#2-architecture-overview)
3. [Configuration Schema](#3-configuration-schema)
4. [Episode Metadata Structure](#4-episode-metadata-structure)
5. [Search Behavior](#5-search-behavior)
6. [Implementation Requirements](#6-implementation-requirements)
7. [Migration Guide](#7-migration-guide)
8. [Security Considerations](#8-security-considerations)
9. [Testing Requirements](#9-testing-requirements)

---

## 1. Design Rationale

### 1.1 Problem Statement

The original session tracking design used **complete project isolation** via distinct `group_id` values derived from project path hashes. While this provided data separation, it created several limitations:

1. **No cross-project learning**: Knowledge gained in Project A was invisible to Project B
2. **Repeated mistakes**: Agents couldn't learn from corrections made in other projects
3. **Lost institutional knowledge**: Patterns discovered in one context couldn't inform others
4. **Configuration complexity**: Users needed to manage settings per-project

### 1.2 Design Options Considered

Four architectural approaches were evaluated:

#### Option A: Pure Global Scope
```
GROUP_ID: Single global ID
Pros: Simple, full cross-project sharing
Cons: No isolation, context contamination risk, no filtering
```
**Rejected**: Too risky without provenance tracking.

#### Option B: Global Config + Project GROUP_IDs (Hybrid)
```
GROUP_ID: Per-project hash (unchanged)
Config: Global location only
Pros: Maintains isolation, simpler config
Cons: No cross-project learning by default
```
**Rejected**: Doesn't solve the core knowledge sharing problem.

#### Option C: Hierarchical Config (Most Flexible)
```
GROUP_ID: Configurable per-project or inherit global
Config: Global defaults + project overrides
Pros: Maximum flexibility
Cons: Most complex, harder to reason about
```
**Rejected**: Over-engineered for pre-release software.

#### Option D: Global + Namespace Tagging (SELECTED)
```
GROUP_ID: Single global (hostname__global)
Metadata: project_namespace embedded in episodes
Pros: Cross-project learning with provenance, filterable
Cons: Requires schema changes
```
**Selected**: Best balance of knowledge sharing and safety.

### 1.3 Key Design Decisions

#### Decision 1: Global-Only (No Project Scope Option)

**Question**: Should we support both global and project-scoped modes for backward compatibility?

**Decision**: No. Since session tracking hasn't been released/tested yet, we opted for a clean global-only design without backward compatibility overhead.

**Rationale**:
- Pre-release software doesn't need backward compatibility
- Dual modes add complexity and testing burden
- Users who truly need isolation can use `trusted_namespaces` filtering
- Simpler mental model for users

#### Decision 2: Namespace Tagging Over Schema Extension

**Question**: Should we add `project_namespace` as a new field on `EpisodicNode`, or embed it in episode content?

**Decision**: Embed in episode content as YAML frontmatter header.

**Rationale**:
- No Neo4j schema migration required
- Works with existing Graphiti API
- Human-readable in episode content
- Agents can naturally interpret the metadata
- Simpler implementation

#### Decision 3: Cross-Project Search Default

**Question**: Should cross-project search be opt-in or opt-out?

**Decision**: Opt-out (enabled by default).

**Rationale**:
- The whole point of Option D is cross-project learning
- Agents can infer from context when information may not apply
- User feedback during sessions naturally corrects misconceptions
- Users who need isolation can set `cross_project_search: false`

#### Decision 4: Handling Bad Context Contamination

**Question**: What if Project A has incorrect context that misleads agents working on Project B?

**Decision**: Trust agent inference + user feedback loop + optional `trusted_namespaces` filtering.

**Rationale**:
- Agents see `project_namespace` metadata and can weigh relevance
- When users correct agents, those corrections are ALSO indexed
- Self-correcting system: bad context gets overwritten by corrections
- For known-bad projects, users can exclude via `trusted_namespaces`
- This is the "most autonomously compatible approach"

---

## 2. Architecture Overview

### 2.1 Current Architecture (v1.0.0)

```
+-------------------------------------------------------------+
|                    Claude Code Sessions                      |
|  ~/.claude/projects/{hash_A}/sessions/*.jsonl               |
|  ~/.claude/projects/{hash_B}/sessions/*.jsonl               |
+---------------------------+---------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|                   Session Tracking                           |
|  - Watches all project directories                          |
|  - Indexes to SEPARATE group_ids per project                |
+---------------------------+---------------------------------+
                            |
            +---------------+---------------+
            v                               v
+-----------------+             +-----------------+
|  Neo4j Graph    |             |  Neo4j Graph    |
|  group_id: A    |             |  group_id: B    |
|  (isolated)     |             |  (isolated)     |
+-----------------+             +-----------------+
```

**Problem**: Projects A and B cannot share knowledge.

### 2.2 Proposed Architecture (v2.0.0)

```
+-------------------------------------------------------------+
|                    Claude Code Sessions                      |
|  ~/.claude/projects/{hash_A}/sessions/*.jsonl               |
|  ~/.claude/projects/{hash_B}/sessions/*.jsonl               |
+---------------------------+---------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|                   Session Tracking                           |
|  - Watches all project directories                          |
|  - Extracts project_namespace from path                     |
|  - Embeds namespace metadata in episode content             |
|  - Indexes ALL to SINGLE global group_id                    |
+---------------------------+---------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|                    Neo4j Graph                               |
|                group_id: HOSTNAME__global                    |
|                                                              |
|  +-----------------+         +-----------------+             |
|  | Episode (A)     |         | Episode (B)     |             |
|  | namespace: A    |         | namespace: B    |             |
|  | path: /proj/a   |         | path: /proj/b   |             |
|  +-----------------+         +-----------------+             |
|                                                              |
|  Cross-project search enabled by default                    |
|  Namespace metadata enables filtering when needed           |
+-------------------------------------------------------------+
```

**Benefit**: Unified knowledge graph with provenance tracking.

---

## 3. Configuration Schema

### 3.1 SessionTrackingConfig (Updated)

```python
class SessionTrackingConfig(BaseModel):
    """Global session tracking with cross-project namespace tagging.

    All sessions are indexed to a single global graph with project_namespace
    metadata for provenance tracking and optional filtering. This enables
    cross-project knowledge sharing while maintaining context awareness.
    """

    # === Core Settings (UNCHANGED) ===

    enabled: bool = Field(
        default=False,
        description=(
            "Enable or disable session tracking. "
            "When enabled, monitors Claude Code session files and indexes them "
            "to the global Graphiti knowledge graph. Opt-in for security."
        )
    )

    watch_path: Optional[str] = Field(
        default=None,
        description=(
            "Path to directory containing Claude Code session files. "
            "If None, defaults to ~/.claude/projects/. "
            "Must be an absolute path (native OS format)."
        )
    )

    inactivity_timeout: int = Field(
        default=900,
        description=(
            "Inactivity timeout in seconds before a session is considered closed. "
            "After this timeout, the session will be indexed into Graphiti. "
            "Default: 900 seconds (15 minutes)."
        )
    )

    check_interval: int = Field(
        default=60,
        description=(
            "Interval in seconds to check for inactive sessions. "
            "The file watcher checks for inactive sessions at this interval."
        )
    )

    auto_summarize: bool = Field(
        default=False,
        description=(
            "Automatically summarize closed sessions using Graphiti's LLM. "
            "If False, sessions are stored as raw episodes without summarization "
            "(no LLM costs)."
        )
    )

    store_in_graph: bool = Field(
        default=True,
        description=(
            "Store session summaries in the Graphiti knowledge graph. "
            "If False, sessions are logged but not persisted to Neo4j."
        )
    )

    keep_length_days: Optional[int] = Field(
        default=7,
        description=(
            "Rolling window filter for session discovery in days. "
            "Only sessions modified within the last N days will be indexed. "
            "Set to null to index all sessions (not recommended, may cause "
            "bulk LLM costs on first run)."
        )
    )

    filter: FilterConfig = Field(
        default_factory=FilterConfig,
        description=(
            "Filtering configuration for session content. "
            "Controls how messages and tool results are filtered for token reduction."
        )
    )

    resilience: SessionTrackingResilienceConfig = Field(
        default_factory=SessionTrackingResilienceConfig,
        description=(
            "Resilience configuration for session tracking. "
            "Defines behavior when LLM is unavailable during session processing."
        )
    )

    # === NEW: Global Scope Settings ===

    group_id: Optional[str] = Field(
        default=None,
        description=(
            "Global group ID for all indexed sessions. "
            "If None, defaults to '{hostname}__global'. "
            "All projects share this single graph with project_namespace "
            "metadata embedded in each episode for filtering."
        )
    )

    # === NEW: Cross-Project Query Settings ===

    cross_project_search: bool = Field(
        default=True,
        description=(
            "Allow searching across all project namespaces. "
            "If True (default), queries return results from all projects with "
            "namespace metadata visible for agent interpretation. "
            "If False, queries are automatically filtered to only return "
            "results matching the current project's namespace."
        )
    )

    trusted_namespaces: Optional[list[str]] = Field(
        default=None,
        description=(
            "List of project namespace hashes to trust for cross-project search. "
            "If None (default), all namespaces are trusted. "
            "Use this to exclude known-problematic project contexts from search. "
            "Example: ['a1b2c3d4', 'e5f6g7h8'] to only trust specific projects."
        )
    )

    include_project_path: bool = Field(
        default=True,
        description=(
            "Include human-readable project path in episode metadata. "
            "Helps agents understand context provenance (e.g., '/home/user/myproject'). "
            "Set to False if project paths contain sensitive information."
        )
    )

    # === Validators ===

    @field_validator('keep_length_days')
    def validate_keep_length_days(cls, v):
        if v is not None and v <= 0:
            raise ValueError("keep_length_days must be > 0 or null")
        return v

    @field_validator('trusted_namespaces')
    def validate_trusted_namespaces(cls, v):
        if v is not None:
            # Validate namespace format (should be hex hashes)
            import re
            for ns in v:
                if not re.match(r'^[a-f0-9]+$', ns.lower()):
                    raise ValueError(
                        f"Invalid namespace format: {ns}. "
                        "Expected hex hash (e.g., 'a1b2c3d4')."
                    )
        return v
```

### 3.2 JSON Configuration Example

```json
{
  "$schema": "./graphiti.config.schema.json",
  "version": "2.0.0",

  "session_tracking": {
    "enabled": true,
    "watch_path": null,
    "inactivity_timeout": 900,
    "check_interval": 60,
    "auto_summarize": false,
    "store_in_graph": true,
    "keep_length_days": 7,

    "group_id": null,
    "cross_project_search": true,
    "trusted_namespaces": null,
    "include_project_path": true,

    "filter": {
      "tool_calls": true,
      "tool_content": "default-tool-content.md",
      "user_messages": true,
      "agent_messages": true
    },

    "resilience": {
      "on_llm_unavailable": "STORE_RAW_AND_RETRY",
      "retry_queue": {
        "max_retries": 5,
        "retry_delays_seconds": [300, 900, 2700, 7200, 21600],
        "max_queue_size": 1000,
        "persist_to_disk": true
      },
      "notifications": {
        "on_permanent_failure": true,
        "notification_method": "log",
        "webhook_url": null
      }
    }
  }
}
```

### 3.3 Configuration Precedence

Configuration is loaded from (in order):

1. `./graphiti.config.json` (project root, if exists)
2. `~/.graphiti/graphiti.config.json` (global)
3. Built-in defaults

**Note**: For session tracking, we recommend using the global config only since the feature operates across all projects.

---

## 4. Episode Metadata Structure

### 4.1 Metadata Header Format

All indexed episodes include a YAML frontmatter header with namespace metadata:

```markdown
---
graphiti_session_metadata:
  version: "2.0"
  project_namespace: "a1b2c3d4e5f6g7h8"
  project_path: "/home/user/my-awesome-project"
  hostname: "DESKTOP-ABC123"
  indexed_at: "2025-12-08T15:30:00Z"
  session_file: "session-abc123.jsonl"
  message_count: 47
  duration_minutes: 23
---

# Session 015: Implemented Authentication Flow

## Summary
This session focused on implementing JWT-based authentication...

## Completed Tasks
- [x] Created auth middleware
- [x] Added token refresh logic
...
```

### 4.2 Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Metadata schema version ("2.0") |
| `project_namespace` | string | Hash derived from project path (for filtering) |
| `project_path` | string\|null | Human-readable path (if `include_project_path: true`) |
| `hostname` | string | Machine hostname for multi-machine disambiguation |
| `indexed_at` | ISO8601 | Timestamp when episode was indexed |
| `session_file` | string | Original JSONL filename |
| `message_count` | int | Number of messages in session |
| `duration_minutes` | int | Approximate session duration |

### 4.3 Source Description Format

The `source_description` field is prefixed with namespace for quick identification:

```
[a1b2c3d4] Session with 47 messages, 3 completed tasks, 5 files modified
```

This allows agents to see provenance even without parsing the full episode content.

---

## 5. Search Behavior

### 5.1 Default Behavior (cross_project_search: true)

When an agent queries the knowledge graph:

```python
# Agent's query
results = await graphiti.search(
    query="How did we implement JWT authentication?",
    group_ids=["HOSTNAME__global"]
)
```

**Returns**: All matching episodes from all projects, each with visible namespace metadata.

**Agent interpretation**: The agent sees results like:
```
Result 1: [namespace: a1b2c3d4, path: /home/user/auth-service]
  "Implemented JWT with RS256 signing, 15-minute expiry..."

Result 2: [namespace: e5f6g7h8, path: /home/user/old-prototype]
  "Used HS256 symmetric signing (later found insecure)..."
```

The agent can:
- Recognize that Result 2 is from a different project
- Note the "later found insecure" correction
- Apply Result 1's approach while avoiding Result 2's mistake

### 5.2 Restricted Behavior (cross_project_search: false)

```python
# System automatically filters to current project namespace
results = await graphiti.search(
    query="How did we implement JWT authentication?",
    group_ids=["HOSTNAME__global"],
    # Auto-injected filter:
    metadata_filter={"project_namespace": current_project_hash}
)
```

**Returns**: Only episodes from the current project.

### 5.3 Trusted Namespaces Filter

```python
# Config: trusted_namespaces: ["a1b2c3d4", "e5f6g7h8"]

results = await graphiti.search(
    query="How did we implement JWT authentication?",
    group_ids=["HOSTNAME__global"],
    # Auto-injected filter:
    metadata_filter={"project_namespace": {"$in": ["a1b2c3d4", "e5f6g7h8"]}}
)
```

**Returns**: Only episodes from trusted projects.

### 5.4 Provenance-Aware Agent Behavior

Agents using this system should:

1. **Always note provenance** when presenting cross-project context
2. **Weigh recency** - newer sessions may have corrections
3. **Look for corrections** - if context says "X didn't work", apply that learning
4. **Ask when uncertain** - if context from another project seems inapplicable

Example agent response:
> "Based on a session from the `auth-service` project (namespace a1b2c3d4),
> JWT authentication was implemented using RS256 signing. I also found an
> earlier session from `old-prototype` that used HS256 but was later marked
> as insecure. I'll follow the RS256 approach."

---

## 6. Implementation Requirements

### 6.1 Files to Modify

| File | Changes |
|------|---------|
| `mcp_server/unified_config.py` | Add new fields to `SessionTrackingConfig` |
| `graphiti_core/session_tracking/path_resolver.py` | Add method to get project path (not just hash) |
| `graphiti_core/session_tracking/indexer.py` | Embed namespace metadata in episodes |
| `graphiti_core/session_tracking/graphiti_storage.py` | Update `store_session()` to include metadata |
| `graphiti_core/session_tracking/session_manager.py` | Pass project info to indexer |
| `mcp_server/graphiti_mcp_server.py` | Compute global group_id, pass namespace to storage |
| `graphiti.config.schema.json` | Update JSON schema with new fields |

### 6.2 New Helper Functions

```python
# In path_resolver.py
def get_project_path_from_hash(self, project_hash: str) -> Optional[str]:
    """Reverse-lookup project path from hash.

    Note: Claude Code stores a mapping file we can read, or we can
    scan known project directories to find matches.

    Args:
        project_hash: The hash to look up

    Returns:
        Project directory path, or None if cannot be determined
    """
    pass

def get_global_group_id(self, hostname: str) -> str:
    """Generate the global group ID for this machine.

    Args:
        hostname: Machine hostname

    Returns:
        Global group ID in format '{hostname}__global'
    """
    return f"{hostname}__global"
```

```python
# In indexer.py or new metadata.py
def build_episode_metadata_header(
    project_namespace: str,
    project_path: Optional[str],
    hostname: str,
    session_file: str,
    message_count: int,
    duration_minutes: int,
    include_project_path: bool = True
) -> str:
    """Build YAML frontmatter header for episode content.

    Returns:
        YAML frontmatter string to prepend to episode body
    """
    import yaml
    from datetime import datetime, timezone

    metadata = {
        "graphiti_session_metadata": {
            "version": "2.0",
            "project_namespace": project_namespace,
            "project_path": project_path if include_project_path else None,
            "hostname": hostname,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "session_file": session_file,
            "message_count": message_count,
            "duration_minutes": duration_minutes,
        }
    }

    # Remove None values
    metadata["graphiti_session_metadata"] = {
        k: v for k, v in metadata["graphiti_session_metadata"].items()
        if v is not None
    }

    return f"---\n{yaml.dump(metadata, default_flow_style=False)}---\n\n"
```

### 6.3 Search Filter Implementation

```python
# In graphiti_mcp_server.py - modify search tools

async def search_memory_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    # NEW: namespace filtering
    project_namespaces: list[str] | None = None,
) -> dict:
    """Search for memory nodes with optional namespace filtering.

    Args:
        query: Search query
        group_ids: Group IDs to search (default: global group)
        max_nodes: Maximum results
        project_namespaces: Filter to specific project namespaces.
            If None, uses config (cross_project_search, trusted_namespaces).
    """
    config = get_config()
    st_config = config.session_tracking

    # Determine effective group_ids
    if group_ids is None:
        hostname = socket.gethostname()
        global_group = st_config.group_id or f"{hostname}__global"
        group_ids = [global_group]

    # Determine namespace filter
    effective_namespaces = project_namespaces
    if effective_namespaces is None:
        if not st_config.cross_project_search:
            # Filter to current project only
            effective_namespaces = [get_current_project_namespace()]
        elif st_config.trusted_namespaces:
            # Filter to trusted namespaces
            effective_namespaces = st_config.trusted_namespaces

    # Execute search
    results = await graphiti.search(
        query=query,
        group_ids=group_ids,
        num_results=max_nodes,
    )

    # Post-filter by namespace if needed
    # (Until Graphiti supports native metadata filtering)
    if effective_namespaces:
        results = filter_by_namespace(results, effective_namespaces)

    return format_results(results)
```

### 6.4 Episode Storage Changes

```python
# In graphiti_storage.py - modify store_session()

async def store_session(
    self,
    summary: SessionSummary,
    group_id: str,
    project_namespace: str,  # NEW
    project_path: Optional[str] = None,  # NEW
    hostname: Optional[str] = None,  # NEW
    include_project_path: bool = True,  # NEW
    previous_session_uuid: str | None = None,
    handoff_file_path: Path | None = None,
) -> str:
    """Store session summary with namespace metadata."""

    # Build metadata header
    metadata_header = build_episode_metadata_header(
        project_namespace=project_namespace,
        project_path=project_path,
        hostname=hostname or socket.gethostname(),
        session_file=summary.session_file,
        message_count=summary.message_count,
        duration_minutes=summary.duration_minutes,
        include_project_path=include_project_path,
    )

    # Build episode body with metadata
    episode_body = metadata_header + summary.to_markdown()

    # Prefix source description with namespace
    source_description = (
        f"[{project_namespace[:8]}] "
        f"Session with {summary.message_count} messages, "
        f"{len(summary.completed_tasks)} completed tasks"
    )

    # Add to graph with global group_id
    result = await self.graphiti.add_episode(
        name=episode_name,
        episode_body=episode_body,
        source_description=source_description,
        group_id=group_id,  # Now uses global group_id
        ...
    )

    return result.episode.uuid
```

---

## 7. Migration Guide

### 7.1 For New Users

No migration needed. Default configuration works out of the box:

1. Install Graphiti MCP server
2. Set `session_tracking.enabled: true` in `~/.graphiti/graphiti.config.json`
3. Sessions are automatically indexed to global graph

### 7.2 For Existing Test Users

If you tested the v1.0.0 project-scoped implementation:

1. **Data migration**: Existing episodes have project-specific `group_id` values
2. **Option A**: Keep old data in old group_ids (won't be searched by default)
3. **Option B**: Re-index sessions with new global group_id
4. **Option C**: Manual migration script (if needed)

Since v1.0.0 was never released publicly, migration is not a priority.

### 7.3 Configuration Migration

**Old config** (v1.0.0):
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": null
  }
}
```

**New config** (v2.0.0):
```json
{
  "session_tracking": {
    "enabled": true,
    "watch_path": null,
    "group_id": null,
    "cross_project_search": true,
    "trusted_namespaces": null,
    "include_project_path": true
  }
}
```

New fields have sensible defaults, so existing configs work without changes.

---

## 8. Security Considerations

### 8.1 Project Path Exposure

**Risk**: `project_path` may reveal sensitive directory structures.

**Mitigation**: Set `include_project_path: false` to redact paths.

### 8.2 Cross-Project Information Leakage

**Risk**: Sensitive information from Project A visible when working on Project B.

**Mitigations**:
1. Session content filtering already in place (filter config)
2. Set `cross_project_search: false` for sensitive projects
3. Use `trusted_namespaces` to exclude specific projects
4. Credential detection in existing security scans

### 8.3 Namespace Hash Collision

**Risk**: Two projects could theoretically have the same namespace hash.

**Mitigation**:
- Hash is derived from full path (collision probability negligible)
- Hostname included in metadata for disambiguation
- Even with collision, provenance metadata helps agents differentiate

### 8.4 Multi-User Environments

**Risk**: On shared machines, users might see each other's project data.

**Mitigation**:
- Session files are in user-specific `~/.claude/` directory
- Global group_id includes hostname (not shared across machines)
- For shared Neo4j instances, use separate databases or group_id prefixes

---

## 9. Testing Requirements

### 9.1 Unit Tests

```python
# Test namespace metadata generation
def test_build_episode_metadata_header():
    header = build_episode_metadata_header(
        project_namespace="a1b2c3d4",
        project_path="/home/user/project",
        hostname="DESKTOP-TEST",
        session_file="session-123.jsonl",
        message_count=50,
        duration_minutes=30,
    )
    assert "project_namespace: a1b2c3d4" in header
    assert "version: '2.0'" in header or 'version: "2.0"' in header

def test_build_episode_metadata_header_redacted_path():
    header = build_episode_metadata_header(
        project_namespace="a1b2c3d4",
        project_path="/home/user/project",
        hostname="DESKTOP-TEST",
        session_file="session-123.jsonl",
        message_count=50,
        duration_minutes=30,
        include_project_path=False,
    )
    assert "project_path" not in header

# Test global group_id generation
def test_get_global_group_id():
    resolver = ClaudePathResolver()
    group_id = resolver.get_global_group_id("MYHOST")
    assert group_id == "MYHOST__global"

# Test config validation
def test_trusted_namespaces_validation():
    # Valid hex hashes
    config = SessionTrackingConfig(trusted_namespaces=["a1b2c3d4", "e5f6g7h8"])
    assert config.trusted_namespaces == ["a1b2c3d4", "e5f6g7h8"]

    # Invalid format should raise
    with pytest.raises(ValueError):
        SessionTrackingConfig(trusted_namespaces=["not-a-hash!"])
```

### 9.2 Integration Tests

```python
# Test cross-project search
async def test_cross_project_search_enabled():
    """Sessions from multiple projects should be returned."""
    # Index sessions from two projects
    await index_session(project_namespace="proj_a", content="Auth with JWT")
    await index_session(project_namespace="proj_b", content="Auth with OAuth")

    # Search should return both
    results = await search("authentication")
    assert len(results) == 2
    namespaces = {extract_namespace(r) for r in results}
    assert namespaces == {"proj_a", "proj_b"}

async def test_cross_project_search_disabled():
    """Only current project sessions should be returned."""
    config.session_tracking.cross_project_search = False
    current_namespace = "proj_a"

    results = await search("authentication", current_namespace=current_namespace)
    assert all(extract_namespace(r) == "proj_a" for r in results)

async def test_trusted_namespaces_filter():
    """Only trusted namespace sessions should be returned."""
    config.session_tracking.trusted_namespaces = ["proj_a"]

    results = await search("authentication")
    assert all(extract_namespace(r) == "proj_a" for r in results)
```

### 9.3 End-to-End Tests

```python
# Test full workflow
async def test_session_indexing_with_metadata():
    """Session should be indexed with correct namespace metadata."""
    # Create test session file
    session_path = create_test_session(
        project_hash="a1b2c3d4",
        messages=[...],
    )

    # Trigger indexing
    await session_manager.process_session(session_path)

    # Verify episode in graph
    episodes = await graphiti.retrieve_episodes(
        group_ids=["TESTHOST__global"],
        last_n=1,
    )

    assert len(episodes) == 1
    assert "project_namespace: a1b2c3d4" in episodes[0].content
```

---

## Appendix A: Configuration Quick Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Enable session tracking |
| `watch_path` | `null` | Path to sessions (default: ~/.claude/projects/) |
| `inactivity_timeout` | `900` | Seconds before session closes |
| `check_interval` | `60` | Seconds between inactivity checks |
| `auto_summarize` | `false` | Use LLM to summarize sessions |
| `store_in_graph` | `true` | Persist to Neo4j |
| `keep_length_days` | `7` | Rolling window filter |
| `group_id` | `null` | Global group ID (default: {hostname}__global) |
| `cross_project_search` | `true` | Search across all projects |
| `trusted_namespaces` | `null` | Restrict to specific projects |
| `include_project_path` | `true` | Include paths in metadata |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Group ID** | Identifier for a collection of episodes in Graphiti |
| **Project Namespace** | Hash derived from project path, used for filtering |
| **Episode** | A unit of knowledge stored in the Graphiti graph |
| **Session** | A Claude Code conversation session (JSONL file) |
| **Cross-Project Search** | Ability to search knowledge from multiple projects |
| **Provenance** | Origin/source information for a piece of knowledge |

---

## Appendix C: Decision Log

This appendix documents the conversation flow that led to this specification.

### Initial Question
> "How is our current configuration schema defined for the automated session logging features?"

The user was considering whether session tracking config should be:
- Project-scoped (in working directory)
- Global-scoped (in ~/.graphiti/)

### User's Initial Concerns
1. Global scope would allow cross-project learning
2. But `filter_by_days` needed to control API token usage
3. GROUP_IDs would need to work across projects
4. Risk: Project A's incorrect context could mislead Project B

### Options Presented
Four architectural options were analyzed (A, B, C, D).

### User's Selection
> "I think Option D is what I want. If we allowed cross-project learning, agents should be able to infer based on the context from last sessions if something was unsupported so long as the user gives the agent feedback during the process of the chat."

Key insight: The user recognized that:
- Agents can interpret provenance metadata
- User corrections during sessions are also indexed
- This creates a self-correcting system
- This is "the most autonomously compatible approach"

### Simplification Decision
> "Since this still hasn't even been tested after last development sprint was finished, we don't need backwards compatibility support for scoping project-specific configs."

This allowed removal of the `scope: "global" | "project"` toggle, simplifying the design to global-only.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0.0-draft | 2025-12-08 | Human + Claude | Initial specification |
