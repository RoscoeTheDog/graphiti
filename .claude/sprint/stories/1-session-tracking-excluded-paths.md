---
description: Session Tracking Excluded Paths
---

# Feature 1: Session Tracking Excluded Paths

**Type**: Feature (Container)
**Status**: unassigned
**Parent**: None (top-level)
**Created**: 2025-12-15T22:01:08.645286

---

## Phase Status

| Phase | Story ID | Status | Artifact |
|-------|----------|--------|----------|
| Discovery | 1.d | pending | plans/1-plan.yaml |
| Implementation | 1.i | pending | Code changes |
| Testing | 1.t | pending | test-results/1-results.json |

---

## User Story

As a developer using Graphiti auto-tracking with multiple projects, I want to exclude specific project paths from session tracking so that orchestration systems (like Temporal BMAD server) can use direct Graphiti writes for structured checkpoints without interference from auto-tracking summarization.

---

## Background

### Problem Statement

When running a Temporal orchestrator that manages BMAD agents:
1. **Orchestrator** needs structured checkpoints stored verbatim (no LLM summarization)
2. **BMAD Agents** benefit from auto-tracking with summarization for context memory
3. Currently, auto-tracking processes ALL sessions under `watch_path` uniformly

### Decision Made (Q1 Resolution)

**Option C: Dual-Track Architecture** was selected:
- Temporal Server: Uses manual `graphiti.add_episode()` for checkpoints (excluded from auto-tracking)
- BMAD Agents: Use auto-tracking with default summarization

This requires adding `excluded_paths` to the session tracking configuration.

---

## Acceptance Criteria

- [ ] Add `excluded_paths: List[str]` to `SessionTrackingConfig`
- [ ] Default value: `[]` (empty list, no exclusions)
- [ ] Update `graphiti.config.schema.json` to include new field
- [ ] Paths support both absolute and relative-to-watch_path formats
- [ ] Support glob patterns (e.g., `**/temporal-*-server/**`)
- [ ] Platform-agnostic path comparison (normalize slashes)
- [ ] Implement path matching in `SessionManager._start_tracking_session()`
- [ ] Skip session tracking for JSONL files under excluded paths
- [ ] Log when a session is skipped due to exclusion (DEBUG level)
- [ ] Log excluded paths on daemon startup (INFO level)
- [ ] Update CONFIGURATION.md with new field
- [ ] Add example showing Temporal server exclusion

---

## Implementation Notes

### Approach

Add `excluded_paths` field to `SessionTrackingConfig` and implement path matching in `SessionManager`.

### Files to Modify

1. `graphiti_core/config/session_tracking.py` - Add field to SessionTrackingConfig
2. `graphiti_core/session_tracking/session_manager.py` - Implement exclusion logic
3. `graphiti.config.schema.json` - Regenerate schema
4. `CONFIGURATION.md` - Document new field

### Technical Design

```python
# In SessionTrackingConfig
excluded_paths: List[str] = Field(
    default_factory=list,
    description=(
        "List of paths to exclude from session tracking. "
        "Supports absolute paths, paths relative to watch_path, and glob patterns."
    )
)
```

```python
# In SessionManager
def _is_path_excluded(self, session_path: Path) -> bool:
    """Check if session path matches any exclusion pattern."""
    ...

def _start_tracking_session(self, session_path: Path):
    if self._is_path_excluded(session_path):
        logger.debug(f"Skipping excluded path: {session_path}")
        return
    # ... existing logic ...
```

### Testing Requirements

- Test empty `excluded_paths` (no exclusions, all sessions tracked)
- Test absolute path exclusion
- Test relative path exclusion
- Test glob pattern matching
- Test platform-specific path normalization (Windows backslashes)
- Test daemon startup with excluded paths configured
- Test that excluded sessions are actually skipped
- Test that non-excluded sessions are still tracked

---

## 5W Completeness Check

- **Who**: Developers using Graphiti with orchestration systems (Temporal, etc.)
- **What**: Add `excluded_paths` configuration to session tracking
- **When**: When session tracking daemon processes new JSONL files
- **Where**: `SessionTrackingConfig` and `SessionManager`
- **Why**: Enable dual-track architecture where orchestrators use direct writes while agents use auto-tracking

---

## Out of Scope

- Per-path filter configuration (different FilterConfig per path)
- Include patterns (only exclusion, not inclusion filtering)
- Runtime path updates (requires daemon restart)

---

## Metadata

**Workload Score**: Small (2-3 hours)
**Estimated Tokens**: ~5000
**Dependencies**: None
**Phase Children**: 1.d, 1.i, 1.t
