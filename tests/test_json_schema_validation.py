"""
Unit tests for JSON Schema validation of graphiti.config.json.

Story 2.t: Testing - JSON Schema and Config File Updates

Test Requirements:
- Unit: Schema loads without JSON parse errors
- Unit: graphiti.config.json validates against schema
- Unit: trusted_namespaces pattern rejects invalid format (non-hex)
- Unit: trusted_namespaces pattern accepts valid hex hashes
- Integration: Load GraphitiConfig from updated graphiti.config.json
- Integration: Verify all new fields have expected default values
- Integration: Config with trusted_namespaces=['a1b2c3d4'] loads correctly
- Integration: Config with trusted_namespaces=['invalid!'] raises validation error
"""

import json
import pytest
from pathlib import Path

import jsonschema
from jsonschema import Draft7Validator, ValidationError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def project_root():
    """Get the project root directory."""
    # Navigate from tests/ to project root
    current_file = Path(__file__).resolve()
    return current_file.parent.parent


@pytest.fixture
def schema_path(project_root):
    """Get path to the JSON schema file."""
    return project_root / "graphiti.config.schema.json"


@pytest.fixture
def config_path(project_root):
    """Get path to the config file."""
    return project_root / "graphiti.config.json"


@pytest.fixture
def schema(schema_path):
    """Load the JSON schema."""
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def config(config_path):
    """Load the config file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def validator(schema):
    """Create a JSON Schema validator."""
    return Draft7Validator(schema)


# =============================================================================
# UNIT TESTS - Schema Loading
# =============================================================================

class TestSchemaLoading:
    """Test that the JSON schema file is valid and loadable."""

    def test_schema_file_exists(self, schema_path):
        """Test that graphiti.config.schema.json exists."""
        assert schema_path.exists(), f"Schema file not found at {schema_path}"

    def test_schema_is_valid_json(self, schema_path):
        """Test that schema file contains valid JSON."""
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            assert isinstance(schema, dict), "Schema should be a JSON object"
        except json.JSONDecodeError as e:
            pytest.fail(f"Schema file contains invalid JSON: {e}")

    def test_schema_is_valid_json_schema(self, schema):
        """Test that schema is a valid JSON Schema document."""
        try:
            Draft7Validator.check_schema(schema)
        except jsonschema.exceptions.SchemaError as e:
            pytest.fail(f"Invalid JSON Schema: {e}")

    def test_schema_has_required_structure(self, schema):
        """Test that schema has required top-level structure."""
        assert "$defs" in schema, "Schema should have $defs section"
        assert "properties" in schema, "Schema should have properties section"
        assert "description" in schema, "Schema should have description"
        assert "title" in schema, "Schema should have title"

    def test_schema_has_session_tracking_def(self, schema):
        """Test that SessionTrackingConfig is defined in schema."""
        assert "SessionTrackingConfig" in schema["$defs"], \
            "SessionTrackingConfig should be defined in $defs"

    def test_schema_has_filter_config_def(self, schema):
        """Test that FilterConfig is defined in schema (Story 2 requirement)."""
        assert "FilterConfig" in schema["$defs"], \
            "FilterConfig should be defined in $defs"

    def test_schema_has_retry_queue_config_def(self, schema):
        """Test that RetryQueueConfig is defined in schema (Story 2 requirement)."""
        assert "RetryQueueConfig" in schema["$defs"], \
            "RetryQueueConfig should be defined in $defs"

    def test_schema_has_session_resilience_config_def(self, schema):
        """Test that SessionTrackingResilienceConfig is defined in schema."""
        assert "SessionTrackingResilienceConfig" in schema["$defs"], \
            "SessionTrackingResilienceConfig should be defined in $defs"


# =============================================================================
# UNIT TESTS - Config File Validation
# =============================================================================

class TestConfigValidation:
    """Test that graphiti.config.json validates against the schema."""

    def test_config_file_exists(self, config_path):
        """Test that graphiti.config.json exists."""
        assert config_path.exists(), f"Config file not found at {config_path}"

    def test_config_is_valid_json(self, config_path):
        """Test that config file contains valid JSON."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            assert isinstance(config, dict), "Config should be a JSON object"
        except json.JSONDecodeError as e:
            pytest.fail(f"Config file contains invalid JSON: {e}")

    def test_config_validates_against_schema(self, validator, config):
        """Test that config validates against schema (AC-2.4)."""
        errors = list(validator.iter_errors(config))
        if errors:
            error_messages = [f"  - {e.json_path}: {e.message}" for e in errors]
            pytest.fail(
                f"Config validation failed with {len(errors)} errors:\n"
                + "\n".join(error_messages)
            )

    def test_config_has_session_tracking_section(self, config):
        """Test that config has session_tracking section."""
        assert "session_tracking" in config, \
            "Config should have session_tracking section"

    def test_config_session_tracking_has_new_fields(self, config):
        """Test that session_tracking has all new Story 2 fields."""
        session_tracking = config.get("session_tracking", {})

        required_fields = [
            "group_id",
            "cross_project_search",
            "trusted_namespaces",
            "include_project_path"
        ]

        for field in required_fields:
            assert field in session_tracking, \
                f"session_tracking should have '{field}' field"


