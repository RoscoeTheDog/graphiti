"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, NamedTuple

from pydantic import BaseModel, Field

from graphiti_core.session_tracking.tool_classifier import ToolDomain, ToolIntent

if TYPE_CHECKING:
    from graphiti_core.llm_client import LLMClient

logger = logging.getLogger(__name__)


# LLM Classification Prompt Template for Bash Commands
LLM_BASH_CLASSIFICATION_PROMPT = """Analyze these bash commands and classify their intent.

For each command, determine:
1. Intent: create, modify, delete, read, search, execute, configure, validate, transform
2. Domain: filesystem, code, database, network, process, version_control, package, testing, memory
3. Activity Signals: Rate 0.0-1.0 contribution to each dimension:
   - building: Creating new code/features
   - fixing: Fixing bugs or issues
   - configuring: Setting up environment/dependencies
   - exploring: Investigating/understanding code
   - refactoring: Restructuring existing code
   - reviewing: Reviewing code changes
   - testing: Running tests/validation
   - documenting: Writing documentation

4. Reasoning: Brief explanation of classification

Respond with a JSON object containing a "classifications" array. Each classification should have:
- raw_command: The exact command from input
- intent: One of the intent values above
- domain: One of the domain values above
- activity_signals: Object mapping dimension names to float values 0.0-1.0
- reasoning: Brief explanation

## Commands to Classify:
{commands_json}
"""


class CommandHeuristic(NamedTuple):
    """Heuristic configuration for a command."""

    default_intent: ToolIntent
    default_domain: ToolDomain
    default_confidence: float
    subcommands: dict[str, tuple[ToolIntent, ToolDomain, float]] | None


class BashCommandClassification(BaseModel):
    """Classification result for a bash command.

    Contains parsed command structure and classification with activity signals.

    Example:
        >>> analyzer = BashAnalyzer()
        >>> result = analyzer.classify("git commit -m 'feat: new feature'")
        >>> result.intent
        <ToolIntent.CREATE: 'create'>
        >>> result.domain
        <ToolDomain.VERSION_CONTROL: 'version_control'>
    """

    raw_command: str = Field(description="Original command string")

    base_command: str = Field(description="Primary executable (pytest, git, npm)")

    subcommand: str | None = Field(
        default=None, description="Subcommand if applicable (install, commit)"
    )

    flags: list[str] = Field(
        default_factory=list, description="Command flags and options"
    )

    targets: list[str] = Field(
        default_factory=list, description="Command targets/arguments"
    )

    intent: ToolIntent = Field(description="Detected intent")

    domain: ToolDomain = Field(description="Detected domain")

    confidence: float = Field(
        ge=0.0, le=1.0, description="0.0-1.0 confidence score"
    )

    reasoning: str = Field(default="", description="Classification explanation")

    activity_signals: dict[str, float] = Field(
        default_factory=dict, description="Activity vector contributions"
    )

    method: Literal["heuristic", "llm", "cached"] = Field(
        default="heuristic", description="Classification method used"
    )


class LLMBashClassificationResult(BaseModel):
    """Single bash command classification result from LLM.

    Used as part of the structured response from LLM classification.
    """

    raw_command: str = Field(description="Original command string")
    intent: str = Field(description="Intent enum value (lowercase)")
    domain: str = Field(description="Domain enum value (lowercase)")
    activity_signals: dict[str, float] = Field(
        default_factory=dict, description="Activity vector contributions (0.0-1.0)"
    )
    reasoning: str = Field(default="", description="Classification explanation")


class LLMBashClassificationResponse(BaseModel):
    """Pydantic model for LLM structured response.

    Contains a list of classification results for batch bash command classification.
    """

    classifications: list[LLMBashClassificationResult] = Field(
        description="List of classification results from LLM"
    )


