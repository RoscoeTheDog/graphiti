"""Tests for FilterConfig and configurable filtering."""

import pytest
from datetime import datetime

from graphiti_core.session_tracking.filter import SessionFilter
from graphiti_core.session_tracking.filter_config import ContentMode, FilterConfig
from graphiti_core.session_tracking.types import (
    ConversationContext,
    MessageRole,
    SessionMessage,
    ToolCall,
    ToolCallStatus,
    TokenUsage,
)


class TestFilterConfig:
    """Test FilterConfig dataclass and methods."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FilterConfig()

        assert config.tool_calls is True
        assert config.tool_content == ContentMode.SUMMARY
        assert config.user_messages == ContentMode.FULL
        assert config.agent_messages == ContentMode.FULL

    def test_custom_config(self):
        """Test custom configuration."""
        config = FilterConfig(
            tool_calls=False,
            tool_content=ContentMode.OMIT,
            user_messages=ContentMode.SUMMARY,
            agent_messages=ContentMode.OMIT,
        )

        assert config.tool_calls is False
        assert config.tool_content == ContentMode.OMIT
        assert config.user_messages == ContentMode.SUMMARY
        assert config.agent_messages == ContentMode.OMIT

    def test_is_no_filtering(self):
        """Test is_no_filtering detection."""
        # Default config does some filtering (tool_content=SUMMARY)
        assert FilterConfig().is_no_filtering() is False

        # Full preservation config
        config = FilterConfig(
            tool_content=ContentMode.FULL,
            user_messages=ContentMode.FULL,
            agent_messages=ContentMode.FULL,
        )
        assert config.is_no_filtering() is True

    def test_is_aggressive_filtering(self):
        """Test aggressive filtering detection."""
        # Default config is not aggressive
        assert FilterConfig().is_aggressive_filtering() is False

        # OMIT modes are aggressive
        assert FilterConfig(tool_content=ContentMode.OMIT).is_aggressive_filtering() is True
        assert FilterConfig(user_messages=ContentMode.OMIT).is_aggressive_filtering() is True
        assert FilterConfig(agent_messages=ContentMode.OMIT).is_aggressive_filtering() is True

    def test_estimate_token_reduction(self):
        """Test token reduction estimation."""
        # Default: SUMMARY for tools only (~35% reduction)
        default_config = FilterConfig()
        assert 0.3 < default_config.estimate_token_reduction() < 0.4

        # No filtering (0% reduction)
        full_config = FilterConfig(
            tool_content=ContentMode.FULL,
            user_messages=ContentMode.FULL,
            agent_messages=ContentMode.FULL,
        )
        assert full_config.estimate_token_reduction() == 0.0

        # Aggressive filtering (OMIT all)
        omit_config = FilterConfig(
            tool_content=ContentMode.OMIT,
            user_messages=ContentMode.OMIT,
            agent_messages=ContentMode.OMIT,
        )
        assert omit_config.estimate_token_reduction() > 0.9


class TestSessionFilterWithConfig:
    """Test SessionFilter with FilterConfig."""

    def test_default_filter_config(self):
        """Test filter with default configuration."""
        filter_obj = SessionFilter()

        assert filter_obj.config is not None
        assert filter_obj.config.tool_content == ContentMode.SUMMARY

    def test_custom_filter_config(self):
        """Test filter with custom configuration."""
        config = FilterConfig(
            tool_content=ContentMode.OMIT,
            user_messages=ContentMode.FULL,
        )
        filter_obj = SessionFilter(config=config)

        assert filter_obj.config.tool_content == ContentMode.OMIT

    def test_preserve_tool_results_backward_compat(self):
        """Test backward compatibility with preserve_tool_results."""
        filter_obj = SessionFilter(preserve_tool_results=True)

        # Should create config with FULL modes
        assert filter_obj.config.tool_content == ContentMode.FULL
        assert filter_obj.config.user_messages == ContentMode.FULL
        assert filter_obj.config.agent_messages == ContentMode.FULL

    def test_tool_content_full_mode(self):
        """Test tool_content=FULL preserves original tool results."""
        config = FilterConfig(tool_content=ContentMode.FULL)
        filter_obj = SessionFilter(config=config)

        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "/file.txt"},
            status=ToolCallStatus.SUCCESS,
            result_summary="Original result content here...",
        )

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.ASSISTANT,
            timestamp=datetime.now(),
            content="Reading file.",
            tool_calls=[tool_call],
            tokens=TokenUsage(input_tokens=100, output_tokens=500),
        )

        filtered = filter_obj._filter_message(message)

        # Should preserve original result
        assert filtered.tool_calls is not None
        assert filtered.tool_calls[0].result_summary == "Original result content here..."
        assert filtered.tokens == message.tokens  # Tokens unchanged

    def test_tool_content_summary_mode(self):
        """Test tool_content=SUMMARY creates 1-line summaries."""
        config = FilterConfig(tool_content=ContentMode.SUMMARY)
        filter_obj = SessionFilter(config=config)

        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "/file.txt"},
            status=ToolCallStatus.SUCCESS,
            result_summary="Very long original result...",
        )

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.ASSISTANT,
            timestamp=datetime.now(),
            content="Reading file.",
            tool_calls=[tool_call],
            tokens=TokenUsage(input_tokens=100, output_tokens=500),
        )

        filtered = filter_obj._filter_message(message)

        # Should have 1-line summary
        assert filtered.tool_calls is not None
        assert "Read 1 file(s)" in filtered.tool_calls[0].result_summary

    def test_tool_content_omit_mode(self):
        """Test tool_content=OMIT removes tool results."""
        config = FilterConfig(tool_content=ContentMode.OMIT)
        filter_obj = SessionFilter(config=config)

        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "/file.txt"},
            status=ToolCallStatus.SUCCESS,
            result_summary="Original result",
        )

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.ASSISTANT,
            timestamp=datetime.now(),
            content="Reading file.",
            tool_calls=[tool_call],
            tokens=TokenUsage(input_tokens=100, output_tokens=500),
        )

        filtered = filter_obj._filter_message(message)

        # Should have omit placeholder
        assert filtered.tool_calls is not None
        assert filtered.tool_calls[0].result_summary == "[Tool result omitted]"

    def test_user_messages_full_mode(self):
        """Test user_messages=FULL preserves user content."""
        config = FilterConfig(user_messages=ContentMode.FULL)
        filter_obj = SessionFilter(config=config)

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.USER,
            timestamp=datetime.now(),
            content="User's detailed question here",
            tool_calls=None,
            tokens=TokenUsage(input_tokens=50, output_tokens=0),
        )

        filtered = filter_obj._filter_message(message)

        assert filtered.content == "User's detailed question here"

    def test_user_messages_omit_mode(self):
        """Test user_messages=OMIT removes user content."""
        config = FilterConfig(user_messages=ContentMode.OMIT)
        filter_obj = SessionFilter(config=config)

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.USER,
            timestamp=datetime.now(),
            content="User's detailed question here",
            tool_calls=None,
            tokens=TokenUsage(input_tokens=50, output_tokens=0),
        )

        filtered = filter_obj._filter_message(message)

        assert filtered.content == "[User message omitted]"

    def test_agent_messages_omit_mode(self):
        """Test agent_messages=OMIT removes agent text content."""
        config = FilterConfig(agent_messages=ContentMode.OMIT)
        filter_obj = SessionFilter(config=config)

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.ASSISTANT,
            timestamp=datetime.now(),
            content="Agent's detailed response here",
            tool_calls=None,
            tokens=TokenUsage(input_tokens=100, output_tokens=200),
        )

        filtered = filter_obj._filter_message(message)

        assert filtered.content == "[Agent message omitted]"

    def test_tool_calls_false_omits_all_tool_calls(self):
        """Test tool_calls=False removes tool calls entirely."""
        config = FilterConfig(tool_calls=False)
        filter_obj = SessionFilter(config=config)

        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "/file.txt"},
            status=ToolCallStatus.SUCCESS,
            result_summary="Original result",
        )

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.ASSISTANT,
            timestamp=datetime.now(),
            content="Reading file.",
            tool_calls=[tool_call],
            tokens=TokenUsage(input_tokens=100, output_tokens=500),
        )

        filtered = filter_obj._filter_message(message)

        # Tool calls should be completely removed
        assert filtered.tool_calls is None

    def test_combined_filtering_modes(self):
        """Test multiple filtering modes combined."""
        config = FilterConfig(
            tool_content=ContentMode.OMIT,
            user_messages=ContentMode.FULL,
            agent_messages=ContentMode.OMIT,
        )
        filter_obj = SessionFilter(config=config)

        context = ConversationContext(
            session_id="session-1",
            messages=[
                SessionMessage(
                    uuid="msg-1",
                    session_id="session-1",
                    role=MessageRole.USER,
                    timestamp=datetime.now(),
                    content="User question",
                    tool_calls=None,
                    tokens=TokenUsage(input_tokens=50, output_tokens=0),
                ),
                SessionMessage(
                    uuid="msg-2",
                    session_id="session-1",
                    role=MessageRole.ASSISTANT,
                    timestamp=datetime.now(),
                    content="Agent response",
                    tool_calls=[
                        ToolCall(
                            tool_name="Read",
                            parameters={"file_path": "/file.txt"},
                            status=ToolCallStatus.SUCCESS,
                            result_summary="Tool result",
                        )
                    ],
                    tokens=TokenUsage(input_tokens=100, output_tokens=500),
                ),
            ],
            metadata={},
        )

        filtered_context, stats = filter_obj.filter_conversation(context)

        # User message preserved
        assert filtered_context.messages[0].content == "User question"

        # Agent message content omitted
        assert filtered_context.messages[1].content == "[Agent message omitted]"

        # Tool result omitted
        assert filtered_context.messages[1].tool_calls[0].result_summary == "[Tool result omitted]"
