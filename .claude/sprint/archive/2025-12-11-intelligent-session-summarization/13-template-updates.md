# Story 13: Template Updates

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Update default summarization templates with "1 paragraph or less" wording and activity-aware instructions. This addresses the original user feedback about template specificity.

## Acceptance Criteria

- [ ] (P0) `default-user-messages.md` updated with "1 paragraph or less"
- [ ] (P0) `default-agent-messages.md` updated with "1 paragraph or less"
- [ ] (P1) `default-session-summary.md` created with dynamic extraction placeholder
- [ ] (P1) Templates reference activity profile when available

## Dependencies

None

## Implementation Notes

**Files to modify**:
- `graphiti_core/session_tracking/prompts/default-user-messages.md`
- `graphiti_core/session_tracking/prompts/default-agent-messages.md`

**File to create**:
- `graphiti_core/session_tracking/prompts/default-session-summary.md`

**default-user-messages.md** (updated):
```markdown
Summarize this user message in 1 paragraph or less.

**Context**: {context}

**Focus on**:
- What the user is asking for
- Key requirements or constraints
- Context or background provided

**Original message**:
{content}

**Summary** (preserve user intent, 1 paragraph or less):
```

**default-agent-messages.md** (updated):
```markdown
Summarize this agent response in 1 paragraph or less.

**Context**: {context}

**Focus on**:
- Main explanation or reasoning
- Decisions made or approaches taken
- Important context or caveats
- Follow-up actions planned

**Original response**:
{content}

**Summary** (reasoning and decisions, 1 paragraph or less):
```

**default-session-summary.md** (new):
```markdown
Summarize this coding session into structured format.

**Activity Profile**: {activity_profile}

**Extract based on session activities**:

{dynamic_extraction_instructions}

**Session Content**:
{content}

**Response** (JSON matching EnhancedSessionSummary schema):
```

**Key changes**:
1. "1 paragraph" -> "1 paragraph or less" (explicit length constraint)
2. Activity profile context included when available
3. New session-level template for full session summarization

## Related Stories

None - this is independent template work
