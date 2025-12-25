# Story 10: Fix Bootstrap Module Invocation

**Status**: in_progress (discovery complete)
**Created**: 2025-12-25 02:02
**Phase**: 3 - Service Manager Updates

## Description

Fix the bootstrap module to work correctly when invoked via `-m mcp_server.daemon.bootstrap` from the frozen installation, including proper sys.path setup for frozen packages.

## Acceptance Criteria

### (d) Discovery Phase
- [x] (P0) Analyze current bootstrap import issues (relative vs absolute)
- [x] Document why direct script execution fails
- [x] Design _setup_frozen_path() function
- [x] Identify all imports that need frozen path

**Discovery Complete**: See `.claude/sprint/discoveries/10.d-bootstrap-import-analysis.md` for full analysis.

### (i) Implementation Phase
- [ ] (P0) Add `_setup_frozen_path()` function at top of bootstrap.py
- [ ] (P0) Detect if running from frozen install vs development
- [ ] Insert lib/ path into sys.path before other imports
- [ ] Update all imports to work with both frozen and dev modes
- [ ] Remove any `if __name__ == "__main__"` direct execution patterns
- [ ] Ensure bootstrap works when invoked as `-m mcp_server.daemon.bootstrap`

### (t) Testing Phase
- [ ] (P0) Verify bootstrap runs with `-m` invocation from install dir
- [ ] Verify bootstrap still works in development mode
- [ ] Verify all imports resolve correctly in frozen mode

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module
- Story 5: Implement Frozen Package Deployment

## Implementation Notes

```python
def _setup_frozen_path():
    """Ensure frozen packages in lib/ are importable."""
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent.parent
    else:
        # bootstrap.py is in {INSTALL}/lib/mcp_server/daemon/
        base = Path(__file__).parent.parent.parent.parent

    lib_path = base / "lib"
    if lib_path.exists() and str(lib_path) not in sys.path:
        sys.path.insert(0, str(lib_path))

_setup_frozen_path()
```
