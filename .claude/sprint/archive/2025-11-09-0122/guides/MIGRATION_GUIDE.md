# Migration Guide: Environment Variables → Unified Configuration

## Overview

This guide helps you migrate from the old scattered configuration system (multiple `.env` files + `graphiti-filter.config.json`) to the new unified `graphiti.config.json` system.

**Timeline**: 15-30 minutes for most projects

---

## Why Migrate?

### Old System (Before)

**Problems:**
- ❌ Configuration scattered across 3+ files
- ❌ 17+ environment variables to manage
- ❌ Difficult to switch database backends
- ❌ Hard to version control (sensitive data mixed with config)
- ❌ No clear defaults or documentation

### New System (After)

**Benefits:**
- ✅ Single `graphiti.config.json` file for all settings
- ✅ Only 5-8 environment variables (secrets only)
- ✅ Easy database switching: change one field
- ✅ Version controlled config (secrets in `.env`)
- ✅ Type-safe validation with clear error messages
- ✅ Graceful defaults for all settings

---

## Migration Checklist

- [ ] **Step 1**: Back up existing configuration
- [ ] **Step 2**: Run migration script (automatic)
- [ ] **Step 3**: Review generated `graphiti.config.json`
- [ ] **Step 4**: Test with MCP server
- [ ] **Step 5**: Customize settings (optional)
- [ ] **Step 6**: Commit config to git
- [ ] **Step 7**: Clean up deprecated files

---

## Step 1: Back Up Existing Configuration

Before starting, create backups of your current configuration:

```bash
# Navigate to your Graphiti project
cd /path/to/graphiti

# Back up environment files
cp .env .env.backup.$(date +%Y%m%d)
cp mcp_server/.env.example mcp_server/.env.example.backup

# Back up filter config (if exists)
cp graphiti-filter.config.json graphiti-filter.config.json.backup 2>/dev/null || true

# Verify backups
ls -la *.backup*
```

---

## Step 2: Run Migration Script (Automatic)

The migration script will automatically convert your environment variables to the new config format.

### Option A: Automatic Migration (Recommended)

```bash
# Run migration script
python scripts/migrate-to-unified-config.py

# Expected output:
# 📦 Graphiti Configuration Migration Tool
#
# Found existing configuration:
#   .env: 12 variables
#   graphiti-filter.config.json: Found
#
# ✅ Generated: graphiti.config.json
# ✅ Generated: .env (minimal)
# ✅ Backed up: .env.backup, graphiti-filter.config.json.backup
#
# Migration complete! Review graphiti.config.json and test your server.
```

### Option B: Manual Migration

