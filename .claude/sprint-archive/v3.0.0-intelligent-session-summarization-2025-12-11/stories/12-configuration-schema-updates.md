# Story 12: Configuration Schema Updates

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Add summarization configuration options to graphiti.config.schema.json and unified_config.py. This enables users to customize extraction threshold, enable/disable specific fields, and configure tool classification cache location.

## Acceptance Criteria

- [ ] (P0) `SummarizationConfig` Pydantic model with fields from spec
- [ ] (P0) JSON schema updated with `summarization` block under `session_tracking`
- [ ] (P0) `extraction_threshold`, `include_decisions`, `include_errors_resolved` configurable
- [ ] (P1) `tool_classification_cache` path configurable
- [ ] (P1) Backward compatible with existing configs (new block optional)

## Dependencies

None

## Implementation Notes

**Files to modify**:
- `graphiti.config.schema.json` - Add SummarizationConfig definition
- `mcp_server/unified_config.py` - Add SummarizationConfig Pydantic model

**SummarizationConfig model**:
```python
class SummarizationConfig(BaseModel):
    """Configuration for intelligent session summarization."""

    template: str | None = Field(
        default=None,
        description="Custom summarization template path. If None, uses dynamic extraction."
    )

    type_detection: Literal["auto", "manual"] = Field(
        default="auto",
        description="Activity detection mode. 'auto' infers from messages, 'manual' requires explicit config."
    )

    extraction_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum priority score to include extraction field"
    )

    include_decisions: bool = Field(
        default=True,
        description="Extract key_decisions (prevents repeated debates)"
    )

    include_errors_resolved: bool = Field(
        default=True,
        description="Extract errors_resolved (debugging continuity)"
    )

    tool_classification_cache: str | None = Field(
        default=None,
        description="Path to tool classification cache. Default: ~/.graphiti/tool_cache.json"
    )
```

**JSON schema addition**:
```json
{
  "session_tracking": {
    "summarization": {
      "template": null,
      "type_detection": "auto",
      "extraction_threshold": 0.3,
      "include_decisions": true,
      "include_errors_resolved": true,
      "tool_classification_cache": null
    }
  }
}
```

**Backward compatibility**:
- New `summarization` block is entirely optional
- If not present, use all defaults
- Existing configs continue to work without changes

## Related Stories

None - this is independent configuration work
