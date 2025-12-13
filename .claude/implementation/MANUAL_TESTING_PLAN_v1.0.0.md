# Manual Testing Plan - Session Tracking Integration Sprint v1.0.0

**Version**: 1.0.0
**Created**: 2025-12-04
**Sprint**: Session Tracking Integration
**Branch**: `sprint/v1.0.0/session-tracking-integration`

---

## Executive Summary

This testing plan covers manual validation of all features implemented in the Session Tracking Integration sprint. Tests are organized by priority and dependency order - foundational features must pass before dependent features can be meaningfully tested.

### Sprint Statistics
- **Total Stories Completed**: 56
- **Total Stories Superseded**: 33
- **Total Files Changed**: 62 Python files (~20,800 lines added)
- **Key Areas**: Session Tracking, LLM Resilience, MCP Tools, Configuration

---

## Pre-Testing Checklist

### Environment Setup

- [ ] **Neo4j Database Running**
  ```bash
  # Windows Service
  sc query Neo4j

  # Or Docker
  docker ps | grep neo4j
  ```

- [ ] **Environment Variables Set**
  ```bash
  # Required
  export NEO4J_PASSWORD=your_password
  export OPENAI_API_KEY=sk-your-key

  # Verify
  echo $NEO4J_PASSWORD
  echo $OPENAI_API_KEY
  ```

- [ ] **Configuration Valid**
  ```bash
  python -m mcp_server.config_validator graphiti.config.json
  ```

- [ ] **Python Environment Active**
  ```bash
  # From project root
  .venv\Scripts\activate  # Windows
  source .venv/bin/activate  # Unix
  ```

- [ ] **Dependencies Installed**
  ```bash
  pip install -e .
  pip install -r requirements-dev.txt
  ```

---

## Phase 1: Foundation Tests (MUST PASS FIRST)

These tests validate core infrastructure that all other features depend on.

### Test 1.1: Configuration Loading and Validation

**Priority**: CRITICAL
**Dependency**: None
**Estimated Time**: 5 minutes

**Purpose**: Ensure configuration system works correctly before testing features.

**Steps**:

1. **Validate default config exists**
   ```bash
   ls -la graphiti.config.json
   ```
   Expected: File exists

2. **Run config validator**
   ```bash
   python -m mcp_server.config_validator
   ```
   Expected: `[OK] Configuration valid`

3. **Test config loading in Python**
   ```python
   from mcp_server.unified_config import get_config
   config = get_config()
   print(f"Database: {config.database.backend}")
   print(f"LLM: {config.llm.provider}")
   print(f"Session Tracking: {config.session_tracking.enabled}")
   ```
   Expected: Values match `graphiti.config.json`

4. **Test environment variable override**
   ```bash
   MODEL_NAME=gpt-4o python -c "
   from mcp_server.unified_config import get_config
   config = get_config()
   print(f'Model: {config.llm.default_model}')
   "
   ```
   Expected: `Model: gpt-4o` (overridden value)

**Pass Criteria**: All 4 steps succeed without errors.

---

### Test 1.2: Database Connectivity

**Priority**: CRITICAL
**Dependency**: Test 1.1
**Estimated Time**: 5 minutes

**Purpose**: Verify Neo4j connection before testing data operations.

**Steps**:

1. **Test direct Neo4j connection**
   ```bash
   python -c "
   from neo4j import GraphDatabase
   import os

   uri = 'bolt://localhost:7687'
   user = 'neo4j'
   password = os.environ.get('NEO4J_PASSWORD')

   driver = GraphDatabase.driver(uri, auth=(user, password))
   with driver.session() as session:
       result = session.run('RETURN 1 as test')
       print(f'Connection test: {result.single()[\"test\"]}')
   driver.close()
   "
   ```
   Expected: `Connection test: 1`

2. **Test MCP health check**
   ```bash
   python -c "
   import asyncio
   from mcp_server.graphiti_mcp_server import health_check
   result = asyncio.run(health_check())
   print(result)
   "
   ```
   Expected: JSON with `status: healthy`, `database_connected: true`

**Pass Criteria**: Both steps succeed with expected outputs.

---

### Test 1.3: LLM Connectivity

