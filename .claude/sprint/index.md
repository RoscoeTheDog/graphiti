# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-14 09:51:09

---

## Sprint Information

- **Sprint ID**: daemon-architecture-vv1.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 30
- **Completion**: 50.0%

### By Status

- completed: 15
- in_progress: 1
- unassigned: 14

### By Type

- implementation: 6
- validation: 6
- validation_discovery: 6
- validation_implementation: 6
- validation_testing: 6

---

## Stories (Execution Order)

  ### Story -1.d: Validate Discovery: Core Infrastructure (Management API + HTTP Client)
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -1
  - Blocks: Story -1.i

  ### Story -1.i: Validate Implementation: Core Infrastructure (Management API + HTTP Client)
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -1, Story -1.d
  - Blocks: Story -1.t

  ### Story -1.t: Validate Testing: Core Infrastructure (Management API + HTTP Client)
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -1, Story -1.i

  ### Story -2.d: Validate Discovery: Bootstrap Service (Config Watcher + MCP Lifecycle)
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -2
  - Blocks: Story -2.i

  ### Story -2.i: Validate Implementation: Bootstrap Service (Config Watcher + MCP Lifecycle)
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -2, Story -2.d
  - Blocks: Story -2.t

  ### Story -2.t: Validate Testing: Bootstrap Service (Config Watcher + MCP Lifecycle)
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -2, Story -2.i

  ### Story -3.d: Validate Discovery: CLI Refactoring (HTTP Client + Error Messages)
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -3
  - Blocks: Story -3.i

  ### Story -3.i: Validate Implementation: CLI Refactoring (HTTP Client + Error Messages)
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -3, Story -3.d
  - Blocks: Story -3.t

  ### Story -3.t: Validate Testing: CLI Refactoring (HTTP Client + Error Messages)
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -3, Story -3.i

  ### Story -4.d: Validate Discovery: Platform Service Installation (Windows/macOS/Linux)
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -4
  - Blocks: Story -4.i

  ### Story -4.i: Validate Implementation: Platform Service Installation (Windows/macOS/Linux)
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -4, Story -4.d
  - Blocks: Story -4.t

  ### Story -4.t: Validate Testing: Platform Service Installation (Windows/macOS/Linux)
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -4, Story -4.i

  ### Story -5.d: Validate Discovery: Claude Code Integration (HTTP Transport)
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -5
  - Blocks: Story -5.i

  ### Story -5.i: Validate Implementation: Claude Code Integration (HTTP Transport)
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -5, Story -5.d
  - Blocks: Story -5.t

  ### Story -5.t: Validate Testing: Claude Code Integration (HTTP Transport)
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -5, Story -5.i

  ### Story -6.d: Validate Discovery: Testing & Documentation
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -6
  - Blocks: Story -6.i

  ### Story -6.i: Validate Implementation: Testing & Documentation
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -6, Story -6.d
  - Blocks: Story -6.t

  ### Story -6.t: Validate Testing: Testing & Documentation
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -6, Story -6.i

### Story 1: Core Infrastructure Management Api Http Client
**Status**: completed | **Type**: implementation
- Blocks: Story 2, Story 3, Story 5

### Story 2: Bootstrap Service Config Watcher Mcp Lifecycle
**Status**: completed | **Type**: implementation
- Dependencies: Story 1
- Blocks: Story 3, Story 4, Story 5

### Story 3: Cli Refactoring Http Client Error Messages
**Status**: completed | **Type**: implementation
- Dependencies: Story 1, Story 2
- Blocks: Story 6

### Story 4: Platform Service Installation
**Status**: completed | **Type**: implementation
- Dependencies: Story 2
- Blocks: Story 6

### Story 5: Claude Code Integration Http Transport
**Status**: completed | **Type**: implementation
- Dependencies: Story 1, Story 2
- Blocks: Story 6

### Story 6: Testing And Documentation
**Status**: completed | **Type**: implementation
- Dependencies: Story 3, Story 4, Story 5

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
