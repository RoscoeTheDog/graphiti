# Claude MCP Installer Templates - Agent Entrypoint

**Version**: 1.3.0 | **Updated**: 2025-10-30 | **Purpose**: AI agent development entrypoint

---

## System

Living documentation templates (2-3 docs):
```
CLAUDE_README.md (this) → agent entrypoint + policies
CLAUDE_INSTALL.md → install guide template (user-facing)
CLAUDE_INSTALL_CHANGELOG.md → version history template (no-git mode only)
CLAUDE_MIGRATE.md → one-time migration wizard
```

**Universal Application**: Templates work for any software project requiring environment setup/configuration.

---

## Policies (MANDATORY)

### P0: Git-First Version Control

**RULE**: git-repo? → use-commits | no-git? → use-changelog-file

**Detection**:
```bash
[ -d ".git" ] → git-mode | [ ! -d ".git" ] → changelog-mode
```

**Git Mode** (git repo exists):
```
CLAUDE_INSTALL.md:updated → commit+push (IMMEDIATE)
⊗ NEVER update CLAUDE_INSTALL_CHANGELOG.md file
✓ Version history tracked via git commits
```

**Changelog Mode** (no git repo):
```
CLAUDE_INSTALL.md:updated → CLAUDE_INSTALL_CHANGELOG.md:add-entry + version++
✓ Use CLAUDE_INSTALL_CHANGELOG.md as version history
```

**Commit Format (Git Mode)**:
```
docs(install): [Title] (vX.Y.Z)

- [change-1]
- [change-2]
- Version: [old] → [new] ([version-type])
- Validation: [status-updates]
```

**Rationale**: git=canonical-history, avoid-dual-systems, commits>changelog-files

### P1: Update Trigger

**MUST update CLAUDE_INSTALL.md when**:
```
code-change?(install|prereq|env|config|platform) → update-required
```

**Triggers**:
- install: procedures, options, steps
- prereq: Python version, dependencies, system requirements
- env: API keys, env vars, .env structure
- config: config files, settings, special permissions
- platform: OS support changes

### P2: Changelog Strategy

**Strategy**:
```
git-repo-exists? → commit-based (P0) | no-git? → file-based (CLAUDE_INSTALL_CHANGELOG.md)
```

### P3: Semantic Versioning

**Version Logic**:
```
breaks-existing-setup? → MAJOR (X.0.0)
adds-feature?(backward-compat) → MINOR (0.X.0)
fixes|clarifies?(no-breaking) → PATCH (0.0.X)
```

**MAJOR Examples**: Python3.10→3.11, removed-option, renamed-env-vars, config-structure-change
**MINOR Examples**: new-install-option, new-optional-dep, new-env-var(optional), enhanced-instructions
**PATCH Examples**: typos, clarifications, validation-badge-updates, broken-link-fixes

### P4: Installation Interaction

**RULE**: ALWAYS prompt for install choices, NEVER store preferences (no Graphiti memory)

**Rationale**: install=infrequent, control>convenience

### P5: Validation Tracking

**Badges**:
- ✅ Validated: tested+working (platform+date)
- ⚠️ Experimental: untested|partial
- ❌ Deprecated: no-longer-recommended

**Format**: `Option: Neo4j Aura ✅ [2025-10-25, W11+M14]`

**Update-When**: test-success | dep-version-change | user-issue | platform-change

### P6: MCP Server Configuration Detection

**RULE**: Detect MCP servers → check install state → elicit credentials → configure Claude Code CLI

### P7: Non-Intrusive Installation

**RULE**: ALWAYS prompt for confirmation before system/environment changes. NEVER install packages or modify global config without explicit user approval.

**Rationale**: installation=system-changes, control>automation, transparency>convenience

