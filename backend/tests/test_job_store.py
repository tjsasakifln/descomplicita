"""Comprehensive tests for the JobStore module (SP-001.3)."""

import asyncio
import time
from unittest.mock import patch

import pytest
import pytest_asyncio

from job_store import JobStore, SearchJob

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store():
    """Fresh JobStore with small limits for testing."""
    return JobStore(max_jobs=3, ttl=5)


# ---------------------------------------------------------------------------
# 1. SearchJob dataclass
# ---------------------------------------------------------------------------


class TestSearchJob:
    """Tests for the SearchJob dataclass defaults and field types."""

    def test_default_status(self):
        job = SearchJob(job_id="j1")
        assert job.status == "queued"

    def test_default_progress(self):
        job = SearchJob(job_id="j1")
        assert job.progress == {
            "phase": "queued",
            "ufs_completed": 0,
            "ufs_total": 0,
            "items_fetched": 0,
            "items_filtered": 0,
            "sources_completed": 0,
            "sources_total": 0,
        }

    def test_default_result_is_none(self):
        job = SearchJob(job_id="j1")
        assert job.result is None

    def test_default_error_is_none(self):
        job = SearchJob(job_id="j1")
        assert job.error is None

    def test_default_completed_at_is_none(self):
        job = SearchJob(job_id="j1")
        assert job.completed_at is None

    def test_created_at_is_set(self):
        before = time.time()
        job = SearchJob(job_id="j1")
        after = time.time()
        assert before <= job.created_at <= after

    def test_progress_instances_are_independent(self):
        """Each SearchJob must get its own progress dict (no shared mutable default)."""
        a = SearchJob(job_id="a")
        b = SearchJob(job_id="b")
        a.progress["phase"] = "fetching"
        assert b.progress["phase"] == "queued"

    def test_job_id_stored(self):
        job = SearchJob(job_id="my-unique-id")
        assert job.job_id == "my-unique-id"


# ---------------------------------------------------------------------------
# 2. JobStore.create
# ---------------------------------------------------------------------------


class TestJobStoreCreate:
    @pytest.mark.asyncio
    async def test_create_returns_search_job(self, store):
        job = await store.create("j1")
        assert isinstance(job, SearchJob)
        assert job.job_id == "j1"
        assert job.status == "queued"

    @pytest.mark.asyncio
    async def test_create_duplicate_raises_value_error(self, store):
        await store.create("j1")
        with pytest.raises(ValueError, match="already exists"):
            await store.create("j1")

    @pytest.mark.asyncio
    async def test_create_multiple_distinct_ids(self, store):
        j1 = await store.create("a")
        j2 = await store.create("b")
        assert j1.job_id != j2.job_id


# ---------------------------------------------------------------------------
# 3. JobStore.update_progress
# ---------------------------------------------------------------------------


class TestJobStoreUpdateProgress:
    @pytest.mark.asyncio
    async def test_merges_kwargs_into_progress(self, store):
        await store.create("j1")
        await store.update_progress("j1", ufs_completed=3, ufs_total=5)
        job = await store.get("j1")
        assert job.progress["ufs_completed"] == 3
        assert job.progress["ufs_total"] == 5

    @pytest.mark.asyncio
    async def test_transitions_queued_to_running(self, store):
        await store.create("j1")
        assert (await store.get("j1")).status == "queued"
        await store.update_progress("j1", phase="fetching")
        job = await store.get("j1")
        assert job.status == "running"

    @pytest.mark.asyncio
    async def test_does_not_overwrite_running_status(self, store):
        await store.create("j1")
        await store.update_progress("j1", phase="fetching")
        await store.update_progress("j1", phase="filtering")
        job = await store.get("j1")
        assert job.status == "running"

    @pytest.mark.asyncio
    async def test_noop_for_missing_job(self, store):
        # Should not raise
        await store.update_progress("nonexistent", phase="x")

    @pytest.mark.asyncio
    async def test_adds_new_keys_to_progress(self, store):
        await store.create("j1")
        await store.update_progress("j1", custom_key="custom_value")
        job = await store.get("j1")
        assert job.progress["custom_key"] == "custom_value"


# ---------------------------------------------------------------------------
# 4. JobStore.complete
# ---------------------------------------------------------------------------


class TestJobStoreComplete:
    @pytest.mark.asyncio
    async def test_sets_completed_status(self, store):
        await store.create("j1")
        await store.complete("j1", result={"items": []})
        job = await store.get("j1")
        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_stores_result(self, store):
        result = {"items": [1, 2, 3], "total": 3}
        await store.create("j1")
        await store.complete("j1", result=result)
        job = await store.get("j1")
        assert job.result == result

    @pytest.mark.asyncio
    async def test_sets_completed_at(self, store):
        await store.create("j1")
        before = time.time()
        await store.complete("j1", result={})
        after = time.time()
        job = await store.get("j1")
        assert before <= job.completed_at <= after

    @pytest.mark.asyncio
    async def test_sets_phase_to_done(self, store):
        await store.create("j1")
        await store.complete("j1", result={})
        job = await store.get("j1")
        assert job.progress["phase"] == "done"

    @pytest.mark.asyncio
    async def test_noop_for_missing_job(self, store):
        await store.complete("nonexistent", result={})


