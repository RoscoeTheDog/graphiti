# Phase 3 Checkpoint: Filter System Implementation

**Status**: 📅 Pending
**Progress**: 0/4 tasks complete (0%)
**Estimated Time**: 3-4 hours
**Started**: [Not started]
**Completed**: [Not completed]

---

## 🎯 Phase Objective

Implement LLM-based memory filter system with hierarchical provider fallback and session management.

---

## ✅ Prerequisites

- [ ] Phase 2 complete and validated
- [ ] `phase-2-complete` git tag exists
- [ ] MCP server starts with unified config
- [ ] Reviewed [IMPLEMENTATION_PLAN_LLM_FILTER.md](../plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § Component Design
- [ ] API keys available:
  - [ ] OPENAI_API_KEY in .env OR
  - [ ] ANTHROPIC_API_KEY in .env
- [ ] Python environment ready
- [ ] Can import: `from mcp_server.unified_config import get_config`

**Prerequisites Status**: ⚠️ Phase 2 must complete first

---

## 📋 Task Breakdown

### Task 3.1: Create LLM Provider Abstraction ⏱️ 1 hour

**File**: `mcp_server/llm_provider.py` (NEW FILE)

**Current Status**: [ ] Not Started

#### Subtasks

- [ ] **3.1.1**: Create new file `mcp_server/llm_provider.py`
- [ ] **3.1.2**: Add imports:
  ```python
  from abc import ABC, abstractmethod
  from typing import Dict, Any
  import os
  import logging

  logger = logging.getLogger(__name__)
  ```
- [ ] **3.1.3**: Copy `LLMProvider` abstract base class from reference plan (lines 250-280)
- [ ] **3.1.4**: Implement `OpenAIProvider` class with:
  - `__init__()` - Initialize with config
  - `is_available()` - Check API key exists
  - `filter()` - Call OpenAI API for filtering decision
- [ ] **3.1.5**: Implement `AnthropicProvider` class with:
  - Similar structure to OpenAI
  - Anthropic-specific API calls
- [ ] **3.1.6**: Implement `create_provider()` factory function
- [ ] **3.1.7**: Save file

#### Reference Code Location
[IMPLEMENTATION_PLAN_LLM_FILTER.md](../plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § LLM Provider Abstraction (lines 250-347)

#### Validation

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

**Expected Output**:
```
✅ openai_primary: available=True
✅ anthropic_fallback: available=True
```

#### Notes
- Abstract base class defines interface
- OpenAI implementation should handle rate limits
- Anthropic as fallback provider
- Graceful error handling required

**Completion Checklist**:
- [ ] File created: `mcp_server/llm_provider.py`
- [ ] `LLMProvider` ABC defined
- [ ] `OpenAIProvider` implemented
- [ ] `AnthropicProvider` implemented
- [ ] `create_provider()` factory working
- [ ] Validation passed
- [ ] Both providers detect API keys correctly

---

### Task 3.2: Create Session Manager ⏱️ 45 min

**File**: `mcp_server/session_manager.py` (NEW FILE)

**Current Status**: [ ] Not Started

**Dependencies**: Task 3.1 complete

#### Subtasks

- [ ] **3.2.1**: Create new file `mcp_server/session_manager.py`
- [ ] **3.2.2**: Add imports:
  ```python
  from typing import Dict, Optional
  from dataclasses import dataclass, field
  from datetime import datetime, timedelta
  import logging
  from mcp_server.llm_provider import create_provider, LLMProvider
  from mcp_server.unified_config import LLMFilterConfig

  logger = logging.getLogger(__name__)
  ```
- [ ] **3.2.3**: Implement `Session` dataclass with:
  - `session_id: str`
  - `provider: LLMProvider`
  - `created_at: datetime`
  - `last_used: datetime`
  - `query_count: int`
  - `context: list` (conversation history)
- [ ] **3.2.4**: Implement `SessionManager` class with:
  - `__init__(config: LLMFilterConfig)`
  - `get_or_create_session(session_id=None)`
  - `_create_provider()` - Hierarchical fallback logic
  - `_cleanup_sessions()` - Remove stale sessions
  - `_should_rotate_provider()` - Query limit checking
- [ ] **3.2.5**: Save file

#### Reference Code Location
[IMPLEMENTATION_PLAN_LLM_FILTER.md](../plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § Session Manager (lines 353-440)

#### Validation

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
print(f'✅ Query count: {session.query_count}')
"
```

**Expected Output**:
```
✅ Session created: [uuid]
✅ Provider: openai_primary
✅ Query count: 0
```

#### Notes
- Sessions auto-expire after inactivity
- Provider rotation based on query limits
- Hierarchical fallback: OpenAI → Anthropic
- Thread-safe session management

**Completion Checklist**:
- [ ] File created: `mcp_server/session_manager.py`
- [ ] `Session` dataclass defined
- [ ] `SessionManager` implemented
- [ ] Hierarchical fallback working
- [ ] Session cleanup logic working
- [ ] Validation passed

---

### Task 3.3: Create Filter Manager ⏱️ 1 hour

**File**: `mcp_server/filter_manager.py` (NEW FILE)

**Current Status**: [ ] Not Started

**Dependencies**: Task 3.2 complete

#### Subtasks

- [ ] **3.3.1**: Create new file `mcp_server/filter_manager.py`
- [ ] **3.3.2**: Add imports:
  ```python
  import logging
  from typing import Dict, Optional
  from mcp_server.session_manager import SessionManager

  logger = logging.getLogger(__name__)
  ```
- [ ] **3.3.3**: Implement `FilterManager` class with:
  - `__init__(session_manager: SessionManager)`
  - `should_store(content: str, context: str, session_id: str = None) -> Dict`
  - `_build_filter_prompt(content: str, context: str) -> str`
  - `_parse_filter_response(response: str) -> Dict`
- [ ] **3.3.4**: Add compact filter prompt (token-efficient):
  ```python
  FILTER_PROMPT = '''
  Analyze if this should be stored in long-term memory.

  Content: {content}
  Context: {context}

  Return JSON:
  {{
    "should_store": true/false,
    "category": "user-pref|env-quirk|project-decision|skip",
    "confidence": 0.0-1.0,
    "reason": "brief explanation"
  }}

  Store: user preferences, environment quirks, project conventions
  Skip: bug fixes in version control, temp issues, ephemeral data
  '''
  ```
- [ ] **3.3.5**: Implement graceful degradation:
  - Try primary provider
  - Fall back to secondary on failure
  - Return safe default if all fail
- [ ] **3.3.6**: Save file

#### Reference Code Location
[IMPLEMENTATION_PLAN_LLM_FILTER.md](../plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § Filter Manager (lines 446-552)

#### Validation

```bash
# Test filter decisions
python -c "
import asyncio
from mcp_server.unified_config import get_config
from mcp_server.session_manager import SessionManager
from mcp_server.filter_manager import FilterManager

async def test():
    config = get_config()
    session_mgr = SessionManager(config.memory_filter.llm_filter)
    filter_mgr = FilterManager(session_mgr)

    # Test 1: Env quirk (SHOULD store)
    result1 = await filter_mgr.should_store(
        'Neo4j timeout fixed by NEO4J_TIMEOUT=60 in .env',
        'Edited .env (gitignored)'
    )
    print(f'Test 1 (env-quirk): {result1[\"should_store\"]} | {result1[\"category\"]}')
    assert result1['should_store'] == True, 'Env quirk should store'

    # Test 2: Bug fix (SHOULD skip)
    result2 = await filter_mgr.should_store(
        'Fixed infinite loop in parseData()',
        'Edited src/parser.py, committed to git'
    )
    print(f'Test 2 (bug-fix): {result2[\"should_store\"]} | {result2[\"category\"]}')
    assert result2['should_store'] == False, 'Bug fix should skip'

    # Test 3: User preference (SHOULD store)
    result3 = await filter_mgr.should_store(
        'User prefers dark mode in all apps',
        'Conversation about UI preferences'
    )
    print(f'Test 3 (user-pref): {result3[\"should_store\"]} | {result3[\"category\"]}')
    assert result3['should_store'] == True, 'User pref should store'

    print('✅ All filter tests passed')

asyncio.run(test())
"
```

**Expected Output**:
```
Test 1 (env-quirk): True | env-quirk
Test 2 (bug-fix): False | skip
Test 3 (user-pref): True | user-pref
✅ All filter tests passed
```

#### Notes
- Filter prompt is compact (minimize tokens)
- JSON response parsing must be robust
- Handle LLM API errors gracefully
- Log filter decisions for debugging

**Completion Checklist**:
- [ ] File created: `mcp_server/filter_manager.py`
- [ ] `FilterManager` class implemented
- [ ] Filter prompt optimized
- [ ] Response parsing robust
- [ ] Graceful degradation working
- [ ] All test cases pass
- [ ] Validation passed

---

### Task 3.4: Add should_store MCP Tool ⏱️ 30 min

**File**: `mcp_server/graphiti_mcp_server.py`

**Current Status**: [ ] Not Started

**Dependencies**: Task 3.3 complete

#### Subtasks

- [ ] **3.4.1**: Open `mcp_server/graphiti_mcp_server.py`
- [ ] **3.4.2**: Locate MCP tools section (around line 800, after existing tools)
- [ ] **3.4.3**: Add new tool registration:
  ```python
  @mcp.tool()
  async def should_store(
      content: str,
      context: str = "",
      session_id: str | None = None,
  ) -> Dict[str, Any]:
      """
      Determine if content should be stored in long-term memory.

      Args:
          content: The information to evaluate
          context: Additional context about the content
          session_id: Optional session ID for context tracking

      Returns:
          Dict with:
          - should_store: bool
          - category: str (user-pref|env-quirk|project-decision|skip)
          - confidence: float (0.0-1.0)
          - reason: str
      """
      global filter_manager

      # If filter disabled or not available, default to storing
      if not filter_manager:
          logger.info("Filter system unavailable, defaulting to store")
          return {
              "should_store": True,
              "category": "default",
              "confidence": 0.5,
              "reason": "Filter system not enabled"
          }

      try:
          result = await filter_manager.should_store(content, context, session_id)
          logger.info(
              f"Filter decision: {result['should_store']} | "
              f"{result['category']} | "
              f"confidence={result['confidence']:.2f}"
          )
          return result
      except Exception as e:
          logger.error(f"Filter error: {e}, defaulting to store")
          return {
              "should_store": True,
              "category": "error",
              "confidence": 0.0,
              "reason": f"Filter error: {str(e)}"
          }
  ```
- [ ] **3.4.4**: Save file

#### Reference Code Location
[IMPLEMENTATION_PLAN_LLM_FILTER.md](../plans/IMPLEMENTATION_PLAN_LLM_FILTER.md) § New MCP Tool (lines 589-650)

#### Validation

```bash
# Test MCP tool registration
python -c "
from mcp_server.graphiti_mcp_server import mcp

tools = [tool.name for tool in mcp.list_tools()]
print(f'Available tools: {tools}')
assert 'should_store' in tools, 'should_store tool not found'
print('✅ should_store tool registered')
"
```

**Expected Output**:
```
Available tools: ['add_memory', 'search_memory_nodes', ..., 'should_store']
✅ should_store tool registered
```

#### Notes
- Tool must handle filter_manager=None gracefully
- Default to storing if filter unavailable (safe fallback)
- Log all filter decisions for debugging
- Return structured response

**Completion Checklist**:
- [ ] Tool added to `graphiti_mcp_server.py`
- [ ] Proper error handling
- [ ] Graceful degradation when filter disabled
- [ ] Logging implemented
- [ ] Tool registered successfully
- [ ] Validation passed

---

## 🧪 Phase 3 Validation

**Run after completing ALL tasks above**

### Validation Checklist

- [ ] **V1**: All modules import successfully
  ```bash
  python -c "from mcp_server.llm_provider import LLMProvider; print('✅')"
  python -c "from mcp_server.session_manager import SessionManager; print('✅')"
  python -c "from mcp_server.filter_manager import FilterManager; print('✅')"
  ```

- [ ] **V2**: Provider creation works
  ```bash
  python -c "
  from mcp_server.unified_config import get_config
  from mcp_server.llm_provider import create_provider
  config = get_config()
  provider = create_provider(config.memory_filter.llm_filter.providers[0])
  print(f'✅ Provider created: {provider.config.name}')
  "
  ```

- [ ] **V3**: Session management works
  ```bash
  python -c "
  from mcp_server.unified_config import get_config
  from mcp_server.session_manager import SessionManager
  config = get_config()
  mgr = SessionManager(config.memory_filter.llm_filter)
  session = mgr.get_or_create_session()
  print(f'✅ Session: {session.session_id}')
  "
  ```

- [ ] **V4**: End-to-end filter test passes
  ```bash
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

      mgr = SessionManager(config.memory_filter.llm_filter)
      filter_mgr = FilterManager(mgr)

      result = await filter_mgr.should_store(
          'User prefers dark mode',
          'UI preferences conversation'
      )

      assert result['should_store'] == True, 'Should store user pref'
      assert result['category'] == 'user-pref'
      print(f'✅ Filter working: {result}')

  asyncio.run(test())
  "
  ```

- [ ] **V5**: MCP tool callable
  ```bash
  python -c "
  from mcp_server.graphiti_mcp_server import mcp
  tools = [t.name for t in mcp.list_tools()]
  assert 'should_store' in tools
  print('✅ MCP tool registered')
  "
  ```

- [ ] **V6**: Hierarchical fallback works (if multiple providers configured)
  ```bash
  # Manually test by temporarily removing primary API key
  # Ensure falls back to secondary provider
  ```

- [ ] **V7**: Integration test suite passes
  ```bash
  pytest tests/test_filter_integration.py -v
  ```

### Expected Results

- ✅ All modules import without errors
- ✅ Providers created and available
- ✅ Sessions manage correctly
- ✅ Filter makes intelligent decisions
- ✅ MCP tool registered and callable
- ✅ Fallback logic works
- ✅ Integration tests pass

### If Validation Fails

1. Check which validation step failed
2. Review error messages carefully
3. Verify API keys are set correctly
4. Check config.memory_filter.enabled = true
5. Review task implementation for that component
6. Fix and re-run validation

---

## 🎯 Completion Criteria

**Phase 3 is complete when:**

- [ ] All 4 tasks completed (3.1 through 3.4)
- [ ] All validation checks pass (V1 through V7)
- [ ] All new files created and working
- [ ] Filter makes correct decisions on test cases
- [ ] Hierarchical fallback functional
- [ ] MCP tool registered and callable
- [ ] No import or runtime errors
- [ ] Changes committed to git
- [ ] Git tag created: `phase-3-complete`

---

## 📝 Git Commit

**After validation passes:**

```bash
# Stage new files
git add mcp_server/llm_provider.py
git add mcp_server/session_manager.py
git add mcp_server/filter_manager.py
git add mcp_server/graphiti_mcp_server.py

# Commit with detailed message
git commit -m "Phase 3: Implement LLM-based memory filter system

- Add LLM provider abstraction (OpenAI, Anthropic)
- Add session management for context tracking
- Add filter manager with intelligent filtering
- Add should_store MCP tool for agent integration
- Implement hierarchical provider fallback
- Graceful degradation on errors

Components:
- mcp_server/llm_provider.py: Abstract provider interface
- mcp_server/session_manager.py: Session lifecycle management
- mcp_server/filter_manager.py: Core filtering logic
- mcp_server/graphiti_mcp_server.py: MCP tool integration

All validation tests passing.
Filter correctly identifies:
- User preferences (store)
- Environment quirks (store)
- Bug fixes in code (skip)
- Project decisions (store)

Refs: implementation/checkpoints/CHECKPOINT_PHASE3.md
Refs: implementation/IMPLEMENTATION_MASTER.md § Phase 3"

# Create checkpoint tag
git tag -a phase-3-complete -m "Phase 3: Filter System Implementation Complete

LLM-based memory filtering operational:
- Intelligent categorization (user-pref, env-quirk, etc)
- Hierarchical provider fallback (OpenAI → Anthropic)
- Session-scoped LLM instances
- Compact, token-efficient prompts
- Graceful degradation

MCP tool 'should_store' available for agent use.

Validated and tested.
Ready for Phase 4 (Documentation)."

# Verify
git log --oneline -1
git tag -l "phase-3*"
```

---

## 📊 Progress Tracking

### Task Progress
- Task 3.1: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 3.2: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 3.3: [ ] Not Started | [ ] In Progress | [ ] Complete
- Task 3.4: [ ] Not Started | [ ] In Progress | [ ] Complete

### Time Tracking
- **Estimated**: 3-4 hours
- **Actual**: [Fill in when complete]
- **Started**: [Fill in]
- **Completed**: [Fill in]

### Session Notes
```
Session 1:
- Started: [timestamp]
- Completed: Task 3.1
- Status: In progress
- Next: Task 3.2

[Add more sessions as needed]
```

---

## 🔗 Related Documents

- **Master Plan**: [../IMPLEMENTATION_MASTER.md](../IMPLEMENTATION_MASTER.md) § Phase 3
- **Detailed Plan**: [../plans/IMPLEMENTATION_PLAN_LLM_FILTER.md](../plans/IMPLEMENTATION_PLAN_LLM_FILTER.md)
- **Previous Checkpoint**: [CHECKPOINT_PHASE2.md](CHECKPOINT_PHASE2.md)
- **Next Checkpoint**: [CHECKPOINT_PHASE4.md](CHECKPOINT_PHASE4.md)
- **TODO Tracker**: [../TODO_MASTER.md](../TODO_MASTER.md)

---

## ⚠️ Blockers / Issues

**Active Blockers**: Phase 2 must complete first

**Resolved Issues**:
- [List any issues encountered and how resolved]

---

## ✅ Sign-Off

**Phase 3 Status**: [ ] Not Complete | [ ] Complete

**Completed By**: [Agent name/session]
**Completion Date**: [Date]
**Validation Passed**: [ ] Yes | [ ] No
**Next Phase Ready**: [ ] Yes | [ ] No

**Notes**:

---

**Last Updated**: 2025-11-03
**Checkpoint Version**: 1.0
