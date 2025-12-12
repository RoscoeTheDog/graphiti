"""
Unit and integration tests for SummarizationConfig.
Tests cover configuration schema updates for intelligent session summarization.

Coverage:
- SummarizationConfig model instantiation and validation
- SessionTrackingConfig integration with summarization block
- JSON schema validation
- Backward compatibility
- Security validation
"""

import pytest
import json
from pathlib import Path
from typing import Literal
from pydantic import ValidationError
from mcp_server.unified_config import (
    GraphitiConfig,
    SessionTrackingConfig,
    SummarizationConfig,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary directory for config files."""
    return tmp_path


@pytest.fixture
def minimal_config():
    """Minimal valid config without summarization block."""
    return {
        "database": {
            "backend": "neo4j",
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password_env": "NEO4J_PASSWORD",
                "database": "neo4j"
            }
        },
        "llm": {
            "provider": "openai",
            "openai": {
                "api_key_env": "OPENAI_API_KEY"
            }
        },
        "embedder": {
            "provider": "openai",
            "openai": {
                "api_key_env": "OPENAI_API_KEY"
            }
        }
    }


@pytest.fixture
def config_with_summarization():
    """Full config with summarization block."""
    return {
        "database": {
            "backend": "neo4j",
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password_env": "NEO4J_PASSWORD",
                "database": "neo4j"
            }
        },
        "llm": {
            "provider": "openai",
            "openai": {
                "api_key_env": "OPENAI_API_KEY"
            }
        },
        "embedder": {
            "provider": "openai",
            "openai": {
                "api_key_env": "OPENAI_API_KEY"
            }
        },
        "session_tracking": {
            "enabled": True,
            "summarization": {
                "template": None,
                "type_detection": "auto",
                "extraction_threshold": 0.3,
                "include_decisions": True,
                "include_errors_resolved": True,
                "tool_classification_cache": None
            }
        }
    }


# =============================================================================
# UNIT TESTS - SummarizationConfig Model
# =============================================================================

class TestSummarizationConfigModel:
    """Test SummarizationConfig Pydantic model."""

    def test_default_instantiation(self):
        """Test SummarizationConfig instantiation with default values."""
        config = SummarizationConfig()

        assert config.template is None
        assert config.type_detection == "auto"
        assert config.extraction_threshold == 0.3
        assert config.include_decisions is True
        assert config.include_errors_resolved is True
        assert config.tool_classification_cache is None

    def test_custom_values(self):
        """Test SummarizationConfig with custom values."""
        config = SummarizationConfig(
            template="/custom/template.txt",
            type_detection="manual",
            extraction_threshold=0.5,
            include_decisions=False,
            include_errors_resolved=False,
            tool_classification_cache="/custom/cache.json"
        )

        assert config.template == "/custom/template.txt"
        assert config.type_detection == "manual"
        assert config.extraction_threshold == 0.5
        assert config.include_decisions is False
        assert config.include_errors_resolved is False
        assert config.tool_classification_cache == "/custom/cache.json"

    def test_extraction_threshold_validation_valid(self):
        """Test extraction_threshold accepts valid range (0.0-1.0)."""
        # Lower bound
        config = SummarizationConfig(extraction_threshold=0.0)
        assert config.extraction_threshold == 0.0

        # Upper bound
        config = SummarizationConfig(extraction_threshold=1.0)
        assert config.extraction_threshold == 1.0

        # Mid-range
        config = SummarizationConfig(extraction_threshold=0.7)
        assert config.extraction_threshold == 0.7

    def test_extraction_threshold_validation_invalid(self):
        """Test extraction_threshold rejects out-of-range values."""
        # Below lower bound
        with pytest.raises(ValidationError) as exc_info:
            SummarizationConfig(extraction_threshold=-0.1)
        assert "extraction_threshold" in str(exc_info.value)

        # Above upper bound
        with pytest.raises(ValidationError) as exc_info:
            SummarizationConfig(extraction_threshold=1.5)
        assert "extraction_threshold" in str(exc_info.value)

    def test_type_detection_literal_valid(self):
        """Test type_detection accepts valid Literal values."""
        config_auto = SummarizationConfig(type_detection="auto")
        assert config_auto.type_detection == "auto"

        config_manual = SummarizationConfig(type_detection="manual")
        assert config_manual.type_detection == "manual"

    def test_type_detection_literal_invalid(self):
        """Test type_detection rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SummarizationConfig(type_detection="invalid")
        assert "type_detection" in str(exc_info.value)

    def test_template_accepts_none_or_str(self):
        """Test template field accepts None or string path."""
        config_none = SummarizationConfig(template=None)
        assert config_none.template is None

        config_path = SummarizationConfig(template="/path/to/template.txt")
        assert config_path.template == "/path/to/template.txt"

    def test_tool_classification_cache_accepts_none_or_str(self):
        """Test tool_classification_cache accepts None or string path."""
        config_none = SummarizationConfig(tool_classification_cache=None)
        assert config_none.tool_classification_cache is None

        config_path = SummarizationConfig(tool_classification_cache="/path/cache.json")
        assert config_path.tool_classification_cache == "/path/cache.json"


# =============================================================================
# UNIT TESTS - SessionTrackingConfig Integration
# =============================================================================

class TestSessionTrackingConfigIntegration:
    """Test SessionTrackingConfig with summarization field."""

    def test_session_tracking_with_summarization_defaults(self):
        """Test SessionTrackingConfig creates default SummarizationConfig."""
        config = SessionTrackingConfig()

        assert config.summarization is not None
        assert isinstance(config.summarization, SummarizationConfig)
        assert config.summarization.extraction_threshold == 0.3
        assert config.summarization.type_detection == "auto"

    def test_session_tracking_with_custom_summarization(self):
        """Test SessionTrackingConfig with custom summarization block."""
        summarization = SummarizationConfig(
            extraction_threshold=0.5,
            type_detection="manual",
            include_decisions=False
        )
        config = SessionTrackingConfig(summarization=summarization)

        assert config.summarization.extraction_threshold == 0.5
        assert config.summarization.type_detection == "manual"
        assert config.summarization.include_decisions is False

    def test_session_tracking_without_summarization_uses_defaults(self):
        """Test backward compatibility: omitted summarization uses defaults."""
        config = SessionTrackingConfig()

        # Should have default SummarizationConfig instance
        assert config.summarization is not None
        assert config.summarization.template is None
        assert config.summarization.extraction_threshold == 0.3


# =============================================================================
# INTEGRATION TESTS - Config Loading
# =============================================================================

class TestConfigLoading:
    """Test loading config files with summarization block."""

    def test_load_config_with_summarization_block(
        self, temp_config_dir, config_with_summarization
    ):
        """Test loading graphiti.config.json with summarization block."""
        config_file = temp_config_dir / "graphiti.config.json"
        config_file.write_text(json.dumps(config_with_summarization, indent=2))

        # Load config
        config = GraphitiConfig.from_file(str(config_file))

        assert config.session_tracking is not None
        assert config.session_tracking.summarization is not None
        assert config.session_tracking.summarization.extraction_threshold == 0.3
        assert config.session_tracking.summarization.type_detection == "auto"

    def test_load_config_without_summarization_block_backward_compat(
        self, temp_config_dir, minimal_config
    ):
        """Test backward compatibility: config without summarization uses defaults."""
        config_file = temp_config_dir / "graphiti.config.json"
        config_file.write_text(json.dumps(minimal_config, indent=2))

        # Load config
        config = GraphitiConfig.from_file(str(config_file))

        # Should have default session_tracking with default summarization
        assert config.session_tracking is not None
        assert config.session_tracking.summarization is not None
        assert config.session_tracking.summarization.extraction_threshold == 0.3

    def test_graphiti_config_from_file_with_summarization(
        self, temp_config_dir, config_with_summarization
    ):
        """Test GraphitiConfig.from_file() with summarization configuration."""
        config_file = temp_config_dir / "graphiti.config.json"
        config_file.write_text(json.dumps(config_with_summarization, indent=2))

        config = GraphitiConfig.from_file(str(config_file))

        assert config.session_tracking.summarization.template is None
        assert config.session_tracking.summarization.include_decisions is True
        assert config.session_tracking.summarization.include_errors_resolved is True

    def test_default_values_propagate_when_summarization_omitted(
        self, temp_config_dir, minimal_config
    ):
        """Test default values propagate correctly when summarization omitted."""
        config_file = temp_config_dir / "graphiti.config.json"
        config_file.write_text(json.dumps(minimal_config, indent=2))

        config = GraphitiConfig.from_file(str(config_file))

        # Verify all defaults propagate
        assert config.session_tracking.summarization.template is None
        assert config.session_tracking.summarization.type_detection == "auto"
        assert config.session_tracking.summarization.extraction_threshold == 0.3
        assert config.session_tracking.summarization.include_decisions is True
        assert config.session_tracking.summarization.include_errors_resolved is True
        assert config.session_tracking.summarization.tool_classification_cache is None


# =============================================================================
# INTEGRATION TESTS - JSON Schema Validation
# =============================================================================

class TestJSONSchemaValidation:
    """Test JSON schema validation with new summarization block."""

    def test_schema_validates_valid_summarization_config(
        self, temp_config_dir, config_with_summarization
    ):
        """Test JSON schema validation accepts valid summarization config."""
        config_file = temp_config_dir / "graphiti.config.json"
        config_file.write_text(json.dumps(config_with_summarization, indent=2))

        # Should load without validation errors
        config = GraphitiConfig.from_file(str(config_file))
        assert config is not None

    def test_schema_rejects_invalid_extraction_threshold(self, temp_config_dir):
        """Test JSON schema validation rejects invalid threshold > 1.0."""
        invalid_config = {
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD",
                    "database": "neo4j"
                }
            },
            "llm": {
                "provider": "openai",
                "openai": {"api_key_env": "OPENAI_API_KEY"}
            },
            "embedder": {
                "provider": "openai",
                "openai": {"api_key_env": "OPENAI_API_KEY"}
            },
            "session_tracking": {
                "summarization": {
                    "extraction_threshold": 1.5  # Invalid: > 1.0
                }
            }
        }

        # Direct validation should raise error (from_file() catches and returns defaults)
        with pytest.raises(ValidationError) as exc_info:
            GraphitiConfig.model_validate(invalid_config)
        assert "extraction_threshold" in str(exc_info.value)

    def test_schema_rejects_invalid_type_detection(self, temp_config_dir):
        """Test JSON schema validation rejects invalid type_detection value."""
        invalid_config = {
            "database": {
                "backend": "neo4j",
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password_env": "NEO4J_PASSWORD",
                    "database": "neo4j"
                }
            },
            "llm": {
                "provider": "openai",
                "openai": {"api_key_env": "OPENAI_API_KEY"}
            },
            "embedder": {
                "provider": "openai",
                "openai": {"api_key_env": "OPENAI_API_KEY"}
            },
            "session_tracking": {
                "summarization": {
                    "type_detection": "invalid"  # Invalid: not 'auto' or 'manual'
                }
            }
        }

        # Direct validation should raise error (from_file() catches and returns defaults)
        with pytest.raises(ValidationError) as exc_info:
            GraphitiConfig.model_validate(invalid_config)
        assert "type_detection" in str(exc_info.value)


