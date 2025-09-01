"""Performance benchmarks for FundCast components."""

import asyncio
import json
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import pytest
import pytest_benchmark
from httpx import AsyncClient

from src.api.async_tasks import TaskPriority, get_task_manager
from src.api.cache import CacheKey, get_cache
from src.api.database_optimization import get_optimized_db_session
from src.api.main import app


class BenchmarkMetrics:
    """Collect and analyze benchmark metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}

    def record(self, operation: str, duration: float):
        """Record operation duration."""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)

    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistical summary for operation."""
        if operation not in self.metrics:
            return {}

        durations = self.metrics[operation]
        return {
            "count": len(durations),
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "std": statistics.stdev(durations) if len(durations) > 1 else 0,
            "min": min(durations),
            "max": max(durations),
            "p95": (
                statistics.quantiles(durations, n=20)[18]
                if len(durations) > 20
                else max(durations)
            ),
            "p99": (
                statistics.quantiles(durations, n=100)[98]
                if len(durations) > 100
                else max(durations)
            ),
        }


@pytest.fixture
def benchmark_metrics():
    """Provide benchmark metrics collector."""
    return BenchmarkMetrics()


class TestCacheBenchmarks:
    """Cache performance benchmarks."""

    @pytest.mark.asyncio
    async def test_cache_set_performance(self, benchmark):
        """Benchmark cache set operations."""
        cache = await get_cache()

        def cache_set_sync():
            # Use new event loop for each benchmark run
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    cache.set("benchmark_key", "benchmark_value", ttl=300)
                )
            finally:
                loop.close()

        result = benchmark(cache_set_sync)

        # Verify the operation succeeded
        cached_value = await cache.get("benchmark_key")
        assert cached_value == "benchmark_value"

    @pytest.mark.asyncio
    async def test_cache_get_performance(self, benchmark):
        """Benchmark cache get operations."""
        cache = await get_cache()

        # Pre-populate cache
        await cache.set("benchmark_get_key", "benchmark_get_value", ttl=300)

        def cache_get_sync():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(cache.get("benchmark_get_key"))
            finally:
                loop.close()

        result = benchmark(cache_get_sync)
        assert result == "benchmark_get_value"

    @pytest.mark.asyncio
    async def test_cache_bulk_operations(self, benchmark_metrics):
        """Benchmark bulk cache operations."""
        cache = await get_cache()

        # Test different data sizes
        sizes = [10, 100, 1000, 5000]

        for size in sizes:
            # Prepare test data
            test_data = {f"bulk_key_{i}": f"bulk_value_{i}" for i in range(size)}

            # Benchmark bulk set
            start_time = time.time()
            for key, value in test_data.items():
                await cache.set(key, value, ttl=300)
            set_duration = time.time() - start_time
            benchmark_metrics.record(f"bulk_set_{size}", set_duration)

            # Benchmark bulk get
            start_time = time.time()
            for key in test_data.keys():
                await cache.get(key)
            get_duration = time.time() - start_time
            benchmark_metrics.record(f"bulk_get_{size}", get_duration)

        # Print results
        for size in sizes:
            set_stats = benchmark_metrics.get_stats(f"bulk_set_{size}")
            get_stats = benchmark_metrics.get_stats(f"bulk_get_{size}")

            print(f"\nSize {size}:")
            print(
                f"  Set: {set_stats['mean']:.4f}s ({size/set_stats['mean']:.0f} ops/sec)"
            )
            print(
                f"  Get: {get_stats['mean']:.4f}s ({size/get_stats['mean']:.0f} ops/sec)"
            )

    @pytest.mark.asyncio
    async def test_cache_memory_usage(self):
        """Benchmark cache memory usage."""
        cache = await get_cache()

        # Clear cache first
        await cache.clear()

        # Get initial stats
        initial_stats = await cache.get_stats()

        # Add data of various sizes
        data_sizes = [
            ("small", "x" * 100),  # 100 bytes
            ("medium", "x" * 10000),  # 10KB
            ("large", "x" * 1000000),  # 1MB
        ]

        for name, data in data_sizes:
            await cache.set(f"memory_test_{name}", data, ttl=600)

            stats = await cache.get_stats()
            print(f"\n{name.upper()} data added:")
            print(f"  L1 size: {stats.get('l1_cache', {}).get('size', 0)} keys")
            print(
                f"  L2 memory: {stats.get('l2_cache', {}).get('memory_usage', 0)} bytes"
            )