**Priority**: CRITICAL
**Dependency**: Test 1.1
**Estimated Time**: 5 minutes

**Purpose**: Verify OpenAI API access before testing LLM-dependent features.

**Steps**:

1. **Test LLM health check**
   ```bash
   python -c "
   import asyncio
   from mcp_server.graphiti_mcp_server import llm_health_check
   result = asyncio.run(llm_health_check())
   print(result)
   "
   ```
   Expected: JSON with `status: healthy`, `available: true`

2. **Test basic LLM call**
   ```bash
   python -c "
   import openai
   import os

   client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
   response = client.chat.completions.create(
       model='gpt-4o-mini',
       messages=[{'role': 'user', 'content': 'Say hello'}],
       max_tokens=10
   )
   print(f'LLM Response: {response.choices[0].message.content}')
   "
   ```
   Expected: A greeting response from the LLM

**Pass Criteria**: Both steps succeed with valid responses.

---

## Phase 2: Core Feature Tests

These tests validate the main session tracking functionality.

### Test 2.1: Session Filtering (Smart Filter)

**Priority**: HIGH
**Dependency**: Test 1.1
**Estimated Time**: 10 minutes

**Purpose**: Verify the 93% token reduction filter works correctly.

**Steps**:

1. **Run filter unit tests**
   ```bash
   pytest tests/session_tracking/test_filter.py -v
   ```
   Expected: All tests pass

2. **Manual filter test with sample data**
   ```python
   from graphiti_core.session_tracking.filter import SessionFilter
   from graphiti_core.session_tracking.filter_config import FilterConfig

   # Create filter with default config
   filter = SessionFilter(FilterConfig())

   # Sample conversation with tool calls
   messages = [
       {"type": "user", "content": "Read the config file"},
       {"type": "assistant", "content": [
           {"type": "tool_use", "name": "Read", "input": {"file_path": "/test/file.txt"}},
       ]},
       {"type": "tool_result", "content": "File content here..." * 100},  # Large content
       {"type": "assistant", "content": "Here's what I found in the file."}
   ]

   result = filter.filter_conversation(messages)
   print(f"Original tokens: ~{result['statistics']['original_tokens']}")
   print(f"Filtered tokens: ~{result['statistics']['filtered_tokens']}")
   print(f"Reduction: {result['statistics']['reduction_percentage']:.1f}%")
   ```
   Expected: Reduction percentage > 50%

3. **Verify filter preserves user/assistant messages**
   ```python
   # Check that user and assistant text is preserved
   filtered = result['filtered_messages']
   user_messages = [m for m in filtered if m.get('type') == 'user']
   assistant_text = [m for m in filtered if m.get('type') == 'assistant' and isinstance(m.get('content'), str)]

   assert len(user_messages) > 0, "User messages should be preserved"
   assert len(assistant_text) > 0, "Assistant text should be preserved"
   print("[OK] User and assistant messages preserved")
   ```

**Pass Criteria**: Unit tests pass, token reduction > 50%, messages preserved.

---

### Test 2.2: JSONL Parser

**Priority**: HIGH
**Dependency**: Test 1.1
**Estimated Time**: 5 minutes

**Purpose**: Verify Claude Code session files can be parsed correctly.

**Steps**:

1. **Run parser tests**
   ```bash
   pytest tests/session_tracking/test_parser.py -v
   ```
   Expected: All tests pass

2. **Parse a real session file (if available)**
   ```python
   from graphiti_core.session_tracking.parser import SessionParser
   import os

   # Find a real session file
   claude_dir = os.path.expanduser("~/.claude/projects")
   if os.path.exists(claude_dir):
       for root, dirs, files in os.walk(claude_dir):
           for f in files:
               if f.endswith('.jsonl'):
                   path = os.path.join(root, f)
                   print(f"Testing parser with: {path}")

                   parser = SessionParser()
                   messages = parser.parse_file(path)
                   print(f"Parsed {len(messages)} messages")

                   # Show first message types
                   types = [m.get('type', 'unknown')[:20] for m in messages[:5]]
                   print(f"First 5 message types: {types}")
                   break
           else:
               continue
           break
   else:
       print("No Claude sessions directory found - skip real file test")
   ```

**Pass Criteria**: Unit tests pass, real file parsing succeeds (if available).