# =============================================================================
# UNIT TESTS - trusted_namespaces Pattern Validation
# =============================================================================

class TestTrustedNamespacesPattern:
    """Test trusted_namespaces pattern validation (hex format)."""

    @pytest.fixture
    def session_tracking_schema(self, schema):
        """Extract SessionTrackingConfig schema."""
        return schema["$defs"]["SessionTrackingConfig"]

    def test_trusted_namespaces_accepts_valid_hex_lowercase(self, validator):
        """Test that trusted_namespaces accepts lowercase hex hashes."""
        config = {
            "session_tracking": {
                "trusted_namespaces": ["a1b2c3d4", "abcdef01"]
            }
        }
        errors = list(validator.iter_errors(config))
        assert len(errors) == 0, f"Valid lowercase hex rejected: {errors}"

    def test_trusted_namespaces_accepts_valid_hex_uppercase(self, validator):
        """Test that trusted_namespaces accepts uppercase hex hashes."""
        config = {
            "session_tracking": {
                "trusted_namespaces": ["A1B2C3D4", "ABCDEF01"]
            }
        }
        errors = list(validator.iter_errors(config))
        assert len(errors) == 0, f"Valid uppercase hex rejected: {errors}"

    def test_trusted_namespaces_accepts_valid_hex_mixed_case(self, validator):
        """Test that trusted_namespaces accepts mixed case hex hashes."""
        config = {
            "session_tracking": {
                "trusted_namespaces": ["A1b2C3d4", "AbCdEf01"]
            }
        }
        errors = list(validator.iter_errors(config))
        assert len(errors) == 0, f"Valid mixed case hex rejected: {errors}"

    def test_trusted_namespaces_accepts_long_hex_hashes(self, validator):
        """Test that trusted_namespaces accepts long hex strings."""
        config = {
            "session_tracking": {
                "trusted_namespaces": [
                    "abcdef0123456789",
                    "0123456789abcdef0123456789abcdef"
                ]
            }
        }
        errors = list(validator.iter_errors(config))
        assert len(errors) == 0, f"Valid long hex rejected: {errors}"

    def test_trusted_namespaces_accepts_null(self, validator):
        """Test that trusted_namespaces accepts null value."""
        config = {
            "session_tracking": {
                "trusted_namespaces": None
            }
        }
        errors = list(validator.iter_errors(config))
        assert len(errors) == 0, f"Null value rejected: {errors}"

    def test_trusted_namespaces_accepts_empty_array(self, validator):
        """Test that trusted_namespaces accepts empty array."""
        config = {
            "session_tracking": {
                "trusted_namespaces": []
            }
        }
        errors = list(validator.iter_errors(config))
        assert len(errors) == 0, f"Empty array rejected: {errors}"

    def test_trusted_namespaces_rejects_non_hex_characters(self, validator):
        """Test that trusted_namespaces rejects non-hex characters."""
        invalid_values = [
            ["ghijk"],         # g-z are not hex
            ["invalid!"],     # special characters
            ["namespace_1"],  # underscore
            ["name-space"],   # dash
            ["name space"],   # space
        ]

        for invalid_namespace in invalid_values:
            config = {
                "session_tracking": {
                    "trusted_namespaces": invalid_namespace
                }
            }
            errors = list(validator.iter_errors(config))
            assert len(errors) > 0, \
                f"Invalid namespace '{invalid_namespace[0]}' was not rejected"

    def test_trusted_namespaces_rejects_non_string_items(self, validator):
        """Test that trusted_namespaces rejects non-string array items."""
        config = {
            "session_tracking": {
                "trusted_namespaces": [12345]
            }
        }
        errors = list(validator.iter_errors(config))
        assert len(errors) > 0, "Integer array item was not rejected"

    def test_trusted_namespaces_rejects_object_items(self, validator):
        """Test that trusted_namespaces rejects object array items."""
        config = {
            "session_tracking": {
                "trusted_namespaces": [{"hash": "a1b2c3d4"}]
            }
        }
        errors = list(validator.iter_errors(config))
        assert len(errors) > 0, "Object array item was not rejected"


