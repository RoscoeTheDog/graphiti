"""Parse Claude Code JSONL conversation files.

This module provides a parser for Claude Code's JSONL conversation format,
extracting messages, tool calls, and token usage information.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .types import MessageRole, SessionMessage, ToolCall, ToolCallStatus, TokenUsage

logger = logging.getLogger(__name__)


class JSONLParser:
    """Parse Claude Code JSONL conversation files."""

    def __init__(self, extract_tool_calls: bool = True, store_content: bool = True):
        """Initialize parser.

        Args:
            extract_tool_calls: Whether to extract tool call information from messages
            store_content: Whether to extract and store full message content
        """
        self.extract_tool_calls = extract_tool_calls
        self.store_content = store_content

    def parse_line(self, line: str) -> Optional[SessionMessage]:
        """Parse a single JSONL line.

        Args:
            line: JSONL string to parse

        Returns:
            SessionMessage if parsing successful, None otherwise
        """
        try:
            data = json.loads(line.strip())
            return self.parse_message(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSONL line: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing message: {e}", exc_info=True)
            return None

    def parse_message(self, data: Dict[str, Any]) -> Optional[SessionMessage]:
        """Parse a message dictionary.

        Args:
            data: Parsed JSONL dictionary

        Returns:
            SessionMessage if message is valid, None otherwise
        """
        # Extract required fields
        uuid = data.get("uuid")
        session_id = data.get("sessionId")
        message = data.get("message", {})

        # Skip if missing required fields
        if not uuid or not session_id or not message:
            return None

        # Extract role
        role_str = message.get("role")
        if not role_str:
            return None

        try:
            role = MessageRole(role_str)
        except ValueError:
            logger.warning(f"Unknown message role: {role_str}")
            return None

        # Extract timestamp
        timestamp = self._parse_timestamp(data.get("timestamp"))

        # Extract token usage
        usage = message.get("usage", {})
        tokens = self._extract_tokens(usage)

        # Extract content if configured
        content = None
        if self.store_content:
            content = self._extract_content(message.get("content"))

        # Extract tool calls if configured
        tool_calls = []
        if self.extract_tool_calls:
            tool_calls = self._extract_tool_calls(message.get("content", []))

        # Extract metadata
        metadata = {
            "type": data.get("type"),
        }

        return SessionMessage(
            uuid=uuid,
            session_id=session_id,
            role=role,
            timestamp=timestamp,
            content=content,
            tool_calls=tool_calls,
            tokens=tokens,
            metadata=metadata,
        )

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            Parsed datetime, or current time if parsing fails
        """
        if not timestamp_str:
            return datetime.now()

        try:
            # Parse ISO format timestamp
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return datetime.now()

    def _extract_tokens(self, usage: Dict[str, Any]) -> TokenUsage:
        """Extract token counts from usage dictionary.

        Args:
            usage: Usage dictionary from message

        Returns:
            TokenUsage object
        """
        return TokenUsage(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
        )

    def _extract_content(self, content: Any) -> Optional[str]:
        """Extract text content from message content.

        Args:
            content: Message content (can be string, list, or dict)

        Returns:
            Extracted text or None
        """
        if not content:
            return None

        # If content is a string, return it
        if isinstance(content, str):
            return content

        # If content is a list, extract text from text blocks
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            return "\n".join(text_parts) if text_parts else None

        # If content is a dict, try to extract text
        if isinstance(content, dict):
            return content.get("text") or content.get("content")

        return None

    def _extract_tool_calls(self, content: Any) -> List[ToolCall]:
        """Extract tool call information from message content.

        Args:
            content: Message content (typically a list of content blocks)

        Returns:
            List of ToolCall objects
        """
        tool_calls = []

        if not isinstance(content, list):
            return tool_calls

        for item in content:
            if not isinstance(item, dict):
                continue

            # Check if this is a tool use block
            if item.get("type") == "tool_use":
                tool_name = item.get("name", "unknown")
                parameters = item.get("input", {})

                # Create basic tool call (status will be updated when result is seen)
                tool_call = ToolCall(
                    tool_name=tool_name,
                    parameters=parameters,
                    status=ToolCallStatus.SUCCESS,  # Default to success
                )

                tool_calls.append(tool_call)

            # Check if this is a tool result block (for error detection)
            elif item.get("type") == "tool_result":
                # Extract error information if present
                is_error = item.get("is_error", False)
                content_data = item.get("content")

                # If we have a matching tool call, update its status
                if is_error and tool_calls:
                    # Find most recent tool call (simple heuristic)
                    tool_calls[-1].status = ToolCallStatus.ERROR
                    tool_calls[-1].error_message = self._extract_content(content_data)

        return tool_calls

    def parse_file(
        self, file_path: str, start_offset: int = 0
    ) -> Tuple[List[SessionMessage], int]:
        """Parse a JSONL file from a given offset.

        Args:
            file_path: Path to JSONL file
            start_offset: Byte offset to start reading from

        Returns:
            Tuple of (list of SessionMessage, new offset)
        """
        messages = []
        new_offset = start_offset

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Seek to start offset
                f.seek(start_offset)

                # Read and parse lines
                for line in f:
                    message = self.parse_line(line)
                    if message:
                        messages.append(message)

                # Get new offset
                new_offset = f.tell()

        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)

        return messages, new_offset

    def parse_file_incremental(
        self, file_path: str, start_offset: int = 0
    ) -> Tuple[List[SessionMessage], int]:
        """Parse new content from a JSONL file (alias for parse_file).

        This method is an alias for parse_file to match the incremental
        reading pattern used in file watchers.

        Args:
            file_path: Path to JSONL file
            start_offset: Byte offset to start reading from

        Returns:
            Tuple of (list of SessionMessage, new offset)
        """
        return self.parse_file(file_path, start_offset)
