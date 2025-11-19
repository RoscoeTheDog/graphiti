# Graphiti CLI Reference

Complete command-line interface reference for Graphiti session tracking management.

**Version**: v1.0.0
**Last Updated**: 2025-11-18

---

## Table of Contents

1. [Installation](#installation)
2. [Session Tracking CLI](#session-tracking-cli)
3. [Configuration Validation CLI](#configuration-validation-cli)
4. [Examples](#examples)
5. [Troubleshooting](#troubleshooting)

---

## Installation

The CLI is automatically available after installing Graphiti:

```bash
pip install graphiti-core
# or
uv pip install graphiti-core
```

**Entry Points**:
- `graphiti-mcp-session-tracking` - Session tracking management
- `python -m mcp_server.config_validator` - Configuration validation

---

## Session Tracking CLI

### Command: `graphiti-mcp-session-tracking`

Manage session tracking configuration (enable/disable/status).

**Synopsis**:
```bash
graphiti-mcp-session-tracking <command> [options]
```

**Commands**:
- `enable` - Enable session tracking
- `disable` - Disable session tracking
- `status` - Show current configuration

---

### `enable` - Enable Session Tracking

**Description**: Enables automatic session tracking in Graphiti MCP server.

**Usage**:
```bash
graphiti-mcp-session-tracking enable [--config PATH]
```

**Options**:
- `--config PATH` - Path to graphiti.config.json (optional, auto-discovered if not provided)

**Config Discovery Order**:
1. `--config` argument (if provided)
2. `./graphiti.config.json` (project directory)
3. `~/.graphiti/graphiti.config.json` (global config)

**Behavior**:
- Sets `session_tracking.enabled = true` in configuration
- Preserves all other config values
- Creates global config if missing (with defaults)
- Validates configuration after update

**Example**:
```bash
# Enable using auto-discovered config
$ graphiti-mcp-session-tracking enable

✅ Session tracking enabled
Config: /home/user/.graphiti/graphiti.config.json

Session tracking configuration:
  Enabled: true
  Watch path: ~/.claude-code/sessions
  Check interval: 5 seconds
  Inactivity timeout: 300 seconds
```

```bash
# Enable using specific config
$ graphiti-mcp-session-tracking enable --config ./graphiti.config.json

✅ Session tracking enabled
Config: ./graphiti.config.json
```

**Exit Codes**:
- `0` - Success
- `1` - Error (invalid config, write failure)

---

### `disable` - Disable Session Tracking

**Description**: Disables automatic session tracking in Graphiti MCP server.

**Usage**:
```bash
graphiti-mcp-session-tracking disable [--config PATH]
```

**Options**:
- `--config PATH` - Path to graphiti.config.json (optional, auto-discovered if not provided)

**Behavior**:
- Sets `session_tracking.enabled = false` in configuration
- Preserves all other config values
- Does NOT stop currently running MCP server (restart required)

**Example**:
```bash
$ graphiti-mcp-session-tracking disable

✅ Session tracking disabled
Config: /home/user/.graphiti/graphiti.config.json

⚠️  Note: Restart MCP server for changes to take effect
```

**Exit Codes**:
- `0` - Success
- `1` - Error (config not found, write failure)

---

### `status` - Show Configuration Status

**Description**: Displays current session tracking configuration.

**Usage**:
```bash
graphiti-mcp-session-tracking status [--config PATH]
```

**Options**:
- `--config PATH` - Path to graphiti.config.json (optional, auto-discovered if not provided)

**Behavior**:
- Reads configuration (does not modify)
- Displays all session tracking settings
- Shows config file location

**Example**:
```bash
$ graphiti-mcp-session-tracking status

Session Tracking Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Config: /home/user/.graphiti/graphiti.config.json

Session Tracking:
  Enabled: true
  Watch path: ~/.claude-code/sessions
  Check interval: 5 seconds
  Inactivity timeout: 300 seconds

Filtering Configuration:
  Tool calls: SUMMARY
  Tool content: SUMMARY
  User messages: FULL
  Agent messages: FULL

Estimated token reduction: ~35%
```

**Exit Codes**:
- `0` - Success
- `1` - Error (config not found, invalid format)

---

## Configuration Validation CLI

### Command: `python -m mcp_server.config_validator`

Validate Graphiti configuration files.

**Synopsis**:
```bash
python -m mcp_server.config_validator [FILE] [OPTIONS]
```

**Arguments**:
- `FILE` - Path to graphiti.config.json (default: ./graphiti.config.json)

**Options**:
- `--level LEVEL` - Validation level: `syntax`, `schema`, `semantic`, `full` (default: `full`)
- `--json` - Output results as JSON
- `--no-path-check` - Skip path existence validation
- `--no-env-check` - Skip environment variable checking

---

### Validation Levels

#### `syntax` - JSON Syntax

Validates JSON syntax only (fastest).

```bash
$ python -m mcp_server.config_validator --level syntax

✅ JSON syntax valid
```

#### `schema` - Pydantic Schema

Validates against Pydantic models (type checking, required fields).

```bash
$ python -m mcp_server.config_validator --level schema

✅ Schema validation passed
  - All required fields present
  - All types correct
```

#### `semantic` - Semantic Validation

Validates field values make sense (paths exist, URIs valid, etc.).

```bash
$ python -m mcp_server.config_validator --level semantic

⚠️  Semantic warnings:
  - Environment variable NEO4J_PASSWORD not set
  - Path ~/.claude-code/sessions does not exist (will be created)
```

#### `full` - Complete Validation (default)

Runs all validation levels.

```bash
$ python -m mcp_server.config_validator

✅ Configuration valid

Validation Results:
  ✅ JSON syntax
  ✅ Schema (all fields valid)
  ⚠️  2 semantic warnings (non-blocking)

Warnings:
  - Environment variable NEO4J_PASSWORD not set
  - Path ~/.claude-code/sessions does not exist
```

---

### JSON Output Mode

**Usage**:
```bash
$ python -m mcp_server.config_validator --json
```

**Output**:
```json
{
  "valid": true,
  "level": "full",
  "errors": [],
  "warnings": [
    {
      "field": "neo4j_password",
      "message": "Environment variable NEO4J_PASSWORD not set",
      "severity": "warning"
    }
  ],
  "suggestions": [
    {
      "field": "session_tracking.watch_path",
      "message": "Path does not exist (will be created on startup)"
    }
  ]
}
```

**Exit Codes**:
- `0` - Valid (may have warnings)
- `1` - Invalid (has errors)

---

### Field Name Typo Detection

The validator suggests corrections for field name typos:

```bash
$ python -m mcp_server.config_validator

❌ Schema validation failed

Errors:
  - Unknown field: watch_directory
    Did you mean: watch_path?

  - Unknown field: inactivity_minutes
    Did you mean: inactivity_timeout?
```

---

## Examples

### Example 1: Initial Setup

```bash
# Check if session tracking is enabled
$ graphiti-mcp-session-tracking status

Session Tracking Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Config: ~/.graphiti/graphiti.config.json
Session Tracking: Enabled: true (default)

# Disable if desired (opt-out model)
$ graphiti-mcp-session-tracking disable

✅ Session tracking disabled
⚠️  Restart MCP server for changes to take effect
```

### Example 2: Configuration Validation Workflow

```bash
# Validate configuration before starting MCP server
$ python -m mcp_server.config_validator

✅ Configuration valid

# Check specific validation level
$ python -m mcp_server.config_validator --level schema

✅ Schema validation passed

# Get JSON output for CI/CD
$ python -m mcp_server.config_validator --json > validation-result.json
$ echo $?
0
```

### Example 3: Multi-Environment Setup

```bash
# Development config
$ graphiti-mcp-session-tracking status --config ./graphiti.dev.json

# Production config
$ graphiti-mcp-session-tracking status --config ./graphiti.prod.json

# Enable session tracking in development only
$ graphiti-mcp-session-tracking enable --config ./graphiti.dev.json
$ graphiti-mcp-session-tracking disable --config ./graphiti.prod.json
```

### Example 4: Troubleshooting

```bash
# Check current config
$ graphiti-mcp-session-tracking status

# Validate configuration
$ python -m mcp_server.config_validator

# Check for environment variables
$ python -m mcp_server.config_validator --level semantic

⚠️  Warnings:
  - NEO4J_PASSWORD not set (using placeholder)
  - OPENAI_API_KEY not set (required for LLM features)

# Fix environment variables
$ export NEO4J_PASSWORD="your-password"
$ export OPENAI_API_KEY="sk-..."

# Re-validate
$ python -m mcp_server.config_validator --level semantic

✅ All environment variables set
```

---

## Troubleshooting

### Common Issues

#### Issue: "Config file not found"

**Error**:
```
❌ Error: Configuration file not found
Searched locations:
  - ./graphiti.config.json
  - ~/.graphiti/graphiti.config.json
```

**Solution**:
```bash
# Create global config (automatically)
$ graphiti-mcp-session-tracking status

# Or specify custom location
$ graphiti-mcp-session-tracking status --config /path/to/config.json
```

---

#### Issue: "Invalid configuration format"

**Error**:
```
❌ Schema validation failed
  - Field 'session_tracking.enabled' must be boolean
  - Field 'session_tracking.check_interval' must be number
```

**Solution**:
```bash
# Validate configuration to see all errors
$ python -m mcp_server.config_validator

# Check example config
$ cat /path/to/graphiti/graphiti.config.json.example
```

---

#### Issue: "Changes not taking effect"

**Error**:
```
Session tracking still enabled after running 'disable'
```

**Solution**:
```bash
# CLI only modifies config file, must restart MCP server
$ pkill -f "graphiti_mcp_server"
$ # Restart MCP server via Claude Code or systemd

# Verify config was updated
$ graphiti-mcp-session-tracking status
```

---

#### Issue: "Permission denied writing config"

**Error**:
```
❌ Error: Permission denied writing to ~/.graphiti/graphiti.config.json
```

**Solution**:
```bash
# Check file permissions
$ ls -la ~/.graphiti/graphiti.config.json

# Fix permissions
$ chmod 644 ~/.graphiti/graphiti.config.json

# Or use project-level config (no sudo needed)
$ graphiti-mcp-session-tracking enable --config ./graphiti.config.json
```

---

## Environment Variables

CLI respects these environment variables:

- `GRAPHITI_CONFIG_PATH` - Override default config search path
- `NEO4J_PASSWORD` - Neo4j database password
- `OPENAI_API_KEY` - OpenAI API key for LLM features

**Example**:
```bash
export GRAPHITI_CONFIG_PATH="/etc/graphiti/config.json"
export NEO4J_PASSWORD="your-password"
export OPENAI_API_KEY="sk-..."

graphiti-mcp-session-tracking status
```

---

## Related Documentation

- [API Reference](API_REFERENCE.md) - Python API
- [Architecture](ARCHITECTURE.md) - System design
- [Configuration](../CONFIGURATION.md) - Config schema
- [Migration Guide](../claude-mcp-installer/instance/SESSION_TRACKING_MIGRATION.md)
- [Troubleshooting](SESSION_TRACKING_TROUBLESHOOTING.md)
