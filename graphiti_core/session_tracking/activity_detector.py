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
from typing import ClassVar

from .activity_vector import ActivityVector
from .types import MessageRole, SessionMessage

logger = logging.getLogger(__name__)


class ActivityDetector:
    """Detect activity vector from session messages.

    Analyzes session messages to detect activity patterns using three
    signal sources:
    1. User intent keywords - Match keywords in user messages to activity dimensions
    2. Error patterns - Detect error indicators to boost "fixing" dimension
    3. File patterns - Detect file types to boost relevant dimensions

    Example:
        >>> detector = ActivityDetector()
        >>> messages = [SessionMessage(role=MessageRole.USER, content="fix the bug")]
        >>> activity_vector = detector.detect(messages)
        >>> activity_vector.fixing  # Should be high
    """

    # Mapping of activity dimensions to keyword patterns
    INTENT_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        'building': [
            'implement',
            'add',
            'create',
            'build',
            'new feature',
            'develop',
            'write',
            'generate',
        ],
        'fixing': [
            'fix',
            'bug',
            'error',
            'broken',
            'not working',
            'debug',
            'resolve',
            'crash',
            'issue',
        ],
        'configuring': [
            'config',
            'setup',
            'install',
            'environment',
            'settings',
            '.env',
            'configure',
            'initialization',
        ],
        'exploring': [
            'how does',
            'what is',
            'find',
            'search',
            'understand',
            'explain',
            'where is',
            'show me',
        ],
        'refactoring': [
            'refactor',
            'restructure',
            'reorganize',
            'clean up',
            'simplify',
            'improve',
            'optimize',
        ],
        'reviewing': [
            'review',
            'check',
            'analyze',
            'look at',
            'examine',
            'inspect',
            'audit',
        ],
        'testing': [
            'test',
            'verify',
            'validate',
            'check if',
            'make sure',
            'assert',
            'coverage',
        ],
        'documenting': [
            'document',
            'readme',
            'comment',
            'docstring',
            'changelog',
            'docs',
            'documentation',
        ],
    }

    # Regex patterns indicating error/fix scenarios
    ERROR_PATTERNS: ClassVar[list[str]] = [
        r'\berror\b',
        r'\bexception\b',
        r'\bfailed\b',
        r'\btraceback\b',
        r'\bcrash\b',
        r'\bTypeError\b',
        r'\bValueError\b',
        r'\bKeyError\b',
        r'\bAttributeError\b',
        r'\bImportError\b',
        r'\bRuntimeError\b',
        r'\bAssertionError\b',
    ]

    # File type patterns mapped to activities
    FILE_PATTERNS: ClassVar[dict[str, list[str]]] = {
        'configuring': [
            '.env',
            'config.',
            '.json',
            '.yaml',
            '.yml',
            '.toml',
            'package.json',
            'pyproject.toml',
            'setup.py',
            'setup.cfg',
        ],
        'testing': [
            'test_',
            '_test.',
            '_test.py',
            '.spec.',
            'conftest.py',
            'pytest.ini',
            '__tests__',
        ],
        'documenting': [
            'README',
            'CHANGELOG',
            '.md',
            'docs/',
            'CONTRIBUTING',
            'LICENSE',
        ],
    }

    # Maximum contribution from each signal source
    KEYWORD_CAP: ClassVar[float] = 0.5
    ERROR_BOOST: ClassVar[float] = 0.3
    FILE_BOOST: ClassVar[float] = 0.25

    def detect(self, messages: list[SessionMessage]) -> ActivityVector:
        """Detect activity vector from session messages.

        Analyzes messages using keyword detection, error pattern detection,
        and file pattern detection to build a comprehensive activity vector.

        Args:
            messages: List of session messages to analyze.

        Returns:
            ActivityVector representing detected activities.
        """
        if not messages:
            logger.debug('No messages provided, returning zero vector')
            return ActivityVector()

        # Collect signals from different sources
        keyword_signals = self._detect_user_intent_keywords(messages)
        error_signals = self._detect_error_patterns(messages)
        file_signals = self._detect_file_patterns(messages)

        # Combine all signals
        combined_signals = self._combine_signals(keyword_signals, error_signals, file_signals)

        logger.debug(
            'Combined signals: keywords=%s, errors=%s, files=%s -> combined=%s',
            keyword_signals,
            error_signals,
            file_signals,
            combined_signals,
        )

        # Create and return ActivityVector
        return ActivityVector.from_signals(combined_signals)

    def _detect_user_intent_keywords(
        self, messages: list[SessionMessage]
    ) -> dict[str, float]:
        """Analyze user messages for intent keywords.

        Args:
            messages: List of session messages.

        Returns:
            Dictionary mapping activity dimensions to signal values.
        """
        # Filter to user messages only
        user_messages = [m for m in messages if m.role == MessageRole.USER and m.content]

        if not user_messages:
            return {}

        # Count keyword matches per dimension
        dimension_counts: dict[str, int] = {dim: 0 for dim in ActivityVector.DIMENSIONS}
        total_matches = 0

        for message in user_messages:
            content_lower = message.content.lower() if message.content else ''

            for dimension, keywords in self.INTENT_KEYWORDS.items():
                for keyword in keywords:
                    # Count occurrences of keyword in content
                    count = content_lower.count(keyword.lower())
                    if count > 0:
                        dimension_counts[dimension] += count
                        total_matches += count

        if total_matches == 0:
            return {}

        # Normalize by total matches and cap at KEYWORD_CAP
        signals: dict[str, float] = {}
        for dimension, count in dimension_counts.items():
            if count > 0:
                normalized = count / total_matches
                signals[dimension] = min(normalized, self.KEYWORD_CAP)

        return signals

    def _detect_error_patterns(self, messages: list[SessionMessage]) -> dict[str, float]:
        """Detect error patterns to boost fixing dimension.

        Args:
            messages: List of session messages (all roles).

        Returns:
            Dictionary with potential fixing boost.
        """
        error_count = 0

        # Compile regex patterns for efficiency
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.ERROR_PATTERNS]

        for message in messages:
            if not message.content:
                continue

            for pattern in compiled_patterns:
                matches = pattern.findall(message.content)
                error_count += len(matches)

        if error_count == 0:
            return {}

        # Calculate fixing boost based on error count
        if error_count > 3:
            return {'fixing': self.ERROR_BOOST}
        else:
            # Gradual boost: 1-3 errors = 0.1 per error
            return {'fixing': error_count * 0.1}

    def _detect_file_patterns(self, messages: list[SessionMessage]) -> dict[str, float]:
        """Detect file type patterns in message content.

        Args:
            messages: List of session messages (all roles).

        Returns:
            Dictionary mapping activity dimensions to signal values.
        """
        # Count file pattern matches per dimension
        dimension_counts: dict[str, int] = {}

        for message in messages:
            if not message.content:
                continue

            content = message.content

            for dimension, patterns in self.FILE_PATTERNS.items():
                for pattern in patterns:
                    # Count occurrences of pattern in content
                    count = content.count(pattern)
                    if count > 0:
                        dimension_counts[dimension] = dimension_counts.get(dimension, 0) + count

        if not dimension_counts:
            return {}

        # Calculate signals based on counts
        signals: dict[str, float] = {}
        for dimension, count in dimension_counts.items():
            if count > 2:
                signals[dimension] = self.FILE_BOOST
            elif count >= 1:
                # Gradual boost: 1-2 files = 0.12 per file
                signals[dimension] = count * 0.12

        return signals

    def _combine_signals(self, *signal_dicts: dict[str, float]) -> dict[str, float]:
        """Combine signals from different sources with capping.

        Args:
            signal_dicts: Variable number of signal dictionaries.

        Returns:
            Combined signals dictionary with each dimension capped at 1.0.
        """
        combined: dict[str, float] = {}

        for signal_dict in signal_dicts:
            for dimension, value in signal_dict.items():
                current = combined.get(dimension, 0.0)
                combined[dimension] = current + value

        # Cap each dimension at 1.0
        for dimension in combined:
            combined[dimension] = min(combined[dimension], 1.0)

        return combined
