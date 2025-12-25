# Story 17: Windows v2.0 to v2.1 Migration Test

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 5 - End-to-End Testing

## Description

Test the complete migration path from v2.0 installation (~/.graphiti/) to v2.1 on Windows, ensuring configuration is preserved and old artifacts are cleaned up.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Create v2.0 test fixture (~/.graphiti/ structure)
- [ ] Document expected migration behavior
- [ ] Define success criteria for migration
- [ ] Document rollback procedure if migration fails

### (i) Implementation Phase
- [ ] (P0) Set up v2.0 installation fixture with config and logs
- [ ] Run migration process
- [ ] Verify old Task Scheduler task is detected
- [ ] Verify config is copied to new location

### (t) Testing Phase
- [ ] (P0) Verify config content is preserved after migration
- [ ] (P0) Verify old Task Scheduler task is removed
- [ ] Verify new v2.1 installation works after migration
- [ ] Verify no data loss during migration
- [ ] Test migration when v2.1 already partially exists

## Dependencies

- Story 11: Implement v2.0 Installation Detection
- Story 12: Implement Config Migration
- Story 13: Implement Old Installation Cleanup
- Story 14: Windows Fresh Install Test

## Implementation Notes

Create ~/.graphiti/ with:
- graphiti.config.json (with test settings)
- .venv/ (can be empty placeholder)
- logs/bootstrap.log (with test content)
