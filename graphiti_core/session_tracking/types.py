"""Type definitions for session tracking.

This module provides dataclasses for session tracking functionality,
including message types, conversation context, and session metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageRole(str, Enum):
    """Role of a message in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ToolCallStatus(str, Enum):
    """Status of a tool call execution."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TokenUsage:
    """Token usage statistics for a message or session."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Calculate total token usage."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary representation."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "total_tokens": self.total_tokens,
        }

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage objects together."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_creation_tokens=self.cache_creation_tokens + other.cache_creation_tokens,
        )


@dataclass
class ToolCall:
    """Information about a tool call within a message."""

    tool_name: str
    """Name of the tool that was called."""

    parameters: Dict[str, Any] = field(default_factory=dict)
    """Parameters passed to the tool."""

    status: ToolCallStatus = ToolCallStatus.SUCCESS
    """Execution status of the tool call."""

    result_summary: Optional[str] = None
    """One-line summary of the tool result (for filtering)."""

    execution_time_ms: Optional[int] = None
    """Execution time in milliseconds."""

    error_message: Optional[str] = None
    """Error message if status is ERROR."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "status": self.status.value,
            "result_summary": self.result_summary,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
        }


@dataclass
class SessionMessage:
    """A single message in a conversation session."""

    uuid: str
    """Unique identifier for the message."""

    session_id: str
    """ID of the session this message belongs to."""

    role: MessageRole
    """Role of the message sender."""

    timestamp: datetime
    """When the message was created."""

    content: Optional[str] = None
    """Text content of the message."""

    tool_calls: List[ToolCall] = field(default_factory=list)
    """List of tool calls made in this message."""

    tokens: TokenUsage = field(default_factory=TokenUsage)
    """Token usage for this message."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for the message."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "uuid": self.uuid,
            "session_id": self.session_id,
            "role": self.role.value,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tokens": self.tokens.to_dict(),
            "metadata": self.metadata,
        }


@dataclass
class ConversationContext:
    """Context information for a conversation session."""

    session_id: str
    """Unique identifier for the session."""

    project_name: Optional[str] = None
    """Name of the project (if available)."""

    project_path: Optional[str] = None
    """Path to the project directory."""

    start_time: Optional[datetime] = None
    """When the session started."""

    last_activity: Optional[datetime] = None
    """Last activity timestamp."""

    messages: List[SessionMessage] = field(default_factory=list)
    """List of messages in the conversation."""

    total_tokens: TokenUsage = field(default_factory=TokenUsage)
    """Total token usage for the session."""

    files_modified: List[str] = field(default_factory=list)
    """List of files modified during the session."""

    mcp_tools_used: List[str] = field(default_factory=list)
    """List of MCP tools used during the session."""

    def add_message(self, message: SessionMessage) -> None:
        """Add a message to the conversation and update stats."""
        self.messages.append(message)
        self.total_tokens += message.tokens
        self.last_activity = message.timestamp

        if not self.start_time:
            self.start_time = message.timestamp

        # Track tool usage
        for tool_call in message.tool_calls:
            if tool_call.tool_name not in self.mcp_tools_used:
                self.mcp_tools_used.append(tool_call.tool_name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "project_path": self.project_path,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "message_count": len(self.messages),
            "total_tokens": self.total_tokens.to_dict(),
            "files_modified": self.files_modified,
            "mcp_tools_used": self.mcp_tools_used,
        }


@dataclass
class SessionMetadata:
    """Metadata for a completed session."""

    session_id: str
    """Unique identifier for the session."""

    summary: Optional[str] = None
    """LLM-generated summary of the session."""

    objective: Optional[str] = None
    """Objective or goal of the session."""

    work_completed: Optional[List[str]] = None
    """List of completed work items."""

    decisions_made: Optional[List[str]] = None
    """List of key decisions made."""

    issues_encountered: Optional[List[str]] = None
    """List of issues encountered."""

    context: Optional[ConversationContext] = None
    """Full conversation context."""

    graphiti_node_uuid: Optional[str] = None
    """UUID of the EpisodicNode in Graphiti graph."""

    storage_timestamp: Optional[datetime] = None
    """When the session was stored in Graphiti."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "session_id": self.session_id,
            "summary": self.summary,
            "objective": self.objective,
            "work_completed": self.work_completed,
            "decisions_made": self.decisions_made,
            "issues_encountered": self.issues_encountered,
            "context": self.context.to_dict() if self.context else None,
            "graphiti_node_uuid": self.graphiti_node_uuid,
            "storage_timestamp": (
                self.storage_timestamp.isoformat() if self.storage_timestamp else None
            ),
        }
