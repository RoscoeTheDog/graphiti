# Story 3: Update Installation Documentation

**Status**: unassigned
**Created**: 2025-12-17 15:28

## Description

Update CLAUDE_INSTALL.md and related docs to reflect the simplified install-once flow where daemon auto-enables.

## Acceptance Criteria

- [ ] (P0) CLAUDE_INSTALL.md updated to show single-command daemon setup
- [ ] (P1) Remove manual "edit config to enable" instructions
- [ ] (P1) Add troubleshooting section for common connection issues
- [ ] (P2) Update DAEMON_ARCHITECTURE_SPEC_v1.0.md to reflect auto-enable default

## Dependencies

- Story 1: Auto-Enable Daemon on Install (must be complete first)

## Implementation Notes

**Key Files**:
- `claude-mcp-installer/instance/CLAUDE_INSTALL.md` - Main installation guide
- `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md` - Architecture spec
- `README.md` - Project overview (if daemon setup mentioned)

**Documentation Changes**:

1. **CLAUDE_INSTALL.md**:
   - Simplify daemon setup to single command
   - Remove "edit config to enable" step
   - Add troubleshooting section with common issues
   - Update expected behavior description

2. **DAEMON_ARCHITECTURE_SPEC_v1.0.md**:
   - Update default config section (`enabled: true` after install)
   - Update user workflow section
   - Note breaking change from previous behavior

**Before/After Example**:

Before:
```
1. Run: graphiti-mcp daemon install
2. Edit config: Set daemon.enabled: true
3. Wait 5 seconds for server to start
```

After:
```
1. Run: graphiti-mcp daemon install
   (Server starts automatically)
```

## Related Stories

- Story 1: Auto-Enable (prerequisite)
- Story 4: Validation (will verify docs are accurate)
