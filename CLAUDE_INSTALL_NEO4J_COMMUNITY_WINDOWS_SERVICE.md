# CLAUDE_INSTALL_NEO4J_COMMUNITY_WINDOWS_SERVICE.md

> **For AI Agents**: This is a living document that instructs how to set up Neo4j Community Edition as a Windows Service for local Graphiti development.
> After making changes to the installation process, you MUST:
> 1. Update this document to reflect the new state
> 2. Add an entry to `CLAUDE_CHANGELOG.md` documenting what changed and why
> 3. Verify the changes work before updating documentation
> 4. Maintain the bidirectional relationship between this document and `CLAUDE_CHANGELOG.md`
> 5. **⚠️ SECURITY**: NEVER commit real credentials. Always use placeholders in examples: `your-password`, `your_username`, etc.
> 6. **🔗 TROUBLESHOOTING**: See `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md` for detailed issue documentation

## Document Purpose

This document provides step-by-step instructions for setting up **Neo4j Community Edition as a Windows Service** for local Graphiti development. This is a **free, local alternative** to Neo4j Aura (cloud) that runs in the background without occupying a terminal.

### Why Neo4j Community Edition (Local)?

**✅ Advantages**:
- **Free** - No monthly cost ($0 vs $65/month for Neo4j Aura)
- **Fast** - No network latency, runs on localhost
- **Private** - Data stays on your machine
- **Offline** - Works without internet connection
- **Full control** - Complete access to all Neo4j features

