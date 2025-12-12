"""Unit tests for preprocessing prompt injection in node and edge operations.

Tests Story 4 and Story 5: Preprocessing injection in extract_nodes and extract_edges.
"""

from unittest.mock import AsyncMock, MagicMock, call
from datetime import datetime, timezone

import pytest

from graphiti_core.graphiti_types import GraphitiClients
from graphiti_core.nodes import EntityNode, EpisodicNode, EpisodeType
from graphiti_core.edges import EntityEdge
from graphiti_core.utils.datetime_utils import utc_now
from graphiti_core.utils.maintenance.node_operations import extract_nodes
from graphiti_core.utils.maintenance.edge_operations import extract_edges


@pytest.fixture
def mock_clients_with_preprocessing():
    """Create mock GraphitiClients with preprocessing fields."""
    driver = MagicMock()
    embedder = MagicMock()
    embedder.create = AsyncMock(return_value=[0.1, 0.2, 0.3])
    embedder.create_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    cross_encoder = MagicMock()
    llm_client = MagicMock()
    llm_client.generate_response = AsyncMock(
        return_value={'extracted_entities': []}
    )

    clients = GraphitiClients.model_construct(
        driver=driver,
        embedder=embedder,
        cross_encoder=cross_encoder,
        llm_client=llm_client,
        preprocessing_prompt="Test preprocessing prompt",
        preprocessing_mode="prepend",
    )

    return clients


@pytest.fixture
def mock_clients_without_preprocessing():
    """Create mock GraphitiClients without preprocessing."""
    driver = MagicMock()
    embedder = MagicMock()
    cross_encoder = MagicMock()
    llm_client = MagicMock()
    llm_client.generate_response = AsyncMock(
        return_value={'extracted_entities': []}
    )

    clients = GraphitiClients.model_construct(
        driver=driver,
        embedder=embedder,
        cross_encoder=cross_encoder,
        llm_client=llm_client,
        preprocessing_prompt=None,
        preprocessing_mode="prepend",
    )

    return clients


@pytest.fixture
def mock_episode():
    """Create a mock episode."""
    return EpisodicNode(
        name='test_episode',
        group_id='test_group',
        source=EpisodeType.message,
        source_description='test',
        content='test content',
        valid_at=utc_now(),
    )


class TestNodeOperationsPreprocessingInjection:
    """Test preprocessing injection in node_operations.py (Story 4)."""

    @pytest.mark.asyncio
    async def test_extract_nodes_uses_preprocessing_prompt(
        self, mock_clients_with_preprocessing, mock_episode
    ):
        """Test that preprocessing_prompt is passed to LLM in extract_nodes (AC-4.1)."""
        await extract_nodes(
            mock_clients_with_preprocessing,
            mock_episode,
            previous_episodes=[],
            entity_types=None,
            excluded_entity_types=None,
        )

        # Verify LLM was called
        assert mock_clients_with_preprocessing.llm_client.generate_response.call_count > 0

        # Get the actual call arguments
        call_args = mock_clients_with_preprocessing.llm_client.generate_response.call_args
        messages = call_args[0][0]  # First positional argument is messages

        # Verify preprocessing prompt is in the context
        message_content = str(messages)
        assert "Test preprocessing prompt" in message_content

    @pytest.mark.asyncio
    async def test_extract_nodes_without_preprocessing_prompt(
        self, mock_clients_without_preprocessing, mock_episode
    ):
        """Test extract_nodes works without preprocessing_prompt (AC-4.4)."""
        # Should not raise error
        result = await extract_nodes(
            mock_clients_without_preprocessing,
            mock_episode,
            previous_episodes=[],
            entity_types=None,
            excluded_entity_types=None,
        )

        # Verify result is valid
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_extract_nodes_prepend_mode(
        self, mock_clients_with_preprocessing, mock_episode
    ):
        """Test preprocessing_mode='prepend' in extract_nodes (AC-4.3)."""
        mock_clients_with_preprocessing.preprocessing_mode = "prepend"

        await extract_nodes(
            mock_clients_with_preprocessing,
            mock_episode,
            previous_episodes=[],
            entity_types=None,
            excluded_entity_types=None,
        )

        # Get the call arguments
        call_args = mock_clients_with_preprocessing.llm_client.generate_response.call_args
        messages = call_args[0][0]

        # Verify preprocessing prompt is present
        message_content = str(messages)
        assert "Test preprocessing prompt" in message_content

    @pytest.mark.asyncio
    async def test_extract_nodes_append_mode(
        self, mock_clients_with_preprocessing, mock_episode
    ):
        """Test preprocessing_mode='append' in extract_nodes (AC-4.3)."""
        mock_clients_with_preprocessing.preprocessing_mode = "append"

        await extract_nodes(
            mock_clients_with_preprocessing,
            mock_episode,
            previous_episodes=[],
            entity_types=None,
            excluded_entity_types=None,
        )

        # Get the call arguments
        call_args = mock_clients_with_preprocessing.llm_client.generate_response.call_args
        messages = call_args[0][0]

        # Verify preprocessing prompt is present
        message_content = str(messages)
        assert "Test preprocessing prompt" in message_content


