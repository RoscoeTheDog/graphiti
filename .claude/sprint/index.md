# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-18 19:26:04

---

## Sprint Information

- **Sprint ID**: per-project-configuration-overrides-v1.1.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 52
- **Completion**: 92.3%

### By Status

- blocked: 2
- completed: 48
- in_progress: 1
- unassigned: 1

### By Type

- discovery: 7
- feature: 6
- implementation: 7
- remediation: 1
- testing: 7
- validation: 6
- validation_discovery: 6
- validation_implementation: 6
- validation_testing: 6

---

## Stories (Execution Order)

    ### Story 1.r.d: Discovery: Fix Test Isolation - Global Config Singleton Pollution
    **Status**: completed | **Type**: discovery
    - Dependencies: Story 1.r
    - Blocks: Story 1.r.i

    ### Story 1.r.i: Implementation: Fix Test Isolation - Global Config Singleton Pollution
    **Status**: completed | **Type**: implementation
    - Dependencies: Story 1.r, Story 1.r.d
    - Blocks: Story 1.r.t

    ### Story 1.r.t: Testing: Fix Test Isolation - Global Config Singleton Pollution
    **Status**: completed | **Type**: testing
    - Dependencies: Story 1.r, Story 1.r.i

  ### Story -1.d: Validate Discovery: Add ProjectOverride Schema and Deep Merge Logic
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -1
  - Blocks: Story -1.i

  ### Story -1.i: Validate Implementation: Add ProjectOverride Schema and Deep Merge Logic
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -1, Story -1.d
  - Blocks: Story -1.t

  ### Story -1.t: Validate Testing: Add ProjectOverride Schema and Deep Merge Logic
  **Status**: blocked | **Type**: validation_testing
  - Dependencies: Story -1, Story -1.i

  ### Story -2.d: Validate Discovery: Implement get_effective_config() Method
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -2
  - Blocks: Story -2.i

  ### Story -2.i: Validate Implementation: Implement get_effective_config() Method
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -2, Story -2.d
  - Blocks: Story -2.t

  ### Story -2.t: Validate Testing: Implement get_effective_config() Method
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -2, Story -2.i

  ### Story -3.d: Validate Discovery: CLI Command - config effective
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -3
  - Blocks: Story -3.i

  ### Story -3.i: Validate Implementation: CLI Command - config effective
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -3, Story -3.d
  - Blocks: Story -3.t

  ### Story -3.t: Validate Testing: CLI Command - config effective
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -3, Story -3.i

  ### Story -4.d: Validate Discovery: CLI Commands - list-projects, set-override, remove-override
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -4
  - Blocks: Story -4.i

  ### Story -4.i: Validate Implementation: CLI Commands - list-projects, set-override, remove-override
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -4, Story -4.d
  - Blocks: Story -4.t

  ### Story -4.t: Validate Testing: CLI Commands - list-projects, set-override, remove-override
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -4, Story -4.i

  ### Story -5.d: Validate Discovery: Session Tracking Integration
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -5
  - Blocks: Story -5.i

  ### Story -5.i: Validate Implementation: Session Tracking Integration
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -5, Story -5.d
  - Blocks: Story -5.t

  ### Story -5.t: Validate Testing: Session Tracking Integration
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -5, Story -5.i

  ### Story -6.d: Validate Discovery: Config Validation and Documentation
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -6
  - Blocks: Story -6.i

  ### Story -6.i: Validate Implementation: Config Validation and Documentation
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -6, Story -6.d
  - Blocks: Story -6.t

  ### Story -6.t: Validate Testing: Config Validation and Documentation
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -6, Story -6.i

  ### Story 1.d: Discovery: Add ProjectOverride Schema and Deep Merge Logic
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 1

  ### Story 1.i: Implementation: Add ProjectOverride Schema and Deep Merge Logic
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 1

  ### Story 1.t: Testing: Add ProjectOverride Schema and Deep Merge Logic
  **Status**: completed | **Type**: testing
  - Dependencies: Story 1

  ### Story 2.d: Discovery: Implement get_effective_config() Method
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 2

  ### Story 2.i: Implementation: Implement get_effective_config() Method
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 2

  ### Story 2.t: Testing: Implement get_effective_config() Method
  **Status**: completed | **Type**: testing
  - Dependencies: Story 2

  ### Story 3.d: Discovery: CLI Command - config effective
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 3

  ### Story 3.i: Implementation: CLI Command - config effective
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 3

  ### Story 3.t: Testing: CLI Command - config effective
  **Status**: completed | **Type**: testing
  - Dependencies: Story 3

  ### Story 4.d: Discovery: CLI Commands - list-projects, set-override, remove-override
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 4

  ### Story 4.i: Implementation: CLI Commands - list-projects, set-override, remove-override
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 4

  ### Story 4.t: Testing: CLI Commands - list-projects, set-override, remove-override
  **Status**: completed | **Type**: testing
  - Dependencies: Story 4

  ### Story 5.d: Discovery: Session Tracking Integration
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 5

  ### Story 5.i: Implementation: Session Tracking Integration
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 5

  ### Story 5.t: Testing: Session Tracking Integration
  **Status**: completed | **Type**: testing
  - Dependencies: Story 5

  ### Story 6.d: Discovery: Config Validation and Documentation
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 6

  ### Story 6.i: 6 Plan
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 6

  ### Story 6.t: Testing: Config Validation and Documentation
  **Status**: completed | **Type**: testing
  - Dependencies: Story 6

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