# ---------------------------------------------------------------------------
# 5. JobStore.fail
# ---------------------------------------------------------------------------


class TestJobStoreFail:
    @pytest.mark.asyncio
    async def test_sets_failed_status(self, store):
        await store.create("j1")
        await store.fail("j1", error="timeout")
        job = await store.get("j1")
        assert job.status == "failed"

    @pytest.mark.asyncio
    async def test_stores_error_message(self, store):
        await store.create("j1")
        await store.fail("j1", error="Connection refused")
        job = await store.get("j1")
        assert job.error == "Connection refused"

    @pytest.mark.asyncio
    async def test_sets_completed_at(self, store):
        await store.create("j1")
        before = time.time()
        await store.fail("j1", error="err")
        after = time.time()
        job = await store.get("j1")
        assert before <= job.completed_at <= after

    @pytest.mark.asyncio
    async def test_noop_for_missing_job(self, store):
        await store.fail("nonexistent", error="err")


# ---------------------------------------------------------------------------
# 5b. JobStore.cancel (TD-DB-017)
# ---------------------------------------------------------------------------


class TestJobStoreCancel:
    @pytest.mark.asyncio
    async def test_sets_cancelled_status(self, store):
        await store.create("j1")
        await store.cancel("j1")
        job = await store.get("j1")
        assert job.status == "cancelled"

    @pytest.mark.asyncio
    async def test_stores_default_reason(self, store):
        await store.create("j1")
        await store.cancel("j1")
        job = await store.get("j1")
        assert job.error == "Busca cancelada pelo usuário."

    @pytest.mark.asyncio
    async def test_stores_custom_reason(self, store):
        await store.create("j1")
        await store.cancel("j1", reason="Timeout pelo sistema.")
        job = await store.get("j1")
        assert job.error == "Timeout pelo sistema."

    @pytest.mark.asyncio
    async def test_sets_completed_at(self, store):
        await store.create("j1")
        before = time.time()
        await store.cancel("j1")
        after = time.time()
        job = await store.get("j1")
        assert before <= job.completed_at <= after

    @pytest.mark.asyncio
    async def test_noop_for_missing_job(self, store):
        await store.cancel("nonexistent")


# ---------------------------------------------------------------------------
# 6. JobStore.get
# ---------------------------------------------------------------------------


