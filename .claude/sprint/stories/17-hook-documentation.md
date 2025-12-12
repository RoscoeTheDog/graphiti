# Story 17: Document Hook Setup in User Guide (ST-H17)

**Status**: unassigned
**Created**: 2025-12-11 22:28
**Priority**: Medium
**Estimate**: S

## Description

Document the Claude Code hook setup process for users, including manual and automatic installation options.

## Acceptance Criteria

- [ ] (P0) Add hook setup section to user documentation
- [ ] (P0) Document manual setup instructions (Section 13.6.2 of spec)
- [ ] (P0) Document automatic setup via setup_claude_code_hooks()
- [ ] (P1) Include troubleshooting for common hook issues
- [ ] (P1) Document hook behavior and expected flow (Section 13.7 of spec)
- [ ] (P2) Add FAQ for hook-related questions

## Dependencies

- Story 15: Setup utilities (to document)
- Story 10: Base documentation structure

## Implementation Notes

- Location: docs/HOOKS.md (NEW) or section in existing docs
- Include JSON snippets for ~/.claude/settings.json
- Reference platform-specific notes (Unix vs Windows)

## Related Stories

- Depends on: Story 10, Story 15
- Enables: User adoption of hook integration
