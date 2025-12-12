# Story 1: Enhanced Session Summary Schema

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Add `key_decisions` (structured with rationale) and `errors_resolved` fields to the session summary schema, and update the summarization prompt to extract these fields. This enables capturing important decisions with their reasoning (preventing repeated debates in future sessions) and structured error resolution records (enabling debugging continuity).

## Acceptance Criteria

- [ ] (P0) `SessionSummarySchema` includes `key_decisions: list[DecisionRecord]` with decision, rationale, alternatives fields
- [ ] (P0) `SessionSummarySchema` includes `errors_resolved: list[ErrorResolution]` with error, root_cause, fix, verification fields
- [ ] (P0) `SUMMARIZATION_PROMPT` updated to extract key_decisions with rationale
- [ ] (P1) `to_markdown()` renders key_decisions and errors_resolved sections
- [ ] (P1) Unit tests verify new fields serialize/deserialize correctly

## Dependencies

None

## Implementation Notes

**Files to modify**:
- `graphiti_core/session_tracking/summarizer.py` - Add DecisionRecord, ErrorResolution models and update SessionSummarySchema

**New models**:
```python
class DecisionRecord(BaseModel):
    decision: str          # "Used RS256 over HS256 for JWT signing"
    rationale: str         # "RS256 is more secure for production"
    alternatives: list[str] | None = None  # ["HS256", "EdDSA"]

class ErrorResolution(BaseModel):
    error: str             # "ImportError: No module named 'foo'"
    root_cause: str        # "Missing dependency in requirements.txt"
    fix: str               # "Added foo==1.2.3 to requirements.txt"
    verification: str      # "Ran tests, all passing"
```

## Related Stories

None - this is a foundational story
