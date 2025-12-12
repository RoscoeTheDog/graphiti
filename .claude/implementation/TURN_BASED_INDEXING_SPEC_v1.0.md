# Turn-Based Indexing with Single-Pass LLM Processing - Specification v1.0

**Version**: 1.0.0
**Status**: Approved for Implementation
**Authors**: Human + Claude Agent
**Date**: 2025-12-12
**Supersedes**: TURN_BASED_INDEXING_SPEC_v0.1.md, SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md

---

## Executive Summary

This specification defines the implementation of **turn-based indexing** with **single-pass LLM processing** via preprocessing prompt injection into Graphiti's existing extraction pipeline.

### Key Decisions from Research

| Research | Finding | Decision |
|----------|---------|----------|
| R1: Turn Boundaries | Role transitions (user→assistant) are natural delimiters | Use role-based detection |
| R2: LLM Injection | `custom_prompt` field exists in upstream Graphiti | Leverage existing field |
| R4: Token Economics | Single-pass saves ~13% tokens (eliminates redundant summarization pass) | Proceed with single-pass |

### Architecture Summary

```
Turn Complete (user→assistant pair)
    ↓
Filter noise programmatically (no LLM)
    ↓
Build context with preprocessing_prompt
    ↓
Graphiti add_episode() with injected custom_prompt
    ↓
Single LLM pass: preprocessing + entity extraction
    ↓
Graph updated
```

---

## Research Findings

### R2: Graphiti LLM Injection Points (COMPLETE)

**Finding**: The `custom_prompt` field is an **upstream Graphiti feature** (not our addition).

