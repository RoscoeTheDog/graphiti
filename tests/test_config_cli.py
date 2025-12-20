"""
Tests for Configuration CLI (config_cli.py)

Tests for:
- Command-line argument parsing
- Config file discovery and loading
- Effective config computation
- Output formatting (human, diff, JSON)
- Color/TTY detection
- Error handling
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.config_cli import (
    Colors,
    _compare_configs,
    _delete_nested_value,
    _ensure_global_config,
    _format_config_diff,
    _format_config_human,
    _format_config_json,
    _format_section,
    _format_value,
    _get_nested_value,
    _is_empty_nested_dict,
    _load_config_dict,
    _parse_value,
    _save_config_dict,
    _set_nested_value,
    _validate_key_path,
    cmd_effective,
    cmd_list_projects,
    cmd_remove_override,
    cmd_set_override,
    colorize,
    find_config_file,
    is_tty,
    mask_sensitive,
)
from mcp_server.unified_config import GraphitiConfig, normalize_project_path


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary config directory for testing"""
    config_dir = tmp_path / ".graphiti"
    config_dir.mkdir(parents=True, exist_ok=True)
    yield config_dir


@pytest.fixture
def minimal_config_dict() -> dict:
    """Minimal valid configuration dictionary"""
    return {
        "version": "1.0.0",
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
            "default_model": "gpt-4.1-mini",
            "small_model": "gpt-4.1-nano",
            "temperature": 0.0
        },
        "embedder": {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "dimensions": 1536
        }
    }


@pytest.fixture
def config_with_override(minimal_config_dict: dict, tmp_path: Path) -> dict:
    """Config with a project override"""
    config = minimal_config_dict.copy()
    project_path = str(tmp_path / "myproject")
    # Normalize path to match what get_effective_config expects
    normalized_path = normalize_project_path(project_path)

    config["project_overrides"] = {
        normalized_path: {
            "llm": {
                "provider": "anthropic",
                "default_model": "claude-3-5-sonnet-20241022"
            }
        }
    }

    return config


# ============================================================================
# Test Utilities
# ============================================================================


def test_is_tty_detection(monkeypatch):
    """Test TTY detection for color support"""
    # Mock TTY
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    assert is_tty() is True

    # Mock non-TTY
    mock_stdout.isatty.return_value = False
    assert is_tty() is False


def test_colorize_with_tty(monkeypatch):
    """Test colorize applies colors when TTY"""
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    result = colorize("test", Colors.GREEN)
    assert Colors.GREEN in result
    assert Colors.RESET in result
    assert "test" in result


def test_colorize_without_tty(monkeypatch):
    """Test colorize returns plain text when not TTY"""
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = False
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    result = colorize("test", Colors.GREEN)
    assert Colors.GREEN not in result
    assert Colors.RESET not in result
    assert result == "test"


def test_mask_sensitive():
    """Test sensitive value masking"""
    # Should mask API keys
    assert mask_sensitive("api_key", "sk-1234567890") == "***REDACTED***"
    assert mask_sensitive("openai_api_key", "sk-test") == "***REDACTED***"

    # Should mask passwords
    assert mask_sensitive("password", "secret123") == "***REDACTED***"
    assert mask_sensitive("neo4j_password", "pass") == "***REDACTED***"

    # Should mask tokens
    assert mask_sensitive("auth_token", "token123") == "***REDACTED***"

    # Should not mask non-sensitive values
    assert mask_sensitive("model", "gpt-4") == "gpt-4"
    assert mask_sensitive("temperature", 0.7) == 0.7

    # Should handle empty strings
    assert mask_sensitive("api_key", "") == ""

    # Should handle non-string values
    assert mask_sensitive("port", 7687) == 7687


def test_get_nested_value():
    """Test nested value retrieval using dot notation"""
    test_dict = {
        "database": {
            "backend": "neo4j",
            "neo4j": {
                "uri": "bolt://localhost:7687"
            }
        }
    }

    assert _get_nested_value(test_dict, "database.backend") == "neo4j"
    assert _get_nested_value(test_dict, "database.neo4j.uri") == "bolt://localhost:7687"
    assert _get_nested_value(test_dict, "nonexistent") is None
    assert _get_nested_value(test_dict, "database.nonexistent.uri") is None


