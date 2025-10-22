# CLAUDE_CHANGELOG.md

> **For AI Agents**: This is a living changelog documenting all deviations from the upstream Graphiti repository.
> Follow these principles when updating:
> - **Document Everything**: Every configuration change, package modification, or setup deviation must be logged
> - **Follow Convention**: Use [Keep a Changelog](https://keepachangelog.com/) format
> - **Cross-Reference**: Link to `CLAUDE_INSTALL.md` when changes affect installation steps
> - **Verify First**: Only document changes after successful verification
> - **Bidirectional Updates**: When updating this file, also update `CLAUDE_INSTALL.md` if installation steps changed

## Changelog Format

```markdown
## [Date] - YYYY-MM-DD
### Added/Changed/Deprecated/Removed/Fixed/Security
- **Component**: Description of change
  - Reason: Why this change was made
  - Impact: What this affects
  - Related: Link to relevant sections in CLAUDE_INSTALL.md
```

---

## [Unreleased] - Current Working State

### Summary
Repository is in **vanilla state** (matches upstream), using **Neo4j Aura (Cloud)** backend with system environment variables for configuration. Zero local database setup required.

**IMPORTANT**: VM users must use `neo4j+ssc://` URI scheme instead of `neo4j+s://` to avoid routing errors.

**NEW**: Idiot-proof setup with automated script (`setup-graphiti-env.ps1`) and AI agent instructions (`SETUP_AGENT_INSTRUCTIONS.md`).

---

## [2025-10-22 Final Update] - Platform Prerequisite Checks

### Changed
- **AI Agent Setup Instructions**: Enhanced with comprehensive prerequisite checks
  - **Step 0.1**: PowerShell execution policy verification (Windows)
    - Detects `Restricted` policy that blocks scripts
    - Provides commands to enable script execution
    - Falls back to manual setup if policy cannot be changed
  - **Step 0.2**: Administrator privilege elevation testing (Windows)
    - Tests current privilege level
    - Validates elevation capability with temporary test file
    - Falls back to credential file creation + manual instructions if elevation fails
  - **Fallback Strategy**: Creates credentials.txt and instructs user to run setup script manually with admin privileges
  - **Reason**: AI agents cannot always elevate privileges or modify execution policies
  - **Impact**: Setup works even in restricted corporate environments
  - **Related**: See SETUP_AGENT_INSTRUCTIONS.md § "Prerequisites Check"

### Benefits
- ✅ **Handles restricted environments**: Detects and works around Group Policy restrictions
- ✅ **Clear fallback path**: Creates credentials file + provides manual setup instructions
- ✅ **No surprises**: Tests prerequisites before attempting automated setup
- ✅ **Corporate-friendly**: Works in enterprise environments with locked-down policies

---

## [2025-10-22 Final] - Idiot-Proof Setup Process

### Added
- **Automated Setup Script**: `setup-graphiti-env.ps1` in repository root
  - **Auto-elevation**: Automatically requests Administrator privileges if needed
  - **Credential parsing**: Reads from `credentials.txt` file (Neo4j Aura format)
  - **VM detection**: Auto-detects Virtual Machines and fixes URI scheme
  - **Built-in validation**: Verifies environment variables after setting
  - **Error handling**: Clear messages for missing files, permissions, etc.
  - **Related**: See CLAUDE_INSTALL.md § "Method 2: Automated PowerShell Script"

- **AI Agent Setup Instructions**: `SETUP_AGENT_INSTRUCTIONS.md`
  - **Interactive setup**: Step-by-step instructions for AI agents
  - **Credential elicitation**: Prompts user if credentials.txt not found
  - **Platform-agnostic**: Works on Windows, macOS, Linux
  - **Validation guidance**: Includes troubleshooting steps
  - **Related**: See CLAUDE_INSTALL.md § "Method 1: AI Agent Setup"

- **Credentials Template**: `credentials.txt.template`
  - **Safe to commit**: Template file (actual credentials.txt is gitignored)
  - **Clear instructions**: Comments explain each field
  - **Copy-paste ready**: Just fill in values from Neo4j Aura

### Changed
- **CLAUDE_INSTALL.md**: Restructured to show 3 setup methods
  1. **AI Agent Setup** (Recommended - Most flexible)
  2. **Automated Script** (Best for credentials file)
  3. **Manual Setup** (Fallback)

- **.gitignore**: Added `credentials.txt` to prevent credential commits
  - **Safe**: User can create credentials.txt without risk of committing secrets
  - **Template tracked**: credentials.txt.template IS committed for reference

### Benefits
- ✅ **One-command setup**: `.\setup-graphiti-env.ps1` does everything
- ✅ **No admin confusion**: Script auto-elevates to Administrator
- ✅ **VM-aware**: Automatically fixes neo4j+s:// → neo4j+ssc:// in VMs
- ✅ **Error-proof**: Clear messages for every failure scenario
- ✅ **AI-assisted alternative**: Agent can set up interactively without script
- ✅ **Cross-platform**: AI agent instructions work on any OS

---

## [2025-10-22 Late Evening] - Critical VM Fix: Neo4j URI Scheme

### Fixed
- **Neo4j Connection Routing Errors in VMs**: Changed URI scheme from `neo4j+s://` to `neo4j+ssc://`
  - **Problem**: "Unable to retrieve routing information" error when connecting from Virtual Machines (Proxmox, VMware, VirtualBox, etc.)
  - **Root Cause**: Neo4j Aura uses self-signed SSL certificates, but `neo4j+s://` scheme requires CA-signed certificates. VM environments fail SSL certificate chain validation during routing protocol discovery
  - **Fix**: Use `neo4j+ssc://` scheme which accepts self-signed certificates
  - **Impact**: Connection now works reliably from all VM environments
  - **Related**: See CLAUDE_INSTALL.md § "VM Troubleshooting: Neo4j Routing Errors"

### Changed
- **Environment Variable Scripts**: Updated to use `neo4j+ssc://` by default
  - **File**: `setup-graphiti-env-vars-final.ps1`
  - **Change**: `NEO4J_URI` now uses `neo4j+ssc://YOUR_INSTANCE_ID.databases.neo4j.io`
  - **Reason**: Prevent VM routing errors out of the box
  - **Impact**: Setup works on first try for VM users

- **Documentation**: Added comprehensive VM troubleshooting section
  - **Added Section**: "VM Troubleshooting: Neo4j Routing Errors" in CLAUDE_INSTALL.md
  - **Content**: URI scheme comparison table, step-by-step fix, root cause explanation
  - **Related**: See CLAUDE_INSTALL.md lines 513-562

### Technical Details

**URI Scheme Comparison**:
| Scheme | Encryption | Certificate Requirement | Use Case |
|--------|------------|-------------------------|----------|
| `neo4j+s://` | ✅ Encrypted | CA-signed certificates | Bare metal systems |
| `neo4j+ssc://` | ✅ Encrypted | Accepts self-signed | VMs, containers, WSL2 |
| `neo4j://` | ❌ Unencrypted | None | Local development only |

**Why VMs Fail with neo4j+s://**:
1. Neo4j Python async driver uses routing protocol to discover cluster topology
2. Routing requires SSL handshake with certificate validation
3. VMs often have incomplete/misconfigured root CA certificate chains
4. Neo4j Aura uses self-signed certificates (not CA-signed)
5. `neo4j+s://` rejects self-signed → routing fails
6. `neo4j+ssc://` accepts self-signed → routing succeeds

**Security Note**: No security degradation - connection remains fully encrypted (TLS/SSL), just uses correct certificate validation for Aura's self-signed certs.

---

## [2025-10-22 Evening] - Neo4j Aura Migration & Environment Variables

### Changed
- **Database Backend**: Migrated from FalkorDB (local Docker) to Neo4j Aura (Cloud)
  - **Reason**: Nested virtualization issues in Proxmox VM prevented Docker Desktop/WSL2 from working reliably; Neo4j Aura bypasses all local setup
  - **Impact**: Zero local infrastructure, works across VM migrations/clones, fully managed cloud database
  - **Related**: See CLAUDE_INSTALL.md § "Set Up Neo4j Aura"

- **Configuration Method**: System environment variables instead of hardcoded config values
  - **Variables Created**:
    - `GRAPHITI_NEO4J_URI` - Connection endpoint (neo4j+s://...)
    - `GRAPHITI_NEO4J_USER` - Database username
    - `GRAPHITI_NEO4J_PASSWORD` - Database password
    - `GRAPHITI_NEO4J_DATABASE` - Database name
  - **Reason**: Secure (not in config files), easy to update, system-wide availability, VM-friendly
  - **Impact**: Change credentials once at system level, applies everywhere
  - **Related**: See CLAUDE_INSTALL.md § "Configure System Environment Variables"

- **MCP Configuration**: Updated to reference environment variables
  - **File**: `C:\Users\Admin\.claude\mcp_servers.json`
  - **Syntax**: `${GRAPHITI_NEO4J_URI}` references system env var
  - **Reason**: Decouples credentials from configuration files
  - **Impact**: Config file can be version controlled safely
  - **Related**: See CLAUDE_INSTALL.md § "Configure MCP Server"

### Added
- **PowerShell Setup Scripts**: Automated environment variable configuration
  - **Files**:
    - `setup-graphiti-env-vars.ps1` - Sets environment variables (requires admin)
    - `verify-graphiti-env-vars.ps1` - Verifies variables are set correctly
  - **Location**: `C:\Users\Admin\Downloads\`
  - **Reason**: Automate setup process, reduce human error
  - **Impact**: One-command setup for environment variables
  - **Related**: See CLAUDE_INSTALL.md § "Setup Scripts"

### Removed
- **Docker/FalkorDB Configuration**: Removed all Docker-related setup
  - **Files Removed**:
    - `C:\Users\Admin\.graphiti\docker-compose.yml` (no longer needed)
  - **Reason**: Neo4j Aura eliminates need for local database
  - **Impact**: No Docker Desktop requirement, no WSL2 requirement, no virtualization issues

- **Backend-Specific Dependencies**: No longer need FalkorDB or Kuzu extras
  - **Previous**: `graphiti-core[falkordb]` or `graphiti-core[kuzu]`
  - **Current**: `graphiti-core` (vanilla) - Neo4j support included by default
  - **Reason**: Neo4j is the default/primary backend for Graphiti
  - **Impact**: Simpler dependency management

### Benefits of Neo4j Aura Setup
- ✅ **Zero local setup** - No Docker, no WSL, no database installation
- ✅ **Nested VM friendly** - Works in Windows VM on Proxmox without virtualization issues
- ✅ **VM migration ready** - Clone VM, update env vars, works immediately
- ✅ **Concurrent access** - Multiple Claude Code instances work simultaneously
- ✅ **Free tier** - 200k nodes + 400k relationships (sufficient for personal use)
- ✅ **Fully managed** - No backups, updates, or maintenance needed
- ✅ **Always available** - Cloud-based, accessible from anywhere

### Documentation Enhanced
- **Git Workflow Section**: Added comprehensive guide on fork management
  - Explains what files to commit vs gitignore
  - Documents syncing strategy with upstream
  - Clarifies dependency installation and VM migration workflow
  - Reason: Help future AI agents understand repository structure and maintenance
  - Related: See CLAUDE_INSTALL.md § "Git Workflow & Fork Management"

- **Dependency Management Section**: Added explanation of `uv sync` and virtual environments
  - Clarifies that `.venv/` is local and OS-specific
  - Documents multi-platform lock file behavior
  - Explains isolated installation vs system-wide
  - Reason: Prevent confusion about what gets committed and how dependencies work
  - Related: See CLAUDE_INSTALL.md § "What `uv sync` Does"

---

## [2025-10-22 Afternoon] - FalkorDB Migration & Repo Cleanup (SUPERSEDED)

### Changed
- **Database Backend**: Migrated from Kuzu to FalkorDB
  - **Reason**: Kuzu is embedded (single-process), causing connection failures when multiple Claude Code instances attempt concurrent access
  - **Impact**: Enables multiple Claude Code instances to use Graphiti memory simultaneously
  - **Related**: See CLAUDE_INSTALL.md § "Configure FalkorDB Backend"

- **Database Port**: FalkorDB configured on port 6380 (instead of default 6379)
  - **Reason**: Reserve port 6379 for future Django/Celery Redis integration
  - **Impact**: Prevents port conflicts with other Redis instances
  - **Related**: See CLAUDE_INSTALL.md § "Create Docker Compose Configuration"

- **Deployment Method**: Docker with auto-restart policy
  - **Reason**: Enable automatic startup on system boot with no manual intervention
  - **Impact**: FalkorDB always available after system restart
  - **Configuration**: `restart: unless-stopped` in docker-compose.yml
  - **Related**: See CLAUDE_INSTALL.md § "Start FalkorDB Service"

### Removed
- **Kuzu Integration**: All Kuzu-specific code reverted
  - **Files Restored**:
    - `mcp_server/graphiti_mcp_server.py` - Removed KuzuDriver imports and initialization
    - `mcp_server/pyproject.toml` - Removed local file dependency and kuzu package
    - `mcp_server/uv.lock` - Regenerated without kuzu dependencies
  - **Files Deleted**:
    - `INSTALL.md` - Removed untracked custom installation document
  - **Reason**: Return to vanilla upstream state for easier maintenance and updates
  - **Verification**: `git status` shows clean working directory

### Added
- **Docker Compose Configuration**: `~/.graphiti/docker-compose.yml` (external to repo)
  - **Location**: `C:\Users\Admin\.graphiti\docker-compose.yml` (Windows)
  - **Reason**: Keep infrastructure configuration separate from source code
  - **Impact**: FalkorDB runs as isolated Docker service
  - **Related**: See CLAUDE_INSTALL.md § "Configure FalkorDB Backend"

- **Living Documentation**: Two documentation files for agent guidance
  - **CLAUDE_INSTALL.md**: Step-by-step installation instructions
  - **CLAUDE_CHANGELOG.md**: This file - configuration change history
  - **Reason**: Enable future AI agents to replicate exact setup on new systems
  - **Impact**: Reduces setup time and errors through documented, verified procedures

---

## [2025-10-19] - Initial Kuzu Attempt (REVERTED)

### Changed (REVERTED on 2025-10-22)
- **Database Backend**: Modified to use Kuzu (embedded database)
  - **Files Modified**:
    - `mcp_server/graphiti_mcp_server.py` - Added KuzuDriver integration
    - `mcp_server/pyproject.toml` - Changed to local file dependency, added kuzu package
    - `mcp_server/uv.lock` - Updated for kuzu dependencies
  - **Files Created**:
    - `INSTALL.md` - Custom installation notes
  - **Reason**: Attempt to simplify setup by eliminating external database server requirement
  - **Problem Discovered**: Kuzu's embedded nature prevents concurrent access from multiple processes
  - **Resolution**: Reverted all changes on 2025-10-22, migrated to FalkorDB

---

## Platform-Specific Notes

### Windows (Primary Platform)
- **Tested On**: Windows 11 (MSYS_NT-10.0-26100)
- **Docker**: Docker Desktop required
- **Path Format**: Use double backslashes in JSON configs: `C:\\Users\\Admin\\...`
- **Package Manager**: uv installed via pip or standalone installer
- **Status**: ✅ Fully tested and verified

### macOS (Untested)
- **Docker**: Docker Desktop or Colima recommended
- **Path Format**: Unix-style paths: `/Users/<username>/...`
- **Package Manager**: uv via curl installer or pip
- **Status**: ⚠️ Not yet verified - needs testing

### Linux (Untested)
- **Docker**: Docker Engine or Docker Desktop
- **Path Format**: Unix-style paths: `/home/<username>/...`
- **Package Manager**: uv via curl installer or pip
- **Status**: ⚠️ Not yet verified - needs testing

---

## Configuration Deviations from Upstream

### 1. Database Backend Selection
- **Upstream Default**: Neo4j (client-server, requires separate service)
- **Our Configuration**: FalkorDB (client-server, Redis-based, Docker-deployed)
- **Reason**:
  - Lighter weight than Neo4j
  - Supports concurrent connections (unlike Kuzu)
  - No foreground service distraction (runs in Docker)
  - Reserves standard Redis port for future Celery use

### 2. Port Allocation
- **Standard Redis**: Port 6379
- **Our FalkorDB**: Port 6380
- **Reason**: Future Django/Celery integration will need port 6379

### 3. Docker Networking
- **Network Name**: `graphiti-network`
- **Network Type**: Bridge (isolated)
- **Reason**: Clean separation from other Docker services

### 4. Data Persistence
- **Volume Name**: `falkordb-data`
- **Mount Point**: `/var/lib/falkordb/data`
- **Reason**: Preserve graph data across container restarts and system reboots

---

## MCP Server Environment Variables

### Current Configuration (FalkorDB)
```bash
FALKORDB_HOST=localhost
FALKORDB_PORT=6380
OPENAI_API_KEY=sk-XXXXXXXX
MODEL_NAME=gpt-4o-mini
```

### Previous Configuration (Kuzu - DEPRECATED)
```bash
KUZU_DB_PATH=C:/Users/Admin/.graphiti/kuzu.db  # No longer used
```

### Original Configuration (Neo4j - Upstream Default)
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

---

## Dependencies

### Current (FalkorDB)
```toml
[project.dependencies]
mcp = ">=1.5.0"
openai = ">=1.68.2"
graphiti-core = ">=0.14.0"  # With [falkordb] extra
azure-identity = ">=1.21.0"
```

### Removed (Kuzu)
```toml
# Previously added, now removed:
graphiti-core = "@ file:///${PROJECT_ROOT}/.."  # Local file dependency
kuzu = ">=0.11.2"                                # Kuzu package
```

---

## Testing Checklist

When making changes to this setup, verify the following:

- [ ] FalkorDB container starts automatically after system reboot
- [ ] Port 6380 is accessible: `netstat -an | grep 6380`
- [ ] Port 6379 remains available: `netstat -an | grep 6379` (should be empty)
- [ ] First Claude Code instance can connect to Graphiti MCP server
- [ ] Second Claude Code instance can connect simultaneously (concurrent access test)
- [ ] Data persists after container restart: `docker restart graphiti-falkordb`
- [ ] MCP server tools work (add_memory, search_memory_nodes, search_memory_facts)
- [ ] `git status` shows clean working directory (no modifications to tracked files)

---

## Known Issues

### Issue: None currently documented
*Document issues as they arise with format:*
```markdown
### Issue: Brief Description
- **Symptoms**: What goes wrong
- **Workaround**: Temporary fix
- **Status**: Open/In Progress/Resolved
```

---

## Future Considerations

### Planned Changes
1. **Platform Verification**: Test installation on macOS and Linux
2. **Authentication**: Consider adding FalkorDB authentication if exposing publicly
3. **Monitoring**: Add health check endpoint or monitoring solution
4. **Backup Strategy**: Implement automated backup of falkordb-data volume

### Questions for Future Investigation
1. Does FalkorDB support cluster mode for even higher concurrency?
2. What are the performance implications of running both FalkorDB and Celery Redis?
3. Should we consider Redis Sentinel for high availability?

---

## Principles & Best Practices

### Configuration Management
1. **Keep Repo Clean**: No local modifications to tracked files
2. **External Infrastructure**: Docker configs live outside repository
3. **Environment Variables**: Sensitive data (API keys) never committed
4. **Version Control**: Document all deviations from upstream

### Documentation Updates
1. **Before Changes**: Read this changelog and CLAUDE_INSTALL.md
2. **During Changes**: Take notes on what's being modified and why
3. **After Verification**: Update both documents with verified information
4. **Commit Pattern**: Separate commits for code changes vs. documentation updates

### Testing Requirements
1. **Verify Locally**: Test all changes on your local system first
2. **Concurrent Testing**: Always test with multiple Claude Code instances
3. **Persistence Testing**: Verify data survives restarts
4. **Clean State**: Ensure `git status` is clean after configuration changes

---

**Changelog Maintained By**: AI Agents (Claude)
**Last Updated**: 2025-10-22
**Repository State**: Vanilla (matches upstream getzep/graphiti)
**Configuration State**: FalkorDB on port 6380 via Docker
