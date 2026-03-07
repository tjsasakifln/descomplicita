"""Shared test fixtures for the Descomplicita backend test suite."""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, Mock

from job_store import JobStore
from sources.orchestrator import OrchestratorResult, SourceStats
from sources.base import NormalizedRecord


# Module-level job store for tests (replaces the DI-provided one)
_test_job_store = JobStore()


def get_test_job_store():
    """Return the test job store instance."""
    return _test_job_store


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset slowapi rate limiter state between tests."""
    from main import limiter
    yield
    try:
        limiter.reset()
    except Exception:
        if hasattr(limiter, "_storage") and hasattr(limiter._storage, "storage"):
            limiter._storage.storage.clear()


@pytest.fixture(autouse=True)
def _disable_auth_for_tests(monkeypatch):
    """Ensure API_KEY is not set during tests (auth bypassed)."""
    monkeypatch.delenv("API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _override_dependencies():
    """Override DI dependencies for testing (no Redis, in-memory stores)."""
    from main import app
    from dependencies import get_job_store, get_orchestrator, get_pncp_source, get_redis, get_redis_cache

    # Use test job store
    app.dependency_overrides[get_job_store] = get_test_job_store
    app.dependency_overrides[get_redis] = lambda: None
    app.dependency_overrides[get_redis_cache] = lambda: None

    yield

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_job_store():
    """Clear the test job store before and after every test."""
    _test_job_store._jobs.clear()
    yield
    _test_job_store._jobs.clear()


@pytest.fixture()
def run_sync(monkeypatch):
    """
    Make background search jobs execute synchronously inside the TestClient.

    Patches run_search_job to avoid thread pool deadlocks with Starlette's
    TestClient, and patches asyncio.create_task to run the background
    coroutine inline.

    Updated for the new 4-param signature:
        run_search_job(job_id, request, job_store, orchestrator)
    """
    import main as main_module

    original_run_search_job = main_module.run_search_job

    async def _inline_run_search_job(job_id, request, job_store, orchestrator):
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
            await original_run_search_job(job_id, request, job_store, orchestrator)
        finally:
            loop.run_in_executor = original_rie

    monkeypatch.setattr("main.run_search_job", _inline_run_search_job)

    original_create_task = asyncio.create_task

    def _inline_create_task(coro, *args, **kwargs):
        coro_name = getattr(coro, "__qualname__", "") or getattr(coro, "__name__", "")
        if "run_search_job" in coro_name or "_inline" in coro_name:
            loop = asyncio.get_event_loop()
            return loop.create_task(coro)
        return original_create_task(coro, *args, **kwargs)

    monkeypatch.setattr("main.asyncio.create_task", _inline_create_task)


def make_mock_orchestrator(raw_records=None, error=None):
    """Create a mock MultiSourceOrchestrator from raw legacy dicts."""
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
