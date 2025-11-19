# Complete Session Tracking Configuration Template

**Purpose**: Reference template showing ALL available session tracking configuration parameters with safe defaults and documentation.

---

## Full Configuration Schema

### Complete `session_tracking` Section
```json
{
  "session_tracking": {
    "_comment": "Session tracking monitors Claude Code sessions and indexes them into Graphiti",
    "_docs": "https://github.com/getzep/graphiti/blob/main/docs/SESSION_TRACKING_USER_GUIDE.md",
    
    "enabled": false,
    "_enabled_comment": "Enable session tracking (opt-in for security). Default: false",
    
    "watch_path": null,
    "_watch_path_comment": "Path to Claude projects directory. null = ~/.claude/projects/. Must be absolute path (C:\\ on Windows, / on Unix)",
    
    "inactivity_timeout": 45,
    "_inactivity_timeout_comment": "Seconds of inactivity before session considered closed and indexed. Default: 45 (realtime-like)",
    
    "check_interval": 15,
    "_check_interval_comment": "Interval in seconds to check for inactive sessions. Default: 15 (responsive)",
    
    "auto_summarize": false,
    "_auto_summarize_comment": "Automatically summarize sessions via LLM (costs money). Default: false (no costs)",
    
    "store_in_graph": true,
    "_store_in_graph_comment": "Store sessions in Neo4j graph (required for cross-session memory). Default: true",
    
    "keep_length_days": 7,
    "_keep_length_days_comment": "Only track sessions modified within last N days (null = all sessions). Default: 7 (rolling window)",
    
    "filter": {
      "_comment": "Message filtering controls token reduction vs information preservation",
      
      "tool_calls": true,
      "_tool_calls_comment": "Preserve tool call structure (names, parameters). Default: true (recommended)",
      
      "tool_content": "omit",
      "_tool_content_comment": "How to handle tool results: 'full' (no filtering), 'summary' (1-line), 'omit' (remove). Default: 'omit' (60% reduction)",
      
      "user_messages": "full",
      "_user_messages_comment": "How to handle user messages: 'full' (preserve), 'summary' (condense), 'omit' (remove). Default: 'full' (preserve intent)",
      
      "agent_messages": "full",
      "_agent_messages_comment": "How to handle agent responses: 'full' (preserve), 'summary' (condense), 'omit' (remove). Default: 'full' (preserve context)"
    }
  }
}
```

---

## Parameter Reference Table

| Parameter | Type | Default | Values | Description |
|-----------|------|---------|--------|-------------|
| `enabled` | bool | `false` | true/false | Enable session tracking (opt-in) |
| `watch_path` | string\|null | `null` | path or null | Directory to monitor (`null` = `~/.claude/projects/`) |
| `inactivity_timeout` | int | `45` | 30-300 | Seconds before session closed (realtime: 30-60, conservative: 300) |
| `check_interval` | int | `15` | 10-60 | Seconds between inactivity checks (responsive: 10-15, conservative: 60) |
| `auto_summarize` | bool | `false` | true/false | Use LLM to summarize sessions (costs $) |
| `store_in_graph` | bool | `true` | true/false | Store in Neo4j graph (required for memory) |
| `keep_length_days` | int\|null | `7` | 1-365 or null | Rolling window for session age (`null` = all) |
| `filter.tool_calls` | bool | `true` | true/false | Preserve tool structure |
| `filter.tool_content` | string | `"omit"` | full/summary/omit | Tool result filtering mode |
| `filter.user_messages` | string | `"full"` | full/summary/omit | User message filtering mode |
| `filter.agent_messages` | string | `"full"` | full/summary/omit | Agent response filtering mode |

---

## ContentMode Values Explained

### `"full"` (No filtering)
- Preserves complete original content
- **Pros**: No information loss
- **Cons**: High token usage
- **Use case**: Important conversations, debugging sessions

### `"summary"` (1-line summary)
- Replaces content with concise summary (via LLM if `auto_summarize: true`)
- **Pros**: 50-70% token reduction, preserves gist
- **Cons**: Loses details, requires LLM
- **Use case**: Tool results, verbose agent responses

### `"omit"` (Remove content)
- Completely removes content, keeps only structure
- **Pros**: 95% token reduction, no LLM needed
- **Cons**: Loses all content
- **Use case**: Tool results (large file reads, grep outputs)

---

## Configuration Presets

### Preset 1: Safe Default (Recommended)
**Use case**: General use, security-first, cost-conscious
```json
{
  "enabled": false,
  "watch_path": null,
  "inactivity_timeout": 45,
  "check_interval": 15,
  "auto_summarize": false,
  "store_in_graph": true,
  "keep_length_days": 7,
  "filter": {
    "tool_calls": true,
    "tool_content": "omit",
    "user_messages": "full",
    "agent_messages": "full"
  }
}
```
**Token reduction**: ~60%
**LLM cost**: $0/month (no summarization)
**Memory**: Conversation flow preserved, tool outputs omitted

