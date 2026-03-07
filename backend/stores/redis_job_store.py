"""Redis-backed job store for async search jobs (TD-005)."""

import json
import logging
import time
from typing import Dict, Optional

from job_store import JobStore, SearchJob

logger = logging.getLogger(__name__)

# Default TTL for jobs in Redis: 24 hours
REDIS_JOB_TTL = 86400


class RedisJobStore(JobStore):
    """Redis-backed job store with graceful fallback to in-memory.

    Implements the same interface as JobStore but persists data to Redis.
    On Redis connection failure, falls back to in-memory storage and logs warnings.

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

    @staticmethod
    def _serialize_job(job: SearchJob) -> str:
        return json.dumps({
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "result": job.result,
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
            logger.warning(f"Redis write failed for job {job.job_id}: {e}")

    async def _redis_get(self, job_id: str) -> Optional[SearchJob]:
        """Read job from Redis."""
        try:
            data = await self._redis.get(self._key(job_id))
            if data is None:
                return None
            return self._deserialize_job(data)
        except Exception as e:
            logger.warning(f"Redis read failed for job {job_id}: {e}")
            return None

    async def create(self, job_id: str) -> SearchJob:
        """Create a new job in both in-memory and Redis."""
        job = await super().create(job_id)
        await self._redis_set(job)
        return job

    async def update_progress(self, job_id: str, **kwargs: object) -> None:
        """Update progress in both in-memory and Redis."""
        await super().update_progress(job_id, **kwargs)
        async with self._lock:
            job = self._jobs.get(job_id)
        if job:
            await self._redis_set(job)

    async def complete(self, job_id: str, result: Dict) -> None:
        """Mark job complete in both in-memory and Redis."""
        await super().complete(job_id, result)
        async with self._lock:
            job = self._jobs.get(job_id)
        if job:
            await self._redis_set(job)

    async def fail(self, job_id: str, error: str) -> None:
        """Mark job failed in both in-memory and Redis."""
        await super().fail(job_id, error)
        async with self._lock:
            job = self._jobs.get(job_id)
        if job:
            await self._redis_set(job)

    async def get(self, job_id: str) -> Optional[SearchJob]:
        """Get job from in-memory first, fallback to Redis."""
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
        """Clean up expired jobs from in-memory. Redis handles its own TTL."""
        return await super().cleanup_expired()
