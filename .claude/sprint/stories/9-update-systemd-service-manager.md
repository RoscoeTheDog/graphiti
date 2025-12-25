# Story 9: Update SystemdServiceManager (Linux)

**Status**: unassigned
**Created**: 2025-12-25 02:02
**Phase**: 3 - Service Manager Updates

## Description

Update the SystemdServiceManager to use the new v2.1 installation paths for Linux, including proper PYTHONPATH configuration for frozen packages.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Review current systemd unit template
- [ ] Identify all path references that need updating
- [ ] Document Environment variable for PYTHONPATH
- [ ] Review XDG state directory for logs

### (i) Implementation Phase
- [ ] (P0) Update ExecStart to use `{INSTALL_DIR}/bin/python -m mcp_server.daemon.bootstrap`
- [ ] (P0) Update WorkingDirectory to `{INSTALL_DIR}`
- [ ] Add Environment="PYTHONPATH={INSTALL_DIR}/lib"
- [ ] Update StandardOutput/StandardError paths to XDG state dir
- [ ] Import and use paths.py for path resolution
- [ ] Update unit file template generation

### (t) Testing Phase
- [ ] (P0) Verify generated unit file has correct paths
- [ ] Verify Environment line sets PYTHONPATH correctly
- [ ] Verify log paths use XDG_STATE_HOME/graphiti/logs/

## Dependencies

- Story 1: Create Platform-Aware Path Resolution Module
- Story 2: Migrate Daemon Modules to New Path System

## Implementation Notes

Key unit file changes:
```ini
[Service]
ExecStart={INSTALL_DIR}/bin/python -m mcp_server.daemon.bootstrap
WorkingDirectory={INSTALL_DIR}
Environment="PYTHONPATH={INSTALL_DIR}/lib"
StandardOutput=append:{LOG_DIR}/bootstrap.log
StandardError=append:{LOG_DIR}/bootstrap.log
```