---

### Preset 2: Balanced (Moderate)
**Use case**: Active projects, occasional LLM summarization
```json
{
  "enabled": true,
  "watch_path": "/home/user/my-project/.claude/sessions",
  "inactivity_timeout": 60,
  "check_interval": 20,
  "auto_summarize": true,
  "store_in_graph": true,
  "keep_length_days": 14,
  "filter": {
    "tool_calls": true,
    "tool_content": "summary",
    "user_messages": "full",
    "agent_messages": "full"
  }
}
```
**Token reduction**: ~35%
**LLM cost**: ~$1-5/month (summarization enabled)
**Memory**: Full conversation + tool summaries

---

### Preset 3: Maximum Memory (Research)
**Use case**: Deep research, long-term projects, cost not a concern
```json
{
  "enabled": true,
  "watch_path": null,
  "inactivity_timeout": 30,
  "check_interval": 10,
  "auto_summarize": true,
  "store_in_graph": true,
  "keep_length_days": 30,
  "filter": {
    "tool_calls": true,
    "tool_content": "summary",
    "user_messages": "full",
    "agent_messages": "summary"
  }
}
```
**Token reduction**: ~50%
**LLM cost**: ~$10-20/month (heavy summarization)
**Memory**: Full user intent + summarized responses

---

### Preset 4: Aggressive Filtering (Low-bandwidth)
**Use case**: Constrained resources, minimal LLM costs
```json
{
  "enabled": true,
  "watch_path": null,
  "inactivity_timeout": 120,
  "check_interval": 30,
  "auto_summarize": false,
  "store_in_graph": true,
  "keep_length_days": 3,
  "filter": {
    "tool_calls": true,
    "tool_content": "omit",
    "user_messages": "full",
    "agent_messages": "omit"
  }
}
```
**Token reduction**: ~85%
**LLM cost**: $0/month (no summarization)
**Memory**: User prompts + tool structure only

---

### Preset 5: No Filtering (Debug/Archive)
**Use case**: Debugging, archival, full session replay
```json
{
  "enabled": true,
  "watch_path": "/path/to/specific/project",
  "inactivity_timeout": 300,
  "check_interval": 60,
  "auto_summarize": false,
  "store_in_graph": true,
  "keep_length_days": null,
  "filter": {
    "tool_calls": true,
    "tool_content": "full",
    "user_messages": "full",
    "agent_messages": "full"
  }
}
```
**Token reduction**: 0%
**LLM cost**: $0/month (no summarization)
**Memory**: Complete session history preserved

---

## Parameter Tuning Guide

### Performance Tuning

#### Realtime Responsiveness
```json
"inactivity_timeout": 30,
"check_interval": 10
```
- Session closes 30-40 seconds after last activity
- **Use case**: Active development, frequent context switches

#### Balanced Performance
```json
"inactivity_timeout": 45,
"check_interval": 15
```
- Session closes 45-60 seconds after last activity
- **Use case**: General development (RECOMMENDED)

#### Conservative Performance
```json
"inactivity_timeout": 120,
"check_interval": 30
```
- Session closes 2-3 minutes after last activity
- **Use case**: Battery-saving, low CPU usage

---

### Rolling Period Tuning

#### Short Window (Active projects only)
```json
"keep_length_days": 3
```
- Only tracks sessions modified in last 3 days
- **Use case**: Prevent old project pollution

#### Medium Window (Recommended)
```json
"keep_length_days": 7
```
- Tracks last week of activity
- **Use case**: General use, cost-effective

#### Long Window (Research projects)
```json
"keep_length_days": 30
```
- Tracks last month of activity
- **Use case**: Long-running research, historical context

#### Unlimited (Expert mode)
```json
"keep_length_days": null
```
- Tracks ALL sessions (no time filtering)
- **WARNING**: Can index 1000+ old sessions on first run
- **Use case**: Archive mode, full history needed

---

### Filter Tuning

#### Maximum Token Reduction (~85%)
```json
"filter": {
  "tool_calls": true,
  "tool_content": "omit",
  "user_messages": "full",
  "agent_messages": "omit"
}
```
- Keeps user prompts + tool structure only
- **Use case**: Minimal storage, cost-conscious

#### Balanced Reduction (~50%)
```json
"filter": {
  "tool_calls": true,
  "tool_content": "summary",
  "user_messages": "full",
  "agent_messages": "summary"
}
```
- Summarizes tools and agent responses
- **Use case**: Good balance of memory vs cost

#### Minimal Reduction (~35%)
```json
"filter": {
  "tool_calls": true,
  "tool_content": "summary",
  "user_messages": "full",
  "agent_messages": "full"
}
```
- Only summarizes tool results
- **Use case**: Preserve conversation flow

