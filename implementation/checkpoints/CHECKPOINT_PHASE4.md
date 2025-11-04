# Phase 4 Checkpoint: Documentation Updates

**Status**: 📅 Pending
**Progress**: 0/4 tasks complete (0%)
**Estimated Time**: 2 hours
**Dependencies**: Phase 3 complete

---

## 🎯 Objective
Update user-facing documentation for unified config and filter systems.

## ✅ Prerequisites
- [ ] Phase 3 complete (`phase-3-complete` tag exists)
- [ ] Filter system tested with real configurations
- [ ] Both Neo4j and FalkorDB backends tested

---

## 📋 Tasks

### Task 4.1: Update README.md ⏱️ 30 min
**File**: `README.md` (root)

#### Subtasks
- [ ] Add "Configuration" section with quick start
- [ ] Link to `implementation/guides/UNIFIED_CONFIG_SUMMARY.md`
- [ ] Add example: copy config template, set env vars, start server
- [ ] Link to migration guide for existing users
- [ ] Update installation section to mention config file

**Template** (add after installation):
```markdown
## Configuration

Graphiti uses unified configuration (`graphiti.config.json`).

### Quick Start
1. Copy template: `cp implementation/config/graphiti.config.json .`
2. Set secrets in `.env`: `NEO4J_PASSWORD=xxx` `OPENAI_API_KEY=xxx`
3. Start: `python -m mcp_server.graphiti_mcp_server`

See [Configuration Guide](implementation/guides/UNIFIED_CONFIG_SUMMARY.md) for details.

### Migration
Migrating from .env? See [Migration Guide](implementation/guides/MIGRATION_GUIDE.md).
```

---

### Task 4.2: Update .env.example ⏱️ 15 min
**File**: `.env.example` (root)

#### Subtasks
- [ ] Simplify to minimal set (5-8 variables)
- [ ] Add header: "Only secrets - config in graphiti.config.json"
- [ ] Include: NEO4J_PASSWORD, FALKORDB_PASSWORD, OPENAI_API_KEY, ANTHROPIC_API_KEY
- [ ] Note Azure variables as optional
- [ ] Add comment: prefer graphiti.config.json for non-secret settings

**Template**:
```bash
# Graphiti Environment Configuration
# Secrets only - structural config in graphiti.config.json

# Database Passwords
NEO4J_PASSWORD=your_password
FALKORDB_PASSWORD=your_password  # Optional

# LLM API Keys
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key  # Optional: fallback

# Azure OpenAI (Optional)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_key
```

---

### Task 4.3: Create CONFIGURATION.md ⏱️ 45 min
**File**: `CONFIGURATION.md` (NEW, root)

#### Subtasks
- [ ] Create comprehensive config reference
- [ ] Document all sections: database, llm, embedder, memory_filter
- [ ] Provide examples for each backend/provider
- [ ] Explain environment variable overrides
- [ ] Add troubleshooting section
- [ ] Link to detailed implementation plans

#### Complete CONFIGURATION.md Template

**Copy this complete template to create `CONFIGURATION.md`:**

