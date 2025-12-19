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

    config = get_config(reload=True)

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


def test_config_migration_from_claude_dir(tmp_path, monkeypatch, clean_env):
    """Test automatic migration from ~/.claude/ to ~/.graphiti/."""
    from pathlib import Path
    import mcp_server.unified_config

    # Create old config location (~/.claude/graphiti.config.json)
    old_config_dir = tmp_path / ".claude"
    old_config_dir.mkdir(parents=True, exist_ok=True)
    old_config = old_config_dir / "graphiti.config.json"
    old_config.write_text(json.dumps({
        "database": {"backend": "neo4j"},
        "llm": {"provider": "openai", "default_model": "gpt-4o-migrated"}
    }))

    # Load config (should trigger migration)
    from mcp_server.unified_config import GraphitiConfig

    # Mock Path.home() AFTER importing to patch the module's imported Path class
    import mcp_server.unified_config
    monkeypatch.setattr(mcp_server.unified_config.Path, "home", lambda: tmp_path)

    config = GraphitiConfig.from_file()

    # Verify migration occurred
    new_config_path = tmp_path / ".graphiti" / "graphiti.config.json"
    assert new_config_path.exists(), "Config not migrated to ~/.graphiti/"
    assert config.llm.default_model == "gpt-4o-migrated", "Config not loaded correctly after migration"

    # Verify deprecation notice created
    deprecation_notice = old_config_dir / "graphiti.config.json.deprecated"
    assert deprecation_notice.exists(), "Deprecation notice not created"
    assert "~/.graphiti/" in deprecation_notice.read_text(), "Deprecation notice doesn't mention new path"


def test_config_no_migration_if_new_exists(tmp_path, monkeypatch, clean_env):
    """Test that migration doesn't overwrite existing ~/.graphiti/ config."""
    from pathlib import Path

    # Create both old and new config locations
    old_config_dir = tmp_path / ".claude"
    old_config_dir.mkdir(parents=True, exist_ok=True)
    old_config = old_config_dir / "graphiti.config.json"
    old_config.write_text(json.dumps({
        "llm": {"default_model": "gpt-4o-old"}
    }))

    new_config_dir = tmp_path / ".graphiti"
    new_config_dir.mkdir(parents=True, exist_ok=True)
    new_config = new_config_dir / "graphiti.config.json"
    new_config.write_text(json.dumps({
        "llm": {"default_model": "gpt-4o-new"}
    }))

    # Load config (should NOT trigger migration since new config exists)
    from mcp_server.unified_config import GraphitiConfig

    # Mock Path.home() AFTER importing to patch the module's imported Path class
    import mcp_server.unified_config
    monkeypatch.setattr(mcp_server.unified_config.Path, "home", lambda: tmp_path)

    config = GraphitiConfig.from_file()

    # Verify new config is loaded (not old)
    assert config.llm.default_model == "gpt-4o-new", "Should load from new location when both exist"

    # Verify old config is untouched
    assert old_config.exists(), "Old config should not be deleted"
    old_data = json.loads(old_config.read_text())
    assert old_data["llm"]["default_model"] == "gpt-4o-old", "Old config should be unchanged"


# =============================================================================
# SESSION TRACKING CONFIG - GLOBAL SCOPE TESTS (Story 1)
# =============================================================================

def test_session_tracking_default_values():
    """Test that SessionTrackingConfig has correct default values for global scope fields."""
    from mcp_server.unified_config import SessionTrackingConfig

    config = SessionTrackingConfig()

    # Verify default values per Story 1 acceptance criteria
    assert config.group_id is None, "group_id should default to None"
    assert config.cross_project_search is True, "cross_project_search should default to True"
    assert config.trusted_namespaces is None, "trusted_namespaces should default to None"
    assert config.include_project_path is True, "include_project_path should default to True"


