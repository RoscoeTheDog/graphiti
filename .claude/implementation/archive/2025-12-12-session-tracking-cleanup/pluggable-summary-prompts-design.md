# Pluggable Summary Prompts Design

**Purpose**: Make summary definitions configurable via markdown templates, allowing users to customize summarization behavior for different message types.

---

## Current Implementation Issues

**Hardcoded prompt** (line 112-114 in `message_summarizer.py`):
```python
prompt = (
    f"Summarize this message{context_hint} concisely in 1-2 sentences, "
    f"preserving key intent and context:\n\n{content}"
)
```

**Problems**:
- Fixed "1-2 sentences" constraint (too restrictive)
- No user control over summary style/length
- Cannot differentiate between tool results vs user/agent messages
- No way to tune without code changes

---

## Proposed Solution: Template-Based Prompts

### Configuration Schema Extension

**Add to `SessionTrackingConfig`**:
```python
class SessionTrackingConfig(BaseModel):
    # ... existing fields ...
    
    summary_prompts: SummaryPromptsConfig = Field(
        default_factory=SummaryPromptsConfig,
        description="Customizable prompts for content summarization"
    )
```

**New `SummaryPromptsConfig` class**:
```python
class SummaryPromptsConfig(BaseModel):
    """Customizable prompts for different message types.
    
    Supports both inline strings and .md file paths for flexibility.
    Variables available in templates: {content}, {context}, {max_chars}
    """
    
    tool_results: str = Field(
        default="default",
        description=(
            "Prompt for summarizing tool results. "
            "Use 'default' for built-in, or path to .md file, or inline prompt string."
        )
    )
    
    user_messages: str = Field(
        default="default",
        description=(
            "Prompt for summarizing user messages. "
            "Use 'default' for built-in, or path to .md file, or inline prompt string."
        )
    )
    
    agent_messages: str = Field(
        default="default",
        description=(
            "Prompt for summarizing agent responses. "
            "Use 'default' for built-in, or path to .md file, or inline prompt string."
        )
    )
    
    max_summary_chars: int = Field(
        default=500,
        description=(
            "Maximum characters for summaries (soft limit for LLM guidance). "
            "Default: 500 (approximately 1 large paragraph)"
        )
    )
```

---

## Template System

### Template Variables
Templates can use these placeholders:
- `{content}` - The actual message/tool result content
- `{context}` - Context hint (e.g., "user message", "agent response", "tool: Read")
- `{max_chars}` - Maximum character limit from config

### Template Locations

**Built-in templates** (packaged with Graphiti):
```
graphiti_core/session_tracking/prompts/
├── tool_results.md
├── user_messages.md
└── agent_messages.md
```

**User templates** (optional overrides):
```
~/.graphiti/prompts/
├── tool_results.md
├── user_messages.md
└── agent_messages.md
```

**Project-specific** (highest priority):
```
/path/to/project/.graphiti/prompts/
├── tool_results.md
├── user_messages.md
└── agent_messages.md
```

### Template Resolution Logic
```python
def resolve_prompt_template(template_value: str, message_type: str) -> str:
    """Resolve template from config value.
    
    Args:
        template_value: Config value ("default", path, or inline prompt)
        message_type: "tool_results", "user_messages", or "agent_messages"
    
    Returns:
        Resolved prompt template string
    
    Resolution order:
        1. If "default" -> load from built-in templates
        2. If path exists -> load from file
        3. Otherwise -> treat as inline prompt string
    """
    if template_value == "default":
        # Load built-in template
        builtin_path = Path(__file__).parent / "prompts" / f"{message_type}.md"
        return builtin_path.read_text()
    
    # Try as file path (absolute or relative to ~/.graphiti/)
    path = Path(template_value)
    if not path.is_absolute():
        path = Path.home() / ".graphiti" / "prompts" / template_value
    
    if path.exists():
        return path.read_text()
    
    # Treat as inline prompt string
    return template_value
```

---

## Default Prompt Templates

### `tool_results.md` (Default)
```markdown
Summarize this tool result concisely in 1 paragraph (max {max_chars} characters).

**Context**: {context}

**Goal**: Extract the key information that would be useful for future sessions. Focus on:
- What operation was performed
- Key findings or outputs
- Any errors or warnings
- Relevant file paths, function names, or data values

**Original content**:
{content}

**Summary** (1 paragraph, focus on actionable information):
```

### `user_messages.md` (Default)
```markdown
Summarize this user message in 1-2 sentences (max {max_chars} characters).

**Context**: {context}

**Goal**: Preserve the user's intent and request. Focus on:
- What the user is asking for
- Key requirements or constraints mentioned
- Context or background provided

**Original message**:
{content}

**Summary** (preserve user intent clearly):
```

