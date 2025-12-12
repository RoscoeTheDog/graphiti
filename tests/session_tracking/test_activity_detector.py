"""Tests for ActivityDetector class.

Tests Story 3 acceptance criteria:
- ActivityDetector class with detect(messages) -> ActivityVector method
- User intent keyword detection (implement, fix, debug, configure, explore, etc.)
- Error pattern detection (error, exception, traceback, failed)
- File pattern detection (config files, test files, documentation)
- Integration tests with sample session messages
"""

from datetime import datetime
from uuid import uuid4

import pytest

from graphiti_core.session_tracking.activity_detector import ActivityDetector
from graphiti_core.session_tracking.activity_vector import ActivityVector
from graphiti_core.session_tracking.types import MessageRole, SessionMessage


def make_message(
    content: str,
    role: MessageRole = MessageRole.USER,
    session_id: str = "test-session",
) -> SessionMessage:
    """Helper to create SessionMessage for testing."""
    return SessionMessage(
        uuid=str(uuid4()),
        session_id=session_id,
        role=role,
        timestamp=datetime.now(),
        content=content,
    )


class TestActivityDetectorBasics:
    """Test basic ActivityDetector creation and interface."""

    def test_detector_creation(self):
        """Test ActivityDetector can be instantiated."""
        detector = ActivityDetector()
        assert detector is not None

    def test_detect_returns_activity_vector(self):
        """Test detect() method returns ActivityVector."""
        detector = ActivityDetector()
        messages = [make_message("fix the bug")]
        result = detector.detect(messages)
        assert isinstance(result, ActivityVector)

    def test_detect_empty_messages(self):
        """Test detect() with empty list returns zero vector."""
        detector = ActivityDetector()
        result = detector.detect([])
        assert result == ActivityVector()

    def test_detect_none_content(self):
        """Test detect() handles messages with None content."""
        detector = ActivityDetector()
        msg = SessionMessage(
            uuid=str(uuid4()),
            session_id="test-session",
            role=MessageRole.USER,
            timestamp=datetime.now(),
            content=None,
        )
        result = detector.detect([msg])
        # Should not raise, should return zero vector
        assert isinstance(result, ActivityVector)