# =============================================================================
# UNIT TESTS - New Schema Fields (AC-2.1, AC-2.2)
# =============================================================================

class TestNewSchemaFields:
    """Test that new Story 2 fields are properly defined in schema."""

    def test_group_id_field_definition(self, schema):
        """Test group_id field is properly defined."""
        props = schema["$defs"]["SessionTrackingConfig"]["properties"]
        assert "group_id" in props, "group_id should be in schema"

        group_id = props["group_id"]
        # Should allow string or null
        assert "anyOf" in group_id, "group_id should allow multiple types"
        types = [t.get("type") for t in group_id["anyOf"]]
        assert "string" in types, "group_id should allow string"
        assert "null" in types, "group_id should allow null"
        # Should have description
        assert "description" in group_id, "group_id should have description"
        assert len(group_id["description"]) > 20, "group_id description too short"

    def test_cross_project_search_field_definition(self, schema):
        """Test cross_project_search field is properly defined."""
        props = schema["$defs"]["SessionTrackingConfig"]["properties"]
        assert "cross_project_search" in props, \
            "cross_project_search should be in schema"

        field = props["cross_project_search"]
        assert field.get("type") == "boolean", \
            "cross_project_search should be boolean"
        assert field.get("default") is True, \
            "cross_project_search should default to true"
        assert "description" in field, \
            "cross_project_search should have description"

    def test_trusted_namespaces_field_definition(self, schema):
        """Test trusted_namespaces field is properly defined."""
        props = schema["$defs"]["SessionTrackingConfig"]["properties"]
        assert "trusted_namespaces" in props, \
            "trusted_namespaces should be in schema"

        field = props["trusted_namespaces"]
        # Should allow array or null
        assert "anyOf" in field, "trusted_namespaces should allow multiple types"
        # Check for array with pattern validation
        array_def = None
        for type_def in field["anyOf"]:
            if type_def.get("type") == "array":
                array_def = type_def
                break
        assert array_def is not None, "trusted_namespaces should allow array type"
        assert "items" in array_def, "trusted_namespaces array should have items"
        assert "pattern" in array_def["items"], \
            "trusted_namespaces items should have pattern"
        assert "description" in field, \
            "trusted_namespaces should have description"

    def test_include_project_path_field_definition(self, schema):
        """Test include_project_path field is properly defined."""
        props = schema["$defs"]["SessionTrackingConfig"]["properties"]
        assert "include_project_path" in props, \
            "include_project_path should be in schema"

        field = props["include_project_path"]
        assert field.get("type") == "boolean", \
            "include_project_path should be boolean"
        assert field.get("default") is True, \
            "include_project_path should default to true"
        assert "description" in field, \
            "include_project_path should have description"


# =============================================================================
# INTEGRATION TESTS - GraphitiConfig Loading
# =============================================================================

