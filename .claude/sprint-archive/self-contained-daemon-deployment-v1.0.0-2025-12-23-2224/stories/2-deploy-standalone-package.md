# Story 2: Deploy standalone package to ~/.graphiti/

**Status**: unassigned
**Created**: 2025-12-23 14:49

## Description

During daemon installation, copy the complete `mcp_server/` package to `~/.graphiti/mcp_server/` so the daemon can run independently of the project directory.

## Acceptance Criteria

- [ ] (P0) `mcp_server/` package is copied to `~/.graphiti/mcp_server/`
- [ ] (P0) All submodules (daemon/, etc.) are included in the deployment
- [ ] (P1) Deployment is idempotent (can run multiple times safely)
- [ ] (P1) Old deployments are backed up or cleanly replaced
- [ ] (P2) Deployment includes version marker for upgrade detection

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- [Story 1: Generate requirements.txt](1-generate-requirements-txt.md)