**Applies To**:
```
system-changes:
├─ package-install (pip, npm, apt, brew, etc.)
├─ global-env-vars (system environment variables)
├─ service-install (databases, runtimes, background processes)
├─ system-config (PATH modifications, registry edits, etc.)
└─ file-creation (outside project directory)

project-changes (OK without prompt):
├─ .env file creation/editing (project-local)
├─ venv creation/activation (project-local)
├─ project-dependencies (pip install -r requirements.txt in active venv)
└─ project-config (config files within project directory)
```

**Confirmation Format**:
```
About to perform system change:
→ Action: [install python-package "requests" via pip]
→ Scope: [system-wide] OR [project-local (venv)]
→ Impact: [adds dependency to system Python] OR [adds to project venv only]
→ Reversible: [yes - pip uninstall requests] OR [no - requires manual cleanup]

Proceed? [Y/N]
```

**Examples**:

**✅ CORRECT - Prompt First**:
```
Agent: "I need to install the Neo4j Python driver. This will run:
        pip install neo4j

        In your active virtual environment (project-local).
        Proceed? [Y/N]"

User: "Y"
Agent: [Executes: pip install neo4j]
```

**❌ WRONG - No Prompt**:
```
Agent: [Silently executes: pip install neo4j]
Agent: "Installed Neo4j driver."
```

**✅ CORRECT - Batch Prompt**:
```
Agent: "I need to install 5 dependencies from requirements.txt:
        - neo4j==5.15.0
        - python-dotenv==1.0.0
        - anthropic==0.18.0
        - tavily-python==0.3.0
        - openai==1.12.0

        This will run: pip install -r requirements.txt
        In your active virtual environment (project-local).
        Proceed? [Y/N]"
```

**✅ CORRECT - System Change**:
```
Agent: "To add OPENAI_API_KEY to system environment:

        Windows (PowerShell):
        [Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-...', 'User')

        This is OPTIONAL. You can also:
        - Store in .env file only (project-local, recommended)
        - Set manually later via Windows GUI

        Add to system environment now? [Y/N]"
```

**Exceptions (NO PROMPT NEEDED)**:
```
✓ Reading files (always safe)
✓ Creating .env in project directory (project-local)
✓ Creating venv in project directory (project-local)
✓ Installing deps in active venv from requirements.txt (project-scoped)
✓ Git operations in project repo (clone, commit, push - project-scoped)
✓ Running validation scripts (read-only operations)
```

**Integration with P6** (MCP Server Config):
```
Phase 0: Installation state check → run claude mcp list (read-only, OK)
Phase 1: Project detection → search files (read-only, OK)
Phase 2: Credential elicitation → prompt user (interactive, OK)
Phase 3: Configure MCP server → PROMPT before: claude mcp add-json (system change)
         "About to add MCP server to global Claude Code config:
          → Command: claude mcp add-json --scope user [server-name]
          → Scope: User-wide (available in all projects)
          → Location: ~/.claude.json
          Proceed? [Y/N]"
Phase 4: Verification → claude mcp list (read-only, OK)
```

**Update Trigger**:
```
P7 policy added/changed? → MINOR version (new feature, backward-compatible)
CLAUDE_INSTALL.md updated with confirmation prompts? → include in same commit
```

**Phase 0: Installation State Check** (Execute FIRST, before any detection):
```
Run: claude mcp list
Extract: {server-name} from README/directory/package-metadata
Search output for: {server-name}

NOT FOUND → fresh-install-flow (Phase 1)
FOUND (user scope) → prompt-wizard ↓
  "Already installed globally. What would you like to do?"
  [1] Update Configuration → load-config + prompt-changes + update
  [2] Repair Installation → verify-paths + test-connection + fix-issues
  [3] Reinstall Completely → remove + fresh-install-flow
  [4] Cancel → exit

FOUND (project scope) → prompt-migration
  "Found in project scope. Migrate to global (user) scope? [Y/N]"
  Y → remove-local + add-user-scope
  N → exit

FOUND (broken/disconnected) → prompt-repair
  "Installation found but not working. Repair? [Y/N]"
  Y → execute-repair-workflow
  N → exit
```