**⚠️ Considerations**:
- **Local only** - Not accessible from other machines (unless you configure networking)
- **Manual setup** - Requires installation and configuration (vs Aura's zero setup)
- **Single machine** - Data doesn't sync across VMs/machines automatically
- **Maintenance** - You handle backups and updates

**When to use this vs Neo4j Aura**:
- Use **Community Edition** for: Development, testing, cost-sensitive projects, privacy-critical data
- Use **Neo4j Aura** for: Multi-machine access, zero setup, managed backups, production workloads

See `CLAUDE_INSTALL_NEO4J_AURA.md` for cloud setup instructions.

## System Requirements

### Tested Platforms
- ✅ **Windows 10/11** (MSYS_NT-10.0-26100) - Primary platform, fully tested
- ⚠️ **macOS** - Not yet verified (use Neo4j Desktop or Docker)
- ⚠️ **Linux** - Not yet verified (use apt/yum packages or Docker)

**Note**: This guide is **Windows-specific**. For other platforms, see Neo4j documentation or use Neo4j Desktop.

### Prerequisites

1. **Java 21** (required by Neo4j Community 2025.09.0)
   - Will be installed via Chocolatey in this guide
   - Neo4j requires Java Runtime Environment (JRE) or Java Development Kit (JDK)

2. **Chocolatey** (Windows package manager)
   - Check if installed: `choco --version`
   - Install: https://chocolatey.org/install
   - Used for Java installation

3. **Administrator Access** (for Windows service installation)
   - Required for: Installing Windows service, setting system environment variables
   - Verify: Right-click PowerShell → "Run as Administrator" should be available

4. **Python 3.10+** (for Graphiti MCP server)
   - Check version: `python --version`

5. **uv** (Python package manager)
   - Install: `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`

6. **OpenAI API Key** (for LLM operations)
   - Get from: https://platform.openai.com/api-keys

## Installation Steps

### Quick Start Checklist

Follow these steps in order. Each step includes validation to ensure correctness before proceeding.

1. ✅ **Download Neo4j Community Edition** → Verify: Extracted to `C:\neo4j\neo4j-community-2025.09.0`
2. ✅ **Install Java 21** → Verify: `java -version` shows Java 21
3. ✅ **Install Neo4j Windows Service** → Verify: Service appears in Services (services.msc)
4. ✅ **Start Neo4j Service** → Verify: http://localhost:7474 loads Neo4j Browser
5. ✅ **Set Initial Password** → Verify: Can log into Neo4j Browser
6. ✅ **Configure Environment Variables** → Verify: Variables appear in PowerShell
7. ✅ **Configure MCP Server** → Verify: File exists at `.claude/mcp_servers.json`
8. ✅ **Install Graphiti Dependencies** → Verify: `uv run python -c "import graphiti_core"`
9. ✅ **Test Complete Setup** → Verify: MCP server connects in Claude Code

**Estimated Time**: 30-40 minutes for fresh setup

---

### 1. Download Neo4j Community Edition

Neo4j Community 2025.09.0 is **not available in Chocolatey** (only v3.5.1 is packaged). You must download manually.

#### Download Steps

1. **Go to Neo4j Download Center**: https://neo4j.com/deployment-center/#community
2. **Select**: Neo4j Community Edition 2025.09.x (latest stable)
3. **Platform**: Windows (.zip)
4. **Download** the ZIP file (~150MB)

#### Extract to Standard Location

```powershell
# Create directory
New-Item -Path "C:\neo4j" -ItemType Directory -Force

# Extract downloaded ZIP to C:\neo4j\
# This should create: C:\neo4j\neo4j-community-2025.09.0\
```

**Note**: This guide assumes `C:\neo4j\neo4j-community-2025.09.0` as the installation path. Adjust commands if you use a different location.

#### Verify Extraction

```powershell
# Check directory exists
Test-Path C:\neo4j\neo4j-community-2025.09.0
# Should return: True

# List contents
Get-ChildItem C:\neo4j\neo4j-community-2025.09.0
# Should show: bin, conf, data, lib, logs, plugins, etc.
```

---

### 2. Install Java 21

Neo4j Community 2025.09.0 **requires Java 21**. Without Java, Neo4j will fail silently (no logs, no error messages).

#### Install via Chocolatey

```powershell
# Run in PowerShell as Administrator
choco install temurin21 -y
```

**What this installs**:
- Eclipse Temurin 21 (OpenJDK distribution)
- Sets `JAVA_HOME` environment variable
- Adds Java to system PATH

**Installation time**: ~2-3 minutes

#### Verify Installation

**⚠️ IMPORTANT**: You **must restart PowerShell** after Java installation for the PATH to be updated.

```powershell
# Close and reopen PowerShell, then:
java -version
```

**Expected output**:
```
openjdk version "21.0.x" 2024-xx-xx LTS
OpenJDK Runtime Environment Temurin-21.0.x+x (build 21.0.x+x-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.x+x (build 21.0.x+x-LTS, mixed mode, sharing)
```

**If Java is not found**:
1. Restart PowerShell (required for PATH update)
2. Restart Claude Code (if running - it won't see Java until restarted)
3. If still not found, check: `[Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine')`

---

### 3. Install Neo4j as Windows Service

Neo4j can run in two modes:
- **Console mode** (`neo4j.bat console`) - Runs in foreground, blocks terminal ❌
- **Windows Service** (`neo4j.bat windows-service install`) - Runs in background ✅

We'll use Windows Service mode for clean background execution.

#### Install Service

**Run in PowerShell as Administrator**:

```powershell
cd C:\neo4j\neo4j-community-2025.09.0

# Install as Windows service
.\bin\neo4j.bat windows-service install
```

**Expected output**:
```
Neo4j service installed.
```

**Note**: The `windows-service` command syntax changed in Neo4j 2025.x. Old syntax `install-service` no longer works. See [Troubleshooting](#troubleshooting-windows-service-command-syntax) for details.

#### Verify Service Installation

```powershell
# Check if service exists
Get-Service -Name "Neo4j"
```

**Expected output**:
```
Status   Name               DisplayName
------   ----               -----------
Stopped  Neo4j              Neo4j Graph Database - neo4j
```

**If service not found**:
- Ensure you ran the command as Administrator
- Check for error messages in the installation output
- See troubleshooting document: `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md`

---

### 4. Start Neo4j Service

The `windows-service install` command **only registers** the service. It does **not start** it automatically.

#### Start Service

**Option A - PowerShell (Recommended)**:
```powershell
Start-Service Neo4j

# Check status
Get-Service Neo4j
```

**Expected output**:
```
Status   Name               DisplayName
------   ----               -----------
Running  Neo4j              Neo4j Graph Database - neo4j
```

**Option B - Neo4j Command**:
```powershell
cd C:\neo4j\neo4j-community-2025.09.0
.\bin\neo4j.bat start
```

**Option C - Windows Services GUI**:
1. Open Services: `services.msc`
2. Find "Neo4j Graph Database - neo4j"
3. Right-click → Start

#### Verify Neo4j is Running

**Wait 30 seconds** for Neo4j to fully start, then:

1. **Open browser**: http://localhost:7474
2. **Should see**: Neo4j Browser login page

**If browser shows "Connection Refused"**:
- Wait another 30 seconds (Neo4j takes time to start)
- Check logs: `C:\neo4j\neo4j-community-2025.09.0\logs\neo4j.log`
- If logs are empty (0 bytes), Java is not found - see Step 2
- See troubleshooting: `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md`

---

### 5. Set Initial Password

Neo4j requires you to change the default password on first login.

#### First Login

1. **Open**: http://localhost:7474
2. **Default credentials**:
   - Username: `neo4j`
   - Password: `neo4j`
3. **Click**: "Connect"
4. **Prompted**: "Please change your password"
5. **Set new password**: Choose a strong password (e.g., `graphiti-dev-password`)
6. **Confirm password**
7. **Click**: "Apply"

**⚠️ IMPORTANT**: Remember this password! You'll need it for:
- Environment variables (next step)
- MCP server configuration
- Future Neo4j Browser logins

**Recommendation**: Use a password manager or write it down securely.

---

### 6. Configure System Environment Variables

Set environment variables at **system level** (not user level) so they're available to all applications.

#### Variables to Set

| Variable Name | Value | Example |
|---------------|-------|---------|
| `NEO4J_URI` | `bolt://localhost:7687` | Fixed (default Neo4j Bolt port) |
| `NEO4J_USER` | `neo4j` | Fixed (default username) |
| `NEO4J_PASSWORD` | Your password from Step 5 | `graphiti-dev-password` |
| `NEO4J_DATABASE` | `neo4j` | Fixed (default database name) |

**Note**: These use different variable names than the Aura setup (no `GRAPHITI_` prefix) to avoid conflicts if you switch between local and cloud.

#### Setup Methods

Choose **ONE** of the following methods:

##### Method 1: Interactive PowerShell Script (Recommended)

**Location**: `C:\Users\Admin\Documents\GitHub\graphiti\setup-neo4j-community-env.ps1`

**Run in PowerShell as Administrator**:

```powershell
cd C:\Users\Admin\Documents\GitHub\graphiti
.\setup-neo4j-community-env.ps1
```

**What this script does**:
- ✅ Checks for Administrator privileges
- ✅ Shows current environment variable values
- ✅ Prompts you to enter each credential
- ✅ Provides defaults (bolt://localhost:7687, neo4j, etc.)
- ✅ Asks for confirmation before setting
- ✅ Verifies variables were set correctly
- ✅ Shows next steps (restart PowerShell, restart Claude Code)

**Example interaction**:
```
NEO4J_URI
  For local Neo4j Community Edition: bolt://localhost:7687
  Enter NEO4J_URI [bolt://localhost:7687]: (press Enter)

NEO4J_USER
  Default username is typically: neo4j
  Enter NEO4J_USER [neo4j]: (press Enter)

NEO4J_PASSWORD
  Enter the password you set when first logging into Neo4j Browser
  Enter NEO4J_PASSWORD: password

NEO4J_DATABASE
  Default database name is: neo4j
  Enter NEO4J_DATABASE [neo4j]: (press Enter)

Review your settings:
  NEO4J_URI      : bolt://localhost:7687
  NEO4J_USER     : neo4j
  NEO4J_PASSWORD : password
  NEO4J_DATABASE : neo4j

Set these values? (Y/N): Y
```

##### Method 2: Manual PowerShell Commands

**Run in PowerShell as Administrator**:

```powershell
# Set Neo4j connection details
[Environment]::SetEnvironmentVariable('NEO4J_URI', 'bolt://localhost:7687', 'Machine')
[Environment]::SetEnvironmentVariable('NEO4J_USER', 'neo4j', 'Machine')
[Environment]::SetEnvironmentVariable('NEO4J_PASSWORD', 'your-password-here', 'Machine')
[Environment]::SetEnvironmentVariable('NEO4J_DATABASE', 'neo4j', 'Machine')
```

**⚠️ Replace `your-password-here` with your actual password from Step 5.**

#### Verify Variables

**Close and reopen PowerShell** (or restart your system) for environment variables to be available, then:

```powershell
# Check each variable
[Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')
# Should return: bolt://localhost:7687

[Environment]::GetEnvironmentVariable('NEO4J_USER', 'Machine')
# Should return: neo4j

[Environment]::GetEnvironmentVariable('NEO4J_PASSWORD', 'Machine')
# Should return: your-password

[Environment]::GetEnvironmentVariable('NEO4J_DATABASE', 'Machine')
# Should return: neo4j
```

**If variables return blank/null**:
1. Verify you ran PowerShell as Administrator
2. Restart PowerShell
3. If still blank, verify command had no typos

---

### 7. Configure MCP Server for Claude Code

Update your Claude Code MCP configuration to use the local Neo4j instance.

#### Find Configuration File

Claude Code MCP configuration is at:
- **Windows**: `C:\Users\Admin\.claude\mcp_servers.json`
- **macOS/Linux**: `~/.claude/mcp_servers.json`

#### MCP Server Configuration

Create or update `mcp_servers.json`:

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "transport": "stdio",
      "command": "C:\\Users\\Admin\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--isolated",
        "--directory",
        "C:\\Users\\Admin\\Documents\\GitHub\\graphiti\\mcp_server",
        "--project",
        ".",
        "graphiti_mcp_server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "NEO4J_URI": "${NEO4J_URI}",
        "NEO4J_USER": "${NEO4J_USER}",
        "NEO4J_PASSWORD": "${NEO4J_PASSWORD}",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "MODEL_NAME": "gpt-4o-mini"
      }
    }
  }
}
```

**Important Notes**:
- Variables use `${VARIABLE}` syntax to reference system environment variables
- `OPENAI_API_KEY` should already be set as a system environment variable
- Adjust `command` path if your `uv` installation differs (find with: `where uv`)
- Adjust `directory` path if your graphiti repo is elsewhere
- On Windows, use double backslashes `\\` in paths

**To find your uv path**:
```bash
# Windows
where uv