If you prefer to migrate manually, see [Manual Migration](#manual-migration-detailed) section below.

---

## Step 3: Review Generated Configuration

Open `graphiti.config.json` and verify the settings:

```bash
# View generated config
cat graphiti.config.json

# Or open in editor
code graphiti.config.json  # VS Code
nano graphiti.config.json  # Terminal editor
```

**What to check:**

1. **Database settings** - Verify URI, user, and password reference
   ```json
   "database": {
     "backend": "neo4j",
     "neo4j": {
       "uri": "bolt://localhost:7687",  // ← Check this
       "user": "neo4j",                 // ← Check this
       "password_env": "NEO4J_PASSWORD" // ← Env var name
     }
   }
   ```

2. **LLM settings** - Verify provider and models
   ```json
   "llm": {
     "provider": "openai",              // ← Check this
     "default_model": "gpt-4.1-mini",   // ← Check this
     "openai": {
       "api_key_env": "OPENAI_API_KEY"  // ← Env var name
     }
   }
   ```

3. **Memory filter** - Verify enabled and providers
   ```json
   "memory_filter": {
     "enabled": true,                   // ← Check this
     "llm_filter": {
       "providers": [...]               // ← Check providers
     }
   }
   ```

4. **New `.env` file** - Should only contain secrets
   ```bash
   # View new minimal .env
   cat .env

   # Expected content (only secrets):
   NEO4J_PASSWORD=your_password
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

---

## Step 4: Test with MCP Server

Test that your migrated configuration works:

```bash
# Start MCP server
python -m mcp_server.graphiti_mcp_server

# Expected output (check logs):
# INFO - Loading config from: /path/to/graphiti/graphiti.config.json
# INFO - Successfully loaded config from: /path/to/graphiti/graphiti.config.json
# INFO - Initialized neo4j database connection
# INFO - Initialized openai LLM provider: gpt-4.1-mini
# INFO - Memory filtering enabled
# INFO - MCP server started
```

**If you see errors:**

1. **Config validation error**
   ```
   ERROR - Failed to load config: 1 validation error for GraphitiConfig
   ```
   → Check JSON syntax in `graphiti.config.json`
   → Verify all required fields are present

2. **Missing environment variable**
   ```
   ERROR - NEO4J_PASSWORD not found in environment
   ```
   → Check `.env` file exists and contains the variable
   → Ensure `.env` is in the project root

3. **Connection error**
   ```
   ERROR - Failed to connect to Neo4j database
   ```
   → Verify database is running
   → Check `database.neo4j.uri` in config

---

## Step 5: Customize Settings (Optional)

Now that migration is complete, you can customize your configuration:

### Switch Database Backend

```json
{
  "database": {
    "backend": "falkordb",  // ← Changed from "neo4j"
    "falkordb": {
      "uri": "redis://localhost:6379",
      "password_env": "FALKORDB_PASSWORD",
      "database": "my_graph"
    }
  }
}
```

### Switch LLM Provider

```json
{
  "llm": {
    "provider": "anthropic",  // ← Changed from "openai"
    "default_model": "claude-sonnet-3-5-20241022",
    "anthropic": {
      "api_key_env": "ANTHROPIC_API_KEY"
    }
  }
}
```

### Adjust Memory Filter

```json
{
  "memory_filter": {
    "enabled": false,  // ← Disable filtering
    // OR customize categories:
    "llm_filter": {
      "categories": {
        "store": ["env-quirk", "user-pref"],  // ← Only these
        "skip": ["bug-in-code", "first-success"]
      }
    }
  }
}
```

### Configure for Production

```json
{
  "database": {
    "neo4j": {
      "pool_size": 100,           // ← Increased from 50
      "connection_timeout": 60    // ← Increased from 30
    }
  },
  "llm": {
    "semaphore_limit": 50,        // ← Increased from 10
    "max_retries": 5,             // ← Increased from 3
    "timeout": 120                // ← Increased from 60
  },
  "logging": {
    "level": "WARNING",           // ← Changed from "INFO"
    "log_file": "/var/log/graphiti/mcp_server.log"
  }
}
```

---

## Step 6: Commit Configuration to Git

The new config file is designed to be version controlled:

```bash
# Add config to git
git add graphiti.config.json

# Verify .env is ignored
git status  # Should NOT show .env

# If .env appears, add to .gitignore:
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# Commit
git commit -m "Migrate to unified configuration system"
```

**What to commit:**
- ✅ `graphiti.config.json` - Version controlled config
- ✅ `.env.example` - Template with placeholders
- ✅ `.gitignore` - Ensures `.env` not committed

**What NOT to commit:**
- ❌ `.env` - Contains secrets
- ❌ `.env.local` - Local overrides
- ❌ `*.backup` - Backup files

---

## Step 7: Clean Up Deprecated Files

After successful migration and testing:

```bash
# Remove deprecated filter config
rm graphiti-filter.config.json

# Remove old backup files (after verification)
rm .env.backup.* graphiti-filter.config.json.backup

# Remove old .env.example files in subdirectories
rm mcp_server/.env.example.backup
rm server/.env.example

# Verify cleanup
git status
```

---

## Manual Migration (Detailed)

If you prefer to migrate manually without the script:

### Step 1: Create `graphiti.config.json`

```bash
# Copy template
cp graphiti.config.json.template graphiti.config.json

# Or create from scratch
cat > graphiti.config.json << 'EOF'
{
  "version": "1.0.0",
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password_env": "NEO4J_PASSWORD"
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4.1-mini",
    "openai": {
      "api_key_env": "OPENAI_API_KEY"
    }
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small"
  },
  "memory_filter": {
    "enabled": true,
    "mode": "llm"
  }
}
EOF
```

### Step 2: Map Environment Variables to Config

**Old `.env`** → **New `graphiti.config.json`**

| Old Env Var | New Config Path | Keep in .env? |
|-------------|-----------------|---------------|
| `NEO4J_URI` | `database.neo4j.uri` | No |
| `NEO4J_USER` | `database.neo4j.user` | No |
| `NEO4J_PASSWORD` | Reference via `password_env` | ✅ Yes |
| `OPENAI_API_KEY` | Reference via `api_key_env` | ✅ Yes |
| `MODEL_NAME` | `llm.default_model` | No (or override) |
| `SMALL_MODEL_NAME` | `llm.small_model` | No |
| `EMBEDDER_MODEL_NAME` | `embedder.model` | No |
| `SEMAPHORE_LIMIT` | `llm.semaphore_limit` | No |
| `LLM_TEMPERATURE` | `llm.temperature` | No |
| `ANTHROPIC_API_KEY` | Reference via `api_key_env` | ✅ Yes |
| `AZURE_OPENAI_ENDPOINT` | Reference via `endpoint_env` | ✅ Yes |
| `AZURE_OPENAI_API_KEY` | Reference via `api_key_env` | ✅ Yes |

**Example Mapping:**

**Old `.env`:**
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secretpass
OPENAI_API_KEY=sk-abc123
MODEL_NAME=gpt-4.1-mini
SEMAPHORE_LIMIT=15
```

