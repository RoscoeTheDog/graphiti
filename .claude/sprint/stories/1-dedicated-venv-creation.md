# Story 1: Dedicated Venv Creation

**Status**: unassigned
**Created**: 2025-12-14 16:51

## Description

Create infrastructure for a dedicated virtual environment at `~/.graphiti/.venv/` that is decoupled from any repo clone. This enables the daemon to run independently of the source repository location.

## Acceptance Criteria

- [ ] (P0) `daemon install` creates `~/.graphiti/.venv/` if it doesn't exist
- [ ] (P0) Uses `uv venv` if uv is available, falls back to `python -m venv`
- [ ] (P1) Detects existing venv and skips creation (idempotent)
- [ ] (P1) Validates Python version compatibility (>=3.10)

## Dependencies

None

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 2: Package Installation to Dedicated Venv (depends on this)
