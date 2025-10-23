# CLAUDE_INSTALL.md

> **For AI Agents**: This is a living document that instructs how to set up and configure the Graphiti MCP server.
> After making changes to the installation process, you MUST:
> 1. Update this document to reflect the new state
> 2. Add an entry to `CLAUDE_CHANGELOG.md` documenting what changed and why
> 3. Verify the changes work before updating documentation
> 4. Maintain the bidirectional relationship between this document and `CLAUDE_CHANGELOG.md`
> 5. **⚠️ SECURITY**: NEVER commit real credentials. Always use placeholders in examples: `YOUR_PASSWORD_HERE`, `YOUR_INSTANCE_ID`, etc.

## Document Purpose

This document provides step-by-step instructions for setting up the Graphiti MCP server with **Neo4j Aura (Cloud)** backend on a fresh system. It reflects the **current verified working configuration** and should be updated whenever the setup process changes.

## System Requirements

### Tested Platforms
- ✅ **Windows** (MSYS_NT-10.0-26100) - Primary platform, fully tested
- ⚠️ **macOS** - Not yet verified (needs testing)
- ⚠️ **Linux** - Not yet verified (needs testing)

### Prerequisites

1. **Neo4j Aura Account** (for graph database - Cloud/Remote)
   - Sign up: https://neo4j.com/cloud/aura-free/
   - Free tier available (200k nodes + 400k relationships)
   - No local installation required

2. **Python 3.10+** (for Graphiti MCP server)
   - Check version: `python --version`

3. **uv** (Python package manager)
   - Install: `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`

4. **Git** (for cloning repository)

5. **OpenAI API Key** (for LLM operations)
   - Get from: https://platform.openai.com/api-keys

## Installation Steps

### Quick Start Checklist

Follow these steps in order. Each step includes validation to ensure correctness before proceeding.

1. ✅ **Clone Repository** → Verify: `git status` shows clean repo
2. ✅ **Create Neo4j Aura Instance** → Verify: Can log into Neo4j console
3. ✅ **Set Environment Variables** → Verify: Run `verify-graphiti-env-vars.ps1`
4. ✅ **Configure MCP Server** → Verify: File exists at `.claude/mcp_servers.json`
5. ✅ **Validate Environment** → Verify: All variables return values
6. ✅ **Install Dependencies** → Verify: `uv run python -c "import graphiti_core"`
7. ✅ **Test Complete Setup** → Verify: MCP server connects in Claude Code

**Estimated Time**: 15-20 minutes for fresh setup

---

### 1. Clone the Repository

```bash
cd ~/Documents/GitHub  # Or your preferred location (Windows: C:\Users\Admin\Documents\GitHub)
git clone https://github.com/getzep/graphiti.git
cd graphiti
```

**Note**: This uses the upstream repository. If using a fork, adjust the URL accordingly and document in `CLAUDE_CHANGELOG.md`.

### 2. Set Up Neo4j Aura (Cloud Database)

#### Why Neo4j Aura?
- ✅ **Zero local setup** - No Docker, no WSL, no virtualization issues
- ✅ **Free tier available** - 200k nodes + 400k relationships
- ✅ **Concurrent connections** - Multiple Claude Code instances work simultaneously
- ✅ **VM-agnostic** - Works from any system, survives VM migrations/clones
- ✅ **Fully managed** - No maintenance, automatic backups
- ✅ **Native Graphiti support** - Neo4j is the original/primary backend

#### Create Neo4j Aura Instance

1. **Sign up** at https://neo4j.com/cloud/aura-free/
2. **Create a free database instance**:
   - Name: `claude-code-graphiti` (or your preference)
   - Region: Choose closest to you
   - Wait ~60 seconds for provisioning
3. **Download credentials** - Save the credentials file (contains URI, username, password)
4. **Copy credentials** for next step

**Example credentials format**:
```
NEO4J_URI=neo4j+ssc://YOUR_INSTANCE_ID.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_PASSWORD_HERE
```