```markdown
# Graphiti Configuration Reference

Complete documentation for `graphiti.config.json` - the unified configuration system for Graphiti.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration File Structure](#configuration-file-structure)
4. [Database Configuration](#database-configuration)
5. [LLM Configuration](#llm-configuration)
6. [Embedder Configuration](#embedder-configuration)
7. [Memory Filter Configuration](#memory-filter-configuration)
8. [Project Configuration](#project-configuration)
9. [Search Configuration](#search-configuration)
10. [Environment Variable Overrides](#environment-variable-overrides)
11. [Complete Examples](#complete-examples)
12. [Troubleshooting](#troubleshooting)

---

## Overview

Graphiti uses a **unified configuration system** where all structural settings are in `graphiti.config.json` and only secrets (passwords, API keys) are in `.env`.

### Benefits

- **Single source of truth** for configuration
- **Type-safe** with Pydantic validation
- **Version controlled** (graphiti.config.json is committed)
- **Environment overrides** for deployment flexibility
- **Backend switching** without code changes

### File Locations

Configuration files are searched in this order:
1. `./graphiti.config.json` (project directory)
2. `~/.claude/graphiti.config.json` (global)
3. Built-in defaults (in `mcp_server/unified_config.py`)

---

## Quick Start

### 1. Copy Template
```bash
cp implementation/config/graphiti.config.json graphiti.config.json
```

### 2. Create .env with Secrets
```bash
cat > .env << 'EOF'
NEO4J_PASSWORD=your_neo4j_password
OPENAI_API_KEY=sk-your-openai-key
EOF
```

### 3. Start Server
```bash
python -m mcp_server.graphiti_mcp_server
```

The server will:
1. Load `graphiti.config.json`
2. Apply environment overrides from `.env`
3. Validate configuration
4. Initialize components

---

## Configuration File Structure

```json
{
  "database": { /* Database backend settings */ },
  "llm": { /* LLM provider settings */ },
  "embedder": { /* Embedder settings */ },
  "memory_filter": { /* Memory filtering settings */ },
  "project": { /* Project metadata */ },
  "search": { /* Search parameters */ },
  "logging": { /* Logging configuration */ }
}
```

---

## Database Configuration

### Overview

Graphiti supports multiple graph database backends:
- **Neo4j** (default) - Community or Enterprise Edition
- **FalkorDB** - Redis-based graph database

### Backend Selection

```json
{
  "database": {
    "backend": "neo4j",  // or "falkordb"
    "neo4j": { /* Neo4j config */ },
    "falkordb": { /* FalkorDB config */ }
  }
}
```

### Neo4j Configuration

```json
{
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password": "${NEO4J_PASSWORD}",  // From .env
      "database": "neo4j"
    }
  }
}
```

**Fields:**
- `uri` - Connection URI (bolt://, neo4j://, bolt+s://)
- `user` - Database username
- `password` - Use `${ENV_VAR}` syntax for secrets
- `database` - Database name (default: "neo4j")

**Environment Override:**
```bash
export NEO4J_URI=bolt://production-server:7687
export NEO4J_USER=admin
export NEO4J_PASSWORD=secure_password
```

### FalkorDB Configuration

```json
{
  "database": {
    "backend": "falkordb",
    "falkordb": {
      "uri": "redis://localhost:6379",
      "password": "${FALKORDB_PASSWORD}",
      "graph_name": "graphiti"
    }
  }
}
```

**Fields:**
- `uri` - Redis connection URI
- `password` - Use `${ENV_VAR}` syntax
- `graph_name` - Name of the graph (default: "graphiti")

---

## LLM Configuration

### Overview

Graphiti supports multiple LLM providers:
- **OpenAI** (default)
- **Azure OpenAI**
- **Anthropic**

### Provider Selection

```json
{
  "llm": {
    "provider": "openai",  // "openai" | "azure_openai" | "anthropic"
    "default_model": "gpt-4o-mini",
    "temperature": 0.0,
    "max_tokens": 8192,
    "semaphore_limit": 10,
    "openai": { /* OpenAI config */ },
    "azure_openai": { /* Azure config */ },
    "anthropic": { /* Anthropic config */ }
  }
}
```

### OpenAI Configuration

```json
{
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "openai": {
      "api_key": "${OPENAI_API_KEY}",
      "base_url": null,  // Optional: custom endpoint
      "organization": null  // Optional: org ID
    }
  }
}
```

**Environment Override:**
```bash
export OPENAI_API_KEY=sk-your-key
export MODEL_NAME=gpt-4o  # Override default_model
```

### Azure OpenAI Configuration

```json
{
  "llm": {
    "provider": "azure_openai",
    "default_model": "gpt-4",
    "azure_openai": {
      "api_key": "${AZURE_OPENAI_API_KEY}",
      "endpoint": "${AZURE_OPENAI_ENDPOINT}",
      "api_version": "2024-02-15-preview",
      "deployment_name": "gpt-4-deployment"
    }
  }
}
```

**Fields:**
- `endpoint` - Azure resource endpoint (e.g., https://your-resource.openai.azure.com)
- `deployment_name` - Name of your deployment
- `api_version` - API version (see Azure docs)

### Anthropic Configuration

```json
{
  "llm": {
    "provider": "anthropic",
    "default_model": "claude-3-5-sonnet-20241022",
    "anthropic": {
      "api_key": "${ANTHROPIC_API_KEY}",
      "base_url": null
    }
  }
}
```

---

## Embedder Configuration

### Overview

Embedders generate vector representations for semantic search.

### Supported Providers

- **OpenAI** (default) - text-embedding-3-small
- **Azure OpenAI** - Azure-hosted embeddings

### OpenAI Embedder

```json
{
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "embedding_dim": 1536,
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  }
}
```

**Fields:**
- `model` - Embedding model name
- `embedding_dim` - Dimension of embeddings (1536 for text-embedding-3-small)

### Azure OpenAI Embedder

```json
{
  "embedder": {
    "provider": "azure_openai",
    "model": "text-embedding-ada-002",
    "embedding_dim": 1536,
    "azure_openai": {
      "api_key": "${AZURE_OPENAI_API_KEY}",
      "endpoint": "${AZURE_OPENAI_ENDPOINT}",
      "api_version": "2024-02-15-preview",
      "deployment_name": "embedding-deployment"
    }
  }
}
```

---

## Memory Filter Configuration

### Overview

The memory filter uses LLM-based intelligent filtering to decide what should be stored in long-term memory.

### Configuration Structure

```json
{
  "memory_filter": {
    "enabled": true,
    "llm_filter": {
      "providers": [
        {
          "name": "openai-primary",
          "provider": "openai",
          "model": "gpt-4o-mini",
          "api_key": "${OPENAI_API_KEY}",
          "max_queries_per_session": 50
        },
        {
          "name": "anthropic-fallback",
          "provider": "anthropic",
          "model": "claude-3-5-haiku-20241022",
          "api_key": "${ANTHROPIC_API_KEY}",
          "max_queries_per_session": 50
        }
      ],
      "session": {
        "max_context_size": 10000,
        "context_cleanup_threshold": 8000
      },
      "categories": {
        "store": ["user-pref", "env-quirk", "external-api", "project-decision"],
        "skip": ["bug-in-code", "config-in-repo", "docs-added", "ephemeral"]
      }
    }
  }
}
```

### Fields

**memory_filter:**
- `enabled` - Enable/disable filtering (boolean)

**providers:** (hierarchical fallback)
- `name` - Provider identifier
- `provider` - "openai" or "anthropic"
- `model` - Model to use for filtering
- `api_key` - Use `${ENV_VAR}` syntax
- `max_queries_per_session` - Rotate after N queries

**session:**
- `max_context_size` - Max tokens to track per session
- `context_cleanup_threshold` - Reset context when reached

**categories:**
- `store` - Categories that should be stored
- `skip` - Categories that should be skipped

### Usage Example

```python
# Via MCP tool
result = await should_store(
    content="User prefers dark mode",
    context="UI preferences discussion"
)
# Returns: {"should_store": true, "category": "user-pref", "reason": "..."}
```

---

## Project Configuration

```json
{
  "project": {
    "name": "my-project",
    "version": "1.0.0"
  }
}
```

---

## Search Configuration

```json
{
  "search": {
    "limit": 10,
    "num_episodes": 5,
    "num_results": 10
  }
}
```

**Fields:**
- `limit` - Default result limit
- `num_episodes` - Episodes to retrieve
- `num_results` - Search results to return

---

## Environment Variable Overrides

### Override Priority

1. Environment variables (highest)
2. `graphiti.config.json` file
3. Built-in defaults (lowest)

### Supported Overrides

| Environment Variable | Config Path | Type | Example |
|---------------------|-------------|------|---------|
| `GRAPHITI_DB_BACKEND` | `database.backend` | string | `neo4j` |
| `NEO4J_URI` | `database.neo4j.uri` | string | `bolt://localhost:7687` |
| `NEO4J_USER` | `database.neo4j.user` | string | `neo4j` |
| `NEO4J_PASSWORD` | `database.neo4j.password` | string | `password` |
| `NEO4J_DATABASE` | `database.neo4j.database` | string | `neo4j` |
| `MODEL_NAME` | `llm.default_model` | string | `gpt-4o` |
| `OPENAI_API_KEY` | `llm.openai.api_key` | string | `sk-...` |
| `ANTHROPIC_API_KEY` | `llm.anthropic.api_key` | string | `sk-ant-...` |
| `AZURE_OPENAI_ENDPOINT` | `llm.azure_openai.endpoint` | string | `https://...` |
| `AZURE_OPENAI_API_KEY` | `llm.azure_openai.api_key` | string | `...` |
| `EMBEDDER_MODEL_NAME` | `embedder.model` | string | `text-embedding-3-small` |
| `SEMAPHORE_LIMIT` | `llm.semaphore_limit` | int | `10` |