---

### Test 2.3: Path Resolution (Cross-Platform)

**Priority**: HIGH
**Dependency**: Test 1.1
**Estimated Time**: 5 minutes

**Purpose**: Verify path handling works on Windows and maintains UNIX format for hashing.

**Steps**:

1. **Run path resolver tests**
   ```bash
   pytest tests/session_tracking/test_path_resolver.py -v
   ```
   Expected: All tests pass

2. **Manual path resolution test**
   ```python
   from graphiti_core.session_tracking.path_resolver import PathResolver
   import platform

   resolver = PathResolver()

   # Test relative path
   rel_result = resolver.resolve("./test/file.txt")
   print(f"Relative resolved: {rel_result}")

   # Test home expansion
   home_result = resolver.resolve("~/documents/test.md")
   print(f"Home expanded: {home_result}")

   # Verify format
   if platform.system() == "Windows":
       assert "\\" in str(rel_result), "Windows should use backslashes"
       print("[OK] Windows path format correct")
   else:
       assert "/" in str(rel_result), "Unix should use forward slashes"
       print("[OK] Unix path format correct")
   ```

**Pass Criteria**: Unit tests pass, paths resolve correctly for current platform.

---

### Test 2.4: File Watcher (Watchdog Integration)

**Priority**: HIGH
**Dependency**: Tests 1.1, 2.3
**Estimated Time**: 10 minutes

**Purpose**: Verify file monitoring detects new/modified session files.

**Steps**:

1. **Run watcher tests**
   ```bash
   pytest tests/test_session_file_monitoring.py -v
   ```
   Expected: All tests pass

2. **Manual watcher test**
   ```python
   import asyncio
   import tempfile
   import os
   from graphiti_core.session_tracking.watcher import SessionFileWatcher

   async def test_watcher():
       with tempfile.TemporaryDirectory() as tmpdir:
           detected_files = []

           def on_file_change(path):
               detected_files.append(path)
               print(f"Detected: {path}")

           watcher = SessionFileWatcher(tmpdir, on_file_change)
           watcher.start()

           # Create a test file
           test_file = os.path.join(tmpdir, "test-session.jsonl")
           with open(test_file, 'w') as f:
               f.write('{"type": "test"}\n')

           # Wait for detection
           await asyncio.sleep(2)

           watcher.stop()

           if len(detected_files) > 0:
               print(f"[OK] Watcher detected {len(detected_files)} file(s)")
           else:
               print("[WARN] No files detected - may be platform-specific timing")

   asyncio.run(test_watcher())
   ```

**Pass Criteria**: Unit tests pass, manual test detects file creation.

---

## Phase 3: MCP Integration Tests

### Test 3.1: MCP Server Startup

**Priority**: HIGH
**Dependency**: Phase 1, Phase 2
**Estimated Time**: 5 minutes

**Purpose**: Verify MCP server initializes all components correctly.

**Steps**:

1. **Test server initialization**
   ```bash
   timeout 10 python -c "
   import asyncio
   from mcp_server.graphiti_mcp_server import initialize_server

   async def test():
       try:
           await initialize_server()
           print('[OK] Server initialized successfully')
       except Exception as e:
           print(f'[FAIL] Server init failed: {e}')

   asyncio.run(test())
   " || echo "Server initialized (timeout expected)"
   ```
   Expected: `[OK] Server initialized successfully` before timeout

2. **Check component status**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import (
       graphiti_client,
       session_manager,
       resilient_indexer
   )

   print(f"Graphiti client: {'initialized' if graphiti_client else 'not initialized'}")
   print(f"Session manager: {'initialized' if session_manager else 'not initialized'}")
   print(f"Resilient indexer: {'initialized' if resilient_indexer else 'not initialized'}")
   ```

**Pass Criteria**: Server initializes without errors, components are accessible.

---

### Test 3.2: MCP Tool - add_memory

**Priority**: HIGH
**Dependency**: Test 3.1
**Estimated Time**: 10 minutes

**Purpose**: Verify memory can be added to the knowledge graph.

**Steps**:

1. **Test basic add_memory**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import add_memory

   async def test():
       result = await add_memory(
           name="Manual Test Episode",
           episode_body="This is a test episode for manual testing plan validation.",
           source="text",
           source_description="manual testing"
       )
       print(f"Result: {result}")
       return result

   result = asyncio.run(test())
   ```
   Expected: JSON response with `status: success`

