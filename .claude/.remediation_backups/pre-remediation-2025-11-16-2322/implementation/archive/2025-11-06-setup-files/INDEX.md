# Archive: 2025-11-06 Setup Files

**Archived:** 2025-11-06
**Reason:** Replaced by claude-mcp-installer/ schema
**Original Location:** Project root

---

## Summary

These files were the original installation/setup documentation and scripts located in the project root. They have been replaced by the new `claude-mcp-installer/` directory structure which follows a more organized schema:

- **Templates**: `claude-mcp-installer/templates/` (version controlled, generic)
- **Instance**: `claude-mcp-installer/instance/` (gitignored, platform-specific)

---

## Archived Files (11 files)

### Installation Documentation

| File | Size | Description |
|------|------|-------------|
| CLAUDE_INSTALL.md | 23KB | Main installation guide (TEMPLATE - not populated) |
| CLAUDE_INSTALL_CHANGELOG.md | 4KB | Installation guide changelog (TEMPLATE) |
| CLAUDE_INSTALL_NEO4J_AURA.md | 27KB | Neo4j Aura (cloud) setup guide |
| CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md | 33KB | Neo4j Community Edition troubleshooting (7 major issues) |
| CLAUDE_INSTALL_NEO4J_COMMUNITY_WINDOWS_SERVICE.md | 26KB | Neo4j Community Edition Windows Service setup |

### Setup Scripts & Instructions

| File | Size | Description |
|------|------|-------------|
| SETUP_README.md | 3.5KB | Quick setup overview |
| SETUP_AGENT_INSTRUCTIONS.md | 24KB | AI agent setup instructions (credential elicitation, VM detection) |
| SETUP_STATUS.md | 6KB | Setup status tracking |
| setup-neo4j-aura-env.ps1 | 10KB | PowerShell script for Neo4j Aura environment variables |
| setup-neo4j-community-env.ps1 | 10KB | PowerShell script for Neo4j Community environment variables |
| setup-neo4j-community-wizard.ps1 | 34KB | Interactive wizard for Neo4j Community setup |

---

## New Organization (claude-mcp-installer/)

### Templates (Version Controlled)

Located in `claude-mcp-installer/templates/`:
- `CLAUDE_INSTALL.template.md` - Generic installation template with placeholders
- `CLAUDE_README.md` - Schema documentation

### Instance (Platform-Specific, Gitignored)

Located in `claude-mcp-installer/instance/`:
- `CLAUDE_INSTALL.md` - **Enhanced** with:
  - Fork vs upstream URLs (RoscoeTheDog/graphiti vs getzep/graphiti)
  - All 8 historical Neo4j issues documented
  - VM SSL routing fix (`neo4j+ssc://` scheme)
  - **Neo4j Community Edition recommended** (cost: $0 vs Aura $65/month)
  - Comprehensive troubleshooting
  - Proper attribution to upstream

---

## Key Improvements in New Schema

### 1. Repository Attribution
- **Upstream**: https://github.com/getzep/graphiti (original by Zep)
- **Fork**: https://github.com/RoscoeTheDog/graphiti (your fork)
- Paper citation: [arXiv:2501.13956](https://arxiv.org/abs/2501.13956)

### 2. Cost-Based Recommendation
- **Opt1 (RECOMMENDED)**: Neo4j Community Edition (Windows Service)
  - Cost: $0 forever
  - Setup: 30-60min one-time
  - 8 documented issues with solutions
- **Opt2**: Neo4j Aura (Cloud)
  - Cost: $65/month ($780/year)
  - Setup: 5-10min
  - Good for prototyping, not long-term

### 3. Historical Issues Incorporated
All issues from `CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md`:
1. Chocolatey package outdated (v3.5.1 from 2019) - Use manual ZIP
2. Java 21 silent failures - Install BEFORE Neo4j
3. PowerShell restart required - After Java install
4. Claude Code restart required - To see Java on PATH
5. Command syntax changed - `windows-service install` (NOT `install-service`)
6. Service doesn't auto-start - Explicit `Start-Service Neo4j`
7. Console mode blocks terminal - Use service mode instead
8. VM SSL routing errors - Use `neo4j+ssc://` (NOT `neo4j+s://`)

### 4. VM-Specific Fixes
- Critical `neo4j+ssc://` URI scheme for Proxmox/VMware/VirtualBox/Hyper-V/WSL2
- Prevents "Unable to retrieve routing information" errors
- Works on bare metal too (universal solution)

---

## Restore Instructions

**If you need to restore these files** (not recommended - use new schema instead):

```bash
# Restore all files to project root
cp .claude/implementation/archive/2025-11-06-setup-files/* .

# Or restore specific file
cp .claude/implementation/archive/2025-11-06-setup-files/CLAUDE_INSTALL_NEO4J_COMMUNITY_TROUBLESHOOTING.md .
```

**Note**: The new `claude-mcp-installer/instance/CLAUDE_INSTALL.md` contains all the content from these files PLUS enhancements. Restoring these old files is not necessary.

---

## Migration Benefits

1. **Cleaner root directory** - Setup files moved to dedicated subdirectory
2. **Template/instance separation** - Version control template, gitignore instance
3. **Enhanced content** - New instance file has all historical fixes incorporated
4. **Better organization** - Follows EPHEMERAL-FS and claude-mcp-installer schemas
5. **Cost transparency** - Clear recommendation based on $0 vs $780/year analysis

---

**See Also**:
- `claude-mcp-installer/claude_readme.md` - Installation schema documentation
- `claude-mcp-installer/instance/CLAUDE_INSTALL.md` - Current enhanced installation guide
- `.claude/INDEX.md` - Main ephemeral files index
