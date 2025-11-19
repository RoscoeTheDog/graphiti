# Final Configuration Schema and File Structure

**Purpose**: Finalized design with proper file structure hierarchy and removal of redundant max_summary_chars parameter.

---

## Key Changes from Previous Design

1. ✅ **Removed `max_summary_chars`** - Templates control their own length via prompts
2. ✅ **Unified file structure** - Same structure for global (`~/.graphiti/`) and local (project) directories
3. ✅ **Resolution order** - Project → Global → Hardcoded defaults

---

## Final Configuration Schema

```python
class FilterConfig(BaseModel):
    """Simplified filtering configuration.
    
    Each field accepts:
    - true: Capture full content (no filtering)
    - false: Omit content entirely (structure only)
    - str: Path to .md template OR inline prompt string
    
    Templates control their own length via prompt instructions.
    NO max_summary_chars - templates are self-describing.
    """
    
    tool_calls: bool = Field(
        default=True,
        description="Preserve tool call structure (names, parameters). Recommended: true"
    )
    
    tool_content: bool | str = Field(
        default="default_tool_content.md",
        description=(
            "Tool result filtering:\n"
            "  true = full content\n"
            "  false = omit entirely\n"
            "  'template.md' = use template (project → global → built-in)\n"
            "  'inline prompt...' = use string as prompt"
        )
    )
    
    user_messages: bool | str = Field(
        default=True,
        description=(
            "User message filtering:\n"
            "  true = full content\n"
            "  false = omit entirely\n"
            "  'template.md' = use template\n"
            "  'inline prompt...' = use string as prompt"
        )
    )
    
    agent_messages: bool | str = Field(
        default=True,
        description=(
            "Agent response filtering:\n"
            "  true = full content\n"
            "  false = omit entirely\n"
            "  'template.md' = use template\n"
            "  'inline prompt...' = use string as prompt"
        )
    )
```

---

## Unified File Structure

### Global Directory: `~/.graphiti/`
```
~/.graphiti/
├── auto_tracking/
│   ├── templates/
│   │   ├── default_tool_content.md
│   │   ├── default_user_messages.md
│   │   └── default_agent_messages.md
│   └── session_tracking.json         (global config override)
├── graphiti.config.json              (main config)
└── ... (other graphiti files)
```

### Project Directory: `<project_root>/.graphiti/`
```
<project_root>/.graphiti/
├── auto_tracking/
│   ├── templates/
│   │   ├── custom_tool_content.md     (project-specific override)
│   │   └── custom_agent_messages.md
│   └── session_tracking.json          (project config override)
└── ... (other project-specific files)
```

---

## Template Resolution Order

### Resolution Logic
```
1. Check project directory: <project_root>/.graphiti/auto_tracking/templates/{template_name}
2. Check global directory: ~/.graphiti/auto_tracking/templates/{template_name}
3. Use hardcoded built-in (packaged with Graphiti)
```

### Implementation

```python
def resolve_template_path(
    template_value: str,
    project_root: Path | None = None
) -> str:
    """Resolve template from config value with hierarchy.
    
    Args:
        template_value: Template filename, path, or inline prompt
        project_root: Optional project root for project-specific templates
    
    Returns:
        Resolved prompt template string
    
    Resolution order:
        1. Project: <project_root>/.graphiti/auto_tracking/templates/{template_value}
        2. Global: ~/.graphiti/auto_tracking/templates/{template_value}
        3. Built-in: graphiti_core/session_tracking/prompts/{template_value}
        4. Inline: Treat as inline prompt string
    """
    # If absolute path, use directly
    if Path(template_value).is_absolute():
        path = Path(template_value)
        if path.exists():
            return path.read_text()
        raise FileNotFoundError(f"Template not found: {template_value}")
    
    # If looks like inline prompt (no .md extension), use directly
    if not template_value.endswith('.md'):
        return template_value
    
    # Resolution hierarchy
    search_paths = []
    
    # 1. Project-specific template
    if project_root:
        project_template = project_root / ".graphiti" / "auto_tracking" / "templates" / template_value
        search_paths.append(project_template)
    
    # 2. Global template
    global_template = Path.home() / ".graphiti" / "auto_tracking" / "templates" / template_value
    search_paths.append(global_template)
    
    # 3. Built-in template (packaged with Graphiti)
    builtin_template = Path(__file__).parent / "prompts" / template_value
    search_paths.append(builtin_template)
    
    # Try each path in order
    for path in search_paths:
        if path.exists():
            logger.debug(f"Resolved template '{template_value}' -> {path}")
            return path.read_text()
    
    # Fallback: treat as inline prompt
    logger.debug(f"Template '{template_value}' not found, treating as inline prompt")
    return template_value
```

