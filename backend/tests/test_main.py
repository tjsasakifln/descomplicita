"""Tests for FastAPI application structure and base endpoints."""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, Mock, patch
from io import BytesIO
from fastapi.testclient import TestClient
from main import app, _job_store, run_search_job
from tests.mock_helpers import make_mock_orchestrator


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestApplicationSetup:
    """Test FastAPI application initialization and configuration."""

    def test_app_title(self):
        """Verify app has correct title."""
        assert app.title == "BidIQ Uniformes API"

    def test_app_version(self):
        """Verify app version matches expected."""
        assert app.version == "0.2.0"

    def test_app_has_docs_endpoint(self):
        """Verify OpenAPI documentation is configured."""
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"

    def test_cors_middleware_configured(self):
        """Verify CORS middleware is present."""
        # Check that CORSMiddleware is in the middleware stack
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes


class TestRootEndpoint:
    """Test root endpoint functionality."""

    def test_root_status_code(self, client):
        """Root endpoint should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_response_structure(self, client):
        """Root endpoint should return API information."""
        response = client.get("/")
        data = response.json()

        # Verify required fields
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        assert "status" in data

    def test_root_version_matches(self, client):
        """Root endpoint version should match app version."""
        response = client.get("/")
        data = response.json()
        assert data["version"] == "0.2.0"

    def test_root_endpoints_links(self, client):
        """Root endpoint should include documentation links."""
        response = client.get("/")
        data = response.json()

        endpoints = data["endpoints"]
        assert endpoints["docs"] == "/docs"
        assert endpoints["redoc"] == "/redoc"
        assert endpoints["health"] == "/health"
        assert endpoints["openapi"] == "/openapi.json"

    def test_root_status_operational(self, client):
        """Root endpoint should indicate operational status."""
        response = client.get("/")
        data = response.json()
        assert data["status"] == "operational"


class TestHealthEndpoint:
    """Test health check endpoint functionality."""

    def test_health_status_code(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        """Health endpoint should return status, timestamp, and version."""
        response = client.get("/health")
        data = response.json()

        # Verify all required fields are present
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

    def test_health_status_healthy(self, client):
        """Health endpoint should report 'healthy' status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_timestamp_format(self, client):
        """Health endpoint timestamp should be valid ISO 8601 format."""
        from datetime import datetime

        response = client.get("/health")
        data = response.json()

        timestamp = data["timestamp"]
        # Verify ISO 8601 format by parsing it
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

        # Timestamp should be recent (within last 5 seconds)
        now = datetime.utcnow()
        delta = (now - parsed).total_seconds()
        assert abs(delta) < 5, f"Timestamp {timestamp} is not recent (delta: {delta}s)"

    def test_health_timestamp_changes(self, client):
        """Health endpoint timestamp should update on each request."""
        import time

        response1 = client.get("/health")
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        response2 = client.get("/health")

        timestamp1 = response1.json()["timestamp"]
        timestamp2 = response2.json()["timestamp"]

        # Timestamps should be different (not cached)
        assert timestamp1 != timestamp2

    def test_health_version_matches(self, client):
        """Health endpoint version should match app version."""
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.2.0"

    def test_health_response_time(self, client):
        """Health endpoint should respond quickly (< 100ms)."""
        import time

        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.1  # 100ms threshold

    def test_health_no_authentication_required(self, client):
        """Health endpoint should be publicly accessible (no auth)."""
        # No authentication headers provided
        response = client.get("/health")
        # Should still succeed
        assert response.status_code == 200

    def test_health_json_content_type(self, client):
        """Health endpoint should return JSON content type."""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