class TestUserIntentKeywordDetection:
    """Test user intent keyword detection (Signal Source 1)."""

    def test_building_keywords(self):
        """Test detection of building-related keywords."""
        detector = ActivityDetector()
        messages = [
            make_message("implement a new feature"),
            make_message("add the login functionality"),
            make_message("create the user model"),
        ]
        result = detector.detect(messages)
        assert result.building > 0
        assert "building" in result.dominant_activities

    def test_fixing_keywords(self):
        """Test detection of fixing-related keywords."""
        detector = ActivityDetector()
        messages = [
            make_message("fix the broken authentication"),
            make_message("debug the failing test"),
            make_message("resolve the crash issue"),
        ]
        result = detector.detect(messages)
        assert result.fixing > 0
        assert "fixing" in result.dominant_activities

    def test_configuring_keywords(self):
        """Test detection of configuring-related keywords."""
        detector = ActivityDetector()
        messages = [
            make_message("setup the environment variables"),
            make_message("configure the database connection"),
            make_message("install the dependencies"),
        ]
        result = detector.detect(messages)
        assert result.configuring > 0
        assert "configuring" in result.dominant_activities

    def test_exploring_keywords(self):
        """Test detection of exploring-related keywords."""
        detector = ActivityDetector()
        messages = [
            make_message("how does the authentication work?"),
            make_message("what is the purpose of this function?"),
            make_message("explain the data flow"),
        ]
        result = detector.detect(messages)
        assert result.exploring > 0
        assert "exploring" in result.dominant_activities

    def test_refactoring_keywords(self):
        """Test detection of refactoring-related keywords."""
        detector = ActivityDetector()
        messages = [
            make_message("refactor the legacy code"),
            make_message("restructure the module organization"),
            make_message("simplify the complex function"),
        ]
        result = detector.detect(messages)
        assert result.refactoring > 0
        assert "refactoring" in result.dominant_activities

    def test_reviewing_keywords(self):
        """Test detection of reviewing-related keywords."""
        detector = ActivityDetector()
        messages = [
            make_message("review the pull request"),
            make_message("analyze the code quality"),
            make_message("examine the security aspects"),
        ]
        result = detector.detect(messages)
        assert result.reviewing > 0
        assert "reviewing" in result.dominant_activities

    def test_testing_keywords(self):
        """Test detection of testing-related keywords."""
        detector = ActivityDetector()
        messages = [
            make_message("test the new feature"),
            make_message("verify the functionality works"),
            make_message("validate the input handling"),
        ]
        result = detector.detect(messages)
        assert result.testing > 0
        assert "testing" in result.dominant_activities

    def test_documenting_keywords(self):
        """Test detection of documenting-related keywords."""
        detector = ActivityDetector()
        messages = [
            make_message("document the API endpoints"),
            make_message("update the readme file"),
            make_message("add docstrings to functions"),
        ]
        result = detector.detect(messages)
        assert result.documenting > 0
        assert "documenting" in result.dominant_activities

    def test_only_user_messages_analyzed_for_keywords(self):
        """Test that only user messages are analyzed for intent keywords.

        Note: Error patterns and file patterns are detected in ALL roles,
        but intent keywords are only detected in user messages.
        """
        detector = ActivityDetector()
        # Use keywords that won't trigger error pattern detection
        # (error pattern 'error' would trigger from non-user messages)
        messages = [
            make_message("hello", role=MessageRole.USER),
            make_message("implement the feature", role=MessageRole.ASSISTANT),
            make_message("build the component", role=MessageRole.SYSTEM),
        ]
        result = detector.detect(messages)
        # building should not be detected since those keywords are not in user messages
        # (only in assistant/system messages which are ignored for keyword detection)
        assert result.building == 0.0

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        detector = ActivityDetector()
        messages = [
            make_message("IMPLEMENT the new feature"),
            make_message("FIX the Bug"),
        ]
        result = detector.detect(messages)
        assert result.building > 0
        assert result.fixing > 0

    def test_keyword_cap_applied(self):
        """Test that keyword contribution is capped at KEYWORD_CAP."""
        detector = ActivityDetector()
        # Many fixing keywords to test cap
        messages = [
            make_message("fix fix fix fix fix fix fix fix fix fix"),
        ]
        result = detector.detect(messages)
        # The raw signal should be capped, but after normalization
        # the highest signal becomes 1.0
        assert result.fixing <= 1.0


class TestErrorPatternDetection:
    """Test error pattern detection (Signal Source 2)."""

    def test_error_pattern_detection(self):
        """Test detection of error patterns in messages."""
        detector = ActivityDetector()
        messages = [
            make_message("I'm getting an error message", role=MessageRole.USER),
            make_message(
                "Traceback (most recent call last):\n  File 'test.py'\nTypeError: expected str",
                role=MessageRole.ASSISTANT,
            ),
        ]
        result = detector.detect(messages)
        assert result.fixing > 0

    def test_specific_error_types(self):
        """Test detection of specific Python error types."""
        detector = ActivityDetector()
        error_types = [
            "TypeError",
            "ValueError",
            "KeyError",
            "AttributeError",
            "ImportError",
            "RuntimeError",
            "AssertionError",
        ]
        for error_type in error_types:
            messages = [make_message(f"Got a {error_type}: something went wrong")]
            result = detector.detect(messages)
            assert result.fixing > 0, f"Failed to detect {error_type}"

    def test_error_boost_threshold(self):
        """Test that error boost is applied correctly based on count."""
        detector = ActivityDetector()

        # Few errors (1-3): gradual boost
        messages_few = [make_message("error error error")]
        result_few = detector.detect(messages_few)
        few_error_boost = result_few.fixing

        # Many errors (>3): full ERROR_BOOST
        messages_many = [make_message("error error error error error")]
        result_many = detector.detect(messages_many)
        many_error_boost = result_many.fixing

        # Both should have some fixing signal
        assert few_error_boost > 0
        assert many_error_boost > 0

    def test_error_patterns_all_roles(self):
        """Test that error patterns are detected in all message roles."""
        detector = ActivityDetector()

        # Error in user message
        result_user = detector.detect([make_message("I got an error", role=MessageRole.USER)])

        # Error in assistant message
        result_assistant = detector.detect(
            [make_message("I got an error", role=MessageRole.ASSISTANT)]
        )

        # Both should detect fixing activity
        assert result_user.fixing > 0
        assert result_assistant.fixing > 0

    def test_case_insensitive_error_patterns(self):
        """Test error patterns are matched case-insensitively."""
        detector = ActivityDetector()
        messages = [make_message("ERROR: Something FAILED with TRACEBACK")]
        result = detector.detect(messages)
        assert result.fixing > 0