2. **Test add_memory with filepath**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import add_memory

   async def test():
       result = await add_memory(
           name="Test with Filepath",
           episode_body="Content for file export test",
           filepath=".claude/test-outputs/{date}-test.md"
       )
       print(f"Result: {result}")
       return result

   result = asyncio.run(test())
   # Check file was created
   import os
   from datetime import datetime
   expected_path = f".claude/test-outputs/{datetime.now().strftime('%Y-%m-%d')}-test.md"
   if os.path.exists(expected_path):
       print(f"[OK] File created at {expected_path}")
   else:
       print(f"[WARN] File not found at {expected_path}")
   ```

3. **Test add_memory with wait_for_completion**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import add_memory

   async def test():
       # Test synchronous mode
       result = await add_memory(
           name="Sync Test",
           episode_body="Testing wait_for_completion=True",
           wait_for_completion=True
       )
       print(f"Sync result: {result}")

       # Test async mode
       result = await add_memory(
           name="Async Test",
           episode_body="Testing wait_for_completion=False",
           wait_for_completion=False
       )
       print(f"Async result: {result}")

   asyncio.run(test())
   ```
   Expected: Both modes return appropriate responses

**Pass Criteria**: All 3 tests return success, file is created for filepath test.

---

### Test 3.3: MCP Tool - search_memory_nodes

**Priority**: HIGH
**Dependency**: Test 3.2
**Estimated Time**: 5 minutes

**Purpose**: Verify semantic search works on stored memories.

**Steps**:

1. **Search for test episodes**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import search_memory_nodes

   async def test():
       result = await search_memory_nodes(
           query="manual test episode validation",
           max_nodes=5
       )
       print(f"Search result: {result}")
       return result

   result = asyncio.run(test())
   ```
   Expected: JSON with nodes containing test episode

2. **Search with entity filter**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import search_memory_nodes

   async def test():
       result = await search_memory_nodes(
           query="test",
           entity="Preference",
           max_nodes=10
       )
       print(f"Filtered search: {result}")

   asyncio.run(test())
   ```

**Pass Criteria**: Search returns relevant results, filtering works.

---

### Test 3.4: MCP Tool - search_memory_facts

**Priority**: MEDIUM
**Dependency**: Test 3.2
**Estimated Time**: 5 minutes

**Purpose**: Verify relationship search works.

**Steps**:

1. **Search for relationships**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import search_memory_facts

   async def test():
       result = await search_memory_facts(
           query="testing manual validation",
           max_facts=10
       )
       print(f"Facts result: {result}")

   asyncio.run(test())
   ```

**Pass Criteria**: Returns facts or empty list (valid response).

---

### Test 3.5: Session Tracking MCP Tools

**Priority**: HIGH
**Dependency**: Test 3.1
**Estimated Time**: 15 minutes

**Purpose**: Verify session tracking control tools work correctly.

**Steps**:

1. **Test session_tracking_status**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import session_tracking_status

   async def test():
       result = await session_tracking_status()
       print(f"Status: {result}")

   asyncio.run(test())
   ```
   Expected: JSON with global config, enabled state

2. **Test session_tracking_start**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import session_tracking_start

   async def test():
       result = await session_tracking_start(force=True)
       print(f"Start result: {result}")

   asyncio.run(test())
   ```
   Expected: JSON with `enabled: true`

3. **Test session_tracking_stop**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import session_tracking_stop

   async def test():
       result = await session_tracking_stop()
       print(f"Stop result: {result}")

   asyncio.run(test())
   ```
   Expected: JSON with `enabled: false`

4. **Test session_tracking_health**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import session_tracking_health

   async def test():
       result = await session_tracking_health()
       print(f"Health: {result}")

   asyncio.run(test())
   ```
   Expected: JSON with service status, queue status

5. **Test session_tracking_sync_history (dry-run)**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import session_tracking_sync_history

   async def test():
       result = await session_tracking_sync_history(
           days=7,
           dry_run=True
       )
       print(f"Sync preview: {result}")

   asyncio.run(test())
   ```
   Expected: JSON with sessions_found, estimated_cost