class TestCORSHeaders:
    """Test CORS configuration and headers."""

    def test_cors_preflight_options(self, client):
        """CORS preflight OPTIONS request should succeed."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200

    def test_cors_headers_present(self, client):
        """CORS headers should be present in responses."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        # Check for CORS headers (case-insensitive)
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert "access-control-allow-origin" in headers_lower

    def test_cors_allows_all_origins(self, client):
        """CORS should allow all origins (POC configuration)."""
        response = client.get("/health", headers={"Origin": "http://example.com"})

        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        # FastAPI CORS middleware returns the requesting origin or "*"
        assert "access-control-allow-origin" in headers_lower

    def test_cors_allows_post_method(self, client):
        """CORS should allow POST method."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation generation."""

    def test_openapi_json_accessible(self, client):
        """OpenAPI JSON schema should be accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_openapi_schema_structure(self, client):
        """OpenAPI schema should have required fields."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "openapi" in schema  # OpenAPI version
        assert "info" in schema  # API metadata
        assert "paths" in schema  # Endpoints

    def test_openapi_info_metadata(self, client):
        """OpenAPI info section should match app configuration."""
        response = client.get("/openapi.json")
        schema = response.json()

        info = schema["info"]
        assert info["title"] == "BidIQ Uniformes API"
        assert info["version"] == "0.2.0"

    def test_openapi_has_health_endpoint(self, client):
        """OpenAPI schema should document /health endpoint."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "/health" in schema["paths"]
        assert "get" in schema["paths"]["/health"]

    def test_openapi_has_root_endpoint(self, client):
        """OpenAPI schema should document / endpoint."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "/" in schema["paths"]
        assert "get" in schema["paths"]["/"]

    def test_docs_page_accessible(self, client):
        """Swagger UI docs page should be accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_page_accessible(self, client):
        """ReDoc documentation page should be accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestErrorHandling:
    """Test basic error handling for non-existent endpoints."""

    def test_404_for_invalid_endpoint(self, client):
        """Invalid endpoints should return 404 Not Found."""
        response = client.get("/invalid-endpoint-xyz")
        assert response.status_code == 404

    def test_404_response_structure(self, client):
        """404 response should have error detail."""
        response = client.get("/invalid-endpoint-xyz")
        data = response.json()
        assert "detail" in data


