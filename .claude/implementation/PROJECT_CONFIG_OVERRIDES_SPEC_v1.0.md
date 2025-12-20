# Per-Project Configuration Overrides

> **Version**: 1.0.0
> **Status**: DESIGN DRAFT - Pending Review
> **Created**: 2024-12-18
> **Author**: Claude + Human collaboration
> **Depends On**: Daemon Architecture v1.0, Unified Config Schema

---

## Executive Summary

This document specifies a **per-project configuration override system** that allows individual projects to customize Graphiti behavior (LLM models, extraction prompts, session tracking settings) while maintaining a single global configuration file as the source of truth.

### Key Design Decisions

1. **Single file**: All overrides stored in `~/.graphiti/graphiti.config.json` under `project_overrides`
2. **Path-keyed**: Projects identified by normalized Unix-style path (cross-platform)
3. **Deep merge**: Project overrides merge with global defaults (not replace)
4. **CLI visibility**: `graphiti-mcp config effective` shows computed config for any project
5. **No fragmentation**: No per-project config files to discover or sync

---

## Problem Statement

### Current Behavior

The global config (`~/.graphiti/graphiti.config.json`) applies uniformly to all projects:

```
┌─────────────────────────────────────────────────────────────┐
│                 ~/.graphiti/graphiti.config.json            │
│                                                             │
│  llm.default_model = "gpt-4o-mini"                         │
│  extraction.preprocessing_prompt = "default-session-turn"  │
│  session_tracking.enabled = true                           │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ Project A│        │ Project B│        │ Project C│
    │ (ML/AI)  │        │ (Scripts)│        │ (Web App)│
    └──────────┘        └──────────┘        └──────────┘
    Same config          Same config         Same config
```

**Problems:**
1. ML projects may need `gpt-4o` for better reasoning, not `gpt-4o-mini`
2. Simple script repos may want session tracking disabled entirely
3. Different projects may need different extraction prompts for domain-specific context
4. No way to use different LLM providers per project (e.g., Anthropic for one, OpenAI for another)

### Desired Behavior

```
┌─────────────────────────────────────────────────────────────┐
│                 ~/.graphiti/graphiti.config.json            │
│                                                             │
│  [Global Defaults]                                          │
│  llm.default_model = "gpt-4o-mini"                         │
│                                                             │
│  [Project Overrides]                                        │
│  project_overrides:                                         │
│    "/c/Projects/ml-research":                               │
│      llm.default_model = "gpt-4o"                          │
│    "/c/Projects/simple-scripts":                            │
│      session_tracking.enabled = false                       │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ Project A│        │ Project B│        │ Project C│
    │ (ML/AI)  │        │ (Scripts)│        │ (Web App)│
    └──────────┘        └──────────┘        └──────────┘
    gpt-4o              tracking=off         gpt-4o-mini
    (overridden)        (overridden)         (default)
```

---

## Design Goals

| Goal | Priority | Rationale |
|------|----------|-----------|
| Single source of truth | P0 | One file to understand all config |
| No fragmentation | P0 | Avoid "which config is active?" confusion |
| CLI visibility | P0 | `config effective` shows merged result |
| Deep merge semantics | P1 | Override specific keys, inherit rest |
| Path normalization | P1 | Cross-platform path matching |
| Backward compatible | P1 | Existing configs work unchanged |
| Manageable bloat | P2 | Acceptable for typical usage (<20 projects) |

### Non-Goals (Explicitly Out of Scope)

- **NO per-project config files**: We explicitly avoid `.graphiti/config.json` in project directories
- **NO config discovery/scanning**: Bootstrap does not search filesystem for configs
- **NO inheritance chains**: Only two levels: global → project (no project-of-project)
- **NO dynamic reload per-project**: Config reloads apply to entire config file

---

## Configuration Schema

### Global Config Structure

```json
{
  "version": "1.1.0",

  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "small_model": "gpt-4o-mini"
  },

  "extraction": {
    "preprocessing_prompt": "default-session-turn.md",
    "preprocessing_mode": "prepend"
  },

  "session_tracking": {
    "enabled": true,
    "watch_path": null,
    "keep_length_days": 1
  },

  "project_overrides": {
    "/c/Users/Admin/Documents/GitHub/ml-research": {
      "llm": {
        "default_model": "gpt-4o",
        "temperature": 0.2
      },
      "extraction": {
        "preprocessing_prompt": "You are analyzing ML/AI code. Focus on model architectures, training loops, and data pipelines."
      }
    },
    "/c/Users/Admin/Documents/GitHub/simple-scripts": {
      "session_tracking": {
        "enabled": false
      }
    },
    "/home/user/projects/anthropic-project": {
      "llm": {
        "provider": "anthropic",
        "default_model": "claude-sonnet-4-5-latest"
      }
    }
  }
}
```