**New `graphiti.config.json`:**
```json
{
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",      // ← From NEO4J_URI
      "user": "neo4j",                     // ← From NEO4J_USER
      "password_env": "NEO4J_PASSWORD"     // ← Reference
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4.1-mini",       // ← From MODEL_NAME
    "semaphore_limit": 15,                 // ← From SEMAPHORE_LIMIT
    "openai": {
      "api_key_env": "OPENAI_API_KEY"      // ← Reference
    }
  }
}
```

**New `.env` (minimal):**
```bash
# Only secrets
NEO4J_PASSWORD=secretpass
OPENAI_API_KEY=sk-abc123
```

### Step 3: Migrate Filter Config

If you have `graphiti-filter.config.json`:

**Old `graphiti-filter.config.json`:**
```json
{
  "filter": {
    "enabled": true,
    "providers": [
      {
        "name": "openai",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "priority": 1
      }
    ]
  }
}
```

**New `graphiti.config.json` (merge into `memory_filter`):**
```json
{
  "memory_filter": {
    "enabled": true,
    "mode": "llm",
    "llm_filter": {
      "providers": [
        {
          "name": "openai",
          "model": "gpt-4o-mini",
          "api_key_env": "OPENAI_API_KEY",
          "temperature": 0.0,
          "max_tokens": 200,
          "enabled": true,
          "priority": 1
        }
      ]
    }
  }
}
```

---

## Troubleshooting

### Config Not Loading

**Symptom**: Server uses defaults instead of your config

**Causes:**
1. Config file in wrong location
2. JSON syntax error
3. File permissions

**Solutions:**
```bash
# Verify config file exists
ls -la graphiti.config.json

# Validate JSON syntax
python -c "import json; json.load(open('graphiti.config.json'))"

# Check file permissions
chmod 644 graphiti.config.json

# Test config loading explicitly
python -c "from mcp_server.unified_config import get_config; print(get_config())"
```

### Environment Variables Not Resolved

**Symptom**: `ERROR - OPENAI_API_KEY not found in environment`

**Causes:**
1. `.env` file not in project root
2. `.env` not loaded
3. Variable name mismatch

**Solutions:**
```bash
# Verify .env location
ls -la .env

# Check variable exists
grep OPENAI_API_KEY .env

# Load .env manually for testing
export $(cat .env | xargs)

# Verify environment
env | grep OPENAI_API_KEY
```

### Database Connection Failed

**Symptom**: `ERROR - Failed to connect to Neo4j database`

**Causes:**
1. Database not running
2. Wrong URI in config
3. Incorrect credentials

**Solutions:**
```bash
# Check database status
docker ps | grep neo4j  # If using Docker

# Test connection manually
cypher-shell -a bolt://localhost:7687 -u neo4j -p your_password

# Verify config
cat graphiti.config.json | grep -A5 "neo4j"

# Check logs
tail -f /var/log/neo4j/neo4j.log
```

### Validation Errors

**Symptom**: `ValidationError: 1 validation error for GraphitiConfig`

**Causes:**
1. Invalid enum value (e.g., wrong provider name)
2. Missing required field
3. Wrong data type