### Usage

```bash
# Override in environment
export MODEL_NAME=gpt-4o
export SEMAPHORE_LIMIT=20

# Or inline
MODEL_NAME=gpt-4o python -m mcp_server.graphiti_mcp_server
```

---

## Complete Examples

### Example 1: Neo4j + OpenAI (Default)

```json
{
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password": "${NEO4J_PASSWORD}",
      "database": "neo4j"
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "temperature": 0.0,
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "embedding_dim": 1536,
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  },
  "memory_filter": {
    "enabled": true
  }
}
```

**.env:**
```bash
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=sk-your-key
```

### Example 2: FalkorDB + Azure OpenAI

```json
{
  "database": {
    "backend": "falkordb",
    "falkordb": {
      "uri": "redis://localhost:6379",
      "password": "${FALKORDB_PASSWORD}",
      "graph_name": "graphiti"
    }
  },
  "llm": {
    "provider": "azure_openai",
    "default_model": "gpt-4",
    "azure_openai": {
      "api_key": "${AZURE_OPENAI_API_KEY}",
      "endpoint": "${AZURE_OPENAI_ENDPOINT}",
      "api_version": "2024-02-15-preview",
      "deployment_name": "gpt-4-deployment"
    }
  },
  "embedder": {
    "provider": "azure_openai",
    "model": "text-embedding-ada-002",
    "embedding_dim": 1536,
    "azure_openai": {
      "api_key": "${AZURE_OPENAI_API_KEY}",
      "endpoint": "${AZURE_OPENAI_ENDPOINT}",
      "api_version": "2024-02-15-preview",
      "deployment_name": "embedding-deployment"
    }
  },
  "memory_filter": {
    "enabled": false
  }
}
```

