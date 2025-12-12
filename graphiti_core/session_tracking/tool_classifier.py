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

import logging
import re
from enum import Enum
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolIntent(str, Enum):
    """Enumeration of tool operation intents.

    Each intent represents a fundamental type of operation that a tool
    can perform, regardless of the domain it operates in.
    """

    CREATE = "create"
    """Creating new files or resources."""

    MODIFY = "modify"
    """Modifying existing files or resources."""

    DELETE = "delete"
    """Deleting files or resources."""

    READ = "read"
    """Reading files or data."""

    SEARCH = "search"
    """Searching for content or patterns."""

    EXECUTE = "execute"
    """Running commands or processes."""

    CONFIGURE = "configure"
    """Setting up or modifying configuration."""

    COMMUNICATE = "communicate"
    """Communication or messaging operations."""

    VALIDATE = "validate"
    """Testing or validation operations."""

    TRANSFORM = "transform"
    """Converting or transforming data."""


class ToolDomain(str, Enum):
    """Enumeration of tool operation domains.

    Each domain represents a category of resources or systems that
    a tool operates on.
    """

    FILESYSTEM = "filesystem"
    """File and directory operations."""

    CODE = "code"
    """Code analysis and manipulation."""

    DATABASE = "database"
    """Database operations."""

    NETWORK = "network"
    """Network and web operations."""

    PROCESS = "process"
    """Process and shell operations."""

    VERSION_CONTROL = "version_control"
    """Git and version control operations."""

    PACKAGE = "package"
    """Package management (npm, pip, etc.)."""

    DOCUMENTATION = "documentation"
    """Documentation operations."""

    TESTING = "testing"
    """Test-related operations."""

    MEMORY = "memory"
    """Memory/context operations (MCP)."""

    UNKNOWN = "unknown"
    """Unclassified operations."""


class ToolClassification(BaseModel):
    """Classification result for a tool call.

    Contains the detected intent and domain of a tool operation,
    along with confidence scores and mapping to activity signals.

    Example:
        >>> classifier = ToolClassifier()
        >>> result = classifier.classify("Read")
        >>> result.intent
        <ToolIntent.READ: 'read'>
        >>> result.domain
        <ToolDomain.FILESYSTEM: 'filesystem'>
        >>> result.confidence
        1.0
    """

    intent: ToolIntent = Field(
        description="The detected intent of the tool operation"
    )

    domain: ToolDomain = Field(
        description="The domain this tool operates in"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="0.0-1.0 confidence in the classification"
    )

    activity_signals: dict[str, float] = Field(
        default_factory=dict,
        description="Mapping to ActivityVector dimensions"
    )

    tool_name: str = Field(
        description="Original tool name that was classified"
    )

    method: Literal["heuristic", "llm", "cached"] = Field(
        default="heuristic",
        description="Classification method used"
    )


