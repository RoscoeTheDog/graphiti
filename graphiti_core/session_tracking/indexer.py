"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
from datetime import datetime

from graphiti_core.graphiti import Graphiti
from graphiti_core.nodes import EpisodeType

logger = logging.getLogger(__name__)


class SessionIndexer:
    """
    Indexes filtered session content directly into Graphiti graph database.

    This class provides a thin wrapper around Graphiti's add_episode() method,
    adding filtered session content as episodes. Graphiti's built-in LLM handles
    entity extraction, relationship building, and summarization automatically.

    Architecture Philosophy:
    - Let Graphiti do the heavy lifting (entity extraction, summarization)
    - Minimal preprocessing (just filtering via SessionFilter)
    - Direct episode addition (no intermediate summarization)
    - Let the graph learn naturally from raw filtered content
    """

    def __init__(self, graphiti: Graphiti):
        """
        Initialize SessionIndexer with Graphiti instance.

        Args:
            graphiti: Graphiti instance for graph operations
        """
        self.graphiti = graphiti
        logger.info('SessionIndexer initialized')

    async def index_session(
        self,
        session_id: str,
        filtered_content: str,
        group_id: str,
        session_number: int | None = None,
        reference_time: datetime | None = None,
        previous_episode_uuid: str | None = None,
    ) -> str:
        """
        Index a session by adding filtered content as an episode to Graphiti.

        Graphiti automatically:
        - Extracts entities (files, tools, patterns, decisions)
        - Creates relationships between entities
        - Builds summaries and enables semantic search
        - Links to previous episodes for session continuity

        Args:
            session_id: Unique session identifier
            filtered_content: Filtered session content (from SessionFilter)
            group_id: Group ID for the session (project-scoped, format: hostname__pwdhash)
            session_number: Optional session sequence number for naming
            reference_time: Optional timestamp for the session (defaults to now)
            previous_episode_uuid: Optional UUID of previous session for linking

        Returns:
            UUID of created episode

        Raises:
            Exception: If episode creation fails

        Example:
            >>> indexer = SessionIndexer(graphiti)
            >>> episode_uuid = await indexer.index_session(
            ...     session_id="abc123",
            ...     filtered_content=filtered_session,  # From SessionFilter
            ...     group_id="myhost__a1b2c3d4",
            ...     session_number=5
            ... )
            >>> print(f"Session indexed: {episode_uuid}")
        """
        # Build episode name
        if session_number:
            episode_name = f'Session {session_number:03d}: {session_id[:8]}'
        else:
            episode_name = f'Session {session_id[:8]}'

        # Use provided reference time or current time
        ref_time = reference_time or datetime.now()

        # Build source description with session metadata
        source_description = (
            f'Filtered Claude Code session {session_id} '
            f'(93% token reduction applied, structure preserved)'
        )

        logger.info(f'Indexing session: {episode_name} (group: {group_id})')

        try:
            # Add episode directly to Graphiti
            # Graphiti's LLM will automatically:
            # - Extract entities (files, tools, patterns)
            # - Create relationships
            # - Build summaries
            # - Enable semantic search
            result = await self.graphiti.add_episode(
                name=episode_name,
                episode_body=filtered_content,
                source_description=source_description,
                reference_time=ref_time,
                source=EpisodeType.text,
                group_id=group_id,
                previous_episode_uuids=[previous_episode_uuid] if previous_episode_uuid else None,
            )

            episode_uuid = result.episode.uuid
            logger.info(
                f'Session indexed successfully: {episode_name} (UUID: {episode_uuid}), '
                f'created {len(result.nodes)} nodes and {len(result.edges)} edges'
            )

            return episode_uuid

        except Exception as e:
            logger.error(f'Error indexing session in Graphiti: {e}', exc_info=True)
            raise

    async def find_previous_session(self, group_id: str, before: datetime) -> str | None:
        """
        Find the most recent session episode before the given timestamp.

        Useful for linking sequential sessions together.

        Args:
            group_id: Group ID to search within
            before: Timestamp to search before

        Returns:
            UUID of previous session episode, or None if not found
        """
        logger.debug(f'Finding previous session in group {group_id} before {before}')

        try:
            # Search for recent session episodes
            episodes = await self.graphiti.retrieve_episodes(
                reference_time=before,
                group_ids=[group_id],
                last_n=10,  # Get last 10 episodes
            )

            # Filter for session episodes (name starts with "Session ")
            session_episodes = [
                ep for ep in episodes if ep.name and ep.name.startswith('Session ')
            ]

            if not session_episodes:
                logger.info('No previous session found')
                return None

            # Get most recent session
            most_recent = max(session_episodes, key=lambda ep: ep.created_at)
            logger.info(f'Found previous session: {most_recent.name} (UUID: {most_recent.uuid})')

            return most_recent.uuid

        except Exception as e:
            logger.warning(f'Error finding previous session: {e}', exc_info=True)
            return None

    async def search_sessions(
        self, query: str, group_id: str, limit: int = 10
    ) -> list[dict[str, str]]:
        """
        Search for sessions using semantic search.

        Args:
            query: Search query (e.g., "authentication implementation")
            group_id: Group ID to search within
            limit: Maximum number of results

        Returns:
            List of session metadata dicts with uuid, name, content_preview

        Raises:
            Exception: If search fails

        Example:
            >>> results = await indexer.search_sessions(
            ...     query="JWT authentication bug",
            ...     group_id="myhost__a1b2c3d4"
            ... )
            >>> for result in results:
            ...     print(f"{result['name']}: {result['content_preview']}")
        """
        logger.info(f'Searching sessions: "{query}" in group {group_id}')

        try:
            # Search episodes using Graphiti's semantic search
            search_results = await self.graphiti.search(
                query=query,
                group_ids=[group_id],
                num_results=limit,
            )

            # Filter for session episodes and build result list
            session_results = [
                {
                    'uuid': result.uuid,
                    'name': result.name,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'group_id': result.group_id,
                    'content_preview': (
                        result.content[:200] + '...'
                        if result.content and len(result.content) > 200
                        else result.content or ''
                    ),
                }
                for result in search_results.episodes
                if result.name and result.name.startswith('Session ')
            ]

            logger.info(f'Found {len(session_results)} matching sessions')
            return session_results

        except Exception as e:
            logger.error(f'Error searching sessions: {e}', exc_info=True)
            raise
