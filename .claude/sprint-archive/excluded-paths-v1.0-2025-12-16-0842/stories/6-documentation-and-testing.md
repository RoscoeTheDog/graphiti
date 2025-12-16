# Story 6: Documentation and Testing

**Status**: unassigned
**Created**: 2025-12-14 16:51

## Description

Update installation documentation and add tests for the new setup flow. Documentation must clearly explain the clone → setup → install workflow for new users.

## Acceptance Criteria

- [ ] (P0) README.md updated with new installation steps
- [ ] (P0) TROUBLESHOOTING_DAEMON.md updated for venv-related issues
- [ ] (P1) Unit tests for venv creation and wrapper generation
- [ ] (P1) Integration test for full install → CLI availability flow

## Dependencies

- Stories 1-5 (all implementation stories)

## Implementation Notes

### README.md Updates

New installation flow:
```bash
# 1. Clone the repository
git clone https://github.com/RoscoeTheDog/graphiti.git
cd graphiti

# 2. Run daemon installer (creates venv, installs package, generates wrappers)
python mcp_server/daemon/installer.py

# 3. Add to PATH (follow platform-specific instructions from installer output)

# 4. Install daemon service
graphiti-mcp-daemon install

# 5. Enable daemon
# Edit ~/.graphiti/graphiti.config.json: "daemon": { "enabled": true }
```

### TROUBLESHOOTING_DAEMON.md Updates

New sections:
- "Venv not created" - uv/python issues
- "CLI commands not found after install" - PATH issues
- "Service fails to start" - Python path issues

### Test Coverage

- `test_venv_creation.py` - Tests for Story 1
- `test_package_installation.py` - Tests for Story 2
- `test_wrapper_generation.py` - Tests for Story 3
- `test_bootstrap_service.py` - Tests for Story 5
- `test_full_install_flow.py` - Integration test

## Related Stories

- Stories 1-5: All implementation stories (dependencies)
