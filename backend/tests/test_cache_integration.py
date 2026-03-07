"""
Integration tests for cache behavior in the search pipeline (SP-001.5).

Tests verify that:
- The in-memory cache (PNCPClient) is actually used across repeated searches
- Cache hits reduce PNCP API calls to zero on second identical request
- Overlapping UFs across multiple searches accumulate hits
- /cache/stats and /cache/clear endpoints reflect real cache state

Strategy:
- Mock `pncp_client.PNCPClient.fetch_page` to control HTTP responses and count
  calls without hitting the network. The real cache logic (_cache_get/_cache_put)
  is intentionally NOT mocked so the cache operates end-to-end.
- Mock `llm.gerar_resumo` and `excel.create_excel` to avoid I/O and external
  API dependencies.
- Mock `filter.filter_batch` to pass items through unchanged.
- Use TestClient(app) for all HTTP calls.
- Reset `main._pncp_client` and `main._job_store` between tests so each test
  starts with a fresh client and empty job store.
"""

import asyncio
import time
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import main as main_module
from main import app, _job_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATE_INICIAL = "2026-02-01"
DATE_FINAL = "2026-02-07"  # 7-day window (fits within 30-day chunk, no splits)


def make_pncp_response(uf: str, n_items: int = 10) -> dict:
    """Build a synthetic single-page PNCP API response for a given UF."""
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


def _make_resumo():
    """Return a minimal valid ResumoLicitacoes Pydantic model."""
    from schemas import ResumoLicitacoes

    return ResumoLicitacoes(
        resumo_executivo="Resumo de teste",
        total_oportunidades=0,
        valor_total=0.0,
        destaques=[],
        alerta_urgencia=None,
    )


def _filter_passthrough(bids, **kwargs):
    """filter_batch replacement that approves all items."""
    return list(bids), {
        "total": len(bids),
        "aprovadas": len(bids),
        "rejeitadas_uf": 0,
        "rejeitadas_valor": 0,
        "rejeitadas_keyword": 0,
        "rejeitadas_prazo": 0,
        "rejeitadas_outros": 0,
    }


def _wait_for_job(http_client: TestClient, job_id: str, timeout: float = 15.0) -> dict:
    """
    Poll GET /buscar/{job_id}/result until the job completes or the timeout
    expires. Returns the final JSON response dict.

    Raises RuntimeError if the job does not finish within `timeout` seconds.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = http_client.get(f"/buscar/{job_id}/result")
        if resp.status_code in (200, 500):
            return resp.json()
        # 202 = still running
        time.sleep(0.1)
    raise RuntimeError(f"Job {job_id!r} did not complete within {timeout}s")


def _post_search(http_client: TestClient, ufs: list[str]) -> str:
    """POST /buscar and return the job_id."""
    payload = {
        "ufs": ufs,
        "data_inicial": DATE_INICIAL,
        "data_final": DATE_FINAL,
    }
    resp = http_client.post("/buscar", json=payload)
    assert resp.status_code == 200, f"POST /buscar failed: {resp.text}"
    return resp.json()["job_id"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_app_state(monkeypatch):
    """
    Reset shared app state before (and after) every test so cache counters
    and job store are clean. A brand-new PNCPClient is created on the first
    _get_pncp_client() call after the reset.
    """
    main_module._pncp_client = None
    main_module._pncp_source = None
    main_module._orchestrator = None
    _job_store._jobs.clear()
    # Restrict orchestrator to PNCP only (avoid hitting real external APIs)
    monkeypatch.setattr(
        "sources.orchestrator.get_enabled_source_names",
        lambda: ["pncp"],
    )
    yield
    main_module._pncp_client = None
    main_module._pncp_source = None
    main_module._orchestrator = None
    _job_store._jobs.clear()


@pytest.fixture()
def http_client():
    """Return a FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture()
def mock_excel(monkeypatch):
    """Replace create_excel with a no-op that returns a minimal buffer."""

    def _fake_excel(bids):
        buf = BytesIO(b"fake-excel")
        buf.seek(0)
        return buf

    monkeypatch.setattr("main.create_excel", _fake_excel)


@pytest.fixture()
def mock_llm(monkeypatch):
    """Replace gerar_resumo (and fallback) with a fast stub."""
    monkeypatch.setattr("main.gerar_resumo", lambda bids, **kw: _make_resumo())
    monkeypatch.setattr(
        "main.gerar_resumo_fallback", lambda bids, **kw: _make_resumo()
    )


@pytest.fixture()
def mock_filter(monkeypatch):
    """Replace filter_batch with a pass-through stub."""
    monkeypatch.setattr("main.filter_batch", _filter_passthrough)


