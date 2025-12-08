# Implementation Plan: Unified Configuration System for Graphiti

## Overview

Replace scattered configuration (environment variables + separate filter config) with a **single unified JSON configuration file** (`graphiti.config.json`) that consolidates:

- ✅ Database backend selection (Neo4j, FalkorDB)
- ✅ LLM provider chain (OpenAI, Azure OpenAI, Anthropic)
- ✅ Embedder configuration
- ✅ Memory filter settings (LLM-based filtering)
- ✅ Project-specific preferences
- ✅ Search, logging, performance, and MCP server settings

## Key Benefits

1. **Single Source of Truth** - All configuration in one place
2. **Version Controlled** - Project-specific settings in git
3. **Environment Isolation** - Sensitive data (API keys, passwords) stay in env vars
4. **Database Flexibility** - Easy switching between Neo4j and FalkorDB
5. **Clear Defaults** - Graceful fallback to sensible defaults
6. **Type Safety** - Pydantic validation for all config values

---

## Architecture Changes

### Before (Fragmented)

```
Configuration Sources:
├── .env (17 variables)
│   ├── NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
│   ├── OPENAI_API_KEY, MODEL_NAME
│   ├── AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION
│   ├── ANTHROPIC_API_KEY
│   ├── SEMAPHORE_LIMIT
│   └── ... many more
│
├── graphiti-filter.config.json (filter only)
│   └── LLM filter providers, session config, categories
│
└── Hardcoded defaults in graphiti_mcp_server.py
```

**Problems:**
- Configuration scattered across 3+ locations
- Difficult to understand full configuration
- No database backend switching
- Duplicate LLM provider specifications
- Hard to version control sensitive vs non-sensitive config

### After (Unified)

```
Configuration Sources:
├── graphiti.config.json (ALL settings)
│   ├── database: { backend, neo4j, falkordb }
│   ├── llm: { provider, models, openai, azure_openai, anthropic }
│   ├── embedder: { provider, model, openai, azure_openai }
│   ├── memory_filter: { enabled, llm_filter, rule_based_filter }
│   ├── project: { group_id, entity_types, max_reflexion }
│   ├── search: { max_nodes, max_facts, method, weights }
│   ├── logging: { level, filters, format }
│   ├── performance: { parallel, caching }
│   └── mcp_server: { host, port, cors }
│
├── .env (ONLY sensitive data - API keys, passwords)
│   ├── NEO4J_PASSWORD
│   ├── FALKORDB_PASSWORD
│   ├── OPENAI_API_KEY
│   ├── ANTHROPIC_API_KEY
│   ├── AZURE_OPENAI_API_KEY
│   └── AZURE_OPENAI_ENDPOINT
│
└── unified_config.py (Pydantic models + loader)
    └── GraphitiConfig.from_file() -> loads + validates + applies env overrides
```

**Benefits:**
- ✅ Single config file for all structural settings
- ✅ Environment variables only for secrets
- ✅ Easy database switching: `"backend": "neo4j"` → `"backend": "falkordb"`
- ✅ Version controlled (gitignore .env, commit graphiti.config.json)
- ✅ Type-safe with Pydantic validation
- ✅ Graceful defaults + search order (project → global → defaults)

---

## Configuration File Structure

### Root: `graphiti.config.json`

```json
{
  "version": "1.0.0",
  "database": { ... },
  "llm": { ... },
  "embedder": { ... },
  "memory_filter": { ... },
  "project": { ... },
  "search": { ... },
  "logging": { ... },
  "performance": { ... },
  "mcp_server": { ... }
}
```

### Section 1: Database Configuration

**Purpose**: Select backend and configure connection settings

```json
{
  "database": {
    "backend": "neo4j",  // "neo4j" | "falkordb"

    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password_env": "NEO4J_PASSWORD",  // References env var
      "database": "neo4j",
      "pool_size": 50,
      "connection_timeout": 30,
      "max_connection_lifetime": 3600
    },

    "falkordb": {
      "uri": "redis://localhost:6379",
      "user": "default",
      "password_env": "FALKORDB_PASSWORD",
      "database": "graphiti",
      "pool_size": 50
    }
  }
}
```