### Schema Definition (Pydantic)

```python
class ProjectOverride(BaseModel):
    """Per-project configuration override.

    Only include fields that should override the global config.
    Unspecified fields inherit from global defaults.
    """
    llm: Optional[LLMConfig] = None
    embedder: Optional[EmbedderConfig] = None
    extraction: Optional[ExtractionConfig] = None
    session_tracking: Optional[SessionTrackingConfig] = None
    # Note: database, daemon, resilience are NOT overridable per-project
    # These are system-wide settings that must remain consistent


class GraphitiConfig(BaseModel):
    """Root configuration with project overrides."""

    version: str = "1.1.0"

    # ... existing fields ...

    project_overrides: Dict[str, ProjectOverride] = Field(
        default_factory=dict,
        description=(
            "Per-project configuration overrides. "
            "Keys are normalized Unix-style paths (e.g., '/c/Users/Admin/project'). "
            "Values are partial configs that deep-merge with global defaults."
        )
    )
```

### Overridable vs Non-Overridable Settings

| Section | Overridable | Rationale |
|---------|-------------|-----------|
| `llm` | ✅ Yes | Different projects may need different models/providers |
| `embedder` | ✅ Yes | Embedding model preference per project |
| `extraction` | ✅ Yes | Domain-specific extraction prompts |
| `session_tracking` | ✅ Yes | Enable/disable per project |
| `session_tracking.filter` | ✅ Yes | Different filtering per project |
| `database` | ❌ No | Single database for all projects |
| `daemon` | ❌ No | System-wide daemon settings |
| `resilience` | ❌ No | Consistent error handling |
| `mcp_server` | ❌ No | Server config is global |
| `logging` | ❌ No | Consistent logging |

---

## Path Normalization

### Problem

Paths differ across platforms and even within the same platform:
- Windows: `C:\Users\Admin\project` vs `C:/Users/Admin/project`
- MSYS/Git Bash: `/c/Users/Admin/project`
- Unix: `/home/user/project`
- Symlinks: `/var/project` → `/mnt/data/project`

### Solution: Normalized Unix-Style Paths

All paths in `project_overrides` use **normalized Unix-style format**:

```python
def normalize_project_path(path: str | Path) -> str:
    """Normalize path to Unix-style for consistent matching.

    Examples:
        C:\\Users\\Admin\\project → /c/Users/Admin/project
        C:/Users/Admin/project   → /c/Users/Admin/project
        /home/user/project       → /home/user/project
        ~/project                → /home/user/project (expanded)
    """
    path = Path(path).expanduser().resolve()

    if sys.platform == "win32":
        # Convert Windows path to Unix-style
        # C:\Users\Admin → /c/Users/Admin
        drive, rest = os.path.splitdrive(str(path))
        if drive:
            drive_letter = drive[0].lower()
            return f"/{drive_letter}{rest.replace(os.sep, '/')}"
        return str(path).replace(os.sep, '/')
    else:
        return str(path)
```

### Matching Logic

When resolving config for a project:

```python
def get_project_override(config: GraphitiConfig, project_path: str | Path) -> Optional[ProjectOverride]:
    """Get override config for a specific project path."""
    normalized = normalize_project_path(project_path)
    return config.project_overrides.get(normalized)
```

---

## Merge Semantics

### Deep Merge Algorithm

Project overrides **deep merge** with global defaults, not replace:

```python
def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base config.

    Rules:
    - Scalar values: override replaces base
    - Dicts: recursive merge
    - Lists: override replaces base (no append)
    - None in override: inherits from base (not deletion)
    """
    result = base.copy()

    for key, value in override.items():
        if value is None:
            continue  # Inherit from base
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result
```

### Example Merge

**Global config:**
```json
{
  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "temperature": 0.7,
    "semaphore_limit": 10
  }
}
```

**Project override:**
```json
{
  "llm": {
    "default_model": "gpt-4o",
    "temperature": 0.2
  }
}
```

**Effective config:**
```json
{
  "llm": {
    "provider": "openai",          // inherited
    "default_model": "gpt-4o",     // overridden
    "temperature": 0.2,            // overridden
    "semaphore_limit": 10          // inherited
  }
}
```

---

## CLI Commands

### `graphiti-mcp config effective`

Shows the computed effective configuration for a project:

