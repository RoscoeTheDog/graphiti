# Story 3: Update venv_manager to use deployed package

**Status**: unassigned
**Created**: 2025-12-23 14:49

## Description

Modify `venv_manager.py` to install dependencies from `~/.graphiti/requirements.txt` using `uvx` or `uv pip install -r` instead of installing from the project directory.

## Acceptance Criteria

- [ ] (P0) `install_package()` installs from `~/.graphiti/requirements.txt`
- [ ] (P0) Uses `uvx` when available, falls back to `uv pip` or `pip`
- [ ] (P1) Installation validates that `mcp_server` is importable after install
- [ ] (P1) Error handling provides clear messages if requirements.txt is missing

## Dependencies

Story 1, Story 2

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 1: Generate requirements.txt](1-generate-requirements-txt.md)
- [Story 2: Deploy standalone package](2-deploy-standalone-package.md)
