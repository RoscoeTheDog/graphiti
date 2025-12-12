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

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from graphiti_core.session_tracking.activity_vector import ActivityVector
from graphiti_core.session_tracking.bash_analyzer import (
    BashAnalyzer,
    BashCommandClassification,
)
from graphiti_core.session_tracking.tool_classifier import (
    ToolClassification,
    ToolClassifier,
)

if TYPE_CHECKING:
    from graphiti_core.llm_client import LLMClient

logger = logging.getLogger(__name__)


class UnifiedToolClassifier:
    """Unified classifier that routes tools to appropriate specialized classifiers.

    Combines ToolClassifier (for MCP and native tools) and BashAnalyzer
    (for bash commands) into a single interface. Provides session-level
    classification with activity vector aggregation.

    The routing decision is simple:
    - If tool_name.lower() == "bash": route to BashAnalyzer
    - Otherwise: route to ToolClassifier

    This covers all cases because:
    - Claude Code native "Bash" tool always has name "Bash"
    - MCP tools have names like "mcp__server__tool"
    - Native tools have names like "Read", "Write", "Glob"

    Args:
        llm_client: Optional LLM client for fallback classification.
        tool_cache_path: Optional path for ToolClassifier cache persistence.
        bash_cache_path: Optional path for BashAnalyzer cache persistence.

    Example:
        >>> classifier = UnifiedToolClassifier()
        >>> # Classify a bash command
        >>> result = classifier.classify_message({
        ...     "name": "Bash",
        ...     "params": {"command": "git status"}
        ... })
        >>> result.intent
        <ToolIntent.READ: 'read'>

        >>> # Classify an MCP tool
        >>> result = classifier.classify_message({
        ...     "name": "mcp__serena__find_symbol",
        ...     "params": {"name_path": "MyClass"}
        ... })
        >>> result.intent
        <ToolIntent.SEARCH: 'search'>

        >>> # Classify a full session
        >>> messages = [
        ...     {"name": "Read", "params": {"file_path": "/foo/bar.py"}},
        ...     {"name": "Bash", "params": {"command": "pytest tests/"}},
        ... ]
        >>> activity_vector, classifications = classifier.classify_session(messages)
        >>> activity_vector.testing  # Should be elevated from pytest
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        tool_cache_path: Path | None = None,
        bash_cache_path: Path | None = None,
    ) -> None:
        """Initialize the UnifiedToolClassifier with optional caching and LLM support.

        Args:
            llm_client: Optional LLM client for classifying unknown tools/commands.
            tool_cache_path: Optional path for ToolClassifier cache persistence.
            bash_cache_path: Optional path for BashAnalyzer cache persistence.
        """
        self._llm_client = llm_client
        self._tool_classifier = ToolClassifier(
            cache_path=tool_cache_path,
            llm_client=llm_client,
        )
        self._bash_analyzer = BashAnalyzer(
            llm_client=llm_client,
            cache_path=bash_cache_path,
        )

        logger.debug(
            "UnifiedToolClassifier initialized with llm_client=%s, "
            "tool_cache=%s, bash_cache=%s",
            llm_client is not None,
            tool_cache_path,
            bash_cache_path,
        )

    @property
    def tool_classifier(self) -> ToolClassifier:
        """Access the underlying ToolClassifier instance."""
        return self._tool_classifier

    @property
    def bash_analyzer(self) -> BashAnalyzer:
        """Access the underlying BashAnalyzer instance."""
        return self._bash_analyzer

    def classify_message(
        self, message: dict[str, Any]
    ) -> ToolClassification | BashCommandClassification:
        """Classify a single tool call message.

        Routes the message to the appropriate classifier based on tool name:
        - Bash tool: Routes to BashAnalyzer
        - All other tools: Routes to ToolClassifier

        Args:
            message: Dictionary with tool call information.
                Expected format: {"name": "tool_name", "params": {...}}
                For Bash: {"name": "Bash", "params": {"command": "..."}}

        Returns:
            ToolClassification for non-bash tools, or
            BashCommandClassification for bash commands.

        Example:
            >>> classifier = UnifiedToolClassifier()
            >>> # Bash command
            >>> result = classifier.classify_message({
            ...     "name": "Bash",
            ...     "params": {"command": "git commit -m 'fix'"}
            ... })
            >>> isinstance(result, BashCommandClassification)
            True

            >>> # Native tool
            >>> result = classifier.classify_message({
            ...     "name": "Read",
            ...     "params": {"file_path": "/foo.py"}
            ... })
            >>> isinstance(result, ToolClassification)
            True
        """
        tool_name = message.get("name", "")
        params = message.get("params", {}) or {}

        # Route based on tool type
        if tool_name.lower() == "bash":
            command = params.get("command", "")
            logger.debug("Routing to BashAnalyzer: command='%s'", command[:50])
            return self._bash_analyzer.classify(command)
        else:
            logger.debug("Routing to ToolClassifier: tool='%s'", tool_name)
            return self._tool_classifier.classify(tool_name, params)

    def classify_session(
        self, messages: list[dict[str, Any]]
    ) -> tuple[ActivityVector, list[ToolClassification | BashCommandClassification]]:
        """Classify all tool calls in a session and aggregate into an ActivityVector.

        Processes each message containing tool calls, classifies them, and
        aggregates the activity signals into a single ActivityVector.

        Args:
            messages: List of message dictionaries. Each message should have
                at minimum a "name" field for the tool name.
                Expected format: [{"name": "tool", "params": {...}}, ...]

        Returns:
            Tuple of (ActivityVector, list of classifications).
            - ActivityVector: Aggregated and normalized activity signals
            - List: Individual classification for each message

        Example:
            >>> classifier = UnifiedToolClassifier()
            >>> messages = [
            ...     {"name": "Read", "params": {"file_path": "/foo.py"}},
            ...     {"name": "Bash", "params": {"command": "pytest"}},
            ...     {"name": "mcp__serena__find_symbol", "params": {}},
            ... ]
            >>> activity_vector, classifications = classifier.classify_session(messages)
            >>> len(classifications)
            3
            >>> activity_vector.testing  # Elevated from pytest
        """
        if not messages:
            logger.debug("No messages provided, returning empty results")
            return ActivityVector(), []

        classifications: list[ToolClassification | BashCommandClassification] = []
        aggregate_signals: dict[str, float] = {}

        for msg in messages:
            # Skip messages without tool name
            if not msg.get("name"):
                logger.debug("Skipping message without tool name: %s", msg)
                continue

            # Classify the message
            classification = self.classify_message(msg)
            classifications.append(classification)

            # Aggregate activity signals
            for activity, signal in classification.activity_signals.items():
                aggregate_signals[activity] = (
                    aggregate_signals.get(activity, 0.0) + signal
                )

        logger.debug(
            "Classified %d messages, aggregate signals: %s",
            len(classifications),
            aggregate_signals,
        )

        # Create normalized ActivityVector from aggregated signals
        activity_vector = ActivityVector.from_signals(aggregate_signals)

        return activity_vector, classifications

    async def classify_message_async(
        self, message: dict[str, Any]
    ) -> ToolClassification | BashCommandClassification:
        """Async version of classify_message for batch operations.

        Uses the async batch methods of underlying classifiers for
        better performance when LLM fallback is needed.

        Args:
            message: Dictionary with tool call information.

        Returns:
            ToolClassification or BashCommandClassification.
        """
        tool_name = message.get("name", "")
        params = message.get("params", {}) or {}

        if tool_name.lower() == "bash":
            command = params.get("command", "")
            logger.debug("Async routing to BashAnalyzer: command='%s'", command[:50])
            results = await self._bash_analyzer.classify_batch([command])
            return results[0]
        else:
            logger.debug("Async routing to ToolClassifier: tool='%s'", tool_name)
            results = await self._tool_classifier.classify_batch([(tool_name, params)])
            return results[0]

    async def classify_session_async(
        self, messages: list[dict[str, Any]]
    ) -> tuple[ActivityVector, list[ToolClassification | BashCommandClassification]]:
        """Async version of classify_session with batch optimization.

        Groups messages by type (bash vs non-bash) and classifies in batches
        for better performance with LLM fallback.

        Args:
            messages: List of message dictionaries.

        Returns:
            Tuple of (ActivityVector, list of classifications).
        """
        if not messages:
            logger.debug("No messages provided, returning empty results")
            return ActivityVector(), []

        # Separate bash and non-bash messages
        bash_messages: list[tuple[int, str]] = []  # (original_index, command)
        tool_messages: list[tuple[int, str, dict]] = []  # (index, name, params)

        for idx, msg in enumerate(messages):
            tool_name = msg.get("name", "")
            if not tool_name:
                continue

            params = msg.get("params", {}) or {}

            if tool_name.lower() == "bash":
                command = params.get("command", "")
                bash_messages.append((idx, command))
            else:
                tool_messages.append((idx, tool_name, params))

        # Classify in batches
        results: dict[int, ToolClassification | BashCommandClassification] = {}

        if bash_messages:
            commands = [cmd for _, cmd in bash_messages]
            bash_results = await self._bash_analyzer.classify_batch(commands)
            for (idx, _), result in zip(bash_messages, bash_results):
                results[idx] = result

        if tool_messages:
            tool_calls = [(name, params) for _, name, params in tool_messages]
            tool_results = await self._tool_classifier.classify_batch(tool_calls)
            for (idx, _, _), result in zip(tool_messages, tool_results):
                results[idx] = result

        # Reconstruct ordered list and aggregate signals
        classifications: list[ToolClassification | BashCommandClassification] = []
        aggregate_signals: dict[str, float] = {}

        for idx in sorted(results.keys()):
            classification = results[idx]
            classifications.append(classification)

            for activity, signal in classification.activity_signals.items():
                aggregate_signals[activity] = (
                    aggregate_signals.get(activity, 0.0) + signal
                )

        logger.debug(
            "Async classified %d messages, aggregate signals: %s",
            len(classifications),
            aggregate_signals,
        )

        activity_vector = ActivityVector.from_signals(aggregate_signals)
        return activity_vector, classifications

    def save_caches(self) -> None:
        """Persist caches to disk if cache paths were provided.

        Saves both the ToolClassifier and BashAnalyzer caches.
        """
        self._tool_classifier.save_cache()
        self._bash_analyzer.save_cache()
        logger.debug("Saved classifier caches to disk")
