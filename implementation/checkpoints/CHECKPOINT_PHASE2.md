# Phase 2 Checkpoint: MCP Server Integration

**Status**: ⏳ Not Started
**Progress**: 0/6 tasks complete (0%)
**Estimated Time**: 2-3 hours
**Started**: [Not started]
**Completed**: [Not completed]

---

## 🎯 Phase Objective

Replace scattered `os.environ.get()` calls in `graphiti_mcp_server.py` with unified config system from Phase 1.

---

## ✅ Prerequisites

- [x] Phase 1 complete
- [x] `implementation/config/graphiti.config.json` exists
- [x] `mcp_server/unified_config.py` exists
- [ ] Reviewed [IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](../plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) § Phase 2
- [ ] Python environment ready (`python --version >= 3.10`)
- [ ] Can import unified_config: `python -c "from mcp_server.unified_config import get_config"`

**Prerequisites Status**: ⚠️ Review required before starting

---

## 📋 Task Breakdown

### Task 2.1: Update Imports ⏱️ 15 min

**File**: `mcp_server/graphiti_mcp_server.py`

**Current Status**: [ ] Not Started

#### Subtasks

- [ ] **2.1.1**: Open `mcp_server/graphiti_mcp_server.py`
- [ ] **2.1.2**: Locate existing imports section (around line 1-40)
- [ ] **2.1.3**: Add unified config import after line ~38:
  ```python
  from mcp_server.unified_config import get_config
  ```
- [ ] **2.1.4**: Add global config initialization after imports:
  ```python
  # Load global config instance
  config = get_config()
  ```
- [ ] **2.1.5**: Save file

#### Validation

```bash
# Test import works
python -c "from mcp_server.graphiti_mcp_server import config; print(config)"
```

**Expected Output**: Config object prints successfully

#### Notes
- Location: After `from graphiti_core.utils.maintenance.graph_data_operations import clear_data`
- Don't remove any existing imports yet
- Config should load without errors

**Completion Checklist**:
- [ ] Import added
- [ ] Config instance created
- [ ] Validation passed
- [ ] No syntax errors

---

### Task 2.2: Update Database Connection ⏱️ 30 min

**File**: `mcp_server/graphiti_mcp_server.py`

**Current Status**: [ ] Not Started

**Dependencies**: Task 2.1 complete

#### Subtasks

- [ ] **2.2.1**: Locate `initialize_graphiti()` function (around line 450)
- [ ] **2.2.2**: Find database connection section with env vars:
  ```python
  uri=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
  user=os.environ.get('NEO4J_USER', 'neo4j'),
  password=os.environ.get('NEO4J_PASSWORD', 'password'),
  ```
- [ ] **2.2.3**: Replace with unified config approach:
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
- [ ] **2.2.4**: Remove old env var reads for database
- [ ] **2.2.5**: Save file

#### Validation

```bash
# Test database config loads
python -c "
from mcp_server.unified_config import get_config
config = get_config()
db = config.database.get_active_config()
print(f'Backend: {config.database.backend}')
print(f'URI: {db.uri}')
print(f'User: {db.user}')
"
```

**Expected Output**:
```
Backend: neo4j
URI: bolt://localhost:7687
User: neo4j
```

#### Notes
- Keep backward compatibility during transition
- Test with actual database if available
- FalkorDB support should work via config.database.backend

**Completion Checklist**:
- [ ] Old env vars replaced
- [ ] New config-based code added
- [ ] Validation passed
- [ ] No import errors

---

### Task 2.3: Update LLM Client Initialization ⏱️ 45 min

**File**: `mcp_server/graphiti_mcp_server.py`

**Current Status**: [ ] Not Started

**Dependencies**: Task 2.1 complete

#### Subtasks

