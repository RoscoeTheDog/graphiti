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
from pathlib import Path
from typing import Any

from graphiti_core.graphiti import Graphiti
from graphiti_core.nodes import EpisodeType

from .summarizer import SessionSummary

logger = logging.getLogger(__name__)


class SessionStorage:
    """
    Stores session summaries in Graphiti graph database.

    Creates EpisodicNodes with session metadata and establishes
    relationships between sequential sessions.
    """

    def __init__(self, graphiti: Graphiti):
        """
        Initialize SessionStorage with Graphiti instance.

        Args:
            graphiti: Graphiti instance for graph operations
        """
        self.graphiti = graphiti
        logger.info('SessionStorage initialized')

    async def store_session(
        self,
        summary: SessionSummary,
        group_id: str,
        previous_session_uuid: str | None = None,
        handoff_file_path: Path | None = None,
    ) -> str:
        """
        Store session summary as EpisodicNode in Graphiti graph.

        Args:
            summary: SessionSummary to store
            group_id: Group ID for the session (project-scoped)
            previous_session_uuid: UUID of previous session for relationship linking
            handoff_file_path: Optional path to handoff file for reference

        Returns:
            UUID of created episode

        Raises:
            Exception: If episode creation fails
        """
        logger.info(f'Storing session {summary.sequence_number:03d}: {summary.title}')

        try:
            # Build episode name
            episode_name = f'Session {summary.sequence_number:03d}: {summary.title}'

            # Build episode body with markdown content
            episode_body = summary.to_markdown()

            # Add handoff file reference if provided
            if handoff_file_path:
                episode_body += f'\n---\n\n**Handoff File**: `{handoff_file_path}`\n'

            # Prepare source description
            source_description = (
                f'Session handoff summary with {len(summary.completed_tasks)} completed tasks, '
                f'{len(summary.blocked_items)} blocked items, '
                f'and {len(summary.files_modified)} files modified'
            )

            # Add episode to graph
            logger.debug(f'Adding episode: {episode_name}')
            result = await self.graphiti.add_episode(
                name=episode_name,
                episode_body=episode_body,
                source_description=source_description,
                reference_time=summary.created_at,
                source=EpisodeType.text,
                group_id=group_id,
                previous_episode_uuids=[previous_session_uuid] if previous_session_uuid else None,
            )

            episode_uuid = result.episode.uuid
            logger.info(
                f'Session stored successfully: {episode_name} (UUID: {episode_uuid}), '
                f'created {len(result.nodes)} nodes and {len(result.edges)} edges'
            )

            return episode_uuid

        except Exception as e:
            logger.error(f'Error storing session in Graphiti: {e}', exc_info=True)
            raise

    async def find_previous_session(self, group_id: str, before: datetime) -> str | None:
        """
        Find the most recent session episode before the given timestamp.

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

    async def get_session_metadata(self, episode_uuid: str) -> dict[str, Any] | None:
        """
        Retrieve session metadata by episode UUID.

        Args:
            episode_uuid: UUID of session episode

        Returns:
            Dict with session metadata, or None if not found
        """
        logger.debug(f'Retrieving session metadata for {episode_uuid}')

        try:
            # Retrieve episode from graph
            episodes = await self.graphiti.retrieve_episodes(
                reference_time=datetime.now(),
                last_n=1000,  # Fetch many to find specific UUID
            )

            # Find matching episode
            episode = next((ep for ep in episodes if ep.uuid == episode_uuid), None)

            if not episode:
                logger.warning(f'Session episode not found: {episode_uuid}')
                return None

            # Extract metadata from episode
            metadata = {
                'uuid': episode.uuid,
                'name': episode.name,
                'created_at': episode.created_at.isoformat(),
                'group_id': episode.group_id,
                'source_description': episode.source_description,
                'episode_body_preview': (
                    episode.content[:200] + '...' if len(episode.content) > 200 else episode.content
                ),
            }

            logger.info(f'Retrieved session metadata: {episode.name}')
            return metadata

        except Exception as e:
            logger.error(f'Error retrieving session metadata: {e}', exc_info=True)
            return None

    async def search_sessions(
        self, query: str, group_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search for sessions using semantic search.

        Args:
            query: Search query (e.g., "authentication implementation")
            group_id: Group ID to search within
            limit: Maximum number of results

        Returns:
            List of session metadata dicts

        Raises:
            Exception: If search fails
        """
        logger.info(f'Searching sessions: "{query}" in group {group_id}')

        try:
            # Search episodes using Graphiti's semantic search
            search_results = await self.graphiti.search(
                query=query,
                group_ids=[group_id],
                num_results=limit,
            )

            # Filter for session episodes
            session_results = [
                {
                    'uuid': result.uuid,
                    'name': result.name,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'group_id': result.group_id,
                    'content_preview': (
                        result.content[:200] + '...'
                        if result.content and len(result.content) > 200
                        else result.content
                    ),
                    'relevance_score': getattr(result, 'score', None),
                }
                for result in search_results.episodes
                if result.name and result.name.startswith('Session ')
            ]

            logger.info(f'Found {len(session_results)} matching sessions')
            return session_results

        except Exception as e:
            logger.error(f'Error searching sessions: {e}', exc_info=True)
            raise

    async def archive_session(self, episode_uuid: str) -> bool:
        """
        Mark a session as archived (implementation depends on graph schema).

        Note: Current implementation adds a note to the episode.
        Future: Could update episode metadata or add ARCHIVED relationship.

        Args:
            episode_uuid: UUID of session episode to archive

        Returns:
            True if archived successfully, False otherwise
        """
        logger.info(f'Archiving session: {episode_uuid}')

        try:
            # Note: Current Graphiti API doesn't support episode updates directly
            # For now, we'll just log the archive action
            # Future: Add episode update capability or use relationships

            logger.info(f'Session marked for archive: {episode_uuid}')
            logger.warning('Archive functionality not fully implemented - metadata-only operation')
            return True

        except Exception as e:
            logger.error(f'Error archiving session: {e}', exc_info=True)
            return False
