# Session Tracking Security & Configuration Concerns - Handoff

**Date**: 2025-11-18
**Status**: ACTIVE - Requires immediate review and configuration changes
**Priority**: HIGH (Security & Privacy)

---

## Executive Summary

During review of the session auto-tracking feature in Graphiti MCP v1.0.0, critical security and privacy concerns were identified with the default configuration. The current defaults enable **automatic, opt-out tracking of all Claude Code sessions** across all projects with **LLM processing enabled by default**, creating significant cost, privacy, and performance risks.

---

## Critical Issues Identified

### 1. **Overly Aggressive Default Configuration**

**Current Defaults** (`mcp_server/unified_config.py:328-374`, `graphiti.config.json:108-121`):
```json
{
  "session_tracking": {
    "enabled": true,                    // ❌ ENABLED BY DEFAULT (opt-out)
    "watch_path": null,                 // ❌ Watches ALL projects (~/.claude/projects/)
    "auto_summarize": true,             // ❌ LLM processing by default
    "store_in_graph": true,             // Persists to Neo4j
    "filter": {
      "tool_calls": true,
      "tool_content": "summary",        // ⚠️ Still processes large outputs
      "user_messages": "full",
      "agent_messages": "full"
    }
  }
}
```

**Problems**:
- **Opt-out model**: Users must explicitly disable tracking (violates privacy-first principle)
- **All projects tracked**: No project-specific authorization required
- **LLM costs**: `auto_summarize: true` sends every session to OpenAI by default
- **Tool content overhead**: `"summary"` mode still processes tool outputs via LLM

---

### 2. **Lack of User Authorization**

**Current Behavior**:
- MCP server starts → Automatically watches `~/.claude/projects/` → Indexes ALL sessions from ALL projects
- No per-project consent mechanism
- No client-initiated authorization flow
- User unaware of tracking unless they read logs

**Risk Scenarios**:
1. **Sensitive projects**: Work projects, client codebases, personal projects tracked without consent
2. **API cost explosion**: Large sessions (100+ tool calls) × many projects × LLM summarization = $$$
3. **Privacy violation**: Session data (prompts, code, tool outputs) indexed without explicit permission

---

### 3. **Indiscriminate Bulk Indexing**

**What happens when `watch_path: null`**:
- Resolves to `~/.claude/projects/` (`ClaudePathResolver.__init__:30-38`)
- Watches ALL subdirectories recursively
- If directory doesn't exist: Logs warning, returns empty (graceful) (`path_resolver.py:199-201`)
- If directory has 100+ projects with years of session files: **Attempts to index ALL of them**

**Example Risk**:
```
~/.claude/projects/
├── project-a/sessions/ (500 JSONL files, 2GB)
├── project-b/sessions/ (300 JSONL files, 1.5GB)
├── project-c/sessions/ (200 JSONL files, 1GB)
└── [... 50 more projects ...]

Total: 1000+ session files = Automatic indexing on MCP server start
Cost: 1000 sessions × $0.50 avg (LLM summarization) = $500+
```

---

### 4. **Parameter Confusion**

**User asked about**:

**`inactivity_timeout`** (default: 300 seconds = 5 minutes):
- Time since last file modification before session considered "closed"
- Triggers indexing callback after timeout expires
- Check performed every `check_interval` seconds

**`check_interval`** (default: 60 seconds):
- How often SessionManager polls for inactive sessions
- Higher = lower CPU, but delayed indexing
- Lower = faster indexing, but higher overhead

**Missing directory behavior**:
- `~/.claude/projects/` doesn't exist → Logs warning, continues gracefully
- Empty directory → No sessions discovered, watcher runs idle
- Massive directory → Indexes everything automatically (RISK)

---

## What We've Discovered

### Architecture Analysis

**Initialization Flow** (`mcp_server/graphiti_mcp_server.py:1900-1990`):
1. MCP server starts → `initialize_server()` called
2. Loads `unified_config` → Checks `session_tracking.enabled`
3. If `enabled == true` (DEFAULT) → Calls `initialize_session_tracking()`
4. Creates `ClaudePathResolver` with `watch_path` (or defaults to `~/.claude/projects/`)
5. Creates `SessionManager` → Starts file watcher
6. Discovers all existing sessions → Queues them for indexing
7. Monitors for new sessions continuously

**No safeguards**:
- ✅ Directory existence check (graceful if missing)
- ❌ No project count warning
- ❌ No session file count limit
- ❌ No cost estimation before bulk indexing
- ❌ No user confirmation prompt