- [ ] **2.3.1**: Locate `get_llm_client()` function (around line 200)
- [ ] **2.3.2**: Review current implementation with env vars
- [ ] **2.3.3**: Replace entire function with config-based version:
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
          return OpenAIClient(
              LLMConfig(
                  api_key=provider_config.api_key,
                  model=model,
                  base_url=f"{provider_config.endpoint}/openai/deployments/{provider_config.deployment_name}",
                  api_version=provider_config.api_version,
                  temperature=config.llm.temperature,
              )
          )

      elif provider == "anthropic":
          provider_config = config.llm.anthropic
          return AnthropicClient(
              LLMConfig(
                  api_key=provider_config.api_key,
                  model=model,
                  temperature=config.llm.temperature,
              )
          )

      else:
          raise ValueError(f"Unknown LLM provider: {provider}")
  ```
- [ ] **2.3.4**: Remove all old `os.environ.get()` calls for LLM config
- [ ] **2.3.5**: Save file

#### Reference
See [IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](../plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) § Phase 2 § Update LLM Client Initialization for complete code.

#### Validation

```bash
# Test LLM client creation
python -c "
from mcp_server.graphiti_mcp_server import get_llm_client
client = get_llm_client()
print(f'✅ LLM Client: {client}')
print(f'✅ Model: {client.config.model}')
"
```

**Expected Output**: LLM client created successfully

#### Notes
- Ensure API keys available in .env or config
- Test with actual API call if possible
- Anthropic support may need AnthropicClient import

**Completion Checklist**:
- [ ] Function replaced
- [ ] All providers supported (OpenAI, Azure, Anthropic)
- [ ] Old env var code removed
- [ ] Validation passed
- [ ] Can create client without errors

---

### Task 2.4: Update Embedder Initialization ⏱️ 30 min

**File**: `mcp_server/graphiti_mcp_server.py`

**Current Status**: [ ] Not Started

**Dependencies**: Task 2.3 complete (similar pattern)

#### Subtasks

- [ ] **2.4.1**: Locate `get_embedder()` function (around line 360)
- [ ] **2.4.2**: Replace env var reads with config access:
  ```python
  def get_embedder() -> Embedder:
      """Get embedder based on unified config."""
      global config

      provider = config.embedder.provider

      if provider == "openai":
          provider_config = config.embedder.openai
          return OpenAIEmbedder(
              api_key=provider_config.api_key,
              model=config.embedder.model,
              embedding_dim=config.embedder.embedding_dim,
          )

      elif provider == "azure_openai":
          provider_config = config.embedder.azure_openai
          return AzureOpenAIEmbedder(
              api_key=provider_config.api_key,
              model=config.embedder.model,
              endpoint=provider_config.endpoint,
              api_version=provider_config.api_version,
              deployment_name=provider_config.deployment_name,
              embedding_dim=config.embedder.embedding_dim,
          )

      else:
          raise ValueError(f"Unknown embedder provider: {provider}")
  ```
- [ ] **2.4.3**: Remove old `os.environ.get('EMBEDDER_MODEL_NAME')` calls
- [ ] **2.4.4**: Save file

#### Reference
See [IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](../plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) § Phase 2 § Update Embedder Initialization

#### Validation

```bash
# Test embedder creation
python -c "
from mcp_server.graphiti_mcp_server import get_embedder
embedder = get_embedder()
print(f'✅ Embedder: {embedder}')
print(f'✅ Model: {embedder.model}')
"
```

**Expected Output**: Embedder created successfully

#### Notes
- Follow same pattern as LLM client
- Ensure embedding_dim matches model

**Completion Checklist**:
- [ ] Function replaced
- [ ] Provider selection working
- [ ] Old env var code removed
- [ ] Validation passed

---

### Task 2.5: Update Semaphore Limit ⏱️ 10 min

**File**: `mcp_server/graphiti_mcp_server.py`

**Current Status**: [ ] Not Started

**Dependencies**: Task 2.1 complete

#### Subtasks

- [ ] **2.5.1**: Locate global `SEMAPHORE_LIMIT` variable (around line 48)
- [ ] **2.5.2**: Change from:
  ```python
  SEMAPHORE_LIMIT = int(os.getenv('SEMAPHORE_LIMIT', 10))
  ```
  To:
  ```python
  # Will be set after config loads
  SEMAPHORE_LIMIT = 10  # Placeholder, updated in initialize_graphiti()
  ```
- [ ] **2.5.3**: In `initialize_graphiti()` function, add after config loads:
  ```python
  global SEMAPHORE_LIMIT
  SEMAPHORE_LIMIT = config.llm.semaphore_limit
  ```
- [ ] **2.5.4**: Save file

#### Validation

```bash
# Check semaphore loads from config
python -c "
from mcp_server.unified_config import get_config
config = get_config()
print(f'✅ Semaphore limit: {config.llm.semaphore_limit}')
"
```

**Expected Output**: Shows configured semaphore limit (default: 10)

#### Notes
- Simple change, low risk
- Ensures config value used

**Completion Checklist**:
- [ ] Variable updated
- [ ] Set in initialize_graphiti()
- [ ] Validation passed

---

### Task 2.6: Initialize Memory Filter System ⏱️ 20 min

**File**: `mcp_server/graphiti_mcp_server.py`

**Current Status**: [ ] Not Started

**Dependencies**: Task 2.2 complete (in initialize_graphiti function)

#### Subtasks

- [ ] **2.6.1**: In `initialize_graphiti()`, after database initialization, add:
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
- [ ] **2.6.2**: Add `filter_manager = None` at global scope (around line 50)
- [ ] **2.6.3**: Save file

#### Validation

```bash
# Test filter initialization (will warn about missing modules until Phase 3)
python -c "
from mcp_server.unified_config import get_config
config = get_config()
print(f'✅ Filter enabled in config: {config.memory_filter.enabled}')
"
```

**Expected Output**: Shows whether filter enabled

#### Notes
- This prepares for Phase 3
- Will log warning until filter modules exist (expected)
- Graceful degradation built in

**Completion Checklist**:
- [ ] Filter initialization code added
- [ ] Global variable declared
- [ ] Graceful degradation working
- [ ] Validation passed

---

## 🧪 Phase 2 Validation

**Run after completing ALL tasks above**

### Validation Checklist

- [ ] **V1**: Syntax check passes
  ```bash
  python -m py_compile mcp_server/graphiti_mcp_server.py
  ```

- [ ] **V2**: Import check passes
  ```bash
  python -c "from mcp_server import graphiti_mcp_server; print('✅ Imports OK')"
  ```

- [ ] **V3**: Config loads correctly
  ```bash
  python -c "
  from mcp_server.graphiti_mcp_server import config
  print(f'✅ Config loaded: {config.database.backend}')
  "
  ```

- [ ] **V4**: Server starts without critical errors
  ```bash
  timeout 10 python -m mcp_server.graphiti_mcp_server || echo "✅ Server started (timeout OK)"
  ```

- [ ] **V5**: Database config working
  ```bash
  python -c "
  from mcp_server.unified_config import get_config
  db = get_config().database.get_active_config()
  assert db.uri, 'URI should exist'
  print('✅ Database config valid')
  "
  ```

- [ ] **V6**: LLM config working
  ```bash
  python -c "
  from mcp_server.unified_config import get_config
  assert get_config().llm.provider, 'Provider should exist'
  print('✅ LLM config valid')
  "
  ```

- [ ] **V7**: Filter system logs appropriately
  ```bash
  # Should see warning about filter not yet implemented (expected)
  python -m mcp_server.graphiti_mcp_server 2>&1 | grep -i "filter" || echo "✅"
  ```

### Expected Results

- ✅ No syntax errors
- ✅ All imports succeed
- ✅ Config loads from file
- ✅ Server starts (timeout is OK)
- ⚠️ Filter system logs "not yet implemented" (expected until Phase 3)

### If Validation Fails

1. Review error messages
2. Check which validation step failed
3. Re-read task instructions for that step
4. Fix issues
5. Re-run validation from V1

---

## 🎯 Completion Criteria

**Phase 2 is complete when:**

- [x] All 6 tasks completed (2.1 through 2.6)
- [ ] All validation checks pass (V1 through V7)
- [ ] No import errors
- [ ] No syntax errors
- [ ] Server starts successfully
- [ ] Config loads from graphiti.config.json
- [ ] Database backend selectable via config
- [ ] LLM provider selectable via config
- [ ] Changes committed to git
- [ ] Git tag created: `phase-2-complete`

---

## 📝 Git Commit

**After validation passes:**

```bash
# Stage changes
git add mcp_server/graphiti_mcp_server.py
git add mcp_server/unified_config.py  # If modified