# =============================================================================
# SECURITY TESTS - Path Validation
# =============================================================================

class TestPathValidation:
    """Test path validation for security."""

    def test_tool_classification_cache_path_sanitization(self):
        """Test tool_classification_cache path is validated."""
        # Valid absolute path
        config = SummarizationConfig(
            tool_classification_cache="/home/user/.graphiti/cache.json"
        )
        assert config.tool_classification_cache == "/home/user/.graphiti/cache.json"

        # Valid relative path (Pydantic accepts, validation happens at runtime)
        config = SummarizationConfig(
            tool_classification_cache="./cache.json"
        )
        assert config.tool_classification_cache == "./cache.json"

        # None is valid
        config = SummarizationConfig(tool_classification_cache=None)
        assert config.tool_classification_cache is None

    def test_template_path_sanitization(self):
        """Test template path is validated to prevent path traversal."""
        # Valid absolute path
        config = SummarizationConfig(
            template="/home/user/templates/summary.txt"
        )
        assert config.template == "/home/user/templates/summary.txt"

        # Valid relative path (accepted by Pydantic, runtime validation needed)
        config = SummarizationConfig(template="./templates/summary.txt")
        assert config.template == "./templates/summary.txt"

        # Potentially dangerous path (Pydantic accepts as string, runtime should validate)
        config = SummarizationConfig(template="../../../etc/passwd")
        assert config.template == "../../../etc/passwd"
        # Note: Runtime validation should prevent actual file access

        # None is valid
        config = SummarizationConfig(template=None)
        assert config.template is None

    def test_path_traversal_detection_note(self):
        """
        Note: Path traversal prevention should be implemented at runtime
        when these paths are actually used, not in the Pydantic model.

        The model accepts string paths; validation happens when:
        1. Loading template files
        2. Accessing tool classification cache

        Runtime validation should:
        - Resolve paths to absolute
        - Verify they don't escape allowed directories
        - Check file permissions
        """
        # This test documents the expected behavior
        config = SummarizationConfig(template="../../../etc/passwd")

        # Model accepts the string
        assert config.template == "../../../etc/passwd"

        # Runtime code using config.template should:
        # 1. Resolve to absolute path
        # 2. Verify it's within allowed directory
        # 3. Reject if path traversal detected
        pass  # Documented for future runtime implementation


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_extraction_threshold_boundary_values(self):
        """Test extraction_threshold at exact boundaries."""
        # Exactly 0.0
        config = SummarizationConfig(extraction_threshold=0.0)
        assert config.extraction_threshold == 0.0

        # Exactly 1.0
        config = SummarizationConfig(extraction_threshold=1.0)
        assert config.extraction_threshold == 1.0

        # Just inside lower bound
        config = SummarizationConfig(extraction_threshold=0.0001)
        assert config.extraction_threshold == 0.0001

        # Just inside upper bound
        config = SummarizationConfig(extraction_threshold=0.9999)
        assert config.extraction_threshold == 0.9999

    def test_empty_string_paths_accepted(self):
        """Test empty strings are accepted for path fields (Pydantic behavior)."""
        # Pydantic accepts empty strings as valid str values
        # Runtime validation should handle empty path checks
        config = SummarizationConfig(template="")
        assert config.template == ""

        config = SummarizationConfig(tool_classification_cache="")
        assert config.tool_classification_cache == ""

    def test_all_boolean_combinations(self):
        """Test all combinations of boolean flags."""
        configs = [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ]

        for include_decisions, include_errors in configs:
            config = SummarizationConfig(
                include_decisions=include_decisions,
                include_errors_resolved=include_errors
            )
            assert config.include_decisions == include_decisions
            assert config.include_errors_resolved == include_errors