# ============================================================================
# Test Config Discovery
# ============================================================================


def test_find_config_file_project_root(tmp_path: Path, monkeypatch):
    """Test finding config in project root"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text("{}")

    monkeypatch.chdir(tmp_path)

    found = find_config_file()
    assert found is not None
    assert found.name == "graphiti.config.json"


def test_find_config_file_global(tmp_path: Path, monkeypatch):
    """Test finding config in global location"""
    global_config = tmp_path / ".graphiti" / "graphiti.config.json"
    global_config.parent.mkdir(parents=True, exist_ok=True)
    global_config.write_text("{}")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Change to directory without project config
    work_dir = tmp_path / "workspace"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    found = find_config_file()
    assert found is not None
    assert found.name == "graphiti.config.json"
    assert ".graphiti" in str(found)


def test_find_config_file_not_found(tmp_path: Path, monkeypatch):
    """Test when no config file exists"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    found = find_config_file()
    assert found is None


# ============================================================================
# Test Config Comparison
# ============================================================================


def test_compare_configs_no_differences():
    """Test comparing identical configs"""
    config1 = {"llm": {"provider": "openai", "temperature": 0.7}}
    config2 = {"llm": {"provider": "openai", "temperature": 0.7}}

    diffs = _compare_configs(config1, config2)
    assert len(diffs) == 0


def test_compare_configs_with_differences():
    """Test comparing configs with differences"""
    effective = {
        "llm": {
            "provider": "anthropic",
            "temperature": 0.7,
            "default_model": "claude-3-5-sonnet-20241022"
        }
    }
    global_config = {
        "llm": {
            "provider": "openai",
            "temperature": 0.7,
            "default_model": "gpt-4.1-mini"
        }
    }

    diffs = _compare_configs(effective, global_config)

    assert "llm.provider" in diffs
    assert diffs["llm.provider"] == ("openai", "anthropic")
    assert "llm.default_model" in diffs
    assert diffs["llm.default_model"] == ("gpt-4.1-mini", "claude-3-5-sonnet-20241022")
    assert "llm.temperature" not in diffs  # Same value


def test_compare_configs_nested():
    """Test comparing deeply nested configs"""
    effective = {
        "database": {
            "backend": "neo4j",
            "neo4j": {
                "uri": "neo4j+s://example.com",
                "database": "custom"
            }
        }
    }
    global_config = {
        "database": {
            "backend": "neo4j",
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "database": "neo4j"
            }
        }
    }

    diffs = _compare_configs(effective, global_config)

    assert "database.neo4j.uri" in diffs
    assert "database.neo4j.database" in diffs
    assert "database.backend" not in diffs


def test_compare_configs_skips_project_overrides():
    """Test that project_overrides section is skipped"""
    effective = {
        "llm": {"provider": "openai"},
        "project_overrides": {"/path/to/project": {"llm": {"provider": "anthropic"}}}
    }
    global_config = {
        "llm": {"provider": "openai"},
        "project_overrides": {}
    }

    diffs = _compare_configs(effective, global_config)

    # Should not include project_overrides in diffs
    assert not any("project_overrides" in key for key in diffs.keys())


# ============================================================================
# Test Value Formatting
# ============================================================================


def test_format_value_basic():
    """Test basic value formatting"""
    assert "test_key: value" in _format_value("test_key", "value", indent=0)
    assert "test_key: 123" in _format_value("test_key", 123, indent=0)


def test_format_value_boolean():
    """Test boolean formatting (lowercase)"""
    assert "enabled: true" in _format_value("enabled", True, indent=0)
    assert "enabled: false" in _format_value("enabled", False, indent=0)


def test_format_value_list():
    """Test list formatting"""
    assert "models: [gpt-4, gpt-3.5]" in _format_value("models", ["gpt-4", "gpt-3.5"], indent=0)
    assert "empty: []" in _format_value("empty", [], indent=0)


def test_format_value_none():
    """Test None formatting"""
    assert "value: null" in _format_value("value", None, indent=0)


