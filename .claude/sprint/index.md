# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-23 19:17:33

---

## Sprint Information

- **Sprint ID**: self-contained-daemon-deployment-v1.0.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 48
- **Completion**: 66.7%

### By Status

- completed: 32
- in_progress: 2
- unassigned: 14

### By Type

- discovery: 6
- feature: 6
- implementation: 6
- testing: 6
- validation: 6
- validation_discovery: 6
- validation_implementation: 6
- validation_testing: 6

---

## Stories (Execution Order)

  ### Story -1.d: Validate Discovery: Generate requirements.txt from pyproject.toml
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -1
  - Blocks: Story -1.i

  ### Story -1.i: Validate Implementation: Generate requirements.txt from pyproject.toml
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -1, Story -1.d
  - Blocks: Story -1.t

  ### Story -1.t: Validation_Testing_Results_ 1.T
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -1, Story -1.i

  ### Story -2.d: Validation_Discovery_Results_ 2.D
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -2
  - Blocks: Story -2.i

  ### Story -2.i: Validate Implementation: Deploy standalone package to ~/.graphiti/
  **Status**: completed | **Type**: validation_implementation
  - Dependencies: Story -2, Story -2.d
  - Blocks: Story -2.t

  ### Story -2.t: Validate Testing: Deploy standalone package to ~/.graphiti/
  **Status**: completed | **Type**: validation_testing
  - Dependencies: Story -2, Story -2.i

  ### Story -3.d: Validate Discovery: Update venv_manager to use deployed package
  **Status**: completed | **Type**: validation_discovery
  - Dependencies: Story -3
  - Blocks: Story -3.i

  ### Story -3.i: Validate Implementation: Update venv_manager to use deployed package
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -3, Story -3.d
  - Blocks: Story -3.t

  ### Story -3.t: Validate Testing: Update venv_manager to use deployed package
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -3, Story -3.i

  ### Story -4.d: Validate Discovery: Fix NSSM service configuration
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -4
  - Blocks: Story -4.i

  ### Story -4.i: Validate Implementation: Fix NSSM service configuration
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -4, Story -4.d
  - Blocks: Story -4.t

  ### Story -4.t: Validate Testing: Fix NSSM service configuration
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -4, Story -4.i

  ### Story -5.d: Validate Discovery: End-to-end installation test
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -5
  - Blocks: Story -5.i

  ### Story -5.i: Validate Implementation: End-to-end installation test
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -5, Story -5.d
  - Blocks: Story -5.t

  ### Story -5.t: Validate Testing: End-to-end installation test
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -5, Story -5.i

  ### Story -6.d: Validate Discovery: Standalone uninstall scripts for all platforms
  **Status**: unassigned | **Type**: validation_discovery
  - Dependencies: Story -6
  - Blocks: Story -6.i

  ### Story -6.i: Validate Implementation: Standalone uninstall scripts for all platforms
  **Status**: unassigned | **Type**: validation_implementation
  - Dependencies: Story -6, Story -6.d
  - Blocks: Story -6.t

  ### Story -6.t: Validate Testing: Standalone uninstall scripts for all platforms
  **Status**: unassigned | **Type**: validation_testing
  - Dependencies: Story -6, Story -6.i

  ### Story 1.d: Discovery: Generate requirements.txt from pyproject.toml
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 1

  ### Story 1.i: Implementation: Generate requirements.txt from pyproject.toml
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 1

  ### Story 1.t: Testing: Generate requirements.txt from pyproject.toml
  **Status**: completed | **Type**: testing
  - Dependencies: Story 1

  ### Story 2.d: Discovery: Deploy standalone package to ~/.graphiti/
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 2

  ### Story 2.i: Implementation: Deploy standalone package to ~/.graphiti/
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 2

  ### Story 2.t: Testing: Deploy standalone package to ~/.graphiti/
  **Status**: completed | **Type**: testing
  - Dependencies: Story 2

  ### Story 3.d: Discovery: Update venv_manager to use deployed package
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 3

  ### Story 3.i: Implementation: Update venv_manager to use deployed package
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 3

  ### Story 3.t: Testing: Update venv_manager to use deployed package
  **Status**: completed | **Type**: testing
  - Dependencies: Story 3

  ### Story 4.d: Discovery: Fix NSSM service configuration
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 4

  ### Story 4.i: Implementation: Fix NSSM service configuration
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 4

  ### Story 4.t: Testing: Fix NSSM service configuration
  **Status**: completed | **Type**: testing
  - Dependencies: Story 4

  ### Story 5.d: Discovery End To End Installation Test
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 5

  ### Story 5.i: Implementation: End-to-end installation test
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 5

  ### Story 5.t: Testing: End-to-end installation test
  **Status**: completed | **Type**: testing
  - Dependencies: Story 5

  ### Story 6.d: Discovery: Standalone uninstall scripts for all platforms
  **Status**: completed | **Type**: discovery
  - Dependencies: Story 6
  - Blocks: Story 6.i

  ### Story 6.i: Implementation: Standalone uninstall scripts for all platforms
  **Status**: completed | **Type**: implementation
  - Dependencies: Story 6, Story 6.d
  - Blocks: Story 6.t

  ### Story 6.t: Testing: Standalone uninstall scripts for all platforms
  **Status**: completed | **Type**: testing
  - Dependencies: Story 6, Story 6.i

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
