# Unified Configuration System - Summary

## What Changed?

Replaced scattered configuration (17+ env vars + separate filter config) with **one unified JSON file** (`graphiti.config.json`).

---

## Quick Comparison

### Before ❌

```
Configuration spread across:
├── .env (17+ variables)
├── mcp_server/.env.example
├── server/.env.example
├── graphiti-filter.config.json
└── Hardcoded defaults in code
```

**Problems:**
- Hard to understand full configuration
- Can't easily switch databases
- Mixing secrets with structure
- Not version controlled

### After ✅

```
Configuration in:
├── graphiti.config.json (all settings - VERSION CONTROLLED)
└── .env (5-8 secrets only - GITIGNORED)
```

**Benefits:**
- Single source of truth
- Easy database/LLM switching
- Clear separation: config vs secrets
- Type-safe validation
- Graceful defaults

---

## Example: Before & After

### Before (Old System)

**.env** (17 variables):
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secretpass
OPENAI_API_KEY=sk-abc123
MODEL_NAME=gpt-4.1-mini
SMALL_MODEL_NAME=gpt-4.1-nano
EMBEDDER_MODEL_NAME=text-embedding-3-small
SEMAPHORE_LIMIT=10
LLM_TEMPERATURE=0.0
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
# ... and more
```

**graphiti-filter.config.json** (separate file):
```json
{
  "filter": {
    "enabled": true,
    "providers": [...]
  }
}
```

### After (New System)

**graphiti.config.json** (one file, version controlled):
```json
{
  "version": "1.0.0",
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password_env": "NEO4J_PASSWORD"
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4.1-mini",
    "small_model": "gpt-4.1-nano",
    "semaphore_limit": 10,
    "temperature": 0.0,
    "openai": {
      "api_key_env": "OPENAI_API_KEY"
    }
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small"
  },
  "memory_filter": {
    "enabled": true,
    "llm_filter": {
      "providers": [
        {
          "name": "openai",
          "model": "gpt-4o-mini",
          "api_key_env": "OPENAI_API_KEY",
          "priority": 1
        },
        {
          "name": "anthropic",
          "model": "claude-haiku-3-5-20241022",
          "api_key_env": "ANTHROPIC_API_KEY",
          "priority": 2
        }
      ]
    }
  }
}
```

**.env** (only secrets):
```bash
NEO4J_PASSWORD=secretpass
OPENAI_API_KEY=sk-abc123
ANTHROPIC_API_KEY=sk-ant-abc123
```

**Result:**
- From 17+ env vars → 3 env vars (secrets only)
- From 3+ files → 2 files (config + env)
- All structure in version-controlled JSON

---

## Key Features

### 1. Database Backend Switching

**Change one field** to switch databases:

```json
// Neo4j
"database": { "backend": "neo4j" }

// FalkorDB
"database": { "backend": "falkordb" }
```

### 2. LLM Provider Switching

**Change one field** to switch LLM providers:

```json
// OpenAI
"llm": { "provider": "openai" }

// Azure OpenAI
"llm": { "provider": "azure_openai" }

// Anthropic
"llm": { "provider": "anthropic" }
```

### 3. Memory Filter Control

**Built into main config**:

```json
"memory_filter": {
  "enabled": true,    // ← Toggle on/off
  "mode": "llm",      // ← LLM-based filtering
  "llm_filter": {
    "providers": [    // ← Hierarchical fallback
      {"name": "openai", "priority": 1},
      {"name": "anthropic", "priority": 2}
    ]
  }
}
```

### 4. Type-Safe Validation

**Pydantic validates all settings**:

```python
# Invalid config
{"database": {"backend": "postgres"}}

# Automatic validation error
ValidationError: database.backend must be 'neo4j' or 'falkordb'
```

### 5. Config Search Order

**Automatic precedence**:

1. `./graphiti.config.json` (project - highest priority)
2. `~/.claude/graphiti.config.json` (global)
3. Built-in defaults (fallback)
4. Environment variable overrides (for specific values)

---

## Configuration Sections

| Section | Purpose |
|---------|---------|
| `database` | Backend selection (Neo4j, FalkorDB) + connection settings |
| `llm` | Primary LLM provider for graph operations |
| `embedder` | Embedding provider for vector search |
| `memory_filter` | LLM-based intelligent memory filtering |
| `project` | Project-specific preferences (group_id, entity types) |
| `search` | Default search behavior (max nodes, methods, weights) |
| `logging` | Logging level, filters, output format |
| `performance` | Parallel runtime, caching settings |
| `mcp_server` | MCP server host, port, CORS |

---

## Common Tasks

### Switch from Neo4j to FalkorDB

```bash
# 1. Edit config
nano graphiti.config.json

# 2. Change backend
"database": { "backend": "falkordb" }

# 3. Add FalkorDB password to .env
echo "FALKORDB_PASSWORD=your_password" >> .env

# 4. Restart server
python -m mcp_server.graphiti_mcp_server
```

### Use Anthropic Instead of OpenAI

```bash
# 1. Edit config
nano graphiti.config.json

