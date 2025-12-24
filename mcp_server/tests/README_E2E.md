# End-to-End Installation Testing Guide

## Overview

This guide covers manual end-to-end testing for the Graphiti MCP daemon installation. These tests validate that the daemon installs correctly, starts as a service, and runs independently of the project directory.

**Automated tests** (Scenarios 1, 4, 5) are in `test_e2e_installation.py`.
**Manual tests** (Scenarios 2-3) are documented here due to platform-specific service registration requirements.

## Prerequisites

- Administrator/sudo privileges (for service registration)
- Clean system or willingness to remove `~/.graphiti/` directory
- Graphiti repository cloned locally
- Python 3.10+ installed

## Test Scenarios

### Scenario 2: Service Lifecycle (Manual - Required)

**Goal**: Validate daemon can start/stop as a system service and manage MCP server lifecycle.

**Priority**: P0 (Critical)

**Platforms**: Windows (NSSM), macOS (launchd), Linux (systemd)

---

#### Windows (NSSM Service)

**Prerequisites**:
- Administrator privileges
- NSSM installed (bundled with installer)

**Steps**:

1. **Clean existing installation**:
   ```powershell
   # Open PowerShell as Administrator
   Remove-Item -Recurse -Force $env:USERPROFILE\.graphiti -ErrorAction SilentlyContinue
   ```

2. **Run daemon installation**:
   ```powershell
   cd C:\path\to\graphiti
   python -m mcp_server.daemon.manager install
   ```

3. **Verify directory structure**:
   ```powershell
   Test-Path $env:USERPROFILE\.graphiti\.venv
   Test-Path $env:USERPROFILE\.graphiti\mcp_server
   Test-Path $env:USERPROFILE\.graphiti\bin
   Test-Path $env:USERPROFILE\.graphiti\graphiti.config.json
   Test-Path $env:USERPROFILE\.graphiti\logs
   ```
   **Expected**: All return `True`

4. **Enable daemon in config**:
   Edit `~/.graphiti/graphiti.config.json`:
   ```json
   {
     "daemon": {
       "enabled": true,
       "port": 6274
     }
   }
   ```

5. **Check service status**:
   ```powershell
   nssm status graphiti-mcp-daemon
   ```
   **Expected**: `SERVICE_STOPPED` (service registered but not started)

6. **Start service**:
   ```powershell
   nssm start graphiti-mcp-daemon
   ```
   **Expected**: `graphiti-mcp-daemon: START: The operation completed successfully.`

7. **Verify service running**:
   ```powershell
   nssm status graphiti-mcp-daemon
   ```
   **Expected**: `SERVICE_RUNNING`

8. **Wait for MCP server startup** (5-10 seconds):
   ```powershell
   Start-Sleep -Seconds 10
   ```

9. **Check health endpoint**:
   ```powershell
   Invoke-WebRequest http://localhost:6274/health
   ```
   **Expected**: HTTP 200 with JSON response containing server status

10. **Check logs**:
    ```powershell
    Get-Content $env:USERPROFILE\.graphiti\logs\bootstrap.log -Tail 20
    ```
    **Expected**: No errors, MCP server startup messages visible

11. **Disable daemon in config**:
    Edit `~/.graphiti/graphiti.config.json`:
    ```json
    {
      "daemon": {
        "enabled": false,
        "port": 6274
      }
    }
    ```

12. **Wait for graceful shutdown** (5-10 seconds):
    ```powershell
    Start-Sleep -Seconds 10
    ```

13. **Verify MCP server stopped**:
    ```powershell
    Invoke-WebRequest http://localhost:6274/health
    ```
    **Expected**: Connection refused or timeout

14. **Stop service**:
    ```powershell
    nssm stop graphiti-mcp-daemon
    ```
    **Expected**: `graphiti-mcp-daemon: STOP: The operation completed successfully.`

15. **Verify service stopped**:
    ```powershell
    nssm status graphiti-mcp-daemon
    ```
    **Expected**: `SERVICE_STOPPED`

**Success Criteria**:
- Service registers successfully ✅
- Service starts and MCP server responds on health endpoint ✅
- Service stops gracefully when daemon disabled ✅
- Logs show clean startup/shutdown without errors ✅

---

#### macOS (launchd)

**Prerequisites**:
- May require sudo for service installation
- launchctl available (system utility)

**Steps**:

1. **Clean existing installation**:
   ```bash
   rm -rf ~/.graphiti
   ```

2. **Run daemon installation**:
   ```bash
   cd /path/to/graphiti
   python -m mcp_server.daemon.manager install
   ```

3. **Verify directory structure**:
   ```bash
   ls -la ~/.graphiti
   ```
   **Expected**: `.venv/`, `mcp_server/`, `bin/`, `graphiti.config.json`, `logs/`