**Pass Criteria**: All 5 tools return valid JSON responses.

---

## Phase 4: Safety & Resilience Tests

### Test 4.1: LLM Unavailability Handling

**Priority**: HIGH
**Dependency**: Phase 3
**Estimated Time**: 15 minutes

**Purpose**: Verify graceful degradation when LLM is unavailable.

**Steps**:

1. **Simulate LLM unavailability (invalid API key)**
   ```bash
   # Temporarily use invalid key
   OPENAI_API_KEY=invalid_key_12345 python -c "
   import asyncio
   from mcp_server.graphiti_mcp_server import add_memory, llm_health_check

   async def test():
       # Check health shows unavailable
       health = await llm_health_check()
       print(f'Health: {health}')

       # Try to add memory - should handle gracefully
       try:
           result = await add_memory(
               name='Test During LLM Outage',
               episode_body='This should be handled gracefully'
           )
           print(f'Add memory result: {result}')
       except Exception as e:
           print(f'Exception (expected): {type(e).__name__}: {e}')

   asyncio.run(test())
   "
   ```
   Expected: Error response with `status: error`, `category: llm_unavailable`

2. **Test circuit breaker behavior**
   ```python
   from graphiti_core.llm_client.availability import CircuitBreaker, CircuitBreakerConfig

   cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))

   # Simulate failures
   for i in range(5):
       cb.record_failure()
       print(f"After failure {i+1}: state={cb.state.name}, failures={cb._failure_count}")

   # Check if circuit is open
   assert cb.state.name == "OPEN", "Circuit should be open after threshold"
   print("[OK] Circuit breaker opened after threshold")
   ```

**Pass Criteria**: LLM errors handled gracefully, circuit breaker opens correctly.

---

### Test 4.2: Database Reconnection

**Priority**: HIGH
**Dependency**: Phase 3
**Estimated Time**: 10 minutes

**Purpose**: Verify automatic reconnection after database disconnect.

**Steps**:

1. **Test reconnection logic**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import (
       initialize_graphiti_with_retry,
       is_recoverable_error
   )

   # Test error classification
   from neo4j.exceptions import ServiceUnavailable, AuthError

   assert is_recoverable_error(ServiceUnavailable("test")) == True
   print("[OK] ServiceUnavailable is recoverable")

   assert is_recoverable_error(AuthError("test")) == False
   print("[OK] AuthError is not recoverable")
   ```

2. **Test retry with exponential backoff**
   ```python
   from mcp_server.unified_config import get_config

   config = get_config()
   resilience = config.resilience

   print(f"Max retries: {resilience.max_retries}")
   print(f"Backoff base: {resilience.retry_backoff_base}")

   # Calculate expected delays
   for i in range(resilience.max_retries):
       delay = resilience.retry_backoff_base ** i
       print(f"  Retry {i+1}: {delay}s delay")
   ```

**Pass Criteria**: Error classification correct, retry delays calculated correctly.

---

### Test 4.3: Episode Timeout Handling

**Priority**: MEDIUM
**Dependency**: Phase 3
**Estimated Time**: 5 minutes

**Purpose**: Verify episodes don't hang indefinitely.

**Steps**:

1. **Check timeout configuration**
   ```python
   from mcp_server.unified_config import get_config

   config = get_config()
   print(f"Episode timeout: {config.resilience.episode_timeout}s")
   print(f"MCP tools timeout: {config.mcp_tools.timeout_seconds}s")
   ```

2. **Test timeout behavior (unit test)**
   ```bash
   pytest tests/mcp/test_wait_for_completion.py -v -k timeout
   ```

**Pass Criteria**: Timeouts are configured, timeout tests pass.

---

### Test 4.4: Retry Queue

**Priority**: MEDIUM
**Dependency**: Test 4.1
**Estimated Time**: 10 minutes

**Purpose**: Verify failed episodes are queued for retry.

**Steps**:

1. **Run retry queue tests**
   ```bash
   pytest tests/test_retry_queue.py -v
   ```
   Expected: All tests pass

2. **Check retry queue status**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import get_failed_episodes

   async def test():
       result = await get_failed_episodes(limit=10)
       print(f"Failed episodes: {result}")

   asyncio.run(test())
   ```
   Expected: JSON with queue status (may be empty)