**.env:**
```bash
FALKORDB_PASSWORD=your_password
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_azure_key
```

### Example 3: Neo4j + Anthropic (Filter Only)

```json
{
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password": "${NEO4J_PASSWORD}",
      "database": "neo4j"
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "embedding_dim": 1536,
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  },
  "memory_filter": {
    "enabled": true,
    "llm_filter": {
      "providers": [
        {
          "name": "anthropic-filter",
          "provider": "anthropic",
          "model": "claude-3-5-haiku-20241022",
          "api_key": "${ANTHROPIC_API_KEY}",
          "max_queries_per_session": 100
        }
      ]
    }
  }
}
```

**.env:**
```bash
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

---

## Troubleshooting

### Config Not Loading

**Symptom:** Server uses defaults despite config file existing

**Debug:**
```bash
# Check file exists
ls -la graphiti.config.json

# Validate JSON
python -c "import json; json.load(open('graphiti.config.json'))"

# Check loading
python -c "from mcp_server.unified_config import get_config; print(get_config())"
```

**Solution:** Ensure config file is in project root or `~/.claude/`

### Environment Variables Not Working

**Symptom:** API keys not found

**Debug:**
```bash
# Check .env exists
ls -la .env

# Check variables set
grep OPENAI_API_KEY .env

# Verify in Python
python -c "import os; print(os.environ.get('OPENAI_API_KEY', 'NOT SET'))"
```

**Solution:** Export variables or load .env before starting server

### Database Connection Fails

**Symptom:** Cannot connect to database

**Debug:**
```bash
# Check database running
docker ps | grep neo4j

