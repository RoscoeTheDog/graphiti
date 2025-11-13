# Implementation Sprint: Session Tracking Integration
**Created**: 2025-11-13 09:30
**Status**: active
**Version**: v1.0.0
**Base Branch**: main
**Sprint Goal**: Integrate automatic JSONL session tracking into Graphiti MCP server with CLI opt-in/out and runtime toggle capabilities

## Sprint Metadata

**Source**: Extract and refactor modules from claude-window-watchdog project
**Priority**: Session tracking first (foundation infrastructure supports independent implementation)
**Estimated Cost**: ~$0.03-$0.50 per session (highly acceptable)
**Timeline**: 3 weeks (15-18 days)

## Cross-Cutting Requirements

**ALL stories must satisfy the requirements in `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`**

Key requirements:
1. **Platform-Agnostic Path Handling**: Paths must use native OS format (Windows: `C:\...`, Unix: `/...`)
2. **Error Handling**: Comprehensive logging and graceful degradation
3. **Type Safety**: Type hints and Pydantic models for all code
4. **Testing**: >80% coverage with platform-specific tests
5. **Performance**: <5% overhead for session tracking
6. **Security**: No exposure of sensitive information
7. **Configuration**: Use unified `graphiti.config.json` system
8. **Documentation**: User and developer docs updated

See full requirements: `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`

## Stories

### Story 1: Foundation Infrastructure
**Status**: completed
**Claimed**: 2025-11-13 08:00
**Completed**: 2025-11-13 09:15
**Description**: Create core module structure, extract types, implement JSONL parser and path resolver
**Acceptance Criteria**:
- [x] `graphiti_core/session_tracking/` module structure created
- [x] `types.py` implemented with all dataclasses (SessionMessage, ConversationContext, SessionMetadata)
- [x] `parser.py` extracted and refactored from watchdog (SQLite dependencies removed)
- [x] `path_resolver.py` implemented with Claude Code path mapping
- [x] Unit tests pass for parser + path resolver (27 tests passing)
- [x] Can parse JSONL files and extract messages correctly

**Implementation Notes**:
- Created comprehensive type system with MessageRole, ToolCallStatus, TokenUsage, ToolCall, SessionMessage, ConversationContext, and SessionMetadata
- Parser successfully extracts tool calls, token usage, and message content
- Path resolver handles cross-platform path normalization (Windows/Unix/WSL)
- All 27 unit tests passing successfully
- Zero SQLite dependencies, using pure Python dataclasses
- Tool call extraction includes error detection and status tracking

### Story 1.1: Core Types Module
**Status**: unassigned
**Parent**: Story 1
**Description**: Create type definitions for session tracking (TokenUsage, ToolCall, SessionMessage, ConversationContext, SessionMetadata)
**Acceptance Criteria**:
- [ ] All dataclasses defined in `types.py`
- [ ] Proper type hints and documentation
- [ ] No external dependencies (pure Python types)

### Story 1.2: JSONL Parser
**Status**: unassigned
**Parent**: Story 1
**Description**: Extract and refactor parser from claude-window-watchdog, remove SQLite dependencies, add tool call extraction
**Acceptance Criteria**:
- [ ] `parser.py` created with JSONLParser class
- [ ] Incremental parsing with offset tracking works
- [ ] Tool call extraction implemented (MCP-specific)
- [ ] Unit tests cover all parsing scenarios

### Story 1.3: Path Resolution
**Status**: unassigned
**Parent**: Story 1
**Description**: Implement Claude Code JSONL path resolution with project root → hash mapping
**Acceptance Criteria**:
- [ ] `path_resolver.py` implemented with ClaudePathResolver class
- [ ] Cross-platform path handling (Windows/Unix/WSL)
- [ ] Can resolve `~/.claude/projects/{hash}/sessions/` correctly
- [ ] Unit tests for path resolution edge cases

