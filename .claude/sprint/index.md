# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-14 19:54:39

---

## Sprint Information

- **Sprint ID**: daemon-venv-isolation-vv1.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 34
- **Completion**: 64.7%

### By Status

- blocked: 4
- completed: 22
- in_progress: 1
- pending: 3
- unassigned: 4

### By Type

- discovery: 7
- feature: 6
- implementation: 8
- remediation: 6
- testing: 7

---

## Stories (Execution Order)

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

  ### Story 2.d: Discovery: Package Installation to Dedicated Venv
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
  **Status**: blocked | **Type**: testing
  - Dependencies: Story 5

  ### Story 6.d: Discovery: Documentation and Testing
  **Status**: pending | **Type**: discovery
  - Dependencies: Story 6

  ### Story 6.i: Implementation: Documentation and Testing
  **Status**: pending | **Type**: implementation
  - Dependencies: Story 6

  ### Story 6.t: Testing: Documentation and Testing
  **Status**: pending | **Type**: testing
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
  **Status**: unassigned | **Type**: remediation
  - Dependencies: Story 5

  ### Story 5.r3: Fix Integration Test Mocking
  **Status**: unassigned | **Type**: remediation
  - Dependencies: Story 5

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
