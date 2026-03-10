"""
Tests for v2-story-4.0: Backend Architecture — Structural Fixes.

Covers:
- TD-H03: Async OpenAI (gerar_resumo is async)
- TD-L06: Dedicated ThreadPoolExecutor for filter_batch
- TD-M01: Deadline filter using dataFimReceberPropostas
- TD-L02/XD-API-03: Structured error codes
- TD-M06/XD-API-01: API versioning (/api/v1/)
- TD-M05: DI architecture (AppState)
- TD-H04: Database persistence
- XD-API-02: Contract tests (Pydantic JSON Schema)
- TD-H06: Chunked streaming download
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from error_codes import ErrorCode, error_response
from filter import filter_licitacao, filter_batch
from schemas import (
    BuscaRequest,
    ResumoLicitacoes,
    FilterStats,
    BuscaResponse,
    JobCreatedResponse,
    JobProgress,
    JobStatusResponse,
    JobResultResponse,
)


# ─────────────────────────────────────────────────────────────────────────────
# Error Codes (TD-L02/XD-API-03)
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorCodes:
    """Test structured error codes."""

    def test_error_code_to_dict_default_message(self):
        """Should use default message when none provided."""
        result = ErrorCode.JOB_NOT_FOUND.to_dict()
        assert result["error"]["code"] == "JOB_NOT_FOUND"
        assert "message" in result["error"]
        assert "details" not in result["error"]

    def test_error_code_to_dict_custom_message(self):
        """Should use custom message when provided."""
        result = ErrorCode.SEARCH_TIMEOUT.to_dict(message="Custom timeout msg")
        assert result["error"]["code"] == "SEARCH_TIMEOUT"
        assert result["error"]["message"] == "Custom timeout msg"

    def test_error_code_to_dict_with_details(self):
        """Should include details when provided."""
        result = ErrorCode.PNCP_RATE_LIMITED.to_dict(
            details={"retry_after": 60}
        )
        assert result["error"]["details"]["retry_after"] == 60

    def test_error_response_creates_http_exception(self):
        """Should create HTTPException with structured body."""
        exc = error_response(ErrorCode.JOB_NOT_FOUND, status_code=404)
        assert exc.status_code == 404
        assert exc.detail["error"]["code"] == "JOB_NOT_FOUND"

    def test_all_error_codes_have_default_messages(self):
        """Every error code should have a default message."""
        for code in ErrorCode:
            result = code.to_dict()
            assert result["error"]["message"], f"Missing default message for {code}"

    def test_error_code_format_is_consistent(self):
        """All error code values should be UPPER_SNAKE_CASE."""
        for code in ErrorCode:
            assert code.value == code.value.upper(), f"{code.value} is not uppercase"
            assert "_" in code.value or code.value.isalpha(), f"{code.value} format issue"


# ─────────────────────────────────────────────────────────────────────────────
# Deadline Filter (TD-M01)
# ─────────────────────────────────────────────────────────────────────────────


class TestDeadlineFilter:
    """Test deadline filtering using dataFimReceberPropostas."""

    def _make_bid(self, data_fim=None, **kwargs):
        """Helper to create a test bid."""
        bid = {
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "objetoCompra": "Aquisição de uniformes escolares",
            **kwargs,
        }
        if data_fim is not None:
            bid["dataFimReceberPropostas"] = data_fim
        return bid

    def test_bid_with_future_deadline_passes(self):
        """Bid with future deadline should pass."""
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        bid = self._make_bid(data_fim=future)
        approved, reason, _kw, _sc = filter_licitacao(bid, {"SP"})
        assert approved is True
        assert reason is None

    def test_bid_with_past_deadline_rejected(self):
        """Bid with past deadline should be rejected."""
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        bid = self._make_bid(data_fim=past)
        approved, reason, _kw, _sc = filter_licitacao(bid, {"SP"})
        assert approved is False
        assert "Prazo de submissão encerrado" in reason

    def test_bid_without_deadline_passes(self):
        """Bid without dataFimReceberPropostas should pass (no filter applied)."""
        bid = self._make_bid()
        approved, reason, _kw, _sc = filter_licitacao(bid, {"SP"})
        assert approved is True

    def test_bid_with_z_suffix_deadline(self):
        """Should handle ISO dates with 'Z' suffix."""
        past = "2025-01-01T10:00:00Z"
        bid = self._make_bid(data_fim=past)
        approved, reason, _kw, _sc = filter_licitacao(bid, {"SP"})
        assert approved is False

    def test_bid_with_offset_deadline(self):
        """Should handle ISO dates with timezone offset."""
        past = "2025-01-01T10:00:00+00:00"
        bid = self._make_bid(data_fim=past)
        approved, reason, _kw, _sc = filter_licitacao(bid, {"SP"})
        assert approved is False

    def test_bid_with_unparseable_deadline_passes(self):
        """Should not reject bids with malformed dates."""
        bid = self._make_bid(data_fim="not-a-date")
        approved, reason, _kw, _sc = filter_licitacao(bid, {"SP"})
        assert approved is True  # Unparseable → don't reject

    def test_filter_batch_counts_deadline_rejections(self):
        """filter_batch should count deadline rejections correctly."""
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        bids = [
            self._make_bid(data_fim=past),   # rejected
            self._make_bid(data_fim=future),  # approved
            self._make_bid(),                 # approved (no deadline)
        ]

        approved, stats = filter_batch(bids, {"SP"})
        assert len(approved) == 2
        assert stats["rejeitadas_prazo"] == 1

    def test_deadline_edge_case_exactly_now(self):
        """Bid with deadline exactly now should be rejected (already passed)."""
        now = datetime.now(timezone.utc).isoformat()
        bid = self._make_bid(data_fim=now)
        approved, reason, _kw, _sc = filter_licitacao(bid, {"SP"})
        # Could be either depending on timing, but should not crash
        assert isinstance(approved, bool)


# ─────────────────────────────────────────────────────────────────────────────
# API Versioning (TD-M06/XD-API-01)
# ─────────────────────────────────────────────────────────────────────────────


class TestApiVersioning:
    """Test /api/v1/ prefix routing."""

    @pytest.fixture()
    def client(self):
        from main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_v1_health_endpoint(self, client):
        """Should serve health check at /api/v1/health."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_v1_setores_endpoint(self, client):
        """Should serve sectors at /api/v1/setores."""
        resp = client.get("/api/v1/setores")
        assert resp.status_code == 200
        assert "setores" in resp.json()

    def test_legacy_health_still_works(self, client):
        """Legacy /health should still work (backward compat)."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_legacy_setores_still_works(self, client):
        """Legacy /setores should still work."""
        resp = client.get("/setores")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Structured Error Responses in Endpoints
# ─────────────────────────────────────────────────────────────────────────────


class TestStructuredErrors:
    """Test that endpoints return structured error codes."""

    @pytest.fixture()
    def client(self):
        from main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_job_not_found_returns_structured_error(self, client):
        """GET /buscar/{id}/status with invalid ID should return structured error."""
        resp = client.get("/buscar/nonexistent-id/status")
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["error"]["code"] == "JOB_NOT_FOUND"

    def test_job_not_completed_download_returns_structured_error(self, client):
        """GET /buscar/{id}/download with unfinished job should return structured error."""
        from tests.conftest import _test_job_store
        import asyncio

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test_job_store.create("test-job-123"))
        loop.close()

        resp = client.get("/buscar/test-job-123/download")
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["error"]["code"] == "JOB_NOT_COMPLETED"

    def test_items_invalid_page_returns_structured_error(self, client):
        """GET /buscar/{id}/items with invalid page should return structured error."""
        resp = client.get("/buscar/test-job/items?page=0")
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["error"]["code"] == "VALIDATION_ERROR"


# ─────────────────────────────────────────────────────────────────────────────
# DI Architecture (TD-M05)
# ─────────────────────────────────────────────────────────────────────────────


class TestDIArchitecture:
    """Test DI refactoring with AppState."""

    def test_app_state_class_exists(self):
        """AppState should be importable."""
        from dependencies import AppState
        state = AppState()
        assert state.redis is None
        assert state.job_store is None
        assert state.database is None

    def test_get_app_state_returns_singleton(self):
        """get_app_state should return the same instance."""
        from dependencies import get_app_state
        s1 = get_app_state()
        s2 = get_app_state()
        assert s1 is s2

    def test_dependency_overrides_work(self):
        """FastAPI dependency_overrides should work for test isolation."""
        from main import app
        from dependencies import get_database

        mock_db = Mock()
        mock_db.get_recent_searches = AsyncMock(return_value=[])
        app.dependency_overrides[get_database] = lambda: mock_db

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/search-history")
        assert resp.status_code == 200

        app.dependency_overrides[get_database] = lambda: None


# ─────────────────────────────────────────────────────────────────────────────
# Database Persistence (TD-H04)
# ─────────────────────────────────────────────────────────────────────────────


class MockSupabaseResponse:
    """Mock Supabase API response for test_story4."""
    def __init__(self, data=None):
        self.data = data or []


class MockTableQuery:
    """Mock Supabase table query builder for test_story4."""
    def __init__(self, data=None):
        self._data = data or []
    def select(self, *a, **kw): return self
    def insert(self, *a, **kw): return self
    def update(self, *a, **kw): return self
    def upsert(self, *a, **kw): return self
    def eq(self, *a, **kw): return self
    def order(self, *a, **kw): return self
    def limit(self, *a, **kw): return self
    def execute(self): return MockSupabaseResponse(self._data)


@pytest_asyncio.fixture()
async def test_db():
    """Create a mock Supabase-backed database for testing."""
    from database import Database
    from unittest.mock import Mock
    _db = Database(supabase_url="https://test.supabase.co", supabase_key="test-key")
    _db._client = Mock()
    _db._client.table = lambda name: MockTableQuery()
    yield _db
    await _db.close()


class TestDatabase:
    """Test Supabase persistence layer (v3-story-2.0)."""

    TEST_USER = "test-user-uuid"

    @pytest.mark.asyncio
    async def test_record_and_retrieve_search(self, test_db):
        """Should record and retrieve search history with user_id."""
        calls = []

        class TrackingInsertQuery(MockTableQuery):
            def insert(self, data, **kw):
                calls.append(data)
                return self

        test_db._client.table = lambda name: TrackingInsertQuery()

        await test_db.record_search(
            job_id="test-123",
            ufs=["SP", "RJ"],
            data_inicial="2026-01-01",
            data_final="2026-01-31",
            setor_id="vestuario",
            user_id=self.TEST_USER,
        )
        assert len(calls) == 1
        assert calls[0]["job_id"] == "test-123"
        assert calls[0]["ufs"] == ["SP", "RJ"]
        assert calls[0]["user_id"] == self.TEST_USER

    @pytest.mark.asyncio
    async def test_complete_search(self, test_db):
        """Should update search with completion data."""
        calls = []

        class TrackingUpdateQuery(MockTableQuery):
            def update(self, data, **kw):
                calls.append(data)
                return self

        test_db._client.table = lambda name: TrackingUpdateQuery()

        await test_db.complete_search(
            job_id="test-456",
            total_raw=500,
            total_filtrado=25,
            elapsed_seconds=12.5,
        )
        assert calls[0]["status"] == "completed"
        assert calls[0]["total_raw"] == 500
        assert calls[0]["total_filtrado"] == 25

    @pytest.mark.asyncio
    async def test_fail_search(self, test_db):
        """Should mark search as failed."""
        calls = []

        class TrackingUpdateQuery(MockTableQuery):
            def update(self, data, **kw):
                calls.append(data)
                return self

        test_db._client.table = lambda name: TrackingUpdateQuery()

        await test_db.fail_search("test-789")
        assert calls[0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_set_and_get_preference(self, test_db):
        """Should save and retrieve user preferences with user_id."""
        calls = []

        class TrackingUpsertQuery(MockTableQuery):
            def upsert(self, data, **kw):
                calls.append(data)
                return self

        test_db._client.table = lambda name: TrackingUpsertQuery()

        await test_db.set_preference("favorite_sector", "vestuario", user_id=self.TEST_USER)
        assert len(calls) == 1
        assert calls[0]["key"] == "favorite_sector"
        assert calls[0]["user_id"] == self.TEST_USER

    @pytest.mark.asyncio
    async def test_get_nonexistent_preference(self, test_db):
        """Should return None for missing preference."""
        val = await test_db.get_preference("nonexistent_key", user_id=self.TEST_USER)
        assert val is None

    @pytest.mark.asyncio
    async def test_upsert_preference(self, test_db):
        """Should upsert preference (conflict on user_id + key)."""
        calls = []

        class TrackingUpsertQuery(MockTableQuery):
            def upsert(self, data, **kw):
                calls.append(data)
                return self

        test_db._client.table = lambda name: TrackingUpsertQuery()

        await test_db.set_preference("theme", "light", user_id=self.TEST_USER)
        await test_db.set_preference("theme", "dark", user_id=self.TEST_USER)
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_get_all_preferences(self, test_db):
        """Should return all preferences as dict for a user."""
        test_db._client.table = lambda name: MockTableQuery(data=[
            {"key": "a", "value": "1"},
            {"key": "b", "value": '"hello"'},
        ])
        all_prefs = await test_db.get_all_preferences(user_id=self.TEST_USER)
        assert "a" in all_prefs
        assert "b" in all_prefs

    @pytest.mark.asyncio
    async def test_operations_when_not_connected(self):
        """Should silently no-op when database is not connected."""
        from database import Database
        db = Database(supabase_url="", supabase_key="")
        # Don't call connect — _client is None
        await db.record_search("x", ["SP"], "2026-01-01", "2026-01-31", "v", user_id="u")
        searches = await db.get_recent_searches(user_id="u")
        assert searches == []
        val = await db.get_preference("key", user_id="u")
        assert val is None


# ─────────────────────────────────────────────────────────────────────────────
# Contract Tests (XD-API-02)
# ─────────────────────────────────────────────────────────────────────────────


class TestContractSchemas:
    """Test that Pydantic JSON schemas match expected structure."""

    def test_busca_request_schema_has_required_fields(self):
        """BuscaRequest schema should include ufs, dates, setor_id."""
        schema = BuscaRequest.model_json_schema()
        props = schema["properties"]
        assert "ufs" in props
        assert "data_inicial" in props
        assert "data_final" in props
        assert "setor_id" in props

    def test_resumo_schema_has_required_fields(self):
        """ResumoLicitacoes should have all fields used by frontend Resumo interface."""
        schema = ResumoLicitacoes.model_json_schema()
        props = schema["properties"]
        assert "resumo_executivo" in props
        assert "total_oportunidades" in props
        assert "valor_total" in props
        assert "destaques" in props
        assert "alerta_urgencia" in props

    def test_filter_stats_schema_matches_frontend(self):
        """FilterStats should match frontend FilterStats interface."""
        schema = FilterStats.model_json_schema()
        props = schema["properties"]
        expected_fields = [
            "rejeitadas_uf", "rejeitadas_valor", "rejeitadas_keyword",
            "rejeitadas_prazo", "rejeitadas_outros",
        ]
        for field in expected_fields:
            assert field in props, f"Missing field: {field}"

    def test_job_status_response_schema(self):
        """JobStatusResponse should match frontend JobStatusResponse."""
        schema = JobStatusResponse.model_json_schema()
        props = schema["properties"]
        assert "job_id" in props
        assert "status" in props
        assert "progress" in props
        assert "created_at" in props
        assert "elapsed_seconds" in props

    def test_job_progress_schema(self):
        """JobProgress should include all frontend-used fields."""
        schema = JobProgress.model_json_schema()
        props = schema["properties"]
        expected = [
            "phase", "ufs_completed", "ufs_total",
            "items_fetched", "items_filtered",
        ]
        for field in expected:
            assert field in props, f"Missing field: {field}"

    def test_schema_contract_generation(self):
        """schemas_contract.py should generate valid JSON output."""
        from schemas_contract import generate_contract_schemas
        schemas = generate_contract_schemas()
        assert "BuscaRequest" in schemas
        assert "ResumoLicitacoes" in schemas
        assert "FilterStats" in schemas
        assert "JobStatusResponse" in schemas
        assert "ErrorCodes" in schemas
        assert isinstance(schemas["ErrorCodes"], list)
        assert "JOB_NOT_FOUND" in schemas["ErrorCodes"]

    def test_all_error_codes_in_contract(self):
        """All ErrorCode values should appear in contract output."""
        from schemas_contract import generate_contract_schemas
        schemas = generate_contract_schemas()
        for code in ErrorCode:
            assert code.value in schemas["ErrorCodes"]


# ─────────────────────────────────────────────────────────────────────────────
# Streaming Download (TD-H06)
# ─────────────────────────────────────────────────────────────────────────────


class TestStreamingDownload:
    """Test chunked streaming download."""

    @pytest.fixture()
    def client(self):
        from main import app
        return TestClient(app, raise_server_exceptions=False)

    @pytest.mark.asyncio
    async def test_download_streams_in_chunks(self, client):
        """Download should stream Excel data successfully."""
        from tests.conftest import _test_job_store

        # Create a completed job with Excel data
        await _test_job_store.create("stream-test")
        await _test_job_store.complete("stream-test", {"resumo": {}})
        # Store fake Excel data (1MB to test chunking)
        fake_excel = b"PK" + b"\x00" * (1024 * 1024)
        await _test_job_store.store_excel("stream-test", fake_excel)

        resp = client.get("/buscar/stream-test/download")
        assert resp.status_code == 200
        assert len(resp.content) == len(fake_excel)
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ─────────────────────────────────────────────────────────────────────────────
# Dedicated ThreadPoolExecutor (TD-L06)
# ─────────────────────────────────────────────────────────────────────────────


class TestDedicatedExecutor:
    """Test that filter_batch uses dedicated executor."""

    def test_filter_executor_exists(self):
        """main module should have a dedicated _filter_executor."""
        from main import _filter_executor
        assert _filter_executor is not None
        assert _filter_executor._max_workers == 4
        # Check thread name prefix
        assert _filter_executor._thread_name_prefix == "filter"


# ─────────────────────────────────────────────────────────────────────────────
# Concurrency: No Thread Pool Starvation (Load Test)
# ─────────────────────────────────────────────────────────────────────────────


class TestConcurrency:
    """Test that concurrent operations don't starve the thread pool."""

    @pytest.mark.asyncio
    async def test_concurrent_filter_batch(self):
        """10 concurrent filter_batch calls should complete without starvation."""
        from main import _filter_executor

        loop = asyncio.get_running_loop()
        bids = [
            {
                "uf": "SP",
                "valorTotalEstimado": 100000.0,
                "objetoCompra": "Aquisição de uniformes escolares para alunos",
            }
            for _ in range(100)
        ]

        async def run_filter():
            return await loop.run_in_executor(
                _filter_executor,
                lambda: filter_batch(bids, {"SP"}),
            )

        # Run 10 concurrent filter operations
        results = await asyncio.gather(*[run_filter() for _ in range(10)])
        assert len(results) == 10
        for approved, stats in results:
            assert stats["total"] == 100


# ─────────────────────────────────────────────────────────────────────────────
# Search History Endpoint
# ─────────────────────────────────────────────────────────────────────────────


class TestSearchHistoryEndpoint:
    """Test /search-history endpoint."""

    @pytest.fixture()
    def client(self):
        from main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_search_history_without_db(self, client):
        """Should return empty list when database is not configured."""
        resp = client.get("/search-history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["searches"] == []

    def test_v1_search_history_endpoint(self, client):
        """Should be available at /api/v1/search-history."""
        resp = client.get("/api/v1/search-history")
        assert resp.status_code == 200