---

## Default Template Creation

### On MCP Server Initialization

```python
def ensure_default_templates_exist():
    """Create default templates in global directory if they don't exist.
    
    This runs on MCP server startup to ensure users always have
    working templates available for customization.
    """
    global_templates_dir = Path.home() / ".graphiti" / "auto_tracking" / "templates"
    global_templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Default templates (hardcoded in source)
    defaults = {
        "default_tool_content.md": BUILTIN_TOOL_CONTENT_TEMPLATE,
        "default_user_messages.md": BUILTIN_USER_MESSAGES_TEMPLATE,
        "default_agent_messages.md": BUILTIN_AGENT_MESSAGES_TEMPLATE,
    }
    
    for filename, content in defaults.items():
        template_path = global_templates_dir / filename
        
        if not template_path.exists():
            template_path.write_text(content)
            logger.info(f"Created default template: {template_path}")
```

### Hardcoded Built-in Templates

```python
# In graphiti_core/session_tracking/prompts.py

BUILTIN_TOOL_CONTENT_TEMPLATE = """Summarize this tool result concisely in 1 paragraph.

**Tool**: {context}

**Focus on**:
- What operation was performed
- Key findings or outputs
- Any errors or warnings
- Relevant file paths, function names, or data values

**Original content**:
{content}

**Summary** (1 paragraph, actionable information):
"""

BUILTIN_USER_MESSAGES_TEMPLATE = """Summarize this user message in 1-2 sentences.

**Context**: {context}

**Focus on**:
- What the user is asking for
- Key requirements or constraints
- Context or background provided

**Original message**:
{content}

**Summary** (preserve user intent):
"""

BUILTIN_AGENT_MESSAGES_TEMPLATE = """Summarize this agent response in 1 paragraph.

**Context**: {context}

**Focus on**:
- Main explanation or reasoning
- Decisions made or approaches taken
- Important context or caveats
- Follow-up actions planned

**Original response**:
{content}

**Summary** (reasoning and decisions):
"""
```

---

## Configuration Examples

### Example 1: Default Configuration (Auto-generated)

**`~/.graphiti/graphiti.config.json`**:
```json
{
  "session_tracking": {
    "enabled": false,
    "watch_path": null,
    "inactivity_timeout": 45,
    "check_interval": 15,
    "auto_summarize": false,
    "store_in_graph": true,
    "keep_length_days": 7,
    
    "filter": {
      "tool_calls": true,
      "tool_content": "default_tool_content.md",
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

**Generated files**:
```
~/.graphiti/
├── auto_tracking/
│   └── templates/
│       ├── default_tool_content.md      (created from hardcoded source)
│       ├── default_user_messages.md     (created from hardcoded source)
│       └── default_agent_messages.md    (created from hardcoded source)
└── graphiti.config.json
```

---

### Example 2: Global Template Customization

**User edits**: `~/.graphiti/auto_tracking/templates/default_tool_content.md`
```markdown
Summarize this tool output in 2-3 sentences maximum.

Tool: {context}

Content:
{content}

Brief summary:
```

**All projects** using `"tool_content": "default_tool_content.md"` now use this custom version.

---

### Example 3: Project-Specific Template Override

**Project structure**:
```
/home/user/my-project/
├── .graphiti/
│   └── auto_tracking/
│       └── templates/
│           └── custom_tool_content.md   (project-specific)
└── ... (project files)
```

**`custom_tool_content.md`**:
```markdown
Extract code-related information from this tool result (focus on technical details):

{content}

Technical summary (functions, classes, errors):
```

**Config** (can be global or project-specific):
```json
{
  "filter": {
    "tool_content": "custom_tool_content.md"
  }
}
```

**Resolution**: Uses project-specific template when running in this project.

---

### Example 4: Inline Prompt (No Template File)

**Config**:
```json
{
  "filter": {
    "tool_content": "Describe what this tool did in 1 sentence: {content}"
  }
}
```

**Resolution**: Uses inline string directly (no file lookup).

---

### Example 5: Mixed Configuration

**Global config** (`~/.graphiti/graphiti.config.json`):
```json
{
  "filter": {
    "tool_content": "default_tool_content.md",
    "user_messages": true,
    "agent_messages": "Brief summary of agent response: {content}"
  }
}
```

**Project override** (`/path/to/project/.graphiti/auto_tracking/session_tracking.json`):
```json
{
  "filter": {
    "tool_content": "custom_tool_content.md"
  }
}
```

**Effective config for this project**:
- `tool_content`: `custom_tool_content.md` (project override)
- `user_messages`: `true` (from global)
- `agent_messages`: Inline prompt (from global)

---

## Template Variables

Templates can use:
- `{content}` - The actual message/tool result content
- `{context}` - Context hint (e.g., "tool: Read", "user message", "agent response")

**NO `{max_chars}`** - Templates control their own length via instructions.

**Examples**:
```markdown
Summarize in 1 paragraph...     (self-describing)
Summarize in 2-3 sentences...   (self-describing)
Summarize in 10 words or less... (self-describing)
```

---

## Auto-Generation Logic

### On MCP Server Startup

```python
async def initialize_server():
    """Initialize MCP server with Graphiti capabilities."""
    
    # 1. Ensure global config exists
    ensure_global_config_exists()  # Creates ~/.graphiti/graphiti.config.json
    
    # 2. Ensure default templates exist
    ensure_default_templates_exist()  # Creates ~/.graphiti/auto_tracking/templates/*.md
    
    # 3. Load and validate configuration
    global unified_config
    unified_config = await load_and_validate_unified_config()
    
    # ... rest of initialization
