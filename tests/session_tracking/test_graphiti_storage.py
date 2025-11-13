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

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from graphiti_core.nodes import EpisodeType, EpisodicNode
from graphiti_core.session_tracking import SessionStorage
from graphiti_core.session_tracking.summarizer import SessionSummary


@pytest.fixture
def mock_graphiti():
    """Create a mock Graphiti instance."""
    graphiti = Mock()
    graphiti.add_episode = AsyncMock()
    graphiti.retrieve_episodes = AsyncMock()
    graphiti.search = AsyncMock()
    return graphiti


@pytest.fixture
def sample_summary():
    """Create a sample session summary."""
    return SessionSummary(
        sequence_number=5,
        title='Implement Authentication',
        slug='implement-authentication',
        objective='Add JWT-based authentication to the API',
        completed_tasks=[
            'Created login endpoint',
            'Added token generation',
            'Wrote authentication tests',
        ],
        blocked_items=['Database migration pending'],
        next_steps=['Complete database migration', 'Add authorization middleware'],
        files_modified=['src/auth.py', 'tests/test_auth.py'],
        documentation_referenced=['docs/auth.md'],
        key_decisions=['Use JWT tokens', 'Store in httpOnly cookies'],
        mcp_tools_used=['serena', 'graphiti-memory'],
        token_count=1500,
        duration_estimate='2 hours',
        created_at=datetime(2025, 11, 13, 10, 30, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_episode():
    """Create a sample episode response."""
    return EpisodicNode(
        name='Session 005: Implement Authentication',
        labels=['EpisodicNode'],
        group_id='test-group',
        source=EpisodeType.text,
        source_description='Session handoff summary',
        content='Session content...',
        created_at=datetime.now(timezone.utc),
        valid_at=datetime.now(timezone.utc),
        uuid='episode-uuid-123',
    )


class TestSessionStorage:
    """Test suite for SessionStorage."""

    def test_initialization(self, mock_graphiti):
        """Test SessionStorage initialization."""
        storage = SessionStorage(mock_graphiti)
        assert storage.graphiti == mock_graphiti

    @pytest.mark.asyncio
    async def test_store_session_success(self, mock_graphiti, sample_summary, sample_episode):
        """Test successful session storage."""
        # Mock episode result
        mock_result = Mock()
        mock_result.episode = sample_episode
        mock_result.nodes = [Mock(), Mock()]  # 2 nodes created
        mock_result.edges = [Mock()]  # 1 edge created
        mock_graphiti.add_episode.return_value = mock_result

        storage = SessionStorage(mock_graphiti)
        episode_uuid = await storage.store_session(
            summary=sample_summary,
            group_id='test-group',
            previous_session_uuid='previous-uuid',
            handoff_file_path=Path('/test/project/.claude/handoff/s005-implement-authentication.md'),
        )

        # Verify episode was added
        mock_graphiti.add_episode.assert_called_once()
        call_kwargs = mock_graphiti.add_episode.call_args[1]

        assert call_kwargs['name'] == 'Session 005: Implement Authentication'
        assert 'Implement Authentication' in call_kwargs['episode_body']
        assert call_kwargs['source'] == EpisodeType.text
        assert call_kwargs['group_id'] == 'test-group'
        assert call_kwargs['reference_time'] == sample_summary.created_at
        assert call_kwargs['previous_episode_uuids'] == ['previous-uuid']
        assert 's005-implement-authentication.md' in call_kwargs['episode_body']

        # Verify returned UUID
        assert episode_uuid == 'episode-uuid-123'

    @pytest.mark.asyncio
    async def test_store_session_without_previous(self, mock_graphiti, sample_summary, sample_episode):
        """Test storing session without previous session link."""
        mock_result = Mock()
        mock_result.episode = sample_episode
        mock_result.nodes = []
        mock_result.edges = []
        mock_graphiti.add_episode.return_value = mock_result

        storage = SessionStorage(mock_graphiti)
        episode_uuid = await storage.store_session(
            summary=sample_summary,
            group_id='test-group',
            previous_session_uuid=None,  # No previous session
        )

        # Verify previous_episode_uuids was None
        call_kwargs = mock_graphiti.add_episode.call_args[1]
        assert call_kwargs['previous_episode_uuids'] is None

        assert episode_uuid == 'episode-uuid-123'

    @pytest.mark.asyncio
    async def test_store_session_error(self, mock_graphiti, sample_summary):
        """Test session storage with error."""
        # Mock error
        mock_graphiti.add_episode.side_effect = Exception('Database connection error')

        storage = SessionStorage(mock_graphiti)

        with pytest.raises(Exception, match='Database connection error'):
            await storage.store_session(
                summary=sample_summary,
                group_id='test-group',
            )

    @pytest.mark.asyncio
    async def test_find_previous_session_found(self, mock_graphiti, sample_episode):
        """Test finding previous session successfully."""
        # Mock episode retrieval
        episode1 = Mock()
        episode1.name = 'Session 003: Previous Work'
        episode1.created_at = datetime(2025, 11, 12, 10, 0, tzinfo=timezone.utc)
        episode1.uuid = 'uuid-003'

        episode2 = Mock()
        episode2.name = 'Session 004: More Recent Work'
        episode2.created_at = datetime(2025, 11, 12, 15, 0, tzinfo=timezone.utc)
        episode2.uuid = 'uuid-004'

        episode3 = Mock()
        episode3.name = 'Regular Episode'
        episode3.created_at = datetime(2025, 11, 12, 12, 0, tzinfo=timezone.utc)
        episode3.uuid = 'uuid-regular'

        mock_graphiti.retrieve_episodes.return_value = [episode1, episode2, episode3]

        storage = SessionStorage(mock_graphiti)
        result = await storage.find_previous_session(
            group_id='test-group',
            before=datetime(2025, 11, 13, 0, 0, tzinfo=timezone.utc),
        )

        # Should return most recent session episode (004)
        assert result == 'uuid-004'

        # Verify retrieve_episodes was called correctly
        call_kwargs = mock_graphiti.retrieve_episodes.call_args[1]
        assert call_kwargs['group_ids'] == ['test-group']
        assert call_kwargs['last_n'] == 10

    @pytest.mark.asyncio
    async def test_find_previous_session_not_found(self, mock_graphiti):
        """Test finding previous session when none exists."""
        # Mock no session episodes
        episode1 = Mock()
        episode1.name = 'Regular Episode'
        episode1.created_at = datetime(2025, 11, 12, 10, 0, tzinfo=timezone.utc)

        mock_graphiti.retrieve_episodes.return_value = [episode1]

        storage = SessionStorage(mock_graphiti)
        result = await storage.find_previous_session(
            group_id='test-group',
            before=datetime(2025, 11, 13, 0, 0, tzinfo=timezone.utc),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_previous_session_error(self, mock_graphiti):
        """Test finding previous session with error."""
        mock_graphiti.retrieve_episodes.side_effect = Exception('Database error')

        storage = SessionStorage(mock_graphiti)
        result = await storage.find_previous_session(
            group_id='test-group',
            before=datetime.now(timezone.utc),
        )

        # Should return None on error (logged but not raised)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_metadata_found(self, mock_graphiti, sample_episode):
        """Test retrieving session metadata successfully."""
        mock_graphiti.retrieve_episodes.return_value = [sample_episode]

        storage = SessionStorage(mock_graphiti)
        metadata = await storage.get_session_metadata('episode-uuid-123')

        assert metadata is not None
        assert metadata['uuid'] == 'episode-uuid-123'
        assert metadata['name'] == 'Session 005: Implement Authentication'
        assert metadata['group_id'] == 'test-group'
        assert 'created_at' in metadata
        assert 'episode_body_preview' in metadata

    @pytest.mark.asyncio
    async def test_get_session_metadata_not_found(self, mock_graphiti):
        """Test retrieving session metadata when episode not found."""
        episode = Mock()
        episode.uuid = 'different-uuid'
        episode.name = 'Different Episode'
        mock_graphiti.retrieve_episodes.return_value = [episode]

        storage = SessionStorage(mock_graphiti)
        metadata = await storage.get_session_metadata('episode-uuid-123')

        assert metadata is None

    @pytest.mark.asyncio
    async def test_get_session_metadata_error(self, mock_graphiti):
        """Test retrieving session metadata with error."""
        mock_graphiti.retrieve_episodes.side_effect = Exception('Database error')

        storage = SessionStorage(mock_graphiti)
        metadata = await storage.get_session_metadata('episode-uuid-123')

        assert metadata is None

    @pytest.mark.asyncio
    async def test_search_sessions_found(self, mock_graphiti):
        """Test searching sessions successfully."""
        # Mock search results
        result1 = Mock()
        result1.name = 'Session 001: Authentication Work'
        result1.uuid = 'uuid-001'
        result1.created_at = datetime(2025, 11, 10, 10, 0, tzinfo=timezone.utc)
        result1.group_id = 'test-group'
        result1.content = 'Session content for authentication implementation...'
        result1.score = 0.95

        result2 = Mock()
        result2.name = 'Regular Episode'
        result2.uuid = 'uuid-regular'
        result2.created_at = datetime(2025, 11, 11, 10, 0, tzinfo=timezone.utc)
        result2.group_id = 'test-group'
        result2.content = 'Regular content'
        result2.score = 0.75

        mock_search_result = Mock()
        mock_search_result.episodes = [result1, result2]
        mock_graphiti.search.return_value = mock_search_result

        storage = SessionStorage(mock_graphiti)
        results = await storage.search_sessions(
            query='authentication',
            group_id='test-group',
            limit=10,
        )

        # Should return only session episodes
        assert len(results) == 1
        assert results[0]['name'] == 'Session 001: Authentication Work'
        assert results[0]['uuid'] == 'uuid-001'
        assert results[0]['relevance_score'] == 0.95
        assert 'content_preview' in results[0]
        assert len(results[0]['content_preview']) <= 203  # 200 + "..."

        # Verify search was called correctly
        call_kwargs = mock_graphiti.search.call_args[1]
        assert call_kwargs['query'] == 'authentication'
        assert call_kwargs['group_ids'] == ['test-group']
        assert call_kwargs['num_results'] == 10

    @pytest.mark.asyncio
    async def test_search_sessions_no_results(self, mock_graphiti):
        """Test searching sessions with no results."""
        mock_search_result = Mock()
        mock_search_result.episodes = []
        mock_graphiti.search.return_value = mock_search_result

        storage = SessionStorage(mock_graphiti)
        results = await storage.search_sessions(
            query='nonexistent',
            group_id='test-group',
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_sessions_error(self, mock_graphiti):
        """Test searching sessions with error."""
        mock_graphiti.search.side_effect = Exception('Search error')

        storage = SessionStorage(mock_graphiti)

        with pytest.raises(Exception, match='Search error'):
            await storage.search_sessions(
                query='test',
                group_id='test-group',
            )

    @pytest.mark.asyncio
    async def test_archive_session(self, mock_graphiti):
        """Test archiving session (metadata-only operation)."""
        storage = SessionStorage(mock_graphiti)
        result = await storage.archive_session('episode-uuid-123')

        # Should return True (metadata-only operation)
        assert result is True

    @pytest.mark.asyncio
    async def test_episode_body_includes_summary(self, mock_graphiti, sample_summary, sample_episode):
        """Test that episode body includes full summary markdown."""
        mock_result = Mock()
        mock_result.episode = sample_episode
        mock_result.nodes = []
        mock_result.edges = []
        mock_graphiti.add_episode.return_value = mock_result

        storage = SessionStorage(mock_graphiti)
        await storage.store_session(
            summary=sample_summary,
            group_id='test-group',
        )

        call_kwargs = mock_graphiti.add_episode.call_args[1]
        episode_body = call_kwargs['episode_body']

        # Verify markdown elements are present
        assert '# Session 005: Implement Authentication' in episode_body
        assert '**Status**: ACTIVE' in episode_body
        assert '## Completed' in episode_body
        assert 'Created login endpoint' in episode_body
        assert '## Blocked' in episode_body
        assert 'Database migration pending' in episode_body
        assert '## Next Steps' in episode_body
        assert 'Complete database migration' in episode_body
        assert '**Files Modified/Created**:' in episode_body
        assert 'src/auth.py' in episode_body

    @pytest.mark.asyncio
    async def test_source_description_includes_stats(self, mock_graphiti, sample_summary, sample_episode):
        """Test that source description includes summary statistics."""
        mock_result = Mock()
        mock_result.episode = sample_episode
        mock_result.nodes = []
        mock_result.edges = []
        mock_graphiti.add_episode.return_value = mock_result

        storage = SessionStorage(mock_graphiti)
        await storage.store_session(
            summary=sample_summary,
            group_id='test-group',
        )

        call_kwargs = mock_graphiti.add_episode.call_args[1]
        source_description = call_kwargs['source_description']

        # Verify statistics are included
        assert '3 completed tasks' in source_description
        assert '1 blocked items' in source_description
        assert '2 files modified' in source_description
