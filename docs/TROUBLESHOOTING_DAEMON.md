# Troubleshooting Guide: Graphiti Daemon Architecture

This guide covers common issues with the Graphiti daemon architecture and their solutions.

> **Understanding the Architecture**: Before troubleshooting, it helps to understand how the daemon system works.
> See [DAEMON_ARCHITECTURE.md](DAEMON_ARCHITECTURE.md) for a complete overview of the virtual environment
> organization, bootstrap service, and multi-session support.

---

## Prerequisites

The Graphiti daemon uses an isolated virtual environment at `~/.graphiti/.venv/` (separate from any project venv). This design allows the daemon to run independently of where you clone the graphiti repository.

Run the automated installer:

```bash
# From the cloned repository root
cd graphiti
python mcp_server/daemon/installer.py

# This creates:
# - Isolated venv at ~/.graphiti/.venv/
# - CLI wrapper scripts at ~/.graphiti/bin/
# - Installs mcp_server package in the venv

# Add to PATH (see README.md for platform-specific instructions)
# Then verify CLI is available:
graphiti-mcp --help
```

> **Note:** The installer automatically handles venv creation, package installation, and CLI wrapper generation. Manual `pip install` is no longer required.

---

## Quick Diagnostics

Run these commands to quickly diagnose daemon issues:

```bash
# Check daemon service status
graphiti-mcp daemon status

# View recent logs
graphiti-mcp daemon logs

# Check if MCP server is responding
curl http://127.0.0.1:8321/health

# Check configuration
cat ~/.graphiti/graphiti.config.json | grep -A5 '"daemon"'
```

---

## Common Issues

### 0. "graphiti-mcp: command not found"

**Symptoms:**
- Running `graphiti-mcp daemon install` returns "command not found"
- CLI commands are not recognized

**Causes:**
1. Installer has not been run
2. PATH not configured correctly
3. Shell not reloaded after PATH update

**Solution:**
```bash
# 1. Run the installer if you haven't already
cd /path/to/graphiti
python mcp_server/daemon/installer.py

# 2. Add ~/.graphiti/bin to PATH (platform-specific)

# Windows (PowerShell):
$env:Path += ";$env:USERPROFILE\.graphiti\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")

# macOS/Linux (bash):
echo 'export PATH="$HOME/.graphiti/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# macOS/Linux (zsh):
echo 'export PATH="$HOME/.graphiti/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 3. Restart your shell/terminal

# 4. Verify CLI is available
graphiti-mcp --help
```

> **Note:** The CLI commands are wrapper scripts that invoke the venv Python without requiring activation. Make sure `~/.graphiti/bin/` is in your PATH.

---

### 0.1. Venv Creation Failed

**Symptoms:**
- Installer reports "VenvCreationError" or "IncompatiblePythonVersionError"
- `~/.graphiti/.venv/` directory is missing or incomplete

**Causes:**
1. Python version < 3.10
2. Insufficient disk space
3. Permission errors in `~/.graphiti/` directory
4. `uv` or `python -m venv` subprocess failure

**Solutions:**

**Python Version Too Old:**
```bash
# Check Python version
python --version

# If < 3.10, upgrade Python:
# Windows: Download from python.org
# macOS: brew install python@3.10
# Linux: sudo apt install python3.10
```

**Permission Errors:**
```bash
# Check permissions
ls -ld ~/.graphiti/

# Fix permissions (Unix)
chmod 755 ~/.graphiti/

# Windows: Check folder permissions in Properties
```

**Disk Space:**
```bash
# Check available space (need ~100MB for venv)
df -h ~/.graphiti/  # Unix
Get-PSDrive C | Select-Object Used,Free  # Windows
```

**Manual Venv Creation (Diagnostic):**
```bash
# Try creating venv manually to see detailed errors
python -m venv ~/.graphiti/.venv

# Or with uv (faster)
uv venv ~/.graphiti/.venv
```

---

### 0.2. CLI Commands Don't Work After Installation

