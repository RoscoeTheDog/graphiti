# Story 6: Bash Command Analysis

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Implement specialized analysis for bash commands that parses command structure and classifies intent. This enables understanding arbitrary CLI tools, scripts, and installed software without hard-coding.

## Acceptance Criteria

- [ ] (P0) `BashCommandClassification` model with base_command, subcommand, flags, targets
- [ ] (P0) `BashAnalyzer.classify()` parses and classifies bash commands
- [ ] (P0) Heuristic matching for common commands (git, npm, pytest, docker, pip, cargo)
- [ ] (P1) LLM fallback for unknown commands
- [ ] (P1) Unit tests for command parsing and classification

## Dependencies

- Story 4: Tool Classification Heuristics

## Implementation Notes

**File to create**: `graphiti_core/session_tracking/bash_analyzer.py`

**BashCommandClassification model**:
```python
class BashCommandClassification(BaseModel):
    raw_command: str
    base_command: str       # "pytest", "git", "npm"
    subcommand: str | None  # "install", "commit", None
    flags: list[str]        # ["-v", "--cov=src"]
    targets: list[str]      # ["tests/"]
    intent: ToolIntent
    domain: ToolDomain
    confidence: float
    reasoning: str
    activity_signals: dict[str, float]
```

**Common command heuristics**:
- `git *`: VERSION_CONTROL domain
- `npm/yarn/pnpm install`: CONFIGURE intent, PACKAGE domain
- `pytest/jest/mocha`: VALIDATE intent, TESTING domain
- `docker *`: PROCESS domain
- `pip/uv install`: CONFIGURE intent, PACKAGE domain

**LLM prompt for unknown commands**:
```
Analyze this bash command and classify its intent.

Command: {command}

Determine:
1. Base command (primary executable)
2. Subcommand (if applicable)
3. Intent and Domain
4. Activity signals
```

## Related Stories

- Story 4: Tool Classification Heuristics (dependency)
- Story 7: Unified Tool Classifier (uses this)