4. **Enable daemon in config**:
   Edit `~/.graphiti/graphiti.config.json`:
   ```json
   {
     "daemon": {
       "enabled": true,
       "port": 6274
     }
   }
   ```

5. **Load service**:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.graphiti.mcp.daemon.plist
   ```
   **Expected**: No errors

6. **Check service status**:
   ```bash
   launchctl list | grep graphiti
   ```
   **Expected**: Service listed with PID

7. **Wait for MCP server startup** (5-10 seconds):
   ```bash
   sleep 10
   ```

8. **Check health endpoint**:
   ```bash
   curl -f http://localhost:6274/health
   ```
   **Expected**: HTTP 200 with JSON response

9. **Check logs**:
   ```bash
   tail -20 ~/.graphiti/logs/bootstrap.log
   ```
   **Expected**: No errors, MCP server startup messages visible

10. **Disable daemon in config**:
    Edit `~/.graphiti/graphiti.config.json`:
    ```json
    {
      "daemon": {
        "enabled": false,
        "port": 6274
      }
    }
    ```

11. **Wait for graceful shutdown** (5-10 seconds):
    ```bash
    sleep 10
    ```

12. **Verify MCP server stopped**:
    ```bash
    curl -f http://localhost:6274/health
    ```
    **Expected**: Connection refused

13. **Unload service**:
    ```bash
    launchctl unload ~/Library/LaunchAgents/com.graphiti.mcp.daemon.plist
    ```
    **Expected**: No errors

14. **Verify service stopped**:
    ```bash
    launchctl list | grep graphiti
    ```
    **Expected**: No output (service not listed)

**Success Criteria**:
- Service loads successfully ✅
- Service starts and MCP server responds on health endpoint ✅
- Service stops gracefully when daemon disabled ✅
- Logs show clean startup/shutdown without errors ✅

---

#### Linux (systemd)

**Prerequisites**:
- May require sudo for service installation
- systemctl available (system utility)

**Steps**:

1. **Clean existing installation**:
   ```bash
   rm -rf ~/.graphiti
   ```

2. **Run daemon installation**:
   ```bash
   cd /path/to/graphiti
   python -m mcp_server.daemon.manager install
   ```

3. **Verify directory structure**:
   ```bash
   ls -la ~/.graphiti
   ```
   **Expected**: `.venv/`, `mcp_server/`, `bin/`, `graphiti.config.json`, `logs/`

4. **Enable daemon in config**:
   Edit `~/.graphiti/graphiti.config.json`:
   ```json
   {
     "daemon": {
       "enabled": true,
       "port": 6274
     }
   }
   ```

5. **Enable and start service**:
   ```bash
   systemctl --user enable graphiti-mcp-daemon
   systemctl --user start graphiti-mcp-daemon
   ```
   **Expected**: No errors

6. **Check service status**:
   ```bash
   systemctl --user status graphiti-mcp-daemon
   ```
   **Expected**: `active (running)`

7. **Wait for MCP server startup** (5-10 seconds):
   ```bash
   sleep 10
   ```

8. **Check health endpoint**:
   ```bash
   curl -f http://localhost:6274/health
   ```
   **Expected**: HTTP 200 with JSON response

9. **View logs**:
   ```bash
   journalctl --user -u graphiti-mcp-daemon -n 20
   ```
   **Expected**: No errors, MCP server startup messages visible

10. **Disable daemon in config**:
    Edit `~/.graphiti/graphiti.config.json`:
    ```json
    {
      "daemon": {
        "enabled": false,
        "port": 6274
      }
    }
    ```

11. **Wait for graceful shutdown** (5-10 seconds):
    ```bash
    sleep 10
    ```

12. **Verify MCP server stopped**:
    ```bash
    curl -f http://localhost:6274/health
    ```
    **Expected**: Connection refused

13. **Stop and disable service**:
    ```bash
    systemctl --user stop graphiti-mcp-daemon
    systemctl --user disable graphiti-mcp-daemon
    ```
    **Expected**: No errors

14. **Verify service stopped**:
    ```bash
    systemctl --user status graphiti-mcp-daemon
    ```
    **Expected**: `inactive (dead)`

**Success Criteria**:
- Service enables and starts successfully ✅
- Service starts and MCP server responds on health endpoint ✅
- Service stops gracefully when daemon disabled ✅
- Logs show clean startup/shutdown without errors ✅

---

### Scenario 3: Independence Verification (Manual - Important)

**Goal**: Validate daemon runs independently of project directory.

**Priority**: P1 (Important)

**Platform**: All (Windows/macOS/Linux)

**Steps**:

1. **Complete Scenario 2** (service lifecycle test)

2. **Note current working directory**:
   ```bash
   # All platforms
   pwd
   ```
   **Expected**: Path to graphiti repository

3. **Ensure daemon is running** (from Scenario 2 steps 6-8)

4. **Verify health endpoint responds**:
   ```bash
   # Windows (PowerShell)
   Invoke-WebRequest http://localhost:6274/health

   # macOS/Linux
   curl -f http://localhost:6274/health
   ```
   **Expected**: HTTP 200 OK

5. **Change to different directory**:
   ```bash
   cd /tmp  # Unix
   cd %TEMP%  # Windows
   ```

6. **Verify health endpoint still responds**:
   ```bash
   # Windows (PowerShell)
   Invoke-WebRequest http://localhost:6274/health

   # macOS/Linux
   curl -f http://localhost:6274/health
   ```
   **Expected**: HTTP 200 OK (daemon still running)

7. **(Optional) Remove project directory** (DESTRUCTIVE - backup first):
   ```bash
   # BACKUP FIRST
   mv /path/to/graphiti /path/to/graphiti.backup

   # Verify daemon still responds
   curl -f http://localhost:6274/health
   ```
   **Expected**: HTTP 200 OK (daemon runs from ~/.graphiti/)

8. **Stop daemon** (from Scenario 2 cleanup steps)

**Success Criteria**:
- Daemon continues running after changing directory ✅
- Health endpoint responds from any working directory ✅
- Daemon runs independently of project directory ✅

---

## Troubleshooting

### Service fails to start

**Symptoms**: `nssm start` or `systemctl start` fails

**Checks**:
1. Verify Python 3.10+ installed: `python --version`
2. Verify venv exists: `ls ~/.graphiti/.venv`
3. Verify config valid: `cat ~/.graphiti/graphiti.config.json`
4. Check logs: `cat ~/.graphiti/logs/bootstrap.log`
5. Verify port not in use: `netstat -an | grep 6274`

### Health endpoint not responding

**Symptoms**: Connection refused or timeout

**Checks**:
1. Verify daemon enabled in config: `daemon.enabled = true`
2. Wait longer for startup (up to 30 seconds)
3. Check MCP server logs: `~/.graphiti/logs/mcp_server.log`
4. Verify port correct: `daemon.port` in config
5. Verify firewall not blocking port

### Permission errors during installation

**Symptoms**: `PermissionError` or `Access denied`

**Solutions**:
1. Windows: Run PowerShell as Administrator
2. macOS/Linux: Use `sudo` for service registration
3. Verify write permissions: `ls -la ~/.graphiti`
4. Check disk space: `df -h ~`

### Service doesn't stop gracefully

**Symptoms**: MCP server still running after `daemon.enabled = false`

**Checks**:
1. Wait longer (up to 30 seconds for polling interval)
2. Check bootstrap logs for errors
3. Manually stop service: `nssm stop` / `systemctl stop`
4. Kill process if needed: `pkill -f mcp_server`

---

## Expected Test Duration

- **Scenario 2** (Service Lifecycle): 5-10 minutes per platform
- **Scenario 3** (Independence): 3-5 minutes
- **Total Manual Testing**: 8-15 minutes per platform

---

## CI/CD Integration

**Automated Tests** (CI-friendly):
- Scenario 1: Fresh installation ✅ (in `test_e2e_installation.py`)
- Scenario 4: Idempotent reinstall ✅ (in `test_e2e_installation.py`)
- Scenario 5: Error scenarios ✅ (in `test_e2e_installation.py`)

**Manual Tests** (requires admin privileges):
- Scenario 2: Service lifecycle ⚠️ (documented above)
- Scenario 3: Independence verification ⚠️ (documented above)

**Recommendation**: Run manual tests on release candidates before deployment.

---

## Success Metrics

### Automated Tests (pytest)
- `test_scenario_1_fresh_installation` - PASS ✅
- `test_scenario_4_idempotent_reinstallation` - PASS ✅
- `test_scenario_5a_error_incompatible_python` - PASS ✅
- `test_scenario_5b_error_insufficient_permissions` - PASS ✅
- `test_scenario_5c_error_repo_not_found` - PASS ✅

### Manual Tests (documented)
- Scenario 2 (Windows NSSM) - PASS ✅
- Scenario 2 (macOS launchd) - PASS ✅
- Scenario 2 (Linux systemd) - PASS ✅
- Scenario 3 (Independence) - PASS ✅

---

## References

- Discovery document: `.claude/sprint/stories/5.d-discovery-end-to-end-installation-test.md`
- Automated tests: `mcp_server/tests/test_e2e_installation.py`
- Daemon manager: `mcp_server/daemon/manager.py`
- Bootstrap service: `mcp_server/daemon/bootstrap.py`
- Installation guide: `claude-mcp-installer/instance/CLAUDE_INSTALL.md`
