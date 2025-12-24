# Story 1: Generate requirements.txt from pyproject.toml

**Status**: unassigned
**Created**: 2025-12-23 14:49

## Description

Create a mechanism to generate a standalone `requirements.txt` file from `mcp_server/pyproject.toml` during daemon installation. This ensures all dependencies are captured and can be installed independently.

## Acceptance Criteria

- [ ] (P0) Script can parse `mcp_server/pyproject.toml` and extract all dependencies
- [ ] (P0) Generated `requirements.txt` includes pinned versions where available
- [ ] (P1) Script handles optional dependencies appropriately
- [ ] (P1) Output is written to `~/.graphiti/requirements.txt`

## Dependencies

None

## Implementation Notes

*To be added during implementation*

## Related Stories

None
