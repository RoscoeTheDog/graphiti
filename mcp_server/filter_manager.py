"""
Filter Manager for Memory Filter System

Manages LLM-based filtering logic with compact prompts and graceful degradation.
"""

import logging
from typing import Dict, Any, Optional

from mcp_server.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Compact filter prompt (minimize tokens)
FILTER_PROMPT_TEMPLATE = """Analyze event. Store ONLY if non-redundant:

✅ STORE if:
- env-quirk: Machine/OS-specific (can't fix in code)
- user-pref: Subjective preference
- external-api: 3rd party API quirk
- historical-context: Why legacy code exists
- cross-project: General learning/heuristic
- workaround: Non-obvious workaround

❌ SKIP if:
- bug-in-code: Fixed in codebase
- config-in-repo: Config now committed
- docs-added: Info in README/docs
- first-success: No learning occurred

Event: {event_description}
Context: {context}

JSON only: {{"should_store": bool, "category": str, "reason": str}}"""


class FilterManager:
    """Manages LLM-based filtering logic"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        # Check if any providers are available
        self.enabled = len(session_manager.providers) > 0

    async def should_store(
        self,
        event_description: str,
        context: str = "",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determine if event should be stored in memory.

        Args:
            event_description: Description of the event/memory
            context: Additional context (recent actions, errors, etc.)
            session_id: Optional session ID (auto-generated if not provided)

        Returns:
            {
                "should_store": bool,
                "category": str,  # env-quirk | user-pref | external-api | etc.
                "reason": str,
                "session_id": str
            }
        """
        if not self.enabled:
            # Filtering disabled, store everything
            return {
                "should_store": True,
                "category": "filter_disabled",
                "reason": "Filtering is disabled",
                "session_id": session_id or "none"
            }

        try:
            # Get or create session
            session = self.session_manager.get_or_create_session(session_id)

            # Build prompt
            prompt = FILTER_PROMPT_TEMPLATE.format(
                event_description=event_description,
                context=context
            )

            # Call LLM
            result = await session.provider.complete(prompt)

            # Update session stats
            session.query_count += 1
            session.context_tokens += len(prompt) // 4  # Rough token estimate

            # Add session_id to result
            result["session_id"] = session.session_id

            logger.info(
                f"Filter decision: {result['should_store']} "
                f"(category: {result.get('category', 'unknown')}, "
                f"session: {session.session_id})"
            )

            return result

        except Exception as e:
            logger.error(f"Filter error (falling back to store): {e}")
            # Graceful degradation: store on error
            return {
                "should_store": True,
                "category": "filter_error",
                "reason": f"Filter failed: {str(e)}",
                "session_id": session_id or "error"
            }