def test_format_value_indent():
    """Test indentation"""
    result = _format_value("key", "value", indent=2)
    assert result.startswith("    ")  # 2 levels = 4 spaces


def test_format_value_masks_sensitive():
    """Test that sensitive values are masked"""
    result = _format_value("api_key", "sk-1234567890", indent=0)
    assert "***REDACTED***" in result
    assert "sk-1234567890" not in result


# ============================================================================
# Test Output Formatting
# ============================================================================


def test_format_config_human(minimal_config_dict: dict):
    """Test human-readable output format"""
    global_config = GraphitiConfig.model_validate(minimal_config_dict)
    effective_config = global_config  # No overrides

    output = _format_config_human(effective_config, global_config, "/test/project")

    assert "Effective Configuration for Project:" in output
    assert "/test/project" in output
    assert "Database:" in output
    assert "LLM:" in output
    assert "Embedder:" in output


def test_format_config_human_with_overrides(config_with_override: dict, tmp_path: Path):
    """Test human-readable output with overrides highlighted"""
    global_config = GraphitiConfig.model_validate(config_with_override)
    project_path = str(tmp_path / "myproject")
    effective_config = global_config.get_effective_config(project_path)

    # Mock non-TTY for consistent output
    with patch("mcp_server.config_cli.is_tty", return_value=False):
        output = _format_config_human(effective_config, global_config, project_path)

    assert "[OVERRIDE]" in output
    assert "anthropic" in output
    assert "claude-3-5-sonnet-20241022" in output


def test_format_config_diff_no_overrides(minimal_config_dict: dict):
    """Test diff format with no overrides"""
    global_config = GraphitiConfig.model_validate(minimal_config_dict)
    effective_config = global_config

    output = _format_config_diff(effective_config, global_config, "/test/project")

    assert "Configuration Overrides for Project:" in output
    assert "No overrides found" in output


def test_format_config_diff_with_overrides(config_with_override: dict, tmp_path: Path):
    """Test diff format showing only overridden values"""
    global_config = GraphitiConfig.model_validate(config_with_override)
    project_path = str(tmp_path / "myproject")
    effective_config = global_config.get_effective_config(project_path)

    # Mock non-TTY for consistent output
    with patch("mcp_server.config_cli.is_tty", return_value=False):
        output = _format_config_diff(effective_config, global_config, project_path)

    assert "Configuration Overrides for Project:" in output
    assert "→" in output  # Diff arrow
    assert "openai → anthropic" in output or "anthropic" in output
    assert "claude-3-5-sonnet-20241022" in output


def test_format_config_json(minimal_config_dict: dict):
    """Test JSON output format"""
    config = GraphitiConfig.model_validate(minimal_config_dict)

    output = _format_config_json(config)

    # Should be valid JSON
    parsed = json.loads(output)
    assert parsed["version"] == "1.0.0"
    assert parsed["llm"]["provider"] == "openai"
    assert parsed["database"]["backend"] == "neo4j"

    # Should not include project_overrides (meta-config)
    assert "project_overrides" not in parsed


def test_format_config_json_with_overrides(config_with_override: dict, tmp_path: Path):
    """Test JSON output includes effective values"""
    global_config = GraphitiConfig.model_validate(config_with_override)
    project_path = str(tmp_path / "myproject")
    effective_config = global_config.get_effective_config(project_path)

    output = _format_config_json(effective_config)

    parsed = json.loads(output)
    assert parsed["llm"]["provider"] == "anthropic"
    assert parsed["llm"]["default_model"] == "claude-3-5-sonnet-20241022"


# ============================================================================
# Test Command Execution
# ============================================================================


def test_cmd_effective_no_config_file(tmp_path: Path, monkeypatch, capsys):
    """Test error when no config file exists"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    args = argparse.Namespace(project=None, diff=False, json=False)

    with pytest.raises(SystemExit) as exc_info:
        cmd_effective(args)

    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "ERROR" in captured.out
    assert "No configuration file found" in captured.out


def test_cmd_effective_uses_cwd_by_default(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """Test that command uses current directory when --project not specified"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(minimal_config_dict))

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=None, diff=False, json=False)

    # Mock TTY to avoid color codes
    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()
    assert "Effective Configuration for Project:" in captured.out
    assert str(tmp_path) in captured.out


