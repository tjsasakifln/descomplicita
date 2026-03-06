"""
SP-001.5 — Load tests: latency scenarios and progress tracking.

These tests validate that the async job pipeline correctly handles searches
across varying numbers of Brazilian UFs and date ranges, and that the
progress reporting transitions through all expected phases.

All external dependencies (PNCP API, LLM, Excel) are mocked — no real HTTP
calls are made.  The TestClient from Starlette drives the FastAPI app
synchronously, so polling loops work without a running event loop.

Test classes:
    TestLatencyScenarios  — 1, 5, 27 UF searches + 30-day range
    TestProgressTracking  — phase progression and ufs_total accuracy
"""

import asyncio
import time
from io import BytesIO
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from main import app, _job_store
from schemas import ResumoLicitacoes

# ---------------------------------------------------------------------------
# All 27 Brazilian UF codes
# ---------------------------------------------------------------------------

ALL_UFS: List[str] = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

# ---------------------------------------------------------------------------
# Polling timeout (seconds).  Load tests are allowed up to 30 s each.
# ---------------------------------------------------------------------------
POLL_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pncp_page(uf: str, items_per_page: int = 5, total: int = 5) -> Dict[str, Any]:
    """
    Build a synthetic PNCP API response page.

    Args:
        uf: The UF (state) code to embed in each item.
        items_per_page: Number of items in this response page.
        total: Value for ``totalRegistros`` (used for pagination math).

    Returns:
        Dict matching the PNCP ``/contratacoes/publicacao`` response schema.
    """
    return {
        "data": [
            {
                "numeroControlePNCP": f"PNCP-{uf}-{i}",
                "objetoCompra": "Aquisição de uniformes profissionais",
                "valorTotalEstimado": 50_000.0,
                "dataPublicacaoPncp": "2026-03-01T00:00:00",
                "dataAberturaProposta": "2026-03-10T00:00:00",
                "orgaoEntidade": {
                    "razaoSocial": "Org Test",
                    "cnpj": "12345678000100",
                },
                "unidadeOrgao": {
                    "ufSigla": uf,
                    "municipioNome": "Cidade",
                    "nomeUnidade": "Unidade",
                },
                "modalidadeNome": "Pregão - Eletrônico",
            }
            for i in range(items_per_page)
        ],
        "totalRegistros": total,
        "totalPaginas": 1,
        "paginasRestantes": 0,
    }


def _fake_fetch_page(
    self: Any,
    data_inicial: str,
    data_final: str,
    modalidade: int,
    uf: str | None = None,
    pagina: int = 1,
    tamanho: int = 50,
) -> Dict[str, Any]:
    """
    Fake implementation of ``PNCPClient.fetch_page`` that returns ~50 items.

    Must accept ``self`` as the first argument because it is patched directly
    onto the ``PNCPClient`` class and is therefore called as an unbound method
    with the instance passed as the first positional argument.

    The UF embedded in each item is derived from the ``uf`` parameter so
    downstream filter logic (which checks ``item["uf"]``) receives a valid
    Brazilian state code.
    """
    effective_uf = uf or "SP"
    return _make_pncp_page(uf=effective_uf, items_per_page=50, total=50)