**Key Features:**
- `backend` field selects active database
- Each backend has its own config section
- Passwords reference env vars via `*_env` pattern
- Connection pooling and timeout settings

### Section 2: LLM Configuration

**Purpose**: Configure primary LLM provider for graph operations

```json
{
  "llm": {
    "provider": "openai",  // "openai" | "azure_openai" | "anthropic"
    "default_model": "gpt-4.1-mini",
    "small_model": "gpt-4.1-nano",
    "temperature": 0.0,
    "semaphore_limit": 10,
    "max_retries": 3,
    "timeout": 60,

    "openai": {
      "api_key_env": "OPENAI_API_KEY",
      "base_url": null,
      "organization": null
    },

    "azure_openai": {
      "endpoint_env": "AZURE_OPENAI_ENDPOINT",
      "api_key_env": "AZURE_OPENAI_API_KEY",
      "api_version": "2025-01-01-preview",
      "deployment_name": null,
      "use_managed_identity": false
    },

    "anthropic": {
      "api_key_env": "ANTHROPIC_API_KEY",
      "base_url": null
    }
  }
}
```

**Key Features:**
- `provider` field selects active LLM
- All provider configs present (only active one used)
- Semaphore limit for rate limiting
- Environment variable references for API keys

### Section 3: Embedder Configuration

**Purpose**: Configure embedding provider for vector search

```json
{
  "embedder": {
    "provider": "openai",  // "openai" | "azure_openai"
    "model": "text-embedding-3-small",
    "dimensions": 1536,
    "batch_size": 100,

    "openai": {
      "api_key_env": "OPENAI_API_KEY"
    },

    "azure_openai": {
      "endpoint_env": "AZURE_OPENAI_EMBEDDING_ENDPOINT",
      "api_key_env": "AZURE_OPENAI_EMBEDDING_API_KEY",
      "api_version": "2023-05-15",
      "deployment_name": null,
      "use_managed_identity": false
    }
  }
}
```

### Section 4: Memory Filter Configuration

**Purpose**: LLM-based intelligent memory filtering (replaces old graphiti-filter.config.json)

```json
{
  "memory_filter": {
    "enabled": true,
    "mode": "llm",  // "llm" | "rule_based" | "hybrid"

    "llm_filter": {
      "providers": [
        {
          "name": "openai",
          "model": "gpt-4o-mini",
          "api_key_env": "OPENAI_API_KEY",
          "temperature": 0.0,
          "max_tokens": 200,
          "enabled": true,
          "priority": 1
        },
        {
          "name": "anthropic",
          "model": "claude-haiku-3-5-20241022",
          "api_key_env": "ANTHROPIC_API_KEY",
          "temperature": 0.0,
          "max_tokens": 200,
          "enabled": true,
          "priority": 2
        }
      ],

      "session": {
        "max_context_tokens": 5000,
        "auto_cleanup": true,
        "session_timeout_minutes": 60
      },

      "categories": {
        "store": [
          "env-quirk",
          "user-pref",
          "external-api",
          "historical-context",
          "cross-project",
          "workaround"
        ],
        "skip": [
          "bug-in-code",
          "config-in-repo",
          "docs-added",
          "first-success"
        ]
      }
    },

    "rule_based_filter": {
      "enabled": false,
      "rules": []
    }
  }
}
```

**Key Features:**
- Subsumes old `graphiti-filter.config.json`
- Hierarchical provider fallback (OpenAI → Anthropic)
- Session management for context tracking
- Extensible to rule-based filtering

### Section 5: Project Configuration

**Purpose**: Project-specific preferences and metadata