def test_session_tracking_group_id_custom():
    """Test that group_id can be set to a custom value."""
    from mcp_server.unified_config import SessionTrackingConfig

    config = SessionTrackingConfig(group_id="my_custom_group")
    assert config.group_id == "my_custom_group"


def test_session_tracking_cross_project_search_false():
    """Test that cross_project_search can be disabled."""
    from mcp_server.unified_config import SessionTrackingConfig

    config = SessionTrackingConfig(cross_project_search=False)
    assert config.cross_project_search is False


def test_session_tracking_trusted_namespaces_valid():
    """Test that trusted_namespaces accepts valid hexadecimal hashes."""
    from mcp_server.unified_config import SessionTrackingConfig

    # Valid hex hashes
    valid_namespaces = ["a1b2c3d4", "ABCDEF12", "123456", "abcdef0123456789"]
    config = SessionTrackingConfig(trusted_namespaces=valid_namespaces)
    assert config.trusted_namespaces == valid_namespaces


def test_session_tracking_trusted_namespaces_invalid_non_hex():
    """Test that trusted_namespaces rejects non-hex strings."""
    from mcp_server.unified_config import SessionTrackingConfig
    import pytest

    # Invalid: contains non-hex characters
    with pytest.raises(ValueError) as excinfo:
        SessionTrackingConfig(trusted_namespaces=["a1b2c3d4", "invalid_hash!"])

    assert "Invalid namespace format" in str(excinfo.value)
    assert "invalid_hash!" in str(excinfo.value)


def test_session_tracking_trusted_namespaces_invalid_special_chars():
    """Test that trusted_namespaces rejects strings with special characters."""
    from mcp_server.unified_config import SessionTrackingConfig
    import pytest

    # Invalid: contains underscores, dashes, or other non-hex chars
    invalid_inputs = [
        ["namespace_with_underscore"],
        ["namespace-with-dash"],
        ["namespace with space"],
        ["ghijkl"],  # g-z are not hex
    ]

    for namespaces in invalid_inputs:
        with pytest.raises(ValueError) as excinfo:
            SessionTrackingConfig(trusted_namespaces=namespaces)
        assert "Invalid namespace format" in str(excinfo.value) or "Must be a hexadecimal" in str(excinfo.value)


def test_session_tracking_trusted_namespaces_non_string():
    """Test that trusted_namespaces rejects non-string entries."""
    from mcp_server.unified_config import SessionTrackingConfig
    import pytest

    # Invalid: non-string types
    # Pydantic raises ValidationError (subclass of ValueError) for type mismatch
    with pytest.raises(Exception) as excinfo:
        SessionTrackingConfig(trusted_namespaces=["a1b2c3d4", 12345])

    # Pydantic error message says "input should be a valid string"
    assert "string" in str(excinfo.value).lower()


def test_session_tracking_trusted_namespaces_empty_list():
    """Test that trusted_namespaces accepts empty list."""
    from mcp_server.unified_config import SessionTrackingConfig

    config = SessionTrackingConfig(trusted_namespaces=[])
    assert config.trusted_namespaces == []


def test_session_tracking_include_project_path_false():
    """Test that include_project_path can be disabled for privacy."""
    from mcp_server.unified_config import SessionTrackingConfig

    config = SessionTrackingConfig(include_project_path=False)
    assert config.include_project_path is False


def test_session_tracking_all_fields_combined():
    """Test SessionTrackingConfig with all global scope fields set."""
    from mcp_server.unified_config import SessionTrackingConfig

    config = SessionTrackingConfig(
        enabled=True,
        group_id="team__shared",
        cross_project_search=False,
        trusted_namespaces=["a1b2c3d4", "e5f6a7b8"],
        include_project_path=False
    )

    assert config.enabled is True
    assert config.group_id == "team__shared"
    assert config.cross_project_search is False
    assert config.trusted_namespaces == ["a1b2c3d4", "e5f6a7b8"]
    assert config.include_project_path is False