### Current Filter Behavior

**FilterConfig defaults** (`filter_config.py:27-163`):
```python
tool_content: ContentMode.SUMMARY  # Default
# Reduction: ~70% for tool results
# BUT: Still sends to LLM for summarization
```

**Token reduction estimates**:
- Default config: ~35% reduction (tool results summarized)
- Aggressive (omit tools): ~57% reduction
- No filtering: 0% reduction

**LLM dependency**:
- `auto_summarize: true` → ALWAYS calls OpenAI for episode summarization
- `tool_content: "summary"` → ALWAYS calls OpenAI to condense tool outputs
- **Result**: Even with filtering, every session hits OpenAI API

---

## Recommended Configuration Changes

### Immediate (Security Fix)

**Change defaults to opt-in model**:
```json
{
  "session_tracking": {
    "enabled": false,                   // ✅ DISABLED BY DEFAULT (opt-in)
    "watch_path": null,                 // ✅ User must configure
    "auto_summarize": false,            // ✅ Disable LLM by default
    "store_in_graph": true,             // OK (no cost if disabled)
    "filter": {
      "tool_calls": true,               // ✅ Preserve structure
      "tool_content": "omit",           // ✅ Remove expensive content
      "user_messages": "full",          // ✅ Preserve intent
      "agent_messages": "full"          // ✅ Preserve context
    }
  }
}
```

**Rationale**:
- **Privacy-first**: No tracking without explicit enablement
- **Cost-safe**: No LLM calls without user authorization
- **Token-efficient**: Omit tool content (60% of tokens), preserve conversation flow

---

### Medium-term (Authorization System)

**Project-level authorization**:
```json
{
  "session_tracking": {
    "enabled": true,
    "authorized_projects": [           // NEW: Explicit project list
      "/home/user/my-project",
      "/home/user/client-project-a"
    ],
    "watch_mode": "authorized_only"   // NEW: "authorized_only" | "all_projects"
  }
}
```

**Client-initiated tracking**:
- MCP tool: `session_tracking_authorize_project(project_path)`
- Tool: `session_tracking_start(session_id, project_path)` with auth check
- Fallback: Global `watch_mode: "all_projects"` if user explicitly configures

---

### Long-term (Cost Controls)

**Session limits and warnings**:
```json
{
  "session_tracking": {
    "max_sessions_per_index": 100,    // NEW: Warn if >100 pending
    "max_total_sessions": 1000,       // NEW: Hard limit across all projects
    "cost_estimate_threshold": 10.0   // NEW: Warn if estimated cost > $10
  }
}
```

**Bulk indexing protection**:
- Detect >50 existing session files → Prompt user: "Found 200 sessions. Index all? (est. cost: $100)"
- Show per-project breakdown before indexing
- Allow selective indexing by date range or project

---

## What Still Needs Investigating

### 1. **Existing User Impact**

**Questions**:
- How many users have v1.0.0 deployed with default config?
- How many sessions have been auto-indexed without user knowledge?
- What are actual API costs incurred by early adopters?

**Action**: Survey logs, check OpenAI usage patterns, contact early users

---

### 2. **Migration Path**

**Questions**:
- How to change defaults without breaking existing users?
- Should we auto-disable on upgrade if `enabled: true` was never explicitly set by user?
- How to distinguish "user configured" vs "default value"?

**Approaches**:
- Config versioning: `config_version: 1` (old defaults) vs `config_version: 2` (new defaults)
- Migration script: Detect v1.0.0 config → Prompt user → Update to safe defaults
- Deprecation warning: "Session tracking will change to opt-in in v1.1.0. Configure now."

---

### 3. **Alternative Authorization Models**

**Options**:
1. **Per-project opt-in file**: `.graphiti-track` in project root (user creates)
2. **Client-side permission**: Claude Code prompts "Allow Graphiti to track this project?"
3. **MCP capability negotiation**: Client declares `supports_session_tracking` capability
4. **OAuth-style flow**: MCP server requests permission, client shows UI consent

**Research needed**:
- MCP specification support for authorization flows
- Claude Code extension points for permission dialogs
- Best practices from other MCP servers (filesystem, browser control)

---

### 4. **Cost Estimation Accuracy**

**Current estimates** (`FilterConfig.estimate_token_reduction()`):
- Based on "typical" session composition (60% tools, 15% user, 25% agent)
- No actual token counting before indexing
- No LLM cost calculation (summarization is separate)

