# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-20 18:35:55

---

## Sprint Information

- **Sprint ID**: remediation-test-reconciliation-v1.0.0
- **Status**: completed
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 65
- **Completion**: 64.6%

### By Status

- completed: 42
- failed_validation: 1
- in_progress: 1
- unassigned: 21

### By Type

- discovery: 8
- feature: 8
- implementation: 8
- remediation: 1
- testing: 8
- validation: 8
- validation_discovery: 8
- validation_implementation: 8
- validation_testing: 8

---

## Stories (Execution Order)

  ### Story -1.d: Validation Discovery
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -1
  - Blocks: Story -1.i

  ### Story -1.i: Validate Implementation: Metadata Schema Extension
  **Status**: failed_validation | **Type**: validation_implementation
  - Dependencies: Story -1, Story -1.d
  - Blocks: Story -1.t

    ### Story 1.i.1: Fix Implementation Location
    **Status**: completed | **Type**: remediation
    - Dependencies: Story 1.i
    - Blocks: Story -1.t

  ### Story -1.t: Validate Testing: Metadata Schema Extension
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -1, Story -1.i, Story 1.i.1

  ### Story -2.d: Validation Discovery
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -2
  - Blocks: Story -2.i

  ### Story -2.i: Validation Implementation
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -2, Story -2.d
  - Blocks: Story -2.t

  ### Story -2.t: Validation Testing
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -2, Story -2.i

  ### Story -3.d: Validation Discovery
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -3
  - Blocks: Story -3.i

  ### Story -3.i: Validation Implementation
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -3, Story -3.d
  - Blocks: Story -3.t

  ### Story -3.t: Validate Testing: Overlap Calculation Algorithm
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -3, Story -3.i

  ### Story -4.d: Validate Discovery: Reconciliation Application Functions
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -4
  - Blocks: Story -4.i

  ### Story -4.i: Validate Implementation: Reconciliation Application Functions
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -4, Story -4.d
  - Blocks: Story -4.t

  ### Story -4.t: Validate Testing: Reconciliation Application Functions
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -4, Story -4.i

  ### Story -5.d: Validate Discovery: Container Status Propagation
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -5
  - Blocks: Story -5.i

  ### Story -5.i: Validate Implementation: Container Status Propagation
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -5, Story -5.d
  - Blocks: Story -5.t

  ### Story -5.t: Validate Testing: Container Status Propagation
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -5, Story -5.i

  ### Story -6.d: Validate Discovery: Remediation Testing Trigger
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -6
  - Blocks: Story -6.i

  ### Story -6.i: Validate Implementation: Remediation Testing Trigger
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -6, Story -6.d
  - Blocks: Story -6.t

  ### Story -6.t: Validate Testing: Remediation Testing Trigger
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -6, Story -6.i

  ### Story -7.d: Validate Discovery: queue_helpers.py Commands
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -7
  - Blocks: Story -7.i

  ### Story -7.i: Validate Implementation: queue_helpers.py Commands
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -7, Story -7.d
  - Blocks: Story -7.t

  ### Story -7.t: Validate Testing: queue_helpers.py Commands
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -7, Story -7.i

  ### Story -8.d: Validate Discovery: Validation Engine Skip Logic
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -8
  - Blocks: Story -8.i

  ### Story -8.i: Validate Implementation: Validation Engine Skip Logic
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -8, Story -8.d
  - Blocks: Story -8.t

  ### Story -8.t: Validate Testing: Validation Engine Skip Logic
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -8, Story -8.i

  ### Story 1.d: Discovery: Metadata Schema Extension
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 1

  ### Story 1.i: Implementation: Metadata Schema Extension
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 1

  ### Story 1.t: Testing: Metadata Schema Extension
  **Status**: completed | **Type**: testing
  - Dependencies: Story 1

  ### Story 2.d: Discovery: Test Identity Capture in REMEDIATE
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 2

  ### Story 2.i: Implementation: Test Identity Capture in REMEDIATE
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 2

  ### Story 2.t: Testing: Test Identity Capture in REMEDIATE
  **Status**: completed | **Type**: testing
  - Dependencies: Story 2

  ### Story 3.d: Discovery: Overlap Calculation Algorithm
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 3

  ### Story 3.i: Implementation: Overlap Calculation Algorithm
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 3

  ### Story 3.t: Testing: Overlap Calculation Algorithm
  **Status**: completed | **Type**: testing
  - Dependencies: Story 3

  ### Story 4.d: Discovery: Reconciliation Application Functions
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 4

  ### Story 4.i: Implementation: Reconciliation Application Functions
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 4

  ### Story 4.t: Testing: Reconciliation Application Functions
  **Status**: completed | **Type**: testing
  - Dependencies: Story 4

  ### Story 5.d: Discovery: Container Status Propagation
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 5

  ### Story 5.i: Implementation: Container Status Propagation
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 5

  ### Story 5.t: Testing: Container Status Propagation
  **Status**: completed | **Type**: testing
  - Dependencies: Story 5

  ### Story 6.d: Discovery: Remediation Testing Trigger
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 6

  ### Story 6.i: Implementation: Remediation Testing Trigger
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 6

  ### Story 6.t: Testing: Remediation Testing Trigger
  **Status**: completed | **Type**: testing
  - Dependencies: Story 6

  ### Story 7.d: Discovery: queue_helpers.py Commands
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 7

  ### Story 7.i: Implementation: queue_helpers.py Commands
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 7

  ### Story 7.t: Testing: queue_helpers.py Commands
  **Status**: completed | **Type**: testing
  - Dependencies: Story 7

  ### Story 8.d: Discovery: Validation Engine Skip Logic
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 8

  ### Story 8.i: Implementation: Validation Engine Skip Logic
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 8

  ### Story 8.t: Testing: Validation Engine Skip Logic
  **Status**: completed | **Type**: testing
  - Dependencies: Story 8

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