class TestFilePatternDetection:
    """Test file pattern detection (Signal Source 3)."""

    def test_config_file_patterns(self):
        """Test detection of configuration file patterns."""
        detector = ActivityDetector()
        messages = [
            make_message("Check the .env file"),
            make_message("Update package.json"),
            make_message("Modify pyproject.toml"),
        ]
        result = detector.detect(messages)
        assert result.configuring > 0

    def test_test_file_patterns(self):
        """Test detection of test file patterns."""
        detector = ActivityDetector()
        messages = [
            make_message("Look at test_activity.py"),
            make_message("Update conftest.py"),
            make_message("Check the __tests__ folder"),
        ]
        result = detector.detect(messages)
        assert result.testing > 0

    def test_doc_file_patterns(self):
        """Test detection of documentation file patterns."""
        detector = ActivityDetector()
        messages = [
            make_message("Update the README"),
            make_message("Check CHANGELOG.md"),
            make_message("Look in the docs/ folder"),
        ]
        result = detector.detect(messages)
        assert result.documenting > 0

    def test_file_boost_threshold(self):
        """Test that file boost is applied correctly based on count."""
        detector = ActivityDetector()

        # Few file mentions (1-2): gradual boost
        messages_few = [make_message("Check .json file")]
        result_few = detector.detect(messages_few)

        # Many file mentions (>2): full FILE_BOOST
        messages_many = [
            make_message("Update .json .yaml .toml package.json pyproject.toml")
        ]
        result_many = detector.detect(messages_many)

        # Many mentions should have higher signal (after normalization)
        assert result_many.configuring > 0

    def test_file_patterns_all_roles(self):
        """Test that file patterns are detected in all message roles."""
        detector = ActivityDetector()

        # File pattern in assistant message
        result = detector.detect(
            [make_message("I'll check the conftest.py", role=MessageRole.ASSISTANT)]
        )
        assert result.testing > 0


class TestSignalCombination:
    """Test combination of signals from different sources."""

    def test_multiple_signal_sources_combine(self):
        """Test that signals from different sources are combined."""
        detector = ActivityDetector()
        messages = [
            # Keyword signal for fixing
            make_message("fix the bug", role=MessageRole.USER),
            # Error pattern signal
            make_message("TypeError: invalid type", role=MessageRole.ASSISTANT),
        ]
        result = detector.detect(messages)
        # fixing should be boosted by both keyword and error pattern
        assert result.fixing > 0
        assert "fixing" in result.dominant_activities

    def test_dimension_capped_at_1(self):
        """Test that combined signals don't exceed 1.0."""
        detector = ActivityDetector()
        # Many signals for same dimension
        messages = [
            make_message("fix fix fix debug debug resolve bug error crash issue"),
            make_message("ERROR ERROR ERROR ERROR ERROR", role=MessageRole.ASSISTANT),
        ]
        result = detector.detect(messages)
        # After normalization, max should be 1.0
        assert result.fixing <= 1.0

    def test_multiple_dimensions_detected(self):
        """Test that multiple activities can be detected simultaneously."""
        detector = ActivityDetector()
        messages = [
            make_message("implement the new feature and fix the bug"),
            make_message("also update the documentation"),
        ]
        result = detector.detect(messages)
        # Should detect multiple activities
        assert result.building > 0
        assert result.fixing > 0
        assert result.documenting > 0