class TestGraphitiConfigIntegration:
    """Integration tests for loading config with new fields."""

    def test_load_graphiti_config_from_file(self, config_path):
        """Test loading GraphitiConfig from updated graphiti.config.json."""
        from mcp_server.unified_config import GraphitiConfig

        # Load config using the actual config file
        config = GraphitiConfig.from_file(config_path)
        assert config is not None, "Config should load successfully"

    def test_session_tracking_default_values(self):
        """Test SessionTrackingConfig has expected default values."""
        from mcp_server.unified_config import SessionTrackingConfig

        config = SessionTrackingConfig()

        # Verify Story 2 field defaults
        assert config.group_id is None, "group_id should default to None"
        assert config.cross_project_search is True, \
            "cross_project_search should default to True"
        assert config.trusted_namespaces is None, \
            "trusted_namespaces should default to None"
        assert config.include_project_path is True, \
            "include_project_path should default to True"

    def test_config_with_valid_trusted_namespaces(self):
        """Test config with trusted_namespaces=['a1b2c3d4'] loads correctly."""
        from mcp_server.unified_config import SessionTrackingConfig

        config = SessionTrackingConfig(
            trusted_namespaces=["a1b2c3d4", "e5f6a7b8"]
        )

        assert config.trusted_namespaces == ["a1b2c3d4", "e5f6a7b8"]

    def test_config_with_invalid_trusted_namespaces_raises(self):
        """Test config with trusted_namespaces=['invalid!'] raises error."""
        from mcp_server.unified_config import SessionTrackingConfig

        with pytest.raises(ValueError) as excinfo:
            SessionTrackingConfig(trusted_namespaces=["invalid!"])

        assert "invalid" in str(excinfo.value).lower() or \
               "hex" in str(excinfo.value).lower() or \
               "format" in str(excinfo.value).lower()

    def test_config_all_new_fields_combined(self):
        """Test SessionTrackingConfig with all new fields set."""
        from mcp_server.unified_config import SessionTrackingConfig

        config = SessionTrackingConfig(
            enabled=True,
            group_id="custom_group_id",
            cross_project_search=False,
            trusted_namespaces=["a1b2c3d4", "e5f6a7b8"],
            include_project_path=False
        )

        assert config.group_id == "custom_group_id"
        assert config.cross_project_search is False
        assert config.trusted_namespaces == ["a1b2c3d4", "e5f6a7b8"]
        assert config.include_project_path is False

    def test_actual_config_file_loads_with_graphiti_config(self, config_path):
        """Test that actual graphiti.config.json loads via GraphitiConfig."""
        from mcp_server.unified_config import GraphitiConfig

        config = GraphitiConfig.from_file(config_path)

        # Verify session_tracking has expected values from file
        st = config.session_tracking

        # These should match values in graphiti.config.json
        assert st.group_id is None, "group_id should be null from file"
        assert st.cross_project_search is True, \
            "cross_project_search should be true from file"
        assert st.trusted_namespaces is None, \
            "trusted_namespaces should be null from file"
        assert st.include_project_path is True, \
            "include_project_path should be true from file"


# =============================================================================
# UNIT TESTS - Field Descriptions Match Pydantic (AC-2.2)
# =============================================================================

class TestFieldDescriptionsMatch:
    """Test that JSON schema descriptions match Pydantic model docstrings."""

    @pytest.fixture
    def pydantic_field_descriptions(self):
        """Get field descriptions from Pydantic model."""
        from mcp_server.unified_config import SessionTrackingConfig

        fields = SessionTrackingConfig.model_fields
        return {
            name: field.description
            for name, field in fields.items()
            if field.description
        }

    @pytest.fixture
    def schema_field_descriptions(self, schema):
        """Get field descriptions from JSON schema."""
        props = schema["$defs"]["SessionTrackingConfig"]["properties"]
        return {
            name: prop.get("description", "")
            for name, prop in props.items()
        }

    def test_group_id_description_matches(
        self, pydantic_field_descriptions, schema_field_descriptions
    ):
        """Test group_id description matches between schema and Pydantic."""
        assert "group_id" in pydantic_field_descriptions
        assert "group_id" in schema_field_descriptions
        # Descriptions should be substantively similar
        pydantic_desc = pydantic_field_descriptions["group_id"].lower()
        schema_desc = schema_field_descriptions["group_id"].lower()
        assert "group" in schema_desc, "Schema description should mention 'group'"
        assert "session" in schema_desc or "index" in schema_desc, \
            "Schema description should mention sessions or indexing"

    def test_cross_project_search_description_matches(
        self, pydantic_field_descriptions, schema_field_descriptions
    ):
        """Test cross_project_search description matches."""
        assert "cross_project_search" in pydantic_field_descriptions
        assert "cross_project_search" in schema_field_descriptions
        schema_desc = schema_field_descriptions["cross_project_search"].lower()
        assert "search" in schema_desc, "Description should mention search"
        assert "project" in schema_desc, "Description should mention project"

    def test_trusted_namespaces_description_matches(
        self, pydantic_field_descriptions, schema_field_descriptions
    ):
        """Test trusted_namespaces description matches."""
        assert "trusted_namespaces" in pydantic_field_descriptions
        assert "trusted_namespaces" in schema_field_descriptions
        schema_desc = schema_field_descriptions["trusted_namespaces"].lower()
        assert "namespace" in schema_desc, "Description should mention namespace"
        assert "hex" in schema_desc or "hash" in schema_desc, \
            "Description should mention hex or hash format"

    def test_include_project_path_description_matches(
        self, pydantic_field_descriptions, schema_field_descriptions
    ):
        """Test include_project_path description matches."""
        assert "include_project_path" in pydantic_field_descriptions
        assert "include_project_path" in schema_field_descriptions
        schema_desc = schema_field_descriptions["include_project_path"].lower()
        assert "path" in schema_desc, "Description should mention path"
        assert "project" in schema_desc or "metadata" in schema_desc, \
            "Description should mention project or metadata"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
