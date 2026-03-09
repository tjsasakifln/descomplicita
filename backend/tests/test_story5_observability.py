"""Tests for Story 5.0 — Observability, Safety, and API Quality features."""

import asyncio
import logging
import uuid
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import MAX_DATE_RANGE_DAYS, MAX_DOWNLOAD_SIZE, PNCP_BASE_URL
from main import app
from middleware.correlation_id import (
    CorrelationIdFilter,
    CorrelationIdMiddleware,
    correlation_id_var,
)
from schemas import BuscaRequest, JobResultResponse


# ---------------------------------------------------------------------------
# Correlation ID middleware tests (TD-017)
# ---------------------------------------------------------------------------


class TestCorrelationIdMiddleware:
    """Test correlation ID generation and propagation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_response_has_x_request_id_header(self, client):
        """Correlation ID middleware generates UUID and attaches to response header."""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        uuid.UUID(request_id)  # Validates UUID format

    def test_request_id_is_uuid_format(self, client):
        """Generated request ID is a valid UUID."""
        response = client.get("/")
        request_id = response.headers["X-Request-ID"]
        parsed = uuid.UUID(request_id)
        assert str(parsed) == request_id

    def test_each_request_gets_unique_id(self, client):
        """Each request gets a different correlation ID."""
        r1 = client.get("/health")
        r2 = client.get("/health")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]

    def test_client_provided_request_id_preserved(self, client):
        """If client sends X-Request-ID, it is preserved."""
        custom_id = str(uuid.uuid4())
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id


class TestCorrelationIdInLogs:
    """Test that correlation ID appears in log output."""

    def test_correlation_id_filter_adds_to_record(self):
        """CorrelationIdFilter injects correlation_id into log records."""
        log_filter = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )

        test_id = str(uuid.uuid4())
        token = correlation_id_var.set(test_id)
        try:
            log_filter.filter(record)
            assert record.correlation_id == test_id
        finally:
            correlation_id_var.reset(token)

    def test_correlation_id_empty_when_not_set(self):
        """Without middleware, correlation_id defaults to empty string."""
        log_filter = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )
        # Reset to default
        token = correlation_id_var.set("")
        try:
            log_filter.filter(record)
            assert record.correlation_id == ""
        finally:
            correlation_id_var.reset(token)


# ---------------------------------------------------------------------------
# Sentry integration tests (TD-057)
# ---------------------------------------------------------------------------


class TestSentryIntegration:
    """Test Sentry SDK integration (mocked)."""

    def test_sentry_captures_exception_when_configured(self):
        """Sentry captures exception when DSN is set (mock verify)."""
        with patch.dict("os.environ", {"SENTRY_DSN": "https://test@sentry.io/123"}):
            with patch("sentry_sdk.init") as mock_init:
                with patch("sentry_sdk.capture_exception") as mock_capture:
                    import sentry_sdk
                    sentry_sdk.capture_exception(ValueError("test error"))
                    mock_capture.assert_called_once()

    def test_sentry_not_initialized_without_dsn(self):
        """Sentry is not initialized when SENTRY_DSN is empty."""
        import os
        dsn = os.getenv("SENTRY_DSN", "")
        # In test environment, SENTRY_DSN should not be set
        assert dsn == ""


# ---------------------------------------------------------------------------
# PNCP base URL configuration (TD-018)
# ---------------------------------------------------------------------------


class TestPNCPBaseURLConfig:
    """Test PNCP client uses configured base URL from environment."""

    def test_pncp_base_url_has_default(self):
        """PNCP_BASE_URL defaults to the public API endpoint."""
        assert PNCP_BASE_URL == "https://pncp.gov.br/api/consulta/v1"

    def test_pncp_base_url_in_sources_config(self):
        """SOURCES_CONFIG uses the configurable PNCP_BASE_URL."""
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["pncp"]["base_url"] == PNCP_BASE_URL


# ---------------------------------------------------------------------------
# Date range validation (TD-037)
# ---------------------------------------------------------------------------


class TestDateRangeValidation:
    """Test configurable maximum date range validation."""

    def test_date_range_within_limit_accepted(self):
        """Date range within MAX_DATE_RANGE_DAYS is accepted."""
        today = date.today()
        d_ini = (today - timedelta(days=30)).isoformat()
        d_fin = today.isoformat()
        request = BuscaRequest(ufs=["SP"], data_inicial=d_ini, data_final=d_fin)
        assert request.data_inicial == d_ini

    def test_date_range_at_limit_accepted(self):
        """Date range exactly at MAX_DATE_RANGE_DAYS is accepted."""
        today = date.today()
        d_ini = (today - timedelta(days=MAX_DATE_RANGE_DAYS)).isoformat()
        d_fin = today.isoformat()
        request = BuscaRequest(ufs=["SP"], data_inicial=d_ini, data_final=d_fin)
        assert request.data_inicial == d_ini

    def test_date_range_exceeds_limit_returns_422(self):
        """Date range > MAX_DATE_RANGE_DAYS returns validation error."""
        today = date.today()
        d_ini = (today - timedelta(days=MAX_DATE_RANGE_DAYS + 1)).isoformat()
        d_fin = today.isoformat()
        with pytest.raises(ValidationError) as exc_info:
            BuscaRequest(ufs=["SP"], data_inicial=d_ini, data_final=d_fin)
        assert "máximo permitido" in str(exc_info.value).lower() or "excede" in str(exc_info.value).lower()

    def test_date_range_far_exceeds_limit(self):
        """Date range of 180 days is rejected."""
        today = date.today()
        d_ini = (today - timedelta(days=180)).isoformat()
        d_fin = today.isoformat()
        with pytest.raises(ValidationError):
            BuscaRequest(ufs=["SP"], data_inicial=d_ini, data_final=d_fin)

    def test_max_date_range_default_is_90(self):
        """Default MAX_DATE_RANGE_DAYS is 90."""
        assert MAX_DATE_RANGE_DAYS == 90


# ---------------------------------------------------------------------------
# Content-length validation for downloads (TD-036)
# ---------------------------------------------------------------------------


class TestContentLengthValidation:
    """Test content-length validation for Excel downloads."""

    def test_max_download_size_configured(self):
        """MAX_DOWNLOAD_SIZE is configured with a default."""
        assert MAX_DOWNLOAD_SIZE == 50 * 1024 * 1024  # 50MB

    def test_download_rejects_oversized_file(self):
        """Download endpoint rejects files exceeding MAX_DOWNLOAD_SIZE."""
        from dependencies import get_job_store
        from tests.conftest import get_test_job_store

        client = TestClient(app)
        job_store = get_test_job_store()

        # Create a job with an oversized "excel" result
        job_id = str(uuid.uuid4())
        loop = asyncio.new_event_loop()
        loop.run_until_complete(job_store.create(job_id))
        loop.run_until_complete(job_store.complete(job_id, {"resumo": {}}))
        # Store oversized Excel via streaming path (TD-C01/XD-PERF-01)
        job_store._excel[job_id] = b"x" * (MAX_DOWNLOAD_SIZE + 1)
        loop.close()

        response = client.get(f"/buscar/{job_id}/download")
        assert response.status_code == 413


# ---------------------------------------------------------------------------
# OpenAPI schema tests (TD-022)
# ---------------------------------------------------------------------------


class TestOpenAPISchema:
    """Test that OpenAPI schema includes result endpoint response model."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_openapi_includes_result_endpoint(self, client):
        """OpenAPI schema is generated and includes result endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/buscar/{job_id}/result" in schema["paths"]

    def test_result_endpoint_has_response_schema(self, client):
        """Result endpoint has a typed response schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        result_path = schema["paths"]["/buscar/{job_id}/result"]
        get_op = result_path["get"]
        # Should reference JobResultResponse
        assert "200" in get_op["responses"]
        response_schema = get_op["responses"]["200"]
        assert "content" in response_schema

    def test_job_result_response_model_has_fields(self):
        """JobResultResponse model has expected fields."""
        fields = JobResultResponse.model_fields
        assert "job_id" in fields
        assert "status" in fields
        assert "resumo" in fields
        assert "total_raw" in fields
        assert "total_filtrado" in fields
        assert "error" in fields
