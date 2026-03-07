"""Shared test fixtures for the Descomplicita backend test suite."""

import os
import pytest
from unittest.mock import AsyncMock, Mock

from sources.orchestrator import OrchestratorResult, SourceStats
from sources.base import NormalizedRecord


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset slowapi rate limiter state between tests."""
    from main import limiter
    yield
    try:
        limiter.reset()
    except Exception:
        # reset() may not exist on all storage backends; clear manually
        if hasattr(limiter, "_storage") and hasattr(limiter._storage, "storage"):
            limiter._storage.storage.clear()


@pytest.fixture(autouse=True)
def _disable_auth_for_tests(monkeypatch):
    """Ensure API_KEY is not set during tests (auth bypassed)."""
    monkeypatch.delenv("API_KEY", raising=False)


def make_mock_orchestrator(raw_records=None, error=None):
    """Create a mock MultiSourceOrchestrator from raw legacy dicts.

    This bridges the old PNCPClient.fetch_all() test pattern to the new
    orchestrator-based flow. Converts raw dicts to NormalizedRecords so
    orchestrator.search_all() returns them properly, and downstream
    to_legacy_dict() re-produces the original dicts for filter_batch.

    Args:
        raw_records: List of raw dicts (like old PNCPClient responses).
                     Each will be wrapped in a NormalizedRecord.
        error: If set, search_all will raise this exception.

    Returns:
        A mock object compatible with MultiSourceOrchestrator.
    """
    mock_orch = Mock()
    mock_orch.enabled_sources = [Mock(source_name="pncp")]

    if error:
        mock_orch.search_all = AsyncMock(side_effect=error)
        return mock_orch

    records = []
    for i, raw in enumerate(raw_records or []):
        rec = NormalizedRecord(
            id=raw.get("codigoCompra", f"mock_{i}"),
            source="pncp",
            sources=["pncp"],
            numero_licitacao=raw.get("codigoCompra", ""),
            objeto=raw.get("objetoCompra", ""),
            orgao=raw.get("nomeOrgao", ""),
            cnpj_orgao=raw.get("cnpj", ""),
            uf=raw.get("uf", ""),
            municipio=raw.get("municipio", ""),
            valor_estimado=raw.get("valorTotalEstimado"),
            modalidade=raw.get("modalidade", ""),
            raw_data=dict(raw),
        )
        records.append(rec)

    orch_result = OrchestratorResult(
        records=records,
        source_stats={"pncp": SourceStats(
            total_fetched=len(records),
            after_dedup=len(records),
            elapsed_ms=100,
            status="success",
        )},
        dedup_removed=0,
        sources_used=["pncp"],
    )

    mock_orch.search_all = AsyncMock(return_value=orch_result)
    return mock_orch