# 2. Change provider
"llm": { "provider": "anthropic" }

# 3. Ensure API key in .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# 4. Restart server
```

### Disable Memory Filtering

```bash
# Edit config
nano graphiti.config.json

# Set enabled to false
"memory_filter": { "enabled": false }

# Restart server
```

---

## Files Created

### Core System (Phase 1 - ✅ Complete)

| File | Purpose | Status |
|------|---------|--------|
| `graphiti.config.json` | Unified configuration schema | ✅ Created |
| `mcp_server/unified_config.py` | Pydantic models + loader | ✅ Created |
| `IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md` | Complete implementation plan | ✅ Created |
| `MIGRATION_GUIDE.md` | Migration instructions | ✅ Created |
| `UNIFIED_CONFIG_SUMMARY.md` | This summary | ✅ Created |

### Pending Implementation (Phases 2-6)

| File | Purpose | Status |
|------|---------|--------|
| `mcp_server/llm_provider.py` | LLM provider abstraction | ⏳ Phase 3 |
| `mcp_server/session_manager.py` | Session management | ⏳ Phase 3 |
| `mcp_server/filter_manager.py` | Filter logic | ⏳ Phase 3 |
| `scripts/migrate-to-unified-config.py` | Auto-migration script | ⏳ Phase 5 |
| `CONFIGURATION.md` | Complete config reference | ⏳ Phase 4 |

### Modified Files (Pending)

| File | Changes | Status |
|------|---------|--------|
| `mcp_server/graphiti_mcp_server.py` | Use unified config | ⏳ Phase 2 |
| `.env.example` | Minimal secrets template | ⏳ Phase 4 |
| `README.md` | Document unified config | ⏳ Phase 4 |
| `CLAUDE.md` | Update GRAPHITI section | ⏳ Phase 6 |

---

## Next Steps

### For Users

1. **Read**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for migration instructions
2. **Migrate**: Run migration script or manual migration
3. **Test**: Verify config loads and server starts
4. **Customize**: Adjust settings for your use case
5. **Commit**: Add `graphiti.config.json` to version control

### For Developers

**Phase 2**: MCP Server Integration (Next)
- [ ] Update `graphiti_mcp_server.py` to use `unified_config.py`
- [ ] Replace env var reads with config access
- [ ] Support all database backends and LLM providers
- [ ] Initialize memory filter system

**Phase 3**: Filter Implementation
- [ ] Create `llm_provider.py`, `session_manager.py`, `filter_manager.py`
- [ ] Add `should_store` MCP tool
- [ ] Implement hierarchical provider fallback

**Phase 4**: Documentation
- [ ] Update README.md
- [ ] Create CONFIGURATION.md
- [ ] Update .env.example

**Phase 5**: Migration Tooling
- [ ] Create auto-migration script
- [ ] Test migration with real configs

**Phase 6**: Testing
- [ ] Unit tests for unified_config.py
- [ ] Integration tests for MCP server
- [ ] End-to-end tests

---

## Design Decisions

### Why JSON instead of YAML/TOML?

- ✅ Native Python support (no extra dependencies)
- ✅ Pydantic model_dump() generates valid JSON
- ✅ JSON Schema validation support
- ✅ Widely understood format
- ❌ YAML: More complex parsing, security issues
- ❌ TOML: Less common, fewer tools

### Why Pydantic Models?

- ✅ Type-safe validation
- ✅ Auto-generated JSON schema
- ✅ Clear error messages
- ✅ IDE autocomplete support
- ✅ Easy testing with mock configs

### Why Environment Variables for Secrets?

- ✅ Never committed to version control
- ✅ Standard practice (12-factor app)
- ✅ Easy rotation without code changes
- ✅ Works with Docker, Kubernetes, CI/CD
- ✅ Separate concerns (config vs secrets)

### Why Config File for Structure?

- ✅ Easy to read and understand
- ✅ Version controlled (track changes)
- ✅ Type-safe validation
- ✅ IDE-friendly (autocomplete, validation)
- ✅ Shareable defaults

---

## Benefits Summary

### Before (Scattered Config)

- ❌ 17+ environment variables
- ❌ 3+ configuration files
- ❌ Hard to switch databases/providers
- ❌ Mixing secrets with structure
- ❌ No validation
- ❌ Hard to version control
- ❌ No clear defaults

### After (Unified Config)

- ✅ 5-8 environment variables (secrets only)
- ✅ 1 configuration file + 1 env file
- ✅ Easy switching (change one field)
- ✅ Clear separation (config vs secrets)
- ✅ Type-safe validation
- ✅ Version controlled config
- ✅ Graceful defaults with fallback

---

## Questions?

**Migration help**: See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

**Configuration reference**: See [IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md)

**Implementation details**: See [mcp_server/unified_config.py](mcp_server/unified_config.py)

**Issues**: https://github.com/getzep/graphiti/issues

---

**Status**: Phase 1 Complete (Core System) ✅

**Next**: Phase 2 (MCP Server Integration) ⏳

**Author**: Claude Code

**Date**: 2025-11-03

**Version**: v1.0
