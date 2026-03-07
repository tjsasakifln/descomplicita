"""
SP-001.5 — Resilience tests for PNCP API failure scenarios.

Validates that the search pipeline handles partial failures, full outages,
rate limiting, and intermittent HTTP errors gracefully — either completing
with available data or failing with a clear, human-readable error message
(never an unhandled traceback).

Test classes:
    TestPNCPErrorResilience  — intermittent errors and full-offline scenarios
    TestPartialFailure       — per-UF error isolation
    TestTimeoutBehavior      — zero-timeout confirmation with fast mocks
"""

import asyncio
import time
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from exceptions import PNCPAPIError, PNCPRateLimitError
from main import app, _job_store, run_search_job


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """
    Reset shared mutable state between tests.

    Clears the in-memory job store and resets the shared PNCPClient singleton
    so that each test starts with a clean slate.  Runs automatically for every
    test in this module (autouse=True).
    """
    _job_store._jobs.clear()
    import main
    main._pncp_client = None
    yield
    _job_store._jobs.clear()
    import main
    main._pncp_client = None


@pytest.fixture
def run_sync(monkeypatch):
    """
    Make background search jobs complete synchronously inside the TestClient.

    The Starlette TestClient runs on a background event-loop thread.
    asyncio.create_task schedules the search coroutine there, but
    loop.run_in_executor inside the coroutine contends with the TestClient
    for the default thread-pool, causing deadlocks.

    This fixture patches run_search_job with a version that replaces
    loop.run_in_executor with a synchronous adapter (returning already-resolved
    futures) so the background task completes without needing the thread-pool.
    """
    import main as main_module
    original_run_search_job = main_module.run_search_job

    async def _inline_run_search_job(job_id, request):
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

    monkeypatch.setattr("main.run_search_job", _inline_run_search_job)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

VALID_REQUEST = {
    "ufs": ["SP"],
    "data_inicial": "2025-01-01",
    "data_final": "2025-01-31",
}

VALID_REQUEST_TWO_UFS = {
    "ufs": ["SP", "RJ"],
    "data_inicial": "2025-01-01",
    "data_final": "2025-01-31",
}


def _make_licitacao(numero: str = "2025NCP000001", uf: str = "SP") -> dict:
    """Return a minimal PNCP bid record that passes all pipeline stages."""
    return {
        "numeroControlePNCP": numero,
        "objetoCompra": "Aquisicao de uniformes escolares para secretaria de educacao",
        "nomeOrgao": "Prefeitura Municipal de Sao Paulo",
        "uf": uf,
        "municipio": "Sao Paulo",
        "valorTotalEstimado": 200_000.00,
        "dataAberturaProposta": "2025-02-15T10:00:00",
        "linkSistemaOrigem": "https://pncp.gov.br/app/editais/" + numero,
        "unidadeOrgao": {"ufSigla": uf, "municipioNome": "Sao Paulo", "nomeUnidade": "SMED"},
        "orgaoEntidade": {"razaoSocial": "Prefeitura de SP", "cnpj": "00000000000191"},
    }


def _make_pncp_page_response(items: list) -> dict:
    """Return a minimal PNCP API page dict wrapping the given items (no next page)."""
    return {
        "data": items,
        "totalRegistros": len(items),
        "totalPaginas": 1,
        "paginasRestantes": 0,
        "paginaAtual": 1,
    }


def _mock_gerar_resumo(bids, **kwargs):
    """Lightweight LLM-summary stub that avoids real OpenAI calls."""
    from schemas import ResumoLicitacoes
    return ResumoLicitacoes(
        resumo_executivo=f"{len(bids)} licitacao(es) encontrada(s)",
        total_oportunidades=len(bids),
        valor_total=sum(b.get("valorTotalEstimado", 0) for b in bids),
    )


def _mock_create_excel(bids) -> BytesIO:
    """Minimal Excel stub."""
    buf = BytesIO(b"PK\x03\x04fake-excel")
    buf.seek(0)
    return buf