class TestJobStoreGet:
    @pytest.mark.asyncio
    async def test_returns_existing_job(self, store):
        created = await store.create("j1")
        fetched = await store.get("j1")
        assert fetched is created

    @pytest.mark.asyncio
    async def test_returns_none_for_missing(self, store):
        result = await store.get("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# 7. JobStore.cleanup_expired
# ---------------------------------------------------------------------------


class TestJobStoreCleanupExpired:
    @pytest.mark.asyncio
    async def test_removes_completed_jobs_past_ttl(self, store):
        await store.create("j1")
        await store.complete("j1", result={})
        # Simulate time passing beyond TTL
        job = await store.get("j1")
        job.completed_at = time.time() - 10  # TTL is 5s
        job.created_at = time.time() - 10
        removed = await store.cleanup_expired()
        assert removed == 1
        assert await store.get("j1") is None

    @pytest.mark.asyncio
    async def test_removes_failed_jobs_past_ttl(self, store):
        await store.create("j1")
        await store.fail("j1", error="err")
        job = await store.get("j1")
        job.completed_at = time.time() - 10
        job.created_at = time.time() - 10
        removed = await store.cleanup_expired()
        assert removed == 1

    @pytest.mark.asyncio
    async def test_keeps_recent_jobs(self, store):
        await store.create("j1")
        await store.complete("j1", result={})
        removed = await store.cleanup_expired()
        assert removed == 0
        assert await store.get("j1") is not None

    @pytest.mark.asyncio
    async def test_removes_stale_queued_jobs_past_ttl(self, store):
        """Even queued jobs should be cleaned up if created_at exceeds TTL."""
        await store.create("j1")
        job = await store.get("j1")
        job.created_at = time.time() - 10  # older than TTL
        removed = await store.cleanup_expired()
        assert removed == 1

    @pytest.mark.asyncio
    async def test_returns_count_of_removed(self, store):
        for i in range(3):
            await store.create(f"j{i}")
            await store.complete(f"j{i}", result={})
            job = await store.get(f"j{i}")
            job.completed_at = time.time() - 10
            job.created_at = time.time() - 10
        removed = await store.cleanup_expired()
        assert removed == 3

    @pytest.mark.asyncio
    async def test_no_jobs_returns_zero(self, store):
        removed = await store.cleanup_expired()
        assert removed == 0


# ---------------------------------------------------------------------------
# 8. JobStore.active_count
# ---------------------------------------------------------------------------


class TestJobStoreActiveCount:
    @pytest.mark.asyncio
    async def test_empty_store(self, store):
        assert store.active_count == 0

    @pytest.mark.asyncio
    async def test_counts_queued(self, store):
        await store.create("j1")
        assert store.active_count == 1

    @pytest.mark.asyncio
    async def test_counts_running(self, store):
        await store.create("j1")
        await store.update_progress("j1", phase="fetching")
        assert store.active_count == 1

    @pytest.mark.asyncio
    async def test_excludes_completed(self, store):
        await store.create("j1")
        await store.complete("j1", result={})
        assert store.active_count == 0

    @pytest.mark.asyncio
    async def test_excludes_failed(self, store):
        await store.create("j1")
        await store.fail("j1", error="err")
        assert store.active_count == 0

    @pytest.mark.asyncio
    async def test_mixed_statuses(self, store):
        await store.create("j1")  # queued
        await store.create("j2")  # will be running
        await store.create("j3")  # will be completed
        await store.update_progress("j2", phase="fetching")
        await store.complete("j3", result={})
        # j1=queued, j2=running, j3=completed -> active=2
        assert store.active_count == 2


# ---------------------------------------------------------------------------
# 9. JobStore.is_full
# ---------------------------------------------------------------------------


class TestJobStoreIsFull:
    @pytest.mark.asyncio
    async def test_not_full_when_empty(self, store):
        assert store.is_full is False

    @pytest.mark.asyncio
    async def test_not_full_below_limit(self, store):
        await store.create("j1")
        await store.create("j2")
        assert store.is_full is False

    @pytest.mark.asyncio
    async def test_full_at_limit(self, store):
        # max_jobs=3
        await store.create("j1")
        await store.create("j2")
        await store.create("j3")
        assert store.is_full is True

    @pytest.mark.asyncio
    async def test_not_full_after_completing_jobs(self, store):
        await store.create("j1")
        await store.create("j2")
        await store.create("j3")
        assert store.is_full is True
        await store.complete("j3", result={})
        assert store.is_full is False

    @pytest.mark.asyncio
    async def test_not_full_after_failing_jobs(self, store):
        await store.create("j1")
        await store.create("j2")
        await store.create("j3")
        await store.fail("j2", error="err")
        assert store.is_full is False


# ---------------------------------------------------------------------------
# 10. Concurrency
# ---------------------------------------------------------------------------


class TestJobStoreConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_creates_no_corruption(self):
        """Many concurrent creates should all succeed without data loss."""
        store = JobStore(max_jobs=100, ttl=60)
        ids = [f"job-{i}" for i in range(50)]

        async def create_job(jid):
            await store.create(jid)

        await asyncio.gather(*(create_job(jid) for jid in ids))

        # All 50 jobs should exist
        for jid in ids:
            job = await store.get(jid)
            assert job is not None, f"Job {jid} missing after concurrent create"
        assert store.active_count == 50

    @pytest.mark.asyncio
    async def test_concurrent_updates_no_corruption(self):
        """Concurrent progress updates should all apply without crashing."""
        store = JobStore(max_jobs=10, ttl=60)
        await store.create("j1")

        async def update(i):
            await store.update_progress("j1", **{f"step_{i}": i})

        await asyncio.gather(*(update(i) for i in range(20)))

        job = await store.get("j1")
        # All 20 keys should be present
        for i in range(20):
            assert job.progress[f"step_{i}"] == i

    @pytest.mark.asyncio
    async def test_concurrent_create_and_complete(self):
        """Create and immediately complete jobs concurrently."""
        store = JobStore(max_jobs=100, ttl=60)

        async def create_and_complete(i):
            jid = f"job-{i}"
            await store.create(jid)
            await store.complete(jid, result={"index": i})

        await asyncio.gather(*(create_and_complete(i) for i in range(30)))

        for i in range(30):
            job = await store.get(f"job-{i}")
            assert job is not None
            assert job.status == "completed"
            assert job.result == {"index": i}

        # All completed, so active_count should be 0
        assert store.active_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self):
        """Mix of creates, updates, completes, and fails concurrently."""
        store = JobStore(max_jobs=100, ttl=60)

        # Pre-create jobs
        for i in range(10):
            await store.create(f"j{i}")

        async def do_op(i):
            jid = f"j{i}"
            if i % 3 == 0:
                await store.update_progress(jid, phase="running")
            elif i % 3 == 1:
                await store.complete(jid, result={"i": i})
            else:
                await store.fail(jid, error=f"error-{i}")

        await asyncio.gather(*(do_op(i) for i in range(10)))

        # Verify no exceptions and all jobs still accessible
        for i in range(10):
            job = await store.get(f"j{i}")
            assert job is not None

    @pytest.mark.asyncio
    async def test_concurrent_duplicate_create_raises(self):
        """Only one concurrent create for the same ID should succeed; others raise."""
        store = JobStore(max_jobs=10, ttl=60)
        results = []

        async def try_create():
            try:
                await store.create("same-id")
                results.append("ok")
            except ValueError:
                results.append("error")

        await asyncio.gather(*(try_create() for _ in range(5)))

        assert results.count("ok") == 1
        assert results.count("error") == 4
