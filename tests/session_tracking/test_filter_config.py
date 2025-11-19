"""Tests for FilterConfig and configurable filtering with bool|str type system (Story 10)."""

import pytest
from datetime import datetime

from graphiti_core.session_tracking.filter import SessionFilter
from graphiti_core.session_tracking.filter_config import FilterConfig
from graphiti_core.session_tracking.types import (
    ConversationContext,
    MessageRole,
    SessionMessage,
    ToolCall,
    ToolCallStatus,
    TokenUsage,
)


class TestFilterConfig:
    """Test FilterConfig dataclass and bool|str type system."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FilterConfig()

        assert config.tool_calls is True
        assert config.tool_content == "default-tool-content.md"  # Template-based
        assert config.user_messages is True  # Preserve user intent
        assert config.agent_messages is True  # Preserve context continuity

    def test_custom_config_with_bool_values(self):
        """Test custom configuration with bool values."""
        config = FilterConfig(
            tool_calls=False,
            tool_content=False,  # Omit
            user_messages=True,  # Preserve
            agent_messages=False,  # Omit
        )

        assert config.tool_calls is False
        assert config.tool_content is False
        assert config.user_messages is True
        assert config.agent_messages is False

    def test_custom_config_with_template_paths(self):
        """Test custom configuration with template file paths."""
        config = FilterConfig(
            tool_content="custom-tool-template.md",
            user_messages="custom-user-template.md",
            agent_messages="custom-agent-template.md",
        )

        assert config.tool_content == "custom-tool-template.md"
        assert config.user_messages == "custom-user-template.md"
        assert config.agent_messages == "custom-agent-template.md"

    def test_custom_config_with_inline_prompts(self):
        """Test custom configuration with inline prompts."""
        config = FilterConfig(
            tool_content="Summarize this tool result briefly.",
            user_messages="Condense user message to key points.",
            agent_messages="Extract main idea from agent response.",
        )

        assert config.tool_content == "Summarize this tool result briefly."
        assert config.user_messages == "Condense user message to key points."
        assert config.agent_messages == "Extract main idea from agent response."

    def test_mixed_config_bool_and_str(self):
        """Test configuration with mixed bool and str values."""
        config = FilterConfig(
            tool_content="default-tool-content.md",  # Template
            user_messages=True,  # Preserve
            agent_messages=False,  # Omit
        )

        assert config.tool_content == "default-tool-content.md"
        assert config.user_messages is True
        assert config.agent_messages is False

    def test_is_no_filtering(self):
        """Test is_no_filtering detection with bool|str types."""
        # Default config does filtering (tool_content=template)
        assert FilterConfig().is_no_filtering() is False

        # Full preservation config (all True)
        config = FilterConfig(
            tool_content=True,
            user_messages=True,
            agent_messages=True,
        )
        assert config.is_no_filtering() is True

        # Any non-True value makes it not "no filtering"
        assert FilterConfig(tool_content=False).is_no_filtering() is False
        assert FilterConfig(tool_content="template.md").is_no_filtering() is False

    def test_is_aggressive_filtering(self):
        """Test aggressive filtering detection with bool|str types."""
        # Default config is not aggressive (template-based)
        assert FilterConfig().is_aggressive_filtering() is False

        # False (omit) modes are aggressive
        assert FilterConfig(tool_content=False).is_aggressive_filtering() is True
        assert FilterConfig(user_messages=False).is_aggressive_filtering() is True
        assert FilterConfig(agent_messages=False).is_aggressive_filtering() is True

        # True or str values are not aggressive
        assert FilterConfig(tool_content=True).is_aggressive_filtering() is False
        assert FilterConfig(tool_content="template.md").is_aggressive_filtering() is False

    def test_estimate_token_reduction(self):
        """Test token reduction estimation with bool|str types."""
        # Default: template for tools, preserve messages (~42% reduction)
        default_config = FilterConfig()
        assert 0.40 <= default_config.estimate_token_reduction() <= 0.45

        # No filtering (all True, 0% reduction)
        full_config = FilterConfig(
            tool_content=True,
            user_messages=True,
            agent_messages=True,
        )
        assert full_config.estimate_token_reduction() == 0.0

        # Aggressive filtering (False = omit all)
        omit_config = FilterConfig(
            tool_content=False,
            user_messages=False,
            agent_messages=False,
        )
        assert omit_config.estimate_token_reduction() > 0.9

        # Template-based (str values)
        template_config = FilterConfig(
            tool_content="custom.md",
            user_messages="user.md",
            agent_messages="agent.md",
        )
        # Tools: 60% * 0.7 + User: 15% * 0.5 + Agent: 25% * 0.5 = 0.42 + 0.075 + 0.125 = 0.62
        assert 0.60 <= template_config.estimate_token_reduction() <= 0.65

    def test_type_validation(self):
        """Test that Pydantic validates bool|str types correctly."""
        # Valid bool values
        config = FilterConfig(tool_content=True)
        assert config.tool_content is True

        config = FilterConfig(tool_content=False)
        assert config.tool_content is False

        # Valid str values
        config = FilterConfig(tool_content="template.md")
        assert config.tool_content == "template.md"

        config = FilterConfig(tool_content="Inline prompt here")
        assert config.tool_content == "Inline prompt here"

        # Invalid types should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            FilterConfig(tool_content=123)  # int not allowed

        with pytest.raises(Exception):  # Pydantic ValidationError
            FilterConfig(tool_content=None)  # None not allowed


@pytest.mark.asyncio
class TestSessionFilterWithBoolStrConfig:
    """Test SessionFilter with bool|str FilterConfig."""

    async def test_default_filter_config(self):
        """Test filter with default bool|str configuration."""
        filter_obj = SessionFilter()

        assert filter_obj.config is not None
        assert filter_obj.config.tool_content == "default-tool-content.md"
        assert filter_obj.config.user_messages is True
        assert filter_obj.config.agent_messages is True

    async def test_filter_with_omit_tool_content(self):
        """Test filter with tool_content=False (omit)."""
        config = FilterConfig(tool_content=False)
        filter_obj = SessionFilter(config=config)

        # Create test message with tool result
        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "test.py"},
            status=ToolCallStatus.SUCCESS,
            result_summary="File content here...",
        )
        message = SessionMessage(
            uuid="msg-1",
            session_id="sess-1",
            role=MessageRole.ASSISTANT,
            content="",
            tool_calls=[tool_call],
            timestamp=datetime.now(),
        )

        context = ConversationContext(messages=[message])
        filtered = await filter_obj.filter_conversation(context)

        # Tool result should be omitted
        assert len(filtered.messages) == 1
        assert filtered.messages[0].tool_calls[0].result_summary == ""  # Empty (omitted)

    async def test_filter_with_preserve_tool_content(self):
        """Test filter with tool_content=True (preserve)."""
        config = FilterConfig(tool_content=True)
        filter_obj = SessionFilter(config=config)

        # Create test message with tool result
        original_result = "File content here that should be preserved..."
        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "test.py"},
            status=ToolCallStatus.SUCCESS,
            result_summary=original_result,
        )
        message = SessionMessage(
            uuid="msg-1",
            session_id="sess-1",
            role=MessageRole.ASSISTANT,
            content="",
            tool_calls=[tool_call],
            timestamp=datetime.now(),
        )

        context = ConversationContext(messages=[message])
        filtered = await filter_obj.filter_conversation(context)

        # Tool result should be preserved
        assert len(filtered.messages) == 1
        assert filtered.messages[0].tool_calls[0].result_summary == original_result

    async def test_filter_with_omit_user_messages(self):
        """Test filter with user_messages=False (omit)."""
        config = FilterConfig(user_messages=False)
        filter_obj = SessionFilter(config=config)

        # Create user message
        message = SessionMessage(
            uuid="msg-1",
            session_id="sess-1",
            role=MessageRole.USER,
            content="This user message should be omitted",
            tool_calls=[],
            timestamp=datetime.now(),
        )

        context = ConversationContext(messages=[message])
        filtered = await filter_obj.filter_conversation(context)

        # User message content should be empty
        assert len(filtered.messages) == 1
        assert filtered.messages[0].content == ""

    async def test_filter_with_omit_agent_messages(self):
        """Test filter with agent_messages=False (omit)."""
        config = FilterConfig(agent_messages=False)
        filter_obj = SessionFilter(config=config)

        # Create agent message
        message = SessionMessage(
            uuid="msg-1",
            session_id="sess-1",
            role=MessageRole.ASSISTANT,
            content="This agent message should be omitted",
            tool_calls=[],
            timestamp=datetime.now(),
        )

        context = ConversationContext(messages=[message])
        filtered = await filter_obj.filter_conversation(context)

        # Agent message content should be empty
        assert len(filtered.messages) == 1
        assert filtered.messages[0].content == ""

    async def test_filter_resolution_logic(self):
        """Test that filter correctly interprets bool|str values."""
        # True = preserve
        config_preserve = FilterConfig(tool_content=True)
        assert config_preserve.tool_content is True

        # False = omit
        config_omit = FilterConfig(tool_content=False)
        assert config_omit.tool_content is False

        # str with .md = template
        config_template = FilterConfig(tool_content="my-template.md")
        assert config_template.tool_content == "my-template.md"
        assert isinstance(config_template.tool_content, str)

        # str without .md = inline prompt
        config_inline = FilterConfig(tool_content="Summarize this")
        assert config_inline.tool_content == "Summarize this"
        assert isinstance(config_inline.tool_content, str)
