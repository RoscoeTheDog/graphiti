# Graphiti - Installation Guide

> **📝 GENERATED FILE**: Platform-specific installation guide (instance/)
> **Source**: claude-mcp-installer/templates/CLAUDE_INSTALL.template.md
> **Note**: This file is gitignored and customized for your platform
> **Updated**: 2025-11-06 with historical issue fixes

**Version**: 1.1.0 | **For**: AI-assisted + manual install



## TOC

[Overview](#overview) | [Prerequisites](#prerequisites) | [Options](#installation-options) | [MCP Integration](#mcp-server-integration) | [Setup](#step-by-step-setup) | [Environment](#environment-configuration) | [Validation](#validation) | [Troubleshooting](#troubleshooting) | [Support](#support)

---

## Overview

**About**:
- **Upstream**: Graphiti by [Zep](https://www.getzep.com/) - Build Real-Time Knowledge Graphs for AI Agents
- **Upstream Repo**: `https://github.com/getzep/graphiti`
- **This Fork**: `https://github.com/RoscoeTheDog/graphiti` (your custom fork)
- **Paper**: [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)
- **Custom**: MCP server integration for Claude Code CLI with knowledge graph memory

**Philosophy**: Multi-path install, explicit choices (AI always prompts), platform-specific, validation-tracked, non-intrusive (user confirms all system changes)

**AI Installation Policy** (P7: Non-Intrusive Installation):
- ✅ **Agent ALWAYS prompts** before system/environment changes
- ✅ **User explicitly confirms** package installs, global config, system services
- ✅ **Transparent operations** - agent explains scope, impact, reversibility
- ✅ **Project-local changes** (venv, .env, project files) - OK without prompt
- ❌ **NEVER auto-install** packages or modify system without approval

**What Requires Confirmation**:
```
System Changes (PROMPT REQUIRED):
├─ Package installation (pip, npm, apt, brew)
├─ Global environment variables (system-wide)
├─ Service installation (databases, runtimes)
├─ MCP server registration (global Claude Code config)
└─ PATH modifications, registry edits

Project Changes (NO PROMPT NEEDED):
├─ .env file creation/editing (project-local)
├─ Virtual environment setup (project-local)
├─ Installing deps in active venv (project-scoped)
└─ Config files within project directory
```

---

## Prerequisites

### Required

#### Python 3.10+ ✅WML
- **Reason**: Graphiti requires Python 3.10 or higher (3.11+ recommended)
- **Validation**: ✅W11, ✅M14, ✅U22.04
- **Install**:
  - W: [python.org](https://python.org/downloads/)
  - M: `brew install python@3.11`
  - L: `sudo apt install python3.11 python3.11-venv`
- **Verify**: `python --version` (should show 3.10+)

#### Git ✅WML
- **Install**:
  - W: [git-scm.com](https://git-scm.com/)
  - M: `brew install git` | Xcode CLI Tools
  - L: `sudo apt install git`

### Optional

#### Docker ✅WML
- **Reason**: Easiest way to run Neo4j database locally
- **Required-For**: Local development with containerized database
- **Validation**: ✅ All platforms

---

## Installation Options

Wizard-style: Choose per component. Agent prompts, never assumes.

### Database Setup

**Prompt**: "Which database method?"

#### Opt1: Neo4j Community Edition (Windows Service) ✅W11 **RECOMMENDED** (Cost-Effective)
- **Best**: $0 cost, offline dev, full control, long-term cost savings
- **Pros**: Free forever, no internet required, full control, background service (NOT console mode), private data
- **Cons**: Initial setup complexity (30-60min), requires Java 21, manual ZIP download
- **Time**: 30-60min (one-time setup with detailed docs)
- **Validation**: ✅ W11 (fully tested with comprehensive troubleshooting guide)
- **Requires**: Java 21, manual Neo4j download, Windows Service configuration
- **Cost**: **$0/month forever** vs Aura's **$65/month** = **$780/year savings**

**Why Recommended for Long-Term Use**:
- **Zero recurring costs** - Free forever, no subscription fees
- **Cost analysis**: One-time 60min setup vs $780/year ongoing costs
- **Full control** - No vendor lock-in, customize as needed
- **Private data** - Everything stays local, no cloud exposure
- **Offline capable** - Works without internet once configured
- **Production ready** - Background Windows Service, no terminal blocking

**⚠️ Known Setup Issues** (ALL documented with solutions in `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md`):
1. Chocolatey Neo4j package is **severely outdated** (v3.5.1 from 2019) - **UNUSABLE**
   - Solution: Manual ZIP download from neo4j.com (2025.09.0+)
2. Java 21 **mandatory** - silent failures if missing (empty logs, no errors)
   - Solution: `choco install temurin21 -y` BEFORE Neo4j setup
3. PowerShell restart required after Java install
   - Solution: Close/reopen PowerShell (documented in guide)
4. Claude Code restart required to see Java on PATH
   - Solution: Restart Claude Code after Java install (documented in guide)
5. Windows Service command syntax **changed in 2025.x**
   - Solution: Use `windows-service install` (NOT `install-service`)
6. Service **does NOT auto-start** after installation
   - Solution: `Start-Service Neo4j` explicitly (documented in guide)
7. Console mode blocks terminal
   - Solution: Use Windows Service mode (NOT console mode)
8. Chocolatey package manager issues
   - Solution: All manual steps documented with exact commands

**Complete Documentation Available**:
- **Setup Guide**: `CLAUDE_INSTALL_NEO4J_COMMUNITY_WINDOWS_SERVICE.md` (step-by-step)
- **Troubleshooting**: `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md` (all 8 issues with fixes)
- **Agent can guide you** through the entire setup interactively

**Setup is ONE-TIME effort** - Once configured, runs reliably as background service with zero maintenance.

#### Opt2: Neo4j Aura (Cloud) ✅W11+M14+Proxmox (Quick Start Alternative)
- **Best**: Zero setup, quick start, works everywhere (VMs, Docker, bare metal)
- **Pros**: Managed, no maintenance, remote-access, concurrent connections, VM-agnostic, 5-10min setup
- **Cons**: **$65/month recurring cost** ($780/year), internet required, vendor lock-in, data in cloud
- **Time**: 5-10min (quick but ongoing cost)
- **Validation**: ✅W11, ✅M14, ✅Proxmox VM
- **Free Tier**: 200k nodes + 400k relationships (limited, then $65/month)
- **⚠️ CRITICAL**: Use `neo4j+ssc://` URI scheme (NOT `neo4j+s://`) to avoid SSL routing errors in VMs

**When to Choose Aura**:
- **Prototyping/testing** - Quick start for proof-of-concept
- **Multi-VM setup** - Need database accessible from multiple VMs simultaneously
- **Cost not a concern** - $780/year is acceptable for your use case
- **Don't want to troubleshoot** - Prefer managed service over local setup

**Cost Comparison**:
```
Year 1: Neo4j Aura = $780 | Neo4j Community = 1 hour setup = $0
Year 2: Neo4j Aura = $780 | Neo4j Community = $0
Year 3: Neo4j Aura = $780 | Neo4j Community = $0
5-Year Total: $3,900 vs $0 (savings: $3,900)
```

**Why User Originally Chose Community Edition**:
> "Neo4j aura I'm discovering is very expensive. Its about 0.09 an hour or ~$65 a month."
> "Neo4j desktop worked but it involved running a shell in the foreground which was screwing up my development workflow."

**Solution**: Neo4j Community as **Windows Service** (background) = $0 cost + no terminal blocking

#### Opt3: Neo4j Docker ✅WML
- **Best**: Isolated env, easy cleanup
- **Pros**: Containerized, reproducible, easy-reset
- **Cons**: Docker required
- **Time**: 10-15min
- **Validation**: ✅ All platforms

---

## MCP Server Integration

> **Note**: This section configures Graphiti as an MCP server for Claude Code CLI.

**Purpose**: Configure this MCP server for global availability in Claude Code CLI

**When to Use**: After completing base installation, use this to register the MCP server with Claude Code CLI for use across all projects.

**Transport Modes**:
- **HTTP Transport (Daemon Mode)**: Recommended for daemon architecture. Multiple Claude Code sessions share single daemon instance.
- **stdio Transport (Legacy)**: Per-session mode. Each Claude Code session spawns its own MCP server process.

### Prerequisites

- ✅ Claude Code CLI installed (`claude --version`)
- ✅ Base project dependencies installed (see [Step-by-Step Setup](#step-by-step-setup))
- ✅ Required credentials available (see below)
- ✅ (HTTP only) Daemon installed and enabled (see [Daemon Configuration](#daemon-configuration))

### Installation Wizard

**Agent will automatically check for existing installations** before proceeding.

#### Phase 1: Pre-Installation Check

**Automatic Detection**:
```bash
# Agent runs:
claude mcp list | grep graphiti
```

**Possible States**:

| State | Description | Action |
|-------|-------------|--------|
| **Not Installed** | Server not found in list | ✅ Proceed with fresh installation |
| **User Scope** | Already installed globally | ⚙️  Show Update/Repair/Reinstall/Cancel wizard |
| **Project Scope** | Installed locally only | 🔄 Prompt to migrate to global scope |
| **Broken** | In list but disconnected | 🔧 Prompt to repair installation |

**If Already Installed**:
```
┌─────────────────────────────────────────────┐
│ MCP Server Installation Wizard             │
├─────────────────────────────────────────────┤
│                                             │
│ ✓ Found: graphiti-memory (User scope)      │
│   Status: Connected                         │
│   Command: [current-command]                │
│   Entrypoint: [current-entrypoint]          │
│                                             │
│ What would you like to do?                  │
│                                             │
│ [1] Update Configuration                    │
│     → Modify credentials or paths           │
│                                             │
│ [2] Repair Installation                     │
│     → Verify paths, test connection, fix    │
│                                             │
│ [3] Reinstall Completely                    │
│     → Remove and fresh install              │
│                                             │
│ [4] Cancel                                  │
│     → Keep current configuration            │
│                                             │
│ Choice [1-4]:                               │
└─────────────────────────────────────────────┘
```

**Workflow by Choice**:

- **[1] Update** → Load current config, prompt for credential changes, update & verify
- **[2] Repair** → Verify paths exist, test connection, diagnose & fix issues
- **[3] Reinstall** → Remove existing, proceed to fresh installation
- **[4] Cancel** → Exit, keep current configuration unchanged

#### Phase 2: Credential Discovery (Fresh Install or Reinstall)

**Agent will detect required credentials from**:
1. README.md sections (Prerequisites, Configuration, Environment)
2. .env.example file (credential template)
3. Code search (environment variable patterns across all languages)

**Detected Credentials**:
```
Required:
- NEO4J_PASSWORD: Password for Neo4j database connection
- OPENAI_API_KEY: OpenAI API key for LLM operations

Optional:
- ANTHROPIC_API_KEY: Anthropic API key (if using Anthropic as LLM provider)
- AZURE_OPENAI_API_KEY: Azure OpenAI API key (if using Azure)
- AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL (if using Azure)
```

**System Environment Check**:
```bash
# Agent checks system environment for each credential

# Windows (CMD)
echo %NEO4J_PASSWORD%

# Windows (PowerShell)
$env:NEO4J_PASSWORD

# macOS/Linux
echo $NEO4J_PASSWORD
```

**Results**:
```
✓ OPENAI_API_KEY: Found in system environment
✗ NEO4J_PASSWORD: Not found in system environment
✗ ANTHROPIC_API_KEY: Not found (optional)
```

**Credential Elicitation**:

For each **not found** credential:
```
Please provide NEO4J_PASSWORD:
[Masked input: ●●●●●●●●●●●●]

✓ Received: ****...****
```

For each **found** credential:
```
Use existing system value for OPENAI_API_KEY? [Y/N]
→ Y: Use system value (don't show or re-enter)
→ N: Enter new value: [masked input]
```

**Optional: Add to System Environment**:
```
Would you like to add credentials to system environment variables? [Y/N]

→ Y: Agent provides platform-specific instructions
→ N: Skip (credentials stored only in ~/.claude.json)
```

**Platform-Specific Instructions** (if user wants to add to system):

<details>
<summary><strong>Windows (PowerShell - Recommended)</strong></summary>

```powershell
# Set persistent user environment variable
[Environment]::SetEnvironmentVariable("NEO4J_PASSWORD", "value", "User")

# Restart terminal to apply changes
exit
```
</details>

<details>
<summary><strong>Windows (GUI Method)</strong></summary>

1. Press `Win+R`, type: `sysdm.cpl`, press Enter
2. Navigate to **Advanced** tab → **Environment Variables**
3. Under **User variables**, click **New**
4. Variable name: `NEO4J_PASSWORD`
5. Variable value: `[value]`
6. Click **OK** → **OK** → Restart terminal
</details>

<details>
<summary><strong>macOS/Linux (Bash)</strong></summary>

```bash
# Add to ~/.bashrc or ~/.bash_profile
echo 'export NEO4J_PASSWORD="value"' >> ~/.bashrc
source ~/.bashrc
```
</details>

<details>
<summary><strong>macOS/Linux (Zsh)</strong></summary>

```zsh
# Add to ~/.zshrc
echo 'export NEO4J_PASSWORD="value"' >> ~/.zshrc
source ~/.zshrc
```
</details>

**⚠️  Important Note About Environment Variables**:
```
Even if credentials are in system environment variables,
Claude Code CLI stores LITERAL VALUES in ~/.claude.json
(not variable references like ${VAR} or %VAR%).

This means:
- System env vars are READ ONCE at configuration time
- Actual values are STORED in ~/.claude.json
- If you change env vars later, you MUST re-run installation

Security Note:
- ~/.claude.json contains sensitive data
- Never commit ~/.claude.json to git
- Protect with file permissions: chmod 600 ~/.claude.json (Unix)
```

#### Phase 3: Configure MCP Server

**Auto-Generated Configuration**:

Agent automatically detects:
- **Platform**: Windows | macOS | Linux
- **Runtime Path**: Absolute path to Python interpreter
- **Entrypoint Path**: Absolute path to `mcp_server/graphiti_mcp_server.py`
- **Server Name**: `graphiti-memory`

**Command Generated**:

**Agent Workflow** (P7: Non-Intrusive Installation):

**Option 1: HTTP Transport (Recommended for Daemon Architecture)**:
```
Agent: "About to configure MCP server for HTTP transport (daemon mode):

        Configuration Method: Manual edit of claude_desktop_config.json
        Scope: User-wide (available in all your projects)
        Transport: HTTP (connects to running daemon)
        URL: http://127.0.0.1:8321/mcp/

        Prerequisites:
        - Graphiti daemon installed (graphiti-mcp daemon install)
        - Daemon is already running (auto-enabled after install)

        This enables many-to-one architecture:
        - Multiple Claude Code sessions share single daemon
        - Session tracking aggregates across all sessions
        - No per-session process spawning

        Proceed? [Y/N]"

User: "Y"

Agent: [Provides configuration below]
```

**Manual Configuration** (edit `~/.claude/claude_desktop_config.json` or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):
```json
{
  "mcpServers": {
    "graphiti-memory": {
      "url": "http://127.0.0.1:8321/mcp/",
      "transport": "http"
    }
  }
}
```

**Important Notes**:
- **Daemon auto-enabled**: After running `graphiti-mcp daemon install`, the daemon is already running (no config editing needed)
- **NO stdio fallback**: If daemon is not running, connection will fail (by design)
- **Shared state**: All Claude Code sessions connect to same daemon instance
- **No credentials needed**: HTTP transport uses localhost-only binding (secure)

**Option 2: stdio Transport (Legacy, Per-Session Mode)**:
```
Agent: "About to add MCP server to global Claude Code configuration:

        Command: claude mcp add-json --scope user graphiti-memory
        Scope: User-wide (available in all your projects)
        Location: ~/.claude.json

        Configuration:
        - Runtime: [ABSOLUTE_PYTHON_PATH]
        - Entrypoint: [PROJECT_PATH]/mcp_server/graphiti_mcp_server.py
        - Credentials: NEO4J_PASSWORD, OPENAI_API_KEY (values masked)

        This is a SYSTEM CHANGE (modifies global config).

        Proceed? [Y/N]"

User: "Y"

Agent: [Executes command below]
```

```bash
claude mcp add-json --scope user graphiti-memory '{
  "type":"stdio",
  "command":"[ABSOLUTE_PYTHON_PATH]",
  "args":["[PROJECT_PATH]/mcp_server/graphiti_mcp_server.py"],
  "env":{
    "NEO4J_PASSWORD":"[actual-value]",
    "OPENAI_API_KEY":"[actual-value]",
    "NEO4J_URI":"neo4j+ssc://[instance].databases.neo4j.io",
    "NEO4J_USER":"neo4j"
  }
}'
```

**Example (Python-based server on Windows with Proxmox VM)**:
```bash
claude mcp add-json --scope user graphiti-memory '{
  "type":"stdio",
  "command":"C:\\Users\\Admin\\Documents\\GitHub\\graphiti\\.venv\\Scripts\\python.exe",
  "args":["C:\\Users\\Admin\\Documents\\GitHub\\graphiti\\mcp_server\\graphiti_mcp_server.py"],
  "env":{
    "NEO4J_PASSWORD":"your_password",
    "OPENAI_API_KEY":"sk-proj-...",
    "NEO4J_URI":"neo4j+ssc://xxxxx.databases.neo4j.io",
    "NEO4J_USER":"neo4j"
  }
}'
```

**Note**: stdio transport spawns a new MCP server process per Claude Code session. This is the legacy mode and does not support shared state or session tracking aggregation.

**⚠️ CRITICAL - URI Scheme for VMs**:
```
If running in a VM (Proxmox, VMware, VirtualBox, Hyper-V, WSL2):
- ✅ USE: neo4j+ssc:// (accepts self-signed certs, prevents routing errors)
- ❌ AVOID: neo4j+s:// (causes "Unable to retrieve routing information" errors)

This is a KNOWN ISSUE documented in CLAUDE_INSTALL_NEO4J_AURA.md and verified
to work in Proxmox VMs.
```

**Important Configuration Notes**:
- ✅ **Always use `--scope user`** for global availability across all projects
- ✅ **Use absolute paths** for both command and entrypoint (no relative paths)
- ⚠️  **Credentials are stored literally** in `~/.claude.json` (not as env var references)
- ⚠️  **Cannot use `${VAR}` or `%VAR%`** syntax - values are expanded at config time
- 🔒 **Security**: `~/.claude.json` contains plaintext credentials - never commit to git

#### Phase 4: Verification

**Verify Installation**:
```bash
# List all MCP servers
claude mcp list

# Should show:
graphiti-memory: ✓ Connected (User scope)

# Get detailed configuration
claude mcp get graphiti-memory

# Should show:
graphiti-memory:
  Scope: User config (available in all your projects)
  Status: ✓ Connected
  Type: stdio
  Command: [python-path]
  Args: [entrypoint-path]
  Environment:
    NEO4J_PASSWORD: [masked-value]
    OPENAI_API_KEY: [masked-value]
```

**Test in Claude Code CLI**:
```bash
# Restart Claude Code CLI (if currently running)
exit
claude

# Check MCP servers
/mcp

# Should list graphiti-memory with available tools
```

#### Phase 5: Post-Installation

**For Fresh Installation**:
```
✅ Installation complete!

Summary:
- Server: graphiti-memory
- Scope: User (global)
- Status: Connected
- Credentials configured: NEO4J_PASSWORD, OPENAI_API_KEY

Next steps:
1. ✅ Restart Claude Code CLI (if running)
2. ✅ Run '/mcp' to see available MCP servers
3. ✅ Test tools: add_memory, search_memory_nodes, search_memory_facts

Available tools:
- add_memory: Add episodes to the knowledge graph
- search_memory_nodes: Search for entities
- search_memory_facts: Search for relationships
- get_episodes: Retrieve recent episodes
- health_check: Check server health and database connectivity
```

**For Update**:
```
✅ Configuration updated!

Changes:
- NEO4J_PASSWORD: Updated
- OPENAI_API_KEY: Unchanged

Restart Claude Code CLI to apply changes:
> exit
> claude
```

**For Repair**:
```
✅ Installation repaired!

Issues fixed:
- Database connection: Verified
- Python path: Updated

Status: Connected
```

### Troubleshooting

#### Issue: Server not appearing in `/mcp` list

**Symptoms**: `/mcp` command doesn't show graphiti-memory

**Diagnosis**:
```bash
# Check if server is registered
claude mcp list | grep graphiti

# If found, check details
claude mcp get graphiti-memory
```

**Solutions**:
1. **Not in list at all** → Run installation again
2. **Project scope (local)** → Migrate to user scope:
   ```bash
   claude mcp remove graphiti-memory -s local
   # Then re-run installation with --scope user
   ```
3. **Status: Disconnected** → See "Connection failed" issue below

#### Issue: Connection failed / Status: Disconnected

**Symptoms**: Server appears in list but shows "Disconnected" or "Failed to connect"

**Diagnosis**:
```bash
# Verify Python exists
python --version

# Verify entrypoint exists
ls mcp_server/graphiti_mcp_server.py

# Test server manually
python mcp_server/graphiti_mcp_server.py
# Should start without errors (Ctrl+C to stop)
```

**Common Causes & Fixes**:

1. **Missing dependencies**:
   ```
   Error: ModuleNotFoundError: No module named 'graphiti_core'

   Fix: Install dependencies
   pip install -e .
   ```

2. **Wrong Python path**:
   ```
   Error: Command not found / File not found

   Fix: Update configuration with correct path
   - Option 1: Re-run installation (choose "Update")
   - Option 2: Manual update (see "Updating Credentials" below)
   ```

3. **Database not running**:
   ```
   Error: Cannot connect to Neo4j

   Fix: Verify Neo4j Aura instance is running at https://console.neo4j.io
   ```

4. **Invalid credentials**:
   ```
   Error: Authentication failed

   Fix: Update credentials
   - Re-run installation
   - Choose "Update Configuration"
   - Provide new credential values
   ```

5. **VM SSL routing error** (MOST COMMON in VMs):
   ```
   Error: Unable to retrieve routing information

   Fix: Change URI scheme from neo4j+s:// to neo4j+ssc://
   - Re-run installation
   - Choose "Update Configuration"
   - Agent will detect VM and auto-fix URI scheme
   ```

#### Issue: Credential errors

**Symptoms**: Server connects but tools fail with authentication errors

**Verification**:
```bash
# Check stored credentials (masked)
claude mcp get graphiti-memory

# Shows:
Environment:
  NEO4J_PASSWORD: [masked-value]
  OPENAI_API_KEY: [masked-value]
```

**Solution**:
```
# Re-run installation to update credentials
# Agent will detect existing installation
# Choose [1] Update Configuration
# Select credentials to update
# Provide new values
```

#### Issue: Changes not taking effect

**Symptoms**: Updated configuration but still using old values

**Solution**:
```bash
# Claude Code CLI must be restarted to reload config
exit

# Start new session
claude

# Verify changes applied
claude mcp get graphiti-memory
```

### Updating Credentials Later

**If credentials change** (API key rotated, new service, etc.):

**Method 1: Re-run Installation (Recommended)**:
```
1. Navigate to project directory
2. Tell agent: "Read claude-mcp-installer/instance/CLAUDE_INSTALL.md and update MCP server configuration"
3. Agent detects existing installation
4. Choose [1] Update Configuration
5. For each credential: "Update? [Y/N]"
   → Y: Enter new value
   → N: Keep current
6. Agent reconfigures automatically
7. Restart Claude Code CLI
```

**Method 2: Manual Update**:
```bash
# Step 1: Remove existing configuration
claude mcp remove graphiti-memory

# Step 2: Re-add with new credentials
claude mcp add-json --scope user graphiti-memory '{
  "type":"stdio",
  "command":"[python-path]",
  "args":["[entrypoint-path]"],
  "env":{
    "NEO4J_PASSWORD":"[new-value]",
    "OPENAI_API_KEY":"[new-value]"
  }
}'

# Step 3: Verify
claude mcp get graphiti-memory

# Step 4: Restart Claude Code CLI
exit
claude
```

### Migrating from stdio to HTTP Transport

**When to Migrate**:
- You want to use the daemon architecture (many-to-one)
- Multiple Claude Code sessions need to share state
- Session tracking should aggregate across all sessions
- Bootstrap service is installed and running

**Migration Steps**:

1. **Ensure daemon is running**:
   ```bash
   # Edit config file at platform-specific location:
   # Windows: %LOCALAPPDATA%\Graphiti\config\graphiti.config.json
   # macOS: ~/Library/Preferences/Graphiti/graphiti.config.json
   # Linux: ~/.config/graphiti/graphiti.config.json
   # Set: "daemon": { "enabled": true }

   # Wait 5 seconds for bootstrap to detect change and start MCP server

   # Verify daemon is running
   curl http://127.0.0.1:8321/health
   # Should return: {"status": "healthy"}
   ```

2. **Update Claude Code configuration**:

   **Option A: Manual Edit (Recommended)**:
   ```bash
   # Edit ~/.claude/claude_desktop_config.json (macOS/Linux)
   # or %APPDATA%\Claude\claude_desktop_config.json (Windows)

   # Replace stdio configuration:
   {
     "mcpServers": {
       "graphiti-memory": {
         "type": "stdio",
         "command": "...",
         "args": ["..."],
         "env": {...}
       }
     }
   }

   # With HTTP configuration:
   {
     "mcpServers": {
       "graphiti-memory": {
         "url": "http://127.0.0.1:8321/mcp/",
         "transport": "http"
       }
     }
   }
   ```

   **Option B: CLI Commands**:
   ```bash
   # Remove stdio configuration
   claude mcp remove graphiti-memory

   # Note: HTTP transport does not use CLI registration
   # You must manually edit claude_desktop_config.json (see Option A)
   ```

3. **Restart Claude Code**:
   ```bash
   # Exit current session
   exit

   # Start new session
   claude

   # Verify connection
   /mcp
   # Should show graphiti-memory with HTTP transport
   ```

4. **Test multi-session sharing**:
   ```bash
   # Terminal 1: Start Claude Code session
   claude

   # Terminal 2: Start another Claude Code session
   claude

   # Both sessions should connect to same daemon
   # Session tracking will aggregate data from both sessions
   ```

**Rollback to stdio**:

If you need to revert to stdio transport:

1. Edit `claude_desktop_config.json` and change HTTP config back to stdio
2. Restart Claude Code
3. Verify connection with `/mcp`

**Troubleshooting Migration**:

- **Connection refused**: Verify daemon is running (`curl http://127.0.0.1:8321/health`)
- **Daemon not starting**: Check config file at platform-specific location has `daemon.enabled: true`:
  - Windows: `%LOCALAPPDATA%\Graphiti\config\graphiti.config.json`
  - macOS: `~/Library/Preferences/Graphiti/graphiti.config.json`
  - Linux: `~/.config/graphiti/graphiti.config.json`
- **Bootstrap service not running**: Run `graphiti-mcp daemon status` (if daemon CLI installed)
- **Credentials still required**: HTTP transport does NOT need credentials in config (uses daemon's config)

### Security Best Practices

1. **Protect ~/.claude.json**:
   ```bash
   # Unix/macOS
   chmod 600 ~/.claude.json

   # Windows (PowerShell)
   icacls $env:USERPROFILE\.claude.json /inheritance:r /grant:r "$env:USERNAME:(F)"
   ```

2. **Never commit credentials**:
   - Add to .gitignore: `.env`, `~/.claude.json`
   - Use `.env` files for local development
   - Keep API keys in environment variables when possible

3. **Rotate credentials regularly**:
   - Update MCP server config when rotating keys
   - Test after rotation to ensure functionality

4. **Use least-privilege credentials**:
   - API keys should have minimal required permissions
   - Create service-specific keys when possible

---

## Daemon Configuration

> **Note**: This section is for HTTP transport (daemon architecture) only. Skip if using stdio transport.

**What is the Daemon Architecture?**:

The daemon architecture enables a **many-to-one** model where multiple Claude Code sessions connect to a single, persistent MCP server daemon instead of each session spawning its own process.

**Benefits**:
- Shared state across all Claude Code sessions
- Session tracking aggregates data from all connected clients
- Reduced resource usage (single Neo4j connection, single Python process)
- CLI tools can connect to the same server
- Server survives session restarts

**Architecture**:
```
┌─────────────────┐
│ Claude Code #1  │─────┐
└─────────────────┘     │
                        │  HTTP/JSON
┌─────────────────┐     │  :8321
│ Claude Code #2  │─────┼─────────►┌──────────────────────┐
└─────────────────┘     │          │  Graphiti MCP Server │
                        │          │  (Daemon Service)    │
┌─────────────────┐     │          │  - Single Neo4j conn │
│ CLI commands    │─────┘          │  - Shared state      │
└─────────────────┘                └──────────────────────┘
```

**Two-Layer Architecture**:
1. **Bootstrap Service**: Always runs, watches config file for changes
2. **MCP Server**: Only runs when `daemon.enabled: true` in config

### Installation

**Prerequisites**:
- Base dependencies installed (see [Step-by-Step Setup](#step-by-step-setup))
- Database configured (Neo4j Aura, Community Edition, or Docker)

**Install Daemon** (Platform-specific):

The daemon installation is handled by Story 4 (Platform Service Installation). Once Story 4 is complete, you can install the daemon using:

```bash
# Install bootstrap service (auto-starts on boot, daemon auto-enabled)
graphiti-mcp daemon install
# The MCP server starts automatically - no manual config editing needed!

# Verify daemon is running (should be active immediately)
graphiti-mcp daemon status
```

**What Happens During Install**:
1. Bootstrap service is installed and started
2. Configuration file is created with `daemon.enabled: true` (auto-enabled) at:
   - **Windows**: `%LOCALAPPDATA%\Graphiti\config\graphiti.config.json`
   - **macOS**: `~/Library/Preferences/Graphiti/graphiti.config.json`
   - **Linux**: `~/.config/graphiti/graphiti.config.json`
3. MCP server starts automatically within 5 seconds
4. Daemon is ready to accept connections immediately

**Configuration**:

The configuration file is created during daemon install with daemon auto-enabled:

```json
{
  "daemon": {
    "enabled": true,        ← Auto-enabled after install (no manual edit needed!)
    "host": "127.0.0.1",
    "port": 8321,
    "config_poll_seconds": 5
  },
  "neo4j": {
    "uri": "neo4j+ssc://xxxxx.databases.neo4j.io",
    "user": "neo4j",
    "password": "your_password"
  },
  "llm": {
    "api_key": "sk-your-openai-key",
    "model": "gpt-4"
  }
}
```

**Key Settings**:
- `daemon.enabled`: Master switch (true = MCP server running, false = MCP server stopped) - **Defaults to true after install**
- `daemon.host`: Bind address (127.0.0.1 = localhost-only, secure)
- `daemon.port`: HTTP port (8321 is default)
- `config_poll_seconds`: How often bootstrap checks for config changes (5s default)

**Verifying the Daemon**:

After installation, the daemon should be running automatically:

```bash
# Check daemon status (should show "running")
graphiti-mcp daemon status

# Verify health endpoint
curl http://127.0.0.1:8321/health
# Should return: {"status": "healthy"}
```

**Stopping the Daemon**:

```bash
# Disable daemon (edit config file)
# Set: "daemon": { "enabled": false }

# Bootstrap service detects change within 5 seconds and stops MCP server

# Verify daemon is stopped
curl http://127.0.0.1:8321/health
# Should return: Connection refused
```

**Viewing Logs**:

```bash
# Tail daemon logs
graphiti-mcp daemon logs

# Logs location (platform-specific):
# Windows: %LOCALAPPDATA%\Graphiti\logs\graphiti-mcp.log
# macOS: ~/Library/Logs/Graphiti/graphiti-mcp.log
# Linux: ~/.local/state/graphiti/logs/graphiti-mcp.log
```

**Uninstallation**:

```bash
# Uninstall bootstrap service
graphiti-mcp daemon uninstall

# Bootstrap service is removed from OS startup
# MCP server stops automatically
```

### Troubleshooting Daemon

**Issue: Daemon not starting after install**:

This is the most common issue with the auto-enable feature. The daemon should start automatically within 5 seconds of install.

1. Verify daemon was auto-enabled during install (check platform-specific config path):
   ```bash
   # Windows (PowerShell)
   Get-Content "$env:LOCALAPPDATA\Graphiti\config\graphiti.config.json" | Select-String '"enabled"'

   # macOS/Linux
   cat ~/Library/Preferences/Graphiti/graphiti.config.json | grep '"enabled"'  # macOS
   cat ~/.config/graphiti/graphiti.config.json | grep '"enabled"'  # Linux
   # Should show: "enabled": true
   ```

2. Check if bootstrap service is running:
   ```bash
   graphiti-mcp daemon status
   # Should show bootstrap service active
   ```

3. If `daemon.enabled: false` in config (install failed to auto-enable):
   ```bash
   # Manually enable daemon - edit config file at platform-specific location:
   # Windows: %LOCALAPPDATA%\Graphiti\config\graphiti.config.json
   # macOS: ~/Library/Preferences/Graphiti/graphiti.config.json
   # Linux: ~/.config/graphiti/graphiti.config.json
   # Set: "daemon": { "enabled": true }

   # Wait 5 seconds for bootstrap to detect change
   sleep 5

   # Verify daemon started
   graphiti-mcp daemon status
   ```

4. View logs for startup errors:
   ```bash
   graphiti-mcp daemon logs
   ```

**Issue: Connection refused immediately after install**:

If you see connection errors right after running `graphiti-mcp daemon install`:

1. Wait for daemon to start (auto-enable has 5-second detection window):
   ```bash
   # Wait for bootstrap service to detect enabled: true
   sleep 5

   # Check health endpoint
   curl http://127.0.0.1:8321/health
   # Should return: {"status": "healthy"}
   ```

2. Verify daemon is actually running:
   ```bash
   graphiti-mcp daemon status
   # Look for MCP server process (not just bootstrap)
   ```

3. Check if config was created with auto-enable (platform-specific path):
   ```bash
   # Windows (PowerShell)
   Get-Content "$env:LOCALAPPDATA\Graphiti\config\graphiti.config.json"

   # macOS
   cat ~/Library/Preferences/Graphiti/graphiti.config.json

   # Linux
   cat ~/.config/graphiti/graphiti.config.json
   # Verify daemon.enabled is true
   ```

**Issue: Daemon not starting (general)**:

1. Check if bootstrap service is installed:
   ```bash
   graphiti-mcp daemon status
   ```

2. Verify config file exists and is valid JSON (platform-specific path):
   ```bash
   # Windows (PowerShell)
   Test-Path "$env:LOCALAPPDATA\Graphiti\config\graphiti.config.json"

   # macOS
   cat ~/Library/Preferences/Graphiti/graphiti.config.json

   # Linux
   cat ~/.config/graphiti/graphiti.config.json
   ```

3. Check `daemon.enabled` is set to `true`:
   ```bash
   # Use platform-specific path from above
   grep enabled <config-file>
   ```

4. View logs for errors:
   ```bash
   graphiti-mcp daemon logs
   ```

**Issue: Connection refused**:

1. Verify daemon is running:
   ```bash
   curl http://127.0.0.1:8321/health
   ```

2. Check port is not in use by another service:
   ```bash
   # Windows
   netstat -ano | findstr :8321

   # macOS/Linux
   lsof -i :8321
   ```

3. Try changing port in config:
   ```json
   {
     "daemon": {
       "port": 8322
     }
   }
   ```

**Issue: Daemon crashes repeatedly**:

1. Check logs for crash reason:
   ```bash
   graphiti-mcp daemon logs
   ```

2. Common causes:
   - Database connection failed (verify Neo4j credentials)
   - API key invalid (verify OpenAI/Anthropic key)
   - Port already in use (change port in config)

3. Bootstrap service will auto-restart crashed daemon (check logs)

---

## Step-by-Step Setup

### S1: Clone

```bash
# Clone from your fork (or upstream if not forked)
git clone https://github.com/RoscoeTheDog/graphiti
cd graphiti

# Optional: Add upstream remote to pull updates from original repo
git remote add upstream https://github.com/getzep/graphiti.git
```

**Attribution**: This is a fork of [Graphiti by Zep](https://github.com/getzep/graphiti), customized for your use case.

### S2: Virtual Environment

```bash
# Create
python -m venv .venv

# Activate
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux

# Verify
where python                 # Windows
which python                 # macOS/Linux
```

### S3: Dependencies

**Agent Workflow** (P7: Non-Intrusive Installation):
```
Agent: "I need to install dependencies:
        [Lists packages from setup.py/requirements.txt]

        This will run: pip install -e .
        Scope: Project-local (in your active virtual environment)
        Impact: Adds packages to .venv only (not system-wide)

        Proceed? [Y/N]"

User: "Y"

Agent: [Executes installation]
```

**Manual Installation**:
```bash
pip install -e .
```

### S4: Database (Interactive)

**Prompt**: "Which method?" (see [Options](#installation-options))

#### If Opt1: Neo4j Community Edition (Windows Service) - **RECOMMENDED** (Cost-Effective)

**One-time setup (30-60min) for $0 forever vs $780/year**

**See**: `CLAUDE_INSTALL_NEO4J_COMMUNITY_WINDOWS_SERVICE.md` for complete step-by-step setup
**See**: `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md` for all known issues with solutions

**Quick Requirements Checklist**:
1. ✅ Java 21 (install FIRST): `choco install temurin21 -y`
2. ✅ Manual Neo4j ZIP download from neo4j.com (Chocolatey package is 6+ years old)
3. ✅ PowerShell restart after Java install
4. ✅ Claude Code restart to see Java on PATH
5. ✅ Use Windows Service mode (NOT console mode - blocks terminal)
6. ✅ Explicitly start service: `Start-Service Neo4j`

**All 8 issues are documented with exact solutions** - Follow the guides and you'll be setup reliably.

#### If Opt2: Neo4j Aura (Cloud) - **Quick Start Alternative**

**5-10min setup but $780/year ongoing cost**

1. **Account**: Visit [Neo4j Aura](https://console.neo4j.io), sign up, create instance
2. **Connection**: Copy URI, username, password from Aura console
3. **⚠️ CRITICAL - URI Scheme for VMs**:
   ```bash
   # For VMs (Proxmox, VMware, VirtualBox, Hyper-V, WSL2):
   NEO4J_URI=neo4j+ssc://xxxxx.databases.neo4j.io  # Use +ssc (NOT +s)

   # For bare metal (physical machines):
   NEO4J_URI=neo4j+ssc://xxxxx.databases.neo4j.io  # +ssc works everywhere

   # Common credentials:
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_from_aura
   ```

**Why `neo4j+ssc://` instead of `neo4j+s://`**:
- ✅ Accepts Neo4j Aura's self-signed certificates
- ✅ Prevents "Unable to retrieve routing information" errors in VMs
- ✅ Works on both VMs and bare metal
- ✅ Fully encrypted (TLS/SSL)

**See**: `CLAUDE_INSTALL_NEO4J_AURA.md` for detailed Aura setup with VM fixes

**Choose Aura if**: Prototyping, multi-VM access needed, cost not a concern, want zero setup hassle

#### If Opt3: Neo4j Docker

```bash
docker run -d \
  --name graphiti-neo4j \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest

# Env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### S5: API Keys (Interactive)

**Prompt**: "Which LLM provider?"

#### OpenAI ✅WML
1. Visit [platform.openai.com](https://platform.openai.com), sign up/login, create API key
2. Env: `OPENAI_API_KEY=sk-xxxxx`

#### Anthropic ⚠️
1. Visit [console.anthropic.com](https://console.anthropic.com), create API key
2. Env: `ANTHROPIC_API_KEY=sk-ant-xxxxx`

#### Azure OpenAI ⚠️
1. Get endpoint and API key from Azure portal
2. Env: `AZURE_OPENAI_API_KEY=xxxxx`, `AZURE_OPENAI_ENDPOINT=https://...`

---

## Environment Configuration

### Create .env

```bash
cp .env.example .env

# Edit
notepad .env                # Windows
nano .env                   # macOS/Linux
```

### Required Vars

```bash
# Database (Neo4j Aura - RECOMMENDED)
NEO4J_URI=neo4j+ssc://xxxxx.databases.neo4j.io  # Use +ssc for VMs!
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_from_aura

# LLM (choose one)
OPENAI_API_KEY=sk-your-key

# Optional (if using alternative providers)
# ANTHROPIC_API_KEY=sk-ant-xxxxx
# AZURE_OPENAI_API_KEY=xxxxx
# AZURE_OPENAI_ENDPOINT=https://...
```

### Platform-Specific

**W**: Paths with backslashes: `C:\\Users\\Name\\Documents\\graphiti\\data`
**M/L**: Paths with forward slashes: `/Users/Name/Documents/graphiti/data`

---

## Validation

### Auto-Validation

```bash
# Test database connection
python -c "from graphiti_core import Graphiti; print('✅ Database connection OK')"

# Test MCP server manually
python mcp_server/graphiti_mcp_server.py
# Should start without errors (Ctrl+C to stop)
```

### Manual

```bash
# Database (Neo4j Aura with +ssc scheme)
python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('neo4j+ssc://xxxxx.databases.neo4j.io', auth=('neo4j', 'your_password')); driver.verify_connectivity(); print('✅ Connected')"

# LLM
python -c "import openai; openai.api_key = 'sk-your-key'; print('✅ API key set')"
```

### Daemon Installation Verification

After installing the daemon (optional standalone mode), verify the installation:

#### Directory Structure Verification

The v2.1 architecture uses platform-specific paths following industry conventions (Ollama, VS Code pattern):

**Windows (PowerShell)**:
```powershell
# Installation directory (executables and libraries)
Test-Path "$env:LOCALAPPDATA\Programs\Graphiti"       # Should return True
Test-Path "$env:LOCALAPPDATA\Programs\Graphiti\bin"   # Should return True
Test-Path "$env:LOCALAPPDATA\Programs\Graphiti\lib"   # Should return True

# Configuration and state directory
Test-Path "$env:LOCALAPPDATA\Graphiti\config"         # Should return True
Test-Path "$env:LOCALAPPDATA\Graphiti\logs"           # Should return True
Test-Path "$env:LOCALAPPDATA\Graphiti\data"           # Should return True
```

**macOS**:
```bash
# Installation directory
ls -la ~/Library/Application\ Support/Graphiti/

# Configuration
ls -la ~/Library/Preferences/Graphiti/

# Logs
ls -la ~/Library/Logs/Graphiti/

# Data/Cache
ls -la ~/Library/Caches/Graphiti/
```

**Linux**:
```bash
# Installation directory (XDG_DATA_HOME)
ls -la ~/.local/share/graphiti/

# Configuration (XDG_CONFIG_HOME)
ls -la ~/.config/graphiti/

# State - logs and data (XDG_STATE_HOME)
ls -la ~/.local/state/graphiti/
```

**Expected directory structure (v2.1)**:

**Windows**:
```
%LOCALAPPDATA%\Programs\Graphiti\     <- Executables + frozen libs
├── bin\                              # CLI wrappers
├── lib\                              # Frozen packages (mcp_server, graphiti_core)
├── VERSION                           # Version tracking
└── INSTALL_INFO                      # Installation metadata

%LOCALAPPDATA%\Graphiti\              <- Config + runtime
├── config\graphiti.config.json       # Daemon configuration
├── logs\                             # Bootstrap and MCP server logs
└── data\                             # Runtime data
```

**macOS**:
```
~/Library/Application Support/Graphiti/   <- Executables + frozen libs
├── bin/
├── lib/
├── VERSION
└── INSTALL_INFO

~/Library/Preferences/Graphiti/           <- Configuration
└── graphiti.config.json

~/Library/Logs/Graphiti/                  <- Logs

~/Library/Caches/Graphiti/                <- Runtime data
```

**Linux** (XDG Base Directory spec):
```
~/.local/share/graphiti/              <- Executables + frozen libs
├── bin/
├── lib/
├── VERSION
└── INSTALL_INFO

~/.config/graphiti/                   <- Configuration
└── graphiti.config.json

~/.local/state/graphiti/              <- State (logs + data)
├── logs/
└── data/
```

#### Service Verification (Optional - Requires Admin Privileges)

**Windows (NSSM)**:
```powershell
# Check service status
nssm status graphiti-mcp-daemon
# Expected: SERVICE_STOPPED (registered) or SERVICE_RUNNING (if started)

# Start service (optional)
nssm start graphiti-mcp-daemon

# Check health endpoint (after service started)
Invoke-WebRequest http://localhost:6274/health
# Expected: HTTP 200 with JSON response
```

**macOS (launchd)**:
```bash
# Check service loaded
launchctl list | grep graphiti
# Expected: Service listed with PID if running

# Load service (if not already loaded)
launchctl load ~/Library/LaunchAgents/com.graphiti.mcp.daemon.plist

# Check health endpoint
curl -f http://localhost:6274/health
# Expected: HTTP 200 with JSON response
```

**Linux (systemd)**:
```bash
# Check service status
systemctl --user status graphiti-mcp-daemon
# Expected: active (running) or inactive (dead, but registered)

# Start service (optional)
systemctl --user start graphiti-mcp-daemon

# Check health endpoint
curl -f http://localhost:6274/health
# Expected: HTTP 200 with JSON response
```

#### CLI Wrapper Verification

```bash
# Windows (PowerShell)
& "$env:LOCALAPPDATA\Programs\Graphiti\bin\graphiti-mcp.cmd" --help

# macOS
~/Library/Application\ Support/Graphiti/bin/graphiti-mcp --help

# Linux
~/.local/share/graphiti/bin/graphiti-mcp --help
```

**Expected**: Help text showing available commands (daemon, health, etc.)

#### Independence Verification

To verify daemon runs independently of project directory:

1. Start daemon service (see above)
2. Verify health endpoint responds
3. Change to different directory: `cd /tmp` or `cd %TEMP%`
4. Verify health endpoint still responds
5. Daemon should continue running without project directory

**See also**: `mcp_server/tests/README_E2E.md` for complete manual testing guide

---

## Troubleshooting

### Error→Fix Matrix

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: graphiti_core` | Dependencies not installed | Verify venv active (`which python`), reinstall: `pip install -e .` |
| `Unable to retrieve routing information` | **VM SSL routing error** | Change URI to `neo4j+ssc://` (NOT `neo4j+s://`) - See VM section |
| DB connection failed (Aura) | Wrong URI scheme or wrong creds | Verify URI uses `neo4j+ssc://`, check username/password |
| DB connection failed (Local) | DB not running / wrong creds | Docker: `docker ps` \| Service: `sc query Neo4j` / `brew services list` |
| API key invalid | Wrong key / not activated | Verify in provider dashboard, check .env for spaces, verify permissions |
| Permission denied (W) | PowerShell execution policy | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `python` not found (W) | Not in PATH | Use `py` instead or add Python to PATH |
| SSL cert errors (M) | Cert issues | `pip install --upgrade certifi` |
| Missing build tools (L) | No compiler | `sudo apt install build-essential python3-dev` |
| Empty Neo4j logs (Local) | **Java 21 missing** | Install Java: `choco install temurin21 -y`, restart PowerShell |
| Neo4j service won't start (Local) | **Silent Java failure** | Verify Java: `java -version`, see troubleshooting doc |
| Terminal blocked by Neo4j | **Console mode** instead of service | Use Windows Service mode, NOT console mode |

### VM-Specific Troubleshooting (Proxmox, VMware, VirtualBox, Hyper-V, WSL2)

**Symptom**: `Unable to retrieve routing information` error

**Root Cause**: Neo4j Aura's self-signed certificates don't work with `neo4j+s://` scheme in VM environments

**Solution**:
```bash
# Change URI scheme from neo4j+s:// to neo4j+ssc://
# Before (BROKEN in VMs):
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io

# After (WORKS in VMs):
NEO4J_URI=neo4j+ssc://xxxxx.databases.neo4j.io
```

**Validation**: Test connection with updated URI:
```bash
python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('neo4j+ssc://xxxxx.databases.neo4j.io', auth=('neo4j', 'password')); driver.verify_connectivity(); print('✅ VM connection OK')"
```

**See**: `SETUP_AGENT_INSTRUCTIONS.md` § "Step 4: Fix URI Scheme for VMs"

---

## Next Steps

After install:
1. **Docs**: [Graphiti Documentation](https://github.com/getzep/graphiti/blob/main/README.md)
2. **Examples**: `examples/` directory
3. **Community**: [Discord](https://discord.com/invite/W8Kw6bsgXQ)
4. **Paper**: [arXiv:2501.13956](https://arxiv.org/abs/2501.13956)

### For Devs

- Read `CLAUDE.md` (runtime docs)
- Read `CONFIGURATION.md` (unified configuration system)
- Setup hooks: `pre-commit install` (if applicable)
- Run tests: `pytest tests/`

---

## Uninstallation

If you need to remove the Graphiti MCP Bootstrap Service, standalone uninstall scripts are provided for all platforms.

### Quick Uninstall

**Windows** (Run as Administrator):
```powershell
cd path\to\graphiti\mcp_server\daemon
.\uninstall_windows.ps1
```

**macOS**:
```bash
cd path/to/graphiti/mcp_server/daemon
./uninstall_macos.sh
```

**Linux**:
```bash
cd path/to/graphiti/mcp_server/daemon
./uninstall_linux.sh
```

### What Gets Removed

- OS service (Windows Service, launchd agent, or systemd service)
- Installation directory with virtual environment and frozen packages:
  - **Windows**: `%LOCALAPPDATA%\Programs\Graphiti\`
  - **macOS**: `~/Library/Application Support/Graphiti/`
  - **Linux**: `~/.local/share/graphiti/`
- Service logs:
  - **Windows**: `%LOCALAPPDATA%\Graphiti\logs\`
  - **macOS**: `~/Library/Logs/Graphiti/`
  - **Linux**: `~/.local/state/graphiti/logs/`

### What Gets Preserved (by default)

- Your data:
  - **Windows**: `%LOCALAPPDATA%\Graphiti\data\`
  - **macOS**: `~/Library/Caches/Graphiti/`
  - **Linux**: `~/.local/state/graphiti/data/`
- Configuration:
  - **Windows**: `%LOCALAPPDATA%\Graphiti\config\graphiti.config.json`
  - **macOS**: `~/Library/Preferences/Graphiti/graphiti.config.json`
  - **Linux**: `~/.config/graphiti/graphiti.config.json`

Use `--delete-all` (Unix) or `-DeleteAll` (Windows) to remove everything including data.

### Standalone Scripts

The uninstall scripts can run **without Python or the repository** being present, making them suitable for recovery scenarios:

```bash
# Download script if repository deleted
curl -L https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/daemon/uninstall_macos.sh -o /tmp/uninstall.sh
chmod +x /tmp/uninstall.sh
/tmp/uninstall.sh
```

### Manual Steps After Uninstall

After running the script, you'll need to:

1. **Remove from Claude Desktop config**:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Remove from PATH** (if added):
   - Windows: System Properties → Environment Variables
   - macOS/Linux: Edit `~/.zshrc`, `~/.bashrc`, or `~/.bash_profile`

3. **Restart Claude Desktop**

For detailed instructions, troubleshooting, and manual removal steps, see [docs/UNINSTALL.md](../../docs/UNINSTALL.md).

---

## Known Issues & Workarounds

### Documented Historical Issues

All known issues are documented in detail:

1. **VM SSL Routing Errors** - Fixed with `neo4j+ssc://` URI scheme
   - See: `CLAUDE_INSTALL_NEO4J_AURA.md`
   - See: `SETUP_AGENT_INSTRUCTIONS.md`

2. **Neo4j Community Edition Windows Service (7 Major Issues)** - All documented with workarounds
   - See: `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md`
   - Includes: Java 21 requirement, silent failures, command syntax changes, etc.

3. **Environment Variable Propagation** - PowerShell/Claude Code restart required
   - See troubleshooting sections in this doc

4. **Chocolatey Neo4j Package Outdated** - Use manual ZIP download instead
   - Package version: 3.5.1 (2019) - UNUSABLE
   - Required version: 2025.09.0+
   - See: `CLAUDE_INSTALL_NEO4J_COMMUNITY_WINDOWS_SERVICE.md`

---

## Changelog

See [claude-mcp-installer/instance/CLAUDE_INSTALL_CHANGELOG.md](./CLAUDE_INSTALL_CHANGELOG.md)

---

## Support

- **Upstream Issues**: `https://github.com/getzep/graphiti/issues` (original repo)
- **Fork Issues**: `https://github.com/RoscoeTheDog/graphiti/issues` (your fork)
- **Upstream Discussions**: `https://github.com/getzep/graphiti/discussions`
- **Discord**: [Zep Community](https://discord.com/invite/W8Kw6bsgXQ)

---

**Template**: v1.3.0 | **Guide**: v1.1.0 (Graphiti - Enhanced with Historical Fixes)
**Attribution**: Forked from [Graphiti by Zep](https://github.com/getzep/graphiti) - [arXiv:2501.13956](https://arxiv.org/abs/2501.13956)