### `agent_messages.md` (Default)
```markdown
Summarize this agent response in 1 paragraph (max {max_chars} characters).

**Context**: {context}

**Goal**: Capture the agent's key explanations, decisions, and actions. Focus on:
- Main explanation or reasoning provided
- Decisions made or approaches taken
- Important context or caveats mentioned
- Any follow-up actions planned

**Original response**:
{content}

**Summary** (1 paragraph, focus on reasoning and decisions):
```

---

## Updated Configuration Examples

### Default Configuration (Auto-generated)
```json
{
  "session_tracking": {
    "filter": {
      "tool_content": "summary",
      "user_messages": "full",
      "agent_messages": "full"
    },
    "summary_prompts": {
      "tool_results": "default",
      "user_messages": "default",
      "agent_messages": "default",
      "max_summary_chars": 500
    }
  }
}
```

### Custom Inline Prompt
```json
{
  "session_tracking": {
    "summary_prompts": {
      "tool_results": "Briefly describe what this tool did and what it found (2-3 sentences max): {content}",
      "max_summary_chars": 300
    }
  }
}
```

### Custom Template File (Absolute Path)
```json
{
  "session_tracking": {
    "summary_prompts": {
      "tool_results": "/home/user/my-project/.graphiti/prompts/custom_tool_summary.md"
    }
  }
}
```

### Custom Template File (Relative to ~/.graphiti/)
```json
{
  "session_tracking": {
    "summary_prompts": {
      "tool_results": "tool_results.md",
      "user_messages": "user_messages.md"
    }
  }
}
```

---

## Implementation Changes

### 1. Update `MessageSummarizer` class

**New initialization**:
```python
class MessageSummarizer:
    def __init__(
        self,
        llm_client: LLMClient,
        max_length: int = 500,  # CHANGED: 200 -> 500
        model: str = "gpt-4o-mini",
        prompt_templates: Optional[SummaryPromptsConfig] = None,  # NEW
    ):
        self.llm_client = llm_client
        self.max_length = max_length
        self.model = model
        self.prompt_templates = prompt_templates or SummaryPromptsConfig()
        self.cache: dict[str, str] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Load and compile templates
        self._load_templates()
    
    def _load_templates(self):
        """Load prompt templates from config."""
        self.tool_results_prompt = self._resolve_template(
            self.prompt_templates.tool_results, "tool_results"
        )
        self.user_messages_prompt = self._resolve_template(
            self.prompt_templates.user_messages, "user_messages"
        )
        self.agent_messages_prompt = self._resolve_template(
            self.prompt_templates.agent_messages, "agent_messages"
        )
    
    def _resolve_template(self, template_value: str, message_type: str) -> str:
        """Resolve template from config value (implementation above)."""
        # ... (implementation from Template Resolution Logic section)
    
    def _get_prompt_for_context(self, context: Optional[str]) -> str:
        """Get appropriate prompt template based on context.
        
        Args:
            context: Message context (e.g., "user message", "tool: Read")
        
        Returns:
            Appropriate prompt template string
        """
        if context and context.startswith("tool:"):
            return self.tool_results_prompt
        elif context == "user message":
            return self.user_messages_prompt
        elif context == "agent response":
            return self.agent_messages_prompt
        else:
            # Default to tool results template
            return self.tool_results_prompt
```

**Updated `summarize()` method**:
```python
async def summarize(self, content: str, context: Optional[str] = None) -> str:
    """Summarize message content using LLM with context-aware templates."""
    
    # Check cache first
    cache_key = self._generate_cache_key(content)
    if cache_key in self.cache:
        self.cache_hits += 1
        return self.cache[cache_key]
    
    self.cache_misses += 1
    
    # Get appropriate prompt template
    prompt_template = self._get_prompt_for_context(context)
    
    # Fill in template variables
    prompt = prompt_template.format(
        content=content,
        context=context or "message",
        max_chars=self.prompt_templates.max_summary_chars
    )
    
    try:
        # Call LLM
        messages = [{"role": "user", "content": prompt}]
        response = await self.llm_client.generate_response(messages=messages)
        summary = response.strip()
        
        # Truncate if needed (hard limit)
        max_len = self.prompt_templates.max_summary_chars
        if len(summary) > max_len:
            summary = summary[:max_len - 3] + "..."
        
        # Cache result
        self.cache[cache_key] = summary
        
        # Log statistics
        reduction = (1 - len(summary) / len(content)) * 100 if len(content) > 0 else 0
        logger.info(
            f"Summarized {context or 'content'}: {len(content)} chars → {len(summary)} chars "
            f"({reduction:.1f}% reduction)"
        )
        
        return summary
    
    except Exception as e:
        logger.error(f"Failed to summarize content: {e}", exc_info=True)
        raise
```

---

### 2. Update Configuration Auto-Generation

