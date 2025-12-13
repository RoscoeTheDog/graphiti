# Story 11: Summarizer Integration

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Wire ActivityDetector, UnifiedToolClassifier, and dynamic prompts into SessionSummarizer. This is the integration story that brings all components together for end-to-end intelligent summarization.

## Acceptance Criteria

- [ ] (P0) `SessionSummarizer` uses `ActivityDetector` to compute activity vector
- [ ] (P0) `SessionSummarizer` uses dynamic prompt based on activity
- [ ] (P0) Output includes activity_vector in summary
- [ ] (P1) Falls back gracefully if activity detection fails
- [ ] (P1) End-to-end integration test with full session

## Dependencies

- Story 3: Activity Detection from Messages
- Story 7: Unified Tool Classifier
- Story 9: Dynamic Prompt Generation
- Story 10: Enhanced Markdown Rendering

## Implementation Notes

**File to modify**: `graphiti_core/session_tracking/summarizer.py`

**Integration flow**:
```python
class SessionSummarizer:
    def __init__(self, llm_client, tool_classifier=None):
        self.llm_client = llm_client
        self.activity_detector = ActivityDetector(tool_classifier)
        self.prompt_builder = PromptBuilder()

    async def summarize_session(self, messages: list[dict], ...) -> SessionSummary:
        # 1. Detect activity vector
        try:
            activity = await self.activity_detector.detect(messages)
        except Exception:
            activity = ActivityVector()  # Fallback to neutral

        # 2. Build dynamic prompt
        filtered_content = self._filter_messages(messages)
        prompt = self.prompt_builder.build_extraction_prompt(
            activity=activity,
            content=filtered_content,
            threshold=0.3,
        )

        # 3. Extract structured summary
        response = await self.llm_client.generate_structured(
            prompt=prompt,
            response_model=EnhancedSessionSummary,
        )

        # 4. Ensure activity vector is set
        response.activity_vector = activity

        return response
```

**Graceful fallback**:
- If activity detection fails, use neutral ActivityVector (all zeros)
- If tool classification fails, continue without tool signals
- If LLM fails, raise (handled by resilient_indexer)

**End-to-end test scenario**:
```python
messages = [
    {"role": "user", "content": "Fix the authentication bug"},
    {"role": "assistant", "content": "I found the issue in config..."},
    {"role": "tool", "name": "Read", "params": {"file": ".env"}},
    {"role": "tool", "name": "Edit", "params": {"file": ".env"}},
    {"role": "tool", "name": "Bash", "params": {"command": "pytest tests/"}},
]

summary = await summarizer.summarize_session(messages)

assert summary.activity_vector.fixing > 0.5
assert summary.activity_vector.testing > 0.3
assert summary.errors_resolved or summary.completed_tasks
```

## Related Stories

- Story 3: Activity Detection from Messages (dependency)
- Story 7: Unified Tool Classifier (dependency)
- Story 9: Dynamic Prompt Generation (dependency)
- Story 10: Enhanced Markdown Rendering (dependency)