### Story 2: Smart Filtering
**Status**: unassigned
**Description**: Implement 93% token reduction filtering per handoff design
**Acceptance Criteria**:
- [ ] `filter.py` implemented with SessionFilter class
- [ ] Filtering rules applied correctly (keep user/agent, omit tool outputs)
- [ ] Tool output summarization works (1-line summaries)
- [ ] MCP tool extraction implemented
- [ ] Token reduction achieves 90%+ (validated with test data)
- [ ] Unit tests pass for all filtering scenarios
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Platform-agnostic path handling (if applicable)
  - [ ] Type hints and comprehensive docstrings
  - [ ] Error handling with logging
  - [ ] >80% test coverage
  - [ ] Performance benchmarks (<5% overhead)

### Story 2.1: Filtering Logic
**Status**: unassigned
**Parent**: Story 2
**Description**: Implement core filtering rules (keep structure, omit outputs)
**Acceptance Criteria**:
- [ ] User messages preserved (full)
- [ ] Agent responses preserved (full)
- [ ] Tool use blocks preserved (structure only)
- [ ] Tool results omitted (replaced with summary)

### Story 2.2: Tool Output Summarization
**Status**: unassigned
**Parent**: Story 2
**Description**: Create concise 1-line summaries for tool results
**Acceptance Criteria**:
- [ ] Read/Write/Edit summaries implemented
- [ ] MCP tool result summaries implemented
- [ ] Summary format is consistent and informative

### Story 3: File Monitoring
**Status**: unassigned
**Description**: Implement watchdog-based automatic session detection and lifecycle management
**Acceptance Criteria**:
- [ ] `watcher.py` extracted and refactored (database storage removed)
- [ ] `session_manager.py` implemented with lifecycle detection
- [ ] Offset tracking works correctly (incremental reading)
- [ ] Session close detection works (inactivity timeout)
- [ ] Configuration schema added to unified_config.py
- [ ] Integration tests pass with mock JSONL files
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Platform-agnostic path handling for file watching
  - [ ] Type hints and comprehensive docstrings
  - [ ] Error handling with logging (file I/O)
  - [ ] >80% test coverage (including platform-specific tests)
  - [ ] Performance: <5% CPU overhead for file watching

### Story 3.1: File Watcher
**Status**: unassigned
**Parent**: Story 3
**Description**: Extract and refactor watchdog-based file monitoring from claude-window-watchdog
**Acceptance Criteria**:
- [ ] SessionFileWatcher class implemented
- [ ] Callback pattern used instead of database storage
- [ ] Offset tracking maintained for incremental reads
- [ ] New session file detection works

### Story 3.2: Session Manager
**Status**: unassigned
**Parent**: Story 3
**Description**: Orchestrate session lifecycle (track active sessions, detect close, trigger summarization)
**Acceptance Criteria**:
- [ ] SessionManager class implemented
- [ ] In-memory session registry tracks active sessions
- [ ] Inactivity timeout detection works
- [ ] Auto-compaction detection implemented (new JSONL = continuation)
- [ ] Triggers summarization on session close

### Story 3.3: Configuration Integration
**Status**: unassigned
**Parent**: Story 3
**Description**: Add session tracking configuration to unified_config.py
**Acceptance Criteria**:
- [ ] SessionTrackingConfig schema added
- [ ] Configuration validation works
- [ ] Default values set correctly
- [ ] Config can be loaded from graphiti.config.json

### Story 4: LLM Summarization
**Status**: unassigned
**Description**: Implement LLM-based session summarization and Graphiti storage
**Acceptance Criteria**:
- [ ] `summarizer.py` implemented using Graphiti LLM client
- [ ] Prompt template from handoff docs used
- [ ] Structured summary extraction works (objective, work_completed, decisions, etc.)
- [ ] `graphiti_storage.py` implemented for graph persistence
- [ ] Sessions stored as EpisodicNodes with proper metadata
- [ ] Relations created (preceded_by, continued_by, spawned_agent)
- [ ] Cost tracking logs actual LLM costs
- [ ] Integration test passes with real Graphiti instance
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Type hints and comprehensive docstrings
  - [ ] Error handling with logging (LLM API errors)
  - [ ] Security: No credentials in summaries
  - [ ] >80% test coverage
  - [ ] Performance: Async summarization (no blocking)