class TestDatabaseBenchmarks:
    """Database performance benchmarks."""

    @pytest.mark.asyncio
    async def test_connection_pool_performance(self, benchmark_metrics):
        """Benchmark database connection pool performance."""

        async def get_connection_time():
            start_time = time.time()
            async with get_optimized_db_session() as session:
                await session.execute_optimized("SELECT 1")
            return time.time() - start_time

        # Test concurrent connections
        connection_counts = [1, 5, 10, 20]

        for count in connection_counts:
            tasks = [get_connection_time() for _ in range(count)]

            start_time = time.time()
            durations = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            avg_connection_time = statistics.mean(durations)
            throughput = count / total_time

            benchmark_metrics.record(f"db_connections_{count}", avg_connection_time)

            print(f"\nConnections: {count}")
            print(f"  Avg connection time: {avg_connection_time:.4f}s")
            print(f"  Total time: {total_time:.4f}s")
            print(f"  Throughput: {throughput:.1f} conn/sec")

    @pytest.mark.asyncio
    async def test_query_performance_by_complexity(self, benchmark_metrics):
        """Benchmark queries of different complexity."""

        queries = {
            "simple_select": "SELECT 1 as test",
            "timestamp_select": "SELECT NOW() as current_time",
            "system_info": "SELECT version(), current_database(), current_user()",
            "table_info": """
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public'
                LIMIT 10
            """,
        }

        async with get_optimized_db_session() as session:
            for query_name, query in queries.items():
                # Warm up
                await session.execute_optimized(query)

                # Benchmark multiple runs
                durations = []
                for _ in range(10):
                    start_time = time.time()
                    await session.execute_optimized(query)
                    durations.append(time.time() - start_time)

                avg_duration = statistics.mean(durations)
                benchmark_metrics.record(query_name, avg_duration)

                print(f"\n{query_name}:")
                print(f"  Avg duration: {avg_duration:.4f}s")
                print(f"  Throughput: {1/avg_duration:.1f} queries/sec")

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, benchmark_metrics):
        """Benchmark bulk insert operations."""

        # Test different batch sizes
        batch_sizes = [100, 500, 1000, 2000]

        for batch_size in batch_sizes:
            # Generate test data
            test_data = [
                {
                    "id": f"test_bulk_{i}",
                    "name": f"Test Record {i}",
                    "value": random.randint(1, 1000),
                    "created_at": time.time(),
                }
                for i in range(batch_size)
            ]

            async with get_optimized_db_session() as session:
                start_time = time.time()

                # Create temporary table for testing
                await session.execute_optimized(
                    """
                    CREATE TEMP TABLE bulk_test (
                        id TEXT,
                        name TEXT,
                        value INTEGER,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """
                )

                # Perform bulk insert
                await session.bulk_insert_optimized("bulk_test", test_data)

                duration = time.time() - start_time
                throughput = batch_size / duration

                benchmark_metrics.record(f"bulk_insert_{batch_size}", duration)

                print(f"\nBulk insert - Batch size: {batch_size}")
                print(f"  Duration: {duration:.4f}s")
                print(f"  Throughput: {throughput:.1f} records/sec")


class TestTaskBenchmarks:
    """Async task performance benchmarks."""

    @pytest.mark.asyncio
    async def test_task_submission_performance(self, benchmark):
        """Benchmark task submission rate."""
        task_manager = await get_task_manager()

        # Register a simple test function
        async def simple_task(x: int) -> int:
            return x * 2

        task_manager.register_function("simple_task", simple_task)

        def submit_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    task_manager.submit_task("simple_task", 42)
                )
            finally:
                loop.close()

        task_id = benchmark(submit_task)
        assert task_id is not None

    @pytest.mark.asyncio
    async def test_task_execution_performance(self, benchmark_metrics):
        """Benchmark task execution with different priorities."""
        task_manager = await get_task_manager()

        # Register test functions with different complexities
        async def fast_task() -> str:
            return "fast_result"

        async def slow_task() -> str:
            await asyncio.sleep(0.1)  # 100ms delay
            return "slow_result"

        def cpu_intensive_task() -> int:
            # CPU-intensive task
            total = 0
            for i in range(100000):
                total += i * i
            return total

        task_manager.register_function("fast_task", fast_task)
        task_manager.register_function("slow_task", slow_task)
        task_manager.register_function("cpu_intensive_task", cpu_intensive_task)

        # Test different priorities
        priorities = [
            TaskPriority.LOW,
            TaskPriority.NORMAL,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL,
        ]

        for priority in priorities:
            # Submit multiple tasks
            task_ids = []
            start_time = time.time()

            for i in range(10):
                task_id = await task_manager.submit_task("fast_task", priority=priority)
                task_ids.append(task_id)

            # Wait for all tasks to complete
            while True:
                completed = 0
                for task_id in task_ids:
                    result = task_manager.get_task_result(task_id)
                    if result and result.status == "completed":
                        completed += 1

                if completed == len(task_ids):
                    break

                await asyncio.sleep(0.01)

            total_time = time.time() - start_time
            throughput = len(task_ids) / total_time

            benchmark_metrics.record(f"task_priority_{priority.value}", total_time)

            print(f"\nPriority {priority.value}:")
            print(f"  Total time: {total_time:.4f}s")
            print(f"  Throughput: {throughput:.1f} tasks/sec")


