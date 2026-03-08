"""Redis-backed PNCP response cache (TD-026)."""

import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default TTL: 4 hours (matches in-memory cache)
DEFAULT_CACHE_TTL = 4 * 3600


class RedisCache:
    """Redis-backed cache for PNCP API responses.

    Replaces the in-memory cache in PNCPClient with a shared, persistent cache.
    Gracefully degrades to no-cache behavior on Redis connection failure.

    Args:
        redis: An async Redis client instance (redis.asyncio.Redis).
        ttl: Time-to-live in seconds for cache entries.
        prefix: Redis key prefix for namespacing.
    """

    def __init__(self, redis, ttl: int = DEFAULT_CACHE_TTL, prefix: str = "pncp_cache") -> None:
        self._redis = redis
        self._ttl = ttl
        self._prefix = prefix
        self._hits = 0
        self._misses = 0

    def _key(self, cache_key: str) -> str:
        return f"{self._prefix}:{cache_key}"

    @staticmethod
    def make_cache_key(uf: str | None, modalidade: int, data_inicial: str, data_final: str) -> str:
        """Generate cache key from query parameters."""
        return f"{uf or 'ALL'}:{modalidade}:{data_inicial}:{data_final}"

    async def get(self, cache_key: str) -> Optional[list]:
        """Get cached data. Returns None on miss or error."""
        try:
            data = await self._redis.get(self._key(cache_key))
            if data is None:
                self._misses += 1
                return None
            self._hits += 1
            return json.loads(data)
        except Exception as e:
            logger.warning("Redis cache get failed for %s: %s", cache_key, e)
            self._misses += 1
            return None

    async def put(self, cache_key: str, data: list) -> None:
        """Store data in cache with TTL."""
        try:
            await self._redis.setex(
                self._key(cache_key),
                self._ttl,
                json.dumps(data),
            )
        except Exception as e:
            logger.warning("Redis cache put failed for %s: %s", cache_key, e)

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / total, 3) if total > 0 else 0.0,
        }

    async def clear(self) -> int:
        """Clear all cache entries matching the prefix. Returns count removed."""
        try:
            pattern = f"{self._prefix}:*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
            self._hits = 0
            self._misses = 0
            return len(keys)
        except Exception as e:
            logger.warning("Redis cache clear failed: %s", e)
            return 0

    async def entry_count(self) -> int:
        """Count cache entries (approximate)."""
        try:
            count = 0
            async for _ in self._redis.scan_iter(match=f"{self._prefix}:*"):
                count += 1
            return count
        except Exception:
            return 0
