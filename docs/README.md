# Graphiti Documentation

Complete documentation for Graphiti's temporal knowledge graph and session tracking system.

**Version**: v1.0.0
**Last Updated**: 2025-11-18

---

## 📚 Documentation Index

### Getting Started

- **[Quick Start Guide](../README.md)** - Installation and basic usage
- **[Session Tracking Migration](../claude-mcp-installer/instance/SESSION_TRACKING_MIGRATION.md)** - Upgrade from v0.3.x to v1.0.0
- **[Configuration Guide](../CONFIGURATION.md)** - Complete configuration reference

### Core Documentation

- **[API Reference](API_REFERENCE.md)** - Complete Python API documentation
  - Session tracking API (parser, filter, indexer)
  - Filtering API (ContentMode, FilterConfig)
  - Path resolution API (cross-platform)
  - Configuration API (unified config system)
  - MCP tools API (runtime control)

- **[CLI Reference](CLI_REFERENCE.md)** - Command-line interface
  - `graphiti-mcp-session-tracking` (enable/disable/status)
  - `python -m mcp_server.config_validator` (validation)
  - Examples and troubleshooting

- **[Architecture Overview](ARCHITECTURE.md)** - System design
  - Component architecture
  - Data flow diagrams
  - Module descriptions
  - Integration points
  - Performance & scalability

### User Guides

- **[Session Tracking User Guide](SESSION_TRACKING_USER_GUIDE.md)** - End-user documentation
  - How session tracking works
  - Configuration options
  - Usage examples

- **[MCP Tools Reference](MCP_TOOLS.md)** - MCP tool documentation
  - Memory operations (add_memory, search)
  - Session tracking tools (start/stop/status)
  - Examples and usage patterns

### Developer Guides

- **[Session Tracking Dev Guide](SESSION_TRACKING_DEV_GUIDE.md)** - Developer documentation
  - Implementation details
  - Extension points
  - Testing strategies

- **[Troubleshooting Guide](SESSION_TRACKING_TROUBLESHOOTING.md)** - Common issues
  - Error messages and solutions
  - Performance tuning
  - Debugging tips

---

## 🎯 Quick Navigation

### By Role

**End Users (Claude Code users)**:
1. Start → [Quick Start Guide](../README.md)
2. Configure → [Configuration Guide](../CONFIGURATION.md)
3. Use → [Session Tracking User Guide](SESSION_TRACKING_USER_GUIDE.md)
4. Troubleshoot → [Troubleshooting Guide](SESSION_TRACKING_TROUBLESHOOTING.md)

**Developers (building on Graphiti)**:
1. Understand → [Architecture Overview](ARCHITECTURE.md)
2. Integrate → [API Reference](API_REFERENCE.md)
3. Extend → [Session Tracking Dev Guide](SESSION_TRACKING_DEV_GUIDE.md)
4. Validate → [CLI Reference](CLI_REFERENCE.md)

