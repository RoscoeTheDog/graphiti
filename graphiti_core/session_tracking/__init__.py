"""Session tracking module for Graphiti.

This module provides automatic tracking and indexing of Claude Code
conversation sessions into the Graphiti graph database. It uses a
simplified architecture where filtered session content is indexed
directly as episodes, allowing Graphiti's native LLM to extract
entities and relationships naturally.

Core components:
- JSONLParser: Parse Claude Code session JSONL files
- SessionFilter: Filter session content for token efficiency
- SessionIndexer: Index filtered sessions directly into Graphiti
- HandoffExporter: Optional markdown export for session handoffs
- SessionManager/Watcher: Automatic session detection and lifecycle
"""

from .filter import SessionFilter
from .filter_config import ContentMode, FilterConfig
from .handoff_exporter import HandoffExporter
from .indexer import SessionIndexer
from .message_summarizer import MessageSummarizer
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
    "FilterConfig",
    "ContentMode",
    # Message summarization (NEW - Story 2.3.4)
    "MessageSummarizer",
    # Indexing (NEW - Story 4 refactoring)
    "SessionIndexer",
    # Optional handoff export (NEW - Story 4 refactoring)
    "HandoffExporter",
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