# ---------------------------------------------------------------------------
# Shared run_sync fixture (avoids executor deadlocks in TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture()
def run_sync(monkeypatch):
    """
    Replace run_search_job with a version that executes run_in_executor calls
    synchronously. This prevents TestClient / asyncio deadlocks while still
    exercising the full pipeline logic.
    """
    original_run_search_job = main_module.run_search_job

    async def _inline(job_id, request):
        loop = asyncio.get_event_loop()
        original_rie = loop.run_in_executor

        def _sync_rie(executor, func, *args):
            fut = loop.create_future()
            try:
                fut.set_result(func(*args))
            except Exception as exc:
                fut.set_exception(exc)
            return fut

        loop.run_in_executor = _sync_rie
        try:
            await original_run_search_job(job_id, request)
        finally:
            loop.run_in_executor = original_rie

    monkeypatch.setattr("main.run_search_job", _inline)


# ---------------------------------------------------------------------------
# Helper: build a fetch_page side_effect that dispatches by UF
# ---------------------------------------------------------------------------


def _make_fetch_page_side_effect(call_counter: dict, uf_responses: dict):
    """
    Return a callable suitable for `fetch_page.side_effect`.

    `call_counter` is mutated (key "count") on every call.
    `uf_responses` maps UF str -> response dict (or a default).
    """

    def _fetch_page(
        data_inicial,
        data_final,
        modalidade,
        uf=None,
        pagina=1,
        tamanho=50,
    ):
        call_counter["count"] += 1
        response = uf_responses.get(uf, make_pncp_response(uf or "ALL"))
        return response

    return _fetch_page


# ===========================================================================
# TestCacheHit
# ===========================================================================


