"""Redis-backed job store for async search jobs (TD-005 + TD-H01 + TD-C01).

Redis is the sole source of truth for job state. In-memory cache is used
only as a read-through optimization for the current process.

Excel bytes are stored in a separate Redis key (not base64-encoded in the
job JSON) to eliminate memory duplication (TD-C01/XD-PERF-01).

v3-story-2.2 optimizations:
- DB-009: Items stored as Redis LIST (RPUSH/LRANGE) for O(1) pagination
- DB-015: Dual-write eliminated — Redis is sole item storage when available
- DB-006: Progress updates skip Redis (transient data, in-memory only)
"""

import json
import logging
import time
from typing import Dict, List, Optional

from job_store import JobStore, SearchJob

logger = logging.getLogger(__name__)

# Default TTL for jobs in Redis: 24 hours (TD-H01)
REDIS_JOB_TTL = 86400

# Default TTL for Excel data: 2 hours (shorter than job metadata)
REDIS_EXCEL_TTL = 7200

# Batch size for RPUSH operations to avoid huge argument lists
_RPUSH_BATCH_SIZE = 500


class RedisJobStore(JobStore):
    """Redis-backed job store — Redis as sole source of truth (TD-H01).

    In-memory dict is used only as a process-local cache. Redis is canonical.

    Args:
        redis: An async Redis client instance (redis.asyncio.Redis).
        max_jobs: Maximum concurrent active jobs.
        ttl: TTL in seconds for completed/failed jobs before cleanup.
        redis_ttl: TTL in seconds for Redis key expiry (default 24h).
    """

    def __init__(
        self,
        redis,
        max_jobs: int = 10,
        ttl: int = 1800,
        redis_ttl: int = REDIS_JOB_TTL,
    ) -> None:
        super().__init__(max_jobs=max_jobs, ttl=ttl)
        self._redis = redis
        self._redis_ttl = redis_ttl

    def _key(self, job_id: str) -> str:
        return f"job:{job_id}"

    def _excel_key(self, job_id: str) -> str:
        return f"excel:{job_id}"

    @staticmethod
    def _serialize_job(job: SearchJob) -> str:
        """Serialize job to JSON. Excel bytes are NOT included (stored separately)."""
        result = job.result
        if result and "excel_bytes" in result:
            # Strip excel_bytes from the serialized result
            result = {k: v for k, v in result.items() if k != "excel_bytes"}

        return json.dumps({
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "result": result,
            "error": job.error,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        })

    @staticmethod
    def _deserialize_job(data: str) -> SearchJob:
        d = json.loads(data)
        job = SearchJob(job_id=d["job_id"])
        job.status = d["status"]
        job.progress = d["progress"]
        job.result = d["result"]
        job.error = d["error"]
        job.created_at = d["created_at"]
        job.completed_at = d["completed_at"]
        return job

    async def _redis_set(self, job: SearchJob) -> None:
        """Write job to Redis with TTL."""
        try:
            await self._redis.setex(
                self._key(job.job_id),
                self._redis_ttl,
                self._serialize_job(job),
            )
        except Exception as e:
            logger.warning("Redis write failed for job %s: %s", job.job_id, e)

    async def _redis_get(self, job_id: str) -> Optional[SearchJob]:
        """Read job from Redis."""
        try:
            data = await self._redis.get(self._key(job_id))
            if data is None:
                return None
            return self._deserialize_job(data)
        except Exception as e:
            logger.warning("Redis read failed for job %s: %s", job_id, e)
            return None

    async def create(self, job_id: str) -> SearchJob:
        """Create a new job in both in-memory cache and Redis."""
        job = await super().create(job_id)
        await self._redis_set(job)
        return job

    async def update_progress(self, job_id: str, **kwargs: object) -> None:
        """Update progress in-memory only (DB-006: no Redis write amplification).

        Progress is transient — only needed while the job is running in this
        process. Full job state is persisted to Redis on state transitions
        (create/complete/fail). If the process dies mid-search, the job is
        lost regardless, so there is no value in persisting every tick.
        """
        await super().update_progress(job_id, **kwargs)

    async def complete(self, job_id: str, result: Dict) -> None:
        """Mark job complete in both in-memory cache and Redis."""
        await super().complete(job_id, result)
        async with self._lock:
            job = self._jobs.get(job_id)
        if job:
            await self._redis_set(job)

    async def fail(self, job_id: str, error: str) -> None:
        """Mark job failed in both in-memory cache and Redis."""
        await super().fail(job_id, error)
        async with self._lock:
            job = self._jobs.get(job_id)
        if job:
            await self._redis_set(job)

    async def get(self, job_id: str) -> Optional[SearchJob]:
        """Get job from in-memory cache first, fallback to Redis."""
        job = await super().get(job_id)
        if job is not None:
            return job
        # Fallback: try Redis (e.g., after restart)
        job = await self._redis_get(job_id)
        if job is not None:
            async with self._lock:
                self._jobs[job_id] = job
        return job

    async def cleanup_expired(self) -> int:
        """Clean up expired jobs from in-memory cache. Redis handles its own TTL."""
        return await super().cleanup_expired()

    # ------------------------------------------------------------------
    # Excel storage (TD-C01/XD-PERF-01) — separate from job JSON
    # ------------------------------------------------------------------

    async def store_excel(self, job_id: str, excel_bytes: bytes) -> None:
        """Store Excel bytes in a dedicated Redis key (not in job JSON).

        This eliminates the 3-copy memory duplication issue:
        - Excel bytes are written directly to Redis as raw bytes
        - NOT base64-encoded inside the job JSON
        - NOT kept in the in-memory job result dict
        """
        try:
            await self._redis.setex(
                self._excel_key(job_id),
                REDIS_EXCEL_TTL,
                excel_bytes,
            )
            logger.debug("Excel stored for job %s (%d bytes)", job_id, len(excel_bytes))
        except Exception as e:
            logger.warning("Failed to store Excel for job %s: %s", job_id, e)

    async def get_excel(self, job_id: str) -> Optional[bytes]:
        """Retrieve Excel bytes from dedicated Redis key.

        Returns:
            Raw Excel bytes, or None if not found/expired.
        """
        try:
            data = await self._redis.get(self._excel_key(job_id))
            return data if isinstance(data, bytes) else (data.encode() if data else None)
        except Exception as e:
            logger.warning("Failed to retrieve Excel for job %s: %s", job_id, e)
            return None

    # ------------------------------------------------------------------
    # Paginated items storage (DB-009 + DB-015)
    #
    # Items are stored as a Redis LIST via RPUSH (one JSON string per item).
    # Pagination uses LRANGE for O(1) page retrieval without deserializing
    # the entire dataset. Count uses LLEN.
    #
    # DB-015: No dual-write — items are NOT stored in self._items when
    # Redis is available. In-memory fallback only if Redis write fails.
    # ------------------------------------------------------------------

    def _items_key(self, job_id: str) -> str:
        return f"job:{job_id}:items"

    async def store_items(self, job_id: str, items: list) -> None:
        """Store filtered items as a Redis LIST (DB-009/DB-015).

        Each item is stored individually via RPUSH, enabling efficient
        LRANGE pagination without full deserialization.

        Falls back to in-memory storage if Redis write fails.
        """
        key = self._items_key(job_id)
        try:
            pipe = self._redis.pipeline()
            pipe.delete(key)
            # RPUSH in batches to avoid huge argument lists
            for i in range(0, len(items), _RPUSH_BATCH_SIZE):
                batch = [json.dumps(item) for item in items[i:i + _RPUSH_BATCH_SIZE]]
                if batch:
                    pipe.rpush(key, *batch)
            pipe.expire(key, self._redis_ttl)
            await pipe.execute()
            logger.debug(
                "Items stored for job %s (%d items) via Redis LIST",
                job_id, len(items),
            )
        except Exception as e:
            logger.warning(
                "Redis LIST store failed for job %s: %s — in-memory fallback",
                job_id, e,
            )
            await super().store_items(job_id, items)

    async def get_items_page(
        self, job_id: str, page: int = 1, page_size: int = 20
    ) -> tuple:
        """Return a page of items and total count via LRANGE (DB-009).

        Uses LLEN for count and LRANGE for the page slice — no full
        deserialization needed. Falls back to in-memory if Redis fails.
        """
        try:
            total = await self._redis.llen(self._items_key(job_id))
            if total == 0:
                # May be in-memory fallback from failed Redis write
                return await super().get_items_page(job_id, page, page_size)
            start = (page - 1) * page_size
            end = start + page_size - 1  # LRANGE end is inclusive
            raw_items = await self._redis.lrange(self._items_key(job_id), start, end)
            items = [json.loads(item) for item in raw_items]
            return items, total
        except Exception as e:
            logger.warning(
                "Redis LRANGE failed for job %s: %s — in-memory fallback",
                job_id, e,
            )
            return await super().get_items_page(job_id, page, page_size)

    async def get_items_count(self, job_id: str) -> int:
        """Return total item count via LLEN (DB-009) — no deserialization."""
        try:
            count = await self._redis.llen(self._items_key(job_id))
            if count > 0:
                return count
            return await super().get_items_count(job_id)
        except Exception as e:
            logger.warning("Redis LLEN failed for job %s: %s", job_id, e)
            return await super().get_items_count(job_id)

    async def get_all_items(self, job_id: str) -> list:
        """Return all items from Redis LIST (for CSV export)."""
        try:
            raw_items = await self._redis.lrange(self._items_key(job_id), 0, -1)
            if raw_items:
                return [json.loads(item) for item in raw_items]
            return await super().get_all_items(job_id)
        except Exception as e:
            logger.warning("Redis LRANGE (all) failed for job %s: %s", job_id, e)
            return await super().get_all_items(job_id)