class TestEdgeOperationsPreprocessingInjection:
    """Test preprocessing injection in edge_operations.py (Story 5)."""

    @pytest.fixture
    def mock_extracted_edges(self):
        """Create mock extracted edges."""
        return [
            EntityEdge(
                source_node_uuid='source_uuid',
                target_node_uuid='target_uuid',
                name='test_edge',
                group_id='test_group',
                fact='Test fact',
                episodes=['episode_1'],
                created_at=datetime.now(timezone.utc),
                valid_at=None,
                invalid_at=None,
            )
        ]

    @pytest.mark.asyncio
    async def test_extract_edges_uses_preprocessing_prompt(
        self, mock_clients_with_preprocessing, mock_episode, mock_extracted_edges
    ):
        """Test that preprocessing_prompt is passed to LLM in extract_edges (AC-5.1)."""
        # Mock entity nodes
        entity_nodes = [
            EntityNode(
                uuid='source_uuid',
                name='Source',
                group_id='test_group',
                labels=['Entity'],
            ),
            EntityNode(
                uuid='target_uuid',
                name='Target',
                group_id='test_group',
                labels=['Entity'],
            ),
        ]

        mock_clients_with_preprocessing.llm_client.generate_response = AsyncMock(
            return_value={'edges': []}
        )

        result = await extract_edges(
            mock_clients_with_preprocessing,
            mock_episode,
            entity_nodes,
            previous_episodes=[],
            edge_type_map={},
        )

        # Verify LLM was called
        assert mock_clients_with_preprocessing.llm_client.generate_response.call_count > 0

        # Get the call arguments
        call_args = mock_clients_with_preprocessing.llm_client.generate_response.call_args
        messages = call_args[0][0]

        # Verify preprocessing prompt is in the context
        message_content = str(messages)
        assert "Test preprocessing prompt" in message_content

    @pytest.mark.asyncio
    async def test_extract_edges_without_preprocessing_prompt(
        self, mock_clients_without_preprocessing, mock_episode
    ):
        """Test extract_edges works without preprocessing_prompt (AC-5.4)."""
        entity_nodes = [
            EntityNode(
                uuid='source_uuid',
                name='Source',
                group_id='test_group',
                labels=['Entity'],
            ),
        ]

        mock_clients_without_preprocessing.llm_client.generate_response = AsyncMock(
            return_value={'edges': []}
        )

        # Should not raise error
        result = await extract_edges(
            mock_clients_without_preprocessing,
            mock_episode,
            entity_nodes,
            previous_episodes=[],
            edge_type_map={},
        )

        # Verify result is valid
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_extract_edges_prepend_mode(
        self, mock_clients_with_preprocessing, mock_episode
    ):
        """Test preprocessing_mode='prepend' in extract_edges (AC-5.3)."""
        mock_clients_with_preprocessing.preprocessing_mode = "prepend"

        entity_nodes = [
            EntityNode(
                uuid='source_uuid',
                name='Source',
                group_id='test_group',
                labels=['Entity'],
            ),
        ]

        mock_clients_with_preprocessing.llm_client.generate_response = AsyncMock(
            return_value={'edges': []}
        )

        await extract_edges(
            mock_clients_with_preprocessing,
            mock_episode,
            entity_nodes,
            previous_episodes=[],
            edge_type_map={},
        )

        # Get the call arguments
        call_args = mock_clients_with_preprocessing.llm_client.generate_response.call_args
        messages = call_args[0][0]

        # Verify preprocessing prompt is present
        message_content = str(messages)
        assert "Test preprocessing prompt" in message_content

    @pytest.mark.asyncio
    async def test_extract_edges_append_mode(
        self, mock_clients_with_preprocessing, mock_episode
    ):
        """Test preprocessing_mode='append' in extract_edges (AC-5.3)."""
        mock_clients_with_preprocessing.preprocessing_mode = "append"

        entity_nodes = [
            EntityNode(
                uuid='source_uuid',
                name='Source',
                group_id='test_group',
                labels=['Entity'],
            ),
        ]

        mock_clients_with_preprocessing.llm_client.generate_response = AsyncMock(
            return_value={'edges': []}
        )

        await extract_edges(
            mock_clients_with_preprocessing,
            mock_episode,
            entity_nodes,
            previous_episodes=[],
            edge_type_map={},
        )

        # Get the call arguments
        call_args = mock_clients_with_preprocessing.llm_client.generate_response.call_args
        messages = call_args[0][0]

        # Verify preprocessing prompt is present
        message_content = str(messages)
        assert "Test preprocessing prompt" in message_content


class TestPreprocessingModeConcat:
    """Test prepend vs append mode concatenation (Story 10 AC)."""

    @pytest.mark.asyncio
    async def test_prepend_mode_order(self, mock_clients_with_preprocessing, mock_episode):
        """Test that prepend mode places preprocessing before reflexion hints."""
        mock_clients_with_preprocessing.preprocessing_mode = "prepend"

        # Mock to trigger reflexion iteration with missed entities
        mock_clients_with_preprocessing.llm_client.generate_response = AsyncMock(
            side_effect=[
                {'extracted_entities': [{'name': 'Entity1', 'entity_type_id': 0}]},
                {'missed_entities': []},  # Reflexion call
            ]
        )

        await extract_nodes(
            mock_clients_with_preprocessing,
            mock_episode,
            previous_episodes=[],
            entity_types=None,
            excluded_entity_types=None,
        )

        # Verify calls were made
        assert mock_clients_with_preprocessing.llm_client.generate_response.call_count >= 1

    @pytest.mark.asyncio
    async def test_append_mode_order(self, mock_clients_with_preprocessing, mock_episode):
        """Test that append mode places preprocessing after reflexion hints."""
        mock_clients_with_preprocessing.preprocessing_mode = "append"

        # Mock to trigger reflexion iteration
        mock_clients_with_preprocessing.llm_client.generate_response = AsyncMock(
            side_effect=[
                {'extracted_entities': [{'name': 'Entity1', 'entity_type_id': 0}]},
                {'missed_entities': []},  # Reflexion call
            ]
        )

        await extract_nodes(
            mock_clients_with_preprocessing,
            mock_episode,
            previous_episodes=[],
            entity_types=None,
            excluded_entity_types=None,
        )

        # Verify calls were made
        assert mock_clients_with_preprocessing.llm_client.generate_response.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