class BashAnalyzer:
    """Analyze and classify bash commands.

    Uses heuristic pattern matching for common commands (git, npm, pytest, etc.)
    with LLM fallback for unknown or ambiguous commands.

    Args:
        llm_client: Optional LLM client for fallback classification.
        cache_path: Optional path for persistent cache storage (JSON file).

    Example:
        >>> analyzer = BashAnalyzer()
        >>> result = analyzer.classify("pytest tests/ -v")
        >>> result.intent
        <ToolIntent.VALIDATE: 'validate'>
        >>> result.domain
        <ToolDomain.TESTING: 'testing'>

        >>> # With LLM fallback
        >>> from graphiti_core.llm_client import OpenAIClient
        >>> analyzer = BashAnalyzer(llm_client=OpenAIClient())
        >>> results = await analyzer.classify_batch(["custom-tool --arg"])
    """

    # Command heuristics: base_command -> CommandHeuristic
    COMMAND_HEURISTICS: ClassVar[dict[str, CommandHeuristic]] = {
        # Git commands
        "git": CommandHeuristic(
            default_intent=ToolIntent.MODIFY,
            default_domain=ToolDomain.VERSION_CONTROL,
            default_confidence=0.9,
            subcommands={
                "add": (ToolIntent.CREATE, ToolDomain.VERSION_CONTROL, 0.95),
                "commit": (ToolIntent.CREATE, ToolDomain.VERSION_CONTROL, 0.95),
                "push": (ToolIntent.CREATE, ToolDomain.VERSION_CONTROL, 0.95),
                "pull": (ToolIntent.READ, ToolDomain.VERSION_CONTROL, 0.95),
                "clone": (ToolIntent.READ, ToolDomain.VERSION_CONTROL, 0.95),
                "fetch": (ToolIntent.READ, ToolDomain.VERSION_CONTROL, 0.95),
                "diff": (ToolIntent.READ, ToolDomain.VERSION_CONTROL, 0.95),
                "status": (ToolIntent.READ, ToolDomain.VERSION_CONTROL, 0.95),
                "log": (ToolIntent.READ, ToolDomain.VERSION_CONTROL, 0.95),
                "show": (ToolIntent.READ, ToolDomain.VERSION_CONTROL, 0.95),
                "checkout": (ToolIntent.MODIFY, ToolDomain.VERSION_CONTROL, 0.9),
                "branch": (ToolIntent.MODIFY, ToolDomain.VERSION_CONTROL, 0.9),
                "merge": (ToolIntent.MODIFY, ToolDomain.VERSION_CONTROL, 0.9),
                "rebase": (ToolIntent.MODIFY, ToolDomain.VERSION_CONTROL, 0.9),
                "reset": (ToolIntent.MODIFY, ToolDomain.VERSION_CONTROL, 0.9),
                "stash": (ToolIntent.MODIFY, ToolDomain.VERSION_CONTROL, 0.9),
                "rm": (ToolIntent.DELETE, ToolDomain.VERSION_CONTROL, 0.9),
            },
        ),
        # NPM/Yarn/PNPM commands
        "npm": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PACKAGE,
            default_confidence=0.8,
            subcommands={
                "install": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "i": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "add": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "remove": (ToolIntent.DELETE, ToolDomain.PACKAGE, 0.95),
                "uninstall": (ToolIntent.DELETE, ToolDomain.PACKAGE, 0.95),
                "run": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "test": (ToolIntent.VALIDATE, ToolDomain.TESTING, 0.95),
                "build": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.9),
                "start": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "init": (ToolIntent.CREATE, ToolDomain.PACKAGE, 0.9),
                "publish": (ToolIntent.CREATE, ToolDomain.PACKAGE, 0.9),
                "update": (ToolIntent.MODIFY, ToolDomain.PACKAGE, 0.9),
                "outdated": (ToolIntent.READ, ToolDomain.PACKAGE, 0.9),
                "list": (ToolIntent.READ, ToolDomain.PACKAGE, 0.9),
                "ls": (ToolIntent.READ, ToolDomain.PACKAGE, 0.9),
            },
        ),
        "yarn": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PACKAGE,
            default_confidence=0.8,
            subcommands={
                "install": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "add": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "remove": (ToolIntent.DELETE, ToolDomain.PACKAGE, 0.95),
                "run": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "test": (ToolIntent.VALIDATE, ToolDomain.TESTING, 0.95),
                "build": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.9),
                "start": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
            },
        ),
        "pnpm": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PACKAGE,
            default_confidence=0.8,
            subcommands={
                "install": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "i": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "add": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "remove": (ToolIntent.DELETE, ToolDomain.PACKAGE, 0.95),
                "run": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "test": (ToolIntent.VALIDATE, ToolDomain.TESTING, 0.95),
                "build": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.9),
                "start": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
            },
        ),
        # Python test runners
        "pytest": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.TESTING,
            default_confidence=0.95,
            subcommands=None,
        ),
        "python": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.8,
            subcommands={
                "-m": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.85),
                "-c": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.85),
            },
        ),
        "py": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.8,
            subcommands=None,
        ),
        # JavaScript test runners
        "jest": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.TESTING,
            default_confidence=0.95,
            subcommands=None,
        ),
        "mocha": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.TESTING,
            default_confidence=0.95,
            subcommands=None,
        ),
        "vitest": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.TESTING,
            default_confidence=0.95,
            subcommands=None,
        ),
        # Docker commands
        "docker": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.8,
            subcommands={
                "run": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.95),
                "build": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.95),
                "push": (ToolIntent.CREATE, ToolDomain.NETWORK, 0.9),
                "pull": (ToolIntent.READ, ToolDomain.NETWORK, 0.9),
                "exec": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.95),
                "ps": (ToolIntent.READ, ToolDomain.PROCESS, 0.9),
                "logs": (ToolIntent.READ, ToolDomain.PROCESS, 0.9),
                "stop": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "start": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "rm": (ToolIntent.DELETE, ToolDomain.PROCESS, 0.9),
                "rmi": (ToolIntent.DELETE, ToolDomain.PROCESS, 0.9),
                "images": (ToolIntent.READ, ToolDomain.PROCESS, 0.9),
                "compose": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.85),
            },
        ),
        "docker-compose": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.85,
            subcommands={
                "up": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "down": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "build": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.9),
                "logs": (ToolIntent.READ, ToolDomain.PROCESS, 0.9),
                "ps": (ToolIntent.READ, ToolDomain.PROCESS, 0.9),
            },
        ),
        # Python package managers
        "pip": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PACKAGE,
            default_confidence=0.8,
            subcommands={
                "install": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "uninstall": (ToolIntent.DELETE, ToolDomain.PACKAGE, 0.95),
                "freeze": (ToolIntent.READ, ToolDomain.PACKAGE, 0.9),
                "list": (ToolIntent.READ, ToolDomain.PACKAGE, 0.9),
                "show": (ToolIntent.READ, ToolDomain.PACKAGE, 0.9),
                "search": (ToolIntent.SEARCH, ToolDomain.PACKAGE, 0.9),
            },
        ),
        "uv": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PACKAGE,
            default_confidence=0.8,
            subcommands={
                "pip": (ToolIntent.EXECUTE, ToolDomain.PACKAGE, 0.85),
                "venv": (ToolIntent.CREATE, ToolDomain.PACKAGE, 0.9),
                "sync": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.9),
                "lock": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.9),
                "add": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "remove": (ToolIntent.DELETE, ToolDomain.PACKAGE, 0.95),
                "run": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
            },
        ),
        "poetry": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PACKAGE,
            default_confidence=0.8,
            subcommands={
                "install": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "add": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "remove": (ToolIntent.DELETE, ToolDomain.PACKAGE, 0.95),
                "update": (ToolIntent.MODIFY, ToolDomain.PACKAGE, 0.9),
                "build": (ToolIntent.CREATE, ToolDomain.PACKAGE, 0.9),
                "publish": (ToolIntent.CREATE, ToolDomain.PACKAGE, 0.9),
                "run": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "shell": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.85),
            },
        ),
        # Rust commands
        "cargo": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PACKAGE,
            default_confidence=0.8,
            subcommands={
                "build": (ToolIntent.CREATE, ToolDomain.CODE, 0.95),
                "run": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
                "test": (ToolIntent.VALIDATE, ToolDomain.TESTING, 0.95),
                "add": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "remove": (ToolIntent.DELETE, ToolDomain.PACKAGE, 0.95),
                "install": (ToolIntent.CONFIGURE, ToolDomain.PACKAGE, 0.95),
                "update": (ToolIntent.MODIFY, ToolDomain.PACKAGE, 0.9),
                "check": (ToolIntent.VALIDATE, ToolDomain.CODE, 0.9),
                "clippy": (ToolIntent.VALIDATE, ToolDomain.CODE, 0.9),
                "fmt": (ToolIntent.MODIFY, ToolDomain.CODE, 0.9),
                "doc": (ToolIntent.CREATE, ToolDomain.DOCUMENTATION, 0.9),
                "publish": (ToolIntent.CREATE, ToolDomain.PACKAGE, 0.9),
                "new": (ToolIntent.CREATE, ToolDomain.CODE, 0.9),
                "init": (ToolIntent.CREATE, ToolDomain.CODE, 0.9),
            },
        ),
        # Build tools
        "make": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.85,
            subcommands={
                "test": (ToolIntent.VALIDATE, ToolDomain.TESTING, 0.9),
                "build": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.9),
                "clean": (ToolIntent.DELETE, ToolDomain.FILESYSTEM, 0.9),
                "install": (ToolIntent.CONFIGURE, ToolDomain.PROCESS, 0.9),
                "all": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.85),
            },
        ),
        "gradle": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.85,
            subcommands={
                "build": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.9),
                "test": (ToolIntent.VALIDATE, ToolDomain.TESTING, 0.95),
                "clean": (ToolIntent.DELETE, ToolDomain.FILESYSTEM, 0.9),
                "run": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
            },
        ),
        "mvn": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.85,
            subcommands={
                "install": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.9),
                "compile": (ToolIntent.CREATE, ToolDomain.CODE, 0.9),
                "test": (ToolIntent.VALIDATE, ToolDomain.TESTING, 0.95),
                "clean": (ToolIntent.DELETE, ToolDomain.FILESYSTEM, 0.9),
                "package": (ToolIntent.CREATE, ToolDomain.PROCESS, 0.9),
            },
        ),
        # File system commands
        "ls": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "cat": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "head": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "tail": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "less": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "more": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "find": CommandHeuristic(
            default_intent=ToolIntent.SEARCH,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "grep": CommandHeuristic(
            default_intent=ToolIntent.SEARCH,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "rg": CommandHeuristic(
            default_intent=ToolIntent.SEARCH,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "ag": CommandHeuristic(
            default_intent=ToolIntent.SEARCH,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "mkdir": CommandHeuristic(
            default_intent=ToolIntent.CREATE,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "touch": CommandHeuristic(
            default_intent=ToolIntent.CREATE,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "rm": CommandHeuristic(
            default_intent=ToolIntent.DELETE,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "rmdir": CommandHeuristic(
            default_intent=ToolIntent.DELETE,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        "cp": CommandHeuristic(
            default_intent=ToolIntent.CREATE,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.9,
            subcommands=None,
        ),
        "mv": CommandHeuristic(
            default_intent=ToolIntent.MODIFY,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.9,
            subcommands=None,
        ),
        "chmod": CommandHeuristic(
            default_intent=ToolIntent.MODIFY,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.9,
            subcommands=None,
        ),
        "chown": CommandHeuristic(
            default_intent=ToolIntent.MODIFY,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.9,
            subcommands=None,
        ),
        "cd": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.85,
            subcommands=None,
        ),
        "pwd": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.FILESYSTEM,
            default_confidence=0.95,
            subcommands=None,
        ),
        # Network commands
        "curl": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.NETWORK,
            default_confidence=0.9,
            subcommands=None,
        ),
        "wget": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.NETWORK,
            default_confidence=0.9,
            subcommands=None,
        ),
        "ssh": CommandHeuristic(
            default_intent=ToolIntent.EXECUTE,
            default_domain=ToolDomain.NETWORK,
            default_confidence=0.9,
            subcommands=None,
        ),
        "scp": CommandHeuristic(
            default_intent=ToolIntent.CREATE,
            default_domain=ToolDomain.NETWORK,
            default_confidence=0.9,
            subcommands=None,
        ),
        # Code formatters/linters
        "prettier": CommandHeuristic(
            default_intent=ToolIntent.MODIFY,
            default_domain=ToolDomain.CODE,
            default_confidence=0.9,
            subcommands=None,
        ),
        "eslint": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.CODE,
            default_confidence=0.9,
            subcommands=None,
        ),
        "black": CommandHeuristic(
            default_intent=ToolIntent.MODIFY,
            default_domain=ToolDomain.CODE,
            default_confidence=0.9,
            subcommands=None,
        ),
        "ruff": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.CODE,
            default_confidence=0.9,
            subcommands={
                "check": (ToolIntent.VALIDATE, ToolDomain.CODE, 0.95),
                "format": (ToolIntent.MODIFY, ToolDomain.CODE, 0.95),
                "fix": (ToolIntent.MODIFY, ToolDomain.CODE, 0.9),
            },
        ),
        "mypy": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.CODE,
            default_confidence=0.95,
            subcommands=None,
        ),
        "pylint": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.CODE,
            default_confidence=0.95,
            subcommands=None,
        ),
        "flake8": CommandHeuristic(
            default_intent=ToolIntent.VALIDATE,
            default_domain=ToolDomain.CODE,
            default_confidence=0.95,
            subcommands=None,
        ),
        # Shell built-ins
        "echo": CommandHeuristic(
            default_intent=ToolIntent.READ,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.8,
            subcommands=None,
        ),
        "export": CommandHeuristic(
            default_intent=ToolIntent.CONFIGURE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.85,
            subcommands=None,
        ),
        "source": CommandHeuristic(
            default_intent=ToolIntent.CONFIGURE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.85,
            subcommands=None,
        ),
        ".": CommandHeuristic(
            default_intent=ToolIntent.CONFIGURE,
            default_domain=ToolDomain.PROCESS,
            default_confidence=0.85,
            subcommands=None,
        ),
    }

    # Activity signal mapping: intent -> activity dimension contributions
    # (Reusing pattern from ToolClassifier)
    INTENT_TO_ACTIVITY: ClassVar[dict[ToolIntent, dict[str, float]]] = {
        ToolIntent.CREATE: {"building": 0.6},
        ToolIntent.MODIFY: {"building": 0.4, "refactoring": 0.3},
        ToolIntent.DELETE: {"refactoring": 0.4},
        ToolIntent.READ: {"exploring": 0.5, "reviewing": 0.3},
        ToolIntent.SEARCH: {"exploring": 0.6},
        ToolIntent.EXECUTE: {"building": 0.3, "testing": 0.2},
        ToolIntent.CONFIGURE: {"configuring": 0.7},
        ToolIntent.COMMUNICATE: {"exploring": 0.3},
        ToolIntent.VALIDATE: {"testing": 0.9},
        ToolIntent.TRANSFORM: {"building": 0.3, "refactoring": 0.2},
    }

    # Domain modifiers: domain -> additional activity boosts
    # (Reusing pattern from ToolClassifier)
    DOMAIN_MODIFIERS: ClassVar[dict[ToolDomain, dict[str, float]]] = {
        ToolDomain.TESTING: {"testing": 0.3},
        ToolDomain.DOCUMENTATION: {"documenting": 0.5},
        ToolDomain.VERSION_CONTROL: {"reviewing": 0.2},
        ToolDomain.CODE: {"building": 0.1, "refactoring": 0.1},
        ToolDomain.PACKAGE: {"configuring": 0.2},
    }

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        cache_path: Path | None = None,
    ) -> None:
        """Initialize the BashAnalyzer with optional LLM and caching.

        Args:
            llm_client: Optional LLM client for classifying unknown commands.
            cache_path: Optional path for persistent cache storage.
        """
        self._llm_client = llm_client
        self._cache_path = cache_path
        self._cache: dict[str, BashCommandClassification] = {}

        # Load persistent cache if path provided
        if cache_path is not None:
            self._load_cache()

    def classify(self, command: str) -> BashCommandClassification:
        """Classify a single bash command.

        Args:
            command: The bash command string to classify.

        Returns:
            BashCommandClassification with parsed structure and classification.

        Example:
            >>> analyzer = BashAnalyzer()
            >>> result = analyzer.classify("git commit -m 'feat: new feature'")
            >>> result.base_command
            'git'
            >>> result.subcommand
            'commit'
        """
        # Check cache first
        cache_key = self._get_cache_key(command)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return BashCommandClassification(
                raw_command=command,
                base_command=cached.base_command,
                subcommand=cached.subcommand,
                flags=cached.flags,
                targets=cached.targets,
                intent=cached.intent,
                domain=cached.domain,
                confidence=cached.confidence,
                reasoning=cached.reasoning,
                activity_signals=cached.activity_signals,
                method="cached",
            )

        # Parse the command
        base_command, subcommand, flags, targets = self._parse_command(command)

        # Try heuristic classification
        result = self._classify_heuristic(
            command, base_command, subcommand, flags, targets
        )

        if result is not None:
            # Update cache
            self._cache[cache_key] = result
            logger.debug(
                "Heuristic classification for '%s': %s/%s (conf=%.2f)",
                command,
                result.intent.value,
                result.domain.value,
                result.confidence,
            )
            return result

        # Fallback: unknown classification with low confidence
        logger.debug(
            "No heuristic match for '%s', returning unknown classification",
            command,
        )
        activity_signals = self._compute_activity_signals(
            ToolIntent.EXECUTE, ToolDomain.UNKNOWN
        )
        return BashCommandClassification(
            raw_command=command,
            base_command=base_command,
            subcommand=subcommand,
            flags=flags,
            targets=targets,
            intent=ToolIntent.EXECUTE,
            domain=ToolDomain.UNKNOWN,
            confidence=0.3,
            reasoning="Unknown command, using default classification",
            activity_signals=activity_signals,
            method="heuristic",
        )

    async def classify_batch(
        self, commands: list[str]
    ) -> list[BashCommandClassification]:
        """Classify multiple bash commands with LLM batching.

        Uses heuristics first, then batches unknown commands for LLM classification.

        Args:
            commands: List of bash command strings to classify.

        Returns:
            List of BashCommandClassification objects in same order as input.

        Example:
            >>> analyzer = BashAnalyzer(llm_client=my_llm)
            >>> results = await analyzer.classify_batch([
            ...     "git commit -m 'fix'",
            ...     "custom-tool --arg",
            ... ])
        """
        results: list[BashCommandClassification | None] = []
        unknown_commands: list[tuple[str, int]] = []

        for idx, command in enumerate(commands):
            # Try heuristic classification
            result = self.classify(command)

            if result.confidence >= 0.7:
                results.append(result)
            else:
                # Queue for LLM classification
                unknown_commands.append((command, idx))
                results.append(None)  # Placeholder

        # Batch LLM classification for unknown commands
        if unknown_commands and self._llm_client is not None:
            logger.debug("Classifying %d unknown commands with LLM", len(unknown_commands))
            llm_results = await self._classify_with_llm(
                [cmd for cmd, _ in unknown_commands]
            )

            # Update results and caches
            for (command, idx), llm_result in zip(unknown_commands, llm_results):
                results[idx] = llm_result
                cache_key = self._get_cache_key(command)
                self._cache[cache_key] = llm_result

        # Fill remaining placeholders with low-confidence defaults
        for idx in range(len(results)):
            if results[idx] is None:
                command = commands[idx]
                base_command, subcommand, flags, targets = self._parse_command(command)
                activity_signals = self._compute_activity_signals(
                    ToolIntent.EXECUTE, ToolDomain.UNKNOWN
                )
                results[idx] = BashCommandClassification(
                    raw_command=command,
                    base_command=base_command,
                    subcommand=subcommand,
                    flags=flags,
                    targets=targets,
                    intent=ToolIntent.EXECUTE,
                    domain=ToolDomain.UNKNOWN,
                    confidence=0.3,
                    reasoning="Unknown command, LLM fallback unavailable",
                    activity_signals=activity_signals,
                    method="heuristic",
                )

        # Cast to list[BashCommandClassification] - all None values have been replaced
        return [r for r in results if r is not None]

    def _parse_command(
        self, command: str
    ) -> tuple[str, str | None, list[str], list[str]]:
        """Parse a bash command into components.

        Handles:
        - Simple commands: "pytest tests/"
        - Commands with flags: "pytest -v --cov=src tests/"
        - Commands with subcommands: "git commit -m 'message'"
        - Quoted strings: "git commit -m 'fix: handle edge case'"
        - Chained commands (&&, ||, |): analyzes first command only

        Args:
            command: The bash command string to parse.

        Returns:
            Tuple of (base_command, subcommand, flags, targets).

        Example:
            >>> analyzer = BashAnalyzer()
            >>> analyzer._parse_command("git commit -m 'feat: new'")
            ('git', 'commit', ['-m', 'feat: new'], [])
        """
        # Handle chained commands - only analyze the first command
        # Split on && || ; | but be careful about quoted strings
        first_command = command
        for sep in ["&&", "||", ";", "|"]:
            # Simple split - shlex will handle quotes properly after
            if sep in command:
                parts = command.split(sep, 1)
                first_command = parts[0].strip()
                break

        try:
            tokens = shlex.split(first_command)
        except ValueError:
            # If shlex fails (unclosed quotes, etc.), do simple split
            tokens = first_command.split()

        if not tokens:
            return ("", None, [], [])

        base_command = tokens[0]

        # Get the binary name (handle paths like /usr/bin/git)
        if "/" in base_command or "\\" in base_command:
            base_command = Path(base_command).name

        subcommand: str | None = None
        flags: list[str] = []
        targets: list[str] = []

        # Check if this command has known subcommands
        heuristic = self.COMMAND_HEURISTICS.get(base_command)
        known_subcommands: set[str] = set()
        if heuristic and heuristic.subcommands:
            known_subcommands = set(heuristic.subcommands.keys())

        # Process remaining tokens
        i = 1
        while i < len(tokens):
            token = tokens[i]

            # Check for subcommand (must be first non-flag token)
            if subcommand is None and not token.startswith("-"):
                if token in known_subcommands or (
                    heuristic is None and i == 1 and not token.startswith("/")
                ):
                    subcommand = token
                    i += 1
                    continue

            # Handle flags
            if token.startswith("-"):
                # Check if flag takes a value (next token or =)
                if "=" in token:
                    flags.append(token)
                elif i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    # Flag with separate value (e.g., -m 'message')
                    # Check if this is a known value-taking flag
                    if token in {"-m", "-c", "-f", "-o", "-p", "--message", "--file"}:
                        flags.append(token)
                        flags.append(tokens[i + 1])
                        i += 2
                        continue
                    else:
                        flags.append(token)
                else:
                    flags.append(token)
            else:
                # Target/argument
                targets.append(token)

            i += 1

        return (base_command, subcommand, flags, targets)

    def _classify_heuristic(
        self,
        raw_command: str,
        base_command: str,
        subcommand: str | None,
        flags: list[str],
        targets: list[str],
    ) -> BashCommandClassification | None:
        """Classify using heuristic patterns.

        Args:
            raw_command: Original command string.
            base_command: Primary executable.
            subcommand: Subcommand if any.
            flags: List of flags.
            targets: List of targets.

        Returns:
            BashCommandClassification if heuristics match, None otherwise.
        """
        heuristic = self.COMMAND_HEURISTICS.get(base_command)

        if heuristic is None:
            return None

        intent: ToolIntent
        domain: ToolDomain
        confidence: float

        # Check for subcommand-specific classification
        if subcommand and heuristic.subcommands and subcommand in heuristic.subcommands:
            intent, domain, confidence = heuristic.subcommands[subcommand]
            reasoning = f"Matched {base_command} {subcommand} subcommand heuristic"
        else:
            intent = heuristic.default_intent
            domain = heuristic.default_domain
            confidence = heuristic.default_confidence
            reasoning = f"Matched {base_command} default heuristic"

        activity_signals = self._compute_activity_signals(intent, domain)

        return BashCommandClassification(
            raw_command=raw_command,
            base_command=base_command,
            subcommand=subcommand,
            flags=flags,
            targets=targets,
            intent=intent,
            domain=domain,
            confidence=confidence,
            reasoning=reasoning,
            activity_signals=activity_signals,
            method="heuristic",
        )

    def _compute_activity_signals(
        self, intent: ToolIntent, domain: ToolDomain
    ) -> dict[str, float]:
        """Compute activity vector contributions from intent and domain.

        Combines base signals from the intent with modifiers from the domain,
        capping each dimension at 1.0.

        Args:
            intent: The detected tool intent.
            domain: The detected tool domain.

        Returns:
            Dictionary mapping activity dimensions to signal values.
        """
        signals: dict[str, float] = {}

        # Start with intent-based signals
        if intent in self.INTENT_TO_ACTIVITY:
            for dim, value in self.INTENT_TO_ACTIVITY[intent].items():
                signals[dim] = signals.get(dim, 0.0) + value

        # Apply domain modifiers
        if domain in self.DOMAIN_MODIFIERS:
            for dim, value in self.DOMAIN_MODIFIERS[domain].items():
                signals[dim] = signals.get(dim, 0.0) + value

        # Cap each signal at 1.0
        for dim in signals:
            signals[dim] = min(signals[dim], 1.0)

        return signals

    async def _classify_with_llm(
        self, commands: list[str]
    ) -> list[BashCommandClassification]:
        """Batch classify unknown commands using LLM.

        Args:
            commands: List of command strings to classify.

        Returns:
            List of BashCommandClassification objects.
        """
        if self._llm_client is None:
            raise ValueError("No LLM client configured for command classification")

        # Import here to avoid circular dependency
        from graphiti_core.prompts.models import Message

        # Build prompt
        commands_json = json.dumps(
            [{"command": cmd} for cmd in commands],
            indent=2,
        )
        prompt = LLM_BASH_CLASSIFICATION_PROMPT.format(commands_json=commands_json)

        logger.debug("Classifying %d commands with LLM", len(commands))

        # Call LLM with structured response
        response = await self._llm_client.generate_response(
            messages=[Message(role="user", content=prompt)],
            response_model=LLMBashClassificationResponse,
        )

        # Convert to BashCommandClassification objects
        results: list[BashCommandClassification] = []
        classifications = response.get("classifications", [])

        # Build lookup by raw_command for matching
        result_map: dict[str, dict[str, Any]] = {}
        for r in classifications:
            if isinstance(r, dict):
                result_map[r.get("raw_command", "")] = r
            else:
                # Pydantic model
                result_map[r.raw_command] = {
                    "intent": r.intent,
                    "domain": r.domain,
                    "activity_signals": r.activity_signals,
                    "reasoning": r.reasoning,
                }

        # Match results to input order
        for command in commands:
            base_command, subcommand, flags, targets = self._parse_command(command)

            if command in result_map:
                r = result_map[command]
                try:
                    results.append(
                        BashCommandClassification(
                            raw_command=command,
                            base_command=base_command,
                            subcommand=subcommand,
                            flags=flags,
                            targets=targets,
                            intent=ToolIntent(r["intent"]),
                            domain=ToolDomain(r["domain"]),
                            confidence=0.85,  # LLM confidence
                            reasoning=r.get("reasoning", "Classified by LLM"),
                            activity_signals=r.get("activity_signals", {}),
                            method="llm",
                        )
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(
                        "Failed to parse LLM result for '%s': %s", command, e
                    )
                    # Fallback to unknown
                    activity_signals = self._compute_activity_signals(
                        ToolIntent.EXECUTE, ToolDomain.UNKNOWN
                    )
                    results.append(
                        BashCommandClassification(
                            raw_command=command,
                            base_command=base_command,
                            subcommand=subcommand,
                            flags=flags,
                            targets=targets,
                            intent=ToolIntent.EXECUTE,
                            domain=ToolDomain.UNKNOWN,
                            confidence=0.3,
                            reasoning="LLM response parsing failed",
                            activity_signals=activity_signals,
                            method="llm",
                        )
                    )
            else:
                # Command not in LLM response - fallback
                logger.warning("LLM did not classify command '%s'", command)
                activity_signals = self._compute_activity_signals(
                    ToolIntent.EXECUTE, ToolDomain.UNKNOWN
                )
                results.append(
                    BashCommandClassification(
                        raw_command=command,
                        base_command=base_command,
                        subcommand=subcommand,
                        flags=flags,
                        targets=targets,
                        intent=ToolIntent.EXECUTE,
                        domain=ToolDomain.UNKNOWN,
                        confidence=0.3,
                        reasoning="Command not found in LLM response",
                        activity_signals=activity_signals,
                        method="llm",
                    )
                )

        return results

    def _get_cache_key(self, command: str) -> str:
        """Generate cache key from command string.

        Args:
            command: The command string.

        Returns:
            Cache key string (MD5 hash of normalized command).
        """
        # Normalize: strip, lowercase
        normalized = command.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def save_cache(self) -> None:
        """Persist cache to JSON file.

        Uses atomic write (temp file + rename) to prevent corruption.
        """
        if self._cache_path is None:
            return

        cache_data = {
            "version": "1.0",
            "classifications": {k: v.model_dump() for k, v in self._cache.items()},
        }

        # Atomic write
        temp_path = self._cache_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            temp_path.replace(self._cache_path)
            logger.info(
                "Saved bash classification cache: %d entries",
                len(self._cache),
            )
        except OSError as e:
            logger.error("Failed to save cache to %s: %s", self._cache_path, e)
            if temp_path.exists():
                temp_path.unlink()

    def _load_cache(self) -> None:
        """Load cache from JSON file."""
        if self._cache_path is None or not self._cache_path.exists():
            return

        try:
            with open(self._cache_path, encoding="utf-8") as f:
                data = json.load(f)

            self._cache = {}
            for k, v in data.get("classifications", {}).items():
                try:
                    self._cache[k] = BashCommandClassification(**v)
                except Exception as e:
                    logger.warning("Skipping invalid cache entry '%s': %s", k, e)

            logger.info(
                "Loaded bash classification cache: %d entries",
                len(self._cache),
            )

        except json.JSONDecodeError as e:
            logger.warning("Cache file corrupted, resetting: %s", e)
            self._cache = {}
        except OSError as e:
            logger.warning("Could not load cache file: %s", e)
            self._cache = {}
