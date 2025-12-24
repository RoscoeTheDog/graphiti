# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-23 16:23:44

---

## Sprint Information

- **Sprint ID**: self-contained-daemon-deployment-v1.0.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 24
- **Completion**: 41.7%

### By Status

- completed: 10
- in_progress: 1
- pending: 6
- unassigned: 7

### By Type

- discovery: 6
- feature: 6
- implementation: 6
- testing: 6

---

## Stories (Execution Order)

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
  **Status**: unassigned | **Type**: testing
  - Dependencies: Story 3

  ### Story 4.d: Discovery: Fix NSSM service configuration
  **Status**: pending | **Type**: discovery
  - Dependencies: Story 4

  ### Story 4.i: Implementation: Fix NSSM service configuration
  **Status**: pending | **Type**: implementation
  - Dependencies: Story 4

  ### Story 4.t: Testing: Fix NSSM service configuration
  **Status**: pending | **Type**: testing
  - Dependencies: Story 4

  ### Story 5.d: Discovery: End-to-end installation test
  **Status**: pending | **Type**: discovery
  - Dependencies: Story 5

  ### Story 5.i: Implementation: End-to-end installation test
  **Status**: pending | **Type**: implementation
  - Dependencies: Story 5

  ### Story 5.t: Testing: End-to-end installation test
  **Status**: pending | **Type**: testing
  - Dependencies: Story 5

  ### Story 6.d: Discovery: Standalone uninstall scripts for all platforms
  **Status**: unassigned | **Type**: discovery
  - Dependencies: Story 6
  - Blocks: Story 6.i

  ### Story 6.i: Implementation: Standalone uninstall scripts for all platforms
  **Status**: unassigned | **Type**: implementation
  - Dependencies: Story 6, Story 6.d
  - Blocks: Story 6.t

  ### Story 6.t: Testing: Standalone uninstall scripts for all platforms
  **Status**: unassigned | **Type**: testing
  - Dependencies: Story 6, Story 6.i

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