```bash
# Show effective config for current directory
graphiti-mcp config effective

# Show effective config for specific project
graphiti-mcp config effective --project /path/to/project

# Show only overridden values (diff mode)
graphiti-mcp config effective --diff

# Output as JSON (for scripting)
graphiti-mcp config effective --json
```

**Example output (default):**
```
Effective Configuration for: /c/Users/Admin/Documents/GitHub/ml-research
================================================================================

[llm]
  provider: openai
  default_model: gpt-4o          ← overridden (global: gpt-4o-mini)
  small_model: gpt-4o-mini
  temperature: 0.2               ← overridden (global: 0.7)

[extraction]
  preprocessing_prompt: "You are analyzing ML/AI code..."  ← overridden

[session_tracking]
  enabled: true
  keep_length_days: 1

================================================================================
Overrides applied from: project_overrides["/c/Users/Admin/Documents/GitHub/ml-research"]
```

**Example output (--diff):**
```
Project Overrides: /c/Users/Admin/Documents/GitHub/ml-research
================================================================================

llm.default_model: gpt-4o-mini → gpt-4o
llm.temperature: 0.7 → 0.2
extraction.preprocessing_prompt: "default-session-turn.md" → "You are analyzing ML/AI code..."
```

### `graphiti-mcp config list-projects`

Lists all projects with overrides:

```bash
graphiti-mcp config list-projects
```

**Example output:**
```
Configured Project Overrides:
================================================================================

1. /c/Users/Admin/Documents/GitHub/ml-research
   Overrides: llm.default_model, llm.temperature, extraction.preprocessing_prompt

2. /c/Users/Admin/Documents/GitHub/simple-scripts
   Overrides: session_tracking.enabled

3. /home/user/projects/anthropic-project
   Overrides: llm.provider, llm.default_model

================================================================================
Total: 3 projects with overrides
```

### `graphiti-mcp config set-override`

Convenience command to add/update project overrides:

```bash
# Set a single override
graphiti-mcp config set-override --project . --key llm.default_model --value gpt-4o

# Set multiple overrides
graphiti-mcp config set-override --project . \
  --key llm.default_model --value gpt-4o \
  --key llm.temperature --value 0.2

# Disable session tracking for a project
graphiti-mcp config set-override --project /path/to/scripts \
  --key session_tracking.enabled --value false
```

### `graphiti-mcp config remove-override`

Remove project overrides:

```bash
# Remove specific override
graphiti-mcp config remove-override --project . --key llm.default_model

# Remove all overrides for a project
graphiti-mcp config remove-override --project . --all
```

---

## Implementation Architecture

### Config Resolution Flow

```
┌────────────────────────────────────────────────────────────────┐
│                      get_effective_config()                     │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 1. Load global config from ~/.graphiti/graphiti.config.json   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 2. Normalize current project path                              │
│    C:\Users\Admin\project → /c/Users/Admin/project             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 3. Look up project_overrides[normalized_path]                  │
│    Found? → Continue to merge                                   │
│    Not found? → Return global config as-is                      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 4. Deep merge: global ← project_override                       │
│    Only overridable sections are merged                         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 5. Apply environment variable overrides (existing logic)       │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 6. Return effective GraphitiConfig                              │
└────────────────────────────────────────────────────────────────┘
```

### Code Changes Required

#### 1. `unified_config.py` - New Types

```python
class ProjectOverride(BaseModel):
    """Per-project configuration override."""
    llm: Optional[LLMConfig] = None
    embedder: Optional[EmbedderConfig] = None
    extraction: Optional[ExtractionConfig] = None
    session_tracking: Optional[SessionTrackingConfig] = None

    class Config:
        extra = "forbid"  # Prevent typos in override keys
```

#### 2. `unified_config.py` - GraphitiConfig Updates

```python
class GraphitiConfig(BaseModel):
    # ... existing fields ...

    project_overrides: Dict[str, ProjectOverride] = Field(
        default_factory=dict,
        description="Per-project configuration overrides keyed by normalized path"
    )

    def get_effective_config(self, project_path: Optional[str | Path] = None) -> "GraphitiConfig":
        """Get configuration with project overrides applied.

        Args:
            project_path: Path to project. If None, uses current directory.

        Returns:
            New GraphitiConfig with overrides merged.
        """
        if project_path is None:
            project_path = Path.cwd()

        normalized = normalize_project_path(project_path)
        override = self.project_overrides.get(normalized)

        if override is None:
            return self

        return self._apply_override(override)

    def _apply_override(self, override: ProjectOverride) -> "GraphitiConfig":
        """Apply project override to create effective config."""
        data = self.model_dump()
        override_data = override.model_dump(exclude_none=True)

        merged = deep_merge(data, override_data)

        # Remove project_overrides from merged (avoid recursion)
        merged.pop("project_overrides", None)

        return GraphitiConfig.model_validate(merged)
```