class TestCacheHit:
    """Verify that identical searches reuse the in-memory cache."""

    def test_second_identical_search_uses_cache(
        self,
        http_client,
        mock_excel,
        mock_llm,
        mock_filter,
        run_sync,
    ):
        """
        Second search with the same UF+dates should hit the cache and make
        zero additional PNCP API calls. /cache/stats must report hits > 0.
        """
        call_counter = {"count": 0}
        uf_responses = {"SP": make_pncp_response("SP", n_items=5)}
        side_effect = _make_fetch_page_side_effect(call_counter, uf_responses)

        with patch.object(
            main_module._get_pncp_client().__class__,
            "fetch_page",
            side_effect=side_effect,
        ):
            # --- First search ---
            job_id_1 = _post_search(http_client, ufs=["SP"])
            result_1 = _wait_for_job(http_client, job_id_1)
            assert result_1["status"] == "completed", f"First job failed: {result_1}"
            calls_after_first = call_counter["count"]
            assert calls_after_first > 0, "Expected at least 1 PNCP API call on first search"

            # --- Second identical search ---
            job_id_2 = _post_search(http_client, ufs=["SP"])
            result_2 = _wait_for_job(http_client, job_id_2)
            assert result_2["status"] == "completed", f"Second job failed: {result_2}"
            calls_after_second = call_counter["count"]

            # The second search should not have made any new HTTP calls
            assert calls_after_second == calls_after_first, (
                f"Expected 0 new PNCP API calls on second search (cache hit), "
                f"but got {calls_after_second - calls_after_first} new call(s)"
            )

        # Verify cache stats via endpoint
        stats_resp = http_client.get("/cache/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["hits"] > 0, f"Expected cache hits > 0, got: {stats}"

    def test_cache_hit_ratio_overlapping_ufs(
        self,
        http_client,
        mock_excel,
        mock_llm,
        mock_filter,
        run_sync,
    ):
        """
        Four searches with overlapping UF sets should accumulate cache hits and
        push hit_ratio above 0.5.

        With DEFAULT_MODALIDADES containing 5 codes, each UF produces 5 cache
        entries (one per modalidade):

        Search 1: ["SP", "RJ"]  -> 10 misses (cold)        total: 10m  0h
        Search 2: ["RJ", "MG"]  -> 5 hits (RJ) + 5 misses  total: 15m  5h
        Search 3: ["SP", "MG"]  -> 10 hits (SP+MG cached)  total: 15m 15h
        Search 4: ["SP", "RJ"]  -> 10 hits (all cached)    total: 15m 25h

        Final: 25 hits / 40 total = 0.625 > 0.5
        """
        call_counter = {"count": 0}
        uf_responses = {
            "SP": make_pncp_response("SP", n_items=3),
            "RJ": make_pncp_response("RJ", n_items=3),
            "MG": make_pncp_response("MG", n_items=3),
        }
        side_effect = _make_fetch_page_side_effect(call_counter, uf_responses)

        with patch.object(
            main_module._get_pncp_client().__class__,
            "fetch_page",
            side_effect=side_effect,
        ):
            # Search 1: SP + RJ (cold)
            job1 = _post_search(http_client, ufs=["SP", "RJ"])
            r1 = _wait_for_job(http_client, job1)
            assert r1["status"] == "completed", f"Search 1 failed: {r1}"

            # Search 2: RJ + MG (RJ should be cached)
            job2 = _post_search(http_client, ufs=["RJ", "MG"])
            r2 = _wait_for_job(http_client, job2)
            assert r2["status"] == "completed", f"Search 2 failed: {r2}"

            # Search 3: SP + MG (both fully cached)
            job3 = _post_search(http_client, ufs=["SP", "MG"])
            r3 = _wait_for_job(http_client, job3)
            assert r3["status"] == "completed", f"Search 3 failed: {r3}"

            # Search 4: SP + RJ again (fully cached — pushes ratio well above 0.5)
            job4 = _post_search(http_client, ufs=["SP", "RJ"])
            r4 = _wait_for_job(http_client, job4)
            assert r4["status"] == "completed", f"Search 4 failed: {r4}"

        stats_resp = http_client.get("/cache/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()

        assert stats["hits"] > 0, f"Expected at least 1 cache hit, got: {stats}"
        assert stats["hit_ratio"] > 0.5, (
            f"Expected hit_ratio > 0.5 after overlapping searches, got: {stats}"
        )

    def test_cache_stats_endpoint_returns_correct_metrics(
        self,
        http_client,
        mock_excel,
        mock_llm,
        mock_filter,
        run_sync,
    ):
        """
        After clearing the cache, running a search, and running the same
        search again, /cache/stats should reflect accurate counters.

        Phase 1 (after first search):
            entries > 0, misses > 0, hits == 0

        Phase 2 (after second identical search):
            hits > 0, hit_ratio > 0
        """
        call_counter = {"count": 0}
        uf_responses = {"RJ": make_pncp_response("RJ", n_items=4)}
        side_effect = _make_fetch_page_side_effect(call_counter, uf_responses)

        with patch.object(
            main_module._get_pncp_client().__class__,
            "fetch_page",
            side_effect=side_effect,
        ):
            # Clear cache to start from scratch
            clear_resp = http_client.post("/cache/clear")
            assert clear_resp.status_code == 200

            # Phase 1: first search (cold cache)
            job1 = _post_search(http_client, ufs=["RJ"])
            r1 = _wait_for_job(http_client, job1)
            assert r1["status"] == "completed", f"Phase 1 job failed: {r1}"

            stats1_resp = http_client.get("/cache/stats")
            assert stats1_resp.status_code == 200
            stats1 = stats1_resp.json()

            assert stats1["entries"] > 0, f"Expected entries > 0 after first search: {stats1}"
            assert stats1["misses"] > 0, f"Expected misses > 0 after first search: {stats1}"
            assert stats1["hits"] == 0, f"Expected hits == 0 after first (cold) search: {stats1}"

            # Phase 2: second identical search (warm cache)
            job2 = _post_search(http_client, ufs=["RJ"])
            r2 = _wait_for_job(http_client, job2)
            assert r2["status"] == "completed", f"Phase 2 job failed: {r2}"

            stats2_resp = http_client.get("/cache/stats")
            assert stats2_resp.status_code == 200
            stats2 = stats2_resp.json()

            assert stats2["hits"] > 0, f"Expected hits > 0 after second search: {stats2}"
            assert stats2["hit_ratio"] > 0.0, (
                f"Expected hit_ratio > 0 after second search: {stats2}"
            )


# ===========================================================================
# TestCacheClear
# ===========================================================================


class TestCacheClear:
    """Verify that POST /cache/clear resets all cache state."""

    def test_cache_clear_resets_all(
        self,
        http_client,
        mock_excel,
        mock_llm,
        mock_filter,
        run_sync,
    ):
        """
        After populating the cache with a search, POST /cache/clear must
        return the number of removed entries and leave entries == 0.
        """
        call_counter = {"count": 0}
        uf_responses = {"MG": make_pncp_response("MG", n_items=6)}
        side_effect = _make_fetch_page_side_effect(call_counter, uf_responses)

        with patch.object(
            main_module._get_pncp_client().__class__,
            "fetch_page",
            side_effect=side_effect,
        ):
            # Populate cache via a search
            job_id = _post_search(http_client, ufs=["MG"])
            result = _wait_for_job(http_client, job_id)
            assert result["status"] == "completed", f"Populate job failed: {result}"

            # Verify cache has entries
            stats_before = http_client.get("/cache/stats").json()
            assert stats_before["entries"] > 0, (
                f"Cache should have entries after search: {stats_before}"
            )

            # Clear cache
            clear_resp = http_client.post("/cache/clear")
            assert clear_resp.status_code == 200
            clear_data = clear_resp.json()

            assert "cleared" in clear_data, f"Response missing 'cleared' key: {clear_data}"
            assert clear_data["cleared"] > 0, (
                f"Expected cleared > 0 after populated cache: {clear_data}"
            )

            # Verify cache is now empty
            stats_after = http_client.get("/cache/stats").json()
            assert stats_after["entries"] == 0, (
                f"Expected 0 entries after clear, got: {stats_after}"
            )
            # Hits and misses counters are also reset by cache_clear
            assert stats_after["hits"] == 0, (
                f"Expected hits reset to 0 after clear: {stats_after}"
            )
            assert stats_after["misses"] == 0, (
                f"Expected misses reset to 0 after clear: {stats_after}"
            )