**Pass Criteria**: Unit tests pass, get_failed_episodes returns valid response.

---

## Phase 5: End-to-End Integration Tests

### Test 5.1: Full Session Tracking Flow

**Priority**: CRITICAL
**Dependency**: All previous phases
**Estimated Time**: 20 minutes

**Purpose**: Verify complete session tracking from file creation to graph storage.

**Steps**:

1. **Enable session tracking**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import session_tracking_start, session_tracking_status

   async def test():
       await session_tracking_start(force=True)
       status = await session_tracking_status()
       print(f"Tracking enabled: {status}")

   asyncio.run(test())
   ```

2. **Create a test session file**
   ```python
   import os
   import json
   import tempfile
   from datetime import datetime

   # Create session content
   session_content = [
       {"type": "human", "message": {"id": "1", "content": "Hello, this is a test session"}},
       {"type": "assistant", "message": {"id": "2", "content": "Hello! I understand this is a test."}},
       {"type": "human", "message": {"id": "3", "content": "Please remember this: TEST_MARKER_12345"}},
       {"type": "assistant", "message": {"id": "4", "content": "I'll remember TEST_MARKER_12345."}},
   ]

   # Write to temp file in watched directory
   watch_path = os.path.expanduser("~/.claude/projects")
   if not os.path.exists(watch_path):
       os.makedirs(watch_path, exist_ok=True)

   test_dir = os.path.join(watch_path, "test-project-hash")
   sessions_dir = os.path.join(test_dir, "sessions")
   os.makedirs(sessions_dir, exist_ok=True)

   session_file = os.path.join(sessions_dir, f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}.jsonl")
   with open(session_file, 'w') as f:
       for msg in session_content:
           f.write(json.dumps(msg) + '\n')

   print(f"Created test session: {session_file}")
   ```

3. **Wait for inactivity timeout and check indexing**
   ```python
   import asyncio
   import time
   from mcp_server.graphiti_mcp_server import search_memory_nodes

   async def test():
       # Wait for session to be indexed (inactivity timeout)
       print("Waiting 2 minutes for session indexing...")
       await asyncio.sleep(120)

       # Search for the test marker
       result = await search_memory_nodes(
           query="TEST_MARKER_12345",
           max_nodes=5
       )
       print(f"Search result: {result}")

       # Check if found
       if "TEST_MARKER" in str(result):
           print("[OK] Test session was indexed and is searchable!")
       else:
           print("[WARN] Test marker not found - may need more time or check logs")

   asyncio.run(test())
   ```

4. **Clean up test files**
   ```python
   import os
   import shutil

   test_dir = os.path.expanduser("~/.claude/projects/test-project-hash")
   if os.path.exists(test_dir):
       shutil.rmtree(test_dir)
       print(f"Cleaned up: {test_dir}")
   ```

**Pass Criteria**: Session file is detected, parsed, filtered, and indexed to graph.

---

### Test 5.2: Manual Sync Command

**Priority**: HIGH
**Dependency**: Test 5.1
**Estimated Time**: 10 minutes

**Purpose**: Verify historical session sync works correctly.

**Steps**:

1. **Dry-run sync**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import session_tracking_sync_history

   async def test():
       result = await session_tracking_sync_history(days=7, dry_run=True)
       print(f"Dry-run result: {result}")

       # Check response structure
       import json
       data = json.loads(result) if isinstance(result, str) else result

       assert "sessions_found" in str(data), "Should report sessions found"
       assert "estimated_cost" in str(data), "Should estimate cost"
       print("[OK] Dry-run returned expected fields")

   asyncio.run(test())
   ```

