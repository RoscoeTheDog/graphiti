# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-12 02:38:27

---

## Sprint Information

- **Sprint ID**: turn-based-preprocessing-injection-v1.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 23
- **Completion**: 95.7%

### By Status

- completed: 22
- unassigned: 1

### By Type

- implementation: 7
- unknown: 16

---

## Stories (Execution Order)

### Story 1: Create Extractionconfig Schema
**Status**: completed | **Type**: implementation
- Blocks: Story 2, Story 6, Story 8

  ### Story 2.d: Discovery: Extend GraphitiClients with Preprocessing Fields
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 2

  ### Story 2.i: Implementation: Extend GraphitiClients with Preprocessing Fields
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 2

  ### Story 2.t: Testing: Extend GraphitiClients with Preprocessing Fields
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 2

  ### Story 3.d: Discovery: Create Default Session Turn Template
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 3

  ### Story 3.i: Implementation: Create Default Session Turn Template
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 3

  ### Story 3.t: Testing: Create Default Session Turn Template
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 3

### Story 4: Modify Node Operations Preprocessing
**Status**: completed | **Type**: implementation
- Dependencies: Story 2
- Blocks: Story 10, Story 5

### Story 5: Modify Edge Operations Preprocessing
**Status**: completed | **Type**: implementation
- Dependencies: Story 2, Story 4
- Blocks: Story 10

  ### Story 6.d: Discovery: Add Extraction Config to unified_config.py
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 6

  ### Story 6.i: Implementation: Add Extraction Config to unified_config.py
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 6

  ### Story 6.t: Testing: Add Extraction Config to unified_config.py
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 6

### Story 7: Wire Preprocessing Mcp Server
**Status**: completed | **Type**: implementation
- Dependencies: Story 2, Story 6

### Story 8: Implement Templateresolver
**Status**: completed | **Type**: implementation
- Dependencies: Story 1
- Blocks: Story 10, Story 9

  ### Story 9.d: Discovery: Add Template Validation and Error Handling
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 9

  ### Story 9.i: Implementation: Add Template Validation and Error Handling
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 9

  ### Story 9.t: Testing: Add Template Validation and Error Handling
  **Status**: completed | **Type**: unknown
  - Dependencies: Story 9

### Story 10: Unit Tests Preprocessing
**Status**: completed | **Type**: implementation
- Dependencies: Story 4, Story 5, Story 8

### Story 11: Update Configuration Docs
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 6

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
