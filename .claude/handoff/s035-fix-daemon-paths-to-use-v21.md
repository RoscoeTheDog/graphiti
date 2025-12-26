# Session Handoff: s035-fix-daemon-paths-to-use-v21

**Status**: ACTIVE
**Created**: 2025-12-26 00:32
**Sequence**: 035

---

## Objective

Fix daemon components to use v2.1 architecture paths instead of legacy v2.0 (~/.graphiti) locations.

---

## Completed

- Committed checkpoint with installer and test updates (34cfe95)
- Committed uninstall script fix to allow non-admin file cleanup (4534438)
- All 363 daemon tests passing (20 skipped Unix-specific on Windows)
- Added `_generate_requirements()` and `_find_repo_root()` methods to DaemonManager
- Updated WrapperGenerator to use `get_install_dir()` instead of `~/.graphiti/.venv`
- Updated PackageDeployer to deploy to `install_dir/lib/` instead of `~/.graphiti/mcp_server`
- Committed and pushed path fixes (f7a97e0)

---

## Blocked

- Old NSSM service was running from v2.0 installation (user killed it manually)
- v2.1 installation at `%LOCALAPPDATA%\Programs\Graphiti` needs testing

---

## Next Steps

1. Run `python -m mcp_server.daemon.manager install` to test full v2.1 install
2. Verify Task Scheduler task is created (not NSSM)
3. Verify MCP server starts and health check passes
4. Clean up old v2.0 artifacts at `~/.graphiti` if install succeeds
5. Run tests to ensure path changes don't break anything

---

## Decisions

- v2.1 architecture uses platform-specific paths:
  - Windows: `%LOCALAPPDATA%\Programs\Graphiti` (install_dir IS the venv)
  - macOS: `~/Library/Application Support/Graphiti`
  - Linux: `~/.local/share/graphiti`
- Frozen packages go to `install_dir/lib/` (not `~/.graphiti/mcp_server`)
- requirements.txt generated from pyproject.toml during install (not pre-existing)
- Task Scheduler replaces NSSM for Windows service management

---

## Files Modified

- `mcp_server/daemon/manager.py` - Added _generate_requirements(), _find_repo_root(), import generate_requirements
- `mcp_server/daemon/wrapper_generator.py` - Use get_install_dir() for default paths
- `mcp_server/daemon/package_deployer.py` - Deploy to install_dir/lib/
- `mcp_server/daemon/uninstall_windows.ps1` - Allow non-admin execution for file cleanup

---

## Environment

- Platform: Windows (win32)
- Python: 3.13.7
- Repository: graphiti
- Branch: sprint/per-user-daemon-v21
- Commits: 34cfe95, 4534438, f7a97e0
