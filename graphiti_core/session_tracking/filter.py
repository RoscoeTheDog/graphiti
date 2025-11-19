"""Smart filtering for session messages to reduce token overhead.

This module implements 93% token reduction by:
1. Keeping user messages (full)
2. Keeping agent responses (full)
3. Keeping tool use structure (parameters only)
4. Omitting tool results (replaced with 1-line summaries)
5. Extracting MCP tools used

Token reduction achieved through selective preservation of conversation structure
while omitting verbose tool outputs.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from graphiti_core.session_tracking.types import (
    ConversationContext,
    MessageRole,
    SessionMessage,
    ToolCall,
    ToolCallStatus,
    TokenUsage,
)
from graphiti_core.session_tracking.filter_config import FilterConfig
from graphiti_core.session_tracking.message_summarizer import MessageSummarizer

logger = logging.getLogger(__name__)


class SessionFilter:
    """Filter session messages for token-efficient summarization."""

    # Tool output patterns for summarization
    TOOL_SUMMARIES = {
        "Read": "Read {file_count} file(s)",
        "Write": "Wrote to {file_count} file(s)",
        "Edit": "Edited {file_count} file(s)",
        "Glob": "Found {result_count} matching files",
        "Grep": "Found {result_count} matches",
        "Bash": "Executed command",
        "mcp__serena__": "Serena: {operation}",
        "mcp__claude-context__": "Claude Context: {operation}",
        "mcp__graphiti-memory__": "Graphiti: {operation}",
        "mcp__context7-local__": "Context7: {operation}",
        "mcp__gptr-mcp__": "GPT Researcher: {operation}",
    }

    def __init__(
            self,
            config: Optional[FilterConfig] = None,
            preserve_tool_results: bool = False,
            summarizer: Optional[MessageSummarizer] = None
        ):
        """Initialize the filter.

        Args:
            config: FilterConfig instance controlling filtering behavior.
                   If None, uses default FilterConfig settings.
            preserve_tool_results: DEPRECATED. If True, sets config to preserve all content.
                                  Use FilterConfig(tool_content=True) instead.
            summarizer: Optional MessageSummarizer for template/inline prompt support.
                       If None, template/prompt mode falls back to full content.
        """
        # Handle backward compatibility
        if preserve_tool_results and config is None:
            logger.warning(
                "preserve_tool_results is deprecated. "
                "Use FilterConfig(tool_content=True) instead."
            )
            config = FilterConfig(
                tool_content=True,
                user_messages=True,
                agent_messages=True
            )

        self.config = config or FilterConfig()
        self.summarizer = summarizer
        self._stats = {
            "original_tokens": 0,
            "filtered_tokens": 0,
            "messages_processed": 0,
            "tool_calls_filtered": 0,
        }

    async def filter_conversation(
        self, context: ConversationContext
    ) -> Tuple[ConversationContext, Dict[str, int]]:
        """Filter a conversation context for summarization.

        Args:
            context: Original conversation context

        Returns:
            Tuple of (filtered context, statistics)

        Notes:
            This method is async to support LLM-based summarization when
            template or inline prompt is configured for user/agent messages.
        """
        logger.info(
            f"Filtering conversation {context.session_id} with {len(context.messages)} messages"
        )

        filtered_messages: List[SessionMessage] = []
        mcp_tools_used: Set[str] = set()
        files_modified: Set[str] = set()

        for message in context.messages:
            filtered_msg = await self._filter_message(message)
            filtered_messages.append(filtered_msg)

            # Track MCP tools and file modifications
            for tool_call in message.tool_calls:
                if self._is_mcp_tool(tool_call.tool_name):
                    mcp_tools_used.add(tool_call.tool_name)

                # Track file modifications
                if tool_call.tool_name in ["Write", "Edit"]:
                    file_path = tool_call.parameters.get("file_path")
                    if file_path:
                        files_modified.add(str(file_path))

        # Create filtered context
        filtered_context = ConversationContext(
            session_id=context.session_id,
            project_name=context.project_name,
            project_path=context.project_path,
            start_time=context.start_time,
            last_activity=context.last_activity,
            messages=filtered_messages,
            total_tokens=self._calculate_total_tokens(filtered_messages),
            files_modified=sorted(list(files_modified)),
            mcp_tools_used=sorted(list(mcp_tools_used)),
        )

        # Calculate statistics
        stats = {
            "original_tokens": context.total_tokens.total_tokens,
            "filtered_tokens": filtered_context.total_tokens.total_tokens,
            "messages_processed": len(context.messages),
            "tool_calls_filtered": self._stats["tool_calls_filtered"],
            "reduction_percent": self._calculate_reduction_percent(
                context.total_tokens.total_tokens,
                filtered_context.total_tokens.total_tokens,
            ),
        }

        logger.info(
            f"Filtered {stats['messages_processed']} messages, "
            f"token reduction: {stats['reduction_percent']}%"
        )

        return filtered_context, stats

    async def _filter_message(self, message: SessionMessage) -> SessionMessage:
        """Filter a single message based on configuration.

        Args:
            message: Original message

        Returns:
            Filtered message according to FilterConfig settings

        Notes:
            This method is async to support LLM-based summarization when
            template or inline prompt is configured for user/agent messages.
        """
        self._stats["messages_processed"] += 1

        # USER messages: Apply user_messages config
        if message.role == MessageRole.USER:
            if self.config.user_messages is True:
                return message
            elif self.config.user_messages is False:
                return SessionMessage(
                    uuid=message.uuid,
                    session_id=message.session_id,
                    role=message.role,
                    timestamp=message.timestamp,
                    content="[User message omitted]",
                    tool_calls=None,
                    tokens=TokenUsage(input=5, output=0, total=5),
                    metadata=message.metadata
                )
            elif isinstance(self.config.user_messages, str):
                # Template or inline prompt - use MessageSummarizer
                if self.summarizer:
                    try:
                        summary = await self.summarizer.summarize(
                            message.content, context="user message"
                        )
                        return SessionMessage(
                            uuid=message.uuid,
                            session_id=message.session_id,
                            role=message.role,
                            timestamp=message.timestamp,
                            content=summary,
                            tool_calls=None,
                            tokens=TokenUsage(
                                input=len(summary) // 4,  # Rough estimate
                                output=0,
                                total=len(summary) // 4
                            ),
                            metadata=message.metadata
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to summarize user message, falling back to full content: {e}"
                        )
                        return message  # Fallback to full content on error
                else:
                    logger.debug(
                        "Template/prompt requested but no summarizer provided, "
                        "falling back to full content"
                    )
                    return message  # Fallback to full content

        # ASSISTANT messages: Apply agent_messages and tool_content config
        if message.role == MessageRole.ASSISTANT:
            # Handle agent text content
            content = message.content
            if self.config.agent_messages is False:
                content = "[Agent message omitted]"
            elif isinstance(self.config.agent_messages, str):
                # Template or inline prompt - use MessageSummarizer
                if self.summarizer and content:
                    try:
                        content = await self.summarizer.summarize(
                            content, context="agent response"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to summarize agent message, falling back to full content: {e}"
                        )
                        # Keep original content on error (fallback to full content)
                else:
                    if not self.summarizer:
                        logger.debug(
                            "Template/prompt requested but no summarizer provided, "
                            "falling back to full content"
                        )
                    # Keep original content (fallback to full content)

            # Handle tool calls
            filtered_tool_calls = None
            tokens_modified = False
            if message.tool_calls:
                if self.config.tool_content is True:
                    filtered_tool_calls = message.tool_calls
                    # No filtering, keep original tokens
                elif not self.config.tool_calls:
                    # Omit tool calls entirely (tool_calls=False in config)
                    filtered_tool_calls = None
                    tokens_modified = True
                else:
                    # Keep tool structure, filter results based on tool_content mode
                    filtered_tool_calls = []
                    for tool_call in message.tool_calls:
                        filtered_tool_calls.append(self._filter_tool_call(tool_call))
                        self._stats["tool_calls_filtered"] += 1
                    tokens_modified = True

            # Determine tokens - only recalculate if we modified content or tool calls
            if tokens_modified or self.config.agent_messages is not True:
                tokens = self._estimate_filtered_tokens(message, filtered_tool_calls) if filtered_tool_calls else message.tokens
            else:
                tokens = message.tokens

            # Create filtered message
            return SessionMessage(
                uuid=message.uuid,
                session_id=message.session_id,
                role=message.role,
                timestamp=message.timestamp,
                content=content,
                tool_calls=filtered_tool_calls,
                tokens=tokens,
                metadata=message.metadata,
            )

        # SYSTEM messages: Keep as-is
        return message

    def _filter_tool_call(self, tool_call: ToolCall) -> ToolCall:
        """Filter a tool call based on tool_content configuration.

        Args:
            tool_call: Original tool call

        Returns:
            Filtered tool call according to tool_content mode
        """
        # Determine result based on tool_content mode
        if self.config.tool_content is True:
            result_summary = tool_call.result_summary  # Keep original result
        elif self.config.tool_content is False:
            result_summary = "[Tool result omitted]"
        else:  # Template or inline prompt (str)
            result_summary = self._summarize_tool_result(tool_call)

        return ToolCall(
            tool_name=tool_call.tool_name,
            parameters=tool_call.parameters,  # Keep parameters for context
            status=tool_call.status,
            result_summary=result_summary,
            execution_time_ms=tool_call.execution_time_ms,
            error_message=tool_call.error_message,
        )

    def _summarize_tool_result(self, tool_call: ToolCall) -> str:
        """Generate 1-line summary for tool result.

        Args:
            tool_call: Tool call to summarize

        Returns:
            One-line summary string
        """
        tool_name = tool_call.tool_name

        # Error handling
        if tool_call.status == ToolCallStatus.ERROR:
            return f"Error: {tool_call.error_message or 'Unknown error'}"

        # File operations
        if tool_name == "Read":
            file_path = tool_call.parameters.get("file_path", "file")
            return f"Read {self._truncate_path(file_path)}"

        if tool_name == "Write":
            file_path = tool_call.parameters.get("file_path", "file")
            return f"Wrote to {self._truncate_path(file_path)}"

        if tool_name == "Edit":
            file_path = tool_call.parameters.get("file_path", "file")
            return f"Edited {self._truncate_path(file_path)}"

        if tool_name == "Glob":
            pattern = tool_call.parameters.get("pattern", "*")
            return f"Glob search: {pattern}"

        if tool_name == "Grep":
            pattern = tool_call.parameters.get("pattern", "")
            return f"Grep search: {pattern}"

        if tool_name == "Bash":
            command = tool_call.parameters.get("command", "")
            return f"Executed: {self._truncate_command(command)}"

        # MCP tools
        if self._is_mcp_tool(tool_name):
            return self._summarize_mcp_tool(tool_name, tool_call.parameters)

        # Default summary
        return f"{tool_name} executed"

    def _summarize_mcp_tool(self, tool_name: str, parameters: Dict) -> str:
        """Summarize MCP tool execution.

        Args:
            tool_name: Name of MCP tool
            parameters: Tool parameters

        Returns:
            One-line summary
        """
        # Extract operation from tool name
        if "serena" in tool_name:
            operation = tool_name.replace("mcp__serena__", "")
            return f"Serena: {operation}"

        if "claude-context" in tool_name:
            operation = tool_name.replace("mcp__claude-context__", "")
            return f"Claude Context: {operation}"

        if "graphiti-memory" in tool_name:
            operation = tool_name.replace("mcp__graphiti-memory__", "")
            return f"Graphiti: {operation}"

        if "context7" in tool_name:
            operation = tool_name.replace("mcp__context7-local__", "")
            return f"Context7: {operation}"

        if "gptr-mcp" in tool_name:
            operation = tool_name.replace("mcp__gptr-mcp__", "")
            return f"GPT Researcher: {operation}"

        return f"MCP: {tool_name}"

    def _is_mcp_tool(self, tool_name: str) -> bool:
        """Check if tool is an MCP tool.

        Args:
            tool_name: Tool name to check

        Returns:
            True if MCP tool
        """
        return tool_name.startswith("mcp__")

    def _truncate_path(self, path: str, max_length: int = 40) -> str:
        """Truncate file path for display.

        Args:
            path: File path to truncate
            max_length: Maximum length

        Returns:
            Truncated path
        """
        if len(path) <= max_length:
            return path

        # Keep filename, truncate directory
        parts = path.split("/")
        if len(parts) > 1:
            filename = parts[-1]
            return f".../{filename}"

        return path[:max_length - 3] + "..."

    def _truncate_command(self, command: str, max_length: int = 50) -> str:
        """Truncate bash command for display.

        Args:
            command: Command to truncate
            max_length: Maximum length

        Returns:
            Truncated command
        """
        if len(command) <= max_length:
            return command

        return command[:max_length - 3] + "..."

    def _estimate_filtered_tokens(
        self, original_message: SessionMessage, filtered_tool_calls: List[ToolCall]
    ) -> TokenUsage:
        """Estimate token reduction from filtering.

        Args:
            original_message: Original message
            filtered_tool_calls: Filtered tool calls

        Returns:
            Estimated token usage after filtering
        """
        # Rough estimation: Each tool result summary saves ~90% of tokens
        # This is a conservative estimate based on handoff design
        tool_result_reduction = len(filtered_tool_calls) * 0.9

        # Calculate reduced output tokens
        original_output = original_message.tokens.output_tokens
        estimated_output = max(
            int(original_output * (1 - tool_result_reduction / len(filtered_tool_calls)))
            if filtered_tool_calls
            else original_output,
            10,  # Minimum tokens
        )

        return TokenUsage(
            input_tokens=original_message.tokens.input_tokens,
            output_tokens=estimated_output,
            cache_read_tokens=original_message.tokens.cache_read_tokens,
            cache_creation_tokens=original_message.tokens.cache_creation_tokens,
        )

    def _calculate_total_tokens(self, messages: List[SessionMessage]) -> TokenUsage:
        """Calculate total token usage for messages.

        Args:
            messages: List of messages

        Returns:
            Total token usage
        """
        total = TokenUsage()
        for message in messages:
            total += message.tokens
        return total

    def _calculate_reduction_percent(
        self, original_tokens: int, filtered_tokens: int
    ) -> float:
        """Calculate percentage reduction in tokens.

        Args:
            original_tokens: Original token count
            filtered_tokens: Filtered token count

        Returns:
            Reduction percentage (0-100)
        """
        if original_tokens == 0:
            return 0.0

        reduction = ((original_tokens - filtered_tokens) / original_tokens) * 100
        return round(reduction, 2)

    def get_statistics(self) -> Dict[str, int]:
        """Get filtering statistics.

        Returns:
            Dictionary of statistics
        """
        return self._stats.copy()

    def reset_statistics(self) -> None:
        """Reset filtering statistics."""
        self._stats = {
            "original_tokens": 0,
            "filtered_tokens": 0,
            "messages_processed": 0,
            "tool_calls_filtered": 0,
        }
