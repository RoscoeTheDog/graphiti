"""Tests for JSONL parser."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from graphiti_core.session_tracking.parser import JSONLParser
from graphiti_core.session_tracking.types import MessageRole, ToolCallStatus


class TestJSONLParser:
    """Test JSONL parser functionality."""

    def test_parse_user_message(self):
        """Test parsing a simple user message."""
        parser = JSONLParser()

        jsonl_data = {
            "uuid": "msg-123",
            "sessionId": "session-456",
            "timestamp": "2025-11-13T08:00:00Z",
            "message": {
                "role": "user",
                "content": "Hello, how are you?",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 0,
                },
            },
        }

        jsonl_line = json.dumps(jsonl_data)
        message = parser.parse_line(jsonl_line)

        assert message is not None
        assert message.uuid == "msg-123"
        assert message.session_id == "session-456"
        assert message.role == MessageRole.USER
        assert message.content == "Hello, how are you?"
        assert message.tokens.input_tokens == 10
        assert message.tokens.output_tokens == 0
        assert message.tokens.total_tokens == 10

    def test_parse_assistant_message_with_tool_calls(self):
        """Test parsing assistant message with tool calls."""
        parser = JSONLParser(extract_tool_calls=True)

        jsonl_data = {
            "uuid": "msg-789",
            "sessionId": "session-456",
            "timestamp": "2025-11-13T08:01:00Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me read that file for you."},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/path/to/file.txt"},
                    },
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_read_input_tokens": 20,
                },
            },
        }

        jsonl_line = json.dumps(jsonl_data)
        message = parser.parse_line(jsonl_line)

        assert message is not None
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Let me read that file for you."
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0].tool_name == "Read"
        assert message.tool_calls[0].parameters == {"file_path": "/path/to/file.txt"}
        assert message.tokens.input_tokens == 100
        assert message.tokens.output_tokens == 50
        assert message.tokens.cache_read_tokens == 20

    def test_parse_message_with_cache_tokens(self):
        """Test parsing message with cache creation tokens."""
        parser = JSONLParser()

        jsonl_data = {
            "uuid": "msg-abc",
            "sessionId": "session-456",
            "timestamp": "2025-11-13T08:02:00Z",
            "message": {
                "role": "assistant",
                "content": "Here's the response.",
                "usage": {
                    "input_tokens": 50,
                    "output_tokens": 100,
                    "cache_creation_input_tokens": 30,
                    "cache_read_input_tokens": 10,
                },
            },
        }

        jsonl_line = json.dumps(jsonl_data)
        message = parser.parse_line(jsonl_line)

        assert message is not None
        assert message.tokens.input_tokens == 50
        assert message.tokens.output_tokens == 100
        assert message.tokens.cache_creation_tokens == 30
        assert message.tokens.cache_read_tokens == 10
        assert message.tokens.total_tokens == 190

    def test_parse_invalid_json(self):
        """Test handling of invalid JSON."""
        parser = JSONLParser()

        invalid_line = "this is not valid json {"
        message = parser.parse_line(invalid_line)

        assert message is None

    def test_parse_missing_required_fields(self):
        """Test handling of messages with missing required fields."""
        parser = JSONLParser()

        # Missing uuid
        jsonl_data = {
            "sessionId": "session-456",
            "message": {"role": "user", "content": "test"},
        }
        message = parser.parse_line(json.dumps(jsonl_data))
        assert message is None

        # Missing sessionId
        jsonl_data = {"uuid": "msg-123", "message": {"role": "user", "content": "test"}}
        message = parser.parse_line(json.dumps(jsonl_data))
        assert message is None

        # Missing role
        jsonl_data = {
            "uuid": "msg-123",
            "sessionId": "session-456",
            "message": {"content": "test"},
        }
        message = parser.parse_line(json.dumps(jsonl_data))
        assert message is None

    def test_parse_file_incremental(self):
        """Test incremental file parsing with offsets."""
        parser = JSONLParser()

        # Create temporary JSONL file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            file_path = f.name

            # Write first message
            msg1 = {
                "uuid": "msg-1",
                "sessionId": "session-1",
                "timestamp": "2025-11-13T08:00:00Z",
                "message": {
                    "role": "user",
                    "content": "First message",
                    "usage": {"input_tokens": 10, "output_tokens": 0},
                },
            }
            f.write(json.dumps(msg1) + "\n")
            first_offset = f.tell()

            # Write second message
            msg2 = {
                "uuid": "msg-2",
                "sessionId": "session-1",
                "timestamp": "2025-11-13T08:01:00Z",
                "message": {
                    "role": "assistant",
                    "content": "Second message",
                    "usage": {"input_tokens": 0, "output_tokens": 20},
                },
            }
            f.write(json.dumps(msg2) + "\n")

        try:
            # Parse from start
            messages, offset = parser.parse_file(file_path, start_offset=0)
            assert len(messages) == 2
            assert messages[0].uuid == "msg-1"
            assert messages[1].uuid == "msg-2"
            assert offset > 0

            # Parse from first offset (should only get second message)
            messages, offset = parser.parse_file(file_path, start_offset=first_offset)
            assert len(messages) == 1
            assert messages[0].uuid == "msg-2"

        finally:
            # Cleanup
            Path(file_path).unlink()

    def test_parse_tool_error(self):
        """Test parsing tool calls with error status."""
        parser = JSONLParser(extract_tool_calls=True)

        jsonl_data = {
            "uuid": "msg-err",
            "sessionId": "session-456",
            "timestamp": "2025-11-13T08:03:00Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me try to read that."},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/nonexistent.txt"},
                    },
                    {
                        "type": "tool_result",
                        "is_error": True,
                        "content": "File not found",
                    },
                ],
                "usage": {"input_tokens": 50, "output_tokens": 25},
            },
        }

        jsonl_line = json.dumps(jsonl_data)
        message = parser.parse_line(jsonl_line)

        assert message is not None
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0].status == ToolCallStatus.ERROR
        assert message.tool_calls[0].error_message == "File not found"

    def test_parse_content_without_storage(self):
        """Test that content is not stored when store_content=False."""
        parser = JSONLParser(store_content=False)

        jsonl_data = {
            "uuid": "msg-123",
            "sessionId": "session-456",
            "timestamp": "2025-11-13T08:00:00Z",
            "message": {
                "role": "user",
                "content": "This should not be stored",
                "usage": {"input_tokens": 10, "output_tokens": 0},
            },
        }

        message = parser.parse_line(json.dumps(jsonl_data))
        assert message is not None
        assert message.content is None

    def test_parse_complex_content_structure(self):
        """Test parsing complex content with multiple text blocks."""
        parser = JSONLParser()

        jsonl_data = {
            "uuid": "msg-complex",
            "sessionId": "session-456",
            "timestamp": "2025-11-13T08:04:00Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Here's the first part."},
                    {"type": "text", "text": "Here's the second part."},
                ],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        }

        message = parser.parse_line(json.dumps(jsonl_data))
        assert message is not None
        assert message.content == "Here's the first part.\nHere's the second part."

    def test_timestamp_parsing(self):
        """Test various timestamp formats."""
        parser = JSONLParser()

        # ISO format with Z
        jsonl_data = {
            "uuid": "msg-1",
            "sessionId": "session-1",
            "timestamp": "2025-11-13T08:00:00Z",
            "message": {
                "role": "user",
                "content": "test",
                "usage": {"input_tokens": 1, "output_tokens": 0},
            },
        }
        message = parser.parse_line(json.dumps(jsonl_data))
        assert message is not None
        assert isinstance(message.timestamp, datetime)

        # ISO format with timezone
        jsonl_data["timestamp"] = "2025-11-13T08:00:00+00:00"
        message = parser.parse_line(json.dumps(jsonl_data))
        assert message is not None
        assert isinstance(message.timestamp, datetime)

        # Missing timestamp (should use current time)
        jsonl_data.pop("timestamp")
        message = parser.parse_line(json.dumps(jsonl_data))
        assert message is not None
        assert isinstance(message.timestamp, datetime)