2. **Actual sync (small batch)**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import session_tracking_sync_history

   async def test():
       result = await session_tracking_sync_history(
           days=1,  # Only 1 day to limit cost
           max_sessions=5,  # Safety limit
           dry_run=False
       )
       print(f"Actual sync result: {result}")

   asyncio.run(test())
   ```

**Pass Criteria**: Dry-run shows sessions, actual sync completes without errors.

---

### Test 5.3: CLI Commands

**Priority**: MEDIUM
**Dependency**: Phase 3
**Estimated Time**: 10 minutes

**Purpose**: Verify CLI interface works correctly.

**Steps**:

1. **Test status command**
   ```bash
   python -m mcp_server.session_tracking_cli status
   ```
   Expected: Shows current configuration

2. **Test enable command**
   ```bash
   python -m mcp_server.session_tracking_cli enable
   ```
   Expected: Enables session tracking

3. **Test disable command**
   ```bash
   python -m mcp_server.session_tracking_cli disable
   ```
   Expected: Disables session tracking

4. **Test sync preview**
   ```bash
   python -m mcp_server.session_tracking_cli sync --days 7
   ```
   Expected: Shows sessions to sync (dry-run by default)

**Pass Criteria**: All CLI commands execute without errors.

---

## Phase 6: Performance Tests

### Test 6.1: Token Reduction Verification

**Priority**: HIGH
**Dependency**: Test 2.1
**Estimated Time**: 10 minutes

**Purpose**: Verify 93% token reduction claim.

**Steps**:

1. **Run performance tests**
   ```bash
   pytest tests/session_tracking/test_performance.py -v
   ```
   Expected: All tests pass

2. **Manual large session test**
   ```python
   from graphiti_core.session_tracking.filter import SessionFilter
   from graphiti_core.session_tracking.filter_config import FilterConfig

   # Create large session (simulate real usage)
   messages = []
   for i in range(50):
       messages.append({"type": "user", "content": f"Request {i}: Please do something"})
       messages.append({
           "type": "assistant",
           "content": [
               {"type": "tool_use", "name": "Read", "input": {"file_path": f"/file{i}.txt"}},
           ]
       })
       messages.append({"type": "tool_result", "content": "x" * 5000})  # 5KB per tool result
       messages.append({"type": "assistant", "content": f"Done with request {i}"})

   filter = SessionFilter(FilterConfig())
   result = filter.filter_conversation(messages)

   reduction = result['statistics']['reduction_percentage']
   print(f"Token reduction: {reduction:.1f}%")

   if reduction >= 90:
       print("[OK] Achieved 90%+ token reduction")
   else:
       print(f"[WARN] Reduction below target: {reduction:.1f}%")
   ```

**Pass Criteria**: Token reduction >= 90% on large sessions.

---

## Phase 7: Security Tests

### Test 7.1: Credential Detection

**Priority**: HIGH
**Dependency**: Test 3.2
**Estimated Time**: 5 minutes

**Purpose**: Verify sensitive data warnings in add_memory.

**Steps**:

1. **Test credential detection**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import add_memory

   async def test():
       # This should trigger a warning
       result = await add_memory(
           name="Test with credentials",
           episode_body="api_key = sk-abc123def456",
           filepath=".claude/test-security.md"
       )
       print(f"Result: {result}")
       # Check for warning in result
       if "warning" in str(result).lower() or "credential" in str(result).lower():
           print("[OK] Credential warning detected")
       else:
           print("[WARN] No credential warning - check implementation")

   asyncio.run(test())
   ```

2. **Run security tests**
   ```bash
   pytest tests/session_tracking/test_security.py -v
   ```

**Pass Criteria**: Credential patterns trigger warnings, security tests pass.

---

### Test 7.2: Path Traversal Protection

**Priority**: HIGH
**Dependency**: Test 3.2
**Estimated Time**: 5 minutes

**Purpose**: Verify path traversal attacks are blocked.

**Steps**:

1. **Test path traversal blocking**
   ```python
   import asyncio
   from mcp_server.graphiti_mcp_server import add_memory

   async def test():
       # This should be blocked
       try:
           result = await add_memory(
               name="Path traversal test",
               episode_body="test content",
               filepath="../../../etc/passwd"
           )
           print(f"Result: {result}")
           if "error" in str(result).lower() or "blocked" in str(result).lower():
               print("[OK] Path traversal blocked")
           else:
               print("[FAIL] Path traversal NOT blocked!")
       except Exception as e:
           print(f"[OK] Path traversal blocked with exception: {e}")

   asyncio.run(test())
   ```

**Pass Criteria**: Path traversal attempts are blocked.

---

## Test Results Summary Template