#### 3. `unified_config.py` - Updated get_config()

```python
def get_config(
    reload: bool = False,
    force_reload: bool = False,
    project_path: Optional[str | Path] = None
) -> GraphitiConfig:
    """Get the global configuration instance with optional project overrides.

    Args:
        reload: Force reload from file (deprecated)
        force_reload: Force reload from file
        project_path: If provided, apply project-specific overrides

    Returns:
        GraphitiConfig instance (with overrides if project_path specified)
    """
    global _config_instance

    should_reload = reload or force_reload

    if _config_instance is None or should_reload:
        _config_instance = GraphitiConfig.from_file()
        _config_instance.apply_env_overrides()

    if project_path is not None:
        return _config_instance.get_effective_config(project_path)

    return _config_instance
```

#### 4. New CLI Module: `cli_config.py`

```python
import click
from pathlib import Path
from mcp_server.unified_config import get_config, normalize_project_path

@click.group()
def config():
    """Configuration management commands."""
    pass

@config.command()
@click.option("--project", "-p", type=click.Path(), default=".", help="Project path")
@click.option("--diff", is_flag=True, help="Show only overridden values")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def effective(project: str, diff: bool, as_json: bool):
    """Show effective configuration for a project."""
    # Implementation here
    pass

@config.command("list-projects")
def list_projects():
    """List all projects with configuration overrides."""
    pass

@config.command("set-override")
@click.option("--project", "-p", type=click.Path(), required=True)
@click.option("--key", "-k", multiple=True, required=True)
@click.option("--value", "-v", multiple=True, required=True)
def set_override(project: str, key: tuple, value: tuple):
    """Set configuration override for a project."""
    pass

@config.command("remove-override")
@click.option("--project", "-p", type=click.Path(), required=True)
@click.option("--key", "-k", multiple=True)
@click.option("--all", "remove_all", is_flag=True)
def remove_override(project: str, key: tuple, remove_all: bool):
    """Remove configuration override for a project."""
    pass
```

---

## Session Tracking Integration

### Project Detection at Runtime

When session tracking processes a JSONL file, it determines the project from the file path:

```
~/.claude/projects/{project_hash}/sessions/{session}.jsonl
                    ↑
                    Project identifier
```

The session tracker resolves this to the actual project path and applies overrides:

```python
class SessionTracker:
    def process_session(self, session_path: Path):
        # Extract project from session path
        project_hash = self._extract_project_hash(session_path)
        project_path = self._resolve_project_path(project_hash)

        # Get effective config for this project
        config = get_config(project_path=project_path)

        # Use project-specific settings
        if not config.session_tracking.enabled:
            logger.debug(f"Session tracking disabled for {project_path}")
            return

        # Apply project-specific extraction prompt
        extraction_prompt = config.extraction.preprocessing_prompt
        # ...
```

### LLM Provider Per-Project

Different projects can use different LLM providers:

```json
{
  "llm": { "provider": "openai", "default_model": "gpt-4o-mini" },

  "project_overrides": {
    "/c/Projects/anthropic-preferred": {
      "llm": {
        "provider": "anthropic",
        "default_model": "claude-sonnet-4-5-latest",
        "anthropic": {
          "api_key_env": "ANTHROPIC_API_KEY"
        }
      }
    }
  }
}
```

---

## Migration & Backward Compatibility

### Existing Configs

Existing configs without `project_overrides` continue to work unchanged:
- `project_overrides` defaults to empty dict `{}`
- All projects use global config
- No migration required

### Version Bump

Config version bumps from `1.0.0` to `1.1.0` to indicate new capability:

```json
{
  "version": "1.1.0",
  ...
}
```

### Validation

Config validator updated to:
1. Validate `project_overrides` keys are valid paths
2. Validate override values match expected schema
3. Warn on non-overridable sections in overrides

---

## Edge Cases & Error Handling

### Path Not Found

If `project_path` doesn't exist on disk:
- Log warning: "Project path does not exist: {path}"
- Still apply override if path matches (user may have moved project temporarily)

### Invalid Override Keys

If override contains non-overridable section (e.g., `database`):
- Log warning during config load
- Ignore invalid section, apply valid sections
- Validator reports this as a warning, not error