# Test connection manually (Neo4j)
cypher-shell -a bolt://localhost:7687 -u neo4j -p your_password

# Check config
python -c "
from mcp_server.unified_config import get_config
db = get_config().database.get_active_config()
print(f'URI: {db.uri}')
print(f'User: {db.user}')
"
```

**Solution:** Start database, verify URI/credentials in config

### Filter System Not Working

**Symptom:** Memory filter not filtering

**Debug:**
```bash
# Check filter enabled
python -c "
from mcp_server.unified_config import get_config
print(f'Enabled: {get_config().memory_filter.enabled}')
"

# Check providers available
python -c "
from mcp_server.unified_config import get_config
config = get_config()
for p in config.memory_filter.llm_filter.providers:
    print(f'{p.name}: key={bool(p.api_key)}')
"
```

**Solution:** Enable in config, ensure API keys set

### Invalid Configuration

**Symptom:** Pydantic validation errors

**Common Issues:**
- Invalid backend: Use "neo4j" or "falkordb" (lowercase)
- Invalid provider: Use "openai", "azure_openai", or "anthropic"
- Missing required fields: Check error message
- Type mismatch: Ensure ints are ints, not strings

**Fix:**
```bash
# Validate against schema
python -c "
from mcp_server.unified_config import GraphitiConfig
import json

with open('graphiti.config.json') as f:
    config_data = json.load(f)

try:
    GraphitiConfig(**config_data)
    print('✅ Config valid')
except Exception as e:
    print(f'❌ Validation error: {e}')
"
```

### Migration Issues

**Symptom:** Migration script fails

**Solution:**
```bash
# Run in dry-run mode first
python implementation/scripts/migrate-to-unified-config.py --dry-run

# Check for backup files
ls -la .env.backup*

# Restore from backup if needed
cp .env.backup.20241103_120000 .env
```

---

## Additional Resources

- [Unified Config Implementation Plan](implementation/plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md)
- [Memory Filter Implementation Plan](implementation/plans/IMPLEMENTATION_PLAN_LLM_FILTER.md)
- [Migration Guide](implementation/guides/MIGRATION_GUIDE.md)
- [Quick Reference](implementation/guides/UNIFIED_CONFIG_SUMMARY.md)

---

**Last Updated:** 2025-11-03
**Version:** 2.0 (Unified Configuration)
```

#### Notes
- This template is complete and ready to use as-is
- All sections include practical examples
- Troubleshooting covers common issues
- Copy entire markdown block to create CONFIGURATION.md

---

### Task 4.4: Update CLAUDE.md ⏱️ 20 min
**File**: Root `CLAUDE.md` or `.claude/CLAUDE.md`

#### Subtasks
- [ ] Locate the `## TOOL DETAILS` section
- [ ] Find the `**g**: Store: prefs, conventions...` line
- [ ] Add filter integration documentation after it
- [ ] Add new workflow to `## WORKFLOWS` section

#### Detailed Instructions

**Step 1: Find TOOL DETAILS Section**

Locate this line in CLAUDE.md:
```markdown
**g**: Store: prefs, conventions, bugs, decisions, patterns | NOT: ephemeral, full-reports
```

**Step 2: Add Filter Documentation After It**

Add this content immediately after the existing `**g**:` line:

```markdown
**g**: Store: prefs, conventions, bugs, decisions, patterns | NOT: ephemeral, full-reports

### Graphiti Filter Integration (NEW)

**Before storing to memory, use the filter tool:**

```python
# Check if content should be stored
result = should_store(
    content="Description of what happened",
    context="Additional context (files changed, errors encountered, etc.)"
)

