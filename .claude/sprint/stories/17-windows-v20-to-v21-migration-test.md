# Story 17: Windows v2.0 to v2.1 Migration Test

**Status**: completed
**Created**: 2025-12-25 02:02
**Phase**: 5 - End-to-End Testing

## Description

Test the complete migration path from v2.0 installation (~/.graphiti/) to v2.1 on Windows, ensuring configuration is preserved and old artifacts are cleaned up.

## Acceptance Criteria

### (d) Discovery Phase ✅ COMPLETE
- [x] (P0) Create v2.0 test fixture (~/.graphiti/ structure)
- [x] Document expected migration behavior
- [x] Define success criteria for migration
- [x] Document rollback procedure if migration fails

### (i) Implementation Phase ✅ COMPLETE
- [x] (P0) Set up v2.0 installation fixture with config and logs
- [x] Run migration process
- [x] Verify old Task Scheduler task is detected
- [x] Verify config is copied to new location

**Artifact**: `tests/daemon/test_config_migration.py` - comprehensive migration tests

### (t) Testing Phase ✅ COMPLETE
- [x] (P0) Verify config content is preserved after migration
- [x] (P0) Verify old Task Scheduler task is removed
- [x] Verify new v2.1 installation works after migration
- [x] Verify no data loss during migration
- [x] Test migration when v2.1 already partially exists

**Artifact**: `tests/daemon/test_config_migration.py` covers all migration scenarios

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
