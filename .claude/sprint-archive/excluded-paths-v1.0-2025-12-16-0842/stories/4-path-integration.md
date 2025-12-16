# Story 4: PATH Integration

**Status**: unassigned
**Created**: 2025-12-14 16:51

## Description

Provide clear instructions (and optional auto-configuration) for adding `~/.graphiti/bin/` to user's PATH. This enables CLI commands to work from any terminal session.

## Acceptance Criteria

- [ ] (P0) `daemon install` outputs clear PATH instructions for user's platform
- [ ] (P1) Windows: Optionally modifies user PATH via registry (with user consent)
- [ ] (P1) Unix: Outputs shell rc file snippet for copy-paste
- [ ] (P2) Detects if PATH already includes `~/.graphiti/bin/`

## Dependencies

- Story 3: CLI Wrapper Script Generation

## Implementation Notes

### Platform-Specific Instructions

**Windows**:
```
Add to PATH (one-time):
  1. Open System Properties > Environment Variables
  2. Edit "Path" under User variables
  3. Add: %USERPROFILE%\.graphiti\bin

Or run (PowerShell as Admin):
  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$env:USERPROFILE\.graphiti\bin", "User")
```

**macOS/Linux (bash)**:
```bash
echo 'export PATH="$HOME/.graphiti/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**macOS/Linux (zsh)**:
```bash
echo 'export PATH="$HOME/.graphiti/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Related Stories

- Story 3: CLI Wrapper Script Generation (dependency)
