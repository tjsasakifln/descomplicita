"""Tests for DurableTaskRunner (TD-H02)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from job_store import JobStore
from task_queue import DurableTaskRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_redis(scan_result=None):
    """Return an AsyncMock Redis client with sensible defaults."""
    redis = AsyncMock()
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    # scan returns (cursor, [keys]); default: empty scan (cursor=0, no keys)
    if scan_result is None:
        redis.scan = AsyncMock(return_value=(0, []))
    else:
        redis.scan = AsyncMock(return_value=scan_result)
    return redis


async def _noop():
    """Coroutine that completes immediately."""


async def _slow():
    """Coroutine that sleeps forever (must be cancelled)."""
    await asyncio.sleep(9999)


# ---------------------------------------------------------------------------
# 1. enqueue — task launches, completes, running_count returns to 0
# ---------------------------------------------------------------------------


class TestEnqueueCompletes:
    @pytest.mark.asyncio
    async def test_task_completes_and_running_count_goes_to_zero(self):
        runner = DurableTaskRunner(redis=None)
        completed = []

        async def work():
            completed.append(True)

        await runner.enqueue("job-1", {}, work)
        # Yield control so the managed task has a chance to run
        await asyncio.sleep(0)

        assert completed == [True]
        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_running_count_is_one_while_task_is_pending(self):
        runner = DurableTaskRunner(redis=None)
        started = asyncio.Event()
        proceed = asyncio.Event()

        async def work():
            started.set()
            await proceed.wait()

        await runner.enqueue("job-1", {}, work)
        await started.wait()

        assert runner.running_count == 1

        proceed.set()
        await asyncio.sleep(0)  # let cleanup run

        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_multiple_tasks_complete_independently(self):
        runner = DurableTaskRunner(redis=None)
        results = []

        async def make_work(n):
            async def work():
                results.append(n)

            return work

        for i in range(3):
            await runner.enqueue(f"job-{i}", {}, await make_work(i))

        await asyncio.sleep(0)

        assert sorted(results) == [0, 1, 2]
        assert runner.running_count == 0


# ---------------------------------------------------------------------------
# 2. enqueue — with mock Redis, params are persisted via setex
# ---------------------------------------------------------------------------


class TestEnqueueRedisParams:
    @pytest.mark.asyncio
    async def test_setex_called_with_correct_key_and_ttl(self):
        redis = _make_redis()
        runner = DurableTaskRunner(redis=redis, job_params_ttl=3600)

        await runner.enqueue("job-abc", {"query": "test"}, _noop)
        await asyncio.sleep(0)

        redis.setex.assert_awaited_once_with(
            "job_params:job-abc",
            3600,
            json.dumps({"query": "test"}),
        )

    @pytest.mark.asyncio
    async def test_setex_stores_serialized_params(self):
        redis = _make_redis()
        runner = DurableTaskRunner(redis=redis)
        params = {"query": "licitacao", "uf": "SP", "limit": 50}

        await runner.enqueue("job-xyz", params, _noop)
        await asyncio.sleep(0)

        _, args, _ = redis.setex.mock_calls[0]
        stored_params = json.loads(args[2])
        assert stored_params == params

    @pytest.mark.asyncio
    async def test_redis_delete_called_after_completion(self):
        redis = _make_redis()
        runner = DurableTaskRunner(redis=redis)

        await runner.enqueue("job-1", {}, _noop)
        await asyncio.sleep(0)

        redis.delete.assert_awaited_once_with("job_params:job-1")

    @pytest.mark.asyncio
    async def test_redis_failure_does_not_prevent_task_execution(self):
        redis = _make_redis()
        redis.setex = AsyncMock(side_effect=ConnectionError("Redis down"))
        runner = DurableTaskRunner(redis=redis)
        completed = []

        async def work():
            completed.append(True)

        await runner.enqueue("job-1", {}, work)
        await asyncio.sleep(0)

        # Task should still have run despite Redis failure
        assert completed == [True]


# ---------------------------------------------------------------------------
# 3. shutdown — marks running jobs as interrupted via job_store.fail()
# ---------------------------------------------------------------------------


class TestShutdownMarksInterrupted:
    @pytest.mark.asyncio
    async def test_shutdown_calls_fail_for_running_jobs(self):
        runner = DurableTaskRunner(redis=None)
        job_store = AsyncMock(spec=JobStore)
        event = asyncio.Event()

        async def work():
            await event.wait()

        await runner.enqueue("job-1", {}, work)
        await asyncio.sleep(0)  # let task start

        count = await runner.shutdown(job_store=job_store)

        job_store.fail.assert_awaited_once()
        call_args = job_store.fail.call_args
        assert call_args[0][0] == "job-1"
        assert isinstance(call_args[0][1], str) and len(call_args[0][1]) > 0
        assert count == 1

    @pytest.mark.asyncio
    async def test_shutdown_returns_interrupted_count(self):
        runner = DurableTaskRunner(redis=None)
        job_store = AsyncMock(spec=JobStore)
        events = [asyncio.Event() for _ in range(3)]

        for i, ev in enumerate(events):
            ev_ref = ev

            async def work(e=ev_ref):
                await e.wait()

            await runner.enqueue(f"job-{i}", {}, work)

        await asyncio.sleep(0)

        count = await runner.shutdown(job_store=job_store)

        assert count == 3
        assert job_store.fail.await_count == 3

    @pytest.mark.asyncio
    async def test_shutdown_without_job_store_returns_zero(self):
        runner = DurableTaskRunner(redis=None)
        event = asyncio.Event()

        async def work():
            await event.wait()

        await runner.enqueue("job-1", {}, work)
        await asyncio.sleep(0)

        count = await runner.shutdown(job_store=None)

        assert count == 0

    @pytest.mark.asyncio
    async def test_shutdown_no_running_jobs_returns_zero(self):
        runner = DurableTaskRunner(redis=None)
        job_store = AsyncMock(spec=JobStore)

        count = await runner.shutdown(job_store=job_store)

        assert count == 0
        job_store.fail.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_shutdown_job_store_fail_exception_is_swallowed(self):
        runner = DurableTaskRunner(redis=None)
        job_store = AsyncMock(spec=JobStore)
        job_store.fail = AsyncMock(side_effect=RuntimeError("store error"))
        event = asyncio.Event()

        async def work():
            await event.wait()

        await runner.enqueue("job-1", {}, work)
        await asyncio.sleep(0)

        # Should not propagate the exception
        count = await runner.shutdown(job_store=job_store)
        assert count == 0  # fail raised, so interrupted counter not incremented


# ---------------------------------------------------------------------------
# 4. shutdown — cancels running tasks
# ---------------------------------------------------------------------------


class TestShutdownCancelsTasks:
    @pytest.mark.asyncio
    async def test_shutdown_cancels_long_running_task(self):
        runner = DurableTaskRunner(redis=None)
        started = asyncio.Event()

        async def work():
            started.set()
            await asyncio.sleep(9999)

        await runner.enqueue("job-1", {}, work)
        await started.wait()

        await runner.shutdown()

        # After shutdown, running_count must be 0
        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_shutdown_clears_running_tasks_dict(self):
        runner = DurableTaskRunner(redis=None)
        events = [asyncio.Event() for _ in range(2)]

        for i, ev in enumerate(events):
            ev_ref = ev

            async def work(e=ev_ref):
                e.set()
                await asyncio.sleep(9999)

            await runner.enqueue(f"job-{i}", {}, work)

        for ev in events:
            await ev.wait()

        assert runner.running_count == 2
        await runner.shutdown()
        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_shutdown_completes_already_finished_tasks_gracefully(self):
        runner = DurableTaskRunner(redis=None)

        await runner.enqueue("job-1", {}, _noop)
        await asyncio.sleep(0)  # task finishes before shutdown

        count = await runner.shutdown()
        assert count == 0
        assert runner.running_count == 0


# ---------------------------------------------------------------------------
# 5. running_count — accurate count of running tasks
# ---------------------------------------------------------------------------


class TestRunningCount:
    @pytest.mark.asyncio
    async def test_zero_when_no_tasks(self):
        runner = DurableTaskRunner(redis=None)
        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_increments_on_enqueue(self):
        runner = DurableTaskRunner(redis=None)
        proceed = asyncio.Event()

        async def work():
            await proceed.wait()

        await runner.enqueue("job-1", {}, work)
        await asyncio.sleep(0)

        assert runner.running_count == 1
        proceed.set()

    @pytest.mark.asyncio
    async def test_decrements_after_completion(self):
        runner = DurableTaskRunner(redis=None)

        await runner.enqueue("job-1", {}, _noop)
        await asyncio.sleep(0)

        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_tracks_multiple_concurrent_tasks(self):
        runner = DurableTaskRunner(redis=None)
        proceed = asyncio.Event()
        started_count = 0

        async def work():
            nonlocal started_count
            started_count += 1
            await proceed.wait()

        for i in range(5):
            await runner.enqueue(f"job-{i}", {}, work)

        await asyncio.sleep(0)

        assert runner.running_count == 5

        proceed.set()
        await asyncio.sleep(0)

        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_decrements_even_when_task_raises(self):
        runner = DurableTaskRunner(redis=None)

        async def failing_work():
            raise ValueError("task failed")

        await runner.enqueue("job-1", {}, failing_work)
        await asyncio.sleep(0)

        assert runner.running_count == 0


# ---------------------------------------------------------------------------
# 6. recover_interrupted — scans Redis for job_params:* keys
# ---------------------------------------------------------------------------


class TestRecoverInterrupted:
    @pytest.mark.asyncio
    async def test_returns_job_ids_from_redis_keys(self):
        redis = _make_redis(scan_result=(0, ["job_params:abc", "job_params:xyz"]))
        runner = DurableTaskRunner(redis=redis)

        result = await runner.recover_interrupted()

        assert sorted(result) == ["abc", "xyz"]

    @pytest.mark.asyncio
    async def test_scan_called_with_correct_pattern(self):
        redis = _make_redis()
        runner = DurableTaskRunner(redis=redis)

        await runner.recover_interrupted()

        redis.scan.assert_awaited_once_with(0, match="job_params:*", count=100)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_keys(self):
        redis = _make_redis(scan_result=(0, []))
        runner = DurableTaskRunner(redis=redis)

        result = await runner.recover_interrupted()

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_multi_page_scan(self):
        """Scan cursor != 0 means more pages to fetch."""
        redis = AsyncMock()
        # First call returns cursor=42 (more pages), second returns cursor=0 (done)
        redis.scan = AsyncMock(
            side_effect=[
                (42, ["job_params:job-1", "job_params:job-2"]),
                (0, ["job_params:job-3"]),
            ]
        )
        runner = DurableTaskRunner(redis=redis)

        result = await runner.recover_interrupted()

        assert sorted(result) == ["job-1", "job-2", "job-3"]
        assert redis.scan.await_count == 2

    @pytest.mark.asyncio
    async def test_redis_scan_failure_returns_empty_list(self):
        redis = AsyncMock()
        redis.scan = AsyncMock(side_effect=ConnectionError("Redis down"))
        runner = DurableTaskRunner(redis=redis)

        result = await runner.recover_interrupted()

        assert result == []

    @pytest.mark.asyncio
    async def test_strips_prefix_from_key(self):
        redis = _make_redis(scan_result=(0, ["job_params:my-job-id-123"]))
        runner = DurableTaskRunner(redis=redis)

        result = await runner.recover_interrupted()

        assert result == ["my-job-id-123"]


# ---------------------------------------------------------------------------
# 7. no Redis — works without Redis (params not persisted)
# ---------------------------------------------------------------------------


class TestNoRedis:
    @pytest.mark.asyncio
    async def test_enqueue_works_without_redis(self):
        runner = DurableTaskRunner(redis=None)
        completed = []

        async def work():
            completed.append(True)

        await runner.enqueue("job-1", {"query": "test"}, work)
        await asyncio.sleep(0)

        assert completed == [True]
        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_recover_interrupted_returns_empty_without_redis(self):
        runner = DurableTaskRunner(redis=None)
        result = await runner.recover_interrupted()
        assert result == []

    @pytest.mark.asyncio
    async def test_shutdown_works_without_redis(self):
        runner = DurableTaskRunner(redis=None)
        proceed = asyncio.Event()

        async def work():
            await proceed.wait()

        await runner.enqueue("job-1", {}, work)
        await asyncio.sleep(0)

        count = await runner.shutdown()
        assert count == 0  # no job_store provided
        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_no_redis_setex_never_called(self):
        """With redis=None, there should be no attribute errors and no Redis I/O."""
        runner = DurableTaskRunner(redis=None)

        # If redis is None and setex were called, it would raise AttributeError.
        # The fact that this completes without error is the assertion.
        await runner.enqueue("job-1", {"key": "value"}, _noop)
        await asyncio.sleep(0)

        assert runner.running_count == 0

    @pytest.mark.asyncio
    async def test_default_constructor_has_no_redis(self):
        runner = DurableTaskRunner()
        assert runner._redis is None

    @pytest.mark.asyncio
    async def test_default_ttl_is_86400(self):
        runner = DurableTaskRunner()
        assert runner._job_params_ttl == 86400