```json
{
  "project": {
    "default_group_id": null,
    "namespace": null,
    "enable_entity_types": true,
    "custom_entity_types": ["Requirement", "Preference", "Procedure"],
    "max_reflexion_iterations": 3
  }
}
```

### Section 6: Search Configuration

**Purpose**: Default search behavior

```json
{
  "search": {
    "default_max_nodes": 10,
    "default_max_facts": 10,
    "default_method": "hybrid_rrf",  // "hybrid_rrf" | "hybrid_node_distance" | "vector" | "text"
    "vector_weight": 0.7,
    "text_weight": 0.3
  }
}
```

### Section 7: Logging Configuration

**Purpose**: Logging behavior and verbosity

```json
{
  "logging": {
    "level": "INFO",  // "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
    "log_filter_decisions": true,
    "log_llm_calls": false,
    "log_database_queries": false,
    "log_file": null,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

### Section 8: Performance Configuration

**Purpose**: Performance tuning and caching

```json
{
  "performance": {
    "use_parallel_runtime": true,
    "enable_caching": true,
    "cache_ttl_seconds": 3600
  }
}
```

### Section 9: MCP Server Configuration

**Purpose**: MCP server runtime settings

```json
{
  "mcp_server": {
    "host": null,
    "port": null,
    "enable_cors": false,
    "allowed_origins": []
  }
}
```

---

## Environment Variables (Minimal Set)

**Purpose**: ONLY sensitive data (passwords, API keys)

```bash
# Database passwords
NEO4J_PASSWORD=your_neo4j_password
FALKORDB_PASSWORD=your_falkordb_password

# LLM API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Azure OpenAI (if using)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_EMBEDDING_API_KEY=your_azure_embedding_key

# Optional overrides (rarely needed)
MODEL_NAME=gpt-4.1-mini          # Override default model
SMALL_MODEL_NAME=gpt-4.1-nano    # Override small model
EMBEDDER_MODEL_NAME=text-embedding-3-small
LLM_TEMPERATURE=0.0
SEMAPHORE_LIMIT=10
GRAPHITI_DB_BACKEND=neo4j        # Override database backend
GROUP_ID=my_project              # Override default group ID
```

**Reduced from 17+ variables to ~5-8 core variables!**

---

## Configuration Loading Logic

### Search Order

When `GraphitiConfig.from_file()` is called:

1. **Project-local**: `./graphiti.config.json` (working directory)
2. **Global**: `~/.claude/graphiti.config.json` (user home)
3. **Defaults**: Built-in defaults in `unified_config.py`

### Loading Flow

```python
from mcp_server.unified_config import get_config

# Load config (searches project → global → defaults)
config = get_config()

# Access specific settings
db_config = config.database.get_active_config()  # Gets neo4j or falkordb
llm_provider = config.llm.get_active_provider_config()  # Gets openai/azure/anthropic
filter_enabled = config.memory_filter.enabled

# Environment overrides are automatically applied
# (e.g., MODEL_NAME env var overrides config.llm.default_model)
```

### Environment Override Pattern

Config file sets **structure and defaults**, environment variables provide **secrets and overrides**:

```python
# In unified_config.py
class GraphitiConfig(BaseModel):
    # ... fields ...

    def apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        if model_name := os.environ.get("MODEL_NAME"):
            self.llm.default_model = model_name

        if db_backend := os.environ.get("GRAPHITI_DB_BACKEND"):
            self.database.backend = db_backend

        # ... other overrides
