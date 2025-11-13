"""Session tracking module for Graphiti.

This module provides automatic tracking and summarization of Claude Code
conversation sessions, storing them as episodic memory in the Graphiti graph.
"""

from .filter import SessionFilter
from .parser import JSONLParser
from .path_resolver import ClaudePathResolver
from .session_manager import ActiveSession, SessionManager
from .types import (
    ConversationContext,
    MessageRole,
    SessionMessage,
    SessionMetadata,
    ToolCall,
    ToolCallStatus,
    TokenUsage,
)
from .watcher import SessionFileEventHandler, SessionFileWatcher

__all__ = [
    # Parser
    "JSONLParser",
    # Path resolution
    "ClaudePathResolver",
    # Filtering
    "SessionFilter",
    # File watching
    "SessionFileWatcher",
    "SessionFileEventHandler",
    # Session management
    "SessionManager",
    "ActiveSession",
    # Types
    "ConversationContext",
    "MessageRole",
    "SessionMessage",
    "SessionMetadata",
    "ToolCall",
    "ToolCallStatus",
    "TokenUsage",
]
