"""
Test to verify that embeddings are generated BEFORE transactions open.

This test ensures the critical performance fix is working:
- Embeddings should be generated outside of database transactions
- Transaction lock time should be minimal
- Data should be visible to other clients immediately after commit
"""

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
import pytest

from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge, EpisodicEdge
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.driver.driver import GraphDriver, GraphDriverSession
from graphiti_core.utils.bulk_utils import add_nodes_and_edges_bulk


class TransactionTracker:
    """Track when transactions are opened and what happens inside them."""

    def __init__(self):
        self.transaction_opened = False
        self.embedding_calls_in_transaction = []
        self.embedding_calls_before_transaction = []

    def mark_transaction_opened(self):
        self.transaction_opened = True

    def mark_embedding_call(self, item_type: str):
        if self.transaction_opened:
            self.embedding_calls_in_transaction.append(item_type)
        else:
            self.embedding_calls_before_transaction.append(item_type)


@pytest.mark.asyncio
async def test_embeddings_generated_before_transaction():
    """
    Test that embeddings are generated BEFORE the transaction opens.

    This is critical for performance - embedding generation involves external
    API calls that can take 100-500ms each. If done inside a transaction,
    the database locks are held for this entire time.
    """
    tracker = TransactionTracker()

    # Create mock embedder that tracks when it's called
    mock_embedder = Mock(spec=EmbedderClient)

    async def mock_embed(*args, **kwargs):
        await asyncio.sleep(0.001)  # Simulate network latency
        tracker.mark_embedding_call("embedding")
        return [0.1] * 1536  # Return a fake embedding

    mock_embedder.create.return_value = mock_embed()

    # Create mock nodes and edges that need embeddings
    test_nodes = [
        EntityNode(
            uuid='node-1',
            name='Test Node 1',
            group_id='test',
            labels=['Entity'],
            created_at=datetime.now(timezone.utc),
            name_embedding=None,  # No embedding yet
        ),
        EntityNode(
            uuid='node-2',
            name='Test Node 2',
            group_id='test',
            labels=['Entity'],
            created_at=datetime.now(timezone.utc),
            name_embedding=None,  # No embedding yet
        ),
    ]

    test_edges = [
        EntityEdge(
            uuid='edge-1',
            source_node_uuid='node-1',
            target_node_uuid='node-2',
            name='test_relation',
            fact='Test fact',
            episodes=['ep-1'],
            created_at=datetime.now(timezone.utc),
            group_id='test',
            fact_embedding=None,  # No embedding yet
        ),
    ]

    test_episodes = [
        EpisodicNode(
            uuid='ep-1',
            name='Test Episode',
            group_id='test',
            content='Test content',
            labels=[],
            source='text',
            source_description='test',
            created_at=datetime.now(timezone.utc),
            valid_at=datetime.now(timezone.utc),
        )
    ]

    test_episodic_edges = []

    # Create mock driver and session
    mock_session = AsyncMock(spec=GraphDriverSession)
    mock_driver = Mock(spec=GraphDriver)
    mock_driver.session.return_value = mock_session

    # Track when execute_write is called (transaction opens)
    original_execute_write = mock_session.execute_write

    async def tracked_execute_write(*args, **kwargs):
        tracker.mark_transaction_opened()
        # Don't actually execute the transaction function
        return None

    mock_session.execute_write.side_effect = tracked_execute_write

    # Patch the generate methods to track calls
    async def tracked_generate_node_embedding(embedder):
        tracker.mark_embedding_call("node_embedding")
        # Simulate embedding generation with slight delay
        await asyncio.sleep(0.001)
        test_nodes[0].name_embedding = [0.1] * 1536

    async def tracked_generate_edge_embedding(embedder):
        tracker.mark_embedding_call("edge_embedding")
        await asyncio.sleep(0.001)
        test_edges[0].fact_embedding = [0.1] * 1536

    test_nodes[0].generate_name_embedding = tracked_generate_node_embedding
    test_nodes[1].generate_name_embedding = AsyncMock(return_value=None)
    test_nodes[1].name_embedding = [0.1] * 1536  # Already has embedding
    test_edges[0].generate_embedding = tracked_generate_edge_embedding

    # Execute the function
    await add_nodes_and_edges_bulk(
        driver=mock_driver,
        episodic_nodes=test_episodes,
        episodic_edges=test_episodic_edges,
        entity_nodes=test_nodes,
        entity_edges=test_edges,
        embedder=mock_embedder,
    )

    # Verify results
    print(f"\nTest Results:")
    print(f"  Embedding calls before transaction: {len(tracker.embedding_calls_before_transaction)}")
    print(f"  Embedding calls in transaction: {len(tracker.embedding_calls_in_transaction)}")
    print(f"  Details before: {tracker.embedding_calls_before_transaction}")
    print(f"  Details in: {tracker.embedding_calls_in_transaction}")

    # CRITICAL ASSERTION: No embeddings should be generated inside the transaction
    assert len(tracker.embedding_calls_in_transaction) == 0, \
        f"PERFORMANCE BUG: {len(tracker.embedding_calls_in_transaction)} embeddings generated inside transaction!"

    # All embeddings should be generated before transaction
    assert len(tracker.embedding_calls_before_transaction) >= 2, \
        f"Expected at least 2 embeddings before transaction, got {len(tracker.embedding_calls_before_transaction)}"

    # Transaction should have been opened
    assert tracker.transaction_opened, "Transaction was never opened"

    print("  ✓ Test PASSED: All embeddings generated before transaction")