```

**Pattern**: Config file = project settings, env vars = deployment overrides

---

## Implementation Phases

### Phase 1: Core Configuration System ✅

**Status**: COMPLETE

Files created:
- ✅ `graphiti.config.json` - Complete unified config schema
- ✅ `mcp_server/unified_config.py` - Pydantic models + loader

Components:
- ✅ `DatabaseConfig` with Neo4j and FalkorDB support
- ✅ `LLMConfig` with OpenAI, Azure OpenAI, Anthropic
- ✅ `EmbedderConfig` with OpenAI and Azure OpenAI
- ✅ `MemoryFilterConfig` (subsumes old filter config)
- ✅ `ProjectConfig`, `SearchConfig`, `LoggingConfig`, etc.
- ✅ `GraphitiConfig` root model with validation
- ✅ Config loading with search order (project → global → defaults)
- ✅ Environment override system

### Phase 2: MCP Server Integration

**Goal**: Replace scattered env var reads with unified config

**Tasks**:
- [ ] Update `graphiti_mcp_server.py` imports
  ```python
  from mcp_server.unified_config import get_config
  ```

- [ ] Replace `initialize_graphiti()` config loading
  - Old: Individual `os.environ.get()` calls
  - New: `config = get_config()`

- [ ] Update LLM client initialization
  - Use `config.llm.get_active_provider_config()`
  - Support all three providers (OpenAI, Azure, Anthropic)

- [ ] Update embedder initialization
  - Use `config.embedder.get_active_config()`

- [ ] Update database connection
  - Use `config.database.get_active_config()`
  - Support both Neo4j and FalkorDB

- [ ] Initialize memory filter system
  - Use `config.memory_filter.llm_filter`
  - Create `SessionManager` and `FilterManager`

- [ ] Add `should_store` MCP tool (from original plan)

**Files to modify**:
- `mcp_server/graphiti_mcp_server.py` (~200 lines changed)

**Estimated effort**: 2-3 hours

### Phase 3: Filter System Integration

**Goal**: Complete LLM-based memory filtering implementation

**Tasks**:
- [ ] Create `mcp_server/llm_provider.py` (from original plan)
  - `LLMProvider` abstract base class
  - `OpenAIProvider` implementation
  - `AnthropicProvider` implementation
  - Use config from `config.memory_filter.llm_filter.providers`

- [ ] Create `mcp_server/session_manager.py`
  - `Session` class for context tracking
  - `SessionManager` for session lifecycle
  - Use config from `config.memory_filter.llm_filter.session`

- [ ] Create `mcp_server/filter_manager.py`
  - `FilterManager` with LLM-based filtering logic
  - Use categories from `config.memory_filter.llm_filter.categories`

- [ ] Add `should_store` tool to MCP server
  - Integrate with `FilterManager`
  - Return filter decision with category and reason

**Files to create**:
- `mcp_server/llm_provider.py` (new)
- `mcp_server/session_manager.py` (new)
- `mcp_server/filter_manager.py` (new)

**Files to modify**:
- `mcp_server/graphiti_mcp_server.py` (add tool)

**Estimated effort**: 3-4 hours

### Phase 4: Documentation Updates

**Tasks**:
- [ ] Update `README.md`
  - Document new unified config system
  - Explain config search order
  - Show example config customization
  - Document database backend switching

- [ ] Update `.env.example`
  - Reduce to minimal set (passwords + API keys)
  - Remove structural config variables
  - Add comments explaining config file vs env vars

- [ ] Create `CONFIGURATION.md`
  - Complete configuration reference
  - All sections with descriptions
  - Common configuration patterns
  - Migration guide from old system

- [ ] Update `CLAUDE.md` (last step)
  - Add `should_store` usage pattern
  - Document unified config approach
  - Update GRAPHITI section

**Estimated effort**: 2 hours

### Phase 5: Migration & Cleanup

**Tasks**:
- [ ] Create migration script `scripts/migrate-to-unified-config.py`
  - Read old `.env` file
  - Generate `graphiti.config.json` from env vars
  - Preserve only sensitive data in new `.env`
  - Backup old config

- [ ] Deprecate old config files
  - Mark `graphiti-filter.config.json` as deprecated
  - Add deprecation warning if old config detected

- [ ] Update `.gitignore`
  ```
  # Environment (sensitive data only)
  .env
  .env.local

  # Config (version controlled)
  # graphiti.config.json  <- NOT ignored, commit this!

  # Old deprecated configs
  graphiti-filter.config.json  # Deprecated
  ```

- [ ] Clean up unused environment variable reads
  - Search for remaining `os.environ.get()` calls
  - Replace or document as intentional overrides

**Files to create**:
- `scripts/migrate-to-unified-config.py`
- `MIGRATION.md`

**Estimated effort**: 2 hours

### Phase 6: Testing

**Tasks**:
- [ ] Unit tests for `unified_config.py`
  - Test config loading (project → global → defaults)
  - Test environment overrides
  - Test validation (invalid values)
  - Test database backend switching
  - Test provider selection

- [ ] Integration tests for MCP server
  - Test with Neo4j backend
  - Test with FalkorDB backend
  - Test with different LLM providers
  - Test memory filter system

- [ ] End-to-end tests
  - Complete workflow with unified config
  - Config reload behavior
  - Error handling and graceful degradation

**Files to create**:
- `tests/test_unified_config.py`
- `tests/test_config_integration.py`

**Estimated effort**: 3-4 hours

---

## Migration Guide (Old → New)

### For Existing Users

**Step 1: Install migration script**

```bash
cd /path/to/graphiti
python scripts/migrate-to-unified-config.py
```

**Step 2: Review generated config**

The script will:
1. Read your current `.env` file
2. Generate `graphiti.config.json` with your settings
3. Create new `.env` with only sensitive data
4. Backup old files to `.env.backup` and `graphiti-filter.config.backup`

**Step 3: Customize config (optional)**

Edit `graphiti.config.json` to:
- Switch database backend: `"backend": "falkordb"`
- Change LLM provider: `"provider": "anthropic"`
- Adjust memory filter settings
- Configure search defaults

**Step 4: Test**

```bash
# Start MCP server with new config
python -m mcp_server.graphiti_mcp_server

