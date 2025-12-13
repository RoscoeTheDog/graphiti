# Implementation Plan: LLM-Based Memory Filter for Graphiti MCP Server

## Overview

Add intelligent memory filtering to the Graphiti MCP server using LLMs to automatically detect storage-worthy events based on non-redundancy criteria. The system will support multiple LLM providers with hierarchical fallback and graceful degradation.

## Objectives

1. **Automatic filter detection** - Determine if memory should be stored without explicit user confirmation
2. **Session-scoped LLM instances** - One LLM instance per agent session (prevent context overflow)
3. **Hierarchical fallback** - Try multiple LLM providers in order (OpenAI → Anthropic → disable)
4. **Configuration-driven** - All settings via environment variables and config file
5. **Minimal agent overhead** - Agent just calls `should_store()`, server handles filtering

---

## Architecture

### Current State (Baseline)

```
Claude Code Agent → Graphiti MCP Server → Neo4j
                         ↓
                    add_memory() - stores everything
```

**Problem**: No filtering, all memories stored (including redundant ones)

### Proposed State

```
Claude Code Agent → Graphiti MCP Server → Neo4j
                         ↓
                    FilterManager (LLM-based)
                         ↓
                    SessionManager (per-agent LLM instances)
                         ↓
                    LLMProvider (OpenAI | Anthropic | None)
```

**Flow**:
1. Agent calls `should_store(event_description, context)`
2. FilterManager checks session-scoped LLM
3. LLM analyzes event against filter criteria
4. Returns `{"should_store": bool, "category": str, "reason": str}`
5. Agent conditionally calls `add_memory()` based on response

---

## Filter Criteria (Non-Redundant Categories)

**STORE** (if YES to any):
- ✅ **env-quirk**: Environment/machine-specific issue (can't fix in code)
- ✅ **user-pref**: User preference revealed (subjective choice)
- ✅ **external-api**: External service quirk (3rd party, out of control)
- ✅ **historical-context**: Why legacy code exists (prevents future breakage)
- ✅ **cross-project**: Learning applicable across projects (general heuristic)
- ✅ **workaround**: Non-obvious workaround (hidden knowledge)

**SKIP** (redundant):
- ❌ **bug-in-code**: Bug fixed in code (redundant)
- ❌ **config-in-repo**: Config change now in repo (redundant)
- ❌ **docs-added**: Documentation added (redundant)
- ❌ **first-success**: First-try success (no learning occurred)

---

## Component Design

### 1. Configuration Schema

**Project-Local Config File**: `graphiti-filter.config.json`

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "description": "Graphiti Memory Filter Configuration",
  "filter": {
    "enabled": true,
    "providers": [
      {
        "name": "openai",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "temperature": 0.0,
        "max_tokens": 200,
        "enabled": true,
        "priority": 1
      },
      {
        "name": "anthropic",
        "model": "claude-haiku-3-5-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
        "temperature": 0.0,
        "max_tokens": 200,
        "enabled": true,
        "priority": 2
      }
    ],
    "session": {
      "max_context_tokens": 5000,
      "auto_cleanup": true,
      "session_timeout_minutes": 60
    },
    "categories": {
      "store": ["env-quirk", "user-pref", "external-api", "historical-context", "cross-project", "workaround"],
      "skip": ["bug-in-code", "config-in-repo", "docs-added", "first-success"]
    },
    "logging": {
      "log_filter_decisions": true,
      "log_level": "INFO"
    }
  }
}
```

**Python Config Loader**: `mcp_server/filter_config.py`

```python
import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import logging

logger = logging.getLogger(__name__)

class LLMProviderConfig(BaseModel):
    """Configuration for a single LLM provider"""
    name: str  # "openai" or "anthropic"
    model: str
    api_key_env: str = Field(description="Environment variable name for API key")
    temperature: float = 0.0
    max_tokens: int = 200
    enabled: bool = True
    priority: int = 1  # Lower number = higher priority