# Unix
which uv
```

---

### 8. Install Graphiti MCP Server Dependencies

```bash
cd C:\Users\Admin\Documents\GitHub\graphiti\mcp_server  # Adjust path as needed

# Install dependencies (Neo4j support included by default)
uv sync

# Verify installation
uv run python -c "from graphiti_core import Graphiti; print('Graphiti installed successfully')"
```

**Expected output**: `Graphiti installed successfully`

**Note**: No need to install `graphiti-core[falkordb]` or `graphiti-core[kuzu]` - Neo4j support is included by default in the core package.

---

### 9. Test Neo4j Connection

Let's verify the connection works before testing with Claude Code.

#### Test Script

Create a test script (or use the one generated earlier):

```python
# test_neo4j_connection.py
from neo4j import GraphDatabase

def test_connection():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = input("Enter your Neo4j password: ")

    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        result = session.run("RETURN 'Connection successful!' as message")
        record = result.single()
        print(f"✓ {record['message']}")

    driver.close()
    print("✓ Neo4j connection test PASSED")

if __name__ == "__main__":
    test_connection()
```

**Run the test**:
```bash
cd C:\Users\Admin\Documents\GitHub\graphiti
uv run python test_neo4j_connection.py neo4j your-password
```

**Expected output**:
```
Attempting to connect to Neo4j at bolt://localhost:7687...
✓ Connection successful!
   Timestamp: 2025-10-23T03:15:09.037000000+00:00