def test_cmd_effective_with_project_flag(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """Test --project flag specifies target project"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(minimal_config_dict))

    monkeypatch.chdir(tmp_path)

    project_path = str(tmp_path / "myproject")
    args = argparse.Namespace(project=project_path, diff=False, json=False)

    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()
    assert "myproject" in captured.out


def test_cmd_effective_json_flag(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """Test --json flag outputs valid JSON"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(minimal_config_dict))

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=None, diff=False, json=True)

    cmd_effective(args)

    captured = capsys.readouterr()

    # Should be valid JSON
    parsed = json.loads(captured.out)
    assert parsed["version"] == "1.0.0"
    assert parsed["llm"]["provider"] == "openai"


def test_cmd_effective_diff_flag(tmp_path: Path, monkeypatch, config_with_override: dict, capsys):
    """Test --diff flag shows only overridden values"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config_with_override))

    project_path = str(tmp_path / "myproject")

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=project_path, diff=True, json=False)

    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()
    assert "Configuration Overrides for Project:" in captured.out
    assert "→" in captured.out


def test_cmd_effective_invalid_config(tmp_path: Path, monkeypatch, capsys):
    """Test that invalid config file falls back to defaults (GraphitiConfig behavior)"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text("invalid json{")

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=None, diff=False, json=False)

    # GraphitiConfig.from_file() catches JSON errors and falls back to defaults
    # So this should succeed and show default config
    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()
    # Should show config (defaults) despite invalid JSON
    assert "Effective Configuration for Project:" in captured.out


# ============================================================================
# Test Section Formatting
# ============================================================================


def test_format_section_flat():
    """Test formatting a flat section"""
    section = {"backend": "neo4j", "enabled": True}
    differences = {}

    output = _format_section("Database", section, differences, "database", indent=0)

    assert "Database:" in output
    assert "backend: neo4j" in output
    assert "enabled: true" in output


def test_format_section_nested():
    """Test formatting a nested section"""
    section = {
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "database": "neo4j"
        }
    }
    differences = {}

    output = _format_section("Database", section, differences, "database", indent=0)

    assert "neo4j:" in output
    assert "uri: bolt://localhost:7687" in output
    assert "database: neo4j" in output


def test_format_section_with_overrides():
    """Test formatting section with override highlighting"""
    section = {"provider": "anthropic", "temperature": 0.7}
    differences = {"llm.provider": ("openai", "anthropic")}

    with patch("mcp_server.config_cli.is_tty", return_value=False):
        output = _format_section("LLM", section, differences, "llm", indent=0)

    assert "[OVERRIDE]" in output
    assert "provider: anthropic" in output
    # temperature should not have [OVERRIDE]
    lines = output.split("\n")
    temp_line = [line for line in lines if "temperature" in line][0]
    assert "[OVERRIDE]" not in temp_line


def test_format_section_skips_project_overrides():
    """Test that project_overrides section is skipped"""
    section = {
        "provider": "openai",
        "project_overrides": {"/path": {"provider": "anthropic"}}
    }
    differences = {}

    output = _format_section("Config", section, differences, "config", indent=0)

    # Should not include project_overrides in output
    assert "project_overrides" not in output


# ============================================================================
# Test Integration
# ============================================================================


def test_end_to_end_no_override(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """End-to-end test: no override, shows global config"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(minimal_config_dict))

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=None, diff=False, json=False)

    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()

    # Should show config but no overrides
    assert "Effective Configuration for Project:" in captured.out
    assert "openai" in captured.out
    assert "[OVERRIDE]" not in captured.out


def test_end_to_end_with_override(tmp_path: Path, monkeypatch, config_with_override: dict, capsys):
    """End-to-end test: with override, shows merged config"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config_with_override))

    project_path = str(tmp_path / "myproject")

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=project_path, diff=False, json=False)

    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()

    # Should show overridden values
    assert "Effective Configuration for Project:" in captured.out
    assert "[OVERRIDE]" in captured.out
    assert "anthropic" in captured.out


