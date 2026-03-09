"""
Tests for concurrent search behavior — SP-001.5.

Covers:
- Multiple simultaneous search jobs completing without error
- HTTP 429 when the job store is at capacity (max 10 active jobs)
- No state leakage across consecutive identical searches
- Job lifecycle transitions (queued -> running -> completed)
- Expired job cleanup via cleanup_expired()
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
from main import app
from dependencies import get_orchestrator
from tests.conftest import get_test_job_store


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def make_pncp_response(uf: str = "SP", n_items: int = 5) -> dict:
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
    return TestClient(app)


@pytest.fixture
def mock_pncp_client(monkeypatch):
    """Replace orchestrator with a mock that returns canned data."""
    from tests.mock_helpers import make_mock_orchestrator
    records = make_pncp_response("SP")["data"]
    mock_orch = make_mock_orchestrator(records)
    app.dependency_overrides[get_orchestrator] = lambda: mock_orch
    yield mock_orch
    app.dependency_overrides.pop(get_orchestrator, None)


@pytest.fixture
def mock_pipeline(monkeypatch):
    """Mock filter_batch, gerar_resumo, and create_excel."""
    from schemas import ResumoLicitacoes

    def _filter(bids, **kwargs):
        return list(bids), {}

    async def _resumo(bids, **kwargs):
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


# ---------------------------------------------------------------------------
# TestConcurrentSearches
# ---------------------------------------------------------------------------


class TestConcurrentSearches:

    def test_5_simultaneous_searches_complete(
        self, client, mock_pncp_client, mock_pipeline, run_sync
    ):
        ufs_list = ["SP", "RJ", "MG", "RS", "PR"]
        requests_data = [
            {**VALID_REQUEST, "ufs": [uf]}
            for uf in ufs_list
        ]

        job_ids = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(client.post, "/buscar", json=req): req
                for req in requests_data
            }
            for future in as_completed(futures):
                resp = future.result()
                assert resp.status_code == 200
                job_ids.append(resp.json()["job_id"])

        assert len(job_ids) == 5

        for job_id in job_ids:
            final = _wait_for_job(client, job_id, timeout=15.0)
            assert final is not None
            assert final["status"] == "completed"

    def test_job_limit_returns_429(self, client):
        _job_store = get_test_job_store()
        for i in range(_job_store.max_jobs):
            fake_job = SearchJob(job_id=f"fake-running-{i}", status="running")
            _job_store._jobs[f"fake-running-{i}"] = fake_job

        assert _job_store.active_count == 10
        assert _job_store.is_full

        response = client.post("/buscar", json=VALID_REQUEST)
        assert response.status_code == 429
        data = response.json()
        assert "detail" in data

    def test_no_race_condition_10_runs(
        self, client, mock_pncp_client, mock_pipeline, run_sync
    ):
        for run in range(10):
            resp = client.post("/buscar", json=VALID_REQUEST)
            assert resp.status_code == 200
            job_id = resp.json()["job_id"]
            final = _wait_for_job(client, job_id, timeout=15.0)
            assert final is not None
            assert final["status"] == "completed"


# ---------------------------------------------------------------------------
# TestJobLifecycle
# ---------------------------------------------------------------------------


class TestJobLifecycle:

    def test_job_transitions_queued_to_completed(
        self, client, mock_pncp_client, mock_pipeline, run_sync
    ):
        resp = client.post("/buscar", json=VALID_REQUEST)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        job_id = data["job_id"]

        final = _wait_for_job(client, job_id, timeout=15.0)
        assert final is not None
        assert final["status"] == "completed"

        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200
        result_data = result_resp.json()
        assert result_data["status"] == "completed"
        assert "resumo" in result_data

    def test_expired_jobs_cleaned_up(self, client):
        _job_store = get_test_job_store()
        job_id = f"expired-{uuid.uuid4()}"
        expired_job = SearchJob(
            job_id=job_id,
            status="completed",
            result={"test": True},
        )
        expired_job.created_at = time.time() - _job_store.ttl - 200
        expired_job.completed_at = time.time() - _job_store.ttl - 200
        _job_store._jobs[job_id] = expired_job

        assert job_id in _job_store._jobs
        removed = asyncio.run(_job_store.cleanup_expired())
        assert job_id not in _job_store._jobs
        assert removed >= 1

    def test_non_expired_job_not_cleaned_up(self, client):
        _job_store = get_test_job_store()
        job_id = f"fresh-{uuid.uuid4()}"
        fresh_job = SearchJob(
            job_id=job_id,
            status="completed",
            result={"test": True},
        )
        fresh_job.completed_at = time.time()
        _job_store._jobs[job_id] = fresh_job

        asyncio.run(_job_store.cleanup_expired())
        assert job_id in _job_store._jobs

    def test_active_job_count_decrements_after_completion(
        self, client, mock_pncp_client, mock_pipeline, run_sync
    ):
        resp = client.post("/buscar", json=VALID_REQUEST)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        final = _wait_for_job(client, job_id, timeout=15.0)
        assert final is not None
        assert final["status"] == "completed"

        _job_store = get_test_job_store()
        assert _job_store.active_count == 0
        assert not _job_store.is_full