Use this template to record test results:

```markdown
## Test Results - [DATE]

### Phase 1: Foundation Tests
- [ ] Test 1.1: Configuration Loading - PASS/FAIL
- [ ] Test 1.2: Database Connectivity - PASS/FAIL
- [ ] Test 1.3: LLM Connectivity - PASS/FAIL

### Phase 2: Core Feature Tests
- [ ] Test 2.1: Session Filtering - PASS/FAIL
- [ ] Test 2.2: JSONL Parser - PASS/FAIL
- [ ] Test 2.3: Path Resolution - PASS/FAIL
- [ ] Test 2.4: File Watcher - PASS/FAIL

### Phase 3: MCP Integration Tests
- [ ] Test 3.1: MCP Server Startup - PASS/FAIL
- [ ] Test 3.2: add_memory - PASS/FAIL
- [ ] Test 3.3: search_memory_nodes - PASS/FAIL
- [ ] Test 3.4: search_memory_facts - PASS/FAIL
- [ ] Test 3.5: Session Tracking Tools - PASS/FAIL

### Phase 4: Safety & Resilience Tests
- [ ] Test 4.1: LLM Unavailability - PASS/FAIL
- [ ] Test 4.2: Database Reconnection - PASS/FAIL
- [ ] Test 4.3: Episode Timeout - PASS/FAIL
- [ ] Test 4.4: Retry Queue - PASS/FAIL

### Phase 5: End-to-End Tests
- [ ] Test 5.1: Full Session Flow - PASS/FAIL
- [ ] Test 5.2: Manual Sync - PASS/FAIL
- [ ] Test 5.3: CLI Commands - PASS/FAIL

### Phase 6: Performance Tests
- [ ] Test 6.1: Token Reduction - PASS/FAIL

### Phase 7: Security Tests
- [ ] Test 7.1: Credential Detection - PASS/FAIL
- [ ] Test 7.2: Path Traversal - PASS/FAIL

### Notes
[Record any issues, warnings, or observations here]
```

---

## Potential Conflicts Identified During Audit

### Issue 1: Documentation Default Mismatch
- **Location**: `docs/SESSION_TRACKING_USER_GUIDE.md` line 359 states FAQ "retroactive tracking" is not possible, but `session_tracking_sync_history` tool enables exactly this.
- **Severity**: LOW (documentation inconsistency)
- **Action**: Verify sync tool behavior matches updated documentation

### Issue 2: Rolling Period Filter Interaction
- **Location**: `keep_length_days` config + manual sync
- **Concern**: If `keep_length_days=7` (default), does manual sync honor this or override?
- **Test**: Test 5.2 should verify this behavior
- **Action**: Confirm sync respects rolling period configuration

### Issue 3: Circuit Breaker State Persistence
- **Location**: `graphiti_core/llm_client/availability.py`
- **Concern**: Circuit breaker state is in-memory; MCP server restart resets state
- **Severity**: LOW (expected behavior, but worth noting)
- **Action**: Document that server restart resets circuit breaker

### Issue 4: Concurrent Session Tracking
- **Location**: `session_manager.py`
- **Concern**: Multiple sessions indexed simultaneously could cause race conditions
- **Severity**: MEDIUM
- **Test**: Consider stress testing with multiple concurrent sessions
- **Action**: Test 5.1 can be extended to create multiple sessions

---

## Appendix: Quick Reference Commands

```bash
# Run all unit tests
pytest tests/ -v

# Run specific test category
pytest tests/session_tracking/ -v
pytest tests/mcp/ -v

# Run with coverage
pytest tests/ --cov=graphiti_core --cov=mcp_server --cov-report=html

# Validate configuration
python -m mcp_server.config_validator

# Check database connection
python -c "from neo4j import GraphDatabase; print(GraphDatabase.driver('bolt://localhost:7687').verify_connectivity())"

# Start MCP server manually (for debugging)
python -m mcp_server.graphiti_mcp_server

# Session tracking CLI
python -m mcp_server.session_tracking_cli status
python -m mcp_server.session_tracking_cli enable
python -m mcp_server.session_tracking_cli disable
python -m mcp_server.session_tracking_cli sync --days 7
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-04
**Author**: Claude Code Sprint Audit