```

---

## Configuration Resolution Hierarchy

### For `graphiti.config.json`

**Resolution order**:
```
1. Project config: <project_root>/.graphiti/graphiti.config.json
2. Global config: ~/.graphiti/graphiti.config.json
3. Defaults: Hardcoded in unified_config.py
```

### For Templates

**Resolution order** (per template reference):
```
1. Project template: <project_root>/.graphiti/auto_tracking/templates/{name}
2. Global template: ~/.graphiti/auto_tracking/templates/{name}
3. Built-in: graphiti_core/session_tracking/prompts/{name}
4. Inline: Treat string as prompt
```

---

## Benefits of This Structure

1. **Consistent hierarchy**: Project → Global → Built-in
2. **No redundant parameters**: Templates self-describe length constraints
3. **Easy customization**: Edit files, no code changes
4. **Team standards**: Commit project `.graphiti/` to version control
5. **Personal defaults**: Customize global templates once, use everywhere
6. **Graceful fallback**: Always works (built-in templates packaged)

---

## Migration from Previous Design

### Removed

❌ `max_summary_chars` parameter (redundant, templates control length)
❌ `summary_prompts` nested config (simplified to direct references)
❌ Scattered prompt locations (unified under `auto_tracking/templates/`)

### Added

✅ Unified file structure (`auto_tracking/templates/`)
✅ Project-level template overrides
✅ Hierarchical resolution (Project → Global → Built-in)

---

## File Structure Reference

### Global (`~/.graphiti/`)
```
~/.graphiti/
├── auto_tracking/
│   ├── templates/
│   │   ├── default_tool_content.md
│   │   ├── default_user_messages.md
│   │   ├── default_agent_messages.md
│   │   └── custom_*.md (user-created)
│   └── session_tracking.json (optional global override)
├── graphiti.config.json
└── ... (other graphiti files)
```

### Project (`<project_root>/.graphiti/`)
```
<project_root>/.graphiti/
├── auto_tracking/
│   ├── templates/
│   │   └── *.md (project-specific templates)
│   └── session_tracking.json (optional project override)
└── ... (other project files)
```

### Packaged (ships with Graphiti)
```
graphiti_core/session_tracking/
├── prompts/
│   ├── default_tool_content.md (fallback)
│   ├── default_user_messages.md (fallback)
│   └── default_agent_messages.md (fallback)
└── prompts.py (hardcoded sources for auto-generation)
```

---

## Final Configuration Schema (JSON)

```json
{
  "session_tracking": {
    "enabled": false,
    "watch_path": null,
    "inactivity_timeout": 45,
    "check_interval": 15,
    "auto_summarize": false,
    "store_in_graph": true,
    "keep_length_days": 7,
    
    "filter": {
      "tool_calls": true,
      "tool_content": "default_tool_content.md",
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

**Total parameters**: 10 (removed `max_summary_chars`)

---

## Implementation Checklist

- [ ] Remove `max_summary_chars` from `FilterConfig`
- [ ] Create hardcoded template constants in `prompts.py`
- [ ] Implement `ensure_default_templates_exist()` function
- [ ] Update `resolve_template_path()` with hierarchy logic
- [ ] Create `auto_tracking/templates/` directories on init
- [ ] Update auto-generated config to use new structure
- [ ] Remove all references to `{max_chars}` template variable
- [ ] Update documentation (CONFIGURATION.md, user guide)
- [ ] Write tests for template resolution hierarchy
- [ ] Write tests for auto-generation logic

---

**Design Status**: FINAL - Ready for implementation
**File Structure**: Unified (global and project use same structure)
**Resolution Order**: Project → Global → Built-in → Inline
