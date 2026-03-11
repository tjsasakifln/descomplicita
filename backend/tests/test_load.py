"""
SP-001.5 — Load tests: latency scenarios and progress tracking.

These tests validate that the async job pipeline correctly handles searches
across varying numbers of Brazilian UFs and date ranges, and that the
progress reporting transitions through all expected phases.
"""

import asyncio
import time
from io import BytesIO
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from dependencies import get_orchestrator
from main import app
from schemas import ResumoLicitacoes
from tests.conftest import get_test_job_store

# ---------------------------------------------------------------------------
# All 27 Brazilian UF codes
# ---------------------------------------------------------------------------

ALL_UFS: list[str] = [
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MG",
    "MS",
    "MT",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RO",
    "RR",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
]

POLL_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_licitacao(numero: str, uf: str = "SP") -> dict:
    return {
        "numeroControlePNCP": numero,
        "objetoCompra": "Aquisição de uniformes profissionais",
        "valorTotalEstimado": 50_000.0,
        "dataPublicacaoPncp": "2026-03-01T00:00:00",
        "dataAberturaProposta": "2026-03-10T00:00:00",
        "orgaoEntidade": {"razaoSocial": "Org Test", "cnpj": "12345678000100"},
        "unidadeOrgao": {
            "ufSigla": uf,
            "municipioNome": "Cidade",
            "nomeUnidade": "Unidade",
        },
        "modalidadeNome": "Pregão - Eletrônico",
        "codigoCompra": numero,
        "nomeOrgao": "Org Test",
        "uf": uf,
        "municipio": "Cidade",
    }


def _fake_filter_batch(bids, **kwargs):
    stats = {
        "total": len(bids),
        "aprovadas": len(bids),
        "rejeitadas_uf": 0,
        "rejeitadas_valor": 0,
        "rejeitadas_keyword": 0,
        "rejeitadas_prazo": 0,
        "rejeitadas_outros": 0,
    }
    return bids, stats


async def _fake_gerar_resumo(bids, **kwargs):
    total = len(bids)
    valor = sum(b.get("valorTotalEstimado", 0) or 0 for b in bids)
    return ResumoLicitacoes(
        resumo_executivo=f"Mock: {total} licitações encontradas (teste de carga).",
        total_oportunidades=total,
        valor_total=valor,
        destaques=[f"Mock summary — {total} bids processed"],
        alerta_urgencia=None,
    )


def _fake_create_excel(bids):
    buf = BytesIO()
    buf.write(b"PK\x03\x04fake-excel-content-for-load-test")
    buf.seek(0)
    return buf


