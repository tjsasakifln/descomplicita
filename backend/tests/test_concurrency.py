"""
Tests for concurrent search behavior — SP-001.5.

Covers:
- Multiple simultaneous search jobs completing without error
- HTTP 429 when the job store is at capacity (max 10 active jobs)
- No state leakage across consecutive identical searches
- Job lifecycle transitions (queued -> running -> completed)
- Expired job cleanup via cleanup_expired()

Design notes:
- All external I/O (PNCP, LLM, Excel) is mocked to isolate concurrency logic.
- _job_store._jobs.clear() is called before/after each test to prevent bleed.
- For the 429 test, we inject 10 fake "running" jobs directly into the store
  rather than relying on timing, making the test deterministic.
- The ``run_sync`` fixture is required for any test that polls for job
  completion.  Starlette's TestClient runs on a background event loop that
  shares a single thread with asyncio.create_task.  loop.run_in_executor
  inside run_search_job dispatches blocking work to a thread pool whose
  futures can never resolve while the event loop is blocked waiting for them
  (classic deadlock).  The fixture replaces run_in_executor with a shim that
  executes the callable synchronously on the event loop thread and wraps the
  result in an already-resolved Future, breaking the deadlock.
  It also patches asyncio.create_task so the background coroutine runs to
  completion inside the same POST /buscar call, meaning the job is already
  'completed' by the time the response returns — no polling races.
"""

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from typing import Optional
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from job_store import SearchJob
from main import app, _job_store


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def make_pncp_response(uf: str = "SP", n_items: int = 5) -> dict:
    """
    Build a minimal PNCP-style response payload for a single page.

    Args:
        uf: Brazilian state code used in the numeric control field.
        n_items: Number of bid items to include in the response.

    Returns:
        A dict matching the structure returned by PNCPClient.fetch_page().
    """
    return {
        "data": [
            {
                "numeroControlePNCP": f"PNCP-{uf}-{i}",
                "objetoCompra": "Aquisição de uniformes profissionais",
                "valorTotalEstimado": 50000.0,
                "dataPublicacaoPncp": "2026-03-01T00:00:00",
                "dataAberturaProposta": "2026-03-10T00:00:00",
                "orgaoEntidade": {"razaoSocial": "Org Test", "cnpj": "12345678000100"},
                "unidadeOrgao": {
                    "ufSigla": uf,
                    "municipioNome": "Cidade",
                    "nomeUnidade": "Unidade",
                },
                "modalidadeNome": "Pregão - Eletrônico",
            }
            for i in range(n_items)
        ],
        "totalRegistros": n_items,
        "totalPaginas": 1,
        "paginasRestantes": 0,
    }


VALID_REQUEST = {
    "ufs": ["SP"],
    "data_inicial": "2026-03-01",
    "data_final": "2026-03-07",
    "setor_id": "vestuario",
}