**⚠️ IMPORTANT - URI Scheme**: Use `neo4j+ssc://` (recommended for all environments):
- ✅ Works on VMs (Proxmox, VMware, VirtualBox, Hyper-V, WSL2)
- ✅ Works on bare metal (Windows, Mac, Linux)
- ✅ Works in Docker containers
- ✅ Accepts Neo4j Aura's self-signed certificates
- ✅ Fully encrypted (TLS/SSL)

**Note**: Neo4j Aura provides `neo4j+s://` in downloaded credentials, but `neo4j+ssc://` is universally compatible. The automated scripts will fix this automatically.

See the [VM Troubleshooting](#vm-troubleshooting-neo4j-routing-errors) section for technical details.

### 3. Configure System Environment Variables

#### Why Environment Variables?
- ✅ **System-wide** - Available to all applications
- ✅ **Secure** - Not stored in config files that might be committed
- ✅ **Easy to update** - Change once, applies everywhere
- ✅ **Team-friendly** - Clone VM, just update env vars

#### Setup Methods

Choose **ONE** of the following methods:

##### Method 1: AI Agent Setup (Recommended - Most Flexible)

**Best for**: Interactive setup with validation and troubleshooting

Ask your AI agent (Claude Code) to follow the instructions in:
```
SETUP_AGENT_INSTRUCTIONS.md
```

The agent will:
- ✅ Check for `credentials.txt` file OR prompt you for credentials
- ✅ Automatically detect if you're in a VM and fix URI scheme
- ✅ Set all environment variables at system level
- ✅ Validate the configuration
- ✅ Guide you through next steps

**Example prompt**:
```
Please follow the instructions in SETUP_AGENT_INSTRUCTIONS.md to configure
my Graphiti environment variables. My credentials are in credentials.txt
(or: I'll provide my Neo4j Aura credentials interactively)
```

##### Method 2: Automated PowerShell Script

**Best for**: Automated setup with credentials file

**Prerequisites**:
1. Create `credentials.txt` in repository root with your Neo4j Aura credentials:
   ```
   NEO4J_URI=neo4j+ssc://xxxxx.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-generated-password
   NEO4J_DATABASE=neo4j
   ```

   **Note**: Use `neo4j+ssc://` for universal compatibility (VMs and bare metal)

**Run the script**:
```powershell
# Script automatically elevates to Administrator if needed
.\setup-graphiti-env.ps1
```

The script will:
- ✅ Check for Admin privileges (auto-elevate if needed)
- ✅ Verify credentials.txt exists
- ✅ Parse credentials from file
- ✅ Auto-detect VM and fix URI scheme if needed
- ✅ Set environment variables
- ✅ Validate configuration
- ✅ Display next steps

**Location**: `C:\Users\Admin\Documents\GitHub\graphiti\setup-graphiti-env.ps1`

##### Method 3: Manual Setup (Fallback)

**Best for**: Custom requirements or troubleshooting

#### Manual Setup (Alternative)

If scripts are not available, set manually via PowerShell (as Administrator):

```powershell
# Use neo4j+ssc:// (recommended for universal compatibility)
[Environment]::SetEnvironmentVariable('NEO4J_URI', 'neo4j+ssc://YOUR_INSTANCE.databases.neo4j.io', 'Machine')
[Environment]::SetEnvironmentVariable('NEO4J_USER', 'neo4j', 'Machine')
[Environment]::SetEnvironmentVariable('NEO4J_PASSWORD', 'YOUR_PASSWORD', 'Machine')
```

#### Environment Variables Created

| Variable Name | Example Value | Purpose |
|---------------|---------------|---------|
| `GRAPHITI_NEO4J_URI` | `neo4j+s://xxx.databases.neo4j.io` | Connection endpoint |
| `GRAPHITI_NEO4J_USER` | `neo4j` | Database username |
| `GRAPHITI_NEO4J_PASSWORD` | `generated-password` | Database password |
| `GRAPHITI_NEO4J_DATABASE` | `neo4j` | Database name |

**Important**: Restart any open applications (including Claude Code) after setting environment variables.

### 4. Configure MCP Server for Claude Code

#### Find Your Configuration File

Claude Code MCP configuration is typically at:
- **Windows**: `C:\Users\Admin\.claude\mcp_servers.json`
- **macOS/Linux**: `~/.claude/mcp_servers.json`

If the file doesn't exist, create it.

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
        "NEO4J_URI": "${GRAPHITI_NEO4J_URI}",
        "NEO4J_USER": "${GRAPHITI_NEO4J_USER}",
        "NEO4J_PASSWORD": "${GRAPHITI_NEO4J_PASSWORD}",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "MODEL_NAME": "gpt-4o-mini"
      }
    }
  }
}
```

**Important Notes**:
- All values use `${VARIABLE}` syntax to reference system environment variables
- `OPENAI_API_KEY` should already be set as a system environment variable
- To verify OpenAI key is set: `[Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'Machine')`
- Adjust `command` path if your `uv` installation differs (find with: `where uv`)
- Adjust `directory` path if your graphiti repo is elsewhere
- On Windows, use double backslashes `\\` in paths
- On Unix systems, adjust paths accordingly (e.g., `/Users/<username>/...`)

**To find your uv path**:
```bash
# Windows
where uv