class TestAPIBenchmarks:
    """API endpoint performance benchmarks."""

    @pytest.mark.asyncio
    async def test_health_endpoint_performance(self, benchmark_metrics):
        """Benchmark health endpoint under load."""

        async def single_health_check():
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/health")
                return response.status_code == 200

        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 25, 50]

        for concurrency in concurrency_levels:
            start_time = time.time()

            # Create concurrent requests
            tasks = [single_health_check() for _ in range(concurrency)]
            results = await asyncio.gather(*tasks)

            total_time = time.time() - start_time
            success_rate = sum(results) / len(results)
            throughput = concurrency / total_time

            benchmark_metrics.record(f"health_endpoint_{concurrency}", total_time)

            print(f"\nConcurrency {concurrency}:")
            print(f"  Total time: {total_time:.4f}s")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Throughput: {throughput:.1f} req/sec")

    @pytest.mark.asyncio
    async def test_auth_endpoint_performance(self, benchmark_metrics):
        """Benchmark authentication endpoints."""

        # Test user registration
        async def register_user(user_id: int):
            user_data = {
                "email": f"benchmark_user_{user_id}@test.com",
                "password": "BenchmarkPassword123!",
                "full_name": f"Benchmark User {user_id}",
            }

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/auth/register", json=user_data)
                return response.status_code == 201

        # Test login
        async def login_user():
            login_data = {
                "email": "benchmark_user_1@test.com",
                "password": "BenchmarkPassword123!",
            }

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/auth/login", json=login_data)
                return response.status_code == 200

        # Benchmark registration
        start_time = time.time()
        reg_tasks = [register_user(i) for i in range(10)]
        reg_results = await asyncio.gather(*reg_tasks, return_exceptions=True)
        reg_time = time.time() - start_time
        reg_success = sum(1 for r in reg_results if r is True) / len(reg_results)

        # Benchmark login (after first user is created)
        start_time = time.time()
        login_tasks = [login_user() for _ in range(20)]
        login_results = await asyncio.gather(*login_tasks, return_exceptions=True)
        login_time = time.time() - start_time
        login_success = sum(1 for r in login_results if r is True) / len(login_results)

        print(f"\nAuth Performance:")
        print(
            f"  Registration: {len(reg_tasks)/reg_time:.1f} req/sec (success: {reg_success:.2%})"
        )
        print(
            f"  Login: {len(login_tasks)/login_time:.1f} req/sec (success: {login_success:.2%})"
        )


class TestMemoryBenchmarks:
    """Memory usage benchmarks."""

    def test_object_creation_memory(self):
        """Benchmark memory usage of object creation."""
        import gc
        import tracemalloc

        # Test different object types
        object_types = {
            "users": lambda i: {
                "id": f"user_{i}",
                "email": f"user{i}@test.com",
                "name": f"User {i}",
                "metadata": {"created": time.time(), "active": True},
            },
            "companies": lambda i: {
                "id": f"company_{i}",
                "name": f"Company {i}",
                "industry": "Technology",
                "employees": random.randint(1, 1000),
            },
            "markets": lambda i: {
                "id": f"market_{i}",
                "title": f"Market {i}",
                "type": "binary",
                "metadata": {"odds": random.random()},
            },
        }

        for obj_type, factory in object_types.items():
            # Start memory tracing
            tracemalloc.start()

            # Create objects
            objects = []
            for i in range(1000):
                objects.append(factory(i))

            # Get memory stats
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Force garbage collection
            del objects
            gc.collect()

            print(f"\n{obj_type.upper()} Memory Usage:")
            print(f"  Current: {current / 1024 / 1024:.2f} MB")
            print(f"  Peak: {peak / 1024 / 1024:.2f} MB")
            print(f"  Per object: {peak / 1000 / 1024:.2f} KB")


# Custom benchmark markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "benchmark: mark test as performance benchmark")
    config.addinivalue_line(
        "markers", "slow_benchmark: mark test as slow performance benchmark"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