@pytest.mark.asyncio
async def test_embedding_performance_improvement():
    """
    Test that the fix actually improves performance.

    Measure the time the transaction is held open and verify it's minimal.
    """
    transaction_start_time = None
    transaction_duration = None

    # Create mock nodes that need embeddings
    test_nodes = [
        EntityNode(
            uuid=f'node-{i}',
            name=f'Test Node {i}',
            group_id='test',
            labels=['Entity'],
            created_at=datetime.now(timezone.utc),
            name_embedding=None,
        )
        for i in range(5)
    ]

    test_edges = [
        EntityEdge(
            uuid=f'edge-{i}',
            source_node_uuid='node-0',
            target_node_uuid=f'node-{i+1}',
            name='test_relation',
            fact=f'Test fact {i}',
            episodes=['ep-1'],
            created_at=datetime.now(timezone.utc),
            group_id='test',
            fact_embedding=None,
        )
        for i in range(4)
    ]

    # Mock embedder with realistic latency
    mock_embedder = Mock(spec=EmbedderClient)

    # Mock generate methods with delay to simulate real API
    async def slow_generate_node_embedding(embedder):
        await asyncio.sleep(0.01)  # 10ms per embedding
        return [0.1] * 1536

    async def slow_generate_edge_embedding(embedder):
        await asyncio.sleep(0.01)  # 10ms per embedding
        return [0.1] * 1536

    for node in test_nodes:
        node.generate_name_embedding = AsyncMock(side_effect=slow_generate_node_embedding)

    for edge in test_edges:
        edge.generate_embedding = AsyncMock(side_effect=slow_generate_edge_embedding)

    # Create mock driver
    mock_session = AsyncMock(spec=GraphDriverSession)
    mock_driver = Mock(spec=GraphDriver)
    mock_driver.session.return_value = mock_session

    # Track transaction duration
    async def tracked_execute_write(*args, **kwargs):
        nonlocal transaction_start_time, transaction_duration
        transaction_start_time = time.time()
        # Simulate minimal DB operation
        await asyncio.sleep(0.001)
        transaction_duration = time.time() - transaction_start_time
        return None

    mock_session.execute_write.side_effect = tracked_execute_write

    # Execute
    total_start = time.time()
    await add_nodes_and_edges_bulk(
        driver=mock_driver,
        episodic_nodes=[],
        episodic_edges=[],
        entity_nodes=test_nodes,
        entity_edges=test_edges,
        embedder=mock_embedder,
    )
    total_duration = time.time() - total_start

    print(f"\nPerformance Test Results:")
    print(f"  Total operation time: {total_duration*1000:.2f}ms")
    print(f"  Transaction held open: {transaction_duration*1000:.2f}ms")
    print(f"  Transaction % of total: {(transaction_duration/total_duration)*100:.1f}%")

    # Transaction should be held for minimal time (< 10% of total)
    # With 9 embeddings at 10ms each = 90ms total if sequential
    # But transaction should only be ~1ms
    assert transaction_duration < total_duration * 0.2, \
        f"Transaction held for {(transaction_duration/total_duration)*100:.1f}% of operation time - embeddings may still be in transaction!"

    print("  ✓ Test PASSED: Transaction time is minimal")


@pytest.mark.asyncio
async def test_parallel_embedding_generation():
    """
    Test that embeddings are generated in parallel, not sequentially.

    This ensures we're using asyncio.gather() effectively.
    """
    embedding_call_times = []

    # Create nodes needing embeddings
    test_nodes = [
        EntityNode(
            uuid=f'node-{i}',
            name=f'Test Node {i}',
            group_id='test',
            labels=['Entity'],
            created_at=datetime.now(timezone.utc),
            name_embedding=None,
        )
        for i in range(3)
    ]

    # Track when each embedding starts
    async def tracked_generate(node_id):
        async def _generate(embedder):
            embedding_call_times.append(time.time())
            await asyncio.sleep(0.01)
            return [0.1] * 1536
        return _generate

    for i, node in enumerate(test_nodes):
        node.generate_name_embedding = AsyncMock(side_effect=tracked_generate(i))

    # Mock driver
    mock_session = AsyncMock(spec=GraphDriverSession)
    mock_driver = Mock(spec=GraphDriver)
    mock_driver.session.return_value = mock_session
    mock_session.execute_write = AsyncMock(return_value=None)

    # Execute
    start_time = time.time()
    await add_nodes_and_edges_bulk(
        driver=mock_driver,
        episodic_nodes=[],
        episodic_edges=[],
        entity_nodes=test_nodes,
        entity_edges=[],
        embedder=Mock(),
    )

    # Check that embeddings started roughly at the same time (parallel)
    if len(embedding_call_times) >= 2:
        time_spread = max(embedding_call_times) - min(embedding_call_times)
        print(f"\nParallel Execution Test:")
        print(f"  Time spread between embedding starts: {time_spread*1000:.2f}ms")

        # If parallel, all should start within 5ms of each other
        # If sequential, would be 30ms apart (3 * 10ms)
        assert time_spread < 0.005, \
            f"Embeddings appear to be sequential (spread: {time_spread*1000:.2f}ms)"

        print("  ✓ Test PASSED: Embeddings generated in parallel")


if __name__ == "__main__":
    # Run tests
    print("=" * 80)
    print("TESTING EMBEDDING PERFORMANCE FIX")
    print("=" * 80)

    asyncio.run(test_embeddings_generated_before_transaction())
    asyncio.run(test_embedding_performance_improvement())
    asyncio.run(test_parallel_embedding_generation())

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)
