# Session Handoff: s038-fix-daemon-tests-and-identify-stale-v20

**Status**: ACTIVE
**Created**: 2025-12-27 00:24
**Sequence**: 038

---

## Objective

Fix daemon tests and identify stale v2.0 references for v2.1 cleanup.

---

## Completed

- Fixed 8 failing daemon tests (test_package_deployer, test_wrapper_generator, test_installer)
- Updated expected paths from v2.0 (`~/.graphiti/`) to v2.1 (`get_install_dir()/lib`)
- Fixed test_install_flow_includes_new_steps to mock all 12 steps (was only 6)
- All 363 daemon tests now pass (was 355 pass, 8 fail)
- Committed test fixes to branch sprint/per-user-daemon-v21
- Ran v2.0 cleanup removing ~/.graphiti/ directory (backup created)
- Committed daemon SSE transport and installer fixes (commit 4efd939)
- Identified extensive stale v2.0/~/.graphiti references across codebase

---

## Blocked

None

---

## Next Steps

1. **Update uninstall scripts for v2.1** (CRITICAL - could delete wrong directories)
   - `uninstall_linux.sh`
   - `uninstall_macos.sh`
   - `uninstall_windows.ps1`

2. **Update service templates for v2.1 paths**
   - `templates/com.graphiti.bootstrap.plist` - Log paths
   - `templates/graphiti-bootstrap.service` - Log paths

3. **Update docstrings/comments for v2.1 paths**
   - `package_deployer.py` - Lines 4-15, 212
   - `wrapper_generator.py` - Lines 9, 42, 94, 107
   - `path_integration.py` - Lines 5-8, 42, 50, 154, 163
   - `generate_requirements.py` - Lines 12, 252, 277, 316

4. **Update config/CLI code paths**
   - `unified_config.py` - Config loading paths
   - `config_cli.py` - User-facing messages
   - `session_tracking_cli.py` - User-facing messages

5. **Update E2E test documentation**
   - `tests/README_E2E.md` - Extensive ~/.graphiti references

---

## Decisions

- **v2.1 path architecture**:
  - Windows: `%LOCALAPPDATA%\Programs\Graphiti` (install), `%LOCALAPPDATA%\Graphiti` (config/state)
  - macOS: `~/Library/Application Support/Graphiti/` (install), `~/Library/Preferences/Graphiti/` (config)
  - Linux: `~/.local/share/graphiti/` (install), `~/.config/graphiti/` (config)
- **Migration code stays**: v2_cleanup.py, v2_detection.py, installer_migration.py intentionally reference v2.0 for migration support

---

## Errors Resolved

- **Test failures**: Expected paths hardcoded to v2.0 (`~/.graphiti/`) while code uses v2.1 paths
- **tmpdir string/Path conversion**: TemporaryDirectory returns string, needed Path(tmpdir)
- **Incomplete mocking**: test_install_flow only mocked 6 of 12 steps

---

## Files Modified

- `tests/daemon/test_package_deployer.py` - Updated path expectations for v2.1
- `tests/daemon/test_wrapper_generator.py` - Updated path expectations for v2.1
- `tests/daemon/test_installer.py` - Extended mocking to all 12 install steps

---

## Stale Reference Categories

### Keep As-Is (Migration Code)
- `v2_cleanup.py` - Cleans up v2.0 artifacts
- `v2_detection.py` - Detects v2.0 installations
- `installer_migration.py` - Migrates v2.0 config to v2.1

### Need Update (Docstrings/Comments)
- `package_deployer.py`, `wrapper_generator.py`, `path_integration.py`, `generate_requirements.py`

### Need Major Update (Scripts)
- `uninstall_linux.sh`, `uninstall_macos.sh`, `uninstall_windows.ps1`

### Need Update (Templates)
- `templates/com.graphiti.bootstrap.plist`, `templates/graphiti-bootstrap.service`

### Need Review (Config/CLI)
- `unified_config.py`, `config_cli.py`, `session_tracking_cli.py`

---

## Environment

- Platform: Windows (win32/MINGW64)
- Python: 3.13.7
- Repository: graphiti
- Branch: sprint/per-user-daemon-v21

---

## Key Locations (v2.1)

- Install Dir: `%LOCALAPPDATA%\Programs\Graphiti` (Windows)
- Config Dir: `%LOCALAPPDATA%\Graphiti\config` (Windows)
- Logs: `%LOCALAPPDATA%\Graphiti\logs` (Windows)
- Lib: `%LOCALAPPDATA%\Programs\Graphiti\lib\{mcp_server,graphiti_core}/`

---

## Test Commands

```bash
# Run daemon tests
pytest tests/daemon/ -v

# Check for stale references
grep -r "~/.graphiti" mcp_server/daemon/

# Check v2.1 paths module
python -c "from mcp_server.daemon.paths import get_paths; print(get_paths())"
```

