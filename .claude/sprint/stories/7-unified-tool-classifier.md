# Story 7: Unified Tool Classifier

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Create UnifiedToolClassifier that routes MCP tools, bash commands, and native tools to appropriate classifiers. This provides a single entry point for all tool classification needs.

## Acceptance Criteria

- [ ] (P0) `UnifiedToolClassifier` class combining ToolClassifier and BashAnalyzer
- [ ] (P0) `classify_message()` routes based on tool type (bash vs MCP vs native)
- [ ] (P0) `classify_session()` returns tuple of (ActivityVector, list[ToolClassification])
- [ ] (P1) Integration with ActivityDetector for tool-based signals
- [ ] (P1) End-to-end test classifying mixed tool session

## Dependencies

- Story 5: LLM Tool Classification with Caching
- Story 6: Bash Command Analysis

## Implementation Notes

**File to create**: `graphiti_core/session_tracking/unified_classifier.py`

**Routing logic**:
```python
async def classify_message(self, message: dict) -> ToolClassification | BashCommandClassification:
    tool_name = message.get("name", "")
    params = message.get("params", {})

    if tool_name.lower() == "bash":
        command = params.get("command", "")
        return await self.bash_analyzer.classify(command)
    else:
        results = await self.tool_classifier.classify_batch(
            [{"name": tool_name, "params": params}]
        )
        return results[0]
```

**Session classification**:
```python
async def classify_session(self, messages: list[dict]) -> tuple[ActivityVector, list]:
    tool_messages = [m for m in messages if m.get("role") == "tool"]

    classifications = []
    for msg in tool_messages:
        cls = await self.classify_message(msg)
        classifications.append(cls)

    # Aggregate into activity signals
    aggregate = {}
    for cls in classifications:
        for activity, signal in cls.activity_signals.items():
            aggregate[activity] = aggregate.get(activity, 0) + signal

    return ActivityVector.from_signals(aggregate), classifications
```

## Related Stories

- Story 5: LLM Tool Classification with Caching (dependency)
- Story 6: Bash Command Analysis (dependency)
- Story 11: Summarizer Integration (uses this)