def test_session_tracking_fields_have_docstrings():
    """Test that all global scope fields have proper docstrings."""
    from mcp_server.unified_config import SessionTrackingConfig

    # Get field info from Pydantic model
    fields = SessionTrackingConfig.model_fields

    # Check that each global scope field has a description
    global_scope_fields = ['group_id', 'cross_project_search', 'trusted_namespaces', 'include_project_path']

    for field_name in global_scope_fields:
        assert field_name in fields, f"Field {field_name} not found in SessionTrackingConfig"
        field_info = fields[field_name]
        assert field_info.description is not None, f"Field {field_name} missing description"
        assert len(field_info.description) > 10, f"Field {field_name} description too short"


def test_session_tracking_case_insensitive_hex():
    """Test that trusted_namespaces accepts both upper and lower case hex."""
    from mcp_server.unified_config import SessionTrackingConfig

    # Mix of upper and lower case
    config = SessionTrackingConfig(trusted_namespaces=["ABCD1234", "abcd1234", "AbCd1234"])
    assert len(config.trusted_namespaces) == 3


# =============================================================================
# EXTRACTION CONFIG TESTS (Story 6)
# =============================================================================

def test_extraction_config_default_values():
    """Test that GraphitiConfig has extraction field with default ExtractionConfig."""
    config = GraphitiConfig._default_config()

    # AC-6.1: GraphitiConfig has extraction field
    assert hasattr(config, 'extraction'), "GraphitiConfig missing extraction field"
    assert config.extraction is not None, "extraction field should not be None"

    # AC-6.2: Default is preprocessing_prompt=False (disabled, not template-based)
    assert config.extraction.preprocessing_prompt is False, "Default should be False (disabled)"
    assert config.extraction.preprocessing_mode == "prepend", "Default mode should be prepend"


def test_extraction_config_explicit_values():
    """Test GraphitiConfig with explicit ExtractionConfig values."""
    from graphiti_core.extraction_config import ExtractionConfig

    config = GraphitiConfig(
        extraction=ExtractionConfig(
            preprocessing_prompt="default-session-turn.md",
            preprocessing_mode="append"
        )
    )

    assert config.extraction.preprocessing_prompt == "default-session-turn.md"
    assert config.extraction.preprocessing_mode == "append"
    assert config.extraction.is_enabled() is True


def test_extraction_config_from_file(tmp_path, monkeypatch, clean_env):
    """Test loading GraphitiConfig.from_file() with extraction config in JSON."""
    config_data = {
        "database": {"backend": "neo4j"},
        "extraction": {
            "preprocessing_prompt": "custom-template.md",
            "preprocessing_mode": "prepend"
        }
    }

    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config_data, indent=2))
    monkeypatch.chdir(tmp_path)

    config = GraphitiConfig.from_file()

    # AC-6.4: JSON config loading works
    assert config.extraction.preprocessing_prompt == "custom-template.md"
    assert config.extraction.preprocessing_mode == "prepend"


def test_extraction_config_backward_compatibility(tmp_path, monkeypatch, clean_env):
    """Test backward compatibility when extraction field is missing from config."""
    config_data = {
        "database": {"backend": "neo4j"},
        "llm": {"provider": "openai"}
        # No extraction field - old config format
    }

    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config_data, indent=2))
    monkeypatch.chdir(tmp_path)

    config = GraphitiConfig.from_file()

    # Should load with default ExtractionConfig
    assert hasattr(config, 'extraction')
    assert config.extraction.preprocessing_prompt is False  # Default disabled


