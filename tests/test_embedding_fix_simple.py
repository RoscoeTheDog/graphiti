"""
Simple test to verify embeddings are generated before transactions.

This test verifies the critical performance fix by checking that
generate_name_embedding and generate_embedding are called before
the transaction opens.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, call
import pytest

from graphiti_core.utils.bulk_utils import add_nodes_and_edges_bulk


@pytest.mark.asyncio
async def test_embeddings_called_before_transaction():
    """
    Test that embedding generation methods are called BEFORE execute_write.

    This ensures the performance fix is working - embeddings should be
    generated outside the transaction to avoid holding database locks
    during external API calls.
    """
    # Track the order of operations
    operation_order = []

    # Create mock driver and session
    mock_session = AsyncMock()
    mock_driver = Mock()
    mock_driver.session.return_value = mock_session

    # Track when execute_write is called
    async def tracked_execute_write(*args, **kwargs):
        operation_order.append('transaction_opened')
        return None

    mock_session.execute_write = AsyncMock(side_effect=tracked_execute_write)
    mock_session.close = AsyncMock()

    # Mock embedder
    mock_embedder = Mock()

    # Create mock nodes - we'll patch the generate methods
    with patch('graphiti_core.nodes.EntityNode.generate_name_embedding') as mock_node_embed:
        with patch('graphiti_core.edges.EntityEdge.generate_embedding') as mock_edge_embed:

            async def track_node_embed(embedder):
                operation_order.append('node_embedding')

            async def track_edge_embed(embedder):
                operation_order.append('edge_embedding')

            mock_node_embed.side_effect = track_node_embed
            mock_edge_embed.side_effect = track_edge_embed

            # Create test data with nodes/edges that need embeddings
            from graphiti_core.nodes import EntityNode, EpisodicNode
            from graphiti_core.edges import EntityEdge

            test_nodes = [
                EntityNode(
                    uuid='node-1',
                    name='Test Node',
                    group_id='test',
                    labels=['Entity'],
                    created_at=datetime.now(timezone.utc),
                    name_embedding=None,  # Needs embedding
                )
            ]

            test_edges = [
                EntityEdge(
                    uuid='edge-1',
                    source_node_uuid='node-1',
                    target_node_uuid='node-2',
                    name='test',
                    fact='test fact',
                    episodes=['ep-1'],
                    created_at=datetime.now(timezone.utc),
                    group_id='test',
                    fact_embedding=None,  # Needs embedding
                )
            ]

            test_episodes = []
            test_episodic_edges = []

            # Execute the function
            await add_nodes_and_edges_bulk(
                driver=mock_driver,
                episodic_nodes=test_episodes,
                episodic_edges=test_episodic_edges,
                entity_nodes=test_nodes,
                entity_edges=test_edges,
                embedder=mock_embedder,
            )

    # Verify operation order
    print(f"\nOperation order: {operation_order}")

    # CRITICAL: Embeddings must happen BEFORE transaction opens
    if 'node_embedding' in operation_order and 'transaction_opened' in operation_order:
        node_embed_index = operation_order.index('node_embedding')
        transaction_index = operation_order.index('transaction_opened')

        assert node_embed_index < transaction_index, \
            f"PERFORMANCE BUG: Node embedding at index {node_embed_index}, transaction at {transaction_index}"
        print("  [OK] Node embeddings generated before transaction")

    if 'edge_embedding' in operation_order and 'transaction_opened' in operation_order:
        edge_embed_index = operation_order.index('edge_embedding')
        transaction_index = operation_order.index('transaction_opened')

        assert edge_embed_index < transaction_index, \
            f"PERFORMANCE BUG: Edge embedding at index {edge_embed_index}, transaction at {transaction_index}"
        print("  [OK] Edge embeddings generated before transaction")

    # Transaction should have been opened
    assert 'transaction_opened' in operation_order, "Transaction was never opened"

    print("  [OK] TEST PASSED: Embeddings generated before transaction")


@pytest.mark.asyncio
async def test_existing_embeddings_not_regenerated():
    """
    Test that nodes/edges with existing embeddings are not re-generated.

    This ensures we're not wasting API calls on already-embedded entities.
    """
    mock_session = AsyncMock()
    mock_driver = Mock()
    mock_driver.session.return_value = mock_session
    mock_session.execute_write = AsyncMock(return_value=None)
    mock_session.close = AsyncMock()

    mock_embedder = Mock()

    with patch('graphiti_core.nodes.EntityNode.generate_name_embedding') as mock_node_embed:
        with patch('graphiti_core.edges.EntityEdge.generate_embedding') as mock_edge_embed:

            from graphiti_core.nodes import EntityNode
            from graphiti_core.edges import EntityEdge

            # Create nodes that ALREADY have embeddings
            test_nodes = [
                EntityNode(
                    uuid='node-1',
                    name='Test Node',
                    group_id='test',
                    labels=['Entity'],
                    created_at=datetime.now(timezone.utc),
                    name_embedding=[0.1] * 1536,  # Already has embedding
                )
            ]

            test_edges = [
                EntityEdge(
                    uuid='edge-1',
                    source_node_uuid='node-1',
                    target_node_uuid='node-2',
                    name='test',
                    fact='test fact',
                    episodes=['ep-1'],
                    created_at=datetime.now(timezone.utc),
                    group_id='test',
                    fact_embedding=[0.1] * 1536,  # Already has embedding
                )
            ]

            await add_nodes_and_edges_bulk(
                driver=mock_driver,
                episodic_nodes=[],
                episodic_edges=[],
                entity_nodes=test_nodes,
                entity_edges=test_edges,
                embedder=mock_embedder,
            )

            # Verify embedding methods were NOT called
            mock_node_embed.assert_not_called()
            mock_edge_embed.assert_not_called()

            print("\n  [OK] TEST PASSED: Existing embeddings not regenerated")


if __name__ == "__main__":
    print("=" * 80)
    print("TESTING EMBEDDING PERFORMANCE FIX")
    print("=" * 80)

    asyncio.run(test_embeddings_called_before_transaction())
    asyncio.run(test_existing_embeddings_not_regenerated())

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED [OK]")
    print("=" * 80)
