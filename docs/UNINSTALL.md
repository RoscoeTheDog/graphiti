# Uninstalling Graphiti MCP Server

This guide covers how to completely remove the Graphiti MCP Bootstrap Service from your system.

## Table of Contents

- [Quick Uninstall](#quick-uninstall)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [What Gets Removed](#what-gets-removed)
- [What Gets Preserved](#what-gets-preserved)
- [Script Options](#script-options)
- [Manual Uninstall](#manual-uninstall)
- [Complete Removal](#complete-removal)
- [Troubleshooting](#troubleshooting)

---

## Quick Uninstall

### Windows

**Prerequisites**: Administrator rights required for service removal.

1. **Download the script** (if repository deleted):
   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/daemon/uninstall_windows.ps1" -OutFile "$env:TEMP\uninstall_graphiti.ps1"
   ```

2. **Run as Administrator**:
   ```powershell
   # Right-click PowerShell -> "Run as Administrator"
   cd path\to\graphiti\mcp_server\daemon
   .\uninstall_windows.ps1
   ```

   Or from download:
   ```powershell
   powershell -ExecutionPolicy Bypass -File "$env:TEMP\uninstall_graphiti.ps1"
   ```

3. **Follow prompts** to preserve or delete config/data

4. **Manual steps** (script will remind you):
   - Remove from Claude Desktop config: `%APPDATA%\Claude\claude_desktop_config.json`
   - Remove from PATH (if added): System Properties → Environment Variables

**Script flags**:
```powershell
# Skip prompts, preserve config/data
.\uninstall_windows.ps1 -Force

# Remove everything including config/data
.\uninstall_windows.ps1 -DeleteAll

# Preview without executing
.\uninstall_windows.ps1 -DryRun

# Show help
.\uninstall_windows.ps1 -Help
```

---

### macOS

1. **Download the script** (if repository deleted):
   ```bash
   curl -L https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/daemon/uninstall_macos.sh -o /tmp/uninstall_graphiti.sh
   chmod +x /tmp/uninstall_graphiti.sh
   ```

2. **Run the script**:
   ```bash
   cd path/to/graphiti/mcp_server/daemon
   ./uninstall_macos.sh
   ```

   Or from download:
   ```bash
   /tmp/uninstall_graphiti.sh
   ```

3. **Follow prompts** to preserve or delete config/data

4. **Manual steps** (script will remind you):
   - Remove from Claude Desktop config: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Remove from PATH: Edit `~/.zshrc` or `~/.bash_profile`

**Script flags**:
```bash
# Skip prompts, preserve config/data
./uninstall_macos.sh --force

# Remove everything including config/data
./uninstall_macos.sh --delete-all

# Preview without executing
./uninstall_macos.sh --dry-run

# Show help
./uninstall_macos.sh --help
```

---

### Linux

1. **Download the script** (if repository deleted):
   ```bash
   curl -L https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/daemon/uninstall_linux.sh -o /tmp/uninstall_graphiti.sh
   chmod +x /tmp/uninstall_graphiti.sh
   ```

2. **Run the script**:
   ```bash
   cd path/to/graphiti/mcp_server/daemon
   ./uninstall_linux.sh
   ```

   Or from download:
   ```bash
   /tmp/uninstall_graphiti.sh
   ```

3. **Follow prompts** to preserve or delete config/data

4. **Manual steps** (script will remind you):
   - Remove from Claude Desktop config: `~/.config/Claude/claude_desktop_config.json`
   - Remove from PATH: Edit `~/.bashrc` or `~/.zshrc`

**Script flags**:
```bash
# Skip prompts, preserve config/data
./uninstall_linux.sh --force

# Remove everything including config/data
./uninstall_linux.sh --delete-all

# Preview without executing
./uninstall_linux.sh --dry-run

# Show help
./uninstall_linux.sh --help
```

---

## What Gets Removed

The uninstall scripts **automatically remove**:

1. **OS Service**:
   - Windows: NSSM service `GraphitiBootstrap`
   - macOS: launchd agent `com.graphiti.bootstrap`
   - Linux: systemd user service `graphiti-bootstrap`

2. **Installation Directories**:
   - `~/.graphiti/.venv/` - Virtual environment
   - `~/.graphiti/mcp_server/` - Deployed package
   - `~/.graphiti/bin/` - Wrapper scripts
   - `~/.graphiti/logs/` - Service logs

3. **Empty Parent Directory**:
   - `~/.graphiti/` if no files remain after cleanup

---

## What Gets Preserved

By **default**, the scripts preserve:

1. **User Data**:
   - `~/.graphiti/data/` - Your graph database and episodes

2. **Configuration**:
   - `~/.graphiti/graphiti.config.json` - Your settings

To delete these as well, use the `--delete-all` (Unix) or `-DeleteAll` (Windows) flag.

---

## Script Options

### Common Flags (All Platforms)

| Flag | Windows | Unix | Description |
|------|---------|------|-------------|
| Help | `-Help` | `--help` | Show usage instructions |
| Force | `-Force` | `--force` | Skip prompts, preserve config/data |
| Delete All | `-DeleteAll` | `--delete-all` | Remove everything including config/data |
| Dry Run | `-DryRun` | `--dry-run` | Preview actions without executing |

### Interactive Mode (Default)

If you run the script without flags, it will:
1. Remove service and installation files automatically
2. **Prompt you** before deleting config/data
3. Provide manual removal instructions

### Automation Example

For CI/CD or scripted uninstalls:

```bash
# Unix: Preserve config/data
./uninstall_macos.sh --force

# Unix: Complete removal
./uninstall_linux.sh --delete-all

# Windows: Preserve config/data
powershell -File uninstall_windows.ps1 -Force

# Windows: Complete removal
powershell -File uninstall_windows.ps1 -DeleteAll
```

---

## Manual Uninstall

If the scripts fail or you prefer manual removal:

### Windows (Manual Steps)

1. **Stop and remove service**:
   ```powershell
   # Using NSSM (if installed)
   nssm stop GraphitiBootstrap
   nssm remove GraphitiBootstrap confirm

   # Or using sc.exe (if NSSM unavailable)
   sc.exe stop GraphitiBootstrap
   sc.exe delete GraphitiBootstrap
   ```

2. **Delete installation**:
   ```powershell
   Remove-Item -Recurse -Force "$env:USERPROFILE\.graphiti"
   ```

3. **Remove from Claude config**:
   - Open: `%APPDATA%\Claude\claude_desktop_config.json`
   - Remove the `graphiti` entry from `mcpServers`

4. **Remove from PATH** (if added):
   - System Properties → Environment Variables
   - Edit user PATH, remove: `C:\Users\<username>\.graphiti\bin`

### macOS (Manual Steps)

1. **Unload and remove service**:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
   rm ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
   ```

2. **Delete installation**:
   ```bash
   rm -rf ~/.graphiti
   ```

3. **Remove from Claude config**:
   - Open: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Remove the `graphiti` entry from `mcpServers`

4. **Remove from PATH** (if added):
   ```bash
   # Edit ~/.zshrc or ~/.bash_profile
   # Remove line: export PATH="$HOME/.graphiti/bin:$PATH"
   source ~/.zshrc  # or source ~/.bash_profile
   ```

### Linux (Manual Steps)

1. **Stop, disable, and remove service**:
   ```bash
   systemctl --user stop graphiti-bootstrap
   systemctl --user disable graphiti-bootstrap
   rm ~/.config/systemd/user/graphiti-bootstrap.service
   systemctl --user daemon-reload
   ```

2. **Delete installation**:
   ```bash
   rm -rf ~/.graphiti
   ```

3. **Remove from Claude config**:
   - Open: `~/.config/Claude/claude_desktop_config.json`
   - Remove the `graphiti` entry from `mcpServers`

4. **Remove from PATH** (if added):
   ```bash
   # Edit ~/.bashrc or ~/.zshrc
   # Remove line: export PATH="$HOME/.graphiti/bin:$PATH"
   source ~/.bashrc  # or source ~/.zshrc
   ```

---

## Complete Removal

To remove **all traces** of Graphiti (including data and config):

### Using Scripts

```bash
# Windows
.\uninstall_windows.ps1 -DeleteAll

# macOS
./uninstall_macos.sh --delete-all

# Linux
./uninstall_linux.sh --delete-all
```

### Manually

After following the manual steps above, also delete:

```bash
# All platforms (Unix)
rm -rf ~/.graphiti

# Windows
Remove-Item -Recurse -Force "$env:USERPROFILE\.graphiti"
```

Then remove from Claude config and PATH as described in manual steps.

---

## Troubleshooting

### "NSSM not found" (Windows)

**Problem**: Script can't find NSSM to remove service.

**Solution**:
1. Check if service exists: `sc.exe query GraphitiBootstrap`
2. If service exists, install NSSM:
   - Download from https://nssm.cc/
   - Or install via Chocolatey: `choco install nssm`
   - Or install via Scoop: `scoop install nssm`
3. Re-run uninstall script
4. If NSSM unavailable, use manual removal with `sc.exe` (see Manual Uninstall)

### "Permission denied" (Unix)

**Problem**: Script can't delete files or stop service.

**Solution**:
```bash
# Make script executable
chmod +x uninstall_macos.sh  # or uninstall_linux.sh

# Service operations don't need sudo (user services)
# File deletion shouldn't need sudo (files in ~/)
# If still failing, check file ownership:
ls -la ~/.graphiti
```

### Service Won't Stop

**Problem**: Service remains running after uninstall attempt.

**Solution**:

**Windows**:
```powershell
# Force kill process
Get-Process | Where-Object {$_.Name -like "*graphiti*"} | Stop-Process -Force
# Then remove service
nssm remove GraphitiBootstrap confirm
```

**macOS**:
```bash
# Force unload
launchctl bootout gui/$(id -u)/com.graphiti.bootstrap || true
rm ~/Library/LaunchAgents/com.graphiti.bootstrap.plist
```

**Linux**:
```bash
# Force stop
systemctl --user kill graphiti-bootstrap
systemctl --user reset-failed graphiti-bootstrap
systemctl --user disable graphiti-bootstrap
rm ~/.config/systemd/user/graphiti-bootstrap.service
systemctl --user daemon-reload
```

### Directory Not Empty

**Problem**: `~/.graphiti` won't delete because files remain.

**Solution**:
```bash
# See what's left
ls -la ~/.graphiti

# Delete specific files if safe
rm -rf ~/.graphiti/.venv
rm -rf ~/.graphiti/mcp_server
rm -rf ~/.graphiti/bin
rm -rf ~/.graphiti/logs

# Preserve only what you need:
# - ~/.graphiti/data/ (graph database)
# - ~/.graphiti/graphiti.config.json (config)
```

### Claude Desktop Still Shows Graphiti

**Problem**: Graphiti appears in Claude MCP servers after uninstall.

**Solution**:
1. **Remove from config**:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Edit the file** (JSON):
   ```json
   {
     "mcpServers": {
       "graphiti": {  ← DELETE THIS ENTIRE BLOCK
         "command": "...",
         "args": ["..."]
       }
     }
   }
   ```

3. **Restart Claude Desktop** completely (quit and reopen)

### Script Exits with "Administrator rights required" (Windows)

**Problem**: Script needs admin rights to remove service.

**Solution**:
1. Right-click PowerShell icon
2. Select "Run as Administrator"
3. Navigate to script location
4. Re-run script

---

## Support

If you encounter issues not covered here:

1. **Check logs** (if service still exists):
   - Windows: `%USERPROFILE%\.graphiti\logs\`
   - macOS: `~/.graphiti/logs/`
   - Linux: `journalctl --user -u graphiti-bootstrap` or `~/.graphiti/logs/`

2. **Open an issue**: https://github.com/getzep/graphiti/issues

3. **Include**:
   - Your OS and version
   - Error message (if any)
   - Output from uninstall script (run with `--dry-run` to preview)

---

## After Uninstall

To **reinstall** Graphiti later:

1. Follow the installation guide: [CLAUDE_INSTALL.md](../claude-mcp-installer/instance/CLAUDE_INSTALL.md)
2. Your old config/data will be preserved if you didn't use `--delete-all`

---

**Version**: 1.0.0
**Last Updated**: 2025-12-23
**Related**: [Installation Guide](../claude-mcp-installer/instance/CLAUDE_INSTALL.md), [README](../README.md)