✓ Neo4j connection test PASSED
```

**If connection fails**:
- Verify Neo4j service is running: `Get-Service Neo4j`
- Check Neo4j Browser works: http://localhost:7474
- Verify password is correct
- See troubleshooting document

---

### 10. Verification & Testing

#### Test 1: Neo4j Browser
1. Open: http://localhost:7474
2. Login with your credentials
3. Run query: `RETURN "Hello, Graphiti!" as greeting`
4. Should return results ✅

#### Test 2: Windows Service Status
```powershell
Get-Service Neo4j
# Status should be "Running"
```

#### Test 3: Environment Variables (Re-check)
```powershell
[Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')
[Environment]::GetEnvironmentVariable('NEO4J_USER', 'Machine')
[Environment]::GetEnvironmentVariable('NEO4J_PASSWORD', 'Machine')
# All should return values
```

#### Test 4: MCP Server Connection
1. **Restart Claude Code** (to pick up environment variables)
2. Check MCP servers status (should show graphiti-memory as connected)
3. Try using Graphiti tools:
   - `add_memory` - Add a test memory
   - `search_memory_nodes` - Search for nodes
   - `search_memory_facts` - Search for facts

#### Test 5: Auto-Start on Reboot
1. Restart your computer
2. Wait 1 minute after login
3. Check: http://localhost:7474 (should load without manually starting service)
4. Verify: `Get-Service Neo4j` shows "Running" status ✅

---

## Troubleshooting

### Neo4j Service Won't Start

**Check logs**:
```powershell
Get-Content C:\neo4j\neo4j-community-2025.09.0\logs\neo4j.log -Tail 50
```

**If logs are empty (0 bytes)**:
- Java is not found on PATH
- Restart PowerShell after Java installation
- Restart Claude Code if it was running during Java install
- Verify Java: `java -version`

**If logs show errors**:
- See detailed troubleshooting: `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md`

### Connection Refused (Port 7687)

**Verify service is running**:
```powershell
Get-Service Neo4j
# Status should be "Running"
```

**Check if port is listening**:
```powershell
netstat -an | findstr "7687"
# Should show: TCP  127.0.0.1:7687  0.0.0.0:0  LISTENING
```

**If port not listening**:
- Neo4j failed to start
- Check logs: `C:\neo4j\neo4j-community-2025.09.0\logs\neo4j.log`
- Java may not be installed or PATH not refreshed

### Windows Service Command Syntax

**Old syntax (Neo4j 4.x/early 5.x)** - ❌ No longer works:
```powershell
.\bin\neo4j.bat install-service  # FAILS in 2025.x
.\bin\neo4j.bat start            # FAILS if using old syntax
```

**New syntax (Neo4j 2025.x)** - ✅ Correct:
```powershell
.\bin\neo4j.bat windows-service install   # Install service
Start-Service Neo4j                       # Start service
Get-Service Neo4j                         # Check status
.\bin\neo4j.bat start                     # Alternative start
.\bin\neo4j.bat stop                      # Stop service
```

**Key change**: `windows-service` is now a **subcommand**, not a flag.

See: `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md` § "Issue #5: Windows service command syntax"

### Environment Variables Not Found

```bash
# Restart Claude Code after setting environment variables
# Or restart your entire system

# Verify they're set at system level
powershell -Command "[Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')"
```

### MCP Server Connection Issues
- Check `uv` command path is correct in config
- Verify OPENAI_API_KEY is valid
- Ensure Neo4j service is running
- Review MCP server logs in Claude Code
- Ensure you restarted Claude Code after setting env vars

---

## Current Configuration Summary

| Component | Configuration | Reason |
|-----------|---------------|--------|
| **Database Backend** | Neo4j Community 2025.09.0 (Local) | Free, fast, private, full control |
| **Database Location** | `bolt://localhost:7687` | Local Windows service |
| **Service Mode** | Windows Service (background) | Runs in background, auto-starts on boot |
| **Configuration Method** | System environment variables | Secure, system-wide, easy to update |
| **Python Package Manager** | uv | Fast, reliable dependency management |
| **Graphiti Version** | Vanilla upstream (no custom modifications) | Clean state, easy to update |

---

## Benefits of This Setup

✅ **No monthly cost** - Completely free (vs $65/month for Neo4j Aura)
✅ **Fast performance** - No network latency, localhost speed
✅ **Background execution** - Windows service runs in background, no terminal occupied
✅ **Auto-start on boot** - Service starts automatically after system restart
✅ **Private data** - Everything stays on your machine
✅ **Offline capable** - Works without internet connection
✅ **Full Neo4j features** - Access to all Community Edition features
✅ **Easy to manage** - Standard Windows service controls (services.msc)

---

## Comparison: Local vs Cloud

| Feature | Neo4j Community (Local) | Neo4j Aura (Cloud) |
|---------|------------------------|-------------------|
| **Cost** | Free | $65/month (~$0.09/hour) |
| **Setup Time** | 30-40 minutes | 5-10 minutes |
| **Performance** | Fast (localhost) | Network latency |
| **Internet Required** | No | Yes |
| **Multi-machine Access** | No (single machine) | Yes (anywhere) |
| **Data Privacy** | Complete (local only) | Shared with Neo4j |
| **Backups** | Manual | Automatic (managed) |
| **Maintenance** | Self-managed | Fully managed |
| **VM Migration** | Manual (export/import) | Seamless (cloud-based) |

**When to use each**:
- **Local**: Development, testing, privacy-critical, cost-sensitive, single machine
- **Cloud (Aura)**: Production, multi-machine, managed backups, zero maintenance

---

## Managing Neo4j Service

### Start Service
```powershell
Start-Service Neo4j
# OR
C:\neo4j\neo4j-community-2025.09.0\bin\neo4j.bat start
```

### Stop Service
```powershell
Stop-Service Neo4j
# OR
C:\neo4j\neo4j-community-2025.09.0\bin\neo4j.bat stop
```

### Check Status
```powershell
Get-Service Neo4j
# OR
C:\neo4j\neo4j-community-2025.09.0\bin\neo4j.bat status
```

### Restart Service
```powershell
Restart-Service Neo4j
# OR
C:\neo4j\neo4j-community-2025.09.0\bin\neo4j.bat restart
```

### Uninstall Service
```powershell
# Stop service first
Stop-Service Neo4j

# Uninstall
C:\neo4j\neo4j-community-2025.09.0\bin\neo4j.bat windows-service uninstall
```

---

## Related Documentation

- See `CLAUDE_CHANGELOG.md` for history of configuration changes
- See `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md` for detailed issue documentation
- See `CLAUDE_INSTALL_NEO4J_AURA.md` for cloud setup instructions (alternative)
- See upstream docs: https://github.com/getzep/graphiti
- See Neo4j Community docs: https://neo4j.com/docs/

---

**Last Updated**: 2025-10-23
**Last Verified By**: Claude (Sonnet 4.5)
**Platform**: Windows 10/11 (MSYS_NT-10.0-26100)
**Database**: Neo4j Community Edition 2025.09.0 (Local Windows Service)
**Neo4j Service**: Background service, auto-starts on boot
