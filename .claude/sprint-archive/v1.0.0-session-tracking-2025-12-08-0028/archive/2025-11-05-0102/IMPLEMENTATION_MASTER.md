# Graphiti Implementation Master Plan

**🎯 Single Entry Point for Complete Implementation**

This document orchestrates the entire implementation of:
1. **Unified Configuration System** - Single config file for all settings
2. **LLM-Based Memory Filter** - Intelligent memory storage filtering

---

## ⚠️ CRITICAL: Read This First

**For Agents/Implementers:**

This is a **coordinated, multi-phase implementation** with dependencies between phases. Do not:
- ❌ Cherry-pick individual phases
- ❌ Skip validation steps
- ❌ Implement out of order
- ❌ Proceed with failing tests

**Always:**
- ✅ Read this entire document before starting
- ✅ Follow phases sequentially
- ✅ Validate after each phase
- ✅ Reference detailed plans as needed
- ✅ Test incrementally

**Estimated Total Time**: 12-15 hours

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Implementation Phases](#implementation-phases)
4. [Phase 1: Core Infrastructure](#phase-1-core-infrastructure-complete) ✅
5. [Phase 2: MCP Server Integration](#phase-2-mcp-server-integration-next) ⏳
6. [Phase 3: Filter System Implementation](#phase-3-filter-system-implementation)
7. [Phase 4: Documentation Updates](#phase-4-documentation-updates)
8. [Phase 5: Migration & Cleanup](#phase-5-migration--cleanup)
9. [Phase 6: Testing](#phase-6-testing)
10. [Validation & Verification](#validation--verification)
11. [Rollback Procedures](#rollback-procedures)
12. [Troubleshooting](#troubleshooting)

---

## System Overview

### What We're Building

**Before (Current State):**
```
Config scattered across:
├── .env (17+ variables)
├── mcp_server/.env.example
├── server/.env.example
├── graphiti-filter.config.json
└── Hardcoded defaults in code
```

**After (Target State):**
```
Unified configuration:
├── graphiti.config.json (all settings - version controlled)
├── .env (5-8 secrets only - gitignored)
└── mcp_server/unified_config.py (Pydantic loader)
    └── Used by all components
```

### Core Components

1. **Unified Config System** ([detailed plan](plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md))
   - Single `graphiti.config.json` for all settings
   - Type-safe Pydantic models with validation
   - Database backend selection (Neo4j, FalkorDB)
   - LLM provider selection (OpenAI, Azure, Anthropic)
   - Environment variable overrides for secrets

2. **Memory Filter System** ([detailed plan](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md))
   - LLM-based intelligent filtering
   - Session-scoped LLM instances
   - Hierarchical provider fallback
   - `should_store` MCP tool

### Dependencies

```
Phase 1: Core Infrastructure (✅ COMPLETE)
    ↓
Phase 2: MCP Server Integration (uses unified_config.py)
    ↓
Phase 3: Filter Implementation (uses config.memory_filter)
    ↓
Phase 4: Documentation
    ↓
Phase 5: Migration Scripts
    ↓
Phase 6: Testing (validates all phases)
```

**Key Dependency**: Phase 3 (Filter) **requires** Phase 2 (MCP Integration) to be complete.

---

## Prerequisites

### Before Starting

- [x] **Phase 1 Complete**: Core infrastructure exists
  - `implementation/config/graphiti.config.json`
  - `mcp_server/unified_config.py`
  - Implementation plans documented

- [ ] **Development Environment Ready**:
  ```bash
  # Verify Python environment
  python --version  # >= 3.10

  # Install dependencies
  poetry install

  # Verify tests run
  pytest tests/ -v
  ```

- [ ] **Git Repository Clean**:
  ```bash
  # Check status
  git status

  # Create implementation branch
  git checkout -b feature/unified-config-and-filter

  # Ensure no uncommitted changes
  git diff --exit-code
  ```

- [ ] **Backup Created**:
  ```bash
  # Create backup branch
  git branch backup/pre-unified-config

  # Tag current state
  git tag -a pre-unified-config -m "Before unified config implementation"
  ```

### Required Reading

**Mandatory before implementation:**

1. This document (IMPLEMENTATION_MASTER.md) - Complete read-through
2. [plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) - Sections: Architecture, Configuration File Structure
3. [plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) - Sections: Architecture, Component Design

**Reference during implementation:**
- Detailed implementation plans for specific phase instructions
- Migration guide for examples
- Configuration templates

---

## Implementation Phases

### Phase Status Overview

| Phase | Status | Estimated Time | Dependencies |
|-------|--------|----------------|--------------|
| **1. Core Infrastructure** | ✅ Complete | - | None |
| **2. MCP Server Integration** | ⏳ Next | 2-3 hours | Phase 1 |
| **3. Filter System** | 📅 Pending | 3-4 hours | Phase 2 |
| **4. Documentation** | 📅 Pending | 2 hours | Phase 3 |
| **5. Migration & Cleanup** | 📅 Pending | 2 hours | Phase 4 |
| **6. Testing** | 📅 Pending | 3-4 hours | Phase 5 |

---

## Phase 1: Core Infrastructure ✅ COMPLETE

### Status: ✅ Complete

**Deliverables Created:**
- ✅ `implementation/config/graphiti.config.json` - Unified config schema
- ✅ `mcp_server/unified_config.py` - Pydantic models + loader
- ✅ `implementation/plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md` - Detailed plan
- ✅ `implementation/plans/IMPLEMENTATION_PLAN_LLM_FILTER.md` - Filter plan
- ✅ `implementation/guides/MIGRATION_GUIDE.md` - Migration instructions
- ✅ `implementation/guides/UNIFIED_CONFIG_SUMMARY.md` - Quick reference

**Validation:**
```bash
# Verify files exist
ls -la implementation/config/graphiti.config.json
ls -la mcp_server/unified_config.py

# Validate config loads
python -c "from mcp_server.unified_config import get_config; print(get_config())"
```

**No further action needed for Phase 1.**

---

## Phase 2: MCP Server Integration ⏳ NEXT

### Objective

Replace scattered `os.environ.get()` calls in `graphiti_mcp_server.py` with unified config system.

### Prerequisites

- [x] Phase 1 complete
- [ ] Reviewed [plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) § Phase 2
- [ ] `mcp_server/unified_config.py` understood

### Tasks

#### Task 2.1: Update Imports

**File**: `mcp_server/graphiti_mcp_server.py`

**Action**: Add unified config import at top of file

**Location**: After existing imports (~line 38)

```python
# Add after: from graphiti_core.utils.maintenance.graph_data_operations import clear_data

from mcp_server.unified_config import get_config

# Load global config instance
config = get_config()
```

**Validation**:
```bash
python -c "from mcp_server.graphiti_mcp_server import config; print(config)"
```

#### Task 2.2: Update Database Connection

**File**: `mcp_server/graphiti_mcp_server.py`

**Function**: `initialize_graphiti()` (~line 450)

**Before** (scattered env vars):
```python
uri=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
user=os.environ.get('NEO4J_USER', 'neo4j'),
password=os.environ.get('NEO4J_PASSWORD', 'password'),
```

**After** (unified config):
```python
# Get active database config
db_config = config.database.get_active_config()

# Initialize driver with config
driver = AsyncGraphDatabase.driver(
    uri=db_config.uri,
    auth=(db_config.user, db_config.password),
    database=db_config.database if hasattr(db_config, 'database') else 'neo4j',
)
```

**Validation**:
```bash
# Test database connection with config
python -c "
from mcp_server.unified_config import get_config
config = get_config()
db = config.database.get_active_config()
print(f'Backend: {config.database.backend}')
print(f'URI: {db.uri}')
print(f'User: {db.user}')
"
```

#### Task 2.3: Update LLM Client Initialization

**File**: `mcp_server/graphiti_mcp_server.py`

**Function**: `get_llm_client()` (~line 200)

**Strategy**: Replace env var reads with config-based provider selection

**Before** (complex env var logic):
```python
model_env = os.environ.get('MODEL_NAME', '')
azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT', None)
# ... many more os.environ.get() calls
```

**After** (clean config-based):
```python
def get_llm_client(model_name: str | None = None) -> LLMClient:
    """Get LLM client based on unified config."""
    global config

    # Use provided model or default from config
    model = model_name or config.llm.default_model

    # Get active provider config
    provider = config.llm.provider

    if provider == "openai":
        provider_config = config.llm.openai
        return OpenAIClient(
            LLMConfig(
                api_key=provider_config.api_key,
                model=model,
                base_url=provider_config.base_url,
                organization=provider_config.organization,
                temperature=config.llm.temperature,
            )
        )

    elif provider == "azure_openai":
        provider_config = config.llm.azure_openai
        # Azure implementation (see detailed plan for full code)
        # ...

    elif provider == "anthropic":
        provider_config = config.llm.anthropic
        # Anthropic implementation (see detailed plan for full code)
        # ...

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
```

**Reference**: [plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) § Phase 2 § Update LLM Client Initialization for complete code.

**Validation**:
```bash
# Test LLM client creation
python -c "
from mcp_server.graphiti_mcp_server import get_llm_client
client = get_llm_client()
print(f'LLM Client: {client}')
"
```

#### Task 2.4: Update Embedder Initialization

**File**: `mcp_server/graphiti_mcp_server.py`

**Function**: `get_embedder()` (~line 360)

**Similar pattern to LLM client**:
- Replace `os.environ.get('EMBEDDER_MODEL_NAME')` with `config.embedder.model`
- Use `config.embedder.provider` for provider selection
- Get provider config via `config.embedder.get_active_config()`

**Reference**: [plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) § Phase 2 § Update Embedder Initialization

**Validation**:
```bash
# Test embedder creation
python -c "
from mcp_server.graphiti_mcp_server import get_embedder
embedder = get_embedder()
print(f'Embedder: {embedder}')
"
```

#### Task 2.5: Update Semaphore Limit

**File**: `mcp_server/graphiti_mcp_server.py`

**Location**: Global variable (~line 48)

**Before**:
```python
SEMAPHORE_LIMIT = int(os.getenv('SEMAPHORE_LIMIT', 10))
```

**After**:
```python
# Will be set after config loads
SEMAPHORE_LIMIT = 10  # Placeholder, updated in initialize_graphiti()

# In initialize_graphiti():
global SEMAPHORE_LIMIT
SEMAPHORE_LIMIT = config.llm.semaphore_limit
```

#### Task 2.6: Initialize Memory Filter System

**File**: `mcp_server/graphiti_mcp_server.py`

**Function**: `initialize_graphiti()` (~line 450)

**Add after database initialization**:

```python
# Initialize memory filter system (if enabled)
global filter_manager
if config.memory_filter.enabled:
    try:
        from mcp_server.session_manager import SessionManager
        from mcp_server.filter_manager import FilterManager

        session_manager = SessionManager(config.memory_filter.llm_filter)
        filter_manager = FilterManager(session_manager)
        logger.info("Memory filtering enabled")
    except ImportError:
        logger.warning("Filter system not yet implemented, filtering disabled")
        filter_manager = None
    except Exception as e:
        logger.error(f"Failed to initialize filter system: {e}")
        filter_manager = None
else:
    logger.info("Memory filtering disabled in config")
    filter_manager = None
```

**Note**: This prepares for Phase 3 but won't break if filter modules don't exist yet.

### Phase 2 Validation

**After completing all Task 2.x:**

```bash
# 1. Syntax check
python -m py_compile mcp_server/graphiti_mcp_server.py

# 2. Import check
python -c "from mcp_server import graphiti_mcp_server; print('✅ Imports OK')"

# 3. Config loading check
python -c "
from mcp_server.graphiti_mcp_server import config
print(f'✅ Config loaded: {config.database.backend}')
"

# 4. Server start test (should start without errors)
timeout 10 python -m mcp_server.graphiti_mcp_server || echo "✅ Server started"

# 5. Integration test
pytest tests/test_mcp_integration.py -v
```

**Expected Results:**
- ✅ No syntax errors
- ✅ Imports succeed
- ✅ Config loads correctly
- ✅ Server starts (may timeout, that's OK)
- ⚠️ Filter system logs "not yet implemented" (expected until Phase 3)

### Phase 2 Commit

```bash
# Stage changes
git add mcp_server/graphiti_mcp_server.py
git add mcp_server/unified_config.py

# Commit checkpoint
git commit -m "Phase 2: Integrate unified config into MCP server

- Replace os.environ.get() with config access
- Support database backend selection
- Support multiple LLM providers
- Prepare for memory filter system
- All tests passing

Refs: implementation/IMPLEMENTATION_MASTER.md"

# Tag checkpoint
git tag -a phase-2-complete -m "MCP Server Integration Complete"
```

**🎯 Proceed to Phase 3 only after validation passes.**

---

## Phase 3: Filter System Implementation

### Objective

Implement LLM-based memory filter system with hierarchical provider fallback.

### Prerequisites

- [x] Phase 2 complete and validated
- [ ] Reviewed [plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § Component Design
- [ ] API keys available (OPENAI_API_KEY or ANTHROPIC_API_KEY)

### Tasks

#### Task 3.1: Create LLM Provider Abstraction

**File**: `mcp_server/llm_provider.py` (NEW)

**Content**: Copy from [plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § LLM Provider Abstraction (lines 250-347)

**Key Components**:
- `LLMProvider` abstract base class
- `OpenAIProvider` implementation
- `AnthropicProvider` implementation
- `create_provider()` factory function

**Validation**:
```bash
# Test provider creation
python -c "
from mcp_server.unified_config import get_config
from mcp_server.llm_provider import create_provider

config = get_config()
for provider_config in config.memory_filter.llm_filter.providers:
    provider = create_provider(provider_config)
    print(f'✅ {provider_config.name}: available={provider.is_available()}')
"
```

#### Task 3.2: Create Session Manager

**File**: `mcp_server/session_manager.py` (NEW)

**Content**: Copy from [plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § Session Manager (lines 353-440)

**Key Components**:
- `Session` class (tracks context, query count)
- `SessionManager` class (manages session lifecycle)
- Session cleanup logic

**Validation**:
```bash
# Test session creation
python -c "
from mcp_server.unified_config import get_config
from mcp_server.session_manager import SessionManager

config = get_config()
session_mgr = SessionManager(config.memory_filter.llm_filter)
session = session_mgr.get_or_create_session()
print(f'✅ Session created: {session.session_id}')
print(f'✅ Provider: {session.provider.config.name}')
"
```

#### Task 3.3: Create Filter Manager

**File**: `mcp_server/filter_manager.py` (NEW)

**Content**: Copy from [plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § Filter Manager (lines 446-552)

**Key Components**:
- `FilterManager` class
- `should_store()` method
- Compact filter prompt
- Graceful degradation

**Validation**:
```bash
# Test filter decision
python -c "
import asyncio
from mcp_server.unified_config import get_config
from mcp_server.session_manager import SessionManager
from mcp_server.filter_manager import FilterManager

async def test():
    config = get_config()
    session_mgr = SessionManager(config.memory_filter.llm_filter)
    filter_mgr = FilterManager(session_mgr)

    # Test env-quirk (should store)
    result = await filter_mgr.should_store(
        'Neo4j timeout, fixed by setting NEO4J_TIMEOUT=60 in .env',
        'Edited .env (gitignored)'
    )
    print(f'✅ Env quirk: {result}')

    # Test bug-in-code (should skip)
    result = await filter_mgr.should_store(
        'Fixed infinite loop in parseData()',
        'Edited src/parser.py, committed'
    )
    print(f'✅ Bug fix: {result}')

asyncio.run(test())
"
```

#### Task 3.4: Add should_store MCP Tool

**File**: `mcp_server/graphiti_mcp_server.py`

**Location**: Add after existing MCP tools (~line 800)

**Content**: Copy from [plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § New MCP Tool (lines 589-650)

**Validation**:
```bash
# Test MCP tool registration
python -c "
from mcp_server.graphiti_mcp_server import mcp
print('✅ MCP tools:', [tool.name for tool in mcp.list_tools()])
assert 'should_store' in [tool.name for tool in mcp.list_tools()]
"
```

### Phase 3 Validation

**After completing all Task 3.x:**

```bash
# 1. Module imports
python -c "from mcp_server.llm_provider import LLMProvider; print('✅')"
python -c "from mcp_server.session_manager import SessionManager; print('✅')"
python -c "from mcp_server.filter_manager import FilterManager; print('✅')"

# 2. End-to-end filter test
python -c "
import asyncio
from mcp_server.unified_config import get_config
from mcp_server.session_manager import SessionManager
from mcp_server.filter_manager import FilterManager

async def test():
    config = get_config()
    if not config.memory_filter.enabled:
        print('⚠️  Filter disabled in config')
        return

    session_mgr = SessionManager(config.memory_filter.llm_filter)
    filter_mgr = FilterManager(session_mgr)

    result = await filter_mgr.should_store(
        'User prefers dark mode in all applications',
        'Conversation about UI preferences'
    )

    assert result['should_store'] == True, 'User pref should store'
    assert result['category'] == 'user-pref', 'Should be user-pref'
    print(f'✅ Filter working: {result}')

asyncio.run(test())
"

# 3. MCP tool test
pytest tests/test_filter_integration.py -v
```

**Expected Results:**
- ✅ All modules import successfully
- ✅ Filter makes correct decisions
- ✅ should_store tool callable via MCP
- ✅ Session management works
- ✅ Provider fallback works (if primary fails)

### Phase 3 Commit

```bash
git add mcp_server/llm_provider.py
git add mcp_server/session_manager.py
git add mcp_server/filter_manager.py
git add mcp_server/graphiti_mcp_server.py

git commit -m "Phase 3: Implement LLM-based memory filter system

- Add LLM provider abstraction (OpenAI, Anthropic)
- Add session management for context tracking
- Add filter manager with intelligent filtering
- Add should_store MCP tool
- Hierarchical provider fallback
- All tests passing

Refs: implementation/IMPLEMENTATION_MASTER.md"

git tag -a phase-3-complete -m "Filter System Implementation Complete"
```

**🎯 Proceed to Phase 4 only after validation passes.**

---

## Phase 4: Documentation Updates

### Objective

Update user-facing documentation to reflect unified config and filter systems.

### Prerequisites

- [x] Phase 3 complete and validated
- [ ] Tested with real configurations

### Tasks

#### Task 4.1: Update README.md

**File**: `README.md` (root)

**Changes**:
1. Add "Unified Configuration" section
2. Update installation instructions
3. Add configuration examples
4. Link to implementation/guides/

**Reference**: [plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) § Phase 4

**Template**:
```markdown
## Configuration

Graphiti uses a unified configuration system. All settings are in `graphiti.config.json`.

### Quick Start

1. Copy config template:
   ```bash
   cp implementation/config/graphiti.config.json graphiti.config.json
   ```

2. Set environment variables:
   ```bash
   export NEO4J_PASSWORD=your_password
   export OPENAI_API_KEY=sk-...
   ```

3. Start server:
   ```bash
   python -m mcp_server.graphiti_mcp_server
   ```

### Configuration Guide

See [implementation/guides/UNIFIED_CONFIG_SUMMARY.md](implementation/guides/UNIFIED_CONFIG_SUMMARY.md) for details.

### Migration

Migrating from old .env system? See [implementation/guides/MIGRATION_GUIDE.md](implementation/guides/MIGRATION_GUIDE.md).
```

#### Task 4.2: Update .env.example

**File**: `.env.example` (root)

**Simplify to minimal set**:

```bash
# Graphiti Environment Configuration
# Only sensitive data (passwords, API keys) - structural config in graphiti.config.json

# Database Passwords
NEO4J_PASSWORD=your_neo4j_password
FALKORDB_PASSWORD=your_falkordb_password  # Only if using FalkorDB

# LLM API Keys
OPENAI_API_KEY=sk-your_openai_api_key
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key  # Optional: for filter fallback

# Azure OpenAI (Optional - only if using Azure)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_azure_api_key

# Optional Overrides (rarely needed - prefer graphiti.config.json)
# MODEL_NAME=gpt-4.1-mini
# SEMAPHORE_LIMIT=10
# GRAPHITI_DB_BACKEND=neo4j
```

#### Task 4.3: Create CONFIGURATION.md

**File**: `CONFIGURATION.md` (root)

**Content**: Complete configuration reference with all sections documented

**Template**:
```markdown
# Graphiti Configuration Reference

Complete documentation for `graphiti.config.json`.

## Table of Contents
1. [Overview](#overview)
2. [Configuration Sections](#configuration-sections)
3. [Environment Variables](#environment-variables)
4. [Examples](#examples)
5. [Advanced Topics](#advanced-topics)

## Overview

Graphiti uses a unified JSON configuration file...

[See plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md for complete template]
```

#### Task 4.4: Update CLAUDE.md (Last Step)

**File**: Root `.claude/CLAUDE.md` or project `CLAUDE.md`

**Changes**:
1. Add unified config usage pattern
2. Document `should_store` tool usage
3. Update GRAPHITI section with filter integration

**Reference**: [plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § Phase 6

### Phase 4 Validation

```bash
# 1. Check all docs exist
ls -la README.md .env.example CONFIGURATION.md

# 2. Validate examples in docs
# Extract bash examples and run them

# 3. Check links work
grep -r "implementation/" README.md CONFIGURATION.md
```

### Phase 4 Commit

```bash
git add README.md .env.example CONFIGURATION.md

git commit -m "Phase 4: Update documentation for unified config

- Update README with configuration guide
- Simplify .env.example to minimal set
- Add comprehensive CONFIGURATION.md
- Update CLAUDE.md with new patterns

Refs: implementation/IMPLEMENTATION_MASTER.md"

git tag -a phase-4-complete -m "Documentation Updates Complete"
```

---

## Phase 5: Migration & Cleanup

### Objective

Create migration tooling and clean up deprecated files.

### Prerequisites

- [x] Phase 4 complete and validated
- [ ] Tested migration manually

### Tasks

#### Task 5.1: Create Migration Script

**File**: `implementation/scripts/migrate-to-unified-config.py` (NEW)

**Functionality**:
- Read current `.env` file
- Generate `graphiti.config.json` from env vars
- Create new `.env` with only secrets
- Backup old files

**Template**:
```python
#!/usr/bin/env python3
"""
Migrate from old scattered config to unified config system.

Usage:
    python implementation/scripts/migrate-to-unified-config.py
"""

import json
import os
from pathlib import Path
from datetime import datetime

def migrate():
    print("📦 Graphiti Configuration Migration Tool\n")

    # 1. Read old .env
    env_vars = read_env_file('.env')
    print(f"Found {len(env_vars)} environment variables")

    # 2. Generate graphiti.config.json
    config = generate_config_from_env(env_vars)

    # 3. Write config file
    with open('graphiti.config.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("✅ Generated: graphiti.config.json")

    # 4. Create new minimal .env
    new_env = extract_secrets(env_vars)
    with open('.env', 'w') as f:
        f.write(new_env)
    print("✅ Generated: .env (minimal)")

    # 5. Backup old files
    backup_old_files()
    print("✅ Backed up old config files")

    print("\n✨ Migration complete!")
    print("Next: Review graphiti.config.json and test your server")

if __name__ == '__main__':
    migrate()
```

**Validation**:
```bash
# Test migration script
cd /tmp/test-migration
cp /path/to/graphiti/.env .
python /path/to/graphiti/implementation/scripts/migrate-to-unified-config.py
cat graphiti.config.json
```

#### Task 5.2: Update .gitignore

**File**: `.gitignore`

**Add/Update**:
```bash
# Environment files (secrets)
.env
.env.local
.env.*.local

# Old deprecated configs (backed up, not committed)
graphiti-filter.config.json.backup
.env.backup*

# Config file is version controlled (DO NOT IGNORE)
# graphiti.config.json  <- Commit this!
```

#### Task 5.3: Deprecation Warnings

**File**: `mcp_server/graphiti_mcp_server.py`

**Add startup check**:
```python
def check_deprecated_config():
    """Warn if old config files detected."""
    if Path('graphiti-filter.config.json').exists():
        logger.warning(
            "⚠️  DEPRECATED: graphiti-filter.config.json detected\n"
            "   Please migrate to unified config: graphiti.config.json\n"
            "   See: implementation/guides/MIGRATION_GUIDE.md"
        )

    # Check for excessive env vars
    graphiti_env_vars = [k for k in os.environ if 'NEO4J' in k or 'MODEL' in k]
    if len(graphiti_env_vars) > 10:
        logger.warning(
            "⚠️  Many environment variables detected\n"
            "   Consider migrating to graphiti.config.json\n"
            "   See: implementation/guides/MIGRATION_GUIDE.md"
        )

# Call in initialize_graphiti()
check_deprecated_config()
```

### Phase 5 Validation

```bash
# 1. Test migration script
pytest tests/test_migration.py -v

# 2. Verify .gitignore
git check-ignore .env graphiti.config.json
# .env should be ignored, graphiti.config.json should NOT

# 3. Check deprecation warnings work
touch graphiti-filter.config.json
python -m mcp_server.graphiti_mcp_server 2>&1 | grep "DEPRECATED"
rm graphiti-filter.config.json
```

### Phase 5 Commit

```bash
git add implementation/scripts/migrate-to-unified-config.py
git add .gitignore
git add mcp_server/graphiti_mcp_server.py

git commit -m "Phase 5: Add migration tooling and cleanup

- Add auto-migration script
- Update .gitignore for new config system
- Add deprecation warnings for old config
- Migration guide tested and validated

Refs: implementation/IMPLEMENTATION_MASTER.md"

git tag -a phase-5-complete -m "Migration & Cleanup Complete"
```

---

## Phase 6: Testing

### Objective

Comprehensive testing of all components.

### Prerequisites

- [x] Phase 5 complete
- [ ] All manual testing passed

### Tasks

#### Task 6.1: Unit Tests for Config System

**File**: `tests/test_unified_config.py` (NEW)

**Tests**:
- Config loading (project → global → defaults)
- Environment variable overrides
- Validation (invalid values, missing fields)
- Database backend selection
- LLM provider selection
- Pydantic model validation

**Template**:
```python
import pytest
from mcp_server.unified_config import GraphitiConfig, get_config

def test_config_loads_defaults():
    """Test that default config loads without file."""
    config = GraphitiConfig._default_config()
    assert config.database.backend == "neo4j"
    assert config.llm.provider == "openai"

def test_config_validation():
    """Test that invalid configs raise errors."""
    with pytest.raises(ValueError):
        GraphitiConfig(database={"backend": "postgres"})

# ... more tests
```

#### Task 6.2: Integration Tests for MCP Server

**File**: `tests/test_mcp_integration.py` (UPDATE)

**Tests**:
- MCP server starts with unified config
- Database connection works
- LLM client creation works
- Memory filter system initializes
- should_store tool works

#### Task 6.3: Filter System Tests

**File**: `tests/test_filter_manager.py` (NEW)

**Tests**:
- Env-quirk detection (should store)
- Bug-in-code detection (should skip)
- User-pref detection (should store)
- Hierarchical fallback (OpenAI → Anthropic)
- Session cleanup
- Graceful degradation

**Reference**: [plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § Testing Plan

#### Task 6.4: End-to-End Tests

**File**: `tests/test_e2e_unified_config.py` (NEW)

**Tests**:
- Complete workflow with Neo4j backend
- Complete workflow with FalkorDB backend
- Config reload behavior
- Migration script execution
- Different LLM providers

### Phase 6 Validation

```bash
# 1. Run all tests
pytest tests/ -v --cov=mcp_server --cov-report=html

# 2. Check coverage
open htmlcov/index.html  # Should be >80%

# 3. Run specific test suites
pytest tests/test_unified_config.py -v
pytest tests/test_filter_manager.py -v
pytest tests/test_mcp_integration.py -v
pytest tests/test_e2e_unified_config.py -v

# 4. Integration test with real database
pytest tests/ -v -m integration
```

**Expected Results:**
- ✅ All tests passing
- ✅ Coverage > 80%
- ✅ No flaky tests
- ✅ Integration tests pass with real database

### Phase 6 Commit

```bash
git add tests/

git commit -m "Phase 6: Add comprehensive testing

- Unit tests for unified config system
- Integration tests for MCP server
- Filter system tests with LLM mocking
- End-to-end tests for complete workflows
- >80% code coverage achieved

Refs: implementation/IMPLEMENTATION_MASTER.md"

git tag -a phase-6-complete -m "Testing Complete - Implementation Done"
```

---

## Validation & Verification

### Complete System Validation

**After all phases complete:**

```bash
# 1. Clean checkout
git clone <repo> /tmp/graphiti-test
cd /tmp/graphiti-test
git checkout feature/unified-config-and-filter

# 2. Setup
cp implementation/config/graphiti.config.json .
cat > .env << 'EOF'
NEO4J_PASSWORD=demodemo
OPENAI_API_KEY=sk-your-key
EOF

# 3. Install
poetry install

# 4. Run tests
pytest tests/ -v

# 5. Start server
python -m mcp_server.graphiti_mcp_server

# 6. Test MCP tools
# (use MCP client to test add_memory, should_store, etc.)

# 7. Switch database backend
# Edit graphiti.config.json: "backend": "falkordb"
# Restart server, verify works

# 8. Switch LLM provider
# Edit graphiti.config.json: "provider": "anthropic"
# Restart server, verify works
```

**Success Criteria:**
- ✅ Server starts without errors
- ✅ Config loads from file
- ✅ Database connection works
- ✅ LLM operations work
- ✅ Memory filter works
- ✅ All MCP tools callable
- ✅ Backend switching works
- ✅ Provider switching works

---

## Rollback Procedures

### If Phase Fails

**Option 1: Revert to Last Checkpoint**
```bash
# Revert to previous phase tag
git reset --hard phase-2-complete  # Or phase-3-complete, etc.
```

**Option 2: Revert Specific Files**
```bash
# Revert only problematic file
git checkout HEAD~1 -- mcp_server/graphiti_mcp_server.py
```

**Option 3: Complete Rollback**
```bash
# Return to pre-implementation state
git checkout backup/pre-unified-config

# Or use tag
git checkout pre-unified-config
```

### Emergency Hotfix

If production is broken:

```bash
# 1. Immediately revert to last known good
git revert <commit-hash>

# 2. Or checkout old version
git checkout <old-tag> -- mcp_server/

# 3. Deploy hotfix
# ... deploy old working version

# 4. Debug offline
git checkout feature/unified-config-and-filter
# ... fix issues
# ... test thoroughly
# ... redeploy
```

---

## Troubleshooting

### Common Issues

#### Config Not Loading

**Symptom**: Server uses defaults despite config file existing

**Debug**:
```bash
# Check file exists
ls -la graphiti.config.json

# Validate JSON
python -c "import json; json.load(open('graphiti.config.json'))"

# Check loading
python -c "
from mcp_server.unified_config import get_config
config = get_config()
print(f'Loaded from: {config}')
"
```

**Solution**: Ensure config file in project root or `~/.claude/`

#### Environment Variables Not Working

**Symptom**: API keys not found

**Debug**:
```bash
# Check .env exists
ls -la .env

# Check variable set
grep OPENAI_API_KEY .env

# Load and verify
export $(cat .env | xargs)
echo $OPENAI_API_KEY
```

**Solution**: Ensure `.env` in project root, variables exported

#### Filter System Fails

**Symptom**: Memory filter not working

**Debug**:
```bash
# Check filter enabled
python -c "
from mcp_server.unified_config import get_config
print(get_config().memory_filter.enabled)
"

# Check providers available
python -c "
from mcp_server.unified_config import get_config
config = get_config()
for p in config.memory_filter.llm_filter.providers:
    print(f'{p.name}: key={bool(p.api_key)}')
"
```

**Solution**: Enable in config, ensure API keys set

#### Database Connection Fails

**Symptom**: Cannot connect to database

**Debug**:
```bash
# Check database running
docker ps | grep neo4j

# Test connection manually
cypher-shell -a bolt://localhost:7687 -u neo4j -p your_password

# Check config
python -c "
from mcp_server.unified_config import get_config
db = get_config().database.get_active_config()
print(f'URI: {db.uri}')
print(f'User: {db.user}')
"
```

**Solution**: Start database, verify URI/credentials in config

---

## Success Checklist

### Before Merging to Main

- [ ] **All phases complete** (1-6)
- [ ] **All tests passing** (pytest tests/ -v)
- [ ] **Code coverage > 80%**
- [ ] **Documentation updated** (README, CONFIGURATION.md)
- [ ] **Migration guide tested**
- [ ] **No deprecation warnings** (unless expected)
- [ ] **Clean git history** (squash if needed)
- [ ] **PR description complete**
- [ ] **Team review passed**

### Post-Merge Validation

- [ ] **CI/CD passes**
- [ ] **Integration tests pass** in CI
- [ ] **Docs deployed** (if auto-deployment)
- [ ] **Tagged release** (e.g., v2.0.0-unified-config)
- [ ] **Changelog updated**
- [ ] **Users notified** (breaking changes)

---

## Timeline & Effort

### Estimated Timeline (Sequential)

- Phase 2: 2-3 hours
- Phase 3: 3-4 hours
- Phase 4: 2 hours
- Phase 5: 2 hours
- Phase 6: 3-4 hours
- **Total: 12-15 hours** (1.5-2 work days)

### Parallelization Options

Some tasks can be parallelized:
- Phase 4 (docs) can start during Phase 3
- Phase 5 (migration script) can start during Phase 4
- Phase 6 (tests) should wait for all others

### Milestones

| Milestone | Deliverable | ETA |
|-----------|-------------|-----|
| Phase 2 Complete | MCP server uses unified config | +3h |
| Phase 3 Complete | Memory filter working | +7h |
| Phase 4 Complete | Docs updated | +9h |
| Phase 5 Complete | Migration tools ready | +11h |
| Phase 6 Complete | All tests passing | +15h |
| **Release Ready** | Merged to main | +15h |

---

## Summary

### What You've Built

After completing all phases:

1. ✅ **Unified Configuration System**
   - Single `graphiti.config.json` file
   - Type-safe Pydantic models
   - Database backend switching
   - LLM provider selection
   - Environment variable overrides

2. ✅ **Memory Filter System**
   - LLM-based intelligent filtering
   - Hierarchical provider fallback
   - Session management
   - `should_store` MCP tool

3. ✅ **Documentation**
   - Complete configuration reference
   - Migration guide
   - User guides
   - API documentation

4. ✅ **Tooling**
   - Auto-migration script
   - Deprecation warnings
   - Comprehensive tests

### What's Changed for Users

**Before**: 17+ environment variables, scattered config, manual setup
**After**: 1 config file + 5 secrets, easy switching, automated migration

### Next Steps

1. **Merge PR** to main branch
2. **Tag release** (v2.0.0 or similar)
3. **Update docs site** (if applicable)
4. **Notify users** of new config system
5. **Monitor** for issues in production

---

## Appendix

### Related Documents

- [Implementation Plan: Unified Config](plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md)
- [Implementation Plan: Memory Filter](plans/IMPLEMENTATION_PLAN_LLM_FILTER.md)
- [Migration Guide](guides/MIGRATION_GUIDE.md)
- [Configuration Summary](guides/UNIFIED_CONFIG_SUMMARY.md)

### Git Tags Reference

- `pre-unified-config` - Before implementation
- `phase-1-complete` - Core infrastructure
- `phase-2-complete` - MCP integration
- `phase-3-complete` - Filter implementation
- `phase-4-complete` - Documentation
- `phase-5-complete` - Migration & cleanup
- `phase-6-complete` - Testing (RELEASE READY)

### Command Cheat Sheet

```bash
# Start implementation
cd implementation/
cat IMPLEMENTATION_MASTER.md

# Run tests
pytest tests/ -v

# Validate config
python -c "from mcp_server.unified_config import get_config; print(get_config())"

# Start server
python -m mcp_server.graphiti_mcp_server

# Run migration
python implementation/scripts/migrate-to-unified-config.py
```

---

**🎯 Ready to Implement?**

1. Read this entire document
2. Ensure prerequisites met
3. Start with Phase 2
4. Follow sequentially
5. Validate after each phase

**Questions?** Review detailed plans in `implementation/plans/`

**Status**: Phase 1 Complete ✅ | Ready for Phase 2 ⏳

**Last Updated**: 2025-11-03

**Author**: Claude Code
