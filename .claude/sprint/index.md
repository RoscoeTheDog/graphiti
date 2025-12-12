# Sprint Index (Auto-Generated from .queue.json)

**DO NOT EDIT**: This file is auto-generated. Edit .queue.json instead.

**Generated**: 2025-12-12 01:12:06

---

## Sprint Information

- **Sprint ID**: turn-based-preprocessing-injection-v1.0
- **Status**: active
- **Branch**: dev

## Sprint Statistics

- **Total Stories**: 14
- **Completion**: 35.7%

### By Status

- completed: 5
- unassigned: 9

### By Type

- implementation: 10
- unknown: 4

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

### Story 3: Create Default Session Turn Template
**Status**: unassigned | **Type**: implementation

### Story 4: Modify Node Operations Preprocessing
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 2
- Blocks: Story 10, Story 5

### Story 5: Modify Edge Operations Preprocessing
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 2, Story 4
- Blocks: Story 10

### Story 6: Add Extraction Config Unified
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 1
- Blocks: Story 11, Story 7, Story 9

### Story 7: Wire Preprocessing Mcp Server
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 2, Story 6

### Story 8: Implement Templateresolver
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 1
- Blocks: Story 10, Story 9

### Story 9: Template Validation Error Handling
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 6, Story 8

### Story 10: Unit Tests Preprocessing
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 4, Story 5, Story 8

### Story 11: Update Configuration Docs
**Status**: unassigned | **Type**: implementation
- Dependencies: Story 6

---

**Note**: This index is automatically generated from `.queue.json`. To modify stories, use the queue helper scripts or update `.queue.json` directly.