class ToolClassifier:
    """Classify tools using heuristic pattern matching.

    The classifier uses a three-step process:
    1. Check known tool mappings (exact matches, confidence 1.0)
    2. Pattern matching on tool name parts
    3. Compute activity signals from intent+domain

    LLM fallback is not implemented in this class - see Story 5 for
    LLM classification with caching.

    Example:
        >>> classifier = ToolClassifier()
        >>> result = classifier.classify("mcp__serena__find_symbol")
        >>> result.intent
        <ToolIntent.SEARCH: 'search'>
        >>> result.domain
        <ToolDomain.CODE: 'code'>
    """

    # Known tool mappings: (intent, domain, confidence)
    KNOWN_TOOL_MAPPINGS: ClassVar[dict[str, tuple[ToolIntent, ToolDomain, float]]] = {
        # Claude Code native tools
        "Read": (ToolIntent.READ, ToolDomain.FILESYSTEM, 1.0),
        "Write": (ToolIntent.CREATE, ToolDomain.FILESYSTEM, 1.0),
        "Edit": (ToolIntent.MODIFY, ToolDomain.FILESYSTEM, 1.0),
        "Glob": (ToolIntent.SEARCH, ToolDomain.FILESYSTEM, 1.0),
        "Grep": (ToolIntent.SEARCH, ToolDomain.FILESYSTEM, 1.0),
        "Bash": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 1.0),
        "Task": (ToolIntent.EXECUTE, ToolDomain.PROCESS, 0.9),
        "TodoWrite": (ToolIntent.CREATE, ToolDomain.MEMORY, 0.9),
        "WebFetch": (ToolIntent.READ, ToolDomain.NETWORK, 1.0),
        "WebSearch": (ToolIntent.SEARCH, ToolDomain.NETWORK, 1.0),
        "AskUserQuestion": (ToolIntent.COMMUNICATE, ToolDomain.UNKNOWN, 0.9),
        "NotebookEdit": (ToolIntent.MODIFY, ToolDomain.CODE, 1.0),
        # MCP Serena tools
        "mcp__serena__find_symbol": (ToolIntent.SEARCH, ToolDomain.CODE, 1.0),
        "mcp__serena__replace_symbol_body": (ToolIntent.MODIFY, ToolDomain.CODE, 1.0),
        "mcp__serena__get_symbols_overview": (ToolIntent.READ, ToolDomain.CODE, 1.0),
        "mcp__serena__find_referencing_symbols": (ToolIntent.SEARCH, ToolDomain.CODE, 1.0),
        "mcp__serena__list_dir": (ToolIntent.READ, ToolDomain.FILESYSTEM, 1.0),
        "mcp__serena__find_file": (ToolIntent.SEARCH, ToolDomain.FILESYSTEM, 1.0),
        "mcp__serena__search_for_pattern": (ToolIntent.SEARCH, ToolDomain.CODE, 1.0),
        "mcp__serena__insert_after_symbol": (ToolIntent.CREATE, ToolDomain.CODE, 1.0),
        "mcp__serena__insert_before_symbol": (ToolIntent.CREATE, ToolDomain.CODE, 1.0),
        "mcp__serena__get_symbol_body": (ToolIntent.READ, ToolDomain.CODE, 1.0),
        "mcp__serena__activate_project": (ToolIntent.CONFIGURE, ToolDomain.CODE, 0.9),
        "mcp__serena__check_onboarding_performed": (ToolIntent.READ, ToolDomain.CODE, 0.9),
        "mcp__serena__read_memory": (ToolIntent.READ, ToolDomain.MEMORY, 1.0),
        "mcp__serena__write_memory": (ToolIntent.CREATE, ToolDomain.MEMORY, 1.0),
        "mcp__serena__list_memories": (ToolIntent.READ, ToolDomain.MEMORY, 1.0),
        "mcp__serena__delete_memory": (ToolIntent.DELETE, ToolDomain.MEMORY, 1.0),
        # MCP Claude Context tools
        "mcp__claude-context__search_code": (ToolIntent.SEARCH, ToolDomain.CODE, 1.0),
        "mcp__claude-context__index_codebase": (ToolIntent.CONFIGURE, ToolDomain.CODE, 0.9),
        "mcp__claude-context__get_indexing_status": (ToolIntent.READ, ToolDomain.CODE, 0.9),
        "mcp__claude-context__sync_now": (ToolIntent.CONFIGURE, ToolDomain.CODE, 0.9),
        "mcp__claude-context__get_index_tree": (ToolIntent.READ, ToolDomain.CODE, 0.9),
        "mcp__claude-context__clear_index": (ToolIntent.DELETE, ToolDomain.CODE, 0.9),
        # MCP Graphiti tools
        "mcp__graphiti-memory__add_memory": (ToolIntent.CREATE, ToolDomain.MEMORY, 1.0),
        "mcp__graphiti-memory__search_memory_nodes": (ToolIntent.SEARCH, ToolDomain.MEMORY, 1.0),
        "mcp__graphiti-memory__search_memory_facts": (ToolIntent.SEARCH, ToolDomain.MEMORY, 1.0),
        "mcp__graphiti-memory__get_episodes": (ToolIntent.READ, ToolDomain.MEMORY, 1.0),
        "mcp__graphiti-memory__delete_episode": (ToolIntent.DELETE, ToolDomain.MEMORY, 1.0),
        "mcp__graphiti-memory__clear_graph": (ToolIntent.DELETE, ToolDomain.MEMORY, 1.0),
        "mcp__graphiti-memory__health_check": (ToolIntent.VALIDATE, ToolDomain.MEMORY, 1.0),
        # MCP Context7 tools
        "mcp__context7-local__resolve-library-id": (ToolIntent.SEARCH, ToolDomain.DOCUMENTATION, 1.0),
        "mcp__context7-local__get-library-docs": (ToolIntent.READ, ToolDomain.DOCUMENTATION, 1.0),
        # MCP GPT Researcher tools
        "mcp__gptr-mcp__deep_research": (ToolIntent.SEARCH, ToolDomain.NETWORK, 1.0),
        "mcp__gptr-mcp__quick_search": (ToolIntent.SEARCH, ToolDomain.NETWORK, 1.0),
        "mcp__gptr-mcp__write_report": (ToolIntent.CREATE, ToolDomain.DOCUMENTATION, 0.9),
    }

    # Intent patterns: keywords -> (ToolIntent, confidence)
    INTENT_PATTERNS: ClassVar[list[tuple[list[str], ToolIntent, float]]] = [
        (["read", "get", "fetch", "list", "show", "view", "cat", "head", "tail"], ToolIntent.READ, 0.8),
        (["write", "create", "add", "new", "insert", "touch", "mkdir"], ToolIntent.CREATE, 0.8),
        (["edit", "update", "modify", "replace", "patch", "change"], ToolIntent.MODIFY, 0.8),
        (["delete", "remove", "rm", "unlink", "drop"], ToolIntent.DELETE, 0.8),
        (["search", "find", "grep", "glob", "query", "lookup"], ToolIntent.SEARCH, 0.85),
        (["bash", "shell", "exec", "run", "execute", "command"], ToolIntent.EXECUTE, 0.75),
        (["test", "check", "validate", "verify", "assert", "lint"], ToolIntent.VALIDATE, 0.8),
        (["config", "setup", "init", "set", "configure"], ToolIntent.CONFIGURE, 0.75),
        (["transform", "convert", "parse", "encode", "decode"], ToolIntent.TRANSFORM, 0.75),
        (["ask", "question", "prompt", "input", "communicate"], ToolIntent.COMMUNICATE, 0.7),
    ]

    # Domain patterns: keywords -> (ToolDomain, confidence)
    DOMAIN_PATTERNS: ClassVar[list[tuple[list[str], ToolDomain, float]]] = [
        (["file", "dir", "path", "folder", "fs"], ToolDomain.FILESYSTEM, 0.85),
        (["symbol", "code", "ast", "serena", "class", "function", "method"], ToolDomain.CODE, 0.9),
        (["git", "commit", "branch", "merge", "pr", "push", "pull"], ToolDomain.VERSION_CONTROL, 0.95),
        (["npm", "pip", "yarn", "pnpm", "cargo", "bundle", "package"], ToolDomain.PACKAGE, 0.9),
        (["test", "pytest", "jest", "spec", "coverage"], ToolDomain.TESTING, 0.9),
        (["memory", "graphiti", "context", "episode"], ToolDomain.MEMORY, 0.9),
        (["web", "http", "fetch", "url", "api", "network"], ToolDomain.NETWORK, 0.85),
        (["doc", "readme", "markdown", "md", "documentation"], ToolDomain.DOCUMENTATION, 0.8),
        (["db", "database", "sql", "neo4j", "postgres", "mysql"], ToolDomain.DATABASE, 0.9),
        (["bash", "shell", "process", "command"], ToolDomain.PROCESS, 0.8),
    ]

    # Activity signal mapping: intent -> activity dimension contributions
    INTENT_TO_ACTIVITY: ClassVar[dict[ToolIntent, dict[str, float]]] = {
        ToolIntent.CREATE: {"building": 0.6},
        ToolIntent.MODIFY: {"building": 0.4, "refactoring": 0.3},
        ToolIntent.DELETE: {"refactoring": 0.4},
        ToolIntent.READ: {"exploring": 0.5, "reviewing": 0.3},
        ToolIntent.SEARCH: {"exploring": 0.6},
        ToolIntent.EXECUTE: {"building": 0.3, "testing": 0.2},
        ToolIntent.CONFIGURE: {"configuring": 0.7},
        ToolIntent.COMMUNICATE: {"exploring": 0.3},
        ToolIntent.VALIDATE: {"testing": 0.6},
        ToolIntent.TRANSFORM: {"building": 0.3, "refactoring": 0.2},
    }

    # Domain modifiers: domain -> additional activity boosts
    DOMAIN_MODIFIERS: ClassVar[dict[ToolDomain, dict[str, float]]] = {
        ToolDomain.TESTING: {"testing": 0.3},
        ToolDomain.DOCUMENTATION: {"documenting": 0.5},
        ToolDomain.VERSION_CONTROL: {"reviewing": 0.2},
        ToolDomain.CODE: {"building": 0.1, "refactoring": 0.1},
        ToolDomain.PACKAGE: {"configuring": 0.2},
    }

    # Regex pattern for splitting tool names into parts
    _NAME_SPLIT_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r'[_\-.]|(?<=[a-z])(?=[A-Z])'  # Split on _, -, ., or camelCase boundaries
    )

    def classify(
        self, tool_name: str, parameters: dict[str, Any] | None = None
    ) -> ToolClassification:
        """Classify a tool call by name and optionally parameters.

        Attempts heuristic classification first. If heuristics cannot
        classify the tool, returns a classification with UNKNOWN domain
        and low confidence.

        Args:
            tool_name: The name of the tool to classify.
            parameters: Optional parameters dict (reserved for future use).

        Returns:
            ToolClassification with intent, domain, confidence, and activity signals.

        Example:
            >>> classifier = ToolClassifier()
            >>> result = classifier.classify("Read")
            >>> result.confidence
            1.0
        """
        # Try heuristic classification
        result = self._try_heuristic(tool_name, parameters)

        if result is not None:
            logger.debug(
                "Heuristic classification for '%s': %s/%s (conf=%.2f)",
                tool_name,
                result.intent.value,
                result.domain.value,
                result.confidence,
            )
            return result

        # Fallback: unknown classification with low confidence
        logger.debug(
            "No heuristic match for '%s', returning unknown classification",
            tool_name,
        )
        return ToolClassification(
            intent=ToolIntent.EXECUTE,  # Safe default
            domain=ToolDomain.UNKNOWN,
            confidence=0.3,
            activity_signals={"exploring": 0.3},
            tool_name=tool_name,
            method="heuristic",
        )

    def _try_heuristic(
        self, tool_name: str, parameters: dict[str, Any] | None = None
    ) -> ToolClassification | None:
        """Try to classify using heuristic patterns.

        Args:
            tool_name: The name of the tool to classify.
            parameters: Optional parameters dict (reserved for future use).

        Returns:
            ToolClassification if heuristics match, None otherwise.
        """
        # Step 1: Check known tool mappings
        if tool_name in self.KNOWN_TOOL_MAPPINGS:
            intent, domain, confidence = self.KNOWN_TOOL_MAPPINGS[tool_name]
            activity_signals = self._compute_activity_signals(intent, domain)
            return ToolClassification(
                intent=intent,
                domain=domain,
                confidence=confidence,
                activity_signals=activity_signals,
                tool_name=tool_name,
                method="heuristic",
            )

        # Step 2: Pattern matching on tool name parts
        tool_name_lower = tool_name.lower()
        parts = self._split_tool_name(tool_name_lower)

        intent_match = self._match_intent(parts)
        domain_match = self._match_domain(parts)

        # If we found both intent and domain
        if intent_match and domain_match:
            intent, intent_conf = intent_match
            domain, domain_conf = domain_match
            confidence = min(intent_conf, domain_conf)
            activity_signals = self._compute_activity_signals(intent, domain)
            return ToolClassification(
                intent=intent,
                domain=domain,
                confidence=confidence,
                activity_signals=activity_signals,
                tool_name=tool_name,
                method="heuristic",
            )

        # If we found only intent
        if intent_match:
            intent, intent_conf = intent_match
            domain = ToolDomain.UNKNOWN
            confidence = intent_conf * 0.7  # Reduced confidence
            activity_signals = self._compute_activity_signals(intent, domain)
            return ToolClassification(
                intent=intent,
                domain=domain,
                confidence=confidence,
                activity_signals=activity_signals,
                tool_name=tool_name,
                method="heuristic",
            )

        # If we found only domain
        if domain_match:
            domain, domain_conf = domain_match
            intent = ToolIntent.EXECUTE  # Safe default
            confidence = domain_conf * 0.7  # Reduced confidence
            activity_signals = self._compute_activity_signals(intent, domain)
            return ToolClassification(
                intent=intent,
                domain=domain,
                confidence=confidence,
                activity_signals=activity_signals,
                tool_name=tool_name,
                method="heuristic",
            )

        # No pattern match found
        return None

    def _split_tool_name(self, tool_name: str) -> list[str]:
        """Split a tool name into searchable parts.

        Handles underscore separation, camelCase, dots, and dashes.

        Args:
            tool_name: The tool name to split (should be lowercase).

        Returns:
            List of name parts.
        """
        parts = self._NAME_SPLIT_PATTERN.split(tool_name)
        # Filter out empty strings and return
        return [p for p in parts if p]

    def _match_intent(self, parts: list[str]) -> tuple[ToolIntent, float] | None:
        """Match tool name parts to an intent.

        Args:
            parts: List of tool name parts to match.

        Returns:
            Tuple of (ToolIntent, confidence) if match found, None otherwise.
        """
        best_match: tuple[ToolIntent, float] | None = None
        best_confidence = 0.0

        for keywords, intent, confidence in self.INTENT_PATTERNS:
            for keyword in keywords:
                for part in parts:
                    if keyword in part or part in keyword:
                        if confidence > best_confidence:
                            best_match = (intent, confidence)
                            best_confidence = confidence
                        break

        return best_match

    def _match_domain(self, parts: list[str]) -> tuple[ToolDomain, float] | None:
        """Match tool name parts to a domain.

        Args:
            parts: List of tool name parts to match.

        Returns:
            Tuple of (ToolDomain, confidence) if match found, None otherwise.
        """
        best_match: tuple[ToolDomain, float] | None = None
        best_confidence = 0.0

        for keywords, domain, confidence in self.DOMAIN_PATTERNS:
            for keyword in keywords:
                for part in parts:
                    if keyword in part or part in keyword:
                        if confidence > best_confidence:
                            best_match = (domain, confidence)
                            best_confidence = confidence
                        break

        return best_match

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