**Symptoms:**
- `graphiti-mcp --help` works but commands fail
- Errors like "ModuleNotFoundError: No module named 'mcp_server'"

**Cause:**
Package installation into venv failed. The venv exists but the `mcp_server` package is missing.

**Solution:**
```bash
# Check if package is installed
~/.graphiti/.venv/Scripts/python.exe -m pip list | grep mcp-server  # Windows
~/.graphiti/.venv/bin/python -m pip list | grep mcp-server  # Unix

# If missing, reinstall:
cd /path/to/graphiti
~/.graphiti/.venv/Scripts/python.exe -m pip install ./mcp_server  # Windows
~/.graphiti/.venv/bin/python -m pip install ./mcp_server  # Unix

# Or re-run installer with force flag (if supported)
python mcp_server/daemon/installer.py --force
```

---

### 0.3. Service Fails to Start - Python Path Issues

**Symptoms:**
- `graphiti-mcp daemon status` shows "stopped" or "crashed"
- Daemon logs show "Python executable not found in venv"
- Service configuration references wrong Python path

**Cause:**
Service configuration was generated before venv was created, or venv was recreated at a different location.

**Solution:**
```bash
# 1. Check venv Python exists
ls ~/.graphiti/.venv/Scripts/python.exe  # Windows
ls ~/.graphiti/.venv/bin/python  # Unix

# 2. If missing, recreate venv
rm -rf ~/.graphiti/.venv/
python mcp_server/daemon/installer.py

# 3. Reinstall daemon service (regenerates service config with correct paths)
graphiti-mcp daemon uninstall
graphiti-mcp daemon install

# 4. Check service status
graphiti-mcp daemon status
```

---

### 1. "Connection refused" Error in Claude Code

**Symptoms:**
- Claude Code shows "Connection refused" when trying to use Graphiti tools
- MCP tools are not available in Claude Code

**Causes:**
1. Daemon service not installed
2. MCP server disabled in config (`daemon.enabled: false`)
3. Daemon service crashed or stopped

**Solutions:**

**Step 1: Check if daemon service is installed**
```bash
graphiti-mcp daemon status
```

If output shows "not installed" or "service not found":
```bash
# Install daemon service
graphiti-mcp daemon install
```

**Step 2: Check if MCP server is enabled**
```bash
# Edit config to enable daemon
# ~/.graphiti/graphiti.config.json:
{
  "daemon": {
    "enabled": true
  }
}
```

Wait 5 seconds for changes to take effect (default config watch interval).

**Step 3: Verify server is running**
```bash
# Test HTTP endpoint
curl http://127.0.0.1:8321/health

# Expected response:
{"status": "ok"}
```

**Step 4: Check Claude Code MCP settings**

Verify `~/.claude/settings.json` has HTTP transport configured:
```json
{
  "mcpServers": {
    "graphiti": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-everything",
        "http://127.0.0.1:8321"
      ],
      "transport": "sse"
    }
  }
}
```

**Common mistakes:**
- `transport: "stdio"` instead of `"sse"` - Won't connect to daemon
- Missing `http://127.0.0.1:8321` in args - Wrong endpoint
- Using `python -m mcp_server...` command - That's for stdio, not HTTP

---

### 2. Config Changes Not Taking Effect

**Symptoms:**
- Edited `graphiti.config.json` but daemon still disabled
- Changed port but server still on old port

**Cause:**
- Config watch interval delay (default 5 seconds)
- Syntax error in config JSON

**Solutions:**

**Step 1: Wait for config watcher**
- Default interval: 5 seconds
- Wait at least 5 seconds after saving config

**Step 2: Check config syntax**
```bash
# Validate JSON syntax
python -m json.tool ~/.graphiti/graphiti.config.json > /dev/null

# If errors, fix JSON syntax
```

**Step 3: Check logs for config errors**
```bash
graphiti-mcp daemon logs
```

Look for:
- "Config validation error"
- "Failed to parse config"
- "Invalid daemon configuration"

**Step 4: Force config reload**

