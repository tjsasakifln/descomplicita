"""Integration tests for Redis job store (TD-005)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from stores.redis_job_store import RedisJobStore


class TestRedisJobStore:
    """Test RedisJobStore with mock Redis."""

    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.setex = AsyncMock()
        r.get = AsyncMock(return_value=None)
        r.ping = AsyncMock()
        return r

    @pytest.fixture
    def store(self, mock_redis):
        return RedisJobStore(redis=mock_redis, max_jobs=3, ttl=5)

    @pytest.mark.asyncio
    async def test_create_writes_to_redis(self, store, mock_redis):
        job = await store.create("j1")
        assert job.job_id == "j1"
        assert job.status == "queued"
        mock_redis.setex.assert_called_once()
        # Verify key format
        args = mock_redis.setex.call_args
        assert args[0][0] == "job:j1"

    @pytest.mark.asyncio
    async def test_update_progress_skips_redis_write(self, store, mock_redis):
        """DB-006: Progress updates are in-memory only (no write amplification)."""
        await store.create("j1")
        mock_redis.setex.reset_mock()
        await store.update_progress("j1", phase="fetching")
        # DB-006: Progress is transient — no Redis write on progress updates
        mock_redis.setex.assert_not_called()
        # But in-memory state is updated
        job = await store.get("j1")
        assert job.status == "running"
        assert job.progress["phase"] == "fetching"

    @pytest.mark.asyncio
    async def test_complete_writes_to_redis(self, store, mock_redis):
        await store.create("j1")
        mock_redis.setex.reset_mock()
        await store.complete("j1", result={"items": [1, 2, 3]})
        mock_redis.setex.assert_called_once()
        data = json.loads(mock_redis.setex.call_args[0][2])
        assert data["status"] == "completed"
        assert data["result"]["items"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_fail_writes_to_redis(self, store, mock_redis):
        await store.create("j1")
        mock_redis.setex.reset_mock()
        await store.fail("j1", error="timeout")
        mock_redis.setex.assert_called_once()
        data = json.loads(mock_redis.setex.call_args[0][2])
        assert data["status"] == "failed"
        assert data["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_get_from_memory_first(self, store, mock_redis):
        await store.create("j1")
        job = await store.get("j1")
        assert job is not None
        assert job.job_id == "j1"
        # Redis get should NOT have been called (found in memory)
        mock_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_falls_back_to_redis(self, store, mock_redis):
        """After restart, job only in Redis should be recovered."""
        job_data = json.dumps({
            "job_id": "recovered",
            "status": "completed",
            "progress": {"phase": "done"},
            "result": {"test": True},
            "error": None,
            "created_at": 1000000.0,
            "completed_at": 1000001.0,
        })
        mock_redis.get = AsyncMock(return_value=job_data)

        job = await store.get("recovered")
        assert job is not None
        assert job.job_id == "recovered"
        assert job.status == "completed"
        assert job.result == {"test": True}

    @pytest.mark.asyncio
    async def test_ttl_applied_to_redis(self, store, mock_redis):
        await store.create("j1")
        args = mock_redis.setex.call_args
        ttl = args[0][1]
        assert ttl == 86400  # Default 24h TTL

    @pytest.mark.asyncio
    async def test_redis_write_failure_graceful(self, store, mock_redis):
        mock_redis.setex = AsyncMock(side_effect=ConnectionError("Redis down"))
        # Should not raise — job still created in memory
        job = await store.create("j1")
        assert job is not None
        assert job.job_id == "j1"

    @pytest.mark.asyncio
    async def test_redis_read_failure_graceful(self, store, mock_redis):
        mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        # Job not in memory, Redis fails — should return None
        job = await store.get("nonexistent")
        assert job is None

    @pytest.mark.asyncio
    async def test_cleanup_uses_parent(self, store, mock_redis):
        """Cleanup should use in-memory cleanup (Redis handles its own TTL)."""
        import time
        await store.create("j1")
        await store.complete("j1", result={})
        job = await store.get("j1")
        job.completed_at = time.time() - 10
        job.created_at = time.time() - 10
        removed = await store.cleanup_expired()
        assert removed == 1
