"""
Session Manager for Memory Filter System

Manages session-scoped LLM instances with context tracking and cleanup.
"""

import uuid
from typing import Dict, Optional
from datetime import datetime
import logging

from mcp_server.unified_config import LLMFilterConfig
from mcp_server.llm_provider import LLMProvider, create_provider

logger = logging.getLogger(__name__)


class Session:
    """Represents a single agent session with its own LLM context"""

    def __init__(self, session_id: str, provider: LLMProvider):
        self.session_id = session_id
        self.provider = provider
        self.created_at = datetime.now()
        self.context_tokens = 0
        self.query_count = 0

    def should_cleanup(self, max_context: int) -> bool:
        """Check if session context should be reset"""
        return self.context_tokens > max_context

    def reset_context(self):
        """Reset session context (called when context gets too large)"""
        logger.info(f"Resetting context for session {self.session_id}")
        self.context_tokens = 0
        self.query_count = 0


class SessionManager:
    """Manages session-scoped LLM instances"""

    def __init__(self, filter_config: LLMFilterConfig):
        self.config = filter_config
        self.sessions: Dict[str, Session] = {}
        self.providers: list[LLMProvider] = []

        # Initialize providers in order
        for provider_config in filter_config.get_sorted_providers():
            try:
                provider = create_provider(provider_config)
                if provider.is_available():
                    self.providers.append(provider)
                    logger.info(f"Initialized {provider_config.name} provider: {provider_config.model}")
                else:
                    logger.warning(f"Provider {provider_config.name} not available (missing API key)")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_config.name}: {e}")

        if not self.providers:
            logger.warning("No LLM providers available - filtering will be disabled")

    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        """Get existing session or create new one"""
        if session_id is None:
            session_id = str(uuid.uuid4())

        if session_id not in self.sessions:
            # Try providers in order until one works
            for provider in self.providers:
                try:
                    session = Session(session_id, provider)
                    self.sessions[session_id] = session
                    logger.info(f"Created session {session_id} with provider {provider.config.name}")
                    return session
                except Exception as e:
                    logger.warning(f"Failed to create session with {provider.config.name}: {e}")
                    continue

            # If all providers failed, raise error
            raise RuntimeError("No available LLM providers for filter session")

        session = self.sessions[session_id]

        # Check if context should be reset
        if session.should_cleanup(self.config.session.max_context_tokens):
            session.reset_context()

        return session

    def cleanup_session(self, session_id: str):
        """Remove session (called when agent disconnects)"""
        if session_id in self.sessions:
            logger.info(f"Cleaning up session {session_id}")
            del self.sessions[session_id]