**System Administrators**:
1. Install → [Migration Guide](../claude-mcp-installer/instance/SESSION_TRACKING_MIGRATION.md)
2. Configure → [Configuration Guide](../CONFIGURATION.md)
3. Validate → [CLI Reference](CLI_REFERENCE.md#configuration-validation-cli)
4. Monitor → [Troubleshooting Guide](SESSION_TRACKING_TROUBLESHOOTING.md)

---

### By Task

#### "I want to enable session tracking"
→ [CLI Reference: enable command](CLI_REFERENCE.md#enable---enable-session-tracking)

#### "I want to understand how filtering works"
→ [API Reference: Filtering API](API_REFERENCE.md#filtering-api)

#### "I want to validate my configuration"
→ [CLI Reference: Configuration Validation](CLI_REFERENCE.md#configuration-validation-cli)

#### "I want to see the system architecture"
→ [Architecture Overview: Component Architecture](ARCHITECTURE.md#component-architecture)

#### "I want to use MCP tools"
→ [MCP Tools Reference](MCP_TOOLS.md)

#### "I'm getting errors"
→ [Troubleshooting Guide](SESSION_TRACKING_TROUBLESHOOTING.md)

---

## 📖 Documentation by Feature

### Session Tracking

| Topic | Documentation |
|-------|---------------|
| Overview | [Session Tracking User Guide](SESSION_TRACKING_USER_GUIDE.md) |
| API | [API Reference: Session Tracking API](API_REFERENCE.md#session-tracking-api) |
| CLI | [CLI Reference: Session Tracking CLI](CLI_REFERENCE.md#session-tracking-cli) |
| Architecture | [Architecture: Session Detection Flow](ARCHITECTURE.md#1-session-detection-flow) |
| MCP Tools | [MCP Tools: Session Tracking Tools](MCP_TOOLS.md#session-tracking-operations) |

### Smart Filtering

| Topic | Documentation |
|-------|---------------|
| Overview | [User Guide: Filtering Section](SESSION_TRACKING_USER_GUIDE.md) |
| API | [API Reference: Filtering API](API_REFERENCE.md#filtering-api) |
| Configuration | [Configuration: Filtering Config](../CONFIGURATION.md#filtering-configuration) |
| Architecture | [Architecture: Filtering Flow](ARCHITECTURE.md#2-filtering-flow) |

### Knowledge Graph

| Topic | Documentation |
|-------|---------------|
| Overview | [Quick Start: Memory Operations](../README.md) |
| API | [API Reference: MCP Tools API](API_REFERENCE.md#mcp-tools-api) |
| MCP Tools | [MCP Tools: Memory Operations](MCP_TOOLS.md#memory-operations) |
| Architecture | [Architecture: Neo4j Integration](ARCHITECTURE.md#neo4j-knowledge-graph) |

### Configuration

| Topic | Documentation |
|-------|---------------|
| Reference | [Configuration Guide](../CONFIGURATION.md) |
| API | [API Reference: Configuration API](API_REFERENCE.md#configuration-api) |
| Validation | [CLI Reference: Validation CLI](CLI_REFERENCE.md#configuration-validation-cli) |
| Examples | [Configuration: Examples](../CONFIGURATION.md#example-configurations) |

---

## 🔧 Common Workflows

### First-Time Setup

1. **Install Graphiti**: `pip install graphiti-core`
2. **Configure Neo4j**: Set `NEO4J_PASSWORD` environment variable
3. **Configure OpenAI**: Set `OPENAI_API_KEY` environment variable
4. **Validate Config**: `python -m mcp_server.config_validator`
5. **Check Status**: `graphiti-mcp-session-tracking status`

**Documentation**: [Migration Guide](../claude-mcp-installer/instance/SESSION_TRACKING_MIGRATION.md)

---

### Disable Session Tracking (Opt-Out)

1. **Disable via CLI**: `graphiti-mcp-session-tracking disable`
2. **Restart MCP Server**: Restart Claude Code or MCP server process
3. **Verify**: `graphiti-mcp-session-tracking status`

**Documentation**: [CLI Reference: disable command](CLI_REFERENCE.md#disable---disable-session-tracking)

---

### Custom Filtering Configuration

1. **Edit Config**: Open `graphiti.config.json`
2. **Modify Filter**: Change `session_tracking.filter` section
3. **Validate**: `python -m mcp_server.config_validator`
4. **Restart**: Restart MCP server for changes to take effect

**Documentation**: [Configuration: Filtering](../CONFIGURATION.md#filtering-configuration)

**Example**:
```json
{
  "session_tracking": {
    "filter": {
      "tool_calls": "SUMMARY",
      "tool_content": "OMIT",
      "user_messages": "FULL",
      "agent_messages": "SUMMARY"
    }
  }
}
```

---

### Troubleshooting Errors

1. **Check Status**: `graphiti-mcp-session-tracking status`
2. **Validate Config**: `python -m mcp_server.config_validator`
3. **Check Logs**: Look for errors in MCP server output
4. **Consult Guide**: [Troubleshooting Guide](SESSION_TRACKING_TROUBLESHOOTING.md)

**Common Issues**:
- Config file not found → [Solution](SESSION_TRACKING_TROUBLESHOOTING.md)
- Permission denied → [Solution](CLI_REFERENCE.md#issue-permission-denied-writing-config)
- Changes not applying → [Solution](CLI_REFERENCE.md#issue-changes-not-taking-effect)

---

## 📊 Documentation Metrics

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| API Reference | Complete API docs | Developers | 600+ lines |
| CLI Reference | Command-line guide | Users, Admins | 500+ lines |
| Architecture | System design | Developers | 700+ lines |
| MCP Tools | Tool reference | Users | 400+ lines |
| User Guide | End-user docs | Users | 300+ lines |
| Dev Guide | Developer docs | Developers | 800+ lines |
| Troubleshooting | Error solutions | All | 600+ lines |

**Total**: 3,900+ lines of comprehensive documentation

---

## 🔗 External Resources

- **Graphiti Core**: https://github.com/getzep/graphiti
- **Neo4j Documentation**: https://neo4j.com/docs/
- **OpenAI API**: https://platform.openai.com/docs/
- **MCP Protocol**: https://spec.modelcontextprotocol.io/

---

## 📝 Contributing to Documentation

Found an error or want to improve the documentation?

1. **Report Issues**: Open an issue on GitHub
2. **Suggest Improvements**: Create a pull request
3. **Ask Questions**: Use GitHub Discussions

**Documentation Source**: All markdown files in `docs/` directory

---

## 🎓 Learning Path

### Beginner (Just Getting Started)

1. Read: [Quick Start Guide](../README.md)
2. Install: Follow installation steps
3. Configure: [Configuration Guide](../CONFIGURATION.md)
4. Verify: `graphiti-mcp-session-tracking status`

### Intermediate (Customizing Graphiti)

1. Understand: [Architecture Overview](ARCHITECTURE.md)
2. Configure: Custom filtering via [Configuration](../CONFIGURATION.md)
3. Use: [MCP Tools Reference](MCP_TOOLS.md)
4. Troubleshoot: [Troubleshooting Guide](SESSION_TRACKING_TROUBLESHOOTING.md)

### Advanced (Building on Graphiti)

1. Study: [API Reference](API_REFERENCE.md)
2. Extend: [Session Tracking Dev Guide](SESSION_TRACKING_DEV_GUIDE.md)
3. Integrate: Custom parsers, filters, or indexers
4. Contribute: Submit pull requests

---

## 📅 Documentation Changelog

### v1.0.0 (2025-11-18)

- ✅ Added comprehensive API Reference
- ✅ Added complete CLI Reference
- ✅ Added Architecture Overview
- ✅ Added Documentation Index (this file)
- ✅ Updated all cross-references
- ✅ Verified all examples and code snippets

### Previous Versions

- v0.3.x: Initial session tracking documentation
- v0.2.x: MCP tools documentation
- v0.1.x: Core Graphiti documentation

---

**Last Updated**: 2025-11-18
**Version**: v1.0.0
