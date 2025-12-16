# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-16 00:08:55

---

## Sprint Information

- **Sprint ID**: excluded-paths-v1.0
- **Status**: active
- **Branch**: sprint/daemon-venv-isolation

## Sprint Statistics

- **Total Stories**: 12
- **Completion**: 83.3%

### By Status

- completed: 10
- in_progress: 1
- unassigned: 1

### By Type

- discovery: 2
- feature: 1
- implementation: 2
- remediation: 1
- testing: 2
- validation: 1
- validation_discovery: 1
- validation_implementation: 1
- validation_testing: 1

---

## Stories (Execution Order)

  ### Story -1.d: Validate Discovery: Session Tracking Excluded Paths
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -1
  - Blocks: Story -1.i

  ### Story -1.i: Validate Implementation: Session Tracking Excluded Paths
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -1, Story -1.d
  - Blocks: Story -1.t

  ### Story -1.t: Validate Testing: Session Tracking Excluded Paths
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -1, Story -1.i

  ### Story 1.d: 1 Session Tracking Excluded Paths
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 1
  - Blocks: Story 1.i

  ### Story 1.i: Implementation: Session Tracking Excluded Paths
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 1, Story 1.d
  - Blocks: Story 1.t

  ### Story 1.t: 1 Session Tracking Excluded Paths
  **Status**: completed | **Type**: testing
  - Dependencies: Story 1, Story 1.i

    ### Story 1.r1.d: 1.R1 Fix Path Exclusion Logic Implementation
    **Status**: completed | **Type**: discovery
    - Dependencies: Story 1.r1
    - Blocks: Story 1.r1.i

    ### Story 1.r1.i: Implementation: Fix Path Exclusion Logic Implementation
    **Status**: completed | **Type**: implementation
    - Dependencies: Story 1.r1, Story 1.r1.d
    - Blocks: Story 1.r1.t

    ### Story 1.r1.t: 1.R1 Fix Path Exclusion Logic Implementation
    **Status**: completed | **Type**: testing
    - Dependencies: Story 1.r1, Story 1.r1.i

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
