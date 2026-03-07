"""Unit tests for Redis cache and async PNCP client cache integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cache.redis_cache import RedisCache


class TestRedisCache:
    """Test RedisCache with mock Redis."""

    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.get = AsyncMock(return_value=None)
        r.setex = AsyncMock()
        r.delete = AsyncMock()
        r.scan_iter = MagicMock()
        return r

    @pytest.fixture
    def cache(self, mock_redis):
        return RedisCache(redis=mock_redis, ttl=3600)

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        result = await cache.get("nonexistent")
        assert result is None
        assert cache._misses == 1

    @pytest.mark.asyncio
    async def test_cache_hit_returns_data(self, cache, mock_redis):
        import json
        data = [{"id": 1}, {"id": 2}]
        mock_redis.get = AsyncMock(return_value=json.dumps(data))
        result = await cache.get("key1")
        assert result == data
        assert cache._hits == 1

    @pytest.mark.asyncio
    async def test_cache_put(self, cache, mock_redis):
        data = [{"id": 1}]
        await cache.put("key1", data)
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache, mock_redis):
        import json
        mock_redis.get = AsyncMock(side_effect=[
            json.dumps([{"id": 1}]),  # hit
            json.dumps([{"id": 1}]),  # hit
            None,  # miss
        ])
        await cache.get("key1")
        await cache.get("key1")
        await cache.get("missing")

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == pytest.approx(0.667, abs=0.001)

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache, mock_redis):
        # Mock scan_iter to return some keys
        async def mock_scan_iter(match=None):
            for key in [b"pncp_cache:key1", b"pncp_cache:key2"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter
        removed = await cache.clear()
        assert removed == 2
        mock_redis.delete.assert_called_once()

    def test_make_cache_key_with_uf(self):
        key = RedisCache.make_cache_key("SP", 6, "2024-01-01", "2024-01-30")
        assert key == "SP:6:2024-01-01:2024-01-30"

    def test_make_cache_key_without_uf(self):
        key = RedisCache.make_cache_key(None, 6, "2024-01-01", "2024-01-30")
        assert key == "ALL:6:2024-01-01:2024-01-30"

    def test_different_params_different_keys(self):
        key1 = RedisCache.make_cache_key("SP", 6, "2024-01-01", "2024-01-30")
        key2 = RedisCache.make_cache_key("RJ", 6, "2024-01-01", "2024-01-30")
        key3 = RedisCache.make_cache_key("SP", 7, "2024-01-01", "2024-01-30")
        assert key1 != key2
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_redis_error(self, cache, mock_redis):
        mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        result = await cache.get("key1")
        assert result is None
        assert cache._misses == 1

    @pytest.mark.asyncio
    async def test_put_graceful_on_redis_error(self, cache, mock_redis):
        mock_redis.setex = AsyncMock(side_effect=ConnectionError("Redis down"))
        # Should not raise
        await cache.put("key1", [{"id": 1}])


class TestCacheEndpoints:
    """Test /cache/stats and /cache/clear API endpoints."""

    def test_cache_stats_endpoint(self, monkeypatch):
        monkeypatch.setattr("main._debug_enabled", True)
        from unittest.mock import AsyncMock as AM, Mock
        mock_source = Mock()
        mock_source.cache_stats = AM(return_value={"entries": 0, "hits": 0, "misses": 0, "hit_ratio": 0.0})

        from main import app
        from dependencies import get_pncp_source
        app.dependency_overrides[get_pncp_source] = lambda: mock_source

        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "hits" in data
        assert "misses" in data

        app.dependency_overrides.pop(get_pncp_source, None)

    def test_cache_clear_endpoint(self, monkeypatch):
        monkeypatch.setattr("main._debug_enabled", True)
        from unittest.mock import AsyncMock as AM, Mock
        mock_source = Mock()
        mock_source.cache_clear = AM(return_value=0)

        from main import app
        from dependencies import get_pncp_source
        app.dependency_overrides[get_pncp_source] = lambda: mock_source

        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert "cleared" in data

        app.dependency_overrides.pop(get_pncp_source, None)