# Unix
which uv
```

### 5. Validate Environment Variables

Before installing dependencies, verify that all required environment variables are set correctly.

#### Validation Script (Recommended)

If you created the environment variables using the setup script, verify them:

```powershell
cd C:\Users\Admin\Downloads
.\verify-graphiti-env-vars.ps1
```

**Expected Output**:
```
Checking Graphiti system environment variables...
=================================================
✓ GRAPHITI_NEO4J_URI = neo4j+s://xxx.databases.neo4j.io
✓ GRAPHITI_NEO4J_USER = neo4j
✓ GRAPHITI_NEO4J_PASSWORD = GgY-tiSw3***
✓ GRAPHITI_NEO4J_DATABASE = neo4j
✓ GRAPHITI_AURA_INSTANCE_ID = YOUR_INSTANCE_ID
✓ GRAPHITI_AURA_INSTANCE_NAME = claude-code-graphiti
=================================================
All variables are set correctly!
```

#### Manual Validation (Alternative)

Verify each variable individually in PowerShell:

```powershell
# Check Neo4j Aura connection details
[Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_URI', 'Machine')
# Should return: neo4j+s://xxx.databases.neo4j.io

[Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_USER', 'Machine')
# Should return: neo4j

[Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_PASSWORD', 'Machine')
# Should return: your-generated-password

[Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_DATABASE', 'Machine')
# Should return: neo4j
```

**Validate OpenAI API Key** (should already exist):

```powershell
[Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'Machine')
# Should return: sk-proj-... (your API key)
```

#### Troubleshooting Validation

**If variables return blank/null**:

1. **Verify you ran the setup script as Administrator**:
   ```powershell
   # Run PowerShell as Administrator, then:
   cd C:\Users\Admin\Downloads
   .\setup-graphiti-env-vars.ps1
   ```

2. **Check if variables are set at User level instead** (wrong scope):
   ```powershell
   [Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_URI', 'User')
   # If this returns a value but 'Machine' doesn't, re-run setup script as Admin
   ```

3. **Restart your shell/terminal** - PowerShell may need to reload environment:
   - Close and reopen PowerShell
   - Or restart your system

**If OpenAI API key is missing**:

```powershell
# Set it as a system variable (PowerShell as Administrator):
[Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-proj-YOUR_KEY_HERE', 'Machine')
```

#### Validation Checklist

Before proceeding, confirm:

- [ ] `GRAPHITI_NEO4J_URI` is set and starts with `neo4j+s://`
- [ ] `GRAPHITI_NEO4J_USER` is set (typically `neo4j`)
- [ ] `GRAPHITI_NEO4J_PASSWORD` is set (your generated password)
- [ ] `GRAPHITI_NEO4J_DATABASE` is set (typically `neo4j`)
- [ ] `OPENAI_API_KEY` is set and starts with `sk-proj-` or `sk-`
- [ ] All variables are at **Machine** level (not User level)

**Once all variables are validated**, proceed to install dependencies.

---

### 6. Install Graphiti MCP Server Dependencies

```bash
cd C:\Users\Admin\Documents\GitHub\graphiti\mcp_server  # Adjust path as needed

# Install dependencies (uses vanilla graphiti-core, no special backend needed)
uv sync

# Verify installation
uv run python -c "from graphiti_core import Graphiti; print('Graphiti installed successfully')"
```

**Note**: No need to install `graphiti-core[falkordb]` or `graphiti-core[kuzu]` - Neo4j support is included by default in the core package.

#### What `uv sync` Does

`uv sync` synchronizes your project's dependencies based on `pyproject.toml` and `uv.lock`:

1. **Reads dependency declarations** from `pyproject.toml`
2. **Uses exact versions** from `uv.lock` (reproducible builds)
3. **Creates virtual environment** in `.venv/` directory (isolated from system Python)
4. **Installs packages** with OS-specific binaries when needed
5. **Fast and cached** - typically completes in 1-2 minutes on first run

**Key Points**:
- ✅ **Local installation** - Creates `.venv/` in the `mcp_server/` directory
- ✅ **Not system-wide** - Doesn't affect other Python projects or system Python
- ✅ **OS-agnostic workflow** - Works identically on Windows/Linux/macOS
- ✅ **Deletable** - Can delete `.venv/` and re-run `uv sync` anytime
- ✅ **Isolated** - Each project has its own environment

#### Dependency Files

| File | Purpose | Git Tracked | OS-Specific |
|------|---------|-------------|-------------|
| `pyproject.toml` | Declares dependencies | ✅ Yes | ❌ No |
| `uv.lock` | Pins exact versions | ✅ Yes | ⚠️ Multi-platform |
| `.venv/` | Virtual environment | ❌ No (.gitignore) | ✅ Yes |
| Installed packages | Actual libraries | ❌ No | ✅ Yes |

#### VM Migration / Clone Workflow

When you clone your VM or set up on a new system:

1. **Git clone** brings source code + dependency declarations
2. **Run `uv sync`** to install dependencies for the new OS
3. **Set environment variables** using setup script
4. **Ready to go** - Dependencies are automatically OS-appropriate

Example:
```bash
# On new system (any OS)
git clone https://github.com/your-fork/graphiti.git
cd graphiti/mcp_server
uv sync  # Automatically installs correct binaries for this OS
```

#### Post-Installation Validation

After `uv sync` completes, verify the installation:

**1. Check virtual environment was created**:
```bash
# Should see .venv directory
ls C:\Users\Admin\Documents\GitHub\graphiti\mcp_server\.venv

# Or on Unix
ls ~/Documents/GitHub/graphiti/mcp_server/.venv
```

**2. Verify Graphiti can be imported**:
```bash
cd C:\Users\Admin\Documents\GitHub\graphiti\mcp_server
uv run python -c "from graphiti_core import Graphiti; print('✓ Graphiti installed successfully')"
```

**Expected Output**: `✓ Graphiti installed successfully`

**3. Verify Neo4j driver is available**:
```bash
uv run python -c "from graphiti_core.driver.neo4j_driver import Neo4jDriver; print('✓ Neo4j driver available')"
```

**Expected Output**: `✓ Neo4j driver available`

**4. Check MCP server can be found**:
```bash
ls C:\Users\Admin\Documents\GitHub\graphiti\mcp_server\graphiti_mcp_server.py
# Should show the file exists
```

#### Installation Troubleshooting

**If `uv sync` fails**:

1. **Check uv is installed**:
   ```bash
   uv --version
   # Should show: uv 0.x.x
   ```

2. **Verify Python version**:
   ```bash
   python --version
   # Should be 3.10 or higher
   ```

3. **Clear cache and retry**:
   ```bash
   uv cache clean
   uv sync
   ```

4. **Check network connection** - `uv sync` downloads packages from PyPI

**If imports fail after installation**:

```bash
# Ensure you're running commands with 'uv run' prefix
uv run python -c "import graphiti_core"

# Or activate virtual environment first:
# Windows:
.venv\Scripts\activate
python -c "import graphiti_core"

# Unix:
source .venv/bin/activate
python -c "import graphiti_core"
```

---

### 7. Verification & Testing

Now that environment variables are set and dependencies are installed, verify the complete setup.

#### Test 1: Environment Variables (Re-check)
```powershell
# Verify environment variables are set (PowerShell)
[Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_URI', 'Machine')
[Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_USER', 'Machine')
[Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_PASSWORD', 'Machine')
```

#### Test 2: Neo4j Aura Connection
1. Go to Neo4j Aura console: https://console.neo4j.io
2. Click on your database instance
3. Click "Open with" → "Neo4j Browser"
4. Should connect automatically (validates your instance is running)

#### Test 3: MCP Server Connection
1. **Restart Claude Code** (to pick up environment variables)
2. Check MCP servers status (should show graphiti-memory as connected)
3. Try using Graphiti tools:
   - `add_memory` - Add a test memory
   - `search_memory_nodes` - Search for nodes
   - `search_memory_facts` - Search for facts

#### Test 4: Concurrent Access ⭐
1. Open first Claude Code instance
2. Use Graphiti memory tools
3. Open second Claude Code instance simultaneously
4. Both should be able to use Graphiti without conflicts ✅

#### Test 5: VM Migration/Clone (Important!)
1. Clone or migrate your Windows VM to another system
2. Update environment variables with Neo4j Aura credentials
3. Restart Claude Code
4. Graphiti should work immediately without any database setup ✅

### 8. Troubleshooting

#### Environment Variables Not Found
```bash
# Restart Claude Code after setting environment variables
# Or restart your entire system

# Verify they're set at system level
powershell -Command "[Environment]::GetEnvironmentVariable('GRAPHITI_NEO4J_URI', 'Machine')"
```

#### MCP Server Connection Issues
- Check `uv` command path is correct in config
- Verify OPENAI_API_KEY is valid
- Check Neo4j Aura instance is running (console.neo4j.io)
- Review MCP server logs in Claude Code
- Ensure you restarted Claude Code after setting env vars

#### Neo4j Aura Connection Errors
- Verify credentials are correct
- Check instance is "Running" in Aura console
- Wait 60 seconds after creating instance (initial provisioning)
- Ensure firewall allows outbound HTTPS (port 443)

#### "Cannot connect to database" Error
- Verify `NEO4J_URI` uses `neo4j+s://` protocol (secure)
- Check no typos in environment variable names
- Confirm password is exactly as generated (case-sensitive)

#### VM Troubleshooting: Neo4j Routing Errors

**Symptom**: "Unable to retrieve routing information" error when connecting to Neo4j Aura from a Virtual Machine.

**Error in logs**:
```
neo4j.exceptions.ServiceUnavailable: Unable to retrieve routing information
```

**Root Cause**:
Neo4j Aura uses self-signed SSL certificates, but the `neo4j+s://` URI scheme requires CA-signed certificates. In VM environments (Proxmox, VMware, VirtualBox, Hyper-V), the SSL certificate chain validation fails during the routing protocol discovery phase.

**The Fix**: Change URI scheme from `neo4j+s://` to `neo4j+ssc://`

**URI Scheme Comparison**:
| Scheme | Encryption | Certificate Requirement | Compatibility | Recommended |
|--------|------------|-------------------------|---------------|-------------|
| `neo4j+ssc://` | ✅ Encrypted | Accepts self-signed | ✅ Universal (VMs, bare metal, containers) | ⭐ **Yes** |
| `neo4j+s://` | ✅ Encrypted | CA-signed certificates | ⚠️ Bare metal only (fails in VMs) | No |
| `neo4j://` | ❌ Unencrypted | None | ⚠️ Local development only | No |

**Step-by-Step Fix**:

1. **Update environment variable** (PowerShell as Administrator):
   ```powershell
   [Environment]::SetEnvironmentVariable('NEO4J_URI', 'neo4j+ssc://YOUR_INSTANCE.databases.neo4j.io', 'Machine')
   ```

2. **Verify the change**:
   ```powershell
   [Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')
   # Should return: neo4j+ssc://xxx.databases.neo4j.io
   ```

3. **Restart Claude Code** to pick up the new environment variable

4. **Test connection** - MCP server should now connect successfully

**Why This Works**:
- Neo4j Aura actually uses self-signed certificates (not CA-signed)
- `neo4j+ssc://` tells the driver to accept self-signed certs
- The connection remains fully encrypted (TLS/SSL)
- No security downgrade - just correct certificate validation

**Recommended URI Scheme**:
- **⭐ All Neo4j Aura connections**: Use `neo4j+ssc://` (universally compatible)
  - ✅ Works on VMs (Proxmox, VMware, VirtualBox, Hyper-V)
  - ✅ Works on bare metal (Windows, Mac, Linux)
  - ✅ Works in Docker containers
  - ✅ Works in WSL2
  - ✅ Fully encrypted (TLS/SSL)
- **Local Neo4j Desktop only**: Use `bolt://localhost:7687`

**Note**: `neo4j+s://` works on bare metal but fails in VMs. Since `neo4j+ssc://` works everywhere, it's the recommended choice for Neo4j Aura.

## Current Configuration Summary

| Component | Configuration | Reason |
|-----------|---------------|--------|
| **Database Backend** | Neo4j Aura (Cloud) | Zero setup, free tier, concurrent access |
| **Database Location** | Remote (neo4j+ssc://xxx.databases.neo4j.io) | Universal compatibility, VM-agnostic |
| **Configuration Method** | System environment variables | Secure, system-wide, easy to update |
| **Python Package Manager** | uv | Fast, reliable dependency management |
| **Graphiti Version** | Vanilla upstream (no custom modifications) | Clean state, easy to update |

## Benefits of This Setup

✅ **No Docker required** - Bypasses Docker/WSL/virtualization issues entirely
✅ **No local database** - No services to manage, no disk space used
✅ **VM migration friendly** - Clone VM, update env vars, works immediately
✅ **Concurrent access** - Multiple Claude Code instances work simultaneously
✅ **Free tier** - 200k nodes + 400k relationships (plenty for personal use)
✅ **Always available** - Cloud-based, accessible from anywhere
✅ **Fully managed** - Neo4j handles backups, updates, maintenance

## Git Workflow & Fork Management

### What's in Your Fork vs Upstream

This repository is a **fork** of the upstream `getzep/graphiti`. Here's what's tracked:

#### Files Committed to Your Fork

**Custom Documentation** (Option A - Recommended):
- ✅ `CLAUDE_INSTALL.md` - This installation guide
- ✅ `CLAUDE_CHANGELOG.md` - Configuration change history
- ✅ `SETUP_STATUS.md` - Current setup status (optional)

**Upstream Files** (Tracked by Default):
- ✅ `pyproject.toml` - Dependency declarations
- ✅ `uv.lock` - Exact version pins
- ✅ All source code (`graphiti_core/`, `mcp_server/`, etc.)
- ✅ `.gitignore` - Already properly configured

#### Files NOT Committed (Gitignored)

**Local Environment**:
- ❌ `.venv/` - Virtual environment (OS-specific)
- ❌ `__pycache__/` - Python bytecode cache
- ❌ `*.pyc` - Compiled Python files
- ❌ `.pytest_cache/` - Test cache

**Secrets & Configuration**:
- ❌ `.env` - Environment variable files
- ❌ `.claude/` - Your personal Claude Code config
- ❌ Credential files

**System-Specific**:
- ❌ `.DS_Store` - macOS metadata
- ❌ `.idea/` - JetBrains IDE settings
- ❌ `.vscode/` - VS Code settings

### Syncing with Upstream

When upstream `getzep/graphiti` releases updates:

```bash
# Add upstream remote (one-time setup)
git remote add upstream https://github.com/getzep/graphiti.git

# Fetch latest from upstream
git fetch upstream

# Merge upstream changes into your fork
git merge upstream/main

# If conflicts occur with CLAUDE_*.md files, keep your versions:
git checkout --ours CLAUDE_INSTALL.md CLAUDE_CHANGELOG.md
git add CLAUDE_INSTALL.md CLAUDE_CHANGELOG.md
git commit -m "Merge upstream, preserve custom docs"

# Re-sync dependencies after merge
cd mcp_server
uv sync
```

### Why Custom Docs Won't Conflict

Your custom documentation files (`CLAUDE_INSTALL.md`, `CLAUDE_CHANGELOG.md`) are:
- ✅ **New files** - Don't exist in upstream
- ✅ **Won't conflict** - Unless upstream adds same-named files (unlikely)
- ✅ **Preserves knowledge** - Setup instructions travel with the repo
- ✅ **Version controlled** - Changes tracked over time

### Committing Your Custom Docs

```bash
# Check current status
cd C:\Users\Admin\Documents\GitHub\graphiti
git status

# Add custom documentation
git add CLAUDE_INSTALL.md CLAUDE_CHANGELOG.md

# Commit with clear message
git commit -m "Add custom installation docs for Neo4j Aura setup with environment variables"

# Push to your fork
git push origin main
```

### Repository State After Setup

```
graphiti/ (your fork)
├── .git/                           ← Git repository
├── .gitignore                      ← Properly configured (from upstream)
├── pyproject.toml                  ← Dependency declarations (upstream)
├── uv.lock                         ← Lock file (upstream)
├── CLAUDE_INSTALL.md              ← YOUR custom doc ✅ Commit this
├── CLAUDE_CHANGELOG.md            ← YOUR custom doc ✅ Commit this
├── graphiti_core/                 ← Source code (upstream)
├── mcp_server/                    ← MCP server code (upstream)
│   ├── .venv/                     ← Local environment ❌ NOT committed
│   ├── pyproject.toml             ← Upstream
│   └── uv.lock                    ← Upstream
└── ...

External (not in repo):
C:\Users\Admin\.claude\
├── mcp_servers.json               ← Your MCP config (local, not committed)

C:\Users\Admin\Downloads\
├── setup-graphiti-env-vars.ps1    ← Setup script (local, not committed)
└── verify-graphiti-env-vars.ps1   ← Verification script (local, not committed)
```

### Clean Git Status

After committing your docs, `git status` should show:

```bash
On branch main
Your branch is ahead of 'origin/main' by 1 commit.
  (use "git push" to publish your local commits)

nothing to commit, working tree clean
```

This confirms:
- ✅ All source code unchanged (vanilla upstream)
- ✅ Custom docs committed and tracked
- ✅ `.venv/` and other local files properly ignored

## Related Documentation

- See `CLAUDE_CHANGELOG.md` for history of configuration changes
- See `setup-graphiti-env-vars.ps1` for environment variable setup script
- See `verify-graphiti-env-vars.ps1` for verification script
- See upstream docs: https://github.com/getzep/graphiti
- See Neo4j Aura docs: https://neo4j.com/docs/aura/

---

**Last Updated**: 2025-10-22
**Last Verified By**: Claude (Sonnet 4.5)
**Platform**: Windows (MSYS_NT-10.0-26100)
**Database**: Neo4j Aura Free Tier
