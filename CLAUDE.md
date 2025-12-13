# Claude Agent Directives - Graphiti

**Purpose**: Instructions for AI assistants (Claude agents) when working with Graphiti codebase and MCP server.

**Audience**: AI assistants only (not end users)

**User Documentation**: See [docs/](docs/) and project root markdown files

---

## Configuration System

Graphiti uses a **unified configuration system**:
- **graphiti.config.json** - All structural settings (version controlled)
- **.env** - Secrets only (passwords, API keys)

**Agent Actions**:
- When modifying configuration, update `graphiti.config.json` (not scattered config files)
- Never commit secrets - use `.env` for passwords/API keys
- Reference [CONFIGURATION.md](CONFIGURATION.md) for complete config schema

---

## MCP Server Context

When the agent is running as an MCP server (via `mcp_server/graphiti_mcp_server.py`), the following tools are available to Claude Code:

### Available MCP Tools

- `add_memory` - Add episodes to the knowledge graph
- `search_memory_nodes` - Search for entities
- `search_memory_facts` - Search for relationships
- `get_episodes` - Retrieve recent episodes
- `delete_episode` - Remove episodes
- `delete_entity_edge` - Remove relationships
- `clear_graph` - Clear all data (use with caution)
- `health_check` - Check server health and database connectivity

**User Documentation**: See [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md) for detailed tool reference.

---

## Resilience Features

The MCP server includes automatic recovery and monitoring:

- **Automatic Reconnection**: Reconnects to database on connection failure with exponential backoff
- **Episode Timeouts**: Prevents indefinite hangs (default: 60 seconds per episode)
- **Health Monitoring**: Tracks connection status and processing metrics
- **Queue Recovery**: Queue workers restart automatically after successful reconnection
- **Error Classification**: Distinguishes recoverable errors (retries) from fatal errors (stops)

**Agent Actions**:
- Use `health_check` tool before bulk memory operations
- Monitor connection metrics when debugging MCP server issues
- Reference resilience config in `graphiti.config.json` under `resilience` section

**Configuration Reference**: [CONFIGURATION.md](CONFIGURATION.md#resilience-configuration)

---

## Codebase Guidelines

### When Working on Code

1. **Platform-Agnostic Path Handling**: **CRITICAL REQUIREMENT**
   - **All path operations MUST be platform-agnostic**
   - **Hashing/Internal**: Always normalize to UNIX format (`/c/Users/...` on Windows)
   - **Return Values**: Always use native OS format (`C:\Users\...` on Windows, `/home/...` on Unix)
   - Use Python's `pathlib.Path` for all path operations (handles platform automatically)
   - Test on both Windows and Unix platforms
   - See: `.claude/implementation/PLATFORM_AGNOSTIC_PATHS.md`

2. **Type Safety**: Graphiti uses Pydantic for configuration validation
   - Maintain type hints in all code
   - Use Pydantic models for config schemas
   - All functions must have type-annotated parameters and return values

3. **Testing**: Tests are in `tests/` directory
   - Run tests with `pytest tests/`
   - Maintain >80% test coverage for new features
   - Include platform-specific tests (Windows + Unix)
   - Test error conditions and edge cases

4. **Configuration Changes**:
   - Update `graphiti.config.json` schema if adding new config options
   - Update `CONFIGURATION.md` with new options
   - Maintain backward compatibility or document breaking changes
   - Use unified configuration system (no scattered config files)

5. **Error Handling and Logging**:
   - All file I/O wrapped in try-except blocks
   - Use appropriate logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Include context in error messages (file paths, IDs)
   - Log unexpected errors with stack traces (`exc_info=True`)

6. **Memory Operations**:
   - Episodes are stored in Neo4j graph database
   - Support for text, JSON, and message sources
   - Automatic temporal tracking

### Cross-Cutting Requirements

**ALL new code must satisfy requirements in `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`**

Key requirements:
- Platform-agnostic path handling
- Comprehensive error handling and logging
- Type safety with Pydantic models
- >80% test coverage with platform-specific tests
- <5% performance overhead
- No exposure of sensitive information
- Unified configuration system
- Complete user and developer documentation

### Migration Notes

- **From Old System**: `.env`-only configuration (pre-v2.0)
- **To New System**: Unified `graphiti.config.json` + `.env` secrets
- **Migration Guide**: [.claude/implementation/guides/MIGRATION_GUIDE.md](.claude/implementation/guides/MIGRATION_GUIDE.md)

---

## Database Context

Graphiti requires Neo4j database:

**Supported Backends**:
- Neo4j Community Edition (local, free)
- Neo4j Aura (cloud, managed)
- Neo4j Docker (containerized)

**Agent Actions**:
- Recommend Neo4j Community Edition for cost-effectiveness ($0 vs $780/year for Aura)
- Use `neo4j+ssc://` URI scheme for VMs (not `neo4j+s://`)
- Reference installation guide: `claude-mcp-installer/instance/CLAUDE_INSTALL.md`

---

## Installation & Setup

**For MCP Server Installation**:
- Guide: `claude-mcp-installer/instance/CLAUDE_INSTALL.md`
- Templates: `claude-mcp-installer/templates/`
- User must provide: Neo4j credentials, OpenAI API key

**Agent Workflow**:
- Follow installation guide interactively with user
- Detect VM environment for URI scheme fixes
- Verify credentials before MCP server registration
- Test connection with `health_check` after setup

---

## Documentation Structure

**Agent Directives** (this file):
- CLAUDE.md - Instructions for AI assistants

**User Documentation**:
- README.md - Project overview, quick start
- CONFIGURATION.md - Complete configuration reference
- docs/MCP_TOOLS.md - MCP tools reference
- claude-mcp-installer/ - Installation guides

**Developer Documentation**:
- .claude/implementation/ - Sprint tracking, implementation plans
- .claude/context/ - Analysis, troubleshooting
- CONTRIBUTING.md - Contribution guidelines

---

## Related Files

**Configuration & Requirements**:
- **[CONFIGURATION.md](CONFIGURATION.md)** - Configuration schema and reference
- **[.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md](.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md)** - Cross-cutting requirements for all code
- **[.claude/implementation/PLATFORM_AGNOSTIC_PATHS.md](.claude/implementation/PLATFORM_AGNOSTIC_PATHS.md)** - Platform-agnostic path handling guide

**User Documentation**:
- **[README.md](README.md)** - User-facing quick start
- **[docs/MCP_TOOLS.md](docs/MCP_TOOLS.md)** - MCP tools user documentation
- **[claude-mcp-installer/instance/CLAUDE_INSTALL.md](claude-mcp-installer/instance/CLAUDE_INSTALL.md)** - Installation guide

**Implementation**:
- **[.claude/implementation/index.md](.claude/implementation/index.md)** - Sprint tracking and implementation plans

---

**Last Updated:** 2025-11-13
**Version:** 3.1 (Added Platform-Agnostic Requirements)