def test_end_to_end_diff_mode(tmp_path: Path, monkeypatch, config_with_override: dict, capsys):
    """End-to-end test: diff mode shows only overrides"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config_with_override))

    project_path = str(tmp_path / "myproject")

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=project_path, diff=True, json=False)

    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()

    # Should show diff format
    assert "Configuration Overrides for Project:" in captured.out
    assert "→" in captured.out


def test_end_to_end_json_mode(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """End-to-end test: JSON mode outputs parseable JSON"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(minimal_config_dict))

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=None, diff=False, json=True)

    cmd_effective(args)

    captured = capsys.readouterr()

    # Should be valid, parseable JSON
    parsed = json.loads(captured.out)
    assert parsed["version"] == "1.0.0"


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_handles_relative_path(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """Test that relative paths are resolved correctly"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(minimal_config_dict))

    monkeypatch.chdir(tmp_path)

    # Use relative path
    args = argparse.Namespace(project="./subdir", diff=False, json=False)

    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()

    # Should resolve to absolute path
    assert "subdir" in captured.out
    assert "Effective Configuration for Project:" in captured.out


def test_handles_empty_override(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """Test that empty override (all None) shows global config"""
    config = minimal_config_dict.copy()
    project_path = str(tmp_path / "project")

    # Override with all None values (should inherit everything)
    config["project_overrides"] = {
        project_path: {}
    }

    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config))

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=project_path, diff=False, json=False)

    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()

    # Should show no overrides
    assert "Effective Configuration for Project:" in captured.out
    assert "[OVERRIDE]" not in captured.out


def test_colored_output_in_tty(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """Test that colored output uses ANSI codes in TTY"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(minimal_config_dict))

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=None, diff=False, json=False)

    # Mock TTY
    with patch("mcp_server.config_cli.is_tty", return_value=True):
        cmd_effective(args)

    captured = capsys.readouterr()

    # Should contain ANSI codes
    assert "\033[" in captured.out  # ANSI escape sequence


def test_no_color_in_non_tty(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """Test that non-TTY output has no ANSI codes"""
    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(minimal_config_dict))

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace(project=None, diff=False, json=False)

    # Mock non-TTY
    with patch("mcp_server.config_cli.is_tty", return_value=False):
        cmd_effective(args)

    captured = capsys.readouterr()

    # Should not contain ANSI codes
    assert "\033[" not in captured.out


# ============================================================================
# Test Helper Functions (Story 4)
# ============================================================================


def test_validate_key_path_valid_llm():
    """Test validation of valid llm key paths"""
    is_valid, error = _validate_key_path("llm.provider")
    assert is_valid is True
    assert error == ""

    is_valid, error = _validate_key_path("llm.default_model")
    assert is_valid is True
    assert error == ""

    is_valid, error = _validate_key_path("llm.openai.api_key_env")
    assert is_valid is True
    assert error == ""

def test_validate_key_path_valid_embedder():
    """Test validation of valid embedder key paths"""
    is_valid, error = _validate_key_path("embedder.provider")
    assert is_valid is True
    assert error == ""

    is_valid, error = _validate_key_path("embedder.model")
    assert is_valid is True


def test_validate_key_path_valid_extraction():
    """Test validation of valid extraction key paths"""
    is_valid, error = _validate_key_path("extraction.max_reflexion_iterations")
    assert is_valid is True


def test_validate_key_path_valid_session_tracking():
    """Test validation of valid session_tracking key paths"""
    is_valid, error = _validate_key_path("session_tracking.enabled")
    assert is_valid is True

    is_valid, error = _validate_key_path("session_tracking.filter.tool_calls")
    assert is_valid is True


def test_validate_key_path_invalid_database():
    """Test validation rejects database section"""
    is_valid, error = _validate_key_path("database.backend")
    assert is_valid is False
    assert "database" in error.lower()
    assert "not overridable" in error.lower()


def test_validate_key_path_invalid_daemon():
    """Test validation rejects daemon section"""
    is_valid, error = _validate_key_path("daemon.enabled")
    assert is_valid is False
    assert "daemon" in error.lower()