On Windows:
```bash
# Restart service to reload config immediately
sc stop GraphitiBootstrap
sc start GraphitiBootstrap
```

On macOS:
```bash
launchctl stop com.graphiti.bootstrap
launchctl start com.graphiti.bootstrap
```

On Linux:
```bash
sudo systemctl restart graphiti-bootstrap
```

---

### 3. Daemon Service Won't Start

**Symptoms:**
- `graphiti-mcp daemon status` shows "stopped" or "failed"
- Service starts but immediately stops

**Common Causes:**

#### A. Python not in PATH

**Check:**
```bash
which python
python --version
```

**Fix (Windows):**
```bash
# Find Python installation
where python

# Add to system PATH in Environment Variables
# Or specify full path in service config
```

**Fix (macOS/Linux):**
```bash
# Find Python installation
which python3

# Update service config to use full path
# See: ~/.graphiti/daemon/graphiti-bootstrap.plist (macOS)
# Or: /etc/systemd/system/graphiti-bootstrap.service (Linux)
```

#### B. Permission Denied

**Check logs:**
```bash
graphiti-mcp daemon logs
```

Look for "Permission denied" errors.

**Fix (Windows):**
```bash
# Run install with admin privileges
# Right-click Command Prompt -> "Run as administrator"
graphiti-mcp daemon install
```

**Fix (macOS/Linux):**
```bash
# Ensure user has permission for ~/.graphiti/
chmod 755 ~/.graphiti
chmod 644 ~/.graphiti/graphiti.config.json

# On Linux, check SELinux/AppArmor policies
```

#### C. Port Already in Use

**Check:**
```bash
# Windows
netstat -ano | findstr :8321

# macOS/Linux
lsof -i :8321
```

**Fix:**
```bash
# Option 1: Kill process using port 8321
# Windows
taskkill /PID <PID> /F

# macOS/Linux
kill -9 <PID>

# Option 2: Use different port
# Edit ~/.graphiti/graphiti.config.json:
{
  "daemon": {
    "enabled": true,
    "port": 9999
  }
}

# Update Claude Code settings to match new port
```

#### D. Missing Dependencies

**Check logs:**
```bash
graphiti-mcp daemon logs
```

Look for "ModuleNotFoundError" or "ImportError".

**Fix:**
```bash
# Reinstall Graphiti with all dependencies
pip install --upgrade graphiti-core[all]

# Or specific backend
pip install --upgrade graphiti-core[neo4j]
```

---

### 4. Multiple Claude Code Sessions Conflict

**Symptoms:**
- Second Claude Code window shows stale data
- Changes in one window don't appear in another

**Expected Behavior:**
- Daemon architecture supports multiple clients simultaneously
- All clients should see the same shared state

**If conflicts occur:**

**Step 1: Verify all sessions use HTTP transport**
```bash
# Check ~/.claude/settings.json on each machine
# Should have:
"transport": "sse"
# NOT:
"transport": "stdio"
```

**Step 2: Restart all Claude Code sessions**
- Close all Claude Code windows
- Restart Claude Code
- Check that MCP tools work in all windows

**Step 3: Check server logs for errors**
```bash
graphiti-mcp daemon logs
```

Look for connection errors or state inconsistencies.

---

### 5. Daemon Service Not Auto-Starting on Boot

**Symptoms:**
- After reboot, daemon is not running
- Must manually start daemon each boot

**Platform-Specific Solutions:**

#### Windows

**Check service installation:**
```bash
# Check if service exists
sc query GraphitiBootstrap
```

**Fix:**
```bash
# Reinstall service with auto-start
graphiti-mcp daemon uninstall
graphiti-mcp daemon install

# Verify auto-start is enabled
sc qc GraphitiBootstrap
# Should show: START_TYPE: AUTO_START
```

#### macOS

**Check launchd configuration:**
```bash
# Check if plist exists
ls ~/Library/LaunchAgents/com.graphiti.bootstrap.plist

# Check if loaded
launchctl list | grep graphiti
```

