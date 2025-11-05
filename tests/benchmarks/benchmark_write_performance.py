"""
Performance benchmark for Graphiti memory write operations.

This benchmark tests:
1. Single episode write time
2. Multiple episode write times
3. Time to read after write (commit visibility)
4. Large episode write performance
5. Concurrent write scenarios
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
import statistics
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

# Load environment variables
load_dotenv()

# Get database credentials from environment
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'test')


class BenchmarkResults:
    """Container for benchmark results."""

    def __init__(self):
        self.results: dict[str, list[float]] = {}

    def add(self, test_name: str, duration_ms: float):
        """Add a result."""
        if test_name not in self.results:
            self.results[test_name] = []
        self.results[test_name].append(duration_ms)

    def report(self):
        """Generate a report of all results."""
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS")
        print("=" * 80 + "\n")

        for test_name, durations in self.results.items():
            if not durations:
                continue

            mean = statistics.mean(durations)
            median = statistics.median(durations)
            stdev = statistics.stdev(durations) if len(durations) > 1 else 0
            min_val = min(durations)
            max_val = max(durations)

            print(f"{test_name}")
            print(f"  Runs: {len(durations)}")
            print(f"  Mean: {mean:.2f} ms")
            print(f"  Median: {median:.2f} ms")
            print(f"  StdDev: {stdev:.2f} ms")
            print(f"  Min: {min_val:.2f} ms")
            print(f"  Max: {max_val:.2f} ms")
            print()


async def test_single_episode_write(graphiti: Graphiti, group_id: str, results: BenchmarkResults, iteration: int):
    """Test writing a single episode and measure time."""
    episode_name = f"Test Episode {iteration}"
    episode_body = f"This is test episode number {iteration} with some content to process."

    start = time.time()

    await graphiti.add_episode(
        name=episode_name,
        episode_body=episode_body,
        source_description="benchmark test",
        reference_time=datetime.now(timezone.utc),
        source=EpisodeType.text,
        group_id=group_id,
    )

    duration_ms = (time.time() - start) * 1000
    results.add("Single Episode Write", duration_ms)

    return duration_ms


async def test_write_then_read(graphiti: Graphiti, group_id: str, results: BenchmarkResults, iteration: int):
    """Test write followed by immediate read to measure commit visibility."""
    episode_name = f"Read Test Episode {iteration}"
    episode_body = f"Testing read-after-write for iteration {iteration}"

    # Write the episode
    write_start = time.time()
    await graphiti.add_episode(
        name=episode_name,
        episode_body=episode_body,
        source_description="read test",
        reference_time=datetime.now(timezone.utc),
        source=EpisodeType.text,
        group_id=group_id,
    )
    write_duration = (time.time() - write_start) * 1000
    results.add("Write (for read test)", write_duration)

    # Immediately try to search for related content
    read_start = time.time()
    search_results = await graphiti.search(
        query=f"Episode {iteration}",
        group_ids=[group_id],
    )
    read_duration = (time.time() - read_start) * 1000
    results.add("Read After Write", read_duration)

    # Total time from write start to successful read
    total_duration = (time.time() - write_start) * 1000
    results.add("Write-to-Read Total Time", total_duration)

    return {
        'write_ms': write_duration,
        'read_ms': read_duration,
        'total_ms': total_duration,
        'found': len(search_results.nodes) > 0 or len(search_results.edges) > 0
    }


async def test_large_episode_write(graphiti: Graphiti, group_id: str, results: BenchmarkResults, size_kb: int, iteration: int):
    """Test writing a large episode."""
    # Generate content of specified size
    content = "Lorem ipsum dolor sit amet. " * (size_kb * 1024 // 28)
    episode_name = f"Large Episode {size_kb}KB #{iteration}"

    start = time.time()

    await graphiti.add_episode(
        name=episode_name,
        episode_body=content,
        source_description=f"benchmark test {size_kb}KB",
        reference_time=datetime.now(timezone.utc),
        source=EpisodeType.text,
        group_id=group_id,
    )

    duration_ms = (time.time() - start) * 1000
    results.add(f"Large Episode Write ({size_kb}KB)", duration_ms)

    return duration_ms


async def test_sequential_writes(graphiti: Graphiti, group_id: str, results: BenchmarkResults, count: int):
    """Test multiple sequential writes."""
    total_start = time.time()

    for i in range(count):
        await test_single_episode_write(graphiti, group_id, results, i)

    total_duration = (time.time() - total_start) * 1000
    results.add(f"Sequential {count} Writes (Total)", total_duration)

    return total_duration


async def test_concurrent_writes(graphiti: Graphiti, group_id: str, results: BenchmarkResults, count: int):
    """Test concurrent writes to different group_ids."""
    start = time.time()

    tasks = []
    for i in range(count):
        episode_name = f"Concurrent Episode {i}"
        episode_body = f"This is concurrent episode number {i}"

        task = graphiti.add_episode(
            name=episode_name,
            episode_body=episode_body,
            source_description="concurrent test",
            reference_time=datetime.now(timezone.utc),
            source=EpisodeType.text,
            group_id=f"{group_id}_concurrent_{i}",
        )
        tasks.append(task)

    # Wait for all to complete
    await asyncio.gather(*tasks)

    duration_ms = (time.time() - start) * 1000
    results.add(f"Concurrent {count} Writes (Total)", duration_ms)
    results.add(f"Concurrent {count} Writes (Avg per write)", duration_ms / count)

    return duration_ms


async def test_same_group_sequential(graphiti: Graphiti, group_id: str, results: BenchmarkResults, count: int):
    """Test sequential writes to the same group_id (as would happen in MCP queue)."""
    print(f"\n  Testing {count} sequential writes to same group_id...")

    durations = []
    for i in range(count):
        start = time.time()

        await graphiti.add_episode(
            name=f"Same Group Episode {i}",
            episode_body=f"Sequential episode {i} in same group",
            source_description="same group test",
            reference_time=datetime.now(timezone.utc),
            source=EpisodeType.text,
            group_id=group_id,
        )

        duration_ms = (time.time() - start) * 1000
        durations.append(duration_ms)

        # Track individual and total
        results.add(f"Same Group Sequential Write #{i+1}", duration_ms)

    total = sum(durations)
    avg = statistics.mean(durations)

    results.add(f"Same Group {count} Writes (Total)", total)
    results.add(f"Same Group {count} Writes (Avg)", avg)

    # Check if writes are getting slower over time
    if len(durations) >= 3:
        first_half = statistics.mean(durations[:len(durations)//2])
        second_half = statistics.mean(durations[len(durations)//2:])
        degradation_pct = ((second_half - first_half) / first_half) * 100

        print(f"    First half avg: {first_half:.2f} ms")
        print(f"    Second half avg: {second_half:.2f} ms")
        print(f"    Performance change: {degradation_pct:+.1f}%")

    return durations


async def run_benchmarks():
    """Run all benchmarks."""
    print("\n" + "=" * 80)
    print("GRAPHITI WRITE PERFORMANCE BENCHMARK")
    print("=" * 80)

    # Initialize Graphiti
    print("\nInitializing Graphiti...")
    print(f"  Database: {NEO4J_URI}")
    print(f"  User: {NEO4J_USER}")

    graphiti = Graphiti(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
    )

    await graphiti.build_indices_and_constraints()

    results = BenchmarkResults()
    group_id = "benchmark_group"

    # Test 1: Single episode writes (baseline)
    print("\n[Test 1] Single Episode Writes (5 iterations)...")
    for i in range(5):
        duration = await test_single_episode_write(graphiti, group_id, results, i)
        print(f"  Iteration {i+1}: {duration:.2f} ms")

    # Test 2: Write-then-read (commit visibility)
    print("\n[Test 2] Write-Then-Read Tests (3 iterations)...")
    for i in range(3):
        result = await test_write_then_read(graphiti, f"{group_id}_read", results, i)
        print(f"  Iteration {i+1}: Write={result['write_ms']:.2f}ms, Read={result['read_ms']:.2f}ms, Total={result['total_ms']:.2f}ms, Found={result['found']}")

    # Test 3: Large episodes
    print("\n[Test 3] Large Episode Writes...")
    for size_kb in [10, 50, 100]:
        duration = await test_large_episode_write(graphiti, f"{group_id}_large", results, size_kb, 0)
        print(f"  {size_kb}KB: {duration:.2f} ms")

    # Test 4: Sequential writes (same group)
    print("\n[Test 4] Sequential Writes to Same Group (10 episodes)...")
    durations = await test_same_group_sequential(graphiti, f"{group_id}_seq", results, 10)

    # Test 5: Concurrent writes (different groups)
    print("\n[Test 5] Concurrent Writes to Different Groups...")
    for count in [5, 10]:
        duration = await test_concurrent_writes(graphiti, f"{group_id}_concurrent", results, count)
        print(f"  {count} concurrent writes: {duration:.2f} ms total, {duration/count:.2f} ms avg")

    # Generate report
    results.report()

    # Close Graphiti
    await graphiti.close()

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