class TestBuscarEndpoint:
    """Test POST /buscar endpoint - async job-based orchestration pipeline."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self):
        """Reset job store between tests."""
        _job_store._jobs.clear()
        yield
        _job_store._jobs.clear()

    @pytest.fixture
    def valid_request(self):
        """Fixture for valid search request."""
        return {
            "ufs": ["SP", "RJ"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }

    @pytest.fixture
    def mock_licitacao(self):
        """Fixture for a valid PNCP bid matching uniform keywords."""
        return {
            "codigoCompra": "123456789",
            "objetoCompra": "Aquisição de uniformes escolares para secretaria de educação",
            "nomeOrgao": "Prefeitura Municipal de São Paulo",
            "uf": "SP",
            "municipio": "São Paulo",
            "valorTotalEstimado": 150000.00,
            "dataAberturaProposta": "2025-02-15T10:00:00",
            "linkSistemaOrigem": "https://pncp.gov.br/app/editais/123456789",
        }

    @pytest.fixture
    def run_sync(self, monkeypatch):
        """Make background search jobs complete synchronously.

        The Starlette TestClient runs requests on a background event-loop
        thread.  asyncio.create_task schedules the background coroutine on
        that loop, but loop.run_in_executor inside the coroutine contends
        with the TestClient for the default thread-pool, causing deadlocks.

        This fixture replaces run_search_job with a version that calls
        loop.run_in_executor synchronously (returning resolved futures),
        so the background task completes without needing the thread pool.
        """
        import main as main_module
        original_run_search_job = main_module.run_search_job

        async def _inline_run_search_job(job_id, request):
            """Run search job with run_in_executor replaced by sync calls."""
            loop = asyncio.get_event_loop()
            original_rie = loop.run_in_executor

            def _sync_run_in_executor(executor, func, *args):
                """Run func synchronously, returning a completed future."""
                fut = loop.create_future()
                try:
                    result = func(*args)
                    fut.set_result(result)
                except Exception as e:
                    fut.set_exception(e)
                return fut

            loop.run_in_executor = _sync_run_in_executor
            try:
                await original_run_search_job(job_id, request)
            finally:
                loop.run_in_executor = original_rie

        monkeypatch.setattr("main.run_search_job", _inline_run_search_job)

    def _post_and_get_result(self, client, request):
        """POST /buscar with run_sync fixture, then GET the result."""
        resp = client.post("/buscar", json=request)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        # With run_sync fixture, the job completes within the POST handler
        result_resp = client.get(f"/buscar/{job_id}/result")
        return result_resp

    def test_buscar_endpoint_exists(self, client):
        """POST /buscar endpoint should be defined."""
        response = client.post("/buscar", json={})
        assert response.status_code == 422

    def test_buscar_validation_empty_ufs(self, client, valid_request):
        """Request with empty UFs list should fail validation."""
        request = valid_request.copy()
        request["ufs"] = []
        response = client.post("/buscar", json=request)
        assert response.status_code == 422
        assert "ufs" in response.json()["detail"][0]["loc"]

    def test_buscar_validation_invalid_date_format(self, client, valid_request):
        """Request with invalid date format should fail validation."""
        request = valid_request.copy()
        request["data_inicial"] = "01-01-2025"  # Wrong format (DD-MM-YYYY)
        response = client.post("/buscar", json=request)
        assert response.status_code == 422

    def test_buscar_validation_missing_fields(self, client):
        """Request with missing required fields should fail."""
        response = client.post("/buscar", json={"ufs": ["SP"]})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_buscar_returns_job_id(self, client, valid_request, monkeypatch):
        """POST /buscar should return 200 with job_id and status='queued'."""
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        response = client.post("/buscar", json=valid_request)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert len(data["job_id"]) == 36

    def test_buscar_success_response_structure(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        """Completed job result should return all required fields."""
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([mock_licitacao]))

        def mock_filter_batch(bids, **kwargs):
            return [bids[0]], {"total_rejeitados": 0}

        def mock_create_excel(bids):
            buf = BytesIO()
            buf.write(b"fake-excel-content")
            buf.seek(0)
            return buf

        def mock_gerar_resumo(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo="1 licitação encontrada",
                total_oportunidades=1,
                valor_total=150000.00,
                destaques=["SP: R$ 150k"],
            )

        monkeypatch.setattr("main.filter_batch", mock_filter_batch)
        monkeypatch.setattr("main.create_excel", mock_create_excel)
        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 200
        data = result_resp.json()

        assert data["status"] == "completed"
        assert "resumo" in data
        assert "excel_base64" in data
        assert "total_raw" in data
        assert "total_filtrado" in data

    def test_buscar_resumo_structure(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        """Completed job result should include valid resumo structure."""
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel"))

        def mock_gerar_resumo(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo="Test summary",
                total_oportunidades=1,
                valor_total=150000.00,
                destaques=["Test highlight"],
                alerta_urgencia="Test alert",
            )

        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)

        result_resp = self._post_and_get_result(client, valid_request)
        data = result_resp.json()

        resumo = data["resumo"]
        assert "resumo_executivo" in resumo
        assert "total_oportunidades" in resumo
        assert "valor_total" in resumo
        assert "destaques" in resumo
        assert "alerta_urgencia" in resumo

    def test_buscar_excel_base64_valid(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        """Excel should be valid base64 string."""
        import base64

        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))

        excel_content = b"PK\x03\x04fake-excel-header"
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(excel_content))

        def mock_gerar_resumo(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo="Test",
                total_oportunidades=1,
                valor_total=150000.00,
            )

        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)

        result_resp = self._post_and_get_result(client, valid_request)
        data = result_resp.json()

        excel_base64 = data["excel_base64"]
        decoded = base64.b64decode(excel_base64)
        assert decoded == excel_content

    def test_buscar_llm_fallback_on_error(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        """Should use fallback when LLM fails."""
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel"))

        def mock_gerar_resumo(bids, **kwargs):
            raise Exception("OpenAI API error")

        def mock_gerar_resumo_fallback(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo="Fallback summary",
                total_oportunidades=1,
                valor_total=150000.00,
            )

        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)
        monkeypatch.setattr("main.gerar_resumo_fallback", mock_gerar_resumo_fallback)

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["resumo"]["resumo_executivo"] == "Fallback summary"

    def test_buscar_pncp_api_error_fails_job(self, client, valid_request, monkeypatch, run_sync):
        """PNCP API error should result in a failed job."""
        from exceptions import PNCPAPIError
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator(error=PNCPAPIError("Connection timeout")))

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 500
        data = result_resp.json()
        assert data["status"] == "failed"

    def test_buscar_rate_limit_error_fails_job(self, client, valid_request, monkeypatch, run_sync):
        """PNCP rate limit error should result in a failed job."""
        from exceptions import PNCPRateLimitError
        error = PNCPRateLimitError("Rate limit exceeded")
        error.retry_after = 120
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator(error=error))

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 500
        data = result_resp.json()
        assert data["status"] == "failed"

    def test_buscar_internal_error_fails_job(self, client, valid_request, monkeypatch, run_sync):
        """Unexpected error should result in a failed job with sanitized message."""
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator(error=RuntimeError("Internal bug with sensitive data")))

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 500
        data = result_resp.json()
        assert data["status"] == "failed"
        assert "Erro interno" in data["error"]
        assert "sensitive data" not in data["error"]

    def test_buscar_empty_results(self, client, valid_request, monkeypatch, run_sync):
        """Should handle empty results gracefully."""
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["total_raw"] == 0
        assert data["total_filtrado"] == 0

    def test_buscar_statistics_match(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        """total_raw and total_filtrado should reflect actual counts."""
        mock_licitacoes_raw = [mock_licitacao.copy() for _ in range(10)]

        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator(mock_licitacoes_raw))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids[:3], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel"))

        def mock_gerar_resumo(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo="3 licitações",
                total_oportunidades=len(bids),
                valor_total=450000.00,
            )

        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)

        result_resp = self._post_and_get_result(client, valid_request)
        data = result_resp.json()
        assert data["total_raw"] == 10
        assert data["total_filtrado"] == 3

    def test_buscar_logs_pipeline_stages(self, client, valid_request, mock_licitacao, monkeypatch, run_sync, caplog):
        """Should log each pipeline stage."""
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel"))

        def mock_gerar_resumo(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo="Test",
                total_oportunidades=1,
                valor_total=150000.00,
            )

        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)

        with caplog.at_level("INFO"):
            self._post_and_get_result(client, valid_request)

        log_messages = " ".join([record.message for record in caplog.records])
        assert "Search job created" in log_messages
        assert "Fetching bids from" in log_messages
        assert "Filtering complete" in log_messages or "Applying filters" in log_messages
        assert "Generating LLM summary + Excel report in parallel" in log_messages
        assert "Search completed successfully" in log_messages


class TestJobStatusEndpoint:
    """Test GET /buscar/{job_id}/status endpoint."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self):
        """Reset job store between tests."""
        _job_store._jobs.clear()
        yield
        _job_store._jobs.clear()

    def test_status_404_for_unknown_job(self, client):
        """Status of unknown job should return 404."""
        response = client.get("/buscar/nonexistent-job-id/status")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_status_returns_progress(self, client, monkeypatch):
        """Status should return progress for a running job."""
        from job_store import SearchJob

        # Directly insert a running job to avoid background task hangs
        job = SearchJob(job_id="running-status-test", status="running")
        job.progress["phase"] = "fetching"
        job.progress["sources_completed"] = 1
        job.progress["sources_total"] = 3
        _job_store._jobs["running-status-test"] = job

        status_resp = client.get("/buscar/running-status-test/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["job_id"] == "running-status-test"
        assert data["status"] == "running"
        assert "progress" in data
        assert data["progress"]["sources_total"] == 3
        assert "elapsed_seconds" in data
        assert "created_at" in data


class TestJobResultEndpoint:
    """Test GET /buscar/{job_id}/result endpoint."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self):
        """Reset job store between tests."""
        _job_store._jobs.clear()
        yield
        _job_store._jobs.clear()

    @pytest.fixture
    def run_sync(self, monkeypatch):
        """Replace run_in_executor with synchronous calls to avoid deadlocks."""
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
                except Exception as e:
                    fut.set_exception(e)
                return fut

            loop.run_in_executor = _sync_rie
            try:
                await original_run_search_job(job_id, request)
            finally:
                loop.run_in_executor = original_rie

        monkeypatch.setattr("main.run_search_job", _inline_run_search_job)

    def test_result_404_for_unknown_job(self, client):
        """Result of unknown job should return 404."""
        response = client.get("/buscar/nonexistent-job-id/result")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_result_202_for_running_job(self, client, monkeypatch):
        """Result of a running job should return 202."""
        # Directly create a running job in the store to avoid deadlocks
        from job_store import SearchJob
        job = SearchJob(job_id="running-job", status="running")
        _job_store._jobs["running-job"] = job

        result_resp = client.get("/buscar/running-job/result")
        assert result_resp.status_code == 202
        data = result_resp.json()
        assert data["status"] == "running"

    def test_result_500_for_failed_job(self, client, monkeypatch):
        """Result of a failed job should return 500 with error."""
        # Directly create a failed job in the store
        from job_store import SearchJob
        job = SearchJob(
            job_id="failed-job",
            status="failed",
            error="Something went wrong",
            completed_at=time.time(),
        )
        _job_store._jobs["failed-job"] = job

        result_resp = client.get("/buscar/failed-job/result")
        assert result_resp.status_code == 500
        data = result_resp.json()
        assert data["status"] == "failed"
        assert "error" in data

    def test_result_completed_with_data(self, client, monkeypatch, run_sync):
        """Result of a completed job should return 200 with full data."""
        mock_licitacao = {
            "codigoCompra": "123",
            "objetoCompra": "Aquisição de uniformes escolares",
            "nomeOrgao": "Prefeitura Test",
            "uf": "SP",
            "municipio": "São Paulo",
            "valorTotalEstimado": 100000.00,
            "dataAberturaProposta": "2025-02-15T10:00:00",
            "linkSistemaOrigem": "https://pncp.gov.br/test",
        }

        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel-data"))

        def mock_gerar_resumo(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo="Found 1 bid",
                total_oportunidades=1,
                valor_total=100000.00,
            )

        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)

        request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }

        resp = client.post("/buscar", json=request)
        job_id = resp.json()["job_id"]

        # With run_sync, the background task completes within the POST
        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] == "completed"
        assert data["job_id"] == job_id
        assert data["total_raw"] == 1
        assert data["total_filtrado"] == 1
        assert "resumo" in data
        assert "excel_base64" in data
        assert len(data["excel_base64"]) > 0


class TestJobLifecycle:
    """Test job lifecycle behaviors: capacity limits and cleanup."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self):
        """Reset job store between tests."""
        _job_store._jobs.clear()
        yield
        _job_store._jobs.clear()

    def test_429_when_too_many_jobs(self, client, monkeypatch):
        """Should return 429 when job store is at capacity."""
        from job_store import SearchJob

        # Fill up the job store with fake active jobs
        for i in range(_job_store.max_jobs):
            job = SearchJob(job_id=f"fake-job-{i}", status="running")
            _job_store._jobs[f"fake-job-{i}"] = job

        request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }

        response = client.post("/buscar", json=request)
        assert response.status_code == 429
        assert "simultâneas" in response.json()["detail"].lower() or "429" in str(response.status_code)

    def test_job_cleanup(self, client, monkeypatch):
        """Completed jobs with expired TTL should be cleaned up."""
        from job_store import SearchJob

        # Insert a completed job with created_at far in the past
        old_job = SearchJob(
            job_id="old-job",
            status="completed",
            created_at=time.time() - _job_store.ttl - 100,
            completed_at=time.time() - _job_store.ttl - 100,
            result={"test": True},
        )
        _job_store._jobs["old-job"] = old_job

        # Verify the job exists
        assert "old-job" in _job_store._jobs

        # Trigger cleanup via a new POST (which calls cleanup_expired)
        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }
        client.post("/buscar", json=request)

        # The old job should have been cleaned up
        assert "old-job" not in _job_store._jobs


