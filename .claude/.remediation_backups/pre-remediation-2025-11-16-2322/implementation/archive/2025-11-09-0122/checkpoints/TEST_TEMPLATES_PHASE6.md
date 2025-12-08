# Phase 6: Complete Test Templates

This document contains complete, ready-to-use test templates for Phase 6. Copy these into the appropriate test files.

---

## Test File 1: tests/test_unified_config.py

**Complete test file - copy as-is:**

```python
"""
Unit tests for unified configuration system.
Coverage target: >90% of mcp_server/unified_config.py
"""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from mcp_server.unified_config import GraphitiConfig, get_config


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary graphiti.config.json file."""
    config = {
        "database": {
            "backend": "neo4j",
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password": "${NEO4J_PASSWORD}",
                "database": "neo4j"
            },
            "falkordb": {
                "uri": "redis://localhost:6379",
                "password": "${FALKORDB_PASSWORD}",
                "graph_name": "graphiti"
            }
        },
        "llm": {
            "provider": "openai",
            "default_model": "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens": 8192,
            "semaphore_limit": 10,
            "openai": {
                "api_key": "${OPENAI_API_KEY}",
                "base_url": None,
                "organization": None
            },
            "azure_openai": {
                "api_key": "${AZURE_OPENAI_API_KEY}",
                "endpoint": "${AZURE_OPENAI_ENDPOINT}",
                "api_version": "2024-02-15-preview",
                "deployment_name": "gpt-4-deployment"
            },
            "anthropic": {
                "api_key": "${ANTHROPIC_API_KEY}",
                "base_url": None
            }
        },
        "embedder": {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "embedding_dim": 1536,
            "openai": {
                "api_key": "${OPENAI_API_KEY}"
            },
            "azure_openai": {
                "api_key": "${AZURE_OPENAI_API_KEY}",
                "endpoint": "${AZURE_OPENAI_ENDPOINT}",
                "api_version": "2024-02-15-preview",
                "deployment_name": "embedding-deployment"
            }
        },
        "memory_filter": {
            "enabled": True
        },
        "project": {
            "name": "test-project",
            "version": "1.0.0"
        },
        "search": {
            "limit": 10,
            "num_episodes": 5,
            "num_results": 10
        }
    }

    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all Graphiti-related environment variables."""
    for key in list(os.environ.keys()):
        if any(x in key for x in ['NEO4J', 'OPENAI', 'ANTHROPIC', 'AZURE', 'MODEL', 'GRAPHITI', 'EMBEDDER']):
            monkeypatch.delenv(key, raising=False)


# =============================================================================
# TESTS
# =============================================================================

def test_config_loads_defaults(clean_env):
    """Test that default config loads without file."""
    config = GraphitiConfig._default_config()

    assert config.database.backend == "neo4j"
    assert config.llm.provider == "openai"
    assert config.llm.default_model == "gpt-4o-mini"
    assert config.embedder.provider == "openai"
    assert config.memory_filter.enabled == True
    assert config.llm.semaphore_limit == 10


def test_config_loads_from_file(temp_config_file, monkeypatch, clean_env):
    """Test loading config from graphiti.config.json file."""
    monkeypatch.chdir(temp_config_file.parent)

    config = get_config()

    assert config.database.backend == "neo4j"
    assert config.database.neo4j.uri == "bolt://localhost:7687"
    assert config.database.neo4j.user == "neo4j"
    assert config.llm.provider == "openai"
    assert config.llm.default_model == "gpt-4o-mini"
    assert config.embedder.model == "text-embedding-3-small"


def test_config_env_overrides(temp_config_file, monkeypatch):
    """Test that environment variables override config file settings."""
    monkeypatch.chdir(temp_config_file.parent)

    # Set environment overrides
    monkeypatch.setenv("MODEL_NAME", "gpt-4o")
    monkeypatch.setenv("GRAPHITI_DB_BACKEND", "falkordb")
    monkeypatch.setenv("SEMAPHORE_LIMIT", "20")
    monkeypatch.setenv("NEO4J_URI", "bolt://production:7687")

    config = get_config()

    # Environment variables should override file
    assert config.llm.default_model == "gpt-4o"  # Overridden
    assert config.database.backend == "falkordb"  # Overridden
    assert config.llm.semaphore_limit == 20  # Overridden (int conversion)
    assert config.database.neo4j.uri == "bolt://production:7687"  # Overridden


def test_database_backend_selection(temp_config_file, monkeypatch, clean_env):
    """Test switching between Neo4j and FalkorDB backends."""
    monkeypatch.chdir(temp_config_file.parent)

    # Test Neo4j (default)
    config = get_config()
    db_config = config.database.get_active_config()
    assert config.database.backend == "neo4j"
    assert db_config.uri == "bolt://localhost:7687"
    assert hasattr(db_config, 'user')

    # Switch to FalkorDB via environment
    monkeypatch.setenv("GRAPHITI_DB_BACKEND", "falkordb")
    config = get_config()  # Reload with new backend
    db_config = config.database.get_active_config()
    assert config.database.backend == "falkordb"
    assert "redis:" in db_config.uri.lower()
    assert hasattr(db_config, 'graph_name')


def test_llm_provider_selection(temp_config_file, monkeypatch, clean_env):
    """Test LLM provider switching (OpenAI, Azure, Anthropic)."""
    monkeypatch.chdir(temp_config_file.parent)

    # Test OpenAI (default)
    config = get_config()
    assert config.llm.provider == "openai"
    provider_config = config.llm.get_active_provider_config()
    assert hasattr(provider_config, 'api_key')
    assert hasattr(provider_config, 'base_url')

    # Test Azure OpenAI
    # Update config file
    config_data = json.loads(temp_config_file.read_text())
    config_data['llm']['provider'] = 'azure_openai'
    temp_config_file.write_text(json.dumps(config_data, indent=2))

    config = get_config()
    assert config.llm.provider == "azure_openai"
    provider_config = config.llm.get_active_provider_config()
    assert hasattr(provider_config, 'endpoint')
    assert hasattr(provider_config, 'deployment_name')

    # Test Anthropic
    config_data['llm']['provider'] = 'anthropic'
    temp_config_file.write_text(json.dumps(config_data, indent=2))

    config = get_config()
    assert config.llm.provider == "anthropic"
    provider_config = config.llm.get_active_provider_config()
    assert hasattr(provider_config, 'api_key')


def test_config_validation():
    """Test that invalid configurations raise validation errors."""

    # Invalid database backend
    with pytest.raises(ValueError, match="backend"):
        GraphitiConfig(database={"backend": "postgresql"})  # Not supported

    # Invalid LLM provider
    with pytest.raises(ValueError, match="provider"):
        GraphitiConfig(llm={"provider": "gpt3"})  # Not supported

    # Invalid type for semaphore_limit
    with pytest.raises(ValueError):
        GraphitiConfig(llm={"semaphore_limit": "not_a_number"})


def test_missing_secrets(temp_config_file, monkeypatch, clean_env):
    """Test graceful handling when API keys are missing."""
    monkeypatch.chdir(temp_config_file.parent)

    # Ensure no API keys in environment
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    config = get_config()

    # Config should load with placeholder or None for secrets
    # ${ENV_VAR} placeholders should remain as-is when env var not set
    assert config.llm.openai.api_key in (None, "", "${OPENAI_API_KEY}", "your-api-key-here")


def test_config_reload(temp_config_file, monkeypatch):
    """Test that configuration can be reloaded after file changes."""
    monkeypatch.chdir(temp_config_file.parent)

    # Load initial config
    config1 = get_config()
    initial_backend = config1.database.backend
    assert initial_backend == "neo4j"

    # Modify config file
    config_data = json.loads(temp_config_file.read_text())
    config_data['database']['backend'] = 'falkordb'
    temp_config_file.write_text(json.dumps(config_data, indent=2))

    # Clear any caching (implementation-specific)
    # If get_config() caches, you may need to clear it
    # Example: get_config.cache_clear() if using lru_cache

    # Reload config
    config2 = get_config()
    assert config2.database.backend == 'falkordb'


def test_environment_variable_types(monkeypatch, clean_env):
    """Test that environment variable type conversion works correctly."""

    # Integer conversion
    monkeypatch.setenv("SEMAPHORE_LIMIT", "25")
    config = get_config()
    assert config.llm.semaphore_limit == 25
    assert isinstance(config.llm.semaphore_limit, int)

    # String (no conversion)
    monkeypatch.setenv("MODEL_NAME", "gpt-4o")
    config = get_config()
    assert config.llm.default_model == "gpt-4o"
    assert isinstance(config.llm.default_model, str)


def test_config_search_order(tmp_path, monkeypatch, clean_env):
    """Test configuration search order (project > global > defaults)."""

    # Create project-level config
    project_config = tmp_path / "graphiti.config.json"
    project_config.write_text(json.dumps({
        "database": {"backend": "neo4j"},
        "llm": {"provider": "openai", "default_model": "gpt-4o-project"}
    }))

    monkeypatch.chdir(tmp_path)
    config = get_config()

    # Should load from project directory
    assert config.llm.default_model == "gpt-4o-project"


# Run with: pytest tests/test_unified_config.py -v --cov=mcp_server.unified_config --cov-report=term
```

