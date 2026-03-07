"""Tests for Story 1.0: Security Hardening.

Covers:
- CORS origin whitelisting (TD-001)
- API key authentication middleware (TD-003)
- Rate limiting with slowapi (TD-006)
- Debug endpoints feature flag (TD-055)
- termos_busca input length validation (TD-056)
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# TD-001: CORS origin whitelisting
# ---------------------------------------------------------------------------


class TestCORSWhitelist:
    """Verify CORS rejects non-whitelisted origins."""

    def test_cors_rejects_disallowed_origin(self, client):
        """Requests from arbitrary origins should not get CORS headers."""
        response = client.get("/health", headers={"Origin": "http://evil.com"})

        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") != "http://evil.com"

    def test_cors_allows_localhost(self, client):
        """localhost:3000 should be allowed."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_allows_production_origin(self, client):
        """Production Vercel domain should be allowed."""
        response = client.get(
            "/health",
            headers={"Origin": "https://descomplicita.vercel.app"},
        )

        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") == "https://descomplicita.vercel.app"

    def test_cors_preflight_allowed_origin(self, client):
        """Preflight OPTIONS for allowed origin should succeed."""
        response = client.options(
            "/buscar",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") == "http://localhost:3000"


# ---------------------------------------------------------------------------
# TD-003: API key authentication
# ---------------------------------------------------------------------------


class TestAPIKeyAuth:
    """Verify API key middleware."""

    def test_missing_api_key_returns_401(self, monkeypatch):
        """Missing X-API-Key header should return 401 when API_KEY is set."""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        from main import app
        client = TestClient(app)

        response = client.get("/setores")
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_invalid_api_key_returns_401(self, monkeypatch):
        """Invalid X-API-Key should return 401."""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        from main import app
        client = TestClient(app)

        response = client.get("/setores", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_valid_api_key_passes(self, monkeypatch):
        """Valid X-API-Key should allow request through."""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        from main import app
        client = TestClient(app)

        response = client.get("/setores", headers={"X-API-Key": "test-secret-key"})
        assert response.status_code == 200

    def test_health_exempt_from_auth(self, monkeypatch):
        """Health endpoint should be accessible without API key."""
        monkeypatch.setenv("API_KEY", "test-secret-key")
        from main import app
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

    def test_no_api_key_configured_allows_all(self, client):
        """When API_KEY env var is not set, all requests pass through."""
        response = client.get("/setores")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# TD-006: Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Verify slowapi rate limiting."""

    def test_rate_limit_returns_429(self, client, monkeypatch):
        """Exceeding rate limit should return 429."""
        from main import app
        from tests.mock_helpers import make_mock_orchestrator

        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        valid_request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }

        # Send 11 requests (limit is 10/minute)
        responses = []
        for _ in range(11):
            resp = client.post("/buscar", json=valid_request)
            responses.append(resp.status_code)

        assert 429 in responses, f"Expected 429 in responses but got {set(responses)}"


# ---------------------------------------------------------------------------
# TD-055: Debug endpoints feature flag
# ---------------------------------------------------------------------------


class TestDebugEndpointsFeatureFlag:
    """Verify debug endpoints are gated behind ENABLE_DEBUG_ENDPOINTS."""

    def test_cache_stats_returns_404_when_disabled(self, client):
        """GET /cache/stats should return 404 when feature flag is off."""
        response = client.get("/cache/stats")
        assert response.status_code == 404

    def test_cache_clear_returns_404_when_disabled(self, client):
        """POST /cache/clear should return 404 when feature flag is off."""
        response = client.post("/cache/clear")
        assert response.status_code == 404

    def test_debug_pncp_test_returns_404_when_disabled(self, client):
        """GET /debug/pncp-test should return 404 when feature flag is off."""
        response = client.get("/debug/pncp-test")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TD-056: termos_busca input length validation
# ---------------------------------------------------------------------------


class TestTermosBuscaMaxLength:
    """Verify termos_busca rejects input longer than 500 characters."""

    def test_501_chars_returns_422(self, client, monkeypatch):
        """termos_busca with 501+ characters should return 422."""
        from tests.mock_helpers import make_mock_orchestrator

        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        long_terms = "a" * 501
        request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
            "termos_busca": long_terms,
        }

        response = client.post("/buscar", json=request)
        assert response.status_code == 422

    def test_500_chars_accepted(self, client, monkeypatch):
        """termos_busca with exactly 500 characters should be accepted."""
        from tests.mock_helpers import make_mock_orchestrator

        monkeypatch.setattr("main._get_orchestrator", lambda: make_mock_orchestrator([]))
        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        terms_500 = "a" * 500
        request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
            "termos_busca": terms_500,
        }

        response = client.post("/buscar", json=request)
        assert response.status_code == 200