### Story 4.1: Session Summarizer
**Status**: unassigned
**Parent**: Story 4
**Description**: Use Graphiti LLM client to generate structured summaries
**Acceptance Criteria**:
- [ ] SessionSummarizer class implemented
- [ ] Uses gpt-4.1-mini for cost efficiency
- [ ] Prompt template matches handoff design
- [ ] Extracts all required fields (objective, work, decisions, etc.)
- [ ] Handles errors gracefully

### Story 4.2: Graphiti Storage Integration
**Status**: unassigned
**Parent**: Story 4
**Description**: Store session summaries as EpisodicNodes in Graphiti graph
**Acceptance Criteria**:
- [ ] SessionStorage class implemented
- [ ] Sessions stored as EpisodicNodes
- [ ] Metadata includes token_count, mcp_tools_used, files_modified
- [ ] Relations created correctly (preceded_by, continued_by)
- [ ] Integration test with real Graphiti instance passes

### Story 5: CLI Integration
**Status**: unassigned
**Description**: Add global opt-in/out CLI commands for session tracking
**Acceptance Criteria**:
- [ ] CLI commands implemented (enable, disable, status)
- [ ] Configuration persisted to graphiti.config.json
- [ ] Applied on MCP server startup
- [ ] Documentation updated (CONFIGURATION.md)
- [ ] Cost estimates documented
- [ ] Opt-out instructions clear
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Platform-agnostic config file paths
  - [ ] Type hints and comprehensive docstrings
  - [ ] Error handling with logging (config errors)
  - [ ] Configuration uses unified system
  - [ ] Documentation: User guide updated

### Story 5.1: CLI Commands
**Status**: unassigned
**Parent**: Story 5
**Description**: Implement session tracking CLI commands
**Acceptance Criteria**:
- [ ] `graphiti-mcp session-tracking enable` works
- [ ] `graphiti-mcp session-tracking disable` works
- [ ] `graphiti-mcp session-tracking status` works
- [ ] Commands integrated with existing MCP server CLI

### Story 5.2: Configuration Persistence
**Status**: unassigned
**Parent**: Story 5
**Description**: Store session tracking state in graphiti.config.json
**Acceptance Criteria**:
- [ ] Config updates persist to file
- [ ] Config loaded on server startup
- [ ] Validation works correctly

### Story 6: MCP Tool Integration
**Status**: unassigned
**Description**: Add runtime toggle via MCP tool calls for per-session control
**Acceptance Criteria**:
- [ ] `track_session()` MCP tool implemented
- [ ] `stop_tracking_session()` MCP tool implemented
- [ ] `get_session_tracking_status()` MCP tool implemented
- [ ] Session registry tracks per-session state
- [ ] Override global config with force parameter works
- [ ] Integration with session_manager.py complete
- [ ] Agent-friendly tool descriptions written
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Type hints and comprehensive docstrings
  - [ ] Error handling with logging (MCP tool errors)
  - [ ] >80% test coverage
  - [ ] Documentation: MCP_TOOLS.md updated
  - [ ] Security: No sensitive data exposed in tool responses

### Story 6.1: MCP Tool Implementation
**Status**: unassigned
**Parent**: Story 6
**Description**: Add MCP tools to graphiti_mcp_server.py
**Acceptance Criteria**:
- [ ] All three MCP tools registered
- [ ] Tool descriptions are clear and agent-friendly
- [ ] Tools integrated with SessionTrackingService

### Story 6.2: Runtime State Management
**Status**: unassigned
**Parent**: Story 6
**Description**: Implement per-session enable/disable state tracking
**Acceptance Criteria**:
- [ ] In-memory session registry works
- [ ] Per-session overrides global config correctly
- [ ] force=True parameter works as expected