**Phase 1: MCP Project Detection** (If Phase 0 = not found):
```
detect-mcp-project?
├─ Search README.md for: "MCP", "Model Context Protocol", "mcp server"
├─ Search for MCP library imports (language-agnostic):
│  → Python: from fastmcp, from mcp, import mcp
│  → Node.js: require('@modelcontextprotocol/sdk'), import ... from '@modelcontextprotocol/sdk'
│  → Go: import "github.com/modelcontextprotocol/..."
│  → Rust: use mcp::
├─ Search for server entrypoints: server.py, server.js, index.js, main.go, server.ts
├─ Search config files for Claude Desktop mentions

MCP detected? → proceed-to-credential-detection
NOT MCP? → skip-P6 (continue standard workflow)
```

**Credential Detection** (README-first + broad fallback):
```
Primary: README.md
→ Search sections: ## Prerequisites, ## Configuration, ## Setup, ## Environment
→ Extract: Required credentials, optional credentials, descriptions

Secondary: .env.example / config files
→ Search: .env.example, .env.template, example.env, config.example.json
→ Extract: Credential names (keys without values)

Tertiary: Broad code search (all file types, all languages)
→ Python: os.getenv("X"), os.environ.get("X"), os.environ["X"]
→ Node.js: process.env.X
→ Go: os.Getenv("X"), os.LookupEnv("X")
→ Rust: env::var("X"), std::env::var("X")
→ Ruby: ENV["X"], ENV.fetch("X")
→ PHP: getenv("X"), $_ENV["X"]
→ Generic: UPPERCASE_SNAKE_CASE in any config file

Runtime Detection:
→ Python project (requirements.txt, *.py) → python or python3 → which/where
→ Node project (package.json, *.js/*.ts) → node or npx → which/where
→ Go project (go.mod, *.go) → compiled binary path
→ Rust project (Cargo.toml, *.rs) → compiled binary path

Entrypoint Detection:
→ Files matching: server.*, main.*, index.* (root or src/)
→ Files with MCP library imports
→ package.json "main" field
→ pyproject.toml [tool.poetry.scripts]
→ README run command
```

**Conventional Naming Recognition**:
```
Auto-recognize patterns:
→ *_API_KEY, *_KEY, *_TOKEN, *_SECRET, *_PASSWORD → sensitive (mask)
→ *_URL, *_ENDPOINT, *_HOST, *_PORT, *_TIMEOUT → configuration (OK to show)

Common credentials:
→ OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY
→ TAVILY_API_KEY, SERPER_API_KEY
→ GITHUB_TOKEN, GITHUB_PERSONAL_ACCESS_TOKEN
→ DATABASE_URL, POSTGRES_URL, MONGODB_URI

If pattern unknown:
→ "Is {CREDENTIAL} a sensitive value (API key, token, password)? [Y/N]"
```

**Credential Elicitation**:
```
For each required credential:

1. Check system environment
   → Run: echo $CREDENTIAL (Unix) or echo %CREDENTIAL% (Windows)
   → If found: "✓ {CREDENTIAL} found in system environment"
   → If not found: "✗ {CREDENTIAL} not found"

2. Elicit value
   If found in system:
     "Use existing system value for {CREDENTIAL}? [Y/N]"
     → Y: Use system value (don't show or re-enter)
     → N: "Enter new value:" [masked input]

   If not found in system:
     "Please provide {CREDENTIAL}:"
     [Masked input: ●●●●●●●●●●●●]
     → Display: "✓ Received: {first-4}****...****{last-4}"

3. System environment setup (optional)
   "Add {CREDENTIAL} to system environment variables? [Y/N]"
   → Y: Provide platform-specific instructions (PowerShell, GUI, Bash, Zsh)
   → N: Skip (stored only in ~/.claude.json)

4. Important note displayed:
   "⚠️  Claude Code CLI stores LITERAL VALUES in ~/.claude.json
       (not variable references like ${VAR} or %VAR%).
       If you change env vars later, you MUST re-run installation."
```

