# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-14 21:12:15

---

## Sprint Information

- **Sprint ID**: daemon-venv-isolation-vv1.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 58
- **Completion**: 67.2%

### By Status

- blocked: 2
- completed: 39
- in_progress: 2
- unassigned: 15

### By Type

- discovery: 7
- feature: 6
- implementation: 8
- remediation: 6
- testing: 7
- validation: 6
- validation_discovery: 6
- validation_implementation: 6
- validation_testing: 6

---

## Stories (Execution Order)

  ### Story -1.d: Validate Discovery: Dedicated Venv Creation
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -1
  - Blocks: Story -1.i

  ### Story -1.i: Validate Implementation: Dedicated Venv Creation
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -1, Story -1.d
  - Blocks: Story -1.t

  ### Story -1.t: Validate Testing: Dedicated Venv Creation
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -1, Story -1.i

  ### Story -2.d: Validate Discovery: Package Installation to Dedicated Venv
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -2
  - Blocks: Story -2.i

  ### Story -2.i: Validate Implementation: Package Installation to Dedicated Venv
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -2, Story -2.d
  - Blocks: Story -2.t

  ### Story -2.t: Validate Testing: Package Installation to Dedicated Venv
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -2, Story -2.i

  ### Story -3.d: Validate Discovery: CLI Wrapper Script Generation
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -3
  - Blocks: Story -3.i

  ### Story -3.i: Validate Implementation: CLI Wrapper Script Generation
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -3, Story -3.d
  - Blocks: Story -3.t

  ### Story -3.t: Validate Testing: CLI Wrapper Script Generation
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -3, Story -3.i

  ### Story -4.d: Validate Discovery: PATH Integration
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -4
  - Blocks: Story -4.i

  ### Story -4.i: Validate Implementation: PATH Integration
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -4, Story -4.d
  - Blocks: Story -4.t

  ### Story -4.t: Validate Testing: PATH Integration
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -4, Story -4.i

  ### Story -5.d: Validate Discovery: Bootstrap Service Update
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -5
  - Blocks: Story -5.i

  ### Story -5.i: Validate Implementation: Bootstrap Service Update
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -5, Story -5.d
  - Blocks: Story -5.t

  ### Story -5.t: Validate Testing: Bootstrap Service Update
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -5, Story -5.i

  ### Story -6.d: Validate Discovery: Documentation and Testing
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -6
  - Blocks: Story -6.i

  ### Story -6.i: Validate Implementation: Documentation and Testing
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -6, Story -6.d
  - Blocks: Story -6.t

  ### Story -6.t: Validate Testing: Documentation and Testing
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -6, Story -6.i

  ### Story 1.d: Discovery: Dedicated Venv Creation
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 1

  ### Story 1.i: Implementation: Dedicated Venv Creation
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 1

    ### Story 1.t.r1: Test Interface Fixes
    **Status**: completed | **Type**: remediation
    - Dependencies: Story 1.t

  ### Story 1.t: Testing: Dedicated Venv Creation
  **Status**: completed | **Type**: testing
  - Dependencies: Story 1

  ### Story 2.d: 2 Package Installation To Venv
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 2

  ### Story 2.i: Implementation: Package Installation to Dedicated Venv
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 2

    ### Story 2.t.r1: Test Mock Fixes
    **Status**: completed | **Type**: remediation
    - Dependencies: Story 2.t

    ### Story 2.t.r2: Fix Platform Specific Test Moc
    **Status**: completed | **Type**: implementation
    - Dependencies: Story 2.t

  ### Story 2.t: Testing: Package Installation to Dedicated Venv
  **Status**: completed | **Type**: testing
  - Dependencies: Story 2

  ### Story 3.d: Discovery: CLI Wrapper Script Generation
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 3

  ### Story 3.i: Implementation: CLI Wrapper Script Generation
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 3

  ### Story 3.t: Testing: CLI Wrapper Script Generation
  **Status**: completed | **Type**: testing
  - Dependencies: Story 3

  ### Story 4.d: Discovery: PATH Integration
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 4

  ### Story 4.i: Implementation: PATH Integration
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 4

  ### Story 4.t: Testing: PATH Integration
  **Status**: completed | **Type**: testing
  - Dependencies: Story 4

  ### Story 5.d: Discovery: Bootstrap Service Update
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 5

  ### Story 5.i: Implementation: Bootstrap Service Update
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 5

  ### Story 5.t: Testing: Bootstrap Service Update
  **Status**: completed | **Type**: testing
  - Dependencies: Story 5

  ### Story 6.d: Discovery: Documentation and Testing
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 6

  ### Story 6.i: Implementation: Documentation and Testing
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 6

  ### Story 6.t: Testing: Documentation and Testing
  **Status**: completed | **Type**: testing
  - Dependencies: Story 6

      ### Story 4.r1.d: Discovery: Fix Test Failures in PATH Integration
      **Status**: completed | **Type**: discovery
      - Dependencies: Story 4.r1
      - Blocks: Story 4.r1.i

      ### Story 4.r1.i: Implementation: Fix Test Failures in PATH Integration
      **Status**: completed | **Type**: implementation
      - Dependencies: Story 4.r1, Story 4.r1.d
      - Blocks: Story 4.r1.t

      ### Story 4.r1.t: Testing: Fix Test Failures in PATH Integration
      **Status**: unassigned | **Type**: testing
      - Dependencies: Story 4.r1, Story 4.r1.i

  ### Story 5.r1: Error Handling Venv Validation
  **Status**: completed | **Type**: remediation
  - Dependencies: Story 5

  ### Story 5.r2: Fix Template Generation Tests
  **Status**: completed | **Type**: remediation
  - Dependencies: Story 5

  ### Story 5.r3: Fix Integration Test Mocking
  **Status**: completed | **Type**: remediation
  - Dependencies: Story 5

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