# Result structure:
{
    "should_store": true/false,
    "category": "user-pref|env-quirk|project-decision|skip",
    "confidence": 0.0-1.0,
    "reason": "Explanation of the decision"
}

# If should_store=true, proceed with storage
if result["should_store"]:
    g:add_memory(
        name="Descriptive name",
        episode_body=content,
        source="text",
        group_id="session-id"
    )
```

**Filter Categories:**

✅ **STORE** (non-redundant insights):
- `user-pref` - User preferences (dark mode, editor settings, etc.)
- `env-quirk` - Machine/OS-specific issues (can't fix in code)
- `external-api` - Third-party API quirks or undocumented behavior
- `project-decision` - Architectural decisions, conventions
- `workaround` - Non-obvious workarounds for limitations

❌ **SKIP** (already captured elsewhere):
- `bug-in-code` - Fixed bugs (now in version control)
- `config-in-repo` - Configuration now committed
- `docs-added` - Information now in README/docs
- `ephemeral` - Temporary issues, one-time events

**Configuration:**
- Config file: `graphiti.config.json` (memory_filter section)
- Enable/disable: `memory_filter.enabled: true/false`
- Providers: Hierarchical fallback (OpenAI → Anthropic)
```

**Step 3: Add Workflow Example**

Find the `## WORKFLOWS & ANTI-PATTERNS` section and add:

```markdown
### Graphiti Memory Storage Workflow (with Filter)

**Scenario:** User expresses a preference or you discover an environment quirk

1. **Capture the event**
   ```
   Event: "User prefers 2-space indentation for Python"
   Context: "Discussion about code formatting"
   ```

2. **Check if it should be stored**
   ```python
   result = should_store(
       content="User prefers 2-space indentation for Python files",
       context="Code formatting discussion, user explicitly stated preference"
   )
   ```

3. **Evaluate result**
   ```python
   if result["should_store"]:
       category = result["category"]  # Expected: "user-pref"
       reason = result["reason"]
   ```

4. **Store to memory**
   ```python
   g:add_memory(
       name="Python Indentation Preference",
       episode_body="User prefers 2-space indentation for Python files",
       source="message",
       source_description="user preference",
       group_id="user-preferences"
   )
   ```

**Anti-Pattern:**
❌ Don't blindly store everything:
```python
# BAD: No filtering
g:add_memory("Fixed bug in parser.py", ...)  # Already in git!
```

✅ Use filter first:
```python
# GOOD: Check before storing
result = should_store("Fixed bug in parser.py", "Committed to git")
if result["should_store"]:  # Will be False (bug-in-code)
    g:add_memory(...)  # Won't execute
```
```

---

## 🧪 Validation

- [ ] **V1**: All docs exist
  ```bash
  ls -la README.md .env.example CONFIGURATION.md
  ```

- [ ] **V2**: Links valid
  ```bash
  grep -r "implementation/" README.md CONFIGURATION.md
  ```

- [ ] **V3**: Bash examples run without errors
  ```bash
  # Extract and test bash snippets from docs
  ```

- [ ] **V4**: Config examples valid JSON
  ```bash
  # Validate JSON examples in docs
  ```

---

## 📝 Git Commit

```bash
git add README.md .env.example CONFIGURATION.md CLAUDE.md

git commit -m "Phase 4: Update documentation for unified config

- Add configuration section to README
- Simplify .env.example to minimal secrets
- Create comprehensive CONFIGURATION.md
- Update CLAUDE.md with filter integration

Refs: implementation/checkpoints/CHECKPOINT_PHASE4.md"

git tag -a phase-4-complete -m "Phase 4: Documentation Complete"
```

---

## 📊 Progress Tracking

- Task 4.1: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 4.2: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 4.3: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 4.4: [ ] Not Started | [ ] In Progress | [ ] Complete

**Time**: Estimated 2h | Actual: [fill in]

---

**Next**: [CHECKPOINT_PHASE5.md](CHECKPOINT_PHASE5.md)

**Last Updated**: 2025-11-03