**Configuration Generation**:
```
Generate: claude mcp add-json --scope user {server-name} '{
  "type":"stdio",
  "command":"{absolute-runtime-path}",
  "args":["{absolute-entrypoint-path}"],
  "env":{
    "{CREDENTIAL_1}":"{actual-value}",
    "{CREDENTIAL_2}":"{actual-value}"
  }
}'

Execute → Verify: claude mcp get {server-name}
Update: CLAUDE_INSTALL.md (add MCP Server Integration section)
```

**Update Trigger**:
```
MCP config added/changed? → MINOR version (new feature, backward-compatible)

Commit format (if git mode):
docs(install): Add Claude Code CLI integration (vX.Y.Z)

- Added MCP server configuration section
- Required credentials: {list}
- Optional credentials: {list}
- Platform support: {platforms}
- Validation: ⚠️ until tested
```

---

## Workflow

### Standard Cycle

**Git Mode** (git repo exists):
```
code-change → assess-impact? → (no: done | yes: ↓)
→ update(CLAUDE_INSTALL.md)
→ determine-version-increment
→ update-validation-badges
→ commit(CLAUDE_INSTALL.md + code) + push (IMMEDIATE)
⊗ SKIP CLAUDE_INSTALL_CHANGELOG.md
```

**Changelog Mode** (no git):
```
code-change → assess-impact? → (no: done | yes: ↓)
→ update(CLAUDE_INSTALL.md)
→ determine-version-increment
→ update(CLAUDE_INSTALL_CHANGELOG.md)
→ update-validation-badges
→ save-files
```

### Decision Matrix

```
Changed?                  Update?   Version
────────────────────────  ────────  ───────
prereq                    YES       MINOR|MAJOR
api-keys|env-vars         YES       MINOR|MAJOR
install-steps             YES       MINOR|PATCH
dependencies              YES       MINOR|MAJOR
config-files              YES       MINOR|MAJOR
platform-support          YES       MAJOR
code-logic-only           NO        -
tests-only                NO        -
```

---

## Migration

**Check**: `CLAUDE_MIGRATE.md` exists?

### Option A: Auto-Migration (Recommended)
```
agent:read(CLAUDE_MIGRATE.md) → detect-project → prompt-validate → replace-placeholders → gen-v1.0.0 → update-record
Time: 5-15min
```

### Option B: Manual
```
1. Replace placeholders ([PROJECT_NAME], [REPO_URL], [PYTHON_VERSION])
2. Document current state (prereqs, options, validation)
3. Init changelog (v1.0.0 entry)
```

---

## Template Installation (Quick Start)

### Step 1: Copy Templates
```bash
cd /path/to/your-project
cp /path/to/claude-code-tooling/claude-mcp-installer/* .
```

**Files Copied**:
- ✅ CLAUDE_README.md (this - agent entrypoint)
- ✅ CLAUDE_INSTALL.md (install guide template)
- ✅ CLAUDE_INSTALL_CHANGELOG.md (version history template)
- ✅ CLAUDE_MIGRATE.md (migration wizard)

### Step 2: Run Migration
```
Agent: "I found CLAUDE_MIGRATE.md. Should I run the migration wizard?"
You: "Yes"

Agent will:
1. Detect project details (repo URLs, dependencies, Python version, etc.)
2. Show detected values for your validation
3. Prompt for missing information
4. Update all template placeholders
5. Generate v1.0.0 changelog entry
6. Append migration record to CLAUDE_MIGRATE.md

Time: 5-15 minutes
Result: All templates customized and ready to use
```

### Step 3: Start Development
- **For AI agents**: Point to this file (CLAUDE_README.md) as development entrypoint
- **For humans**: Read this file to understand documentation workflow
- Living documentation system is now active!

---

## Examples (Compact)