**Add to `ensure_global_config_exists()`**:
```python
default_config = {
    # ... existing fields ...
    
    "session_tracking": {
        # ... existing fields ...
        
        "summary_prompts": {
            "_comment": "Customizable prompts for content summarization",
            
            "tool_results": "default",
            "_tool_results_help": "default (built-in) | path/to/prompt.md | inline prompt string",
            
            "user_messages": "default",
            "_user_messages_help": "default (built-in) | path/to/prompt.md | inline prompt string",
            
            "agent_messages": "default",
            "_agent_messages_help": "default (built-in) | path/to/prompt.md | inline prompt string",
            
            "max_summary_chars": 500,
            "_max_summary_chars_help": "Maximum characters per summary (soft limit, ~1 paragraph)"
        }
    }
}
```

---

### 3. Create Default Prompt Templates

**File structure**:
```
graphiti_core/session_tracking/prompts/
├── __init__.py
├── tool_results.md
├── user_messages.md
└── agent_messages.md
```

**Include in package** (`pyproject.toml` or `setup.py`):
```toml
[tool.setuptools.package-data]
graphiti_core = ["session_tracking/prompts/*.md"]
```

---

## User Customization Examples

### Example 1: Shorter Tool Summaries
**~/.graphiti/prompts/tool_results.md**:
```markdown
Describe what this tool did in 1-2 sentences (max 200 chars):

{content}

Summary:
```

**Config**:
```json
{
  "summary_prompts": {
    "tool_results": "tool_results.md",
    "max_summary_chars": 200
  }
}
```

---

### Example 2: Detailed Agent Reasoning
**~/.graphiti/prompts/agent_messages.md**:
```markdown
Summarize this agent response in 2-3 paragraphs (max 800 characters).

**Focus areas**:
1. Main reasoning and decision-making process
2. Key technical details and implementation choices
3. Any trade-offs, caveats, or follow-up items mentioned

**Original response**:
{content}

**Detailed summary** (preserve technical depth):
```

**Config**:
```json
{
  "summary_prompts": {
    "agent_messages": "agent_messages.md",
    "max_summary_chars": 800
  }
}
```

---

### Example 3: Code-Focused Tool Summaries
**Project-specific**: `/path/to/project/.graphiti/prompts/tool_results.md`
```markdown
Extract key code information from this tool result (max {max_chars} chars):

**Tool**: {context}

**Focus on**:
- Function/class names mentioned
- File paths modified or read
- Error messages or warnings
- Return values or key data

**Content**:
{content}

**Code-focused summary** (technical details only):
```

---

## Migration Strategy

### Backward Compatibility
- **Default behavior**: `"default"` uses built-in templates → no breaking changes
- **Old configs**: Missing `summary_prompts` field → falls back to defaults
- **Existing users**: No action required, behavior unchanged

### New Users
- Auto-generated config includes `summary_prompts` section with defaults
- Built-in templates ship with package (no external files needed)
- Documentation shows customization examples

---

## Benefits

1. **Flexibility**: Users control summary length/style without code changes
2. **Context-aware**: Different prompts for tools vs messages
3. **Paragraph summaries**: Default 500 chars ≈ 1 large paragraph (vs 1-2 sentences)
4. **Iterative tuning**: Users can refine prompts based on results
5. **Project-specific**: Teams can standardize on custom prompts
6. **No breaking changes**: Defaults preserve existing behavior

---

## Testing Requirements

### Unit Tests
1. Test template resolution (default, file path, inline)
2. Test prompt variable substitution ({content}, {context}, {max_chars})
3. Test fallback behavior (file not found → treat as inline)
4. Test context detection (tool vs user vs agent)

### Integration Tests
1. Test custom template file loading
2. Test template caching and reloading
3. Test summary length limits (soft + hard)
4. Test different prompt styles produce valid summaries

---

## Open Questions

1. **Template caching**: Should templates be cached or reloaded on each call?
   - **Recommendation**: Cache on initialization, reload only if config changes

2. **Template validation**: Should we validate template syntax on load?
   - **Recommendation**: Yes - check for required variables ({content})

3. **Error handling**: What if template file is invalid/corrupt?
   - **Recommendation**: Log error + fall back to built-in default

4. **Template versioning**: Should templates have version markers?
   - **Recommendation**: Not in v1.0, defer to v1.1 if needed

---

## Implementation Checklist

- [ ] Create `SummaryPromptsConfig` class in `unified_config.py`
- [ ] Add `summary_prompts` field to `SessionTrackingConfig`
- [ ] Create `graphiti_core/session_tracking/prompts/` directory
- [ ] Write default prompt templates (tool_results.md, user_messages.md, agent_messages.md)
- [ ] Update `MessageSummarizer` class with template support
- [ ] Implement template resolution logic (`_resolve_template()`)
- [ ] Update auto-generated config to include `summary_prompts`
- [ ] Update configuration documentation
- [ ] Write unit tests for template system
- [ ] Write integration tests for custom prompts
- [ ] Update user guide with customization examples

---

**Design Status**: Ready for implementation after team review
**Default Change**: `tool_content: "summary"` with 500-char paragraph-style summaries
