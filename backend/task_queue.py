"""Durable task queue for search jobs (TD-H02/TD-H01).

Replaces direct asyncio.create_task with a managed task runner that:
- Stores job parameters in Redis before execution (durability)
- Registers running tasks for graceful SIGTERM handling
- Marks interrupted jobs on shutdown (no data loss)
- Can re-enqueue interrupted jobs on startup

Redis is the sole source of truth for job state.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Dict, Optional, Set

logger = logging.getLogger(__name__)


class DurableTaskRunner:
    """Managed async task execution with Redis-backed durability.

    Args:
        redis: Async Redis client instance.
        job_params_ttl: TTL for stored job parameters in Redis (default 24h).
    """

    def __init__(self, redis=None, job_params_ttl: int = 86400) -> None:
        self._redis = redis
        self._job_params_ttl = job_params_ttl
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown = False

    def _params_key(self, job_id: str) -> str:
        return f"job_params:{job_id}"

    async def enqueue(
        self,
        job_id: str,
        params: dict,
        coro_factory: Callable[..., Coroutine],
    ) -> None:
        """Enqueue a durable task.

        1. Stores job parameters in Redis (for restart recovery)
        2. Launches the coroutine as a managed asyncio task
        3. Registers for graceful shutdown handling

        Args:
            job_id: Unique job identifier.
            params: Serializable parameters to persist for recovery.
            coro_factory: Async callable that returns the coroutine to execute.
                         Called as: coro_factory()
        """
        # Persist parameters to Redis for crash recovery
        if self._redis:
            try:
                await self._redis.setex(
                    self._params_key(job_id),
                    self._job_params_ttl,
                    json.dumps(params),
                )
            except Exception as e:
                logger.warning("Failed to persist job params for %s: %s", job_id, e)

        # Launch managed task
        task = asyncio.create_task(self._run_managed(job_id, coro_factory))
        self._running_tasks[job_id] = task

    async def _run_managed(
        self,
        job_id: str,
        coro_factory: Callable[..., Coroutine],
    ) -> None:
        """Execute a task with cleanup on completion."""
        try:
            await coro_factory()
        finally:
            self._running_tasks.pop(job_id, None)
            # Clean up persisted params after successful completion
            if self._redis:
                try:
                    await self._redis.delete(self._params_key(job_id))
                except Exception:
                    pass

    async def shutdown(self, job_store=None) -> int:
        """Gracefully shut down all running tasks.

        Marks running jobs as 'interrupted' in the job store so they can
        be detected and optionally restarted on next startup.

        Args:
            job_store: Optional job store to mark interrupted jobs.

        Returns:
            Number of jobs that were interrupted.
        """
        self._shutdown = True
        interrupted = 0

        for job_id, task in list(self._running_tasks.items()):
            logger.info("Interrupting running job: %s", job_id)
            task.cancel()
            if job_store:
                try:
                    await job_store.fail(
                        job_id,
                        "Job interrompido durante shutdown do servidor. "
                        "Tente novamente.",
                    )
                    interrupted += 1
                except Exception as e:
                    logger.warning("Failed to mark job %s as interrupted: %s", job_id, e)

        # Wait for all tasks to finish cancellation
        if self._running_tasks:
            tasks = list(self._running_tasks.values())
            await asyncio.gather(*tasks, return_exceptions=True)

        self._running_tasks.clear()
        logger.info("Task runner shutdown complete: %d jobs interrupted", interrupted)
        return interrupted

    async def recover_interrupted(self) -> list[str]:
        """Scan Redis for job parameters left by interrupted jobs.

        Returns:
            List of job_ids that have persisted parameters (interrupted).
        """
        if not self._redis:
            return []

        interrupted_ids = []
        try:
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor, match="job_params:*", count=100
                )
                for key in keys:
                    job_id = key.replace("job_params:", "")
                    interrupted_ids.append(job_id)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning("Failed to scan for interrupted jobs: %s", e)

        if interrupted_ids:
            logger.info("Found %d interrupted jobs from previous run", len(interrupted_ids))

        return interrupted_ids

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job by ID. Returns True if cancelled."""
        task = self._running_tasks.get(job_id)
        if task is None:
            return False
        task.cancel()
        self._running_tasks.pop(job_id, None)
        # Clean up persisted params
        if self._redis:
            try:
                await self._redis.delete(self._params_key(job_id))
            except Exception:
                pass
        return True

    @property
    def running_count(self) -> int:
        """Number of currently running tasks."""
        return len(self._running_tasks)
