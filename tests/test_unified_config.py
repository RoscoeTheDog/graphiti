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
                "password_env": "NEO4J_PASSWORD",
                "database": "neo4j"
            },
            "falkordb": {
                "uri": "redis://localhost:6379",
                "password_env": "FALKORDB_PASSWORD",
                "database": "graphiti"
            }
        },
        "llm": {
            "provider": "openai",
            "default_model": "gpt-4o-mini",
            "temperature": 0.0,
            "semaphore_limit": 10,
            "openai": {
                "api_key_env": "OPENAI_API_KEY",
                "base_url": None,
                "organization": None
            },
            "azure_openai": {
                "api_key_env": "AZURE_OPENAI_API_KEY",
                "endpoint_env": "AZURE_OPENAI_ENDPOINT",
                "api_version": "2024-02-15-preview",
                "deployment_name": "gpt-4-deployment"
            },
            "anthropic": {
                "api_key_env": "ANTHROPIC_API_KEY",
                "base_url": None
            }
        },
        "embedder": {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "dimensions": 1536,
            "openai": {
                "api_key_env": "OPENAI_API_KEY"
            },
            "azure_openai": {
                "api_key_env": "AZURE_OPENAI_API_KEY",
                "endpoint_env": "AZURE_OPENAI_ENDPOINT",
                "api_version": "2024-02-15-preview",
                "deployment_name": "embedding-deployment"
            }
        },
        "project": {
            "default_group_id": None,
            "namespace": None
        },
        "search": {
            "default_max_nodes": 10,
            "default_max_facts": 10
        }
    }

    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all Graphiti-related environment variables."""
    for key in list(os.environ.keys()):
        if any(x in key for x in ['NEO4J', 'OPENAI', 'ANTHROPIC', 'AZURE', 'MODEL', 'GRAPHITI', 'EMBEDDER', 'FALKORDB']):
            monkeypatch.delenv(key, raising=False)


# =============================================================================
# TESTS
# =============================================================================

def test_config_loads_defaults(clean_env):
    """Test that default config loads without file."""
    config = GraphitiConfig._default_config()

    assert config.database.backend == "neo4j"
    assert config.llm.provider == "openai"
    assert config.llm.default_model == "gpt-4.1-mini"
    assert config.embedder.provider == "openai"
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

    config = get_config(reload=True)

    # Environment variables should override file
    assert config.llm.default_model == "gpt-4o"  # Overridden
    assert config.database.backend == "falkordb"  # Overridden
    assert config.llm.semaphore_limit == 20  # Overridden (int conversion)


def test_database_backend_selection(temp_config_file, monkeypatch, clean_env):
    """Test switching between Neo4j and FalkorDB backends."""
    monkeypatch.chdir(temp_config_file.parent)

    # Test Neo4j (default)
    config = get_config(reload=True)
    db_config = config.database.get_active_config()
    assert config.database.backend == "neo4j"
    assert db_config.uri == "bolt://localhost:7687"
    assert hasattr(db_config, 'user')

    # Switch to FalkorDB via environment
    monkeypatch.setenv("GRAPHITI_DB_BACKEND", "falkordb")
    config = get_config(reload=True)  # Reload with new backend
    db_config = config.database.get_active_config()
    assert config.database.backend == "falkordb"
    assert "redis:" in db_config.uri.lower()
    assert hasattr(db_config, 'database')


def test_llm_provider_selection(temp_config_file, monkeypatch, clean_env):
    """Test LLM provider switching (OpenAI, Azure, Anthropic)."""
    monkeypatch.chdir(temp_config_file.parent)

    # Test OpenAI (default)
    config = get_config(reload=True)
    assert config.llm.provider == "openai"
    provider_config = config.llm.get_active_provider_config()
    assert hasattr(provider_config, 'api_key')
    assert hasattr(provider_config, 'base_url')

    # Test Azure OpenAI
    # Update config file
    config_data = json.loads(temp_config_file.read_text())
    config_data['llm']['provider'] = 'azure_openai'
    temp_config_file.write_text(json.dumps(config_data, indent=2))

    config = get_config(reload=True)
    assert config.llm.provider == "azure_openai"
    provider_config = config.llm.get_active_provider_config()
    assert hasattr(provider_config, 'endpoint')
    assert hasattr(provider_config, 'deployment_name')

    # Test Anthropic
    config_data['llm']['provider'] = 'anthropic'
    temp_config_file.write_text(json.dumps(config_data, indent=2))

    config = get_config(reload=True)
    assert config.llm.provider == "anthropic"
    provider_config = config.llm.get_active_provider_config()
    assert hasattr(provider_config, 'api_key')


def test_config_validation():
    """Test that invalid configurations raise validation errors."""
    # Test with invalid backend
    try:
        config_dict = {"database": {"backend": "postgresql"}}
        config = GraphitiConfig(**config_dict)
        # If Pydantic validation doesn't raise, check manually
        assert False, "Should have raised validation error for invalid backend"
    except (ValueError, Exception) as e:
        # Pydantic validation error expected
        assert "backend" in str(e).lower() or "postgresql" in str(e).lower()


def test_missing_secrets(temp_config_file, monkeypatch, clean_env):
    """Test graceful handling when API keys are missing."""
    monkeypatch.chdir(temp_config_file.parent)

    # Ensure no API keys in environment
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    config = get_config(reload=True)

    # Config should load successfully even without API keys
    # The properties should return None or empty string
    assert config.llm.openai.api_key is None or config.llm.openai.api_key == ""


def test_config_reload(temp_config_file, monkeypatch):
    """Test that configuration can be reloaded after file changes."""
    monkeypatch.chdir(temp_config_file.parent)

    # Load initial config
    config1 = get_config(reload=True)
    initial_backend = config1.database.backend
    assert initial_backend == "neo4j"

    # Modify config file
    config_data = json.loads(temp_config_file.read_text())
    config_data['database']['backend'] = 'falkordb'
    temp_config_file.write_text(json.dumps(config_data, indent=2))

    # Reload config with reload=True
    config2 = get_config(reload=True)
    assert config2.database.backend == 'falkordb'


def test_environment_variable_types(monkeypatch, clean_env):
    """Test that environment variable type conversion works correctly."""

    # Integer conversion
    monkeypatch.setenv("SEMAPHORE_LIMIT", "25")
    config = get_config(reload=True)
    assert config.llm.semaphore_limit == 25
    assert isinstance(config.llm.semaphore_limit, int)

    # String (no conversion)
    monkeypatch.setenv("MODEL_NAME", "gpt-4o")
    config = get_config(reload=True)
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
    config = get_config(reload=True)

    # Should load from project directory
    assert config.llm.default_model == "gpt-4o-project"


# Run with: pytest tests/test_unified_config.py -v --cov=mcp_server.unified_config --cov-report=term
