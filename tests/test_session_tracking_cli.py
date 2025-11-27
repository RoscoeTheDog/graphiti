"""
Tests for Session Tracking CLI

Tests the session tracking configuration management commands:
    - graphiti-mcp session-tracking enable
    - graphiti-mcp session-tracking disable
    - graphiti-mcp session-tracking status
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.session_tracking_cli import (
    find_config_file,
    ensure_global_config,
    load_config,
    save_config,
    cmd_enable,
    cmd_disable,
    cmd_status,
)


class TestConfigDiscovery:
    """Test configuration file discovery and creation"""

    def test_find_config_file_project_first(self, tmp_path, monkeypatch):
        """Project config takes precedence over global"""
        monkeypatch.chdir(tmp_path)

        # Create both project and global configs
        project_config = tmp_path / "graphiti.config.json"
        project_config.write_text("{}")

        global_config_dir = tmp_path / ".graphiti"
        global_config_dir.mkdir()
        global_config = global_config_dir / "graphiti.config.json"
        global_config.write_text("{}")

        # Mock home directory
        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            result = find_config_file()

        # result is relative Path("graphiti.config.json"), resolve to compare
        assert result.resolve() == project_config.resolve()

    def test_find_config_file_global_fallback(self, tmp_path, monkeypatch):
        """Global config used when no project config exists"""
        # Change to temp directory without project config to isolate from project root
        monkeypatch.chdir(tmp_path)

        global_config_dir = tmp_path / ".graphiti"
        global_config_dir.mkdir()
        global_config = global_config_dir / "graphiti.config.json"
        global_config.write_text("{}")

        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            result = find_config_file()

        assert result == global_config

    def test_find_config_file_none_when_missing(self, tmp_path, monkeypatch):
        """Returns None when no config file exists"""
        # Change to temp directory to isolate from project root's graphiti.config.json
        monkeypatch.chdir(tmp_path)

        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            result = find_config_file()

        assert result is None

    def test_ensure_global_config_creates_directory(self, tmp_path):
        """Ensure global config creates ~/.graphiti/ if missing"""
        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            result = ensure_global_config()

        assert result.parent.exists()
        assert result.parent == tmp_path / ".graphiti"

    def test_ensure_global_config_creates_minimal_config(self, tmp_path):
        """Ensure global config creates minimal JSON if file missing"""
        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            result = ensure_global_config()

        assert result.exists()
        config = json.loads(result.read_text())
        assert "version" in config
        assert "session_tracking" in config
        assert config["session_tracking"]["enabled"] is False

    def test_ensure_global_config_preserves_existing(self, tmp_path):
        """Ensure global config doesn't overwrite existing file"""
        global_config_dir = tmp_path / ".graphiti"
        global_config_dir.mkdir()
        global_config = global_config_dir / "graphiti.config.json"
        existing_content = {"custom": "value"}
        global_config.write_text(json.dumps(existing_content))

        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            result = ensure_global_config()

        config = json.loads(result.read_text())
        assert config == existing_content


class TestConfigIO:
    """Test configuration loading and saving"""

    def test_load_config_success(self, tmp_path):
        """Load valid JSON config"""
        config_file = tmp_path / "test.json"
        test_config = {"test": "value"}
        config_file.write_text(json.dumps(test_config))

        result = load_config(config_file)

        assert result == test_config

    def test_load_config_invalid_json(self, tmp_path, capsys):
        """Load invalid JSON raises error and exits"""
        config_file = tmp_path / "test.json"
        config_file.write_text("not valid json {")

        with pytest.raises(SystemExit):
            load_config(config_file)

        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.out

    def test_save_config_success(self, tmp_path, capsys):
        """Save config to JSON file"""
        config_file = tmp_path / "test.json"
        test_config = {"test": "value"}

        save_config(config_file, test_config)

        captured = capsys.readouterr()
        assert "Configuration saved" in captured.out
        assert json.loads(config_file.read_text()) == test_config


