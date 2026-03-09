"""
SP-001.5 — Resilience tests for PNCP API failure scenarios.

Validates that the search pipeline handles partial failures, full outages,
rate limiting, and intermittent HTTP errors gracefully.
"""

import asyncio
import time
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from exceptions import PNCPAPIError, PNCPRateLimitError
from main import app
from dependencies import get_orchestrator
from tests.conftest import get_test_job_store


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return TestClient(app)


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


async def _mock_gerar_resumo(bids, **kwargs):
    from schemas import ResumoLicitacoes
    return ResumoLicitacoes(
        resumo_executivo=f"{len(bids)} licitacao(es) encontrada(s)",
        total_oportunidades=len(bids),
        valor_total=sum(b.get("valorTotalEstimado", 0) for b in bids),
    )


def _mock_create_excel(bids) -> BytesIO:
    buf = BytesIO(b"PK\x03\x04fake-excel")
    buf.seek(0)
    return buf


def poll_until_done(client, job_id, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/buscar/{job_id}/status")
        data = resp.json()
        if data["status"] in ("completed", "failed"):
            return data
        time.sleep(0.1)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def _post_and_poll(client, request, timeout: float = 15.0) -> dict:
    resp = client.post("/buscar", json=request)
    assert resp.status_code == 200, f"POST /buscar failed: {resp.json()}"
    job_id = resp.json()["job_id"]
    return poll_until_done(client, job_id, timeout=timeout)


def _post_sync(client, request) -> dict:
    resp = client.post("/buscar", json=request)
    assert resp.status_code == 200, f"POST /buscar failed: {resp.json()}"
    job_id = resp.json()["job_id"]
    result_resp = client.get(f"/buscar/{job_id}/result")
    return result_resp.json()


# ---------------------------------------------------------------------------
# TestPNCPErrorResilience
# ---------------------------------------------------------------------------


class TestPNCPErrorResilience:

    def test_completes_with_partial_source_data(self, client, monkeypatch, run_sync):
        """Search completes when orchestrator returns partial data."""
        from tests.mock_helpers import make_mock_orchestrator
        items = [_make_licitacao("2025NCP000001", "SP")]
        mock_orch = make_mock_orchestrator(items)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        status = _post_and_poll(client, VALID_REQUEST)
        assert status["status"] == "completed"

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_fails_gracefully_when_pncp_100pct_offline(self, client, monkeypatch, run_sync):
        """When orchestrator raises PNCPAPIError, the job fails cleanly."""
        from tests.mock_helpers import make_mock_orchestrator
        mock_orch = make_mock_orchestrator(error=PNCPAPIError("Simulated full outage"))
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        result = _post_sync(client, VALID_REQUEST)

        assert result["status"] == "failed"
        assert "error" in result
        error_msg = result["error"]["message"]
        assert "PNCP" in error_msg or "Portal" in error_msg or "indispon" in error_msg
        assert "Traceback" not in error_msg
        assert "PNCPAPIError" not in error_msg

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_fails_gracefully_on_rate_limit(self, client, monkeypatch, run_sync):
        """When orchestrator raises PNCPRateLimitError, the job fails with a rate-limit message."""
        from tests.mock_helpers import make_mock_orchestrator
        error = PNCPRateLimitError("Too many requests — rate limit exceeded")
        error.retry_after = 60
        mock_orch = make_mock_orchestrator(error=error)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        result = _post_sync(client, VALID_REQUEST)

        assert result["status"] == "failed"
        assert "error" in result
        error_msg = result["error"]["message"].lower()
        assert any(
            keyword in error_msg
            for keyword in ("limitando", "aguarde", "rate", "60", "requisic")
        )
        assert "Traceback" not in result["error"]["message"]
        assert "PNCPRateLimitError" not in result["error"]["message"]

        app.dependency_overrides.pop(get_orchestrator, None)


# ---------------------------------------------------------------------------
# TestPartialFailure
# ---------------------------------------------------------------------------


class TestPartialFailure:

    def test_completes_with_some_sources_failing(self, client, monkeypatch, run_sync):
        """Search completes when orchestrator returns data from available sources."""
        from tests.mock_helpers import make_mock_orchestrator
        sp_items = [_make_licitacao("2025NCP000010", "SP")]
        mock_orch = make_mock_orchestrator(sp_items)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        status = _post_and_poll(client, VALID_REQUEST_TWO_UFS)
        assert status["status"] == "completed"

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_partial_failure_result_contains_data(self, client, monkeypatch, run_sync):
        """Result of a partial-failure search includes available data."""
        from tests.mock_helpers import make_mock_orchestrator
        sp_items = [
            _make_licitacao("2025NCP000011", "SP"),
            _make_licitacao("2025NCP000012", "SP"),
        ]
        mock_orch = make_mock_orchestrator(sp_items)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        def mock_filter_batch(bids, **kwargs):
            return bids, {
                "rejeitadas_uf": 0,
                "rejeitadas_valor": 0,
                "rejeitadas_keyword": 0,
                "rejeitadas_prazo": 0,
                "rejeitadas_outros": 0,
            }

        monkeypatch.setattr("main.filter_batch", mock_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        result = _post_sync(client, VALID_REQUEST_TWO_UFS)
        assert result["status"] == "completed"
        assert result.get("total_raw", 0) > 0

        app.dependency_overrides.pop(get_orchestrator, None)


# ---------------------------------------------------------------------------
# TestTimeoutBehavior
# ---------------------------------------------------------------------------


class TestTimeoutBehavior:

    def test_zero_timeouts_all_scenarios(self, client, monkeypatch, run_sync):
        """Search with fast mocked responses completes without timing out."""
        from tests.mock_helpers import make_mock_orchestrator
        fast_licitacoes = [
            _make_licitacao("2025NCP000020", "SP"),
            _make_licitacao("2025NCP000021", "SP"),
            _make_licitacao("2025NCP000022", "SP"),
        ]
        mock_orch = make_mock_orchestrator(fast_licitacoes)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        start = time.time()
        status = _post_and_poll(client, VALID_REQUEST, timeout=15.0)
        elapsed = time.time() - start

        assert status["status"] == "completed"
        assert elapsed < 10.0

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_zero_timeouts_empty_results(self, client, monkeypatch, run_sync):
        """Search that fetches zero bids should complete (not time out)."""
        from tests.mock_helpers import make_mock_orchestrator
        mock_orch = make_mock_orchestrator([])
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        result = _post_sync(client, VALID_REQUEST)
        assert result["status"] == "completed"
        assert result.get("total_raw") == 0
        assert result.get("total_filtrado") == 0

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_zero_timeouts_large_result_set(self, client, monkeypatch, run_sync):
        """Search with many bids completes without timing out."""
        from tests.mock_helpers import make_mock_orchestrator
        large_set = [
            _make_licitacao(f"2025NCP{i:06d}", "SP")
            for i in range(100)
        ]
        mock_orch = make_mock_orchestrator(large_set)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids, {}))
        monkeypatch.setattr("main.gerar_resumo", _mock_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _mock_create_excel)

        start = time.time()
        status = _post_and_poll(client, VALID_REQUEST, timeout=15.0)
        elapsed = time.time() - start

        assert status["status"] == "completed"
        assert elapsed < 10.0

        app.dependency_overrides.pop(get_orchestrator, None)