# Check logs for config loading
# Should see: "Loading config from: ./graphiti.config.json"
```

### Manual Migration

If you prefer manual migration:

**Old `.env`**:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secretpass
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4.1-mini
SEMAPHORE_LIMIT=10
```

**New `graphiti.config.json`**:
```json
{
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
    "semaphore_limit": 10
  }
}
```

**New `.env`** (only secrets):
```bash
NEO4J_PASSWORD=secretpass
OPENAI_API_KEY=sk-...
```

---

## Configuration Examples

### Example 1: Neo4j + OpenAI (Default)

```json
{
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
    "default_model": "gpt-4.1-mini"
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small"
  }
}
```

### Example 2: FalkorDB + Anthropic

```json
{
  "database": {
    "backend": "falkordb",
    "falkordb": {
      "uri": "redis://localhost:6379",
      "password_env": "FALKORDB_PASSWORD",
      "database": "my_graph"
    }
  },
  "llm": {
    "provider": "anthropic",
    "default_model": "claude-sonnet-3-5-20241022",
    "anthropic": {
      "api_key_env": "ANTHROPIC_API_KEY"
    }
  }
}
```

### Example 3: Azure OpenAI + Memory Filter Disabled

```json
{
  "llm": {
    "provider": "azure_openai",
    "default_model": "gpt-4o",
    "azure_openai": {
      "endpoint_env": "AZURE_OPENAI_ENDPOINT",
      "api_key_env": "AZURE_OPENAI_API_KEY",
      "deployment_name": "gpt-4o-deployment"
    }
  },
  "memory_filter": {
    "enabled": false
  }
}
```

### Example 4: Production Settings

```json
{
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt+s://production.neo4j.io:7687",
      "user": "graphiti_app",
      "password_env": "NEO4J_PASSWORD",
      "pool_size": 100,
      "connection_timeout": 60
    }
  },
  "llm": {
    "provider": "openai",
    "semaphore_limit": 50,
    "max_retries": 5,
    "timeout": 120
  },
  "logging": {
    "level": "WARNING",
    "log_filter_decisions": true,
    "log_file": "/var/log/graphiti/mcp_server.log"
  },
  "performance": {
    "use_parallel_runtime": true,
    "enable_caching": true,
    "cache_ttl_seconds": 7200
  }
}
```