---

## Shared Test Fixtures: tests/conftest.py

**Add these fixtures to conftest.py for use across all test files:**

```python
"""
Shared pytest fixtures for all tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


# =============================================================================
# LLM PROVIDER MOCKS (for filter tests)
# =============================================================================

@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider for filter tests."""
    provider = AsyncMock()
    provider.is_available.return_value = True
    provider.complete.return_value = {
        "should_store": True,
        "category": "user-pref",
        "confidence": 0.9,
        "reason": "User preference detected"
    }
    provider.config = MagicMock()
    provider.config.name = "openai-primary"
    provider.config.provider = "openai"
    provider.config.model = "gpt-4o-mini"
    return provider


@pytest.fixture
def mock_anthropic_provider():
    """Mock Anthropic provider for fallback tests."""
    provider = AsyncMock()
    provider.is_available.return_value = True
    provider.complete.return_value = {
        "should_store": False,
        "category": "skip",
        "confidence": 0.8,
        "reason": "Bug fix already in version control"
    }
    provider.config = MagicMock()
    provider.config.name = "anthropic-fallback"
    provider.config.provider = "anthropic"
    provider.config.model = "claude-3-5-haiku-20241022"
    return provider


@pytest.fixture
def failing_provider():
    """Mock provider that always fails (for fallback testing)."""
    provider = AsyncMock()
    provider.is_available.return_value = True
    provider.complete.side_effect = Exception("API Error: Rate limit exceeded")
    provider.config = MagicMock()
    provider.config.name = "failing-provider"
    return provider


@pytest.fixture
def mock_filter_config():
    """Mock filter configuration."""
    config = MagicMock()
    config.enabled = True
    config.max_context_size = 10000
    config.context_cleanup_threshold = 8000
    config.categories = {
        "store": ["user-pref", "env-quirk", "project-decision"],
        "skip": ["bug-in-code", "config-in-repo", "ephemeral"]
    }
    return config


# =============================================================================
# SESSION MANAGER MOCKS
# =============================================================================

@pytest.fixture
def mock_session():
    """Mock session for filter tests."""
    session = MagicMock()
    session.session_id = "test-session-123"
    session.query_count = 0
    session.context_tokens = 0
    session.reset_context = MagicMock()
    session.should_cleanup = MagicMock(return_value=False)
    return session
```

