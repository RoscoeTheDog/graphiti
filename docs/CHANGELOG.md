# Changelog

All notable changes to the Graphiti project architecture and features are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2025-12-20

Major architectural overhaul introducing daemon architecture, global session tracking, turn-based indexing, and per-project configuration overrides.

### Added

#### Session Tracking & Memory
- **Global session tracking** with namespace tagging for cross-project knowledge sharing
  - Single global knowledge graph instead of per-project isolation
  - Project namespace metadata embedded in all indexed episodes
  - Cross-project search enabled by default with optional `trusted_namespaces` filtering
  - See: [docs/SESSION_TRACKING_USER_GUIDE.md](SESSION_TRACKING_USER_GUIDE.md)

- **Turn-based indexing** with single-pass LLM processing
  - Automatic indexing when conversation role transitions occur (user→assistant)
  - Smart filtering reduces token usage by 35-70%
  - Single-pass preprocessing via `custom_prompt` injection (eliminates redundant summarization pass)
  - Template-based preprocessing prompts with hierarchical resolution
  - See: [docs/ARCHITECTURE.md](ARCHITECTURE.md)

- **ActivityVector model** for intelligent session summarization
  - Structured metadata tracking for better context retrieval
  - Optimized for semantic search across sessions
  - Integrated with Neo4j knowledge graph

#### Daemon Architecture
- **Platform-agnostic daemon service** for persistent background operation
  - Runs as system service on Windows, macOS, and Linux
  - Unified HTTP/JSON API on port 8321 for all clients
  - Many-to-one client relationships (multiple sessions, one server)
  - Single Neo4j connection shared across all sessions
  - Auto-starts on system boot via bootstrap service
  - See: [docs/DAEMON_ARCHITECTURE.md](DAEMON_ARCHITECTURE.md)

- **Bootstrap service** for daemon lifecycle management
  - Auto-monitors config changes via file polling (5-second interval)
  - Config-driven daemon control (`daemon.enabled` is the single source of truth)
  - Automatic daemon restart when config enables/disables service
  - See: [docs/DAEMON_ARCHITECTURE.md](DAEMON_ARCHITECTURE.md)

- **Dedicated virtual environment** isolation for daemon
  - Installed to `~/.graphiti/venv/` with all dependencies
  - CLI wrapper scripts for PATH integration
  - Clean separation from user Python environments
  - See: [docs/DAEMON_ARCHITECTURE.md](DAEMON_ARCHITECTURE.md)

#### Configuration System
- **Per-project configuration overrides**
  - Projects identified by normalized Unix-style path (cross-platform)
  - Deep merge of project overrides with global defaults
  - Customize LLM models, extraction prompts, session tracking per project
  - Single file storage in `~/.graphiti/graphiti.config.json` under `project_overrides`
  - CLI visibility via `graphiti-mcp config effective --project <path>`
  - See: [docs/API_REFERENCE.md](API_REFERENCE.md)

- **Unified configuration schema** in `graphiti.config.json`
  - All structural settings version-controlled
  - Secrets separated to `.env` file
  - Schema validation with helpful error messages
  - Default configuration auto-generated on first run

#### Developer Experience
- **HTTP client** for daemon communication
  - Auto-discovery of running daemon
  - Graceful fallback with helpful error messages
  - Unified protocol for CLI and MCP server

- **Enhanced CLI commands**
  - `graphiti-mcp daemon install` - One-time daemon setup
  - `graphiti-mcp daemon status` - Check daemon health
  - `graphiti-mcp config effective` - View computed config for projects
  - `graphiti-mcp session list` - List recent sessions
  - See: [docs/CLI_REFERENCE.md](CLI_REFERENCE.md)

### Changed

#### Session Tracking
- **Session scope**: Project-isolated → Global with `project_namespace` metadata
  - Old: Separate `group_id` per project (e.g., `hostname__6f61768c`)
  - New: Single global `group_id` (e.g., `hostname__global`)
  - Migration: Automatic namespace tagging preserves provenance

- **Indexing trigger**: File watcher → Turn completion detection
  - Old: File system monitoring with JSONL parsing
  - New: In-process detection of role transitions
  - Benefit: Lower overhead, more reliable, no file I/O

- **LLM processing**: Dual-pass → Single-pass with preprocessing injection
  - Old: Summarization pass + entity extraction pass
  - New: Combined single pass via `custom_prompt` field
  - Benefit: ~13% token savings, faster indexing

#### MCP Server
- **Transport**: stdio → HTTP daemon (port 8321)
  - Old: Each Claude Code session spawned separate MCP server process
  - New: Single persistent daemon serves all clients
  - Benefit: Shared state, reduced resource usage, CLI connectivity

- **Configuration control**: Dual-mode → Config-primary
  - Old: CLI commands for start/stop + config file
  - New: Only `daemon.enabled` in config controls runtime state
  - Benefit: Single source of truth, no state conflicts

#### Installation & Setup
- **Virtual environment**: User's Python → Dedicated `~/.graphiti/venv/`
  - Old: Installed in user's active Python environment
  - New: Isolated venv with dedicated dependencies
  - Benefit: No version conflicts, clean uninstall

### Removed