class SessionConfig(BaseModel):
    """Session management configuration"""
    max_context_tokens: int = 5000
    auto_cleanup: bool = True
    session_timeout_minutes: int = 60

class CategoriesConfig(BaseModel):
    """Filter categories configuration"""
    store: List[str] = Field(
        default_factory=lambda: ["env-quirk", "user-pref", "external-api", "historical-context", "cross-project", "workaround"]
    )
    skip: List[str] = Field(
        default_factory=lambda: ["bug-in-code", "config-in-repo", "docs-added", "first-success"]
    )

class LoggingConfig(BaseModel):
    """Logging configuration"""
    log_filter_decisions: bool = True
    log_level: str = "INFO"

class FilterConfigData(BaseModel):
    """Root filter configuration"""
    enabled: bool = True
    providers: List[LLMProviderConfig] = Field(default_factory=list)
    session: SessionConfig = Field(default_factory=SessionConfig)
    categories: CategoriesConfig = Field(default_factory=CategoriesConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

class FilterConfig(BaseModel):
    """Top-level configuration wrapper"""
    filter: FilterConfigData

    @classmethod
    def from_file(cls, config_path: str | Path | None = None) -> 'FilterConfig':
        """Load configuration from JSON file.

        Args:
            config_path: Path to config file. If None, searches in:
                1. ./graphiti-filter.config.json (project root)
                2. ~/.claude/graphiti-filter.config.json (global)
                3. Falls back to defaults
        """
        if config_path is None:
            # Search order: project root -> global -> defaults
            search_paths = [
                Path.cwd() / "graphiti-filter.config.json",
                Path.home() / ".claude" / "graphiti-filter.config.json"
            ]

            for path in search_paths:
                if path.exists():
                    config_path = path
                    logger.info(f"Loading filter config from: {config_path}")
                    break
            else:
                logger.warning("No filter config found, using defaults")
                return cls._default_config()

        config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls._default_config()

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            return cls.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return cls._default_config()

    @classmethod
    def _default_config(cls) -> 'FilterConfig':
        """Return default configuration"""
        return cls(
            filter=FilterConfigData(
                enabled=True,
                providers=[
                    LLMProviderConfig(
                        name="openai",
                        model="gpt-4o-mini",
                        api_key_env="OPENAI_API_KEY",
                        priority=1
                    ),
                    LLMProviderConfig(
                        name="anthropic",
                        model="claude-haiku-3-5-20241022",
                        api_key_env="ANTHROPIC_API_KEY",
                        priority=2
                    )
                ]
            )
        )

    def get_sorted_providers(self) -> List[LLMProviderConfig]:
        """Get providers sorted by priority (lower number = higher priority)"""
        return sorted(self.filter.providers, key=lambda p: p.priority)
```

**Environment Variables** (Only API keys, no Graphiti-specific pollution):
```bash
# Standard LLM API keys (shared with other tools)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

### 2. LLM Provider Abstraction

**File**: `mcp_server/llm_provider.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self.api_key = os.environ.get(config.api_key_env)

    @abstractmethod
    async def complete(self, prompt: str) -> Dict[str, Any]:
        """Send prompt to LLM and return parsed response"""
        pass

    def is_available(self) -> bool:
        """Check if provider is configured and enabled"""
        return self.config.enabled and self.api_key is not None


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider"""

    def __init__(self, config: LLMProviderConfig):
        super().__init__(config)
        if self.api_key:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)

    async def complete(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"}
            )

            import json
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider"""

    def __init__(self, config: LLMProviderConfig):
        super().__init__(config)
        if self.api_key:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=self.api_key)

    async def complete(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API"""
        try:
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            import json
            content = response.content[0].text

            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


def create_provider(config: LLMProviderConfig) -> LLMProvider:
    """Factory function to create LLM provider"""
    if config.provider == "openai":
        return OpenAIProvider(config)
    elif config.provider == "anthropic":
        return AnthropicProvider(config)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")
```

---

### 3. Session Manager

**File**: `mcp_server/session_manager.py`

```python
import uuid
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Session:
    """Represents a single agent session with its own LLM context"""

    def __init__(self, session_id: str, provider: LLMProvider):
        self.session_id = session_id
        self.provider = provider
        self.created_at = datetime.now()
        self.context_tokens = 0
        self.query_count = 0

    def should_cleanup(self, max_context: int) -> bool:
        """Check if session context should be reset"""
        return self.context_tokens > max_context

    def reset_context(self):
        """Reset session context (called when context gets too large)"""
        logger.info(f"Resetting context for session {self.session_id}")
        self.context_tokens = 0
        self.query_count = 0


class SessionManager:
    """Manages session-scoped LLM instances"""

    def __init__(self, filter_config: FilterConfig):
        self.config = filter_config
        self.sessions: Dict[str, Session] = {}
        self.providers: list[LLMProvider] = []

        # Initialize providers in order
        for provider_config in filter_config.providers:
            try:
                provider = create_provider(provider_config)
                if provider.is_available():
                    self.providers.append(provider)
                    logger.info(f"Initialized {provider_config.provider} provider: {provider_config.model}")
                else:
                    logger.warning(f"Provider {provider_config.provider} not available (missing API key)")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_config.provider}: {e}")

        if not self.providers:
            logger.warning("No LLM providers available - filtering will be disabled")

    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        """Get existing session or create new one"""
        if session_id is None:
            session_id = str(uuid.uuid4())

        if session_id not in self.sessions:
            # Try providers in order until one works
            for provider in self.providers:
                try:
                    session = Session(session_id, provider)
                    self.sessions[session_id] = session
                    logger.info(f"Created session {session_id} with provider {provider.config.provider}")
                    return session
                except Exception as e:
                    logger.warning(f"Failed to create session with {provider.config.provider}: {e}")
                    continue

            # If all providers failed, raise error
            raise RuntimeError("No available LLM providers for filter session")

        session = self.sessions[session_id]

        # Check if context should be reset
        if session.should_cleanup(self.config.max_context_size):
            session.reset_context()

        return session

    def cleanup_session(self, session_id: str):
        """Remove session (called when agent disconnects)"""
        if session_id in self.sessions:
            logger.info(f"Cleaning up session {session_id}")
            del self.sessions[session_id]
```

---

### 4. Filter Manager

**File**: `mcp_server/filter_manager.py`

```python
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Compact filter prompt (minimize tokens)
FILTER_PROMPT_TEMPLATE = """Analyze event. Store ONLY if non-redundant:

✅ STORE if:
- env-quirk: Machine/OS-specific (can't fix in code)
- user-pref: Subjective preference
- external-api: 3rd party API quirk
- historical-context: Why legacy code exists
- cross-project: General learning/heuristic
- workaround: Non-obvious workaround

❌ SKIP if:
- bug-in-code: Fixed in codebase
- config-in-repo: Config now committed
- docs-added: Info in README/docs
- first-success: No learning occurred

Event: {event_description}
Context: {context}

JSON only: {{"should_store": bool, "category": str, "reason": str}}"""


class FilterManager:
    """Manages LLM-based filtering logic"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.enabled = session_manager.config.enabled

    async def should_store(
        self,
        event_description: str,
        context: str = "",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determine if event should be stored in memory.

        Args:
            event_description: Description of the event/memory
            context: Additional context (recent actions, errors, etc.)
            session_id: Optional session ID (auto-generated if not provided)

        Returns:
            {
                "should_store": bool,
                "category": str,  # env-quirk | user-pref | external-api | etc.
                "reason": str,
                "session_id": str
            }
        """
        if not self.enabled:
            # Filtering disabled, store everything
            return {
                "should_store": True,
                "category": "filter_disabled",
                "reason": "Filtering is disabled",
                "session_id": session_id or "none"
            }

        try:
            # Get or create session
            session = self.session_manager.get_or_create_session(session_id)

            # Build prompt
            prompt = FILTER_PROMPT_TEMPLATE.format(
                event_description=event_description,
                context=context
            )

            # Call LLM
            result = await session.provider.complete(prompt)

            # Update session stats
            session.query_count += 1
            session.context_tokens += len(prompt) // 4  # Rough token estimate

            # Add session_id to result
            result["session_id"] = session.session_id

            logger.info(
                f"Filter decision: {result['should_store']} "
                f"(category: {result.get('category', 'unknown')}, "
                f"session: {session.session_id})"
            )

            return result

        except Exception as e:
            logger.error(f"Filter error (falling back to store): {e}")
            # Graceful degradation: store on error
            return {
                "should_store": True,
                "category": "filter_error",
                "reason": f"Filter failed: {str(e)}",
                "session_id": session_id or "error"
            }
```

---

### 5. New MCP Tool: `should_store`

**File**: `mcp_server/graphiti_mcp_server.py` (add to existing file)

```python
# Add to imports
from mcp_server.filter_config import FilterConfig
from mcp_server.session_manager import SessionManager
from mcp_server.filter_manager import FilterManager

# Add global instances (after graphiti_client)
filter_config: FilterConfig = FilterConfig.from_env()
session_manager: SessionManager | None = None
filter_manager: FilterManager | None = None

# Add to initialize_graphiti()
async def initialize_graphiti():
    """Initialize the Graphiti client with the configured settings."""
    global graphiti_client, config, session_manager, filter_manager

    # ... existing initialization ...

    # Initialize filter system
    if filter_config.enabled:
        try:
            session_manager = SessionManager(filter_config)
            filter_manager = FilterManager(session_manager)
            logger.info("Memory filtering enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize filtering (disabled): {e}")
            filter_manager = None

# Add new MCP tool
@mcp.tool()
async def should_store(
    event_description: str,
    context: str = "",
    session_id: str | None = None
) -> Dict[str, Any] | ErrorResponse:
    """
    Determine if an event should be stored in memory using LLM-based filtering.

    Args:
        event_description: Description of the event/memory to evaluate
        context: Additional context (recent actions, errors, files changed, etc.)
        session_id: Optional session ID for continuity (auto-generated if not provided)

    Returns:
        {
            "should_store": bool,
            "category": str,  # env-quirk | user-pref | external-api | etc.
            "reason": str,
            "session_id": str
        }

    Examples:
        # Check if environment-specific issue should be stored
        should_store(
            event_description="Neo4j connection timeout, fixed by setting NEO4J_TIMEOUT=60 in .env",
            context="Edited .env (in .gitignore), error resolved",
            session_id="user-123-session-456"
        )
        # Returns: {"should_store": true, "category": "env-quirk", ...}

        # Check if code fix should be stored (redundant)
        should_store(
            event_description="Fixed infinite loop in parseData() function",
            context="Edited src/parser.py, committed to git",
            session_id="user-123-session-456"
        )
        # Returns: {"should_store": false, "category": "bug-in-code", ...}
    """
    global filter_manager

    if filter_manager is None:
        # Filtering not initialized, default to store
        return {
            "should_store": True,
            "category": "filter_unavailable",
            "reason": "Memory filtering not available",
            "session_id": session_id or "none"
        }

    try:
        result = await filter_manager.should_store(
            event_description=event_description,
            context=context,
            session_id=session_id
        )
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in should_store: {error_msg}")
        return ErrorResponse(error=f"Error checking storage criteria: {error_msg}")
```

---

## File Structure

```
graphiti/
├── mcp_server/
│   ├── graphiti_mcp_server.py       # Main server (MODIFIED)
│   ├── filter_config.py             # NEW - Configuration
│   ├── llm_provider.py              # NEW - LLM abstraction
│   ├── session_manager.py           # NEW - Session management
│   └── filter_manager.py            # NEW - Filter logic
├── .env.example                      # UPDATE - Add filter env vars
└── README.md                         # UPDATE - Document filter feature
```

---

## Implementation Phases

### Phase 1: Core Infrastructure ✅
- [x] Create filter_config.py (configuration schema)
- [x] Create llm_provider.py (OpenAI + Anthropic providers)
- [x] Create session_manager.py (session-scoped LLM instances)
- [x] Create filter_manager.py (filter logic + prompt)

### Phase 2: MCP Integration
- [ ] Add `should_store` tool to graphiti_mcp_server.py
- [ ] Initialize filter system in `initialize_graphiti()`
- [ ] Add graceful degradation (filter failures)

### Phase 3: Configuration
- [ ] Update .env.example with filter variables
- [ ] Add CLI arguments for filter config overrides
- [ ] Document environment variables

### Phase 4: Testing
- [ ] Unit tests for filter logic
- [ ] Integration tests for MCP tool
- [ ] Test hierarchical fallback (OpenAI → Anthropic)
- [ ] Test session cleanup

### Phase 5: Documentation
- [ ] Update README.md with filter feature
- [ ] Add examples to MCP tool docstring
- [ ] Document filter categories

### Phase 6: CLAUDE.md Update (LAST)
- [ ] Add `should_store` usage pattern to CLAUDE.md
- [ ] Update GRAPHITI section with filter integration
- [ ] Document session_id usage for continuity

---

## Testing Plan

### Unit Tests

**File**: `tests/test_filter_manager.py`

```python
import pytest
from mcp_server.filter_manager import FilterManager
from mcp_server.session_manager import SessionManager
from mcp_server.filter_config import FilterConfig

@pytest.mark.asyncio
async def test_env_quirk_detection():
    """Test that environment-specific issues are detected"""
    config = FilterConfig.from_env()
    session_mgr = SessionManager(config)
    filter_mgr = FilterManager(session_mgr)

    result = await filter_mgr.should_store(
        event_description="Neo4j timeout fixed by setting NEO4J_TIMEOUT=60 in .env",
        context="Edited .env (in .gitignore)"
    )

    assert result["should_store"] == True
    assert result["category"] == "env-quirk"

@pytest.mark.asyncio
async def test_code_fix_skip():
    """Test that code fixes are skipped (redundant)"""
    config = FilterConfig.from_env()
    session_mgr = SessionManager(config)
    filter_mgr = FilterManager(session_mgr)

    result = await filter_mgr.should_store(
        event_description="Fixed infinite loop in parseData()",
        context="Edited src/parser.py, committed to git"
    )

    assert result["should_store"] == False
    assert result["category"] == "bug-in-code"

@pytest.mark.asyncio
async def test_hierarchical_fallback():
    """Test that providers fall back correctly"""
    # Mock OpenAI failure, should fall back to Anthropic
    # ... test implementation
```

---

## Dependencies

**Add to `pyproject.toml`**:

```toml
[tool.poetry.dependencies]
# Existing dependencies...
openai = "^1.0.0"  # May already be present
anthropic = "^0.18.0"  # NEW - for Anthropic provider
```

---

## Configuration Deployment

### Project Structure

```
graphiti/
├── graphiti-filter.config.json       # Project-local config (version controlled)
├── mcp_server/
│   ├── graphiti_mcp_server.py
│   ├── filter_config.py              # Config loader
│   ├── llm_provider.py
│   ├── session_manager.py
│   └── filter_manager.py
└── scripts/
    └── install-filter-config.sh      # Deployment script
```

### Installation/Deployment Script

**File**: `scripts/install-filter-config.sh`

```bash
#!/bin/bash
# Install Graphiti filter configuration to global Claude directory

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "📦 Installing Graphiti Filter Configuration..."

# Detect platform
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    CLAUDE_DIR="$HOME/.claude"
else
    CLAUDE_DIR="$HOME/.claude"
fi

# Create .claude directory if it doesn't exist
mkdir -p "$CLAUDE_DIR"

# Copy filter config
if [ -f "graphiti-filter.config.json" ]; then
    cp graphiti-filter.config.json "$CLAUDE_DIR/graphiti-filter.config.json"
    echo -e "${GREEN}✅ Deployed filter config to: $CLAUDE_DIR/graphiti-filter.config.json${NC}"
else
    echo -e "${YELLOW}⚠️  graphiti-filter.config.json not found in current directory${NC}"
    exit 1
fi

# Verify API keys are set
echo ""
echo "🔑 Checking API keys..."

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY not set (OpenAI provider will be disabled)${NC}"
else
    echo -e "${GREEN}✅ OPENAI_API_KEY is set${NC}"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  ANTHROPIC_API_KEY not set (Anthropic provider will be disabled)${NC}"
else
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY is set${NC}"
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Ensure API keys are exported in your shell profile:"
echo "   export OPENAI_API_KEY=sk-..."
echo "   export ANTHROPIC_API_KEY=sk-ant-..."
echo ""
echo "2. Restart your MCP server for changes to take effect"
```

**Usage**:
```bash
cd /path/to/graphiti
chmod +x scripts/install-filter-config.sh
./scripts/install-filter-config.sh
```

### Config Search Order

When MCP server starts, it searches for config in this order:

1. **Project-local** (development): `./graphiti-filter.config.json`
2. **Global** (installed): `~/.claude/graphiti-filter.config.json`
3. **Fallback** (defaults): Built-in defaults in `filter_config.py`

This allows:
- ✅ Development with project-specific config
- ✅ Global config for all projects after installation
- ✅ Graceful degradation if no config found

### Environment Variables Reference

**Only standard LLM API keys needed** (no Graphiti-specific variables):

```bash
# Standard API keys (shared with other tools)
OPENAI_API_KEY=sk-...                                      # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...                               # Anthropic API key

# Optional: Neo4j connection (if not in MCP config)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

**No global env var pollution** - all Graphiti-specific config is in JSON file.

---

## Cost Estimation

**Per Filter Query:**
- Input: ~300 tokens (prompt + context)
- Output: ~100 tokens (JSON response)
- Total: ~400 tokens per query

**OpenAI (gpt-4o-mini)**:
- Cost: $0.150/1M input, $0.600/1M output
- Per query: ~$0.0001 ($0.000045 input + $0.00006 output)

**Anthropic (claude-haiku-3-5)**:
- Cost: $0.80/1M input, $4.00/1M output
- Per query: ~$0.0006 ($0.00024 input + $0.0004 output)

**Monthly (100 sessions, 5 queries/session = 500 queries)**:
- OpenAI: **$0.05/month**
- Anthropic: **$0.30/month** (fallback only)

---

## Next Steps

1. ✅ Review this plan
2. Implement Phase 1 (Core Infrastructure)
3. Implement Phase 2 (MCP Integration)
4. Test with real scenarios
5. Update CLAUDE.md (LAST STEP)

---

**Questions to Resolve:**

1. Should session_id be auto-generated or required from agent?
   - **Recommendation**: Auto-generate, agent can optionally provide for continuity
2. How long should sessions persist?
   - **Recommendation**: Until context exceeds 5K tokens, then reset
3. Should we support session cleanup API?
   - **Recommendation**: Yes, add `cleanup_session(session_id)` tool
4. Should filter decisions be logged to graphiti for debugging?
   - **Recommendation**: Yes, optionally store filter decisions as special episodes

---

**Author**: Claude Code
**Date**: 2025-11-03
**Version**: v1.0