---

## Files Summary

### New Files

| File | Purpose | Status |
|------|---------|--------|
| `graphiti.config.json` | Root unified configuration | ✅ Created |
| `mcp_server/unified_config.py` | Pydantic models + loader | ✅ Created |
| `mcp_server/llm_provider.py` | LLM provider abstraction (filter) | ⏳ Pending |
| `mcp_server/session_manager.py` | Filter session management | ⏳ Pending |
| `mcp_server/filter_manager.py` | Filter logic + LLM calls | ⏳ Pending |
| `scripts/migrate-to-unified-config.py` | Migration script | ⏳ Pending |
| `CONFIGURATION.md` | Complete config reference | ⏳ Pending |
| `MIGRATION.md` | Migration guide | ⏳ Pending |

### Modified Files

| File | Changes | Status |
|------|---------|--------|
| `mcp_server/graphiti_mcp_server.py` | Replace env vars with config | ⏳ Pending |
| `.env.example` | Reduce to minimal set | ⏳ Pending |
| `README.md` | Document unified config | ⏳ Pending |
| `.gitignore` | Update config patterns | ⏳ Pending |
| `CLAUDE.md` | Update GRAPHITI section | ⏳ Pending |

### Deprecated Files

| File | Replacement | Action |
|------|-------------|--------|
| `graphiti-filter.config.json` | `graphiti.config.json` → `memory_filter` | Mark deprecated |
| Multiple `.env.example` files | Single root `.env.example` | Consolidate |

---

## Validation & Error Handling

### Config Validation

Pydantic automatically validates:
- ✅ Required fields present
- ✅ Type correctness (string, int, bool, enum)
- ✅ Value constraints (e.g., `temperature` between 0-2)
- ✅ Enum values (e.g., `backend` must be `"neo4j"` or `"falkordb"`)

Example error:
```python
# Invalid config
{"database": {"backend": "postgres"}}  # Not supported

# Pydantic error
ValidationError: 1 validation error for GraphitiConfig
database.backend
  Input should be 'neo4j' or 'falkordb' (type=literal_error)
```

### Missing Config Handling

```python
# No config file found
# → Logs warning
# → Uses built-in defaults
# → Server still starts

logger.warning("No config file found, using defaults")
config = GraphitiConfig._default_config()
```

### Missing Environment Variables

```python
# API key not set
# → Property returns None
# → Provider initialization fails
# → Falls back to next provider OR logs error

if not provider.api_key:
    logger.error(f"{provider.name} API key not found in environment")
    # Graceful degradation
```

---

## Best Practices

### ✅ DO

1. **Version control your config**: Commit `graphiti.config.json` to git
2. **Keep secrets in env vars**: Never commit API keys or passwords
3. **Use project-local config**: Override global config with project-specific settings
4. **Document custom settings**: Add comments in JSON (if supported) or separate docs
5. **Test config changes**: Validate with `GraphitiConfig.from_file()` before deploying

### ❌ DON'T

1. **Don't commit `.env`**: Always in `.gitignore`
2. **Don't hardcode secrets**: Use `*_env` pattern for sensitive data
3. **Don't use env vars for structure**: Use config file for all non-sensitive settings
4. **Don't mix old and new**: Migrate completely, don't use both systems

---

## Next Steps

1. ✅ **Phase 1 Complete** - Core configuration system created
2. **Phase 2** - Integrate with MCP server (replace env var reads)
3. **Phase 3** - Implement memory filter system
4. **Phase 4** - Update documentation
5. **Phase 5** - Create migration script
6. **Phase 6** - Testing

**Ready to proceed with Phase 2** (MCP server integration)?

---

**Author**: Claude Code
**Date**: 2025-11-03
**Version**: v2.0 (Unified Configuration)