| Attribute | Value |
|-----------|-------|
| Introduced | Commit `eba9f40` (PR #212) |
| Author | Preston Rasmussen (Zep team) |
| Date | November 13, 2024 |
| Purpose | Support reflexion iterations |

**Current Usage**: Only populated during reflexion (multi-pass retry for missed entities).

**Injection Points**:
- `graphiti_core/prompts/extract_nodes.py:127` - `extract_message()`
- `graphiti_core/prompts/extract_nodes.py:151` - `extract_json()`
- `graphiti_core/prompts/extract_nodes.py:185` - `extract_text()`
- `graphiti_core/prompts/extract_edges.py:113` - `edge()`

**Mechanism**:
```python
# In node_operations.py
custom_prompt = ''  # Empty on first pass
context = {
    'episode_content': episode.content,
    'custom_prompt': custom_prompt,  # ← INJECTION POINT
    ...
}

# Reflexion (if enabled) concatenates hints:
custom_prompt = 'Make sure that the following entities are extracted: ...'
```

### R1: Turn Boundary Detection (COMPLETE)

**Finding**: Turn boundaries are implicitly defined by role transitions in existing data structures.

- `SessionMessage.role: MessageRole` (USER | ASSISTANT | SYSTEM)
- Role change from `user` to `assistant` = one turn-pair
- `JSONLParser` already processes messages with role tracking

**Detection Strategy**: Process turn-pairs retrospectively when next user message arrives (confirms previous turn complete).

### R4: Token Economics (COMPLETE)

**Dual-Pass (Current)**:
```
Pass 1 (Summarize):     ~4.5k tokens (content + prompt + response)
Pass 2 (Graphiti):      ~30k tokens (content re-read + extraction)
Total:                  ~34.5k tokens
```

**Single-Pass (Proposed)**:
```
Single Pass (Graphiti + preprocessing): ~30k tokens
Savings:                                ~4.5k tokens (13%)
```

**Turn-based vs Session-based**: Turn-based has higher total calls but provides real-time indexing and reliable turn delimiters. Token cost is a tradeoff for reliability.

---

## Implementation Design

### 1. Configuration Schema

**New Config Section**: `extraction` in `GraphitiConfig`

```python
# graphiti_core/extraction_config.py (NEW FILE)

from typing import Literal, Optional, Union
from pydantic import BaseModel, Field


class ExtractionConfig(BaseModel):
    """Configuration for LLM extraction behavior.

    Controls preprocessing prompt injection into Graphiti's entity/relationship
    extraction pipeline. Follows the bool | str pattern from FilterConfig.

    Preprocessing values:
    - None: No preprocessing (default Graphiti behavior)
    - "template.md": Load template from hierarchy (project > global > built-in)
    - "inline prompt...": Use string as direct preprocessing instructions

    Examples:
        # Default (no preprocessing)
        config = ExtractionConfig()

        # Built-in session turn template
        config = ExtractionConfig(
            preprocessing_prompt="default-session-turn.md"
        )

        # Inline custom instructions
        config = ExtractionConfig(
            preprocessing_prompt="Focus on extracting error patterns and their resolutions."
        )
    """

    preprocessing_prompt: Optional[Union[bool, str]] = Field(
        default="default-session-turn.md",
        description=(
            "Preprocessing instructions injected into Graphiti extraction prompts. "
            "None or False disables preprocessing. "
            '"template.md" loads from template hierarchy. '
            '"inline prompt..." uses string directly.'
        )
    )

    preprocessing_mode: Literal["prepend", "append"] = Field(
        default="prepend",
        description=(
            "How to combine preprocessing with reflexion prompts. "
            "'prepend': preprocessing before reflexion hints (recommended). "
            "'append': preprocessing after reflexion hints."
        )
    )

    def is_enabled(self) -> bool:
        """Check if preprocessing is enabled."""
        return self.preprocessing_prompt is not None and self.preprocessing_prompt is not False

    def resolve_prompt(self, template_resolver: "TemplateResolver") -> str | None:
        """Resolve preprocessing_prompt to actual prompt string.

        Args:
            template_resolver: Resolver for loading template files

        Returns:
            Resolved prompt string, or None if disabled
        """
        if not self.is_enabled():
            return None

        if isinstance(self.preprocessing_prompt, str):
            if self.preprocessing_prompt.endswith(".md"):
                # Template file - load from hierarchy
                return template_resolver.load(self.preprocessing_prompt)
            else:
                # Inline prompt
                return self.preprocessing_prompt

        return None
```

**Integration with GraphitiConfig**:

```python
# In mcp_server/unified_config.py

from graphiti_core.extraction_config import ExtractionConfig

class GraphitiConfig(BaseModel):
    # ... existing fields ...
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
```

### 2. Default Template

**File**: `~/.graphiti/templates/default-session-turn.md`

```markdown
## Session Turn Preprocessing

When extracting entities and relationships from this content, apply these guidelines:

### Content Prioritization

**HIGH PRIORITY - Always Extract**:
- User intent and explicit requests
- Agent decisions with stated rationale
- Error messages and their resolutions
- Configuration changes and their reasons
- Files created, modified, or referenced
- Tools/commands used and their outcomes

**MEDIUM PRIORITY - Extract if Significant**:
- Code patterns and architectural decisions
- Dependencies and version information
- Test results and coverage data
- Performance observations

**LOW PRIORITY - Summarize or Skip**:
- Verbose tool output (extract outcome only)
- Stack traces (extract error type and message only)
- Large code blocks (extract purpose and key functions only)
- Repetitive status messages

### Entity Classification Hints

For agentic coding sessions, prioritize these entity types:
- **File**: Source files, configs, documentation
- **Tool**: CLI commands, MCP tools, IDE actions
- **Error**: Error types, exceptions, failures
- **Decision**: Architectural choices, tradeoffs made
- **Concept**: Patterns, techniques, libraries referenced

### Relationship Focus

Extract relationships that capture:
- What files were modified and why
- What tools were used for what purpose
- How errors were diagnosed and resolved
- Dependencies between components
```

### 3. GraphitiClients Extension

**Modification**: Add preprocessing_prompt to GraphitiClients dataclass

```python
# In graphiti_core/graphiti.py

@dataclass
class GraphitiClients:
    driver: GraphDriver
    llm_client: LLMClient
    embedder: EmbedderClient
    cross_encoder: CrossEncoderClient
    tracer: Tracer
    preprocessing_prompt: str | None = None  # NEW
    preprocessing_mode: str = "prepend"       # NEW
```

**Graphiti.__init__ modification**:

```python
def __init__(
    self,
    # ... existing params ...
    preprocessing_prompt: str | None = None,      # NEW
    preprocessing_mode: str = "prepend",          # NEW
):
    # ... existing initialization ...

    self.clients = GraphitiClients(
        driver=self.driver,
        llm_client=self.llm_client,
        embedder=self.embedder,
        cross_encoder=self.cross_encoder,
        tracer=self.tracer,
        preprocessing_prompt=preprocessing_prompt,  # NEW
        preprocessing_mode=preprocessing_mode,      # NEW
    )
```

### 4. Node Operations Modification

**File**: `graphiti_core/utils/maintenance/node_operations.py`

```python
async def extract_nodes(
    clients: GraphitiClients,
    episode: EpisodicNode,
    previous_episodes: list[EpisodicNode],
    entity_types: dict[str, type[BaseModel]] | None = None,
    excluded_entity_types: list[str] | None = None,
) -> list[EntityNode]:
    """Extract entity nodes from an episode using LLM.

    Now supports preprocessing prompt injection via clients.preprocessing_prompt.
    Preprocessing is concatenated with reflexion prompts (not replaced).
    """
    start = time()
    llm_client = clients.llm_client
    llm_response = {}

    # Initialize with preprocessing prompt (if configured)
    preprocessing = clients.preprocessing_prompt or ''
    custom_prompt = preprocessing

    entities_missed = True
    reflexion_iterations = 0
    error_classifier = LLMErrorClassifier()

    # ... entity_types_context building (unchanged) ...

    context = {
        'episode_content': episode.content,
        'episode_timestamp': episode.valid_at.isoformat(),
        'previous_episodes': [ep.content for ep in previous_episodes],
        'custom_prompt': custom_prompt,  # Now includes preprocessing
        'entity_types': entity_types_context,
        'source_description': episode.source_description,
    }

    try:
        while entities_missed and reflexion_iterations <= MAX_REFLEXION_ITERATIONS:
            # ... extraction logic (unchanged) ...

            reflexion_iterations += 1
            if reflexion_iterations < MAX_REFLEXION_ITERATIONS:
                missing_entities = await extract_nodes_reflexion(...)
                entities_missed = len(missing_entities) != 0

                if entities_missed:
                    # Build reflexion hint
                    reflexion_hint = 'Make sure that the following entities are extracted: '
                    for entity in missing_entities:
                        reflexion_hint += f'\n{entity},'

                    # Concatenate based on mode (prepend or append)
                    if clients.preprocessing_mode == "prepend":
                        context['custom_prompt'] = preprocessing + '\n\n' + reflexion_hint if preprocessing else reflexion_hint
                    else:  # append
                        context['custom_prompt'] = reflexion_hint + '\n\n' + preprocessing if preprocessing else reflexion_hint

    # ... rest unchanged ...
```

### 5. Edge Operations Modification

**File**: `graphiti_core/utils/maintenance/edge_operations.py`

Same pattern as node_operations:

```python
async def extract_edges(
    clients: GraphitiClients,
    episode: EpisodicNode,
    nodes: list[EntityNode],
    previous_episodes: list[EpisodicNode],
    edge_type_map: dict[tuple[str, str], list[str]],
    group_id: str = '',
    edge_types: dict[str, type[BaseModel]] | None = None,
) -> list[EntityEdge]:
    """Extract entity edges from an episode using LLM.

    Now supports preprocessing prompt injection via clients.preprocessing_prompt.
    """
    # ... setup ...

    # Initialize with preprocessing
    preprocessing = clients.preprocessing_prompt or ''

    context = {
        'episode_content': episode.content,
        'nodes': [...],
        'previous_episodes': [...],
        'reference_time': episode.valid_at,
        'edge_types': edge_types_context,
        'custom_prompt': preprocessing,  # Now includes preprocessing
    }

    facts_missed = True
    reflexion_iterations = 0

    try:
        while facts_missed and reflexion_iterations <= MAX_REFLEXION_ITERATIONS:
            # ... extraction logic ...

            reflexion_iterations += 1
            if reflexion_iterations < MAX_REFLEXION_ITERATIONS:
                # ... check for missed facts ...

                if facts_missed:
                    reflexion_hint = 'The following facts were missed in a previous extraction: '
                    for fact in missing_facts:
                        reflexion_hint += f'\n{fact},'

                    # Concatenate based on mode
                    if clients.preprocessing_mode == "prepend":
                        context['custom_prompt'] = preprocessing + '\n\n' + reflexion_hint if preprocessing else reflexion_hint
                    else:
                        context['custom_prompt'] = reflexion_hint + '\n\n' + preprocessing if preprocessing else reflexion_hint

    # ... rest unchanged ...
```

### 6. MCP Server Integration

**File**: `mcp_server/graphiti_mcp_server.py`

```python
async def initialize_graphiti():
    """Initialize Graphiti client with preprocessing config."""
    global graphiti_client

    # Load unified config
    config = get_config()

    # Resolve preprocessing prompt from config
    preprocessing_prompt = None
    if config.extraction.is_enabled():
        template_resolver = TemplateResolver()
        preprocessing_prompt = config.extraction.resolve_prompt(template_resolver)

    graphiti_client = Graphiti(
        uri=config.database.neo4j.uri,
        user=config.database.neo4j.user,
        password=config.database.neo4j.password,
        llm_client=llm_client,
        embedder=embedder,
        preprocessing_prompt=preprocessing_prompt,              # NEW
        preprocessing_mode=config.extraction.preprocessing_mode, # NEW
    )
```

---

## Configuration Examples

### Default Configuration (recommended)

```json
{
  "extraction": {
    "preprocessing_prompt": "default-session-turn.md",
    "preprocessing_mode": "prepend"
  }
}
```

### No Preprocessing (upstream Graphiti behavior)

```json
{
  "extraction": {
    "preprocessing_prompt": null
  }
}
```

### Custom Template

```json
{
  "extraction": {
    "preprocessing_prompt": "my-custom-extraction.md",
    "preprocessing_mode": "prepend"
  }
}
```

### Inline Prompt

```json
{
  "extraction": {
    "preprocessing_prompt": "Focus on extracting: 1) Error patterns 2) File modifications 3) Tool usage sequences. Ignore verbose output.",
    "preprocessing_mode": "prepend"
  }
}
```

---

## Template Resolution Hierarchy

Templates are resolved in order:
1. **Project**: `./.graphiti/templates/{template.md}`
2. **Global**: `~/.graphiti/templates/{template.md}`
3. **Built-in**: Package default templates

If template not found at any level, falls back to no preprocessing with warning.

---

## Implementation Plan

### Phase 1: Core Infrastructure (Stories 1-3)

| Story | Description | Files Modified |
|-------|-------------|----------------|
| ST-1 | Create ExtractionConfig schema | `graphiti_core/extraction_config.py` (new) |
| ST-2 | Extend GraphitiClients with preprocessing fields | `graphiti_core/graphiti.py` |
| ST-3 | Create default-session-turn.md template | `~/.graphiti/templates/` |

### Phase 2: Injection Implementation (Stories 4-5)

| Story | Description | Files Modified |
|-------|-------------|----------------|
| ST-4 | Modify node_operations.py for preprocessing | `graphiti_core/utils/maintenance/node_operations.py` |
| ST-5 | Modify edge_operations.py for preprocessing | `graphiti_core/utils/maintenance/edge_operations.py` |

### Phase 3: Integration (Stories 6-7)

| Story | Description | Files Modified |
|-------|-------------|----------------|
| ST-6 | Add extraction config to unified_config.py | `mcp_server/unified_config.py` |
| ST-7 | Wire preprocessing in MCP server initialization | `mcp_server/graphiti_mcp_server.py` |

### Phase 4: Template System (Stories 8-9)

| Story | Description | Files Modified |
|-------|-------------|----------------|
| ST-8 | Implement TemplateResolver with hierarchy | `graphiti_core/template_resolver.py` (new) |
| ST-9 | Add template validation and error handling | `mcp_server/config_validator.py` |

### Phase 5: Testing & Documentation (Stories 10-11)

| Story | Description | Files Modified |
|-------|-------------|----------------|
| ST-10 | Unit tests for preprocessing injection | `tests/` |
| ST-11 | Update CONFIGURATION.md with extraction section | `CONFIGURATION.md` |

---

## Backward Compatibility

- **Default behavior preserved**: `preprocessing_prompt: null` gives upstream Graphiti behavior
- **Reflexion unchanged**: Preprocessing concatenates with (not replaces) reflexion hints
- **Existing data unaffected**: Only affects new episode processing
- **Config optional**: Missing `extraction` section uses defaults

---

## Migration Notes

No migration required. New config section is additive with sensible defaults.

---

## Open Questions (Deferred)

1. **Turn-based watcher**: Separate spec for file watcher turn detection
2. **Template marketplace**: Community templates for different use cases
3. **Per-episode override**: Allow preprocessing_prompt per add_episode call

---

## References

- [Graphiti PR #212](https://github.com/getzep/graphiti/pull/212) - Reflexion feature (custom_prompt origin)
- TURN_BASED_INDEXING_SPEC_v0.1.md - Initial research draft
- SESSION_TRACKING_HYBRID_CLOSE_SPEC_v1.0.md - Previous approach (superseded)

---

**Status**: Approved for Implementation

*Sprint stories to be generated from this spec.*