- **File watcher module** - Replaced by turn-based detection
  - Removed: `graphiti_core/session_tracking/file_watcher.py`
  - Migration: Turn detection is automatic, no config changes needed

- **Session manager time-based logic** - Replaced by config-driven daemon
  - Removed: Auto-close timers, session lifecycle management
  - Migration: Daemon handles lifecycle via config polling

- **MCP tools** (deprecated in v1.0, removed in v2.0):
  - `session_tracking_start` - Removed (tracking is always-on or always-off via config)
  - `session_tracking_stop` - Removed (use config to disable)
  - Migration: Edit `graphiti.config.json` to set `session_tracking.enabled: false`

- **Per-project isolation** (without namespace tagging)
  - Removed: Distinct `group_id` per project
  - Migration: Automatic - namespace added to all episodes during upgrade

### Deprecated

- **stdio transport for MCP server**
  - Use HTTP daemon instead: `graphiti-mcp daemon install`
  - stdio support will be removed in v3.0.0
  - Reason: Daemon provides better resource sharing and CLI connectivity

### Fixed

- **Path handling across platforms** (Windows/Unix/WSL)
  - Normalized Unix-style paths for internal hashing
  - Native OS format for return values and display
  - Consistent cross-platform behavior

- **Connection reliability** with daemon auto-restart
  - Bootstrap service monitors daemon health
  - Automatic recovery from crashes
  - Clear error messages when daemon unavailable

- **Token efficiency** with preprocessing optimization
  - Single-pass LLM processing eliminates redundant calls
  - Smart filtering reduces content by 35-70%
  - Template-based prompts avoid repeated context

### Security

- **Credential isolation** - `.env` for secrets, config for structure
- **Config validation** - Schema validation prevents invalid settings
- **Daemon authentication** - localhost-only HTTP server (127.0.0.1)

---

## [1.0.0] - 2025-11-18

Initial release of session tracking system with project-scoped isolation and file watcher-based indexing.

### Added

- **Project-scoped session tracking**
  - Automatic session detection via file watcher
  - JSONL parsing of Claude Code conversation logs
  - Group ID isolation per project (`hostname__<project_hash>`)

- **File watcher** with JSONL parsing
  - Monitors `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/` for new messages
  - Configurable content filtering (tool calls, file diffs, etc.)
  - Turn boundary detection based on role transitions

- **MCP tool integration**
  - `add_memory` - Add episodes to knowledge graph
  - `search_memory_nodes` - Search for entities
  - `search_memory_facts` - Search for relationships
  - `session_tracking_start` - Enable tracking for current session
  - `session_tracking_stop` - Disable tracking for current session

- **Neo4j integration**
  - Episodes stored as graph nodes with temporal tracking
  - Entity and relationship extraction via LLM
  - Semantic search across conversation history

- **Configuration system**
  - `graphiti.config.json` for project settings
  - `.env` for credentials (Neo4j, OpenAI API keys)
  - Per-project customization support

### Known Limitations (v1.0)

- **No cross-project learning** - Projects completely isolated by `group_id`
- **Dual-pass LLM processing** - Separate summarization + entity extraction
- **File watcher overhead** - Continuous disk monitoring for changes
- **stdio transport only** - One MCP server process per Claude Code session
- **Manual session control** - Required explicit start/stop commands

---

## Migration Guides

### Upgrading from v1.0 to v2.0

**Breaking Changes:**
1. MCP tools `session_tracking_start` and `session_tracking_stop` removed
   - **Action**: Use `graphiti.config.json` to set `session_tracking.enabled: true/false`

2. Session scope changed from project-isolated to global
   - **Action**: None - automatic migration adds namespace tags to existing episodes
   - **Result**: Cross-project search enabled by default

3. stdio transport deprecated in favor of daemon
   - **Action**: Run `graphiti-mcp daemon install` for new daemon architecture
   - **Fallback**: stdio still works in v2.0 but will be removed in v3.0

**Recommended Actions:**
1. Install daemon: `graphiti-mcp daemon install`
2. Verify config: `graphiti-mcp config show`
3. Enable daemon: Edit `~/.graphiti/graphiti.config.json`, set `daemon.enabled: true`
4. Test connectivity: `graphiti-mcp daemon status`

### Upgrading from v2.0-beta to v2.0-stable

No breaking changes - all beta features stabilized in v2.0.0 release.

---

## Documentation

- [Architecture Overview](ARCHITECTURE.md) - System design and component details
- [Session Tracking User Guide](SESSION_TRACKING_USER_GUIDE.md) - End-user documentation
- [Daemon Architecture](DAEMON_ARCHITECTURE.md) - Technical details of daemon system
- [API Reference](API_REFERENCE.md) - Configuration schema and MCP tools
- [CLI Reference](CLI_REFERENCE.md) - Command-line interface documentation
- [MCP Tools Reference](MCP_TOOLS.md) - Available MCP tools and usage

---

## Links

- [GitHub Repository](https://github.com/getzep/graphiti)
- [Issue Tracker](https://github.com/getzep/graphiti/issues)
- [Discussions](https://github.com/getzep/graphiti/discussions)

---

**Note**: Dates in this changelog reflect the completion of implementation sprints, not public release dates. Graphiti is under active development.
