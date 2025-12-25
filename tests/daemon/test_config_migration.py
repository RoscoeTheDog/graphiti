"""
Tests for config migration functionality (Story 12).

This test suite verifies the config migration from v2.0 to v2.1.
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server.daemon.installer_migration import (
    migrate_config,
    _create_backup,
    _deep_merge,
    _merge_configs,
    _overwrite_config,
)


class TestConfigMigration:
    """Test suite for config migration (Story 12.t)."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for test configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def v2_0_config(self, temp_config_dir):
        """Create a v2.0 config file."""
        config_dir = temp_config_dir / ".graphiti"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "graphiti.config.json"

        config_data = {
            "neo4j_uri": "neo4j://localhost:7687",
            "neo4j_user": "neo4j",
            "openai_model": "gpt-4",
            "custom_setting": "test_value"
        }

        config_file.write_text(json.dumps(config_data, indent=2))
        return config_file

    @pytest.fixture
    def mock_installer(self, temp_config_dir):
        """Create a mock installer with paths."""
        installer = Mock()
        installer.paths = Mock()
        installer.paths.config_file = temp_config_dir / "config" / "graphiti.config.json"
        return installer

    def test_migrate_config_copies_to_correct_location(
        self, mock_installer, v2_0_config, temp_config_dir
    ):
        """Test: Verify config is copied to correct new location (AC 1)."""
        # Mock v2.0 detection to return our test config
        with patch("mcp_server.daemon.v2_detection.detect_v2_0_installation") as mock_detect:
            mock_detect.return_value = {
                "detected": True,
                "config_file": v2_0_config
            }

            # Run migration
            result = migrate_config(mock_installer, interactive=False, backup=True)

            # Verify migration succeeded
            assert result["migrated"] is True
            assert result["action"] == "copied"
            assert result["destination"] == mock_installer.paths.config_file

            # Verify file exists at new location
            assert mock_installer.paths.config_file.exists()

    def test_migrate_config_preserves_original_as_backup(
        self, mock_installer, v2_0_config, temp_config_dir
    ):
        """Test: Verify original config is preserved as backup (AC 2)."""
        # Read original content
        original_content = v2_0_config.read_text()

        # Mock v2.0 detection
        with patch("mcp_server.daemon.v2_detection.detect_v2_0_installation") as mock_detect:
            mock_detect.return_value = {
                "detected": True,
                "config_file": v2_0_config
            }

            # Run migration
            result = migrate_config(mock_installer, interactive=False, backup=True)

            # Verify backup was created
            assert result["backup_path"] is not None
            assert result["backup_path"].exists()

            # Verify backup contains original content
            backup_content = result["backup_path"].read_text()
            assert backup_content == original_content

            # Verify original file still exists
            assert v2_0_config.exists()
            assert v2_0_config.read_text() == original_content

    def test_migrate_config_preserves_content(
        self, mock_installer, v2_0_config, temp_config_dir
    ):
        """Test: Verify config content is unchanged after migration (AC 3)."""
        # Read original content
        original_content = v2_0_config.read_text()
        original_data = json.loads(original_content)

        # Mock v2.0 detection
        with patch("mcp_server.daemon.v2_detection.detect_v2_0_installation") as mock_detect:
            mock_detect.return_value = {
                "detected": True,
                "config_file": v2_0_config
            }

            # Run migration
            result = migrate_config(mock_installer, interactive=False, backup=True)

            # Verify migration succeeded
            assert result["migrated"] is True

            # Read migrated content
            migrated_content = mock_installer.paths.config_file.read_text()
            migrated_data = json.loads(migrated_content)

            # Verify content matches exactly
            assert migrated_data == original_data

    def test_migrate_config_skips_when_no_v2_0_config(self, mock_installer):
        """Test: Skip migration when no v2.0 config exists."""
        with patch("mcp_server.daemon.v2_detection.detect_v2_0_installation") as mock_detect:
            mock_detect.return_value = {
                "detected": False,
                "config_file": None
            }

            result = migrate_config(mock_installer, interactive=False, backup=True)

            assert result["migrated"] is False
            assert result["action"] == "skipped"
            assert "No v2.0 config file found" in result["errors"]

    def test_create_backup_creates_timestamped_file(self, v2_0_config):
        """Test: Backup creation with timestamp."""
        backup_path = _create_backup(v2_0_config, "v2.0-config")

        # Verify backup exists
        assert backup_path.exists()

        # Verify backup name contains timestamp pattern
        assert "backup-v2.0-config-" in backup_path.name

        # Verify backup contains same content
        assert backup_path.read_text() == v2_0_config.read_text()

    def test_deep_merge_preserves_primary_keys(self):
        """Test: Deep merge with primary taking precedence."""
        primary = {"a": 1, "b": {"x": 10, "y": 20}}
        secondary = {"a": 2, "b": {"x": 30, "z": 40}, "c": 3}

        result = _deep_merge(primary, secondary)

        # Primary keys should win
        assert result["a"] == 1
        assert result["b"]["x"] == 10
        assert result["b"]["y"] == 20

        # Secondary keys should fill gaps
        assert result["b"]["z"] == 40
        assert result["c"] == 3

    def test_migrate_config_handles_conflict_with_force(
        self, mock_installer, v2_0_config, temp_config_dir
    ):
        """Test: Force overwrite when v2.1 config already exists."""
        # Create existing v2.1 config
        mock_installer.paths.config_file.parent.mkdir(parents=True, exist_ok=True)
        v2_1_content = {"neo4j_uri": "neo4j://different:7687"}
        mock_installer.paths.config_file.write_text(json.dumps(v2_1_content))

        # Mock v2.0 detection
        with patch("mcp_server.daemon.v2_detection.detect_v2_0_installation") as mock_detect:
            mock_detect.return_value = {
                "detected": True,
                "config_file": v2_0_config
            }

            # Run migration with force
            result = migrate_config(
                mock_installer,
                interactive=False,
                force_overwrite=True,
                backup=True
            )

            # Verify overwrite succeeded
            assert result["migrated"] is True
            assert result["action"] == "overwritten"

            # Verify content is from v2.0
            migrated_data = json.loads(mock_installer.paths.config_file.read_text())
            original_data = json.loads(v2_0_config.read_text())
            assert migrated_data == original_data


class TestMigrationHelpers:
    """Test helper functions."""

    def test_deep_merge_handles_nested_dicts(self):
        """Test deep merge with multiple nesting levels."""
        primary = {
            "level1": {
                "level2": {
                    "key1": "primary_value",
                    "key2": "primary_value2"
                }
            }
        }
        secondary = {
            "level1": {
                "level2": {
                    "key1": "secondary_value",
                    "key3": "secondary_value3"
                },
                "other_key": "value"
            }
        }

        result = _deep_merge(primary, secondary)

        assert result["level1"]["level2"]["key1"] == "primary_value"
        assert result["level1"]["level2"]["key2"] == "primary_value2"
        assert result["level1"]["level2"]["key3"] == "secondary_value3"
        assert result["level1"]["other_key"] == "value"

    def test_deep_merge_handles_non_dict_values(self):
        """Test deep merge with lists and primitives."""
        primary = {"list": [1, 2, 3], "string": "primary"}
        secondary = {"list": [4, 5, 6], "string": "secondary", "number": 42}

        result = _deep_merge(primary, secondary)

        # Primary non-dict values should overwrite
        assert result["list"] == [1, 2, 3]
        assert result["string"] == "primary"
        # Secondary should fill gaps
        assert result["number"] == 42
