# Story 9: Dynamic Prompt Generation

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Build extraction prompts dynamically based on activity vector, including only high-priority fields. This reduces token usage by omitting irrelevant extraction instructions and focuses LLM attention on what matters.

## Acceptance Criteria

- [ ] (P0) `build_extraction_prompt(activity, content, threshold) -> str` function
- [ ] (P0) Prompt includes field-specific instructions ordered by priority
- [ ] (P0) Prompt includes activity profile context for LLM
- [ ] (P1) Template integration point for custom override
- [ ] (P1) Unit tests verify prompt structure for different activity profiles

## Dependencies

- Story 8: Extraction Priority Algorithm

## Implementation Notes

**File to create**: `graphiti_core/session_tracking/prompt_builder.py`

**Prompt structure**:
```
Summarize this session into a structured format.

**Session Activity Profile**: fixing (0.8), configuring (0.7), testing (0.5)

Extract the following information (in order of importance):

1. **errors_resolved** (priority: 0.92): For each error: what was it, root cause, how fixed, verified?
2. **config_changes** (priority: 0.78): List config file changes with before/after values
3. **completed_tasks** (priority: 0.71): List specific tasks that were accomplished
4. **test_results** (priority: 0.65): Summarize test execution results and failures
...

## Session Content

{content}

## Response Format
Respond with a JSON object matching the EnhancedSessionSummary schema.
```

**Field instructions**:
```python
FIELD_INSTRUCTIONS = {
    "completed_tasks": "List specific tasks that were accomplished",
    "key_decisions": "Capture decisions made WITH rationale (why this choice?)",
    "errors_resolved": "For each error: what was it, root cause, how fixed, verified?",
    "config_changes": "List config file changes with before/after values",
    "test_results": "Summarize test execution results and failures",
    "discoveries": "Key insights or learnings from exploration",
    # ...
}
```

## Related Stories

- Story 8: Extraction Priority Algorithm (dependency)
- Story 11: Summarizer Integration (uses this)
