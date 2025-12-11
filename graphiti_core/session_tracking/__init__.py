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
- ResilientSessionIndexer: Resilient wrapper with retry queue (Story 19)
- HandoffExporter: Optional markdown export for session handoffs
- SessionManager/Watcher: Automatic session detection and lifecycle
- RetryQueue: Persistent retry queue for failed episodes (Story 19)
- SessionTrackingHealth: Health status aggregation (Story 19)
"""

from .filter import SessionFilter
from .filter_config import FilterConfig
from .handoff_exporter import HandoffExporter
from .indexer import SessionIndexer
from .message_summarizer import MessageSummarizer
from .summarizer import DecisionRecord, ErrorResolution, SessionSummary, SessionSummarySchema
from .metadata import build_episode_metadata_header
from .parser import JSONLParser
from .path_resolver import ClaudePathResolver
from .resilient_indexer import (
    OnLLMUnavailable,
    ResilientIndexerConfig,
    ResilientSessionIndexer,
)
from .retry_queue import FailedEpisode, RetryQueue, RetryQueueProcessor
from .session_manager import ActiveSession, SessionManager
from .status import (
    DegradationLevel,
    LLMStatus,
    QueueStatus,
    RecentFailure,
    RetryQueueStatus,
    ServiceStatus,
    SessionTrackingHealth,
    SessionTrackingStatusAggregator,
)
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
    # Message summarization (NEW - Story 2.3.4)
    "MessageSummarizer",
    # Session summary models (NEW - Story 1 v3.0.0)
    "SessionSummary",
    "SessionSummarySchema",
    "DecisionRecord",
    "ErrorResolution",
    # Episode metadata (NEW - Global Session Tracking Story 4)
    "build_episode_metadata_header",
    # Indexing (NEW - Story 4 refactoring)
    "SessionIndexer",
    # Resilient indexing (NEW - Story 19)
    "ResilientSessionIndexer",
    "ResilientIndexerConfig",
    "OnLLMUnavailable",
    # Retry queue (NEW - Story 19)
    "RetryQueue",
    "RetryQueueProcessor",
    "FailedEpisode",
    # Health status (NEW - Story 19)
    "SessionTrackingHealth",
    "SessionTrackingStatusAggregator",
    "ServiceStatus",
    "DegradationLevel",
    "LLMStatus",
    "QueueStatus",
    "RetryQueueStatus",
    "RecentFailure",
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