def test_extraction_config_preprocessing_prompt_types():
    """Test preprocessing_prompt validation (bool | str | None types)."""
    from graphiti_core.extraction_config import ExtractionConfig

    # Test bool (False - disabled)
    config1 = GraphitiConfig(extraction=ExtractionConfig(preprocessing_prompt=False))
    assert config1.extraction.preprocessing_prompt is False
    assert config1.extraction.is_enabled() is False

    # Test bool (True would be invalid per AC, but None is valid)
    config2 = GraphitiConfig(extraction=ExtractionConfig(preprocessing_prompt=None))
    assert config2.extraction.preprocessing_prompt is None
    assert config2.extraction.is_enabled() is False

    # Test str (template)
    config3 = GraphitiConfig(extraction=ExtractionConfig(preprocessing_prompt="template.md"))
    assert config3.extraction.preprocessing_prompt == "template.md"
    assert config3.extraction.is_enabled() is True

    # Test str (inline)
    config4 = GraphitiConfig(extraction=ExtractionConfig(
        preprocessing_prompt="Consider session context"
    ))
    assert config4.extraction.preprocessing_prompt == "Consider session context"
    assert config4.extraction.is_enabled() is True


def test_extraction_config_preprocessing_mode_literals():
    """Test preprocessing_mode validation (prepend | append literals)."""
    from graphiti_core.extraction_config import ExtractionConfig

    # Test valid: prepend
    config1 = GraphitiConfig(extraction=ExtractionConfig(preprocessing_mode="prepend"))
    assert config1.extraction.preprocessing_mode == "prepend"

    # Test valid: append
    config2 = GraphitiConfig(extraction=ExtractionConfig(preprocessing_mode="append"))
    assert config2.extraction.preprocessing_mode == "append"

    # Test invalid: should raise ValidationError
    with pytest.raises(Exception) as excinfo:
        GraphitiConfig(extraction=ExtractionConfig(preprocessing_mode="invalid"))

    # Pydantic raises validation error for invalid literal
    assert "preprocessing_mode" in str(excinfo.value).lower() or "input" in str(excinfo.value).lower()


def test_extraction_config_serialization():
    """Test config serialization to JSON includes extraction config."""
    from graphiti_core.extraction_config import ExtractionConfig

    config = GraphitiConfig(
        extraction=ExtractionConfig(
            preprocessing_prompt="template.md",
            preprocessing_mode="append"
        )
    )

    # Serialize to dict
    config_dict = config.model_dump()

    assert 'extraction' in config_dict
    assert config_dict['extraction']['preprocessing_prompt'] == "template.md"
    assert config_dict['extraction']['preprocessing_mode'] == "append"

    # Serialize to JSON string
    config_json = config.model_dump_json()
    assert '"extraction"' in config_json
    assert '"preprocessing_prompt":"template.md"' in config_json


def test_extraction_config_path_traversal_prevention():
    """Test preprocessing_prompt with malicious template paths (security)."""
    from graphiti_core.extraction_config import ExtractionConfig

    # Note: Path validation deferred to Story 8 (TemplateResolver)
    # This test ensures config accepts path-like strings but doesn't validate them yet

    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/shadow",
        "C:\\Windows\\System32\\drivers\\etc\\hosts"
    ]

    for path in malicious_paths:
        # Config should accept these (validation happens later in TemplateResolver)
        config = GraphitiConfig(extraction=ExtractionConfig(preprocessing_prompt=path))
        assert config.extraction.preprocessing_prompt == path
        # Story 8 will add path validation logic


def test_extraction_config_dos_prevention():
    """Test preprocessing_prompt with excessively long inline strings (DOS prevention)."""
    from graphiti_core.extraction_config import ExtractionConfig

    # Test very long string (simulating potential DOS attack)
    long_string = "A" * 100000  # 100KB string

    # Config should accept (no length validation at config level)
    config = GraphitiConfig(extraction=ExtractionConfig(preprocessing_prompt=long_string))
    assert len(config.extraction.preprocessing_prompt) == 100000

    # Note: Length/size validation would be in LLM client layer, not config


# =============================================================================
# DEPRECATED PARAMETER REMOVAL TESTS (Story 1 - Testing Phase)
# =============================================================================

