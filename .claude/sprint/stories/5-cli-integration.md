# Story 5: CLI Integration
**Status**: unassigned
**Created**: 2025-11-17 00:05

**Depends on**: Story 1, Story 2, Story 2.3, Story 3
**Description**: Add global opt-in/out CLI commands for session tracking
**Acceptance Criteria**:
- [ ] CLI commands implemented (enable, disable, status)
- [ ] **Default configuration is enabled (opt-out model)** - NEW REQUIREMENT
- [ ] Configuration persisted to graphiti.config.json
- [ ] Applied on MCP server startup
- [ ] Documentation updated (CONFIGURATION.md)
- [ ] Cost estimates documented
- [ ] Opt-out instructions clear
- [ ] Migration note for existing users (default behavior change)
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Platform-agnostic config file paths
  - [ ] Type hints and comprehensive docstrings
  - [ ] Error handling with logging (config errors)
  - [ ] Configuration uses unified system
  - [ ] Documentation: User guide updated