def test_validate_key_path_invalid_resilience():
    """Test validation rejects resilience section"""
    is_valid, error = _validate_key_path("resilience.auto_reconnect")
    assert is_valid is False
    assert "resilience" in error.lower()


def test_validate_key_path_empty():
    """Test validation rejects empty key path"""
    is_valid, error = _validate_key_path("")
    assert is_valid is False
    assert "empty" in error.lower()


def test_set_nested_value_simple():
    """Test setting simple nested value"""
    obj = {}
    _set_nested_value(obj, "llm.provider", "anthropic")
    assert obj == {"llm": {"provider": "anthropic"}}


def test_set_nested_value_deep():
    """Test setting deeply nested value"""
    obj = {}
    _set_nested_value(obj, "llm.openai.api_key_env", "OPENAI_API_KEY")
    assert obj == {"llm": {"openai": {"api_key_env": "OPENAI_API_KEY"}}}


def test_set_nested_value_overwrites_existing():
    """Test setting value overwrites existing"""
    obj = {"llm": {"provider": "openai"}}
    _set_nested_value(obj, "llm.provider", "anthropic")
    assert obj["llm"]["provider"] == "anthropic"


def test_delete_nested_value_simple():
    """Test deleting simple nested value"""
    obj = {"llm": {"provider": "anthropic"}}
    _delete_nested_value(obj, "llm.provider")
    assert obj == {"llm": {}}


def test_delete_nested_value_deep():
    """Test deleting deeply nested value"""
    obj = {"llm": {"openai": {"api_key_env": "KEY"}}}
    _delete_nested_value(obj, "llm.openai.api_key_env")
    assert obj == {"llm": {"openai": {}}}


def test_delete_nested_value_not_found():
    """Test deleting non-existent key raises error"""
    obj = {"llm": {}}
    with pytest.raises(KeyError):
        _delete_nested_value(obj, "llm.provider")


def test_is_empty_nested_dict_empty():
    """Test checking empty nested dict"""
    assert _is_empty_nested_dict({}) is True
    assert _is_empty_nested_dict({"a": {}}) is True
    assert _is_empty_nested_dict({"a": {"b": {}}}) is True


def test_is_empty_nested_dict_not_empty():
    """Test checking non-empty nested dict"""
    assert _is_empty_nested_dict({"a": "value"}) is False
    assert _is_empty_nested_dict({"a": {"b": "value"}}) is False


def test_parse_value_bool():
    """Test parsing boolean values"""
    assert _parse_value("true") is True
    assert _parse_value("True") is True
    assert _parse_value("TRUE") is True
    assert _parse_value("false") is False
    assert _parse_value("False") is False
    assert _parse_value("FALSE") is False


def test_parse_value_int():
    """Test parsing integer values"""
    assert _parse_value("42") == 42
    assert _parse_value("0") == 0
    assert _parse_value("-10") == -10


def test_parse_value_float():
    """Test parsing float values"""
    assert _parse_value("0.5") == 0.5
    assert _parse_value("3.14") == 3.14
    assert _parse_value("-2.5") == -2.5


def test_parse_value_string():
    """Test parsing string values"""
    assert _parse_value("gpt-4") == "gpt-4"
    assert _parse_value("anthropic") == "anthropic"
    assert _parse_value("") == ""


# ============================================================================
# Test list-projects Command (Story 4)
# ============================================================================


def test_cmd_list_projects_no_config(tmp_path: Path, monkeypatch, capsys):
    """Test list-projects when no config file exists"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    args = argparse.Namespace()
    cmd_list_projects(args)

    captured = capsys.readouterr()
    assert "No config file found" in captured.out
    assert "No project overrides configured" in captured.out


def test_cmd_list_projects_empty_overrides(tmp_path: Path, monkeypatch, minimal_config_dict: dict, capsys):
    """Test list-projects when project_overrides is empty"""
    config = minimal_config_dict.copy()
    config["project_overrides"] = {}

    config_file = tmp_path / "graphiti.config.json"
    config_file.write_text(json.dumps(config, indent=2))

    monkeypatch.chdir(tmp_path)

    args = argparse.Namespace()
    cmd_list_projects(args)

    captured = capsys.readouterr()
    assert "No project overrides configured" in captured.out