def _poll_until_done(client, job_id, timeout=POLL_TIMEOUT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/buscar/{job_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] not in ("queued", "running"):
            return data
        time.sleep(0.1)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


# ---------------------------------------------------------------------------
# Shared fixture: TestClient
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# TestLatencyScenarios
# ---------------------------------------------------------------------------


class TestLatencyScenarios:
    def _run_search_and_assert_completed(
        self,
        client,
        ufs,
        data_inicial,
        data_final,
        monkeypatch,
        run_sync,
        n_items_per_uf=50,
    ):
        from tests.mock_helpers import make_mock_orchestrator

        # Create items for all requested UFs
        items = []
        for uf in ufs:
            for i in range(n_items_per_uf):
                items.append(_make_licitacao(f"PNCP-{uf}-{i}", uf))

        mock_orch = make_mock_orchestrator(items)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", _fake_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _fake_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _fake_create_excel)

        payload = {
            "ufs": ufs,
            "data_inicial": data_inicial,
            "data_final": data_final,
        }

        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final_status = _poll_until_done(client, job_id)
        assert final_status["status"] == "completed"

        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200

        app.dependency_overrides.pop(get_orchestrator, None)
        return result_resp.json()

    def test_1uf_7days_completes(self, client, monkeypatch, run_sync):
        result = self._run_search_and_assert_completed(
            client=client,
            ufs=["SP"],
            data_inicial="2026-02-24",
            data_final="2026-03-02",
            monkeypatch=monkeypatch,
            run_sync=run_sync,
        )
        assert result["status"] == "completed"
        assert result["total_raw"] > 0
        assert result["total_filtrado"] == result["total_raw"]
        assert "resumo" in result

    def test_5ufs_7days_completes(self, client, monkeypatch, run_sync):
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
        assert result["total_raw"] > 0

    def test_27ufs_7days_completes(self, client, monkeypatch, run_sync):
        result = self._run_search_and_assert_completed(
            client=client,
            ufs=ALL_UFS,
            data_inicial="2026-02-24",
            data_final="2026-03-02",
            monkeypatch=monkeypatch,
            run_sync=run_sync,
            n_items_per_uf=5,
        )
        assert result["status"] == "completed"
        assert result["total_raw"] > 0

    def test_3ufs_30days_completes(self, client, monkeypatch, run_sync):
        result = self._run_search_and_assert_completed(
            client=client,
            ufs=["SP", "RJ", "MG"],
            data_inicial="2026-02-01",
            data_final="2026-03-02",
            monkeypatch=monkeypatch,
            run_sync=run_sync,
        )
        assert result["status"] == "completed"
        assert result["total_raw"] > 0
        assert "filter_stats" in result


# ---------------------------------------------------------------------------
# TestProgressTracking
# ---------------------------------------------------------------------------


class TestProgressTracking:
    def test_progress_reports_correctly(self, client, monkeypatch, run_sync):
        target_ufs = ["SP", "RJ", "MG"]
        num_ufs = len(target_ufs)

        observed_phases = []
        observed_statuses = []

        from tests.mock_helpers import make_mock_orchestrator

        items = [_make_licitacao(f"PNCP-SP-{i}", "SP") for i in range(10)]
        mock_orch = make_mock_orchestrator(items)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", _fake_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _fake_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _fake_create_excel)

        payload = {
            "ufs": target_ufs,
            "data_inicial": "2026-02-24",
            "data_final": "2026-03-02",
        }

        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200
        job_data = resp.json()
        assert job_data["status"] == "queued"
        job_id = job_data["job_id"]

        deadline = time.monotonic() + POLL_TIMEOUT
        while time.monotonic() < deadline:
            status_resp = client.get(f"/buscar/{job_id}/status")
            assert status_resp.status_code == 200
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
            raise TimeoutError(f"Job {job_id} did not complete within {POLL_TIMEOUT}s")

        assert current_status == "completed"
        assert data["progress"]["phase"] == "done"
        assert data["progress"]["ufs_total"] == num_ufs
        assert data["elapsed_seconds"] >= 0.0

        from datetime import datetime

        try:
            datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            pytest.fail(f"created_at is not valid ISO 8601: {data['created_at']} — {exc}")

        assert "done" in observed_phases

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_progress_ufs_total_matches_single_uf(self, client, monkeypatch, run_sync):
        from tests.mock_helpers import make_mock_orchestrator

        items = [_make_licitacao("PNCP-SP-0", "SP")]
        mock_orch = make_mock_orchestrator(items)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", _fake_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _fake_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _fake_create_excel)

        payload = {"ufs": ["SP"], "data_inicial": "2026-02-24", "data_final": "2026-03-02"}
        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final = _poll_until_done(client, job_id)
        assert final["status"] == "completed"
        assert final["progress"]["ufs_total"] == 1

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_progress_ufs_total_matches_all_27_ufs(self, client, monkeypatch, run_sync):
        from tests.mock_helpers import make_mock_orchestrator

        items = [_make_licitacao(f"PNCP-SP-{i}", "SP") for i in range(5)]
        mock_orch = make_mock_orchestrator(items)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", _fake_filter_batch)
        monkeypatch.setattr("main.gerar_resumo", _fake_gerar_resumo)
        monkeypatch.setattr("main.create_excel", _fake_create_excel)

        payload = {"ufs": ALL_UFS, "data_inicial": "2026-02-24", "data_final": "2026-03-02"}
        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final = _poll_until_done(client, job_id)
        assert final["status"] == "completed"
        assert final["progress"]["ufs_total"] == len(ALL_UFS)

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_progress_phase_done_on_empty_results(self, client, monkeypatch, run_sync):
        from tests.mock_helpers import make_mock_orchestrator

        items = [_make_licitacao("PNCP-SP-0", "SP")]
        mock_orch = make_mock_orchestrator(items)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr(
            "main.filter_batch",
            lambda bids, **kwargs: (
                [],
                {
                    "total": len(bids),
                    "aprovadas": 0,
                    "rejeitadas_uf": 0,
                    "rejeitadas_valor": 0,
                    "rejeitadas_keyword": len(bids),
                    "rejeitadas_prazo": 0,
                    "rejeitadas_outros": 0,
                },
            ),
        )

        payload = {"ufs": ["SP"], "data_inicial": "2026-02-24", "data_final": "2026-03-02"}
        resp = client.post("/buscar", json=payload)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final = _poll_until_done(client, job_id)
        assert final["status"] == "completed"
        assert final["progress"]["phase"] == "done"

        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200
        result = result_resp.json()
        assert result["total_filtrado"] == 0

        app.dependency_overrides.pop(get_orchestrator, None)