**Fix:**
```bash
# Reload launchd config
launchctl unload ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
launchctl load ~/Library/LaunchAgents/com.graphiti.bootstrap.plist

# Verify RunAtLoad is true
cat ~/Library/LaunchAgents/com.graphiti.bootstrap.plist | grep RunAtLoad
```

#### Linux

**Check systemd configuration:**
```bash
# Check if unit exists
systemctl status graphiti-bootstrap

# Check if enabled
systemctl is-enabled graphiti-bootstrap
```

**Fix:**
```bash
# Enable auto-start
sudo systemctl enable graphiti-bootstrap

# Start now
sudo systemctl start graphiti-bootstrap
```

---

### 6. High Memory Usage

**Symptoms:**
- Daemon uses more RAM than expected
- System becomes slow when daemon is running

**Expected Usage:**
- Bootstrap service: ~5MB RAM
- MCP server (enabled): ~100MB RAM
- Total: ~105MB RAM

**If usage is higher:**

**Step 1: Check for memory leaks**
```bash
# Monitor memory over time
# Windows
tasklist /FI "IMAGENAME eq python.exe" /FO TABLE

# macOS/Linux
ps aux | grep python | grep graphiti
```

**Step 2: Check Neo4j connection pool**

Edit `~/.graphiti/graphiti.config.json`:
```json
{
  "database": {
    "max_connection_pool_size": 10
  }
}
```

Reduce `max_connection_pool_size` if many sessions are idle.

**Step 3: Check for zombie processes**
```bash
# Kill orphaned MCP server processes
# Windows
taskkill /F /IM python.exe /FI "WINDOWTITLE eq graphiti*"

# macOS/Linux
pkill -f "graphiti_mcp_server"

# Restart daemon
graphiti-mcp daemon status
```

---

### 7. CLI Commands Don't Work

**Symptoms:**
- `graphiti-mcp daemon ...` commands fail
- "Command not found" error

**Cause:**
- `graphiti-mcp` not in PATH
- Virtual environment not activated

**Solutions:**

**Step 1: Check if graphiti-mcp is installed**
```bash
which graphiti-mcp
# or on Windows:
where graphiti-mcp
```

**Step 2: Reinstall if missing**
```bash
pip install --force-reinstall graphiti-core
```

**Step 3: Add to PATH (if needed)**

**Windows:**
```bash
# Find installation directory
where python
# Add Python Scripts directory to PATH
# Typically: C:\Users\<USER>\AppData\Local\Programs\Python\Python3X\Scripts
```

**macOS/Linux:**
```bash
# Find installation directory
which python

# Add to PATH in ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc
```

---

### 8. Logs Show No Errors But Daemon Won't Work

**Symptoms:**
- `graphiti-mcp daemon logs` shows no errors
- `graphiti-mcp daemon status` says "running"
- But Claude Code can't connect

**Diagnostic Steps:**

**Step 1: Test HTTP endpoint directly**
```bash
# Test health endpoint
curl -v http://127.0.0.1:8321/health

# Test API endpoint
curl -v http://127.0.0.1:8321/api/status
```

Expected responses:
```json
// /health
{"status": "ok"}

// /api/status
{"uptime_seconds": 123, "version": "1.1.0", ...}
```

**Step 2: Check firewall**

**Windows:**
```bash
# Check if port is blocked
netsh advfirewall firewall show rule name=all | findstr 8321

# Add firewall rule if needed
netsh advfirewall firewall add rule name="Graphiti MCP" dir=in action=allow protocol=TCP localport=8321
```

**macOS:**
```bash
# Check firewall status
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# If enabled, add exception for Python
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
```

**Linux:**
```bash
# Check if iptables is blocking
sudo iptables -L -n | grep 8321

# If blocked, allow localhost connections
sudo iptables -I INPUT -p tcp -s 127.0.0.1 --dport 8321 -j ACCEPT
```

**Step 3: Check if bound to wrong interface**
```bash
# Windows
netstat -ano | findstr :8321

# macOS/Linux
lsof -i :8321
```

