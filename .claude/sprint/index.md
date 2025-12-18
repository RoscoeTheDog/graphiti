# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-18 08:49:08

---

## Sprint Information

- **Sprint ID**: daemon-auto-enable-ux-v1.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 36
- **Completion**: 80.6%

### By Status

- blocked: 4
- completed: 29
- in_progress: 1
- unassigned: 2

### By Type

- discovery: 6
- feature: 4
- implementation: 6
- remediation: 2
- testing: 6
- validation: 3
- validation_discovery: 3
- validation_implementation: 3
- validation_testing: 3

---

## Stories (Execution Order)

  ### Story -1.d: Validate Discovery: Auto-Enable Daemon on Install
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -1
  - Blocks: Story -1.i

  ### Story -1.i: Validate Implementation: Auto-Enable Daemon on Install
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -1, Story -1.d
  - Blocks: Story -1.t

  ### Story -1.t: Validate Testing: Auto-Enable Daemon on Install
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -1, Story -1.i

  ### Story -2.d: Validate Discovery: Clear Error Feedback for Connection Failures
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -2
  - Blocks: Story -2.i

  ### Story -2.i: Validate Implementation: Clear Error Feedback for Connection Failures
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -2, Story -2.d
  - Blocks: Story -2.t

  ### Story -2.t: Validate Testing: Clear Error Feedback for Connection Failures
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -2, Story -2.i

  ### Story -3.d: Validate Discovery: Update Installation Documentation
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -3
  - Blocks: Story -3.i

  ### Story -3.i: Validate Implementation: Update Installation Documentation
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -3, Story -3.d
  - Blocks: Story -3.t

  ### Story -3.t: Validate Testing: Update Installation Documentation
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -3, Story -3.i

  ### Story 1.d: Discovery: Auto-Enable Daemon on Install
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 1

  ### Story 1.i: Implementation: Auto-Enable Daemon on Install
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 1

  ### Story 1.t: Testing: Auto-Enable Daemon on Install
  **Status**: completed | **Type**: testing
  - Dependencies: Story 1

  ### Story 2.d: Discovery: Clear Error Feedback for Connection Failures
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 2

  ### Story 2.i: Implementation: Clear Error Feedback for Connection Failures
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 2

  ### Story 2.t: Testing: Clear Error Feedback for Connection Failures
  **Status**: completed | **Type**: testing
  - Dependencies: Story 2

  ### Story 3.d: Discovery: Update Installation Documentation
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 3

  ### Story 3.i: Implementation: Update Installation Documentation
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 3

  ### Story 3.t: Testing: Update Installation Documentation
  **Status**: completed | **Type**: testing
  - Dependencies: Story 3

  ### Story 4.d: Discovery: Validation - End-to-End UX Test
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 4

  ### Story 4.i: Implementation: Validation - End-to-End UX Test
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 4

  ### Story 4.t: Testing: Validation - End-to-End UX Test
  **Status**: blocked | **Type**: testing
  - Dependencies: Story 4

    ### Story 4.1.d: Discovery: Fix E2E Test Fixtures VenvCreationError
    **Status**: completed | **Type**: discovery
    - Dependencies: Story 4.1
    - Blocks: Story 4.1.i

    ### Story 4.1.i: Implementation: Fix E2E Test Fixtures VenvCreationError
    **Status**: completed | **Type**: implementation
    - Dependencies: Story 4.1, Story 4.1.d
    - Blocks: Story 4.1.t

    ### Story 4.1.t: Testing: Fix E2E Test Fixtures VenvCreationError
    **Status**: blocked | **Type**: testing
    - Dependencies: Story 4.1, Story 4.1.i

    ### Story 4.2.d: Discovery: Fix E2E Test API Assertions
    **Status**: completed | **Type**: discovery
    - Dependencies: Story 4.2
    - Blocks: Story 4.2.i

    ### Story 4.2.i: Implementation: Fix E2E Test API Assertions
    **Status**: unassigned | **Type**: implementation
    - Dependencies: Story 4.2, Story 4.2.d
    - Blocks: Story 4.2.t

    ### Story 4.2.t: Testing: Fix E2E Test API Assertions
    **Status**: unassigned | **Type**: testing
    - Dependencies: Story 4.2, Story 4.2.i

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
