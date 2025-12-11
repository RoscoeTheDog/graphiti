# Story 2: Activity Vector Model

**Status**: unassigned
**Created**: 2025-12-11 14:39

## Description

Implement the 8-dimensional ActivityVector model that represents session activities as continuous 0.0-1.0 values, replacing discrete classification. This enables sessions to score high on multiple dimensions simultaneously (e.g., 80% fixing + 70% configuring for a config-caused bug).

## Acceptance Criteria

- [ ] (P0) `ActivityVector` Pydantic model with 8 dimensions (building, fixing, configuring, exploring, refactoring, reviewing, testing, documenting)
- [ ] (P0) `from_signals()` class method normalizes raw signals to 0-1 range
- [ ] (P0) `dominant_activities` property returns activities above 0.3 threshold
- [ ] (P1) `activity_profile` property returns human-readable string (e.g., "fixing (0.8), configuring (0.7)")
- [ ] (P1) Unit tests for normalization, dominant activities, edge cases

## Dependencies

None

## Implementation Notes

**File to create**: `graphiti_core/session_tracking/activity_vector.py`

**Key design decisions**:
- All dimensions are 0.0-1.0 floats (NOT mutually exclusive)
- `from_signals()` normalizes by dividing by max value
- Default threshold of 0.3 for "dominant" activities
- `primary_activity` returns highest intensity or "mixed" if none above threshold

**Example**:
```python
signals = {"fixing": 0.8, "configuring": 0.7, "testing": 0.5}
av = ActivityVector.from_signals(signals)
# av.fixing == 1.0 (normalized to max)
# av.configuring == 0.875
# av.dominant_activities == ["fixing", "configuring", "testing"]
```

## Related Stories

- Story 3: Activity Detection from Messages (depends on this)
- Story 8: Extraction Priority Algorithm (depends on this)
