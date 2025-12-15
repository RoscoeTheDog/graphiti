# Story 3: CLI Wrapper Script Generation

**Status**: unassigned
**Created**: 2025-12-14 16:51

## Description

Generate platform-specific wrapper scripts in `~/.graphiti/bin/` that invoke the venv Python. These wrappers expose the CLI commands globally without requiring venv activation.

## Acceptance Criteria

- [ ] (P0) Creates `~/.graphiti/bin/` directory
- [ ] (P0) Generates wrapper scripts for: graphiti-mcp, graphiti-mcp-daemon, graphiti-bootstrap
- [ ] (P0) Windows: Creates .cmd batch files
- [ ] (P0) Unix: Creates shell scripts with executable permissions
- [ ] (P1) Wrapper scripts use absolute path to `~/.graphiti/.venv/` Python

## Dependencies

- Story 2: Package Installation to Dedicated Venv

## Implementation Notes

### Wrapper Script Templates

**Windows (.cmd)**:
```batch
@echo off
"%USERPROFILE%\.graphiti\.venv\Scripts\python.exe" -m mcp_server.graphiti_mcp_server %*
```

**Unix (shell)**:
```bash
#!/bin/bash
"$HOME/.graphiti/.venv/bin/python" -m mcp_server.graphiti_mcp_server "$@"
```

## Related Stories

- Story 2: Package Installation to Dedicated Venv (dependency)
- Story 4: PATH Integration (depends on this)
