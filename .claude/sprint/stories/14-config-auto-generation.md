# Story 14: Configuration Auto-Generation - First-Run Experience

**Status**: unassigned
**Created**: 2025-11-18 23:01
**Priority**: MEDIUM
**Estimated Effort**: 4 hours
**Phase**: 6 (Week 3, Days 1-2)
**Depends on**: Story 11 (template system)

## Description

Ensure users always have working configuration from moment of installation by auto-generating `~/.graphiti/graphiti.config.json` and default templates on first run. This improves first-run experience and reduces configuration errors.

**Features**:
- Auto-generate config file with inline comments
- Auto-generate default templates
- No overwrite of existing files
- Called automatically on MCP server startup
- Clear logging of created files

## Acceptance Criteria

### Config Auto-Generation
- [ ] Implement `ensure_global_config_exists()` function
- [ ] Create config template with inline comments (_comment fields)
- [ ] Generate `~/.graphiti/graphiti.config.json` if missing
- [ ] Skip generation if file already exists
- [ ] Log config file creation
- [ ] Test: Config created on first run
- [ ] Test: No overwrite on subsequent runs
- [ ] Test: Generated config is valid JSON
- [ ] Test: Generated config loads without errors

### Template Auto-Generation
- [ ] Config auto-generation calls `ensure_default_templates_exist()` (from Story 11)
- [ ] Templates created in `~/.graphiti/auto-tracking/templates/`
- [ ] Skip if templates already exist
- [ ] Test: Templates created with config
- [ ] Test: No overwrite of custom templates

### Server Startup Integration
- [ ] Update `initialize_server()` to call auto-generation
- [ ] Call before loading config (ensure file exists)
- [ ] Handle errors gracefully (log and continue)
- [ ] Test: MCP server starts with no config
- [ ] Test: Config and templates created automatically

## Implementation Details

### Files to Modify

**`mcp_server/graphiti_mcp_server.py`**:

Add config generation function:

```python
def ensure_global_config_exists() -> Path:
    """Ensure global configuration file exists with sensible defaults.

    Creates ~/.graphiti/graphiti.config.json if it doesn't exist.
    Includes inline comments to guide users.

    Returns:
        Path to config file
    """
    config_path = Path.home() / ".graphiti" / "graphiti.config.json"

    if config_path.exists():
        logger.debug(f"Config file already exists: {config_path}")
        return config_path

    # Create directory
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate config with inline comments
    default_config = {
        "_comment": "Graphiti MCP Server Configuration (auto-generated)",
        "_docs": "https://github.com/getzep/graphiti/blob/main/CONFIGURATION.md",

        "database": {
            "_comment": "Required: Configure your Neo4j connection",
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "CHANGE_ME",
        },

        "llm": {
            "_comment": "Required: Configure your OpenAI API key",
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "CHANGE_ME",
        },

        "session_tracking": {
            "_comment": "Session tracking is DISABLED by default for security",
            "_docs": "See docs/SESSION_TRACKING_USER_GUIDE.md",

            "enabled": False,
            "_enabled_help": "Set to true to enable session tracking (opt-in)",

            "watch_path": None,
            "_watch_path_help": "null = ~/.claude/projects/ | Set to specific project path",

            "inactivity_timeout": 900,
            "_inactivity_timeout_help": "Seconds before session closed (900 = 15 minutes, handles long operations)",

            "check_interval": 60,
            "_check_interval_help": "Seconds between inactivity checks (60 = 1 minute, responsive)",

            "auto_summarize": False,
            "_auto_summarize_help": "Use LLM to summarize sessions (costs money, set to true to enable)",

            "store_in_graph": True,
            "_store_in_graph_help": "Store in Neo4j graph (required for cross-session memory)",

            "keep_length_days": 7,
            "_keep_length_days_help": "Track sessions from last N days (7 = safe, null = all)",

            "filter": {
                "_comment": "Message filtering for token reduction",

                "tool_calls": True,
                "_tool_calls_help": "Preserve tool structure (recommended: true)",

                "tool_content": "default-tool-content.md",
                "_tool_content_help": "true (full) | false (omit) | 'template.md' | 'inline prompt...'",

                "user_messages": True,
                "_user_messages_help": "true (full) | false (omit) | 'template.md' | 'inline prompt...'",

                "agent_messages": True,
                "_agent_messages_help": "true (full) | false (omit) | 'template.md' | 'inline prompt...'",
            },
        },
    }

    # Write config
    with open(config_path, "w") as f:
        json.dump(default_config, f, indent=2)

    logger.info(f"Created default config: {config_path}")
    logger.info("Please update database credentials and OpenAI API key!")

    return config_path
```

Update server initialization:

```python
async def initialize_server():
    """Initialize Graphiti MCP server."""
    # Ensure config and templates exist (auto-generate if missing)
    try:
        config_path = ensure_global_config_exists()
        ensure_default_templates_exist()  # From Story 11
    except Exception as e:
        logger.error(f"Failed to auto-generate config/templates: {e}", exc_info=True)
        # Continue - user may have config in project directory

    # Load configuration
    global unified_config
    try:
        unified_config = load_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}", exc_info=True)
        raise

    # ... rest of initialization ...
```

### Testing Requirements

**Create**: `tests/test_config_generation.py`

Test cases:

1. **Config Generation**:
   - Config created when missing
   - No overwrite when exists
   - Generated config is valid JSON
   - Generated config loads without errors

2. **Template Generation**:
   - Templates created with config
   - No overwrite of custom templates

3. **Server Integration**:
   - Server starts with no config
   - Config and templates auto-created
   - Server continues if generation fails

4. **File Content**:
   - All required sections present
   - Inline comments included
   - Help fields included
   - Defaults match schema

Example test:

```python
def test_config_auto_generation():
    """Test that config is auto-generated on first run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override home directory
        config_path = Path(tmpdir) / ".graphiti" / "graphiti.config.json"

        # Ensure config doesn't exist
        assert not config_path.exists()

        # Call generation
        result_path = ensure_global_config_exists()

        # Verify config created
        assert config_path.exists()
        assert result_path == config_path

        # Verify valid JSON
        with open(config_path) as f:
            config = json.load(f)

        # Verify structure
        assert "database" in config
        assert "llm" in config
        assert "session_tracking" in config

        # Verify comments
        assert "_comment" in config
        assert "_docs" in config

        # Verify no overwrite on second call
        original_mtime = config_path.stat().st_mtime
        time.sleep(0.1)
        ensure_global_config_exists()
        assert config_path.stat().st_mtime == original_mtime
```

## Dependencies

- Story 11 (template system) - calls `ensure_default_templates_exist()`

## Related Documents

- `.claude/handoff/session-tracking-complete-overhaul-2025-11-18.md` (Section: New Features - Feature 4)

## Cross-Cutting Requirements

See parent sprint `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`:
- Platform-agnostic paths: Use pathlib.Path
- Error handling: Graceful handling of write errors
- Type hints: All functions properly typed
- Testing: >80% coverage
- Security: No plaintext secrets (use CHANGE_ME placeholders)
- Documentation: Inline comments in generated config