**Solutions:**
```bash
# Common validation errors:

# Invalid backend
"backend": "postgres"  # ❌ Must be "neo4j" or "falkordb"
"backend": "neo4j"     # ✅ Correct

# Invalid provider
"provider": "gpt"      # ❌ Must be "openai", "azure_openai", or "anthropic"
"provider": "openai"   # ✅ Correct

# Wrong type
"semaphore_limit": "10"  # ❌ Must be integer
"semaphore_limit": 10    # ✅ Correct
```

---

## Configuration Templates

### Minimal Configuration

```json
{
  "version": "1.0.0",
  "database": {
    "backend": "neo4j"
  },
  "llm": {
    "provider": "openai"
  }
}
```

### Development Configuration

```json
{
  "version": "1.0.0",
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password_env": "NEO4J_PASSWORD"
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4.1-mini",
    "semaphore_limit": 10
  },
  "logging": {
    "level": "DEBUG",
    "log_filter_decisions": true
  }
}
```

### Production Configuration

```json
{
  "version": "1.0.0",
  "database": {
    "backend": "neo4j",
    "neo4j": {
      "uri": "bolt+s://production.neo4j.io:7687",
      "user": "graphiti_app",
      "password_env": "NEO4J_PASSWORD",
      "pool_size": 100,
      "connection_timeout": 60,
      "max_connection_lifetime": 7200
    }
  },
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4.1-mini",
    "small_model": "gpt-4.1-nano",
    "semaphore_limit": 50,
    "max_retries": 5,
    "timeout": 120
  },
  "memory_filter": {
    "enabled": true,
    "mode": "llm"
  },
  "logging": {
    "level": "WARNING",
    "log_file": "/var/log/graphiti/mcp_server.log"
  },
  "performance": {
    "use_parallel_runtime": true,
    "enable_caching": true,
    "cache_ttl_seconds": 7200
  }
}
```

---

## FAQ

### Q: Can I use both environment variables and config file?

**A**: Yes! Environment variables override config file settings:

```bash
# Config file
"llm": { "default_model": "gpt-4.1-mini" }

# Environment variable override
export MODEL_NAME="gpt-4o"

# Result: Uses gpt-4o (env var wins)
```

### Q: Where should I put my config file?

**A**: Three options (in priority order):

1. **Project root** (recommended): `./graphiti.config.json`
2. **Global**: `~/.claude/graphiti.config.json`
3. **Defaults**: Built-in (no file needed)

### Q: Can I have multiple configs for different environments?

**A**: Yes! Use different filenames and specify:

```bash
# Development
cp graphiti.config.dev.json graphiti.config.json

# Production
cp graphiti.config.prod.json graphiti.config.json

# Or use symbolic links
ln -sf graphiti.config.dev.json graphiti.config.json
```

### Q: What if I don't want to migrate yet?

**A**: The old system will continue to work temporarily, but you'll see deprecation warnings:

```
WARNING - Using deprecated .env configuration
WARNING - Please migrate to graphiti.config.json
WARNING - See MIGRATION_GUIDE.md for instructions
```

### Q: Can I switch back to the old system?

**A**: Yes, restore your backups:

```bash
# Restore old config
mv .env.backup .env
mv graphiti-filter.config.json.backup graphiti-filter.config.json

# Remove new config
rm graphiti.config.json
```

---

## Getting Help

**Issues?**
- Check [Troubleshooting](#troubleshooting) section above
- Review [CONFIGURATION.md](CONFIGURATION.md) for complete reference
- See [IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md](IMPLEMENTATION_PLAN_UNIFIED_CONFIG.md) for details
- Report issues: https://github.com/getzep/graphiti/issues

**Questions?**
- Discuss: https://github.com/getzep/graphiti/discussions
- Discord: [Link to Discord server if available]

---

## Next Steps After Migration

1. ✅ Test your configuration thoroughly
2. ✅ Customize settings for your use case
3. ✅ Commit config to version control
4. ✅ Update CI/CD pipelines with new .env variables
5. ✅ Document project-specific config decisions
6. ✅ Clean up deprecated files

**Congratulations! You've successfully migrated to the unified configuration system.**

---

**Last Updated**: 2025-11-03
**Version**: v1.0