---

## Test File 3: tests/test_filter_manager.py

**Key tests with LLM mocking patterns:**

```python
"""
Tests for memory filter system.
Coverage target: >85% of llm_provider, session_manager, filter_manager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_server.filter_manager import FilterManager
from mcp_server.session_manager import SessionManager


# =============================================================================
# FILTER DECISION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_env_quirk_detection(mock_openai_provider, mock_filter_config):
    """Test that env quirks are correctly detected and marked for storage."""

    # Setup provider to return env-quirk decision
    mock_openai_provider.complete.return_value = {
        "should_store": True,
        "category": "env-quirk",
        "confidence": 0.95,
        "reason": "OS-specific timeout configuration"
    }

    # Create session manager with mocked provider
    session_mgr = MagicMock()
    session = MagicMock()
    session.provider = mock_openai_provider
    session.session_id = "test-session"
    session.query_count = 0
    session.context_tokens = 0
    session_mgr.get_or_create_session.return_value = session
    session_mgr.config = mock_filter_config

    filter_mgr = FilterManager(session_mgr)

    result = await filter_mgr.should_store(
        content="Neo4j timeout fixed by setting NEO4J_TIMEOUT=60 in .env",
        context="Edited .env (gitignored file)"
    )

    assert result['should_store'] == True
    assert result['category'] == 'env-quirk'
    assert result['confidence'] >= 0.9
    mock_openai_provider.complete.assert_called_once()


@pytest.mark.asyncio
async def test_bug_fix_detection(mock_openai_provider, mock_filter_config):
    """Test that bug fixes in code are detected and marked to skip."""

    # Setup provider to return skip decision
    mock_openai_provider.complete.return_value = {
        "should_store": False,
        "category": "bug-in-code",
        "confidence": 0.92,
        "reason": "Bug fix now in version control"
    }

    session_mgr = MagicMock()
    session = MagicMock()
    session.provider = mock_openai_provider
    session.session_id = "test-session"
    session_mgr.get_or_create_session.return_value = session
    session_mgr.config = mock_filter_config

    filter_mgr = FilterManager(session_mgr)

    result = await filter_mgr.should_store(
        content="Fixed infinite loop in parseData()",
        context="Edited src/parser.py, committed to git"
    )

    assert result['should_store'] == False
    assert result['category'] == 'bug-in-code'


@pytest.mark.asyncio
async def test_hierarchical_fallback(failing_provider, mock_anthropic_provider, mock_filter_config):
    """Test fallback from failed primary provider to secondary."""

    # Setup: Primary fails, secondary works
    session_mgr = MagicMock()
    session_mgr.providers = [failing_provider, mock_anthropic_provider]
    session_mgr.config = mock_filter_config

    # First call should fail and trigger fallback
    session1 = MagicMock()
    session1.provider = failing_provider
    session1.session_id = "session-1"

    # Second call should use fallback
    session2 = MagicMock()
    session2.provider = mock_anthropic_provider
    session2.session_id = "session-2"

    session_mgr.get_or_create_session.side_effect = [
        Exception("Primary failed"),  # First attempt fails
        session2  # Fallback succeeds
    ]

    filter_mgr = FilterManager(session_mgr)

    # Should gracefully fall back to anthropic
    result = await filter_mgr.should_store("test content", "test context")

    assert result['should_store'] == False  # Anthropic's response
    assert result['category'] == 'skip'


@pytest.mark.asyncio
async def test_graceful_degradation(mock_filter_config):
    """Test that system degrades gracefully when all providers fail."""

    session_mgr = MagicMock()
    session_mgr.get_or_create_session.side_effect = RuntimeError("No providers available")
    session_mgr.config = mock_filter_config

    filter_mgr = FilterManager(session_mgr)

    # Should default to storing when filter fails
    result = await filter_mgr.should_store("test", "test")

    assert result['should_store'] == True  # Safe default
    assert result['category'] == 'filter_error'


# Run with: pytest tests/test_filter_manager.py -v --cov=mcp_server.filter_manager
```

---

## Quick Reference: Running Tests

```bash
# Run all Phase 6 tests
pytest tests/test_unified_config.py tests/test_filter_manager.py -v

# With coverage
pytest tests/ -v --cov=mcp_server --cov-report=html --cov-report=term

# Specific test file
pytest tests/test_unified_config.py -v

# Specific test function
pytest tests/test_unified_config.py::test_config_loads_defaults -v

# Coverage threshold check
pytest --cov=mcp_server --cov-fail-under=80
```

---

**Note**: For complete implementation of all test files (test_mcp_integration.py, test_e2e_unified_config.py), follow the same patterns shown above with appropriate mocks and assertions.
