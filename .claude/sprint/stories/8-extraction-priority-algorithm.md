# Story 8: Extraction Priority Algorithm

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Implement priority-weighted extraction that determines which fields to include based on activity vector intensity. This ensures debugging sessions prioritize error resolution while exploration sessions prioritize discoveries.

## Acceptance Criteria

- [ ] (P0) `EXTRACTION_AFFINITIES` mapping fields to activity dimension weights
- [ ] (P0) `compute_extraction_priority(field, activity) -> float` function
- [ ] (P0) `get_extraction_fields(activity, threshold) -> list[str]` function
- [ ] (P1) Unit tests verifying priorities for debugging session, exploration session
- [ ] (P1) Threshold filtering works correctly (default 0.3)

## Dependencies

- Story 2: Activity Vector Model

## Implementation Notes

**File to create**: `graphiti_core/session_tracking/extraction_priority.py`

**Field affinities** (field -> {dimension: weight}):
```python
EXTRACTION_AFFINITIES = {
    "completed_tasks": {
        "building": 1.0, "fixing": 0.8, "configuring": 0.7,
        "refactoring": 0.9, "testing": 0.6
    },
    "key_decisions": {
        "building": 1.0, "configuring": 0.9, "refactoring": 0.8,
        "fixing": 0.6, "exploring": 0.5
    },
    "errors_resolved": {
        "fixing": 1.0, "configuring": 0.7, "testing": 0.5
    },
    "discoveries": {
        "exploring": 1.0, "reviewing": 0.8, "documenting": 0.5
    },
    "config_changes": {
        "configuring": 1.0, "fixing": 0.4
    },
    "test_results": {
        "testing": 1.0, "fixing": 0.7, "building": 0.6
    },
    # ... etc
}
```

**Priority computation**:
```python
def compute_extraction_priority(field: str, activity: ActivityVector) -> float:
    affinities = EXTRACTION_AFFINITIES.get(field, {})
    priority = sum(
        getattr(activity, dim) * affinity
        for dim, affinity in affinities.items()
    )
    return priority / sum(affinities.values()) if affinities else 0.5
```

**Example**:
- Debugging session (fixing=0.9, exploring=0.4):
  - errors_resolved priority: ~0.9 (high)
  - discoveries priority: ~0.4 (low)
- Exploration session (exploring=0.9, reviewing=0.7):
  - discoveries priority: ~0.85 (high)
  - errors_resolved priority: ~0.1 (low, excluded)

## Related Stories

- Story 2: Activity Vector Model (dependency)
- Story 9: Dynamic Prompt Generation (uses this)