#### No Reduction (0%)
```json
"filter": {
  "tool_calls": true,
  "tool_content": "full",
  "user_messages": "full",
  "agent_messages": "full"
}
```
- Complete session preservation
- **Use case**: Archival, debugging

---

## Migration from Current Defaults

### Current v1.0.0 Defaults (UNSAFE)
```json
{
  "enabled": true,              // ❌ Opt-out model
  "watch_path": null,           // ❌ Watches all projects
  "inactivity_timeout": 300,    // ⚠️  Slow (5 minutes)
  "check_interval": 60,         // ⚠️  Not used (bug)
  "auto_summarize": true,       // ❌ LLM costs by default
  "store_in_graph": true,       // ✅ OK
  "filter": {
    "tool_calls": true,         // ✅ OK
    "tool_content": "summary",  // ⚠️  Still uses LLM
    "user_messages": "full",    // ✅ OK
    "agent_messages": "full"    // ✅ OK
  }
}
```

### New Safe Defaults (RECOMMENDED)
```json
{
  "enabled": false,             // ✅ Opt-in model
  "watch_path": null,           // ✅ User must configure
  "inactivity_timeout": 45,     // ✅ Realtime-like
  "check_interval": 15,         // ✅ Responsive (bug fix)
  "auto_summarize": false,      // ✅ No LLM costs
  "store_in_graph": true,       // ✅ OK
  "keep_length_days": 7,        // ✅ NEW - Rolling window
  "filter": {
    "tool_calls": true,         // ✅ OK
    "tool_content": "omit",     // ✅ 60% reduction, no LLM
    "user_messages": "full",    // ✅ OK
    "agent_messages": "full"    // ✅ OK
  }
}
```

---

## Auto-Generated Config Template

**Location**: `~/.graphiti/graphiti.config.json`

**Full template with ALL parameters and comments**:
```json
{
  "_comment": "Graphiti MCP Server Configuration (auto-generated)",
  "_docs": "https://github.com/getzep/graphiti/blob/main/CONFIGURATION.md",
  "_version": "1.0.0",
  
  "database": {
    "_comment": "Neo4j database connection (REQUIRED)",
    "uri": "bolt://localhost:7687",
    "user": "neo4j",
    "password": "CHANGE_ME"
  },
  
  "llm": {
    "_comment": "LLM configuration for entity extraction (REQUIRED)",
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "CHANGE_ME"
  },
  
  "session_tracking": {
    "_comment": "Session tracking is DISABLED by default for security",
    "_docs": "https://github.com/getzep/graphiti/blob/main/docs/SESSION_TRACKING_USER_GUIDE.md",
    
    "enabled": false,
    "_enabled_help": "Set to true to enable session tracking (opt-in)",
    
    "watch_path": null,
    "_watch_path_help": "null = ~/.claude/projects/ | Set to specific project path",
    
    "inactivity_timeout": 45,
    "_inactivity_timeout_help": "Seconds before session closed (30-60 = realtime, 120-300 = conservative)",
    
    "check_interval": 15,
    "_check_interval_help": "Seconds between checks (10-15 = responsive, 30-60 = conservative)",
    
    "auto_summarize": false,
    "_auto_summarize_help": "Use LLM to summarize sessions (costs money, set to true to enable)",
    
    "store_in_graph": true,
    "_store_in_graph_help": "Store in Neo4j graph (required for cross-session memory)",
    
    "keep_length_days": 7,
    "_keep_length_days_help": "Track sessions from last N days (3-30 recommended, null = all)",
    
    "filter": {
      "_comment": "Message filtering for token reduction",
      
      "tool_calls": true,
      "_tool_calls_help": "Preserve tool structure (recommended: true)",
      
      "tool_content": "omit",
      "_tool_content_help": "full (no filter) | summary (1-line, needs LLM) | omit (remove, 60% reduction)",
      
      "user_messages": "full",
      "_user_messages_help": "full (preserve) | summary (condense) | omit (remove)",
      
      "agent_messages": "full",
      "_agent_messages_help": "full (preserve) | summary (condense) | omit (remove)"
    }
  }
}
```

---

## Validation Rules

### Required Fields
- `enabled`: bool
- `inactivity_timeout`: int > 0
- `check_interval`: int > 0
- `auto_summarize`: bool
- `store_in_graph`: bool
- `filter.tool_calls`: bool
- `filter.tool_content`: "full" | "summary" | "omit"
- `filter.user_messages`: "full" | "summary" | "omit"
- `filter.agent_messages`: "full" | "summary" | "omit"

### Optional Fields
- `watch_path`: string | null
- `keep_length_days`: int > 0 | null

### Constraints
- `inactivity_timeout >= check_interval` (recommended, not enforced)
- `check_interval >= 10` (minimum for system responsiveness)
- `inactivity_timeout >= 30` (minimum for session stability)
- `keep_length_days >= 1` or null (if set)

---

**Template Status**: Complete reference for all available parameters
