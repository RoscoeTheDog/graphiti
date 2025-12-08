# Graphiti Setup - Quick Start

> **TL;DR**: Run `.\setup-graphiti-env.ps1` with your Neo4j Aura credentials in `credentials.txt`, or ask an AI agent to follow `SETUP_AGENT_INSTRUCTIONS.md`.

## What This Does

Configures environment variables for Graphiti MCP server to connect to Neo4j Aura cloud database.

## Files in This Setup

| File | Purpose | Commit to Git? |
|------|---------|----------------|
| `setup-graphiti-env.ps1` | Automated setup script (PowerShell) | ✅ Yes |
| `SETUP_AGENT_INSTRUCTIONS.md` | AI agent setup guide | ✅ Yes |
| `credentials.txt.template` | Credentials file template | ✅ Yes |
| `credentials.txt` | YOUR actual credentials | ❌ NO (in .gitignore) |
| `CLAUDE_INSTALL.md` | Full installation guide | ✅ Yes |

## Quick Setup Options

### Option 1: AI Agent (Recommended)

**If you have an AI assistant (like Claude Code)**:

```
Please follow the instructions in SETUP_AGENT_INSTRUCTIONS.md to configure
my Graphiti environment variables.
```

The AI will:
- Ask for your Neo4j Aura credentials (or read from credentials.txt)
- Detect if you're in a VM
- Set everything up correctly
- Validate the configuration

### Option 2: Automated Script

**If you have a credentials file**:

1. **Create credentials.txt** from Neo4j Aura:
   ```powershell
   # Copy template
   cp credentials.txt.template credentials.txt

   # Edit with your values from https://console.neo4j.io
   notepad credentials.txt
   ```

2. **Run setup script** (auto-elevates to Admin):
   ```powershell
   .\setup-graphiti-env.ps1
   ```

3. **Done!** Script validates everything.

### Option 3: Manual (If scripts don't work)

See `CLAUDE_INSTALL.md` for detailed manual setup instructions.

## What Gets Set

The setup configures these system environment variables:

```
NEO4J_URI         = neo4j+ssc://xxxxx.databases.neo4j.io  (VM-compatible)
NEO4J_USER        = neo4j
NEO4J_PASSWORD    = your-generated-password
OPENAI_API_KEY    = sk-proj-... (must be set separately)
```

## After Setup

1. **Restart Claude Code** to pick up new environment variables

2. **Install dependencies**:
   ```bash
   cd mcp_server
   uv sync
   ```

3. **Test**: Start Claude Code - Graphiti MCP server should connect

## Troubleshooting

### Script says "credentials.txt not found"
→ Create it from template: `cp credentials.txt.template credentials.txt`
→ Fill in your Neo4j Aura values

### "Unable to retrieve routing information" error
→ You're in a VM - script should auto-fix to `neo4j+ssc://`
→ Verify with: `[Environment]::GetEnvironmentVariable('NEO4J_URI', 'Machine')`
→ Should show `neo4j+ssc://` not `neo4j+s://`

### "Access denied" or permission errors
→ Script auto-elevates - click "Yes" when prompted
→ Or manually run PowerShell as Administrator

### Changes don't take effect
→ Restart Claude Code (or any application)
→ Or restart your system

## More Help

- **Full guide**: `CLAUDE_INSTALL.md`
- **Change history**: `CLAUDE_CHANGELOG.md`
- **VM troubleshooting**: `CLAUDE_INSTALL.md` § "VM Troubleshooting"

## Security Note

- `credentials.txt` is in `.gitignore` - safe to create, won't be committed
- Environment variables are set at system level (secure)
- Only `credentials.txt.template` (empty) is tracked in git

---

**Need help?** Ask an AI agent to follow `SETUP_AGENT_INSTRUCTIONS.md` for interactive setup with validation.