Should show `127.0.0.1:8321`, not `0.0.0.0:8321` or another IP.

If wrong, edit config:
```json
{
  "daemon": {
    "enabled": true,
    "host": "127.0.0.1"
  }
}
```

---

## Platform-Specific Issues

### Windows

**Issue: NSSM not found**

**Solution:**
```bash
# NSSM is bundled with Graphiti, but if missing:
# Download from: https://nssm.cc/download
# Extract to: C:\Windows\System32\nssm.exe
```

**Issue: Service shows "Error 1053" (timeout)**

**Solution:**
```bash
# Increase service timeout
sc config GraphitiBootstrap start= delayed-auto

# Or edit service timeout in registry:
# HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\ServicesPipeTimeout
```

### macOS

**Issue: "Operation not permitted" error**

**Solution:**
```bash
# Grant Full Disk Access to Terminal app
# System Preferences > Security & Privacy > Privacy > Full Disk Access
# Add Terminal.app or iTerm.app

# Then reinstall daemon
graphiti-mcp daemon uninstall
graphiti-mcp daemon install
```

**Issue: plist not loading**

**Solution:**
```bash
# Check plist syntax
plutil -lint ~/Library/LaunchAgents/com.graphiti.bootstrap.plist

# Fix permissions
chmod 644 ~/Library/LaunchAgents/com.graphiti.bootstrap.plist

# Reload
launchctl unload ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
launchctl load ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
```

### Linux

**Issue: systemd unit not found**

**Solution:**
```bash
# Check if systemd is running
systemctl --version

# If user service, check correct location
ls ~/.config/systemd/user/graphiti-bootstrap.service

# Reload systemd
systemctl --user daemon-reload
systemctl --user enable graphiti-bootstrap
systemctl --user start graphiti-bootstrap
```

**Issue: "Failed to connect to bus" error**

**Solution:**
```bash
# Set XDG_RUNTIME_DIR if missing
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Or use system service instead of user service
sudo cp ~/.config/systemd/user/graphiti-bootstrap.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable graphiti-bootstrap
sudo systemctl start graphiti-bootstrap
```

---

## Advanced Debugging

### Enable Debug Logging

Edit `~/.graphiti/graphiti.config.json`:
```json
{
  "logging": {
    "level": "DEBUG",
    "format": "detailed"
  },
  "daemon": {
    "log_file": "~/.graphiti/daemon-debug.log"
  }
}
```

Then check logs:
```bash
tail -f ~/.graphiti/daemon-debug.log
```

### Capture Network Traffic

```bash
# macOS/Linux
sudo tcpdump -i lo0 -A 'tcp port 8321'

# Windows (requires Wireshark)
# Filter: tcp.port == 8321
```

### Test with Python Client

```python
from mcp_server.api.client import GraphitiClient

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test connection
client = GraphitiClient(base_url="http://127.0.0.1:8321")
print(f"Health check: {client.health_check()}")
print(f"Status: {client.get_status()}")
```

---

## Getting Help

If none of these solutions work:

1. **Collect diagnostic information:**
   ```bash
   # Save to file for sharing
   graphiti-mcp daemon status > debug-info.txt
   graphiti-mcp daemon logs >> debug-info.txt
   cat ~/.graphiti/graphiti.config.json >> debug-info.txt
   ```

2. **Check existing issues:**
   - [GitHub Issues](https://github.com/getzep/graphiti/issues)

3. **Report a bug:**
   - Include diagnostic information
   - Specify OS and version
   - Include steps to reproduce

---

## Related Documentation

- [DAEMON_ARCHITECTURE.md](DAEMON_ARCHITECTURE.md) - Complete daemon architecture (venv organization, bootstrap service)
- [CONFIGURATION.md - Daemon Configuration](../CONFIGURATION.md#daemon-configuration)
- [README.md - Daemon Setup](../README.md#daemon-architecture-recommended)
- [MCP_TOOLS.md - Transport Options](MCP_TOOLS.md#transport-options)