**Gaps**:
- Actual session size varies wildly (10KB to 10MB)
- LLM summarization cost depends on episode size, not just token count
- No way to preview cost before bulk indexing

**Investigation**:
- Analyze real session file sizes from sample projects
- Measure actual OpenAI API costs for summarization
- Build cost estimator tool: `graphiti-mcp estimate-cost --path ~/.claude/projects/`

---

### 5. **Performance at Scale**

**Questions**:
- File watcher overhead with 100+ projects (each with subdirs)
- SessionManager memory usage with 1000+ active sessions
- Neo4j indexing performance with 10,000+ episodes
- Disk I/O impact of recursive JSONL monitoring

**Benchmarks needed**:
- Simulate 100 projects × 50 sessions each = 5,000 files
- Measure CPU/RAM/disk usage over 24 hours
- Test session close detection latency (inactivity timeout accuracy)

---

### 6. **Privacy & Compliance**

**Questions**:
- Does automatic session indexing violate GDPR (user data processing without consent)?
- Should we provide data export/deletion tools per-project?
- How to handle sensitive data in session files (API keys, passwords in prompts)?
- What are retention policies (how long to keep indexed sessions)?

**Actions**:
- Legal review of auto-tracking (especially for enterprise users)
- Implement `session_tracking_delete_project(project_path)` tool
- Add credential detection to pre-indexing filter (block/warn if detected)
- Document data retention and deletion procedures

---

## Immediate Next Steps

### Critical Path (Week 1)

1. **Change defaults** (`mcp_server/unified_config.py`):
   - `enabled: false`
   - `auto_summarize: false`
   - `tool_content: "omit"`

2. **Update documentation** (CONFIGURATION.md, SESSION_TRACKING_USER_GUIDE.md):
   - Explain opt-in model
   - Show how to enable safely
   - Warn about costs and privacy

3. **Create migration guide** (SESSION_TRACKING_MIGRATION.md):
   - Detect v1.0.0 config
   - Prompt user for consent
   - Offer safe defaults or custom config

4. **Add safety checks** (`initialize_session_tracking()`):
   - Count existing session files before indexing
   - Warn if >50 sessions detected
   - Require explicit `--force` flag for bulk indexing

### Medium Priority (Week 2-3)

5. **Implement project authorization**:
   - Add `authorized_projects` to config schema
   - Add `watch_mode` setting
   - Implement authorization checks in `on_session_closed` callback

6. **Build cost estimator**:
   - CLI tool: `graphiti-mcp estimate-cost`
   - Show per-project breakdown
   - Include LLM summarization costs

7. **Add MCP tools for authorization**:
   - `session_tracking_authorize_project(path)`
   - `session_tracking_list_authorized()`
   - `session_tracking_revoke_project(path)`

### Low Priority (Month 2)

8. **Performance benchmarks** (simulate large deployments)
9. **Privacy tools** (export, deletion, credential detection)
10. **Alternative authorization models** (research MCP capabilities)

---

## Open Questions for Team Discussion

1. **Default stance**: Should session tracking be opt-in or opt-out? (Recommend: OPT-IN)
2. **Cost responsibility**: Who pays for LLM summarization - user or Graphiti project? (User)
3. **Backward compatibility**: Break existing configs or maintain dangerous defaults? (BREAK, with migration)
4. **Authorization UX**: File-based (`.graphiti-track`) or config-based (`authorized_projects`)? (Config preferred)
5. **Bulk indexing**: Allow automatic indexing of old sessions or require manual trigger? (MANUAL only)

---

## References

**Code locations**:
- Config: `mcp_server/unified_config.py:320-374`
- Initialization: `mcp_server/graphiti_mcp_server.py:1900-1990`
- Filter: `graphiti_core/session_tracking/filter_config.py:27-163`
- Path resolver: `graphiti_core/session_tracking/path_resolver.py:30-222`

**Documentation**:
- User guide: `docs/SESSION_TRACKING_USER_GUIDE.md`
- Configuration: `CONFIGURATION.md#session-tracking-configuration`
- Migration: `.claude/implementation/SESSION_TRACKING_MIGRATION.md`

**Related issues**:
- Privacy concerns (this handoff)
- Cost management (TBD)
- Performance at scale (TBD)

---

**Handoff Status**: Ready for team review and decision on default configuration changes.