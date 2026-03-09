"""In-memory job store for async search jobs (SP-001.3)."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SearchJob:
    """Represents an async search job."""

    job_id: str
    status: str = "queued"  # queued | running | completed | failed
    progress: Dict = field(default_factory=lambda: {
        "phase": "queued",
        "ufs_completed": 0,
        "ufs_total": 0,
        "items_fetched": 0,
        "items_filtered": 0,
        "sources_completed": 0,
        "sources_total": 0,
    })
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class JobStore:
    """Thread-safe in-memory store for search jobs.

    Uses asyncio.Lock for safe concurrent access in FastAPI async context.

    Args:
        max_jobs: Maximum number of concurrent active jobs (queued + running).
        ttl: Time-to-live in seconds for completed/failed jobs before cleanup.
    """

    def __init__(self, max_jobs: int = 10, ttl: int = 1800) -> None:
        self.max_jobs = max_jobs
        self.ttl = ttl
        self._jobs: Dict[str, SearchJob] = {}
        self._excel: Dict[str, bytes] = {}
        self._items: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    async def create(self, job_id: str) -> SearchJob:
        """Create a new queued job.

        Args:
            job_id: Unique identifier for the job.

        Returns:
            The newly created SearchJob.

        Raises:
            ValueError: If a job with the same ID already exists.
        """
        async with self._lock:
            if job_id in self._jobs:
                raise ValueError(f"Job {job_id} already exists")
            job = SearchJob(job_id=job_id)
            self._jobs[job_id] = job
            return job

    async def update_progress(self, job_id: str, **kwargs: object) -> None:
        """Merge keyword arguments into the job's progress dict.

        Also sets the job status to 'running' if it was 'queued'.

        Args:
            job_id: The job to update.
            **kwargs: Key-value pairs to merge into progress.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job.status == "queued":
                job.status = "running"
            job.progress.update(kwargs)

    async def complete(self, job_id: str, result: Dict) -> None:
        """Mark a job as completed with its result.

        Args:
            job_id: The job to complete.
            result: The result dictionary to store.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "completed"
            job.result = result
            job.progress["phase"] = "done"
            job.completed_at = time.time()

    async def fail(self, job_id: str, error: str) -> None:
        """Mark a job as failed with an error message.

        Args:
            job_id: The job to mark as failed.
            error: Description of the error.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "failed"
            job.error = error
            job.completed_at = time.time()

    async def get(self, job_id: str) -> Optional[SearchJob]:
        """Retrieve a job by ID.

        Args:
            job_id: The job to look up.

        Returns:
            The SearchJob if found, None otherwise.
        """
        async with self._lock:
            return self._jobs.get(job_id)

    async def cleanup_expired(self) -> int:
        """Remove jobs older than TTL.

        Returns:
            Number of jobs removed.
        """
        now = time.time()
        async with self._lock:
            expired = [
                jid
                for jid, job in self._jobs.items()
                if (job.completed_at and now - job.completed_at > self.ttl)
                or (now - job.created_at > self.ttl)
            ]
            for jid in expired:
                del self._jobs[jid]
            return len(expired)

    @property
    def active_count(self) -> int:
        """Count of queued + running jobs."""
        return sum(
            1 for job in self._jobs.values()
            if job.status in ("queued", "running")
        )

    @property
    def is_full(self) -> bool:
        """Whether the store has reached its max active jobs limit."""
        return self.active_count >= self.max_jobs

    async def store_excel(self, job_id: str, excel_bytes: bytes) -> None:
        """Store Excel bytes separately from job data (TD-C01)."""
        async with self._lock:
            self._excel[job_id] = excel_bytes

    async def get_excel(self, job_id: str) -> Optional[bytes]:
        """Retrieve stored Excel bytes for a job."""
        async with self._lock:
            return self._excel.get(job_id)

    # ------------------------------------------------------------------
    # Paginated items storage (TD-M02)
    # ------------------------------------------------------------------

    async def store_items(self, job_id: str, items: list) -> None:
        """Store filtered items for paginated retrieval."""
        async with self._lock:
            self._items[job_id] = items

    async def get_items_page(
        self, job_id: str, page: int = 1, page_size: int = 20
    ) -> tuple:
        """Return a page of items and total count."""
        async with self._lock:
            items = self._items.get(job_id, [])
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total