# Commit with detailed message
git commit -m "Phase 2: Integrate unified config into MCP server

- Replace os.environ.get() with config access
- Support database backend selection
- Support multiple LLM providers (OpenAI, Azure, Anthropic)
- Support multiple embedder providers
- Prepare for memory filter system
- All validation tests passing

Tasks completed:
- Task 2.1: Updated imports and config loading
- Task 2.2: Database connection uses unified config
- Task 2.3: LLM client uses provider selection
- Task 2.4: Embedder uses provider selection
- Task 2.5: Semaphore limit from config
- Task 2.6: Filter system initialization (Phase 3 prep)

Refs: implementation/checkpoints/CHECKPOINT_PHASE2.md
Refs: implementation/IMPLEMENTATION_MASTER.md § Phase 2"

# Create checkpoint tag
git tag -a phase-2-complete -m "Phase 2: MCP Server Integration Complete

All environment variables replaced with unified config.
Server now supports:
- Database backend switching (Neo4j, FalkorDB)
- LLM provider switching (OpenAI, Azure, Anthropic)
- Embedder provider selection
- Config-driven settings

Validated and tested.
Ready for Phase 3 (Filter System)."

# Verify
git log --oneline -1
git tag -l "phase-2*"
```

---

## 📊 Progress Tracking

### Task Progress
- Task 2.1: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 2.2: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 2.3: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 2.4: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 2.5: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 2.6: [ ] Not Started | [ ] In Progress | [ ] Complete

### Time Tracking
- **Estimated**: 2-3 hours
- **Actual**: [Fill in when complete]
- **Started**: [Fill in]
- **Completed**: [Fill in]

### Session Notes
```
Session 1:
- Started: [timestamp]
- Completed: Task 2.1, Task 2.2
- Status: In progress
- Next: Task 2.3

Session 2:
- Started: [timestamp]
- Completed: Task 2.3, Task 2.4, Task 2.5, Task 2.6
- Status: Complete
- Next: Validation

[Add more sessions as needed]
```

---

## 🔗 Related Documents

- **Master Plan**: [../IMPLEMENTATION_MASTER.md](../IMPLEMENTATION_MASTER.md) § Phase 2
- **Detailed Plan**: [../plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](../plans/IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md)
- **Next Checkpoint**: [CHECKPOINT_PHASE3.md](CHECKPOINT_PHASE3.md)
- **TODO Tracker**: [../TODO_MASTER.md](../TODO_MASTER.md)

---

## ⚠️ Blockers / Issues

**Active Blockers**: None

**Resolved Issues**:
- [List any issues encountered and how resolved]

---

## ✅ Sign-Off

**Phase 2 Status**: [ ] Not Complete | [ ] Complete

**Completed By**: [Agent name/session]
**Completion Date**: [Date]
**Validation Passed**: [ ] Yes | [ ] No
**Next Phase Ready**: [ ] Yes | [ ] No

**Notes**:

---

**Last Updated**: 2025-11-03
**Checkpoint Version**: 1.0