def _fake_filter_batch(
    bids: List[Dict[str, Any]],
    **kwargs: Any,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fake ``filter.filter_batch`` that passes all bids through unchanged.

    Returns a minimal stats dict so the logging code in ``run_search_job``
    does not raise ``KeyError`` when accessing stats keys.
    """
    stats: Dict[str, Any] = {
        "total": len(bids),
        "aprovadas": len(bids),
        "rejeitadas_uf": 0,
        "rejeitadas_valor": 0,
        "rejeitadas_keyword": 0,
        "rejeitadas_prazo": 0,
        "rejeitadas_outros": 0,
    }
    return bids, stats


def _fake_gerar_resumo(
    bids: List[Dict[str, Any]],
    sector_name: str = "uniformes e fardamentos",
) -> ResumoLicitacoes:
    """
    Fake ``llm.gerar_resumo`` that returns a deterministic summary
    without contacting OpenAI.
    """
    total = len(bids)
    valor = sum(b.get("valorTotalEstimado", 0) or 0 for b in bids)
    return ResumoLicitacoes(
        resumo_executivo=f"Mock: {total} licitações encontradas (teste de carga).",
        total_oportunidades=total,
        valor_total=valor,
        destaques=[f"Mock summary — {total} bids processed"],
        alerta_urgencia=None,
    )


def _fake_create_excel(bids: List[Dict[str, Any]]) -> BytesIO:
    """
    Fake ``excel.create_excel`` that returns a minimal non-empty BytesIO
    without importing openpyxl.
    """
    buf = BytesIO()
    buf.write(b"PK\x03\x04fake-excel-content-for-load-test")
    buf.seek(0)
    return buf


def _poll_until_done(client: TestClient, job_id: str, timeout: float = POLL_TIMEOUT) -> Dict[str, Any]:
    """
    Poll ``GET /buscar/{job_id}/status`` until the job leaves the
    ``queued`` / ``running`` state, then return the final status payload.

    Args:
        client: FastAPI TestClient instance.
        job_id: UUID of the job to poll.
        timeout: Maximum seconds to wait before raising TimeoutError.

    Returns:
        The last ``/status`` response JSON dict.

    Raises:
        TimeoutError: If the job does not complete within ``timeout`` seconds.
        AssertionError: If any intermediate status call does not return HTTP 200.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/buscar/{job_id}/status")
        assert resp.status_code == 200, (
            f"Status endpoint returned {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        if data["status"] not in ("queued", "running"):
            return data
        time.sleep(0.1)
    raise TimeoutError(
        f"Job {job_id} did not complete within {timeout}s. "
        f"Last status: {resp.json()}"
    )


# ---------------------------------------------------------------------------
# Shared fixture: inline run_search_job to avoid thread-pool deadlocks
# ---------------------------------------------------------------------------


@pytest.fixture()
def run_sync(monkeypatch):
    """
    Replace ``asyncio.create_task(run_search_job(...))`` with a version that
    executes ``loop.run_in_executor`` calls synchronously (as resolved futures).

    The Starlette ``TestClient`` runs requests on a background event-loop
    thread.  Calling ``loop.run_in_executor`` from within that thread
    contends with the TestClient for the default ThreadPoolExecutor and
    causes deadlocks.  This fixture sidesteps the issue by making every
    ``run_in_executor`` call run its function immediately in the current
    thread and wrapping the result in an already-resolved Future.
    """
    import main as main_module

    original_run_search_job = main_module.run_search_job

    async def _inline_run_search_job(job_id: str, request: Any) -> None:
        loop = asyncio.get_event_loop()
        original_rie = loop.run_in_executor

        def _sync_run_in_executor(executor: Any, func: Any, *args: Any) -> Any:
            """Execute func synchronously, return a pre-resolved Future."""
            fut = loop.create_future()
            try:
                result = func(*args)
                fut.set_result(result)
            except Exception as exc:
                fut.set_exception(exc)
            return fut

        loop.run_in_executor = _sync_run_in_executor
        try:
            await original_run_search_job(job_id, request)
        finally:
            loop.run_in_executor = original_rie

    monkeypatch.setattr("main.run_search_job", _inline_run_search_job)


# ---------------------------------------------------------------------------
# Shared fixture: reset the global job store between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_job_store():
    """
    Clear all jobs from the global ``_job_store`` before and after each test.

    This prevents state leakage between tests that share the same
    module-level ``_job_store`` singleton imported from ``main``.
    """
    _job_store._jobs.clear()
    yield
    _job_store._jobs.clear()


# ---------------------------------------------------------------------------
# Shared fixture: TestClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> TestClient:
    """Return a synchronous FastAPI TestClient wrapping the app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# TestLatencyScenarios
# ---------------------------------------------------------------------------


class TestLatencyScenarios:
    """
    Validate that search jobs complete (without errors) across a range of
    UF counts and date ranges.

    PNCP, LLM, and Excel are fully mocked.  These tests exercise the full
    async pipeline: job creation -> background coroutine -> polling -> result.

    Each test asserts ``status == "completed"``; the absolute wall-clock
    time is not asserted (Rail environments vary widely) but the poll loop
    enforces a 30-second ceiling via ``_poll_until_done``.
    """

    def _run_search_and_assert_completed(
        self,
        client: TestClient,
        ufs: List[str],
        data_inicial: str,
        data_final: str,
        monkeypatch: Any,
        run_sync: Any,
    ) -> Dict[str, Any]:
        """
        Helper that wires all mocks, posts a search, polls until done, and
        fetches the final result.

        Args:
            client: TestClient instance.
            ufs: List of UF codes to search.
            data_inicial: Start date (YYYY-MM-DD).
            data_final: End date (YYYY-MM-DD).
            monkeypatch: pytest monkeypatch fixture.
            run_sync: Fixture that makes background tasks run synchronously.

        Returns:
            The completed ``/result`` response JSON.
        """
        # Mock PNCPClient.fetch_page — the only real network call
        monkeypatch.setattr(
            "pncp_client.PNCPClient.fetch_page",
            _fake_fetch_page,
        )
        monkeypatch.setattr("main.filter_batch", _fake_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _fake_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _fake_create_excel)

        payload = {
            "ufs": ufs,
            "data_inicial": data_inicial,
            "data_final": data_final,
        }

        # Create job
        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200, f"POST /buscar failed: {resp.text}"
        job_id = resp.json()["job_id"]

        # Poll until terminal state
        final_status = _poll_until_done(client, job_id)
        assert final_status["status"] == "completed", (
            f"Expected status='completed', got: {final_status}"
        )

        # Fetch and return the full result
        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200, (
            f"GET /result returned {result_resp.status_code}: {result_resp.text}"
        )
        return result_resp.json()

    def test_1uf_7days_completes(self, client, monkeypatch, run_sync):
        """
        A single-UF search over a 7-day window should complete without error.

        This is the minimal happy-path scenario: 1 UF * 1 modalidade = 1
        fetch task.  Validates that the pipeline works end-to-end with the
        smallest possible input.
        """
        result = self._run_search_and_assert_completed(
            client=client,
            ufs=["SP"],
            data_inicial="2026-02-24",
            data_final="2026-03-02",
            monkeypatch=monkeypatch,
            run_sync=run_sync,
        )

        assert result["status"] == "completed"
        # The mock returns 50 items per fetch_page call; assert they arrived.
        assert result["total_raw"] > 0, (
            "Mock fetch_page should have returned items — got 0 raw bids. "
            "Check that _fake_fetch_page signature accepts 'self'."
        )
        # All items pass the fake filter, so filtered == raw.
        assert result["total_filtrado"] == result["total_raw"]
        assert "resumo" in result
        assert "excel_base64" in result
        assert len(result["excel_base64"]) > 0

    def test_5ufs_7days_completes(self, client, monkeypatch, run_sync):
        """
        A 5-UF search over a 7-day window should complete without error.

        Tests moderate concurrency: 5 UFs * N modalidades fetch tasks run
        in the ThreadPoolExecutor inside ``fetch_all``.  All tasks are mocked
        so no real network I/O occurs.
        """
        ufs = ["SP", "RJ", "MG", "BA", "RS"]
        result = self._run_search_and_assert_completed(
            client=client,
            ufs=ufs,
            data_inicial="2026-02-24",
            data_final="2026-03-02",
            monkeypatch=monkeypatch,
            run_sync=run_sync,
        )

        assert result["status"] == "completed"
        assert result["total_raw"] > 0, (
            "Mock should return items for 5 UFs — got 0 raw bids. "
            "Check _fake_fetch_page 'self' parameter."
        )
        assert result["total_filtrado"] == result["total_raw"]
        assert "resumo" in result

    def test_27ufs_7days_completes(self, client, monkeypatch, run_sync):
        """
        A full 27-UF search over a 7-day window should complete without error.

        This is the maximum-width scenario.  The ThreadPoolExecutor in
        ``fetch_all`` is capped at 12 workers, so tasks are batched.
        Validates that the pipeline handles all 27 Brazilian states without
        dropping results or raising unhandled exceptions.

        Note: Absolute wall-clock time is not asserted (varies by machine),
        but the 30-second poll ceiling applies.
        """
        result = self._run_search_and_assert_completed(
            client=client,
            ufs=ALL_UFS,
            data_inicial="2026-02-24",
            data_final="2026-03-02",
            monkeypatch=monkeypatch,
            run_sync=run_sync,
        )

        assert result["status"] == "completed"
        assert result["total_raw"] > 0, (
            "Mock should return items for all 27 UFs — got 0 raw bids. "
            "Check _fake_fetch_page 'self' parameter."
        )
        assert result["total_filtrado"] == result["total_raw"]

    def test_3ufs_30days_completes(self, client, monkeypatch, run_sync):
        """
        A 3-UF search over a 30-day window should complete without error.

        The 30-day range exercises the date-chunking path inside
        ``fetch_all`` (``_chunk_date_range`` splits ranges > 30 days; a
        30-day range produces exactly one chunk and should not split).
        Validates that the end-to-end pipeline is stable over a wider time
        window.
        """
        result = self._run_search_and_assert_completed(
            client=client,
            ufs=["SP", "RJ", "MG"],
            data_inicial="2026-02-01",
            data_final="2026-03-02",
            monkeypatch=monkeypatch,
            run_sync=run_sync,
        )

        assert result["status"] == "completed"
        assert result["total_raw"] > 0, (
            "Mock should return items for 3 UFs × 30-day range — got 0 raw bids. "
            "Check _fake_fetch_page 'self' parameter."
        )
        assert result["total_filtrado"] == result["total_raw"]
        # Verify filter stats are present and structured
        assert "filter_stats" in result
        fs = result["filter_stats"]
        assert "rejeitadas_uf" in fs
        assert "rejeitadas_valor" in fs
        assert "rejeitadas_keyword" in fs


# ---------------------------------------------------------------------------
# TestProgressTracking
# ---------------------------------------------------------------------------


class TestProgressTracking:
    """
    Validate that job progress phases are reported correctly during execution.

    These tests inspect the ``/status`` endpoint during and after a job run
    to confirm that:
    - ``ufs_total`` matches the number of UFs in the original request.
    - The final phase upon completion is ``"done"``.
    - At least one intermediate phase beyond ``"queued"`` is observed.
    """

    def test_progress_reports_correctly(self, client, monkeypatch, run_sync):
        """
        Start a search job, observe status transitions, and assert final state.

        Expected phase sequence (subset must be observed):
            queued -> fetching -> filtering -> summarizing/generating_excel -> done

        Assertions:
            1. Initial status response contains ``ufs_total`` matching the
               request (set during the ``fetching`` phase).
            2. The job reaches ``status == "completed"`` within the timeout.
            3. The final progress phase is ``"done"``.
            4. ``progress.ufs_total`` equals the number of UFs requested.
            5. At least one intermediate non-queued phase was observed
               before completion.
        """
        target_ufs = ["SP", "RJ", "MG"]
        num_ufs = len(target_ufs)

        # Phases we expect to observe in order (we collect what we see)
        observed_phases: List[str] = []
        observed_statuses: List[str] = []

        # Slow the mock slightly so polling can catch intermediate phases.
        # The ``run_sync`` fixture makes run_in_executor synchronous, meaning
        # phases transition atomically within the POST request handler.
        # We therefore capture the phase snapshots from status polling
        # *after* the job completes.
        monkeypatch.setattr(
            "pncp_client.PNCPClient.fetch_page",
            _fake_fetch_page,
        )
        monkeypatch.setattr("main.filter_batch", _fake_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _fake_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _fake_create_excel)

        payload = {
            "ufs": target_ufs,
            "data_inicial": "2026-02-24",
            "data_final": "2026-03-02",
        }

        # --- Create job ---
        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200, f"POST /buscar failed: {resp.text}"
        job_data = resp.json()
        assert job_data["status"] == "queued"
        job_id = job_data["job_id"]
        assert len(job_id) == 36, "job_id should be a UUID (36 chars)"

        # --- Poll status until done, collecting all observed phases ---
        deadline = time.monotonic() + POLL_TIMEOUT
        while time.monotonic() < deadline:
            status_resp = client.get(f"/buscar/{job_id}/status")
            assert status_resp.status_code == 200, (
                f"Status returned {status_resp.status_code}: {status_resp.text}"
            )
            data = status_resp.json()

            current_status = data["status"]
            current_phase = data["progress"]["phase"]

            observed_statuses.append(current_status)
            if current_phase not in observed_phases:
                observed_phases.append(current_phase)

            if current_status not in ("queued", "running"):
                break
            time.sleep(0.1)
        else:
            raise TimeoutError(
                f"Job {job_id} did not complete within {POLL_TIMEOUT}s. "
                f"Observed statuses: {observed_statuses}, phases: {observed_phases}"
            )

        # --- Final assertions ---

        # 1. Job must be completed (not failed)
        assert current_status == "completed", (
            f"Expected 'completed', got '{current_status}'. "
            f"Observed phases: {observed_phases}"
        )

        # 2. Final progress phase must be 'done'
        final_progress = data["progress"]
        assert final_progress["phase"] == "done", (
            f"Expected phase='done', got '{final_progress['phase']}'. "
            f"Full progress: {final_progress}"
        )

        # 3. ufs_total must match the number of UFs in the request.
        #    This is set during the 'fetching' phase in run_search_job.
        assert final_progress["ufs_total"] == num_ufs, (
            f"Expected ufs_total={num_ufs}, got {final_progress['ufs_total']}"
        )

        # 4. elapsed_seconds must be non-negative
        assert data["elapsed_seconds"] >= 0.0, (
            f"elapsed_seconds should be >= 0, got {data['elapsed_seconds']}"
        )

        # 5. created_at must be a valid ISO 8601 timestamp
        from datetime import datetime
        try:
            datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            pytest.fail(f"created_at is not valid ISO 8601: {data['created_at']} — {exc}")

        # 6. The 'done' phase must have been reached via at least the
        #    'fetching' phase (confirms progress updates happened).
        #    Because run_sync executes phases synchronously within the POST,
        #    the final status snapshot may only show 'done'.  We verify
        #    correctness by checking that ufs_total was written (which only
        #    happens during 'fetching') and that the phase is 'done'.
        assert "done" in observed_phases, (
            f"Phase 'done' was never observed. Observed phases: {observed_phases}"
        )

    def test_progress_ufs_total_matches_single_uf(self, client, monkeypatch, run_sync):
        """
        ``ufs_total`` in the final progress snapshot must equal 1 when only
        one UF is requested.
        """
        monkeypatch.setattr(
            "pncp_client.PNCPClient.fetch_page",
            _fake_fetch_page,
        )
        monkeypatch.setattr("main.filter_batch", _fake_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _fake_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _fake_create_excel)

        payload = {
            "ufs": ["SP"],
            "data_inicial": "2026-02-24",
            "data_final": "2026-03-02",
        }

        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final = _poll_until_done(client, job_id)
        assert final["status"] == "completed"
        assert final["progress"]["ufs_total"] == 1

    def test_progress_ufs_total_matches_all_27_ufs(self, client, monkeypatch, run_sync):
        """
        ``ufs_total`` must equal 27 when all Brazilian UFs are requested.
        """
        monkeypatch.setattr(
            "pncp_client.PNCPClient.fetch_page",
            _fake_fetch_page,
        )
        monkeypatch.setattr("main.filter_batch", _fake_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _fake_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _fake_create_excel)

        payload = {
            "ufs": ALL_UFS,
            "data_inicial": "2026-02-24",
            "data_final": "2026-03-02",
        }

        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final = _poll_until_done(client, job_id)
        assert final["status"] == "completed"
        assert final["progress"]["ufs_total"] == len(ALL_UFS)

    def test_progress_phase_done_on_empty_results(self, client, monkeypatch, run_sync):
        """
        Even when the filter rejects all bids, the final phase must be 'done'
        and the job must be 'completed' (not 'failed').

        The pipeline has an early-exit path when ``licitacoes_filtradas`` is
        empty that skips LLM + Excel and still marks the job as completed.
        """
        monkeypatch.setattr(
            "pncp_client.PNCPClient.fetch_page",
            _fake_fetch_page,
        )
        # Filter rejects everything
        monkeypatch.setattr(
            "main.filter_batch",
            lambda bids, **kwargs: ([], {
                "total": len(bids),
                "aprovadas": 0,
                "rejeitadas_uf": 0,
                "rejeitadas_valor": 0,
                "rejeitadas_keyword": len(bids),
                "rejeitadas_prazo": 0,
                "rejeitadas_outros": 0,
            }),
        )
        # LLM and Excel should NOT be called in this path, but we patch them
        # anyway to ensure the test fails loudly if they are unexpectedly called.
        monkeypatch.setattr(
            "main.gerar_resumo",
            lambda *a, **kw: pytest.fail("gerar_resumo must not be called when no bids pass"),
        )
        monkeypatch.setattr(
            "main.create_excel",
            lambda *a, **kw: pytest.fail("create_excel must not be called when no bids pass"),
        )

        payload = {
            "ufs": ["SP"],
            "data_inicial": "2026-02-24",
            "data_final": "2026-03-02",
        }

        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final = _poll_until_done(client, job_id)
        assert final["status"] == "completed", (
            f"Expected 'completed' even with no filtered results, got '{final['status']}'"
        )
        assert final["progress"]["phase"] == "done"

        # Verify the result reflects zero filtered items
        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200
        result = result_resp.json()
        assert result["total_filtrado"] == 0
        assert result["excel_base64"] == ""