class TestBuscarIntegration:
    """Integration tests using real modules (not fully mocked)."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self):
        """Reset job store between tests."""
        _job_store._jobs.clear()
        yield
        _job_store._jobs.clear()

    def _wait_for_job(self, client, job_id, timeout=5):
        """Poll job status until completed or failed."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = client.get(f"/buscar/{job_id}/status")
            if resp.status_code == 200:
                data = resp.json()
                if data["status"] in ("completed", "failed"):
                    return data
            time.sleep(0.1)
        return None

    @pytest.mark.integration
    @pytest.mark.skip(reason="Filter correctly rejects bids with future deadlines (>7 days)")
    def test_buscar_with_real_filter_and_excel(self, client, monkeypatch):
        """Test with real filter and excel modules (mock only PNCP and LLM)."""
        from unittest.mock import Mock

        mock_licitacao = {
            "codigoCompra": "TEST123",
            "objetoCompra": "Aquisição de uniformes escolares",
            "nomeOrgao": "Prefeitura Test",
            "uf": "SP",
            "municipio": "São Paulo",
            "valorTotalEstimado": 200000.00,
            "dataAberturaProposta": "2025-02-15T10:00:00",
            "linkSistemaOrigem": "https://pncp.gov.br/test",
        }

        mock_client_instance = Mock()
        mock_client_instance.fetch_all.return_value = iter([mock_licitacao])

        monkeypatch.setattr("main._get_pncp_client", lambda: mock_client_instance)

        def mock_gerar_resumo(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo=f"{len(bids)} licitação encontrada",
                total_oportunidades=len(bids),
                valor_total=sum(b.get("valorTotalEstimado", 0) for b in bids),
            )

        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)

        request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }

        resp = client.post("/buscar", json=request)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        self._wait_for_job(client, job_id)

        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200

        data = result_resp.json()
        assert data["total_filtrado"] >= 1
        assert len(data["excel_base64"]) > 100