### Circular Symlinks

Path normalization uses `resolve()` which handles symlinks:
- Resolves to canonical path
- Detects circular symlinks (raises error)

### Case Sensitivity

- Unix: Paths are case-sensitive (as-is)
- Windows: Paths normalized to lowercase for matching

---

## Testing Strategy

### Unit Tests

1. `test_normalize_project_path()` - Path normalization across platforms
2. `test_deep_merge()` - Merge semantics
3. `test_get_effective_config()` - Override resolution
4. `test_project_override_validation()` - Schema validation

### Integration Tests

1. Config file with overrides loads correctly
2. CLI commands work as expected
3. Session tracking respects project overrides

### Platform Tests

1. Windows path normalization (`C:\` → `/c/`)
2. Unix path normalization
3. Mixed environment (MSYS on Windows)

---

## Future Considerations

### Potential Enhancements (Not In Scope)

1. **Glob patterns for paths**: `"/c/Users/*/projects/*-ml"` matches ML projects
2. **Override inheritance**: Project B inherits from Project A's overrides
3. **Team-shared overrides**: Git-tracked overrides that team members can use
4. **Override templates**: Named templates applied to multiple projects

### Config Size Limits

For typical usage (<20 projects with 2-3 overrides each):
- Additional JSON size: ~2-5 KB
- Acceptable for human readability
- If bloat becomes issue, consider external file reference (Option B hybrid)

---

## Acceptance Criteria

### Must Have (P0)

- [ ] `project_overrides` schema added to `GraphitiConfig`
- [ ] `get_effective_config(project_path)` method implemented
- [ ] Path normalization works on Windows, macOS, Linux
- [ ] Deep merge correctly inherits unspecified fields
- [ ] `graphiti-mcp config effective` CLI command works
- [ ] Existing configs without overrides work unchanged

### Should Have (P1)

- [ ] `graphiti-mcp config list-projects` command
- [ ] `graphiti-mcp config set-override` command
- [ ] `graphiti-mcp config remove-override` command
- [ ] Config validator warns on non-overridable sections
- [ ] Session tracking uses project-specific config

### Nice to Have (P2)

- [ ] `--diff` flag for effective command
- [ ] JSON output option for scripting
- [ ] Config editor TUI (text UI)

---

## Appendix: Full Example Config

```json
{
  "version": "1.1.0",
  "_comment": "Graphiti MCP Server Configuration",

  "database": {
    "uri": "bolt://localhost:7687",
    "user": "neo4j",
    "password_env": "NEO4J_PASSWORD"
  },

  "llm": {
    "provider": "openai",
    "default_model": "gpt-4o-mini",
    "small_model": "gpt-4o-mini",
    "temperature": 0.7,
    "openai": {
      "api_key_env": "OPENAI_API_KEY"
    }
  },

  "extraction": {
    "preprocessing_prompt": "default-session-turn.md",
    "preprocessing_mode": "prepend"
  },

  "session_tracking": {
    "enabled": true,
    "watch_path": null,
    "keep_length_days": 1,
    "filter": {
      "tool_calls": true,
      "tool_content": "default-tool-content.md",
      "user_messages": true,
      "agent_messages": true
    }
  },

  "daemon": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8321
  },

  "project_overrides": {
    "/c/Users/Admin/Documents/GitHub/ml-research": {
      "_comment": "ML project needs better model and custom extraction",
      "llm": {
        "default_model": "gpt-4o",
        "temperature": 0.2
      },
      "extraction": {
        "preprocessing_prompt": "You are analyzing ML/AI code. Focus on model architectures, training loops, and data pipelines. Extract entities for: models, datasets, hyperparameters, metrics."
      }
    },

    "/c/Users/Admin/Documents/GitHub/simple-scripts": {
      "_comment": "Utility scripts don't need session tracking",
      "session_tracking": {
        "enabled": false
      }
    },

    "/c/Users/Admin/Documents/GitHub/anthropic-project": {
      "_comment": "This project uses Anthropic instead of OpenAI",
      "llm": {
        "provider": "anthropic",
        "default_model": "claude-sonnet-4-5-latest",
        "anthropic": {
          "api_key_env": "ANTHROPIC_API_KEY"
        }
      }
    },

    "/home/user/work/confidential-project": {
      "_comment": "Sensitive project - minimal tracking, no path exposure",
      "session_tracking": {
        "include_project_path": false,
        "filter": {
          "tool_content": false,
          "agent_messages": "SUMMARY"
        }
      }
    }
  }
}
```

---

**End of Specification**