### Story 7: Testing & Validation
**Status**: unassigned
**Description**: Comprehensive testing and cost validation with real session data
**Acceptance Criteria**:
- [ ] End-to-end integration tests pass
- [ ] Cost measurement validates projections ($0.03-$0.50/session)
- [ ] Performance testing shows acceptable overhead (<5%)
- [ ] Large sessions (100+ exchanges) handled correctly
- [ ] Multiple concurrent sessions work
- [ ] Documentation complete (user guide, dev guide, troubleshooting)
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Platform-specific tests (Windows + Unix)
  - [ ] >80% overall test coverage
  - [ ] Performance benchmarks documented
  - [ ] Security audit completed
  - [ ] All documentation updated

### Story 7.1: Integration Testing
**Status**: unassigned
**Parent**: Story 7
**Description**: End-to-end workflow testing with full session lifecycle
**Acceptance Criteria**:
- [ ] Full workflow test: detect → parse → filter → summarize → store
- [ ] Multiple sequential sessions tested
- [ ] Multiple parallel sessions tested
- [ ] Auto-compaction detection tested
- [ ] Agent spawning (parent-child linkage) tested

### Story 7.2: Cost Validation
**Status**: unassigned
**Parent**: Story 7
**Description**: Measure actual OpenAI API costs with real session data
**Acceptance Criteria**:
- [ ] Real session data processed
- [ ] Actual costs measured and logged
- [ ] Costs validate against projections ($0.03-$0.50/session)
- [ ] Token reduction confirmed (90%+)

### Story 7.3: Performance Testing
**Status**: unassigned
**Parent**: Story 7
**Description**: Validate performance and resource usage
**Acceptance Criteria**:
- [ ] Large sessions (100+ exchanges) tested
- [ ] Multiple concurrent sessions tested
- [ ] File watcher overhead measured (<5%)
- [ ] Memory usage acceptable
- [ ] No performance degradation for MCP server

### Story 7.4: Documentation
**Status**: unassigned
**Parent**: Story 7
**Description**: Create user and developer documentation
**Acceptance Criteria**:
- [ ] User guide: How to use session tracking
- [ ] Developer guide: Architecture and extension points
- [ ] Troubleshooting guide created
- [ ] README.md updated with session tracking features
- [ ] CONFIGURATION.md updated

### Story 8: Refinement & Launch
**Status**: unassigned
**Description**: Polish, code review, and release preparation
**Acceptance Criteria**:
- [ ] Code review completed and feedback addressed
- [ ] Logging and debugging aids added
- [ ] Error handling improved
- [ ] README.md updated with session tracking features
- [ ] Migration guide created for existing users
- [ ] Release notes written
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] All platform-agnostic path requirements met
  - [ ] All security requirements satisfied
  - [ ] All performance benchmarks met
  - [ ] All documentation complete and reviewed
  - [ ] Final compliance checklist passed

## Progress Log

### 2025-11-13 09:15 - Story 1 Completed
- ✅ **Story 1: Foundation Infrastructure** - Completed in 1.25 hours
- Created `graphiti_core/session_tracking/` module with comprehensive type system
- Implemented `types.py` with 7 dataclasses (MessageRole, ToolCallStatus, TokenUsage, ToolCall, SessionMessage, ConversationContext, SessionMetadata)
- Extracted and refactored `parser.py` from claude-window-watchdog project
  - Removed all SQLite dependencies
  - Added MCP-specific tool call extraction
  - Supports incremental parsing with offset tracking
- Implemented `path_resolver.py` with Claude Code project hash mapping
  - Cross-platform path normalization (Windows/Unix/WSL)
  - Project hash calculation and caching
  - Session file discovery and validation
- Created comprehensive test suite with 27 tests (all passing)
- Zero external dependencies beyond stdlib and Pydantic

### 2025-11-13 09:30 - Sprint Started
- Created sprint structure for Session Tracking Integration
- Archived 12 existing implementation files to `.claude/implementation/archive/2025-11-13-0930/`
- Detected git context: No dev branch, using main as base branch
- Defined 8 main stories with 18 sub-stories
- Total estimated timeline: 3 weeks (15-18 days)
- Sprint initialized and ready for execution

## Sprint Summary
*To be filled upon completion*
