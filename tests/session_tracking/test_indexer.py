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

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from graphiti_core.nodes import EpisodeType
from graphiti_core.session_tracking.indexer import SessionIndexer


@pytest.fixture
def mock_graphiti():
    """Create a mock Graphiti instance."""
    graphiti = MagicMock()
    graphiti.add_episode = AsyncMock()
    graphiti.retrieve_episodes = AsyncMock()
    graphiti.search = AsyncMock()
    return graphiti


@pytest.fixture
def indexer(mock_graphiti):
    """Create a SessionIndexer instance with mocked Graphiti."""
    return SessionIndexer(mock_graphiti)


class TestSessionIndexer:
    """Tests for SessionIndexer class."""

    def test_initialization(self, indexer, mock_graphiti):
        """Test SessionIndexer initialization."""
        assert indexer.graphiti == mock_graphiti

    @pytest.mark.asyncio
    async def test_index_session_success(self, indexer, mock_graphiti):
        """Test successful session indexing."""
        # Setup mock response
        mock_episode = MagicMock()
        mock_episode.uuid = 'test-uuid-123'
        mock_result = MagicMock()
        mock_result.episode = mock_episode
        mock_result.nodes = [MagicMock(), MagicMock()]  # 2 nodes
        mock_result.edges = [MagicMock()]  # 1 edge
        mock_graphiti.add_episode.return_value = mock_result

        # Test data
        session_id = 'abc123def456'
        filtered_content = 'User: Fix auth\nAgent: Reading auth.py...\nTool: Read(auth.py)'
        group_id = 'myhost__a1b2c3d4'
        session_number = 5

        # Call index_session
        episode_uuid = await indexer.index_session(
            session_id=session_id,
            filtered_content=filtered_content,
            group_id=group_id,
            session_number=session_number,
        )

        # Verify result
        assert episode_uuid == 'test-uuid-123'

        # Verify add_episode was called correctly
        mock_graphiti.add_episode.assert_called_once()
        call_kwargs = mock_graphiti.add_episode.call_args.kwargs

        assert call_kwargs['name'] == 'Session 005: abc123de'
        assert call_kwargs['episode_body'] == filtered_content
        assert call_kwargs['group_id'] == group_id
        assert call_kwargs['source'] == EpisodeType.text
        assert 'Filtered Claude Code session' in call_kwargs['source_description']
        assert call_kwargs['previous_episode_uuids'] is None

    @pytest.mark.asyncio
    async def test_index_session_with_previous_episode(self, indexer, mock_graphiti):
        """Test session indexing with previous episode linking."""
        # Setup mock
        mock_episode = MagicMock()
        mock_episode.uuid = 'new-uuid'
        mock_result = MagicMock()
        mock_result.episode = mock_episode
        mock_result.nodes = []
        mock_result.edges = []
        mock_graphiti.add_episode.return_value = mock_result

        # Call with previous episode
        episode_uuid = await indexer.index_session(
            session_id='session2',
            filtered_content='Content',
            group_id='group1',
            previous_episode_uuid='prev-uuid-123',
        )

        # Verify previous episode was linked
        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs['previous_episode_uuids'] == ['prev-uuid-123']
        assert episode_uuid == 'new-uuid'

    @pytest.mark.asyncio
    async def test_index_session_without_sequence_number(self, indexer, mock_graphiti):
        """Test session indexing without sequence number."""
        mock_episode = MagicMock()
        mock_episode.uuid = 'uuid'
        mock_result = MagicMock()
        mock_result.episode = mock_episode
        mock_result.nodes = []
        mock_result.edges = []
        mock_graphiti.add_episode.return_value = mock_result

        await indexer.index_session(
            session_id='abc123',
            filtered_content='Content',
            group_id='group1',
        )

        # Verify name format without sequence number
        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs['name'] == 'Session abc123'

    @pytest.mark.asyncio
    async def test_index_session_with_custom_reference_time(self, indexer, mock_graphiti):
        """Test session indexing with custom reference time."""
        mock_episode = MagicMock()
        mock_episode.uuid = 'uuid'
        mock_result = MagicMock()
        mock_result.episode = mock_episode
        mock_result.nodes = []
        mock_result.edges = []
        mock_graphiti.add_episode.return_value = mock_result

        custom_time = datetime(2025, 11, 13, 10, 30, 0)

        await indexer.index_session(
            session_id='abc123',
            filtered_content='Content',
            group_id='group1',
            reference_time=custom_time,
        )

        call_kwargs = mock_graphiti.add_episode.call_args.kwargs
        assert call_kwargs['reference_time'] == custom_time

    @pytest.mark.asyncio
    async def test_index_session_error(self, indexer, mock_graphiti):
        """Test error handling during session indexing."""
        # Setup mock to raise error
        mock_graphiti.add_episode.side_effect = Exception('Graphiti error')

        # Verify exception is raised
        with pytest.raises(Exception, match='Graphiti error'):
            await indexer.index_session(
                session_id='abc123',
                filtered_content='Content',
                group_id='group1',
            )

    @pytest.mark.asyncio
    async def test_find_previous_session_found(self, indexer, mock_graphiti):
        """Test finding previous session successfully."""
        # Setup mock episodes
        mock_ep1 = MagicMock()
        mock_ep1.name = 'Session 003'
        mock_ep1.uuid = 'uuid-003'
        mock_ep1.created_at = datetime(2025, 11, 13, 10, 0, 0)

        mock_ep2 = MagicMock()
        mock_ep2.name = 'Session 004'
        mock_ep2.uuid = 'uuid-004'
        mock_ep2.created_at = datetime(2025, 11, 13, 11, 0, 0)

        mock_graphiti.retrieve_episodes.return_value = [mock_ep1, mock_ep2]

        # Find previous session
        before_time = datetime(2025, 11, 13, 12, 0, 0)
        result = await indexer.find_previous_session(
            group_id='group1',
            before=before_time,
        )

        # Should return most recent (004)
        assert result == 'uuid-004'
        mock_graphiti.retrieve_episodes.assert_called_once_with(
            reference_time=before_time,
            group_ids=['group1'],
            last_n=10,
        )

    @pytest.mark.asyncio
    async def test_find_previous_session_not_found(self, indexer, mock_graphiti):
        """Test finding previous session when none exists."""
        # Return empty list
        mock_graphiti.retrieve_episodes.return_value = []

        result = await indexer.find_previous_session(
            group_id='group1',
            before=datetime.now(),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_previous_session_filters_non_sessions(self, indexer, mock_graphiti):
        """Test that find_previous_session filters out non-session episodes."""
        # Mix of session and non-session episodes
        mock_session = MagicMock()
        mock_session.name = 'Session 005'
        mock_session.uuid = 'session-uuid'
        mock_session.created_at = datetime(2025, 11, 13, 10, 0, 0)

        mock_other = MagicMock()
        mock_other.name = 'Other Episode'
        mock_other.uuid = 'other-uuid'
        mock_other.created_at = datetime(2025, 11, 13, 11, 0, 0)

        mock_graphiti.retrieve_episodes.return_value = [mock_session, mock_other]

        result = await indexer.find_previous_session(
            group_id='group1',
            before=datetime.now(),
        )

        # Should only return session episode
        assert result == 'session-uuid'

    @pytest.mark.asyncio
    async def test_find_previous_session_error(self, indexer, mock_graphiti):
        """Test error handling when finding previous session."""
        mock_graphiti.retrieve_episodes.side_effect = Exception('Retrieve error')

        result = await indexer.find_previous_session(
            group_id='group1',
            before=datetime.now(),
        )

        # Should return None on error (graceful degradation)
        assert result is None

    @pytest.mark.asyncio
    async def test_search_sessions_found(self, indexer, mock_graphiti):
        """Test searching for sessions with results."""
        # Setup mock search results
        mock_result1 = MagicMock()
        mock_result1.name = 'Session 005: Auth Fix'
        mock_result1.uuid = 'uuid-005'
        mock_result1.created_at = datetime(2025, 11, 13, 10, 0, 0)
        mock_result1.group_id = 'group1'
        mock_result1.content = 'Short content'

        mock_result2 = MagicMock()
        mock_result2.name = 'Session 007: JWT Update'
        mock_result2.uuid = 'uuid-007'
        mock_result2.created_at = datetime(2025, 11, 13, 12, 0, 0)
        mock_result2.group_id = 'group1'
        mock_result2.content = 'x' * 250  # Long content

        mock_search_results = MagicMock()
        mock_search_results.episodes = [mock_result1, mock_result2]
        mock_graphiti.search.return_value = mock_search_results

        # Search sessions
        results = await indexer.search_sessions(
            query='authentication',
            group_id='group1',
            limit=10,
        )

        # Verify results
        assert len(results) == 2
        assert results[0]['uuid'] == 'uuid-005'
        assert results[0]['name'] == 'Session 005: Auth Fix'
        assert results[0]['content_preview'] == 'Short content'

        assert results[1]['uuid'] == 'uuid-007'
        assert results[1]['content_preview'].endswith('...')  # Truncated

        mock_graphiti.search.assert_called_once_with(
            query='authentication',
            group_ids=['group1'],
            num_results=10,
        )

    @pytest.mark.asyncio
    async def test_search_sessions_filters_non_sessions(self, indexer, mock_graphiti):
        """Test that search filters out non-session episodes."""
        mock_session = MagicMock()
        mock_session.name = 'Session 005'
        mock_session.uuid = 'session-uuid'
        mock_session.created_at = datetime.now()
        mock_session.group_id = 'group1'
        mock_session.content = 'Content'

        mock_other = MagicMock()
        mock_other.name = 'File Update'
        mock_other.uuid = 'other-uuid'
        mock_other.created_at = datetime.now()
        mock_other.group_id = 'group1'
        mock_other.content = 'Content'

        mock_search_results = MagicMock()
        mock_search_results.episodes = [mock_session, mock_other]
        mock_graphiti.search.return_value = mock_search_results

        results = await indexer.search_sessions(
            query='test',
            group_id='group1',
        )

        # Should only return session
        assert len(results) == 1
        assert results[0]['uuid'] == 'session-uuid'

    @pytest.mark.asyncio
    async def test_search_sessions_no_results(self, indexer, mock_graphiti):
        """Test searching with no results."""
        mock_search_results = MagicMock()
        mock_search_results.episodes = []
        mock_graphiti.search.return_value = mock_search_results

        results = await indexer.search_sessions(
            query='nonexistent',
            group_id='group1',
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_sessions_error(self, indexer, mock_graphiti):
        """Test error handling during search."""
        mock_graphiti.search.side_effect = Exception('Search error')

        with pytest.raises(Exception, match='Search error'):
            await indexer.search_sessions(
                query='test',
                group_id='group1',
            )