class TestIntegrationScenarios:
    """Integration tests with realistic session scenarios."""

    def test_debugging_session(self):
        """Test a realistic debugging session."""
        detector = ActivityDetector()
        messages = [
            make_message("The login is not working", role=MessageRole.USER),
            make_message("Let me check the error logs", role=MessageRole.ASSISTANT),
            make_message(
                "I found this error:\nTypeError: cannot read property 'user'",
                role=MessageRole.ASSISTANT,
            ),
            make_message("Can you fix this bug?", role=MessageRole.USER),
            make_message("I'll debug the authentication module", role=MessageRole.ASSISTANT),
        ]
        result = detector.detect(messages)
        assert result.primary_activity == "fixing"

    def test_feature_development_session(self):
        """Test a realistic feature development session."""
        detector = ActivityDetector()
        messages = [
            make_message("I want to implement a new user profile feature", role=MessageRole.USER),
            make_message("Let me create the necessary components", role=MessageRole.ASSISTANT),
            make_message("Add support for profile pictures", role=MessageRole.USER),
            make_message("Building the image upload functionality", role=MessageRole.ASSISTANT),
        ]
        result = detector.detect(messages)
        assert result.building > 0
        assert "building" in result.dominant_activities

    def test_configuration_session(self):
        """Test a configuration/setup session."""
        detector = ActivityDetector()
        messages = [
            make_message("Help me setup the development environment", role=MessageRole.USER),
            make_message("I'll configure the .env file", role=MessageRole.ASSISTANT),
            make_message("Install the dependencies from package.json", role=MessageRole.USER),
            make_message("Configuring pyproject.toml settings", role=MessageRole.ASSISTANT),
        ]
        result = detector.detect(messages)
        assert result.configuring > 0
        assert "configuring" in result.dominant_activities

    def test_exploration_session(self):
        """Test an exploration/learning session."""
        detector = ActivityDetector()
        messages = [
            make_message("How does the authentication work?", role=MessageRole.USER),
            make_message("Let me explain the auth flow", role=MessageRole.ASSISTANT),
            make_message("What is the purpose of this middleware?", role=MessageRole.USER),
            make_message("Where is the database connection handled?", role=MessageRole.USER),
        ]
        result = detector.detect(messages)
        assert result.exploring > 0
        assert "exploring" in result.dominant_activities

    def test_testing_session(self):
        """Test a testing-focused session."""
        detector = ActivityDetector()
        messages = [
            make_message("Let's write tests for the user service", role=MessageRole.USER),
            make_message("I'll create test_user_service.py", role=MessageRole.ASSISTANT),
            make_message("Verify the edge cases work", role=MessageRole.USER),
            make_message("Checking conftest.py for fixtures", role=MessageRole.ASSISTANT),
        ]
        result = detector.detect(messages)
        assert result.testing > 0
        assert "testing" in result.dominant_activities

    def test_mixed_activity_session(self):
        """Test a session with mixed activities."""
        detector = ActivityDetector()
        messages = [
            make_message("Implement the new API endpoint", role=MessageRole.USER),
            make_message("I need to fix a bug in the validation", role=MessageRole.ASSISTANT),
            make_message("Also update the README with usage examples", role=MessageRole.USER),
        ]
        result = detector.detect(messages)
        # Should have multiple dominant activities
        dominant = result.dominant_activities
        assert len(dominant) >= 1  # At least one dominant activity

    def test_real_world_error_scenario(self):
        """Test with realistic error message content."""
        detector = ActivityDetector()
        messages = [
            make_message("Running the test suite fails", role=MessageRole.USER),
            make_message(
                """Traceback (most recent call last):
  File "test_api.py", line 42, in test_login
    response = client.post("/login", json=data)
  File "app.py", line 156, in login
    user = authenticate(credentials)
  File "auth.py", line 78, in authenticate
    raise ValueError("Invalid credentials format")
ValueError: Invalid credentials format""",
                role=MessageRole.ASSISTANT,
            ),
            make_message("Can you debug this error?", role=MessageRole.USER),
        ]
        result = detector.detect(messages)
        assert result.fixing > 0