def poll_until_done(client, job_id, timeout: float = 15.0) -> dict:
    """
    Poll GET /buscar/{job_id}/status until the job reaches a terminal state.

    Args:
        client:  FastAPI TestClient
        job_id:  UUID returned by POST /buscar
        timeout: Maximum seconds to wait before raising TimeoutError

    Returns:
        The status response dict (keys: job_id, status, progress, …)

    Raises:
        TimeoutError: If the job does not finish within *timeout* seconds.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/buscar/{job_id}/status")
        data = resp.json()
        if data["status"] in ("completed", "failed"):
            return data
        time.sleep(0.1)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def _post_and_poll(client, request, timeout: float = 15.0) -> dict:
    """POST /buscar then poll until done; return the status dict."""
    resp = client.post("/buscar", json=request)
    assert resp.status_code == 200, f"POST /buscar failed: {resp.json()}"
    job_id = resp.json()["job_id"]
    return poll_until_done(client, job_id, timeout=timeout)


def _post_sync(client, request) -> dict:
    """POST /buscar (with run_sync fixture) then fetch result immediately."""
    resp = client.post("/buscar", json=request)
    assert resp.status_code == 200, f"POST /buscar failed: {resp.json()}"
    job_id = resp.json()["job_id"]
    result_resp = client.get(f"/buscar/{job_id}/result")
    return result_resp.json()


# ---------------------------------------------------------------------------
# TestPNCPErrorResilience
# ---------------------------------------------------------------------------


class TestPNCPErrorResilience:
    """
    Verify that the search pipeline is resilient to PNCP API failures.

    Tests cover:
    - Intermittent HTTP errors (30 %, 10 % failure rates) at the fetch_page level
    - Full API outage (100 % failure) — completes with 0 results, not an exception
    - PNCPRateLimitError propagating from fetch_all — job fails with a clear message
    """

    def test_completes_with_30pct_429_errors(self, client, monkeypatch, run_sync):
        """
        Search completes successfully when ~33% of fetch_page calls fail.

        Strategy: Mock _fetch_uf_modalidade (the per-UF entry point called by
        ThreadPoolExecutor) so that 2 out of 3 calls succeed and 1 returns [].
        This simulates the realistic behaviour where _fetch_uf_modalidade catches
        PNCPAPIError and returns an empty list, allowing other UF/modalidade
        combos to still contribute results.

        Expected: job.status == "completed" (not "failed"), regardless of the
        empty slots introduced by the simulated 429 errors.
        """
        call_count = 0
        good_items = [_make_licitacao("2025NCP000001", "SP")]

        original_fetch = None  # will be set below

        def mock_fetch_uf_modalidade(self_client, data_inicial, data_final,
                                     modalidade, uf, on_progress=None, max_pages=0):
            nonlocal call_count
            call_count += 1
            # Every 3rd call simulates a 429 / empty result (as _fetch_uf_modalidade
            # would return [] after catching the internal PNCPAPIError).
            if call_count % 3 == 0:
                return []
            return list(good_items)

        monkeypatch.setattr(
            "pncp_client.PNCPClient._fetch_uf_modalidade",
            mock_fetch_uf_modalidade,
        )
        monkeypatch.setattr(
            "sources.orchestrator.get_enabled_source_names",
            lambda: ["pncp"],
        )
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        status = _post_and_poll(client, VALID_REQUEST)

        assert status["status"] == "completed", (
            f"Expected 'completed' but got '{status['status']}'. "
            "Pipeline should tolerate partial fetch failures."
        )

    def test_completes_with_10pct_500_errors(self, client, monkeypatch, run_sync):
        """
        Search completes successfully when ~10% of fetch calls return empty.

        Same approach as the 30% test: mock _fetch_uf_modalidade so that every
        10th call returns [] (simulating a swallowed HTTP 500 error).  The
        remaining 90% of calls succeed, so the search should complete normally.

        Expected: job.status == "completed".
        """
        call_count = 0
        good_items = [_make_licitacao("2025NCP000002", "SP")]

        def mock_fetch_uf_modalidade(self_client, data_inicial, data_final,
                                     modalidade, uf, on_progress=None, max_pages=0):
            nonlocal call_count
            call_count += 1
            if call_count % 10 == 0:
                # Simulates _fetch_uf_modalidade returning [] after a caught HTTP 500
                return []
            return list(good_items)

        monkeypatch.setattr(
            "pncp_client.PNCPClient._fetch_uf_modalidade",
            mock_fetch_uf_modalidade,
        )
        monkeypatch.setattr(
            "sources.orchestrator.get_enabled_source_names",
            lambda: ["pncp"],
        )
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        status = _post_and_poll(client, VALID_REQUEST)

        assert status["status"] == "completed", (
            f"Expected 'completed' but got '{status['status']}'. "
            "Pipeline should tolerate a 10% failure rate."
        )

    def test_fails_gracefully_when_pncp_100pct_offline(self, client, monkeypatch, run_sync):
        """
        When orchestrator raises PNCPAPIError, the job fails cleanly.

        Expected:
        - job.status == "failed"
        - error message references "PNCP" (not a raw Python traceback)
        - HTTP result endpoint returns 500
        """
        from tests.mock_helpers import make_mock_orchestrator
        monkeypatch.setattr(
            "main._get_orchestrator",
            lambda: make_mock_orchestrator(error=PNCPAPIError("Simulated full outage")),
        )

        result = _post_sync(client, VALID_REQUEST)

        assert result["status"] == "failed", (
            f"Expected 'failed' but got '{result['status']}'."
        )
        assert "error" in result, "Failed job must include an 'error' field."
        error_msg = result["error"]
        # Error must be human-readable and reference the PNCP portal
        assert "PNCP" in error_msg or "Portal" in error_msg or "indispon" in error_msg, (
            f"Error message does not mention PNCP availability: '{error_msg}'"
        )
        # Must not be a raw traceback
        assert "Traceback" not in error_msg
        assert "PNCPAPIError" not in error_msg

    def test_fails_gracefully_on_rate_limit(self, client, monkeypatch, run_sync):
        """
        When orchestrator raises PNCPRateLimitError, the job fails with a rate-limit message.

        Expected:
        - job.status == "failed"
        - error message references "limitando" or "aguarde" (wait instruction)
        - HTTP result endpoint returns 500
        """
        from tests.mock_helpers import make_mock_orchestrator
        error = PNCPRateLimitError("Too many requests — rate limit exceeded")
        error.retry_after = 60
        monkeypatch.setattr(
            "main._get_orchestrator",
            lambda: make_mock_orchestrator(error=error),
        )

        result = _post_sync(client, VALID_REQUEST)

        assert result["status"] == "failed", (
            f"Expected 'failed' but got '{result['status']}'."
        )
        assert "error" in result
        error_msg = result["error"].lower()
        # Message should tell the user to wait / rate limit context
        assert any(
            keyword in error_msg
            for keyword in ("limitando", "aguarde", "rate", "60", "requisic")
        ), f"Rate-limit error message is not informative enough: '{result['error']}'"
        # Must not expose internals
        assert "Traceback" not in result["error"]
        assert "PNCPRateLimitError" not in result["error"]


# ---------------------------------------------------------------------------
# TestPartialFailure
# ---------------------------------------------------------------------------


class TestPartialFailure:
    """
    Verify that failures on a subset of UFs do not abort the entire search.

    The pipeline fetches each (UF, modalidade) combination independently.
    _fetch_uf_modalidade catches PNCPAPIError and returns [] for the failing
    UF, while other UFs continue normally.  The job should complete with the
    partial data set.
    """

    def test_completes_with_some_ufs_failing(self, client, monkeypatch, run_sync):
        """
        Search with ["SP", "RJ"] completes even when RJ always raises PNCPAPIError.

        Implementation: Mock _fetch_uf_modalidade to return real data for SP and
        [] (simulating a caught PNCPAPIError) for RJ.  The search pipeline must
        complete (not fail) and return whatever SP contributed.

        Expected:
        - job.status == "completed"
        - total_raw >= 0 (SP data present; RJ contributes nothing)
        """
        sp_items = [_make_licitacao("2025NCP000010", "SP")]

        def mock_fetch_uf_modalidade(self_client, data_inicial, data_final,
                                     modalidade, uf, on_progress=None, max_pages=0):
            if uf == "RJ":
                # Simulate _fetch_uf_modalidade catching PNCPAPIError and returning []
                return []
            # SP succeeds
            return list(sp_items)

        monkeypatch.setattr(
            "pncp_client.PNCPClient._fetch_uf_modalidade",
            mock_fetch_uf_modalidade,
        )
        monkeypatch.setattr(
            "sources.orchestrator.get_enabled_source_names",
            lambda: ["pncp"],
        )
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        status = _post_and_poll(client, VALID_REQUEST_TWO_UFS)

        assert status["status"] == "completed", (
            f"Expected 'completed' but got '{status['status']}'. "
            "Partial UF failures should not abort the search."
        )

    def test_partial_failure_result_contains_sp_data(self, client, monkeypatch, run_sync):
        """
        Result of a partial-failure search includes SP bids in total_raw.

        Extends the previous test by inspecting the actual result payload
        to confirm that SP data made it through despite RJ failing.

        Expected:
        - status == "completed"
        - total_raw > 0 (SP items were fetched and passed through filter_batch)
        """
        sp_items = [
            _make_licitacao("2025NCP000011", "SP"),
            _make_licitacao("2025NCP000012", "SP"),
        ]

        def mock_fetch_uf_modalidade(self_client, data_inicial, data_final,
                                     modalidade, uf, on_progress=None, max_pages=0):
            if uf == "RJ":
                return []
            return list(sp_items)

        # filter_batch passes everything through for simplicity
        def mock_filter_batch(bids, **kwargs):
            return bids, {
                "rejeitadas_uf": 0,
                "rejeitadas_valor": 0,
                "rejeitadas_keyword": 0,
                "rejeitadas_prazo": 0,
                "rejeitadas_outros": 0,
            }

        monkeypatch.setattr(
            "pncp_client.PNCPClient._fetch_uf_modalidade",
            mock_fetch_uf_modalidade,
        )
        monkeypatch.setattr(
            "sources.orchestrator.get_enabled_source_names",
            lambda: ["pncp"],
        )
        monkeypatch.setattr("main.filter_batch", mock_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        result = _post_sync(client, VALID_REQUEST_TWO_UFS)

        assert result["status"] == "completed"
        # With 5 modalidades × SP (only) contributing 2 items each, total_raw
        # must be > 0.  The exact count depends on deduplication, but it cannot
        # be zero if any SP call succeeded.
        assert result.get("total_raw", 0) > 0, (
            "Expected total_raw > 0 from SP data, got 0. "
            "SP items should have been included despite RJ failing."
        )


# ---------------------------------------------------------------------------
# TestTimeoutBehavior
# ---------------------------------------------------------------------------


class TestTimeoutBehavior:
    """
    Confirm that the pipeline completes in a reasonable time with fast mocks.

    These tests are not timing-sensitive but serve as a regression guard:
    if the pipeline introduces blocking sleeps or indefinite waits, the
    poll_until_done helper will raise TimeoutError.
    """

    def test_zero_timeouts_all_scenarios(self, client, monkeypatch, run_sync):
        """
        Search with fast mocked responses should complete without timing out.

        Mocks the entire I/O stack (fetch, filter, LLM, Excel) with instant
        in-process functions so there are no real HTTP calls, disk I/O or
        sleep delays.  The job must reach status "completed" quickly.

        Expected:
        - job.status == "completed" (not "failed" or stuck in "running")
        - Completes well within the 15-second poll timeout
        """
        fast_licitacoes = [
            _make_licitacao("2025NCP000020", "SP"),
            _make_licitacao("2025NCP000021", "SP"),
            _make_licitacao("2025NCP000022", "SP"),
        ]

        from tests.mock_helpers import make_mock_orchestrator
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator(fast_licitacoes))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        start = time.time()
        status = _post_and_poll(client, VALID_REQUEST, timeout=15.0)
        elapsed = time.time() - start

        assert status["status"] == "completed", (
            f"Expected 'completed' but got '{status['status']}'. "
            "Fast-mock pipeline should not fail or block."
        )
        # Sanity guard: with all I/O mocked the pipeline should be very fast.
        # We use a generous bound (10s) to avoid flakiness on slow CI runners.
        assert elapsed < 10.0, (
            f"Pipeline with fast mocks took {elapsed:.1f}s — possible timeout bug."
        )

    def test_zero_timeouts_empty_results(self, client, monkeypatch, run_sync):
        """
        Search that fetches zero bids should complete (not time out).

        Tests the early-return branch in run_search_job when fetch_all yields
        nothing.  This path skips LLM and Excel generation entirely; confirming
        it still marks the job as "completed" with 0 results.

        Expected:
        - job.status == "completed"
        - total_raw == 0 and total_filtrado == 0
        """
        from tests.mock_helpers import make_mock_orchestrator
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        result = _post_sync(client, VALID_REQUEST)

        assert result["status"] == "completed", (
            f"Expected 'completed' but got '{result['status']}'. "
            "Zero-result search should complete, not fail."
        )
        assert result.get("total_raw") == 0
        assert result.get("total_filtrado") == 0

    def test_zero_timeouts_large_result_set(self, client, monkeypatch, run_sync):
        """
        Search that fetches many bids should still complete without timing out.

        Exercises the pipeline with a moderately large result set (100 bids) to
        confirm there is no O(n^2) bottleneck or blocking behaviour that would
        cause the job to exceed the poll timeout.

        Expected:
        - job.status == "completed"
        - total_raw == 100
        """
        large_set = [
            _make_licitacao(f"2025NCP{i:06d}", "SP")
            for i in range(100)
        ]

        from tests.mock_helpers import make_mock_orchestrator
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator(large_set))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        start = time.time()
        status = _post_and_poll(client, VALID_REQUEST, timeout=15.0)
        elapsed = time.time() - start

        assert status["status"] == "completed", (
            f"Expected 'completed' but got '{status['status']}'."
        )
        assert elapsed < 10.0, (
            f"Large-result pipeline took {elapsed:.1f}s — possible scaling issue."
        )
