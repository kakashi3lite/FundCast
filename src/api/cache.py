"""Advanced multi-layer caching with Redis and in-memory fallback."""

import asyncio
import hashlib
import json
import pickle
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis
import structlog
from pydantic import BaseModel

from .config import settings

logger = structlog.get_logger(__name__)


class CacheStats(BaseModel):
    """Cache statistics for monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    memory_usage: int = 0

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheKey:
    """Type-safe cache key builder."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def build(self, *args: Any, **kwargs: Any) -> str:
        """Build a consistent cache key from arguments."""
        key_parts = [self.prefix]

        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # Hash complex objects for consistent keys
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")

        return ":".join(key_parts)


class InMemoryCache:
    """High-performance in-memory cache with LRU eviction."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self.stats = CacheStats()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        now = time.time()

        if key not in self._cache:
            self.stats.misses += 1
            return None

        entry = self._cache[key]

        # Check TTL
        if entry["expires_at"] < now:
            await self.delete(key)
            self.stats.misses += 1
            return None

        # Update access time for LRU
        self._access_times[key] = now
        self.stats.hits += 1
        return entry["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        now = time.time()
        ttl = ttl or self.default_ttl

        # Evict if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            await self._evict_lru()

        self._cache[key] = {"value": value, "created_at": now, "expires_at": now + ttl}
        self._access_times[key] = now

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            del self._access_times[key]
            return True
        return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_times.clear()
        self.stats = CacheStats()

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_times:
            return

        lru_key = min(self._access_times, key=self._access_times.get)
        await self.delete(lru_key)
        self.stats.evictions += 1


class RedisCache:
    """Redis-backed cache with advanced features."""

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.is_available = False
        self.stats = CacheStats()

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                max_connections=20,
                retry_on_timeout=True,
            )
            await self.client.ping()
            self.is_available = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(
                "Redis connection failed, using in-memory cache", error=str(e)
            )
            self.is_available = False

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self.is_available:
            return None

        try:
            data = await self.client.get(key)
            if data is None:
                self.stats.misses += 1
                return None

            # Try JSON first, fallback to pickle
            try:
                value = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                value = pickle.loads(data)

            self.stats.hits += 1
            return value

        except Exception as e:
            logger.warning("Redis get failed", key=key, error=str(e))
            self.stats.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        if not self.is_available:
            return False

        try:
            # Try JSON first, fallback to pickle
            try:
                data = json.dumps(value)
            except (TypeError, ValueError):
                data = pickle.dumps(value)

            if ttl:
                result = await self.client.setex(key, ttl, data)
            else:
                result = await self.client.set(key, data)

            return bool(result)

        except Exception as e:
            logger.warning("Redis set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        if not self.is_available:
            return False

        try:
            result = await self.client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning("Redis delete failed", key=key, error=str(e))
            return False

    async def clear(self) -> bool:
        """Clear all cache entries."""
        if not self.is_available:
            return False

        try:
            await self.client.flushdb()
            return True
        except Exception as e:
            logger.error("Redis clear failed", error=str(e))
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics."""
        if not self.is_available:
            return {}

        try:
            info = await self.client.info("memory")
            return {
                "memory_usage": info.get("used_memory", 0),
                "peak_memory": info.get("used_memory_peak", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception:
            return {}


class MultiLayerCache:
    """Multi-layer cache with L1 (in-memory) and L2 (Redis) tiers."""

    def __init__(self):
        self.l1_cache = InMemoryCache(max_size=500, ttl=300)  # 5 min TTL
        self.l2_cache = RedisCache()
        self._connected = False

    async def connect(self) -> None:
        """Initialize cache layers."""
        if not self._connected:
            await self.l2_cache.connect()
            self._connected = True

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 first, then L2)."""
        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            return value

        # Try L2 cache
        value = await self.l2_cache.get(key)
        if value is not None:
            # Populate L1 cache
            await self.l1_cache.set(key, value, ttl=300)
            return value

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in both cache layers."""
        # Set in L1 with shorter TTL
        l1_ttl = min(ttl or 3600, 300)
        await self.l1_cache.set(key, value, l1_ttl)

        # Set in L2 with full TTL
        await self.l2_cache.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        """Delete key from both cache layers."""
        await self.l1_cache.delete(key)
        await self.l2_cache.delete(key)

    async def clear(self) -> None:
        """Clear both cache layers."""
        await self.l1_cache.clear()
        await self.l2_cache.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        l2_stats = await self.l2_cache.get_stats()

        return {
            "l1_cache": {
                "hits": self.l1_cache.stats.hits,
                "misses": self.l1_cache.stats.misses,
                "hit_ratio": self.l1_cache.stats.hit_ratio,
                "size": len(self.l1_cache._cache),
                "evictions": self.l1_cache.stats.evictions,
            },
            "l2_cache": {
                "hits": self.l2_cache.stats.hits,
                "misses": self.l2_cache.stats.misses,
                "hit_ratio": self.l2_cache.stats.hit_ratio,
                "available": self.l2_cache.is_available,
                **l2_stats,
            },
        }


# Global cache instance
_cache: Optional[MultiLayerCache] = None


async def get_cache() -> MultiLayerCache:
    """Get or create cache instance."""
    global _cache
    if _cache is None:
        _cache = MultiLayerCache()
        await _cache.connect()
    return _cache


def cache(
    ttl: int = 3600,
    key_builder: Optional[CacheKey] = None,
    skip_cache_if: Optional[Callable] = None,
):
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        cache_key = key_builder or CacheKey(f"{func.__module__}.{func.__name__}")

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip cache if condition is met
            if skip_cache_if and skip_cache_if(*args, **kwargs):
                return await func(*args, **kwargs)

            # Build cache key
            key = cache_key.build(*args, **kwargs)

            # Try to get from cache
            cache_instance = await get_cache()
            cached_result = await cache_instance.get(key)

            if cached_result is not None:
                logger.debug("Cache hit", function=func.__name__, key=key)
                return cached_result

            # Execute function and cache result
            logger.debug("Cache miss", function=func.__name__, key=key)
            result = await func(*args, **kwargs)

            # Cache the result
            await cache_instance.set(key, result, ttl)

            return result

        # Add cache management methods
        wrapper.cache_key = cache_key
        wrapper.clear_cache = lambda *args, **kwargs: asyncio.create_task(
            _clear_cache_for_function(cache_key, *args, **kwargs)
        )

        return wrapper

    return decorator


async def _clear_cache_for_function(cache_key: CacheKey, *args, **kwargs):
    """Clear cache for specific function call."""
    key = cache_key.build(*args, **kwargs)
    cache_instance = await get_cache()
    await cache_instance.delete(key)


# Cache warming utilities
async def warm_cache(warmup_functions: List[Callable]) -> None:
    """Warm cache by pre-executing common queries."""
    logger.info("Starting cache warm-up", function_count=len(warmup_functions))

    tasks = []
    for func in warmup_functions:
        if asyncio.iscoroutinefunction(func):
            tasks.append(func())
        else:
            # Convert sync function to async
            tasks.append(asyncio.to_thread(func))

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Cache warm-up completed")
    except Exception as e:
        logger.error("Cache warm-up failed", error=str(e))


# Context manager for cache transactions
class CacheTransaction:
    """Context manager for cache transactions with rollback."""

    def __init__(self, cache: MultiLayerCache):
        self.cache = cache
        self.operations: List[Dict[str, Any]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Rollback on exception
            await self._rollback()
        return False

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Add set operation to transaction."""
        # Store original value for rollback
        original = await self.cache.get(key)
        self.operations.append(
            {
                "type": "set",
                "key": key,
                "original_value": original,
                "new_value": value,
                "ttl": ttl,
            }
        )
        await self.cache.set(key, value, ttl)

    async def delete(self, key: str):
        """Add delete operation to transaction."""
        original = await self.cache.get(key)
        self.operations.append(
            {"type": "delete", "key": key, "original_value": original}
        )
        await self.cache.delete(key)

    async def _rollback(self):
        """Rollback all operations."""
        logger.warning("Rolling back cache transaction")
        for op in reversed(self.operations):
            try:
                if op["type"] == "set":
                    if op["original_value"] is not None:
                        await self.cache.set(op["key"], op["original_value"])
                    else:
                        await self.cache.delete(op["key"])
                elif op["type"] == "delete":
                    if op["original_value"] is not None:
                        await self.cache.set(op["key"], op["original_value"])
            except Exception as e:
                logger.error("Cache rollback failed", key=op["key"], error=str(e))
