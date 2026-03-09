"""Tests for FastAPI application structure and base endpoints."""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, Mock, patch
from io import BytesIO
from fastapi.testclient import TestClient
from main import app, run_search_job
from dependencies import get_job_store, get_orchestrator, get_pncp_source
from tests.conftest import get_test_job_store
from tests.mock_helpers import make_mock_orchestrator


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def job_store():
    """Get the test job store."""
    return get_test_job_store()


class TestApplicationSetup:
    """Test FastAPI application initialization and configuration."""

    def test_app_title(self):
        assert app.title == "Descomplicita API"

    def test_app_version(self):
        assert app.version == "0.4.0"

    def test_app_has_docs_endpoint(self):
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"

    def test_cors_middleware_configured(self):
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes


class TestRootEndpoint:
    """Test root endpoint functionality."""

    def test_root_status_code(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_response_structure(self, client):
        response = client.get("/")
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        assert "status" in data

    def test_root_version_matches(self, client):
        response = client.get("/")
        data = response.json()
        assert data["version"] == "0.4.0"

    def test_root_endpoints_links(self, client):
        response = client.get("/")
        data = response.json()
        endpoints = data["endpoints"]
        assert endpoints["docs"] == "/docs"
        assert endpoints["redoc"] == "/redoc"
        assert endpoints["health"] == "/health"
        assert endpoints["openapi"] == "/openapi.json"

    def test_root_status_operational(self, client):
        response = client.get("/")
        data = response.json()
        assert data["status"] == "operational"


class TestHealthEndpoint:
    """Test health check endpoint functionality."""

    def test_health_status_code(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "redis" in data

    def test_health_status_healthy(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_timestamp_format(self, client):
        from datetime import datetime, timezone
        response = client.get("/health")
        data = response.json()
        timestamp = data["timestamp"]
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)
        now = datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        delta = (now - parsed).total_seconds()
        assert abs(delta) < 5

    def test_health_timestamp_changes(self, client):
        import time
        response1 = client.get("/health")
        time.sleep(0.01)
        response2 = client.get("/health")
        assert response1.json()["timestamp"] != response2.json()["timestamp"]

    def test_health_version_matches(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.4.0"

    def test_health_response_time(self, client):
        import time
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 0.1

    def test_health_no_authentication_required(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_json_content_type(self, client):
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]

    def test_health_redis_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["redis"] == "disconnected"  # No Redis in tests


class TestCORSHeaders:
    """Test CORS configuration and headers."""

    def test_cors_preflight_options(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200

    def test_cors_headers_present(self, client):
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert "access-control-allow-origin" in headers_lower

    def test_cors_rejects_disallowed_origins(self, client):
        response = client.get("/health", headers={"Origin": "http://evil.com"})
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") != "http://evil.com"

    def test_cors_allows_whitelisted_origins(self, client):
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_allows_post_method(self, client):
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
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_schema_structure(self, client):
        response = client.get("/openapi.json")
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_openapi_info_metadata(self, client):
        response = client.get("/openapi.json")
        schema = response.json()
        info = schema["info"]
        assert info["title"] == "Descomplicita API"
        assert info["version"] == "0.4.0"

    def test_openapi_has_health_endpoint(self, client):
        response = client.get("/openapi.json")
        schema = response.json()
        assert "/health" in schema["paths"]

    def test_openapi_has_root_endpoint(self, client):
        response = client.get("/openapi.json")
        schema = response.json()
        assert "/" in schema["paths"]

    def test_docs_page_accessible(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_page_accessible(self, client):
        response = client.get("/redoc")
        assert response.status_code == 200


class TestErrorHandling:
    """Test basic error handling for non-existent endpoints."""

    def test_404_for_invalid_endpoint(self, client):
        response = client.get("/invalid-endpoint-xyz")
        assert response.status_code == 404

    def test_404_response_structure(self, client):
        response = client.get("/invalid-endpoint-xyz")
        data = response.json()
        assert "detail" in data


class TestBuscarEndpoint:
    """Test POST /buscar endpoint - async job-based orchestration pipeline."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self, job_store):
        job_store._jobs.clear()
        yield
        job_store._jobs.clear()

    @pytest.fixture
    def valid_request(self):
        return {
            "ufs": ["SP", "RJ"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }

    @pytest.fixture
    def mock_licitacao(self):
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
        """Make background search jobs complete synchronously."""
        import main as main_module
        original_run_search_job = main_module.run_search_job

        async def _inline_run_search_job(job_id, request, job_store, orchestrator, database=None):
            loop = asyncio.get_running_loop()
            original_rie = loop.run_in_executor

            def _sync_run_in_executor(executor, func, *args):
                fut = loop.create_future()
                try:
                    result = func(*args)
                    fut.set_result(result)
                except Exception as e:
                    fut.set_exception(e)
                return fut

            loop.run_in_executor = _sync_run_in_executor
            try:
                await original_run_search_job(job_id, request, job_store, orchestrator, database)
            finally:
                loop.run_in_executor = original_rie

        monkeypatch.setattr("main.run_search_job", _inline_run_search_job)

    def _override_orchestrator(self, mock_orch):
        """Override the orchestrator dependency."""
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

    def _post_and_get_result(self, client, request):
        resp = client.post("/buscar", json=request)
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        result_resp = client.get(f"/buscar/{job_id}/result")
        return result_resp

    def test_buscar_endpoint_exists(self, client):
        response = client.post("/buscar", json={})
        assert response.status_code == 422

    def test_buscar_validation_empty_ufs(self, client, valid_request):
        request = valid_request.copy()
        request["ufs"] = []
        response = client.post("/buscar", json=request)
        assert response.status_code == 422
        assert "ufs" in response.json()["detail"][0]["loc"]

    def test_buscar_validation_invalid_date_format(self, client, valid_request):
        request = valid_request.copy()
        request["data_inicial"] = "01-01-2025"
        response = client.post("/buscar", json=request)
        assert response.status_code == 422

    def test_buscar_validation_missing_fields(self, client):
        response = client.post("/buscar", json={"ufs": ["SP"]})
        assert response.status_code == 422

    def test_buscar_returns_job_id(self, client, valid_request, monkeypatch):
        self._override_orchestrator(make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        response = client.post("/buscar", json=valid_request)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert len(data["job_id"]) == 36

    def test_buscar_success_response_structure(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        self._override_orchestrator(make_mock_orchestrator([mock_licitacao]))

        def mock_filter_batch(bids, **kwargs):
            return [bids[0]], {"total_rejeitados": 0}

        def mock_create_excel(bids):
            buf = BytesIO()
            buf.write(b"fake-excel-content")
            buf.seek(0)
            return buf

        async def mock_gerar_resumo(bids, **kwargs):
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
        assert "total_raw" in data
        assert "total_filtrado" in data
        # excel_bytes should NOT be in JSON result
        assert "excel_bytes" not in data
        assert "excel_base64" not in data

    def test_buscar_resumo_structure(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        self._override_orchestrator(make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel"))

        async def mock_gerar_resumo(bids, **kwargs):
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

    def test_buscar_excel_download(self, client, valid_request, mock_licitacao, monkeypatch, run_sync, job_store):
        """Excel should be downloadable via streaming endpoint."""
        self._override_orchestrator(make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))

        excel_content = b"PK\x03\x04fake-excel-header"
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(excel_content))

        async def mock_gerar_resumo(bids, **kwargs):
            from schemas import ResumoLicitacoes
            return ResumoLicitacoes(
                resumo_executivo="Test",
                total_oportunidades=1,
                valor_total=150000.00,
            )

        monkeypatch.setattr("main.gerar_resumo", mock_gerar_resumo)

        resp = client.post("/buscar", json=valid_request)
        job_id = resp.json()["job_id"]

        # Download via streaming endpoint
        download_resp = client.get(f"/buscar/{job_id}/download")
        assert download_resp.status_code == 200
        assert download_resp.content == excel_content
        assert "application/vnd.openxmlformats" in download_resp.headers["content-type"]

    def test_buscar_llm_fallback_on_error(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        self._override_orchestrator(make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel"))

        async def mock_gerar_resumo(bids, **kwargs):
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
        from exceptions import PNCPAPIError
        self._override_orchestrator(make_mock_orchestrator(error=PNCPAPIError("Connection timeout")))

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 500
        data = result_resp.json()
        assert data["status"] == "failed"

    def test_buscar_rate_limit_error_fails_job(self, client, valid_request, monkeypatch, run_sync):
        from exceptions import PNCPRateLimitError
        error = PNCPRateLimitError("Rate limit exceeded")
        error.retry_after = 120
        self._override_orchestrator(make_mock_orchestrator(error=error))

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 500
        data = result_resp.json()
        assert data["status"] == "failed"

    def test_buscar_internal_error_fails_job(self, client, valid_request, monkeypatch, run_sync):
        self._override_orchestrator(make_mock_orchestrator(error=RuntimeError("Internal bug with sensitive data")))

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 500
        data = result_resp.json()
        assert data["status"] == "failed"
        assert "Erro interno" in data["error"]["message"]
        assert "sensitive data" not in data["error"]["message"]

    def test_buscar_empty_results(self, client, valid_request, monkeypatch, run_sync):
        self._override_orchestrator(make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        result_resp = self._post_and_get_result(client, valid_request)
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["total_raw"] == 0
        assert data["total_filtrado"] == 0

    def test_buscar_statistics_match(self, client, valid_request, mock_licitacao, monkeypatch, run_sync):
        mock_licitacoes_raw = [mock_licitacao.copy() for _ in range(10)]
        self._override_orchestrator(make_mock_orchestrator(mock_licitacoes_raw))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: (bids[:3], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel"))

        async def mock_gerar_resumo(bids, **kwargs):
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
        self._override_orchestrator(make_mock_orchestrator([mock_licitacao]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel"))

        async def mock_gerar_resumo(bids, **kwargs):
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
    def reset_job_store(self, job_store):
        job_store._jobs.clear()
        yield
        job_store._jobs.clear()

    def test_status_404_for_unknown_job(self, client):
        response = client.get("/buscar/nonexistent-job-id/status")
        assert response.status_code == 404

    def test_status_returns_progress(self, client, job_store):
        from job_store import SearchJob
        job = SearchJob(job_id="running-status-test", status="running")
        job.progress["phase"] = "fetching"
        job.progress["sources_completed"] = 1
        job.progress["sources_total"] = 3
        job_store._jobs["running-status-test"] = job

        status_resp = client.get("/buscar/running-status-test/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["job_id"] == "running-status-test"
        assert data["status"] == "running"
        assert data["progress"]["sources_total"] == 3


class TestJobResultEndpoint:
    """Test GET /buscar/{job_id}/result endpoint."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self, job_store):
        job_store._jobs.clear()
        yield
        job_store._jobs.clear()

    @pytest.fixture
    def run_sync(self, monkeypatch):
        import main as main_module
        original_run_search_job = main_module.run_search_job

        async def _inline_run_search_job(job_id, request, job_store, orchestrator, database=None):
            loop = asyncio.get_running_loop()
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
                await original_run_search_job(job_id, request, job_store, orchestrator, database)
            finally:
                loop.run_in_executor = original_rie

        monkeypatch.setattr("main.run_search_job", _inline_run_search_job)

    def test_result_404_for_unknown_job(self, client):
        response = client.get("/buscar/nonexistent-job-id/result")
        assert response.status_code == 404

    def test_result_202_for_running_job(self, client, job_store):
        from job_store import SearchJob
        job = SearchJob(job_id="running-job", status="running")
        job_store._jobs["running-job"] = job

        result_resp = client.get("/buscar/running-job/result")
        assert result_resp.status_code == 202

    def test_result_500_for_failed_job(self, client, job_store):
        from job_store import SearchJob
        job = SearchJob(
            job_id="failed-job",
            status="failed",
            error="Something went wrong",
            completed_at=time.time(),
        )
        job_store._jobs["failed-job"] = job

        result_resp = client.get("/buscar/failed-job/result")
        assert result_resp.status_code == 500

    def test_result_completed_with_data(self, client, monkeypatch, run_sync, job_store):
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

        app.dependency_overrides[get_orchestrator] = lambda: make_mock_orchestrator([mock_licitacao])
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([bids[0]], {}))
        monkeypatch.setattr("main.create_excel", lambda bids: BytesIO(b"excel-data"))

        async def mock_gerar_resumo(bids, **kwargs):
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

        result_resp = client.get(f"/buscar/{job_id}/result")
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["status"] == "completed"
        assert data["total_raw"] == 1
        assert data["total_filtrado"] == 1
        assert "resumo" in data


class TestJobDownloadEndpoint:
    """Test GET /buscar/{job_id}/download endpoint."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self, job_store):
        job_store._jobs.clear()
        yield
        job_store._jobs.clear()

    def test_download_404_for_unknown_job(self, client):
        response = client.get("/buscar/nonexistent/download")
        assert response.status_code == 404

    def test_download_409_for_running_job(self, client, job_store):
        from job_store import SearchJob
        job = SearchJob(job_id="running-job", status="running")
        job_store._jobs["running-job"] = job

        response = client.get("/buscar/running-job/download")
        assert response.status_code == 409

    def test_download_returns_excel_bytes(self, client, job_store):
        from job_store import SearchJob
        excel_data = b"PK\x03\x04fake-excel"
        job = SearchJob(
            job_id="completed-job",
            status="completed",
            result={"resumo": {}},
            completed_at=time.time(),
        )
        job_store._jobs["completed-job"] = job
        # Store Excel via streaming path (TD-C01/XD-PERF-01)
        job_store._excel["completed-job"] = excel_data

        response = client.get("/buscar/completed-job/download")
        assert response.status_code == 200
        assert response.content == excel_data
        assert "application/vnd.openxmlformats" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]


class TestJobLifecycle:
    """Test job lifecycle behaviors: capacity limits and cleanup."""

    @pytest.fixture(autouse=True)
    def reset_job_store(self, job_store):
        job_store._jobs.clear()
        yield
        job_store._jobs.clear()

    def test_429_when_too_many_jobs(self, client, job_store):
        from job_store import SearchJob
        for i in range(job_store.max_jobs):
            job = SearchJob(job_id=f"fake-job-{i}", status="running")
            job_store._jobs[f"fake-job-{i}"] = job

        request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }
        response = client.post("/buscar", json=request)
        assert response.status_code == 429

    def test_job_cleanup(self, client, monkeypatch, job_store):
        from job_store import SearchJob
        old_job = SearchJob(
            job_id="old-job",
            status="completed",
            created_at=time.time() - job_store.ttl - 100,
            completed_at=time.time() - job_store.ttl - 100,
            result={"test": True},
        )
        job_store._jobs["old-job"] = old_job
        assert "old-job" in job_store._jobs

        app.dependency_overrides[get_orchestrator] = lambda: make_mock_orchestrator([])
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }
        client.post("/buscar", json=request)
        assert "old-job" not in job_store._jobs