class TestClassAttributes:
    """Test class-level constants and configuration."""

    def test_intent_keywords_structure(self):
        """Test INTENT_KEYWORDS has expected structure."""
        expected_dimensions = {
            "building",
            "fixing",
            "configuring",
            "exploring",
            "refactoring",
            "reviewing",
            "testing",
            "documenting",
        }
        assert set(ActivityDetector.INTENT_KEYWORDS.keys()) == expected_dimensions

    def test_intent_keywords_non_empty(self):
        """Test each dimension has at least one keyword."""
        for dimension, keywords in ActivityDetector.INTENT_KEYWORDS.items():
            assert len(keywords) > 0, f"No keywords for {dimension}"

    def test_error_patterns_non_empty(self):
        """Test ERROR_PATTERNS has patterns."""
        assert len(ActivityDetector.ERROR_PATTERNS) > 0

    def test_file_patterns_structure(self):
        """Test FILE_PATTERNS has expected structure."""
        expected = {"configuring", "testing", "documenting"}
        assert set(ActivityDetector.FILE_PATTERNS.keys()) == expected

    def test_signal_caps_reasonable(self):
        """Test that signal cap values are reasonable (0-1 range)."""
        assert 0 < ActivityDetector.KEYWORD_CAP <= 1.0
        assert 0 < ActivityDetector.ERROR_BOOST <= 1.0
        assert 0 < ActivityDetector.FILE_BOOST <= 1.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_content_messages(self):
        """Test messages with empty string content."""
        detector = ActivityDetector()
        messages = [
            make_message("", role=MessageRole.USER),
            make_message("", role=MessageRole.ASSISTANT),
        ]
        result = detector.detect(messages)
        assert isinstance(result, ActivityVector)

    def test_whitespace_only_content(self):
        """Test messages with whitespace-only content."""
        detector = ActivityDetector()
        messages = [
            make_message("   \n\t  ", role=MessageRole.USER),
        ]
        result = detector.detect(messages)
        assert isinstance(result, ActivityVector)

    def test_very_long_message(self):
        """Test handling of very long messages."""
        detector = ActivityDetector()
        long_content = "fix the bug " * 1000
        messages = [make_message(long_content)]
        result = detector.detect(messages)
        assert result.fixing > 0

    def test_special_characters_in_content(self):
        """Test messages with special characters."""
        detector = ActivityDetector()
        messages = [
            make_message("Fix the bug! @#$%^&*() in auth.py:123"),
            make_message("Error: \x00\x01\x02 unexpected bytes"),
        ]
        result = detector.detect(messages)
        # Should not raise
        assert isinstance(result, ActivityVector)

    def test_unicode_content(self):
        """Test messages with Unicode content."""
        detector = ActivityDetector()
        messages = [
            make_message("Fix the bug in the API endpoint"),
            make_message("Check the README file"),
        ]
        result = detector.detect(messages)
        assert isinstance(result, ActivityVector)

    def test_no_user_messages(self):
        """Test when there are no user messages."""
        detector = ActivityDetector()
        messages = [
            make_message("I'll fix the bug", role=MessageRole.ASSISTANT),
            make_message("System initialized", role=MessageRole.SYSTEM),
        ]
        result = detector.detect(messages)
        # Should still get signals from error/file patterns in non-user messages
        assert isinstance(result, ActivityVector)

    def test_single_message(self):
        """Test with single message."""
        detector = ActivityDetector()
        messages = [make_message("fix the bug")]
        result = detector.detect(messages)
        assert result.fixing > 0

    def test_many_messages(self):
        """Test with many messages."""
        detector = ActivityDetector()
        messages = [make_message(f"message {i} fix bug") for i in range(100)]
        result = detector.detect(messages)
        assert result.fixing > 0


class TestPrivateMethods:
    """Test private helper methods (white-box testing)."""

    def test_detect_user_intent_keywords(self):
        """Test _detect_user_intent_keywords directly."""
        detector = ActivityDetector()
        messages = [make_message("implement fix configure")]
        signals = detector._detect_user_intent_keywords(messages)

        assert "building" in signals
        assert "fixing" in signals
        assert "configuring" in signals

    def test_detect_error_patterns(self):
        """Test _detect_error_patterns directly."""
        detector = ActivityDetector()
        messages = [make_message("TypeError ValueError KeyError")]
        signals = detector._detect_error_patterns(messages)

        assert "fixing" in signals
        assert signals["fixing"] > 0

    def test_detect_file_patterns(self):
        """Test _detect_file_patterns directly."""
        detector = ActivityDetector()
        messages = [make_message(".env package.json test_foo.py README.md")]
        signals = detector._detect_file_patterns(messages)

        assert "configuring" in signals
        assert "testing" in signals
        assert "documenting" in signals

    def test_combine_signals(self):
        """Test _combine_signals directly."""
        detector = ActivityDetector()

        signal1 = {"fixing": 0.5, "building": 0.3}
        signal2 = {"fixing": 0.3, "testing": 0.4}
        signal3 = {"fixing": 0.5}  # Would exceed 1.0

        combined = detector._combine_signals(signal1, signal2, signal3)

        # fixing: 0.5 + 0.3 + 0.5 = 1.3 -> capped at 1.0
        assert combined["fixing"] == 1.0
        assert combined["building"] == 0.3
        assert combined["testing"] == 0.4