class TestEnableCommand:
    """Test session-tracking enable command"""

    def test_enable_creates_global_config_if_missing(self, tmp_path, capsys, monkeypatch):
        """Enable creates global config when no config exists"""
        from argparse import Namespace

        # Create empty subdirectory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Mock home directory to tmp_path
        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            # Mock cwd to empty directory (no project config)
            monkeypatch.chdir(empty_dir)

            args = Namespace()
            cmd_enable(args)

        global_config = tmp_path / ".graphiti" / "graphiti.config.json"
        assert global_config.exists()

        config = json.loads(global_config.read_text())
        assert config["session_tracking"]["enabled"] is True

        captured = capsys.readouterr()
        assert "enabled" in captured.out.lower()

    def test_enable_updates_existing_config(self, tmp_path, capsys, monkeypatch):
        """Enable updates existing config file"""
        from argparse import Namespace

        monkeypatch.chdir(tmp_path)

        # Create project config
        config_file = tmp_path / "graphiti.config.json"
        initial_config = {
            "version": "1.0.0",
            "session_tracking": {
                "enabled": False,
                "watch_path": "/custom/path"
            }
        }
        config_file.write_text(json.dumps(initial_config, indent=2))

        args = Namespace()
        cmd_enable(args)

        config = json.loads(config_file.read_text())
        assert config["session_tracking"]["enabled"] is True
        assert config["session_tracking"]["watch_path"] == "/custom/path"  # preserved

        captured = capsys.readouterr()
        assert "enabled" in captured.out.lower()

    def test_enable_creates_session_tracking_section(self, tmp_path, capsys, monkeypatch):
        """Enable creates session_tracking section if missing"""
        from argparse import Namespace

        monkeypatch.chdir(tmp_path)

        # Create config without session_tracking section
        config_file = tmp_path / "graphiti.config.json"
        initial_config = {"version": "1.0.0"}
        config_file.write_text(json.dumps(initial_config))

        args = Namespace()
        cmd_enable(args)

        config = json.loads(config_file.read_text())
        assert "session_tracking" in config
        assert config["session_tracking"]["enabled"] is True


class TestDisableCommand:
    """Test session-tracking disable command"""

    def test_disable_updates_config(self, tmp_path, capsys, monkeypatch):
        """Disable sets enabled=false in config"""
        from argparse import Namespace

        monkeypatch.chdir(tmp_path)

        # Create project config
        config_file = tmp_path / "graphiti.config.json"
        initial_config = {
            "session_tracking": {
                "enabled": True,
                "watch_path": "/custom/path"
            }
        }
        config_file.write_text(json.dumps(initial_config))

        args = Namespace()
        cmd_disable(args)

        config = json.loads(config_file.read_text())
        assert config["session_tracking"]["enabled"] is False
        assert config["session_tracking"]["watch_path"] == "/custom/path"  # preserved

        captured = capsys.readouterr()
        assert "disabled" in captured.out.lower()

    def test_disable_no_config_shows_warning(self, tmp_path, capsys, monkeypatch):
        """Disable shows warning when no config exists"""
        from argparse import Namespace

        # Change to temp directory to isolate from project root's graphiti.config.json
        monkeypatch.chdir(tmp_path)

        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            args = Namespace()
            cmd_disable(args)

        captured = capsys.readouterr()
        assert "No config file found" in captured.out
        assert "already disabled" in captured.out


class TestStatusCommand:
    """Test session-tracking status command"""

    def test_status_no_config(self, tmp_path, capsys, monkeypatch):
        """Status shows default disabled when no config exists"""
        from argparse import Namespace

        # Change to temp directory to isolate from project root's graphiti.config.json
        monkeypatch.chdir(tmp_path)

        with patch("mcp_server.session_tracking_cli.Path.home", return_value=tmp_path):
            args = Namespace()
            cmd_status(args)

        captured = capsys.readouterr()
        assert "Not found" in captured.out
        assert "Disabled" in captured.out

    def test_status_shows_enabled_config(self, tmp_path, capsys, monkeypatch):
        """Status displays enabled config details"""
        from argparse import Namespace

        monkeypatch.chdir(tmp_path)

        # Create config with session tracking enabled
        config_file = tmp_path / "graphiti.config.json"
        config = {
            "session_tracking": {
                "enabled": True,
                "watch_path": "/custom/path",
                "inactivity_timeout": 600,
                "check_interval": 120,
                "auto_summarize": False,
                "store_in_graph": True,
                "filter": {
                    "tool_calls": True,
                    "tool_content": "summary",
                    "user_messages": "full",
                    "agent_messages": "omit"
                }
            }
        }
        config_file.write_text(json.dumps(config))

        args = Namespace()
        cmd_status(args)

        captured = capsys.readouterr()
        assert "Enabled" in captured.out
        assert "/custom/path" in captured.out
        assert "600s" in captured.out
        assert "120s" in captured.out
        assert "False" in captured.out  # auto_summarize
        assert "True" in captured.out   # store_in_graph

    def test_status_shows_disabled_config(self, tmp_path, capsys, monkeypatch):
        """Status shows disabled state with enable instructions"""
        from argparse import Namespace

        monkeypatch.chdir(tmp_path)

        # Create config with session tracking disabled
        config_file = tmp_path / "graphiti.config.json"
        config = {"session_tracking": {"enabled": False}}
        config_file.write_text(json.dumps(config))

        args = Namespace()
        cmd_status(args)

        captured = capsys.readouterr()
        assert "Disabled" in captured.out
        assert "enable session tracking" in captured.out.lower()
