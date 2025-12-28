# Session Handoff: s036-fix-daemon-v21-deployment-add-graphiti

**Status**: ACTIVE
**Created**: 2025-12-26 01:06
**Sequence**: 036

---

## Objective

Fix daemon v2.1 deployment to include graphiti_core freezing and add fastapi dependency for HTTP transport.

---

## Completed

- Fixed Unicode encoding issues: Replaced Unicode symbols (checkmark, x, warning) with ASCII equivalents ([OK], [ERROR], [WARN]) in task_scheduler_service.py, installer.py, launchd_service.py, manager.py, systemd_service.py, v2_cleanup.py, windows_service.py
- Updated PackageDeployer to deploy both mcp_server AND graphiti_core to lib/ directory
- Added `_get_repo_root()` method to find repository root containing both packages
- Added `_get_graphiti_core_path()` method for graphiti_core location
- Updated `_deploy_single_package()` helper method for deploying packages
- Updated `verify_deployment()` to check for both mcp_server/ and graphiti_core/ in lib/
- Updated bootstrap.py `_get_mcp_server_path()` to look in `lib/mcp_server/` instead of root
- Successfully deployed both packages to `%LOCALAPPDATA%\Programs\Graphiti\lib\{mcp_server,graphiti_core}/`
- Verified Task Scheduler task is created and running

---

## Blocked

- MCP server fails to start with HTTP transport: `fastapi` module not found
- Need to add `fastapi` and potentially `uvicorn` to GRAPHITI_CORE_DEPS in generate_requirements.py
- SessionManager signature mismatch: `keep_length_days` parameter no longer exists (non-blocking, server continues without session tracking)

---

## Next Steps

1. Add `fastapi>=0.115.0` to GRAPHITI_CORE_DEPS in `mcp_server/daemon/generate_requirements.py`
2. Reinstall to pick up new dependency
3. Verify MCP server starts with HTTP transport on port 8321
4. Run daemon tests to ensure changes don't break anything
5. Fix SessionManager signature mismatch in graphiti_mcp_server.py (remove keep_length_days)
6. Clean up old v2.0 artifacts at ~/.graphiti if install succeeds
7. Commit all changes

---

## Decisions

- Deployment structure: Both mcp_server/ and graphiti_core/ deployed to lib/ subdirectory
- Frozen packages in lib/ added to sys.path by bootstrap's _setup_frozen_path()
- ASCII symbols used for Windows console compatibility (no Unicode in print statements)

---

## Errors Resolved

- UnicodeEncodeError with Unicode symbols on Windows cp1252 console - Replaced with [OK]/[ERROR]/[WARN]
- ModuleNotFoundError: graphiti_core - Updated PackageDeployer to deploy graphiti_core alongside mcp_server

---

## Files Modified

- `mcp_server/daemon/task_scheduler_service.py` - ASCII symbols
- `mcp_server/daemon/installer.py` - ASCII symbols
- `mcp_server/daemon/launchd_service.py` - ASCII symbols
- `mcp_server/daemon/manager.py` - ASCII symbols
- `mcp_server/daemon/systemd_service.py` - ASCII symbols
- `mcp_server/daemon/v2_cleanup.py` - ASCII symbols
- `mcp_server/daemon/windows_service.py` - ASCII symbols
- `mcp_server/daemon/package_deployer.py` - Major refactor for graphiti_core deployment
- `mcp_server/daemon/bootstrap.py` - Updated deployed path to lib/mcp_server/

---

## Environment

- Platform: Windows (win32)
- Python: 3.13.7
- Repository: graphiti
- Branch: sprint/per-user-daemon-v21
