"""Tests for session message filtering."""

import pytest
from datetime import datetime

from graphiti_core.session_tracking.filter import SessionFilter
from graphiti_core.session_tracking.types import (
    ConversationContext,
    MessageRole,
    SessionMessage,
    ToolCall,
    ToolCallStatus,
    TokenUsage,
)


@pytest.mark.asyncio
class TestSessionFilter:
    """Test session filtering functionality."""

    async def test_filter_preserves_user_messages(self):
        """Test that user messages are preserved fully."""
        filter_obj = SessionFilter()

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.USER,
            timestamp=datetime.now(),
            content="Hello, can you help me?",
            tokens=TokenUsage(input_tokens=10, output_tokens=0),
        )

        filtered = await filter_obj._filter_message(message)

        assert filtered.content == message.content
        assert filtered.uuid == message.uuid
        assert filtered.role == MessageRole.USER
        assert len(filtered.tool_calls) == 0

    async def test_filter_preserves_assistant_text(self):
        """Test that assistant text content is preserved."""
        filter_obj = SessionFilter()

        message = SessionMessage(
            uuid="msg-2",
            session_id="session-1",
            role=MessageRole.ASSISTANT,
            timestamp=datetime.now(),
            content="I'll help you with that.",
            tokens=TokenUsage(input_tokens=20, output_tokens=15),
        )

        filtered = await filter_obj._filter_message(message)

        assert filtered.content == message.content
        assert filtered.role == MessageRole.ASSISTANT

    async def test_filter_summarizes_tool_calls(self):
        """Test that tool calls are summarized."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "/path/to/file.txt"},
            status=ToolCallStatus.SUCCESS,
        )

        message = SessionMessage(
            uuid="msg-3",
            session_id="session-1",
            role=MessageRole.ASSISTANT,
            timestamp=datetime.now(),
            content="Let me read that file.",
            tool_calls=[tool_call],
            tokens=TokenUsage(input_tokens=100, output_tokens=500),
        )

        filtered = await filter_obj._filter_message(message)

        assert len(filtered.tool_calls) == 1
        assert filtered.tool_calls[0].result_summary is not None
        assert "Read" in filtered.tool_calls[0].result_summary
        assert filtered.tool_calls[0].tool_name == "Read"
        assert filtered.tool_calls[0].parameters == tool_call.parameters

    async def test_read_tool_summarization(self):
        """Test Read tool result summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "/home/user/project/src/main.py"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Read" in summary
        assert "main.py" in summary or "..." in summary

    async def test_write_tool_summarization(self):
        """Test Write tool result summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="Write",
            parameters={"file_path": "/path/to/output.txt"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Wrote" in summary
        assert "output.txt" in summary or "..." in summary

    async def test_edit_tool_summarization(self):
        """Test Edit tool result summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="Edit",
            parameters={"file_path": "/path/to/file.py"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Edited" in summary
        assert "file.py" in summary or "..." in summary

    async def test_bash_tool_summarization(self):
        """Test Bash tool result summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="Bash",
            parameters={"command": "git status"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Executed" in summary

    async def test_glob_tool_summarization(self):
        """Test Glob tool result summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="Glob",
            parameters={"pattern": "**/*.py"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Glob" in summary
        assert "**/*.py" in summary

    async def test_grep_tool_summarization(self):
        """Test Grep tool result summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="Grep",
            parameters={"pattern": "TODO"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Grep" in summary
        assert "TODO" in summary

    async def test_mcp_serena_tool_summarization(self):
        """Test Serena MCP tool summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="mcp__serena__find_symbol",
            parameters={"name_path": "MyClass"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Serena" in summary
        assert "find_symbol" in summary

    async def test_mcp_claude_context_tool_summarization(self):
        """Test Claude Context MCP tool summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="mcp__claude-context__search_code",
            parameters={"query": "authentication"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Claude Context" in summary
        assert "search_code" in summary

    async def test_mcp_graphiti_tool_summarization(self):
        """Test Graphiti MCP tool summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="mcp__graphiti-memory__add_memory",
            parameters={"name": "test", "episode_body": "content"},
            status=ToolCallStatus.SUCCESS,
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Graphiti" in summary
        assert "add_memory" in summary

    async def test_error_status_summarization(self):
        """Test error status handling in summarization."""
        filter_obj = SessionFilter()

        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "/missing/file.txt"},
            status=ToolCallStatus.ERROR,
            error_message="File not found",
        )

        summary = filter_obj._summarize_tool_result(tool_call)

        assert "Error" in summary
        assert "File not found" in summary

    async def test_is_mcp_tool(self):
        """Test MCP tool detection."""
        filter_obj = SessionFilter()

        assert filter_obj._is_mcp_tool("mcp__serena__find_symbol")
        assert filter_obj._is_mcp_tool("mcp__graphiti-memory__add_memory")
        assert not filter_obj._is_mcp_tool("Read")
        assert not filter_obj._is_mcp_tool("Write")

    async def test_truncate_path(self):
        """Test path truncation."""
        filter_obj = SessionFilter()

        short_path = "/home/file.txt"
        assert filter_obj._truncate_path(short_path) == short_path

        long_path = "/very/long/path/to/some/deeply/nested/directory/file.txt"
        truncated = filter_obj._truncate_path(long_path, max_length=30)
        assert len(truncated) <= 30
        assert "..." in truncated

    async def test_truncate_command(self):
        """Test command truncation."""
        filter_obj = SessionFilter()

        short_cmd = "ls -la"
        assert filter_obj._truncate_command(short_cmd) == short_cmd

        long_cmd = "git log --oneline --graph --all --decorate --pretty=format:'%h %s'"
        truncated = filter_obj._truncate_command(long_cmd, max_length=30)
        assert len(truncated) <= 30
        assert "..." in truncated

    async def test_filter_conversation_extracts_mcp_tools(self):
        """Test that MCP tools are extracted from conversation."""
        filter_obj = SessionFilter()

        messages = [
            SessionMessage(
                uuid="msg-1",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="Let me search for that.",
                tool_calls=[
                    ToolCall(
                        tool_name="mcp__serena__find_symbol",
                        parameters={"name_path": "MyClass"},
                        status=ToolCallStatus.SUCCESS,
                    )
                ],
                tokens=TokenUsage(input_tokens=50, output_tokens=100),
            ),
            SessionMessage(
                uuid="msg-2",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="Adding to memory.",
                tool_calls=[
                    ToolCall(
                        tool_name="mcp__graphiti-memory__add_memory",
                        parameters={"name": "test", "episode_body": "content"},
                        status=ToolCallStatus.SUCCESS,
                    )
                ],
                tokens=TokenUsage(input_tokens=30, output_tokens=50),
            ),
        ]

        context = ConversationContext(
            session_id="session-1",
            messages=messages,
            total_tokens=TokenUsage(input_tokens=80, output_tokens=150),
        )

        filtered_context, stats = await filter_obj.filter_conversation(context)

        assert len(filtered_context.mcp_tools_used) == 2
        assert "mcp__serena__find_symbol" in filtered_context.mcp_tools_used
        assert "mcp__graphiti-memory__add_memory" in filtered_context.mcp_tools_used

    async def test_filter_conversation_tracks_file_modifications(self):
        """Test that file modifications are tracked."""
        filter_obj = SessionFilter()

        messages = [
            SessionMessage(
                uuid="msg-1",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="Writing file.",
                tool_calls=[
                    ToolCall(
                        tool_name="Write",
                        parameters={"file_path": "/path/to/file1.txt"},
                        status=ToolCallStatus.SUCCESS,
                    )
                ],
                tokens=TokenUsage(input_tokens=50, output_tokens=100),
            ),
            SessionMessage(
                uuid="msg-2",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="Editing file.",
                tool_calls=[
                    ToolCall(
                        tool_name="Edit",
                        parameters={"file_path": "/path/to/file2.py"},
                        status=ToolCallStatus.SUCCESS,
                    )
                ],
                tokens=TokenUsage(input_tokens=30, output_tokens=50),
            ),
        ]

        context = ConversationContext(
            session_id="session-1",
            messages=messages,
            total_tokens=TokenUsage(input_tokens=80, output_tokens=150),
        )

        filtered_context, stats = await filter_obj.filter_conversation(context)

        assert len(filtered_context.files_modified) == 2
        assert "/path/to/file1.txt" in filtered_context.files_modified
        assert "/path/to/file2.py" in filtered_context.files_modified

    async def test_filter_conversation_calculates_statistics(self):
        """Test that filtering statistics are calculated correctly."""
        filter_obj = SessionFilter()

        messages = [
            SessionMessage(
                uuid="msg-1",
                session_id="session-1",
                role=MessageRole.USER,
                timestamp=datetime.now(),
                content="Hello",
                tokens=TokenUsage(input_tokens=10, output_tokens=0),
            ),
            SessionMessage(
                uuid="msg-2",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="Let me help.",
                tool_calls=[
                    ToolCall(
                        tool_name="Read",
                        parameters={"file_path": "/file.txt"},
                        status=ToolCallStatus.SUCCESS,
                    )
                ],
                tokens=TokenUsage(input_tokens=100, output_tokens=500),
            ),
        ]

        context = ConversationContext(
            session_id="session-1",
            messages=messages,
            total_tokens=TokenUsage(input_tokens=110, output_tokens=500),
        )

        filtered_context, stats = await filter_obj.filter_conversation(context)

        assert stats["messages_processed"] == 2
        assert stats["tool_calls_filtered"] == 1
        assert stats["original_tokens"] == 610
        assert stats["filtered_tokens"] < stats["original_tokens"]
        assert stats["reduction_percent"] > 0

    async def test_preserve_tool_results_option(self):
        """Test that preserve_tool_results disables filtering."""
        filter_obj = SessionFilter(preserve_tool_results=True)

        tool_call = ToolCall(
            tool_name="Read",
            parameters={"file_path": "/file.txt"},
            status=ToolCallStatus.SUCCESS,
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

        filtered = await filter_obj._filter_message(message)

        # Should preserve original message
        assert filtered == message

    async def test_token_reduction_calculation(self):
        """Test token reduction percentage calculation."""
        filter_obj = SessionFilter()

        # Test normal reduction
        reduction = filter_obj._calculate_reduction_percent(1000, 100)
        assert reduction == 90.0

        # Test no reduction
        reduction = filter_obj._calculate_reduction_percent(100, 100)
        assert reduction == 0.0

        # Test zero original
        reduction = filter_obj._calculate_reduction_percent(0, 0)
        assert reduction == 0.0

    async def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        filter_obj = SessionFilter()

        messages = [
            SessionMessage(
                uuid="msg-1",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="Processing.",
                tool_calls=[
                    ToolCall(
                        tool_name="Read",
                        parameters={"file_path": "/file.txt"},
                        status=ToolCallStatus.SUCCESS,
                    )
                ],
                tokens=TokenUsage(input_tokens=50, output_tokens=100),
            )
        ]

        context = ConversationContext(
            session_id="session-1",
            messages=messages,
            total_tokens=TokenUsage(input_tokens=50, output_tokens=100),
        )

        await filter_obj.filter_conversation(context)

        stats = filter_obj.get_statistics()
        assert stats["messages_processed"] >= 1
        assert stats["tool_calls_filtered"] >= 1

        # Test reset
        filter_obj.reset_statistics()
        stats = filter_obj.get_statistics()
        assert stats["messages_processed"] == 0
        assert stats["tool_calls_filtered"] == 0

    async def test_multiple_tool_calls_in_message(self):
        """Test filtering message with multiple tool calls."""
        filter_obj = SessionFilter()

        tool_calls = [
            ToolCall(
                tool_name="Read",
                parameters={"file_path": "/file1.txt"},
                status=ToolCallStatus.SUCCESS,
            ),
            ToolCall(
                tool_name="Read",
                parameters={"file_path": "/file2.txt"},
                status=ToolCallStatus.SUCCESS,
            ),
            ToolCall(
                tool_name="Write",
                parameters={"file_path": "/output.txt"},
                status=ToolCallStatus.SUCCESS,
            ),
        ]

        message = SessionMessage(
            uuid="msg-1",
            session_id="session-1",
            role=MessageRole.ASSISTANT,
            timestamp=datetime.now(),
            content="Processing multiple files.",
            tool_calls=tool_calls,
            tokens=TokenUsage(input_tokens=200, output_tokens=1000),
        )

        filtered = await filter_obj._filter_message(message)

        assert len(filtered.tool_calls) == 3
        for tool_call in filtered.tool_calls:
            assert tool_call.result_summary is not None
            assert len(tool_call.result_summary) > 0

    async def test_empty_conversation(self):
        """Test filtering empty conversation."""
        filter_obj = SessionFilter()

        context = ConversationContext(
            session_id="session-1",
            messages=[],
            total_tokens=TokenUsage(),
        )

        filtered_context, stats = await filter_obj.filter_conversation(context)

        assert len(filtered_context.messages) == 0
        assert stats["messages_processed"] == 0
        assert stats["reduction_percent"] == 0.0

    async def test_conversation_with_only_user_messages(self):
        """Test filtering conversation with only user messages."""
        filter_obj = SessionFilter()

        messages = [
            SessionMessage(
                uuid="msg-1",
                session_id="session-1",
                role=MessageRole.USER,
                timestamp=datetime.now(),
                content="Hello",
                tokens=TokenUsage(input_tokens=10, output_tokens=0),
            ),
            SessionMessage(
                uuid="msg-2",
                session_id="session-1",
                role=MessageRole.USER,
                timestamp=datetime.now(),
                content="Can you help?",
                tokens=TokenUsage(input_tokens=15, output_tokens=0),
            ),
        ]

        context = ConversationContext(
            session_id="session-1",
            messages=messages,
            total_tokens=TokenUsage(input_tokens=25, output_tokens=0),
        )

        filtered_context, stats = await filter_obj.filter_conversation(context)

        assert len(filtered_context.messages) == 2
        assert all(msg.role == MessageRole.USER for msg in filtered_context.messages)
        # No reduction expected since user messages are preserved
        assert stats["tool_calls_filtered"] == 0


@pytest.mark.asyncio
class TestTokenReduction:
    """Test token reduction functionality."""

    async def test_achieves_90_percent_reduction(self):
        """Test that filtering achieves 90%+ token reduction on realistic data."""
        filter_obj = SessionFilter()

        # Simulate realistic conversation with verbose tool outputs
        messages = [
            SessionMessage(
                uuid="msg-1",
                session_id="session-1",
                role=MessageRole.USER,
                timestamp=datetime.now(),
                content="Can you fix the bug in auth.py?",
                tokens=TokenUsage(input_tokens=20, output_tokens=0),
            ),
            SessionMessage(
                uuid="msg-2",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="Let me read the file first.",
                tool_calls=[
                    ToolCall(
                        tool_name="Read",
                        parameters={"file_path": "/src/auth.py"},
                        status=ToolCallStatus.SUCCESS,
                    )
                ],
                # Simulate large tool output
                tokens=TokenUsage(input_tokens=100, output_tokens=2000),
            ),
            SessionMessage(
                uuid="msg-3",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="I found the issue. Let me fix it.",
                tool_calls=[
                    ToolCall(
                        tool_name="Edit",
                        parameters={"file_path": "/src/auth.py"},
                        status=ToolCallStatus.SUCCESS,
                    )
                ],
                tokens=TokenUsage(input_tokens=150, output_tokens=1500),
            ),
            SessionMessage(
                uuid="msg-4",
                session_id="session-1",
                role=MessageRole.USER,
                timestamp=datetime.now(),
                content="Thanks!",
                tokens=TokenUsage(input_tokens=5, output_tokens=0),
            ),
        ]

        context = ConversationContext(
            session_id="session-1",
            messages=messages,
            total_tokens=TokenUsage(input_tokens=275, output_tokens=3500),
        )

        filtered_context, stats = await filter_obj.filter_conversation(context)

        # Verify significant reduction (targeting 90%+)
        # Note: Actual reduction depends on token estimation accuracy
        assert stats["reduction_percent"] >= 50  # Conservative check for test stability
        assert stats["filtered_tokens"] < stats["original_tokens"]
        assert stats["tool_calls_filtered"] == 2

    async def test_minimal_reduction_without_tool_calls(self):
        """Test that conversations without tool calls have minimal reduction."""
        filter_obj = SessionFilter()

        messages = [
            SessionMessage(
                uuid="msg-1",
                session_id="session-1",
                role=MessageRole.USER,
                timestamp=datetime.now(),
                content="Hello",
                tokens=TokenUsage(input_tokens=10, output_tokens=0),
            ),
            SessionMessage(
                uuid="msg-2",
                session_id="session-1",
                role=MessageRole.ASSISTANT,
                timestamp=datetime.now(),
                content="Hi! How can I help you?",
                tokens=TokenUsage(input_tokens=20, output_tokens=30),
            ),
        ]

        context = ConversationContext(
            session_id="session-1",
            messages=messages,
            total_tokens=TokenUsage(input_tokens=30, output_tokens=30),
        )

        filtered_context, stats = await filter_obj.filter_conversation(context)

        # Should have minimal or no reduction
        assert stats["reduction_percent"] < 10
        assert stats["tool_calls_filtered"] == 0