### Ex1: New API Key (MINOR) - Git Mode
```
Change: Added ANTHROPIC_API_KEY
Update: CLAUDE_INSTALL.md (prereq section + .env example)
Version: 1.2.0 → 1.3.0
Badge: ⚠️ until tested
Commit: docs(install): Add Anthropic API support (v1.3.0)
        - Added ANTHROPIC_API_KEY to prereqs
        - Updated .env example
        - Version: 1.2.0 → 1.3.0 (MINOR)
        - Validation: ⚠️ until tested
Push: IMMEDIATE
```

### Ex2: Python Version Bump (MAJOR) - Git Mode
```
Change: Python3.10+ → Python3.11+
Update: CLAUDE_INSTALL.md (prereq + migration-note)
Version: 1.9.5 → 2.0.0
Badge: Update all platform validations
Commit: docs(install): BREAKING - Python 3.11+ required (v2.0.0)
        - Python3.10+ → Python3.11+
        - Added migration guide for Python upgrade
        - Version: 1.9.5 → 2.0.0 (MAJOR)
        - Validation: Updated all platform badges
Push: IMMEDIATE
```

### Ex3: Typo Fix (PATCH) - Changelog Mode (no git)
```
Change: Fixed Neo4j connection string typo
Update: CLAUDE_INSTALL.md (fix-typo)
Version: 1.3.2 → 1.3.3
Changelog: CLAUDE_INSTALL_CHANGELOG.md
           [1.3.3] Fixed - Neo4j connection string example
Save: Both files
```

---

## Quick Reference

### Update Decision

```
Changed:            Action:
prereq?         →   update (MINOR|MAJOR)
api|env?        →   update (MINOR|MAJOR)
install?        →   update (MINOR|PATCH)
deps?           →   update (MINOR|MAJOR)
config?         →   update (MINOR|MAJOR)
platform?       →   update (MAJOR)
code-only?      →   no-update
tests-only?     →   no-update
```

### Version Decision

```
breaks-setup?   →   MAJOR
adds-feature?   →   MINOR
fixes-docs?     →   PATCH
```

---

## Template Placeholders

### CLAUDE_INSTALL.md Placeholders

| Placeholder | Example | Description |
|-------------|---------|-------------|
| `[PROJECT_NAME]` | `gptr-mcp` | Your project's name |
| `[DATE]` | `2025-10-25` | Current date |
| `[BASE_PROJECT_NAME]` | `Data Pipeline Framework` | If derived from another project |
| `[BASE_REPO_URL]` | `https://github.com/upstream-org/original-project` | Base repository URL |
| `[YOUR_REPO_URL]` | `https://github.com/your-org/your-project` | Your repository URL |
| `[PYTHON_VERSION]` | `3.11` | Required Python version |
| `[DATABASE]` / `[LLM_PROVIDER]` | `Neo4j` / `OpenAI` | Technologies used |
| `[CLOUD_SERVICE_URL]` | `https://console.neo4j.io` | Cloud service URLs |
| `[DOCS_URL]` | `https://docs.gptr.dev` | Documentation URL |
| `[REPO_URL]` | `https://github.com/user/project` | Repository URL |

---

## Integration with CLAUDE.md (Runtime Docs)

Templates are **separate from** runtime documentation (CLAUDE.md):

| Document | Purpose | When Used | Location |
|----------|---------|-----------|----------|
| **CLAUDE.md** | Runtime agent instructions | Every session (auto-loaded) | Project root (agnostic) |
| **CLAUDE_README.md** | Development policies | Development sessions only | Project root (project-specific) |
| **CLAUDE_INSTALL.md** | Installation guide | Setup/onboarding | Project root (project-specific) |

**Workflow**:
1. CLAUDE.md loaded at session start (agent runtime behavior)
2. Agent navigates to project for development
3. Agent reads CLAUDE_README.md (development policies)
4. Agent updates CLAUDE_INSTALL.md as needed (installation docs)

---

## Attribution

**If Derived Project**: Keep base-project refs in CLAUDE_INSTALL.md, clarify project-specific vs upstream divergence

---

**Template**: v1.2.0 | **Maintained**: Claude Code Tooling Project | **License**: Use freely