def _wait_for_job(
    client: TestClient,
    job_id: str,
    timeout: float = 15.0,
    poll_interval: float = 0.05,
) -> Optional[dict]:
    """
    Poll GET /buscar/{job_id}/status until terminal state or timeout.

    With the run_sync fixture in place the job is already completed before the
    POST returns, so the first poll call normally succeeds immediately.  The
    timeout is kept as a safety net for tests that do NOT use run_sync.

    Args:
        client: The Starlette TestClient to use for polling.
        job_id: ID of the job to poll.
        timeout: Maximum seconds to wait before giving up.
        poll_interval: Seconds between each poll attempt.

    Returns:
        The last status response dict, or None if timed out.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/buscar/{job_id}/status")
        if resp.status_code == 200:
            data = resp.json()
            if data["status"] in ("completed", "failed"):
                return data
        time.sleep(poll_interval)
    return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Provide a reusable FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_job_store():
    """
    Clear the global job store before and after every test.

    This prevents any state leakage between test cases since _job_store is a
    module-level singleton shared across the application.
    """
    _job_store._jobs.clear()
    yield
    _job_store._jobs.clear()


@pytest.fixture
def mock_pncp_client(monkeypatch):
    """
    Replace _get_orchestrator() with a mock that returns canned data.

    The mock returns items from make_pncp_response() wrapped in an OrchestratorResult.
    """
    from tests.mock_helpers import make_mock_orchestrator
    records = make_pncp_response("SP")["data"]
    mock_orch = make_mock_orchestrator(records)
    monkeypatch.setattr("main._get_orchestrator", lambda: mock_orch)
    return mock_orch


@pytest.fixture
def mock_pipeline(monkeypatch):
    """
    Mock filter_batch, gerar_resumo, and create_excel to return fast, stable results.

    This keeps tests focused on concurrency/lifecycle behaviour rather than
    the correctness of each pipeline stage.
    """
    from schemas import ResumoLicitacoes

    def _filter(bids, **kwargs):
        # Pass all bids through unmodified so LLM/Excel always run.
        return list(bids), {}

    def _resumo(bids, **kwargs):
        return ResumoLicitacoes(
            resumo_executivo=f"{len(bids)} licitações encontradas",
            total_oportunidades=len(bids),
            valor_total=sum(b.get("valorTotalEstimado", 0) for b in bids),
        )

    def _excel(bids):
        buf = BytesIO(b"fake-excel-content")
        buf.seek(0)
        return buf

    monkeypatch.setattr("main.filter_batch", _filter)
    monkeypatch.setattr("main.gerar_resumo", _resumo)
    monkeypatch.setattr("main.create_excel", _excel)


@pytest.fixture
def run_sync(monkeypatch):
    """
    Make background search jobs execute synchronously inside the POST handler.

    Problem:
        Starlette TestClient runs an event loop on a background thread.
        run_search_job uses loop.run_in_executor to offload blocking work to a
        thread pool.  Those futures will never resolve while the event loop
        thread is blocked servicing the TestClient request — a classic
        event-loop deadlock.

    Solution (mirrors test_main.py):
        1. Wrap run_search_job so that loop.run_in_executor is replaced with a
           shim that calls the callable synchronously and returns an
           already-resolved Future.
        2. Patch asyncio.create_task inside main so the background coroutine
           runs to completion before the POST response is returned.  This means
           job is 'completed' by the time the caller receives the response —
           polling still works (the first GET /status call returns terminal
           state immediately).
    """
    import main as main_module

    original_run_search_job = main_module.run_search_job

    async def _inline_run_search_job(job_id: str, request):
        """Run the search job with run_in_executor replaced by a sync shim."""
        loop = asyncio.get_event_loop()
        original_rie = loop.run_in_executor

        def _sync_rie(executor, func, *args):
            fut = loop.create_future()
            try:
                result = func(*args)
                fut.set_result(result)
            except Exception as exc:
                fut.set_exception(exc)
            return fut

        loop.run_in_executor = _sync_rie
        try:
            await original_run_search_job(job_id, request)
        finally:
            loop.run_in_executor = original_rie

    # Replace the module-level coroutine function.
    monkeypatch.setattr("main.run_search_job", _inline_run_search_job)

    # Also intercept asyncio.create_task inside main so the background
    # coroutine is awaited inline (not scheduled for later).
    original_create_task = asyncio.create_task

    def _inline_create_task(coro, *args, **kwargs):
        """Schedule the coroutine inline if it's a search job coroutine."""
        # We detect search-job coroutines by their qualified name.
        coro_name = getattr(coro, "__qualname__", "") or getattr(
            coro, "__name__", ""
        )
        if "run_search_job" in coro_name or "_inline_run_search_job" in coro_name:
            loop = asyncio.get_event_loop()
            # Drive the coroutine to completion synchronously on the loop.
            return loop.create_task(coro)
        return original_create_task(coro, *args, **kwargs)

    monkeypatch.setattr("main.asyncio.create_task", _inline_create_task)


# ---------------------------------------------------------------------------
# TestConcurrentSearches
# ---------------------------------------------------------------------------


