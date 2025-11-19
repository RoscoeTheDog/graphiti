# Story 11: Template System Implementation - Pluggable Summarization

**Status**: unassigned
**Created**: 2025-11-18 23:01
**Priority**: HIGH
**Estimated Effort**: 8 hours
**Phase**: 3 (Week 1, Day 5 - Week 2, Day 1)
**Depends on**: Story 10 (configuration schema changes)

## Description

Implement a pluggable template system that allows users to customize summarization behavior without code changes. Templates use a resolution hierarchy (Project → Global → Built-in → Inline) and support both file-based templates (.md files) and inline prompts.

**Key Features**:
- Packaged default templates (3 templates built-in)
- File-based template resolution with hierarchy
- Inline prompt support
- Template variables: `{content}`, `{context}`
- Unified file structure: `.graphiti/auto-tracking/templates/`

## Acceptance Criteria

### Hardcoded Template Sources
- [ ] Create `prompts.py` module with template constants
- [ ] Define DEFAULT_TOOL_CONTENT_TEMPLATE constant
- [ ] Define DEFAULT_USER_MESSAGES_TEMPLATE constant
- [ ] Define DEFAULT_AGENT_MESSAGES_TEMPLATE constant
- [ ] Templates include clear instructions and template variables
- [ ] Test: All template constants are valid markdown

### Packaged Template Files
- [ ] Create `graphiti_core/session_tracking/prompts/` directory
- [ ] Create `default-tool-content.md` file
- [ ] Create `default-user-messages.md` file
- [ ] Create `default-agent-messages.md` file
- [ ] Package templates with Graphiti distribution
- [ ] Test: Templates load from package at runtime

### Template Resolution
- [ ] Implement `resolve_template_path()` function
- [ ] Resolution order: Project → Global → Built-in → Inline
- [ ] Support absolute paths (use directly)
- [ ] Support relative paths (resolve via hierarchy)
- [ ] Support inline prompts (non-.md strings)
- [ ] Test: Project templates override global
- [ ] Test: Global templates override built-in
- [ ] Test: Built-in used if no custom templates
- [ ] Test: Inline prompts used directly
- [ ] Test: Absolute paths used directly

### MessageSummarizer Integration
- [ ] Update `MessageSummarizer` to use template resolution
- [ ] Replace hardcoded prompts with template loading
- [ ] Substitute template variables (`{content}`, `{context}`)
- [ ] Cache resolved templates (avoid re-reading)
- [ ] Test: Template caching works correctly
- [ ] Test: Template variables substituted

### File Structure Creation
- [ ] Implement `ensure_default_templates_exist()` function
- [ ] Create `~/.graphiti/auto-tracking/templates/` directory
- [ ] Copy default templates from package on first run
- [ ] Skip copy if templates already exist (no overwrite)
- [ ] Call from `initialize_session_tracking()`
- [ ] Test: Templates created on first run
- [ ] Test: No overwrite on subsequent runs

## Implementation Details

### Files to Create

**`graphiti_core/session_tracking/prompts.py`**:

```python
"""Hardcoded template sources for session summarization."""

DEFAULT_TOOL_CONTENT_TEMPLATE = """Summarize this tool result concisely in 1 paragraph.

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

DEFAULT_USER_MESSAGES_TEMPLATE = """Summarize this user message in 1-2 sentences.

**Context**: {context}

**Focus on**:
- What the user is asking for
- Key requirements or constraints
- Context or background provided

**Original message**:
{content}

**Summary** (preserve user intent):
"""

DEFAULT_AGENT_MESSAGES_TEMPLATE = """Summarize this agent response in 1 paragraph.

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

# Template filename mapping
DEFAULT_TEMPLATES = {
    "default-tool-content.md": DEFAULT_TOOL_CONTENT_TEMPLATE,
    "default-user-messages.md": DEFAULT_USER_MESSAGES_TEMPLATE,
    "default-agent-messages.md": DEFAULT_AGENT_MESSAGES_TEMPLATE,
}
```

**`graphiti_core/session_tracking/prompts/default-tool-content.md`**: (Copy from DEFAULT_TOOL_CONTENT_TEMPLATE)

