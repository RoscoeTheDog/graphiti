# Story 2: Package Installation to Dedicated Venv

**Status**: unassigned
**Created**: 2025-12-14 16:51

## Description

Install mcp_server package (non-editable) into the dedicated venv during daemon install. The installation must not contain hardcoded paths - all paths are discovered dynamically at install time.

## Acceptance Criteria

- [ ] (P0) `daemon install` runs `uv pip install ./mcp_server` (or pip fallback) into `~/.graphiti/.venv/`
- [ ] (P0) Installation is non-editable (stable, not tied to repo location)
- [ ] (P1) Detects repo location dynamically at install time (no hardcoded paths)
- [ ] (P1) Validates successful installation before proceeding

## Dependencies

- Story 1: Dedicated Venv Creation

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Dedicated Venv Creation (dependency)
- Story 3: CLI Wrapper Script Generation (depends on this)
- Story 5: Bootstrap Service Update (depends on this)