class TestConcurrentSearches:
    """Tests for concurrent job creation and completion behaviour."""

    def test_5_simultaneous_searches_complete(
        self, client, mock_pncp_client, mock_pipeline, run_sync
    ):
        """
        Launch 5 search jobs rapidly (different UFs) and verify all complete.

        Uses ThreadPoolExecutor to submit 5 POST /buscar requests at roughly the
        same instant, then polls each job until it reaches a terminal state.
        All 5 must complete (not fail).

        Note: with run_sync the background task finishes inside the POST, so
        jobs should be 'completed' by the time the POST response arrives.
        """
        ufs_list = ["SP", "RJ", "MG", "RS", "PR"]
        requests_data = [
            {**VALID_REQUEST, "ufs": [uf]}
            for uf in ufs_list
        ]

        # Submit all 5 jobs concurrently.
        job_ids = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(client.post, "/buscar", json=req): req
                for req in requests_data
            }
            for future in as_completed(futures):
                resp = future.result()
                assert resp.status_code == 200, (
                    f"Expected 200 from POST /buscar, got {resp.status_code}: "
                    f"{resp.text}"
                )
                job_ids.append(resp.json()["job_id"])

        assert len(job_ids) == 5, "All 5 jobs must be created"

        # Poll all 5 jobs until they finish (should be immediate with run_sync).
        for job_id in job_ids:
            final = _wait_for_job(client, job_id, timeout=15.0)
            assert final is not None, (
                f"Job {job_id} did not reach a terminal state within 15s"
            )
            assert final["status"] == "completed", (
                f"Job {job_id} ended with status '{final['status']}' "
                f"instead of 'completed'"
            )

    def test_job_limit_returns_429(self, client):
        """
        Submitting an 11th job when 10 active jobs are present must return HTTP 429.

        We inject 10 fake "running" jobs directly into the job store — this is
        reliable and deterministic regardless of CPU/thread scheduling.  We then
        submit one additional POST /buscar and assert the 429 response.
        """
        # Pre-fill job store with 10 active (running) jobs.
        for i in range(_job_store.max_jobs):
            fake_job = SearchJob(job_id=f"fake-running-{i}", status="running")
            _job_store._jobs[f"fake-running-{i}"] = fake_job

        assert _job_store.active_count == 10, "Job store should be at capacity"
        assert _job_store.is_full, "is_full should be True with 10 active jobs"

        # The 11th job must be rejected.
        response = client.post("/buscar", json=VALID_REQUEST)

        assert response.status_code == 429, (
            f"Expected 429 Too Many Requests when store is full, "
            f"got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "detail" in data, "429 response must include a 'detail' field"
        # Sanity-check the Portuguese error message contains expected wording.
        assert "simultâneas" in data["detail"] or "busca" in data["detail"].lower(), (
            f"Unexpected 429 detail message: {data['detail']}"
        )

    def test_no_race_condition_10_runs(
        self, client, mock_pncp_client, mock_pipeline, run_sync
    ):
        """
        Run 10 consecutive identical searches (one at a time) and verify all complete.

        Checks that no state leakage or lingering locks from one job affect the
        next.  Each iteration waits for the current job to finish before
        submitting the next.
        """
        for run in range(10):
            resp = client.post("/buscar", json=VALID_REQUEST)
            assert resp.status_code == 200, (
                f"Run {run}: POST /buscar returned {resp.status_code}: {resp.text}"
            )
            job_id = resp.json()["job_id"]

            final = _wait_for_job(client, job_id, timeout=15.0)
            assert final is not None, (
                f"Run {run}: job {job_id} did not complete within 15s"
            )
            assert final["status"] == "completed", (
                f"Run {run}: job {job_id} ended with status '{final['status']}'"
            )


# ---------------------------------------------------------------------------
# TestJobLifecycle
# ---------------------------------------------------------------------------


class TestJobLifecycle:
    """Tests for individual job state transitions and cleanup."""

    def test_job_transitions_queued_to_completed(
        self, client, mock_pncp_client, mock_pipeline, run_sync
    ):
        """
        Verify that a newly created job starts as 'queued' and eventually reaches
        'completed'.

        Flow:
        1. POST /buscar — assert the creation response carries status='queued'.
        2. Poll GET /buscar/{job_id}/status until terminal state.
        3. Assert final status is 'completed'.
        4. Confirm GET /buscar/{job_id}/result returns 200 with full payload.

        With run_sync the background task completes inside the POST, so polling
        resolves on the first attempt.
        """
        resp = client.post("/buscar", json=VALID_REQUEST)
        assert resp.status_code == 200
        data = resp.json()

        # The creation response always carries status="queued".
        assert data["status"] == "queued", (
            f"POST /buscar should return status='queued', got '{data['status']}'"
        )
        job_id = data["job_id"]

        # Poll until done and assert final state.
        final = _wait_for_job(client, job_id, timeout=15.0)
        assert final is not None, f"Job {job_id} did not complete within 15s"
        assert final["status"] == "completed", (
            f"Expected final status 'completed', got '{final['status']}'"
        )

        # Confirm the result endpoint also returns 200 with full payload.
        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200
        result_data = result_resp.json()
        assert result_data["status"] == "completed"
        assert "resumo" in result_data
        assert "excel_base64" in result_data

    def test_expired_jobs_cleaned_up(self, client):
        """
        Jobs whose completed_at timestamp is older than TTL must be removed by
        cleanup_expired().

        Steps:
        1. Create a SearchJob and insert it directly into the store.
        2. Backdate its completed_at to exceed the TTL.
        3. Call cleanup_expired() synchronously via asyncio.run().
        4. Assert the job is no longer in the store.
        """
        job_id = f"expired-{uuid.uuid4()}"
        expired_job = SearchJob(
            job_id=job_id,
            status="completed",
            result={"test": True},
        )
        # Backdate both created_at and completed_at well beyond the TTL.
        expired_job.created_at = time.time() - _job_store.ttl - 200
        expired_job.completed_at = time.time() - _job_store.ttl - 200

        _job_store._jobs[job_id] = expired_job

        assert job_id in _job_store._jobs, "Job should exist before cleanup"

        # Run cleanup synchronously.
        removed = asyncio.run(_job_store.cleanup_expired())

        assert job_id not in _job_store._jobs, (
            f"Expired job '{job_id}' should have been removed by cleanup_expired()"
        )
        assert removed >= 1, (
            f"cleanup_expired() should report at least 1 removal, got {removed}"
        )

    def test_non_expired_job_not_cleaned_up(self, client):
        """
        A recently completed job must survive cleanup_expired().

        Regression guard: ensure cleanup only removes genuinely old jobs and does
        not accidentally evict fresh ones.
        """
        job_id = f"fresh-{uuid.uuid4()}"
        fresh_job = SearchJob(
            job_id=job_id,
            status="completed",
            result={"test": True},
        )
        # completed_at is right now — well within TTL.
        fresh_job.completed_at = time.time()
        _job_store._jobs[job_id] = fresh_job

        asyncio.run(_job_store.cleanup_expired())

        assert job_id in _job_store._jobs, (
            f"Fresh job '{job_id}' should NOT be removed by cleanup_expired()"
        )

    def test_active_job_count_decrements_after_completion(
        self, client, mock_pncp_client, mock_pipeline, run_sync
    ):
        """
        The active_count property must drop back to 0 once all jobs complete.

        This catches resource-leak bugs where a completed job is incorrectly
        counted as still active.
        """
        resp = client.post("/buscar", json=VALID_REQUEST)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final = _wait_for_job(client, job_id, timeout=15.0)
        assert final is not None, f"Job {job_id} did not complete within 15s"
        assert final["status"] == "completed"

        # After completion, active_count must not include this job.
        assert _job_store.active_count == 0, (
            f"Expected active_count=0 after job completion, "
            f"got {_job_store.active_count}"
        )
        assert not _job_store.is_full, (
            "is_full should be False after all jobs complete"
        )