**`graphiti_core/session_tracking/prompts/default-user-messages.md`**: (Copy from DEFAULT_USER_MESSAGES_TEMPLATE)

**`graphiti_core/session_tracking/prompts/default-agent-messages.md`**: (Copy from DEFAULT_AGENT_MESSAGES_TEMPLATE)

### Files to Modify

**`graphiti_core/session_tracking/message_summarizer.py`**:

1. Add template resolution function:
```python
def resolve_template_path(
    template_ref: str,
    project_root: Optional[Path] = None
) -> tuple[str, bool]:
    """Resolve template reference to content and is_inline flag.

    Resolution hierarchy:
    1. Absolute path → use directly
    2. Project template → <project>/.graphiti/auto-tracking/templates/{ref}
    3. Global template → ~/.graphiti/auto-tracking/templates/{ref}
    4. Built-in template → graphiti_core/session_tracking/prompts/{ref}
    5. Inline prompt → use string directly (if not .md extension)

    Returns:
        tuple[str, bool]: (template_content, is_inline)
    """
    # Check if inline prompt (not .md file)
    if not template_ref.endswith('.md'):
        return (template_ref, True)

    # Check absolute path
    if Path(template_ref).is_absolute():
        if Path(template_ref).exists():
            return (Path(template_ref).read_text(), False)
        raise FileNotFoundError(f"Template not found: {template_ref}")

    # Check project template
    if project_root:
        project_template = project_root / ".graphiti" / "auto-tracking" / "templates" / template_ref
        if project_template.exists():
            return (project_template.read_text(), False)

    # Check global template
    global_template = Path.home() / ".graphiti" / "auto-tracking" / "templates" / template_ref
    if global_template.exists():
        return (global_template.read_text(), False)

    # Check built-in template
    if template_ref in DEFAULT_TEMPLATES:
        return (DEFAULT_TEMPLATES[template_ref], False)

    # Template not found
    raise FileNotFoundError(
        f"Template '{template_ref}' not found in hierarchy: "
        f"project > global > built-in"
    )
```

2. Update `MessageSummarizer.__init__()` to cache templates
3. Update summarization methods to use template resolution

**`mcp_server/graphiti_mcp_server.py`**:

1. Add template creation function:
```python
def ensure_default_templates_exist():
    """Ensure default templates exist in global config directory."""
    templates_dir = Path.home() / ".graphiti" / "auto-tracking" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in DEFAULT_TEMPLATES.items():
        template_path = templates_dir / filename
        if not template_path.exists():
            template_path.write_text(content)
            logger.info(f"Created default template: {template_path}")
```

2. Call from `initialize_session_tracking()`:
```python
async def initialize_session_tracking():
    # ... existing code ...

    # Ensure default templates exist
    ensure_default_templates_exist()

    # ... rest of initialization ...
```

### Testing Requirements

**Create**: `tests/session_tracking/test_template_system.py`

Test cases:
1. **Template Resolution Hierarchy**:
   - Project template overrides global
   - Global template overrides built-in
   - Built-in used if no custom templates
   - Inline prompt used if not .md file
   - Absolute path used directly

2. **Template Creation**:
   - Templates created on first run
   - No overwrite on subsequent runs
   - All 3 default templates created

3. **Template Loading**:
   - Templates load from package
   - Templates load from global config
   - Templates load from project
   - Template variables substituted correctly

4. **Error Handling**:
   - Missing template raises FileNotFoundError
   - Invalid template path raises clear error
   - Template read errors logged

## Dependencies

- Story 10 (configuration schema changes) - REQUIRED

## Related Documents

- `.claude/handoff/session-tracking-complete-overhaul-2025-11-18.md` (Section: New Features - Feature 3)
- `.claude/implementation/pluggable-summary-prompts-design.md`

## Cross-Cutting Requirements

See parent sprint `.claude/implementation/CROSS_CUTTING_REQUIREMENTS.md`:
- Platform-agnostic paths: Use pathlib.Path for all file operations
- Error handling: Comprehensive logging for template loading
- Type hints: All functions properly typed
- Testing: >80% coverage with hierarchy tests
- Documentation: Template system documented in user guide