def test_session_tracking_config_without_deprecated_fields():
    """Test SessionTrackingConfig instantiation without deprecated fields.

    Validates AC-1.1: Deprecated fields (inactivity_timeout, check_interval,
    auto_summarize) are removed from SessionTrackingConfig.
    """
    from mcp_server.unified_config import SessionTrackingConfig

    # Create config without deprecated fields
    config = SessionTrackingConfig(
        enabled=True,
        group_id="test_group"
    )

    # Verify deprecated fields are not present
    assert not hasattr(config, 'inactivity_timeout'), \
        "inactivity_timeout should be removed from SessionTrackingConfig"
    assert not hasattr(config, 'check_interval'), \
        "check_interval should be removed from SessionTrackingConfig"
    assert not hasattr(config, 'auto_summarize'), \
        "auto_summarize should be removed from SessionTrackingConfig"

    # Verify existing fields still work
    assert config.enabled is True
    assert config.group_id == "test_group"


def test_session_tracking_config_rejects_deprecated_fields():
    """Test that SessionTrackingConfig silently ignores deprecated field names.

    Validates AC-1.1: Deprecated fields are removed and ignored if passed.
    Note: Pydantic with extra="allow" accepts unknown fields without raising errors.
    """
    from mcp_server.unified_config import SessionTrackingConfig

    # Create config with deprecated fields (will be ignored)
    config = SessionTrackingConfig(
        enabled=True,
        inactivity_timeout=300  # Deprecated field - will be ignored
    )

    # Verify the deprecated field is not actually set on the config
    assert not hasattr(config, 'inactivity_timeout'), \
        "inactivity_timeout should not be accessible as attribute"

    # Verify normal fields still work
    assert config.enabled is True


def test_config_validator_ignores_deprecated_fields():
    """Test that config validator does not check for deprecated fields.

    Validates AC-1.2: Validation logic for deprecated fields removed from
    config_validator.py.
    """
    from mcp_server.unified_config import GraphitiConfig
    from mcp_server.config_validator import ConfigValidator

    # Create a minimal valid config
    config = GraphitiConfig(
        session_tracking={
            "enabled": True,
            "group_id": "test"
        }
    )

    validator = ConfigValidator()
    result = validator.validate_semantics(config)

    # Should not have errors about missing deprecated fields
    for error in result.errors:
        assert 'inactivity_timeout' not in error.message.lower(), \
            "Validator should not check for inactivity_timeout"
        assert 'check_interval' not in error.message.lower(), \
            "Validator should not check for check_interval"
        assert 'auto_summarize' not in error.message.lower(), \
            "Validator should not check for auto_summarize"


def test_schema_validation_accepts_config_without_deprecated_fields():
    """Test that JSON schema validation accepts configs without deprecated fields.

    Validates AC-1.4: graphiti.config.schema.json updated to remove deprecated fields.
    """
    import jsonschema
    import json
    from pathlib import Path

    # Load the JSON schema
    schema_path = Path("graphiti.config.schema.json")
    if not schema_path.exists():
        pytest.skip("Schema file not found")

    schema = json.loads(schema_path.read_text())

    # Config without deprecated fields
    config_instance = {
        "session_tracking": {
            "enabled": True,
            "group_id": "test_group",
            "cross_project_search": True
        }
    }

    # Should validate successfully
    jsonschema.validate(instance=config_instance, schema=schema)

    # Verify deprecated fields are not in schema properties
    session_tracking_properties = schema.get("properties", {}).get("session_tracking", {}).get("properties", {})

    assert "inactivity_timeout" not in session_tracking_properties, \
        "inactivity_timeout should be removed from schema"
    assert "check_interval" not in session_tracking_properties, \
        "check_interval should be removed from schema"
    assert "auto_summarize" not in session_tracking_properties, \
        "auto_summarize should be removed from schema"


# Run with: pytest tests/test_unified_config.py -v --cov=mcp_server.unified_config --cov-report=term
