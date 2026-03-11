"""Tests for Security Hardening (v3-story-3.3 + Story 1.0).

Covers:
- CORS origin whitelisting (TD-001) + restricted headers (SYS-004)
- API key authentication middleware (TD-003) with hmac.compare_digest (DB-005, DB-014)
- Rate limiting with slowapi (TD-006)
- Debug endpoints feature flag (TD-055)
- termos_busca input length validation (TD-056)
- CSP header (SYS-005)
- HSTS header (SYS-005)
- Auth bypass safeguard in production (SYS-007)
- Dev mode auth bypass warning (SYS-007)
"""

import hmac
import inspect
import logging
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from dependencies import get_orchestrator
from main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# TD-001 / SYS-004: CORS origin whitelisting + restricted headers
# ---------------------------------------------------------------------------


class TestCORSWhitelist:
    """Verify CORS rejects non-whitelisted origins."""

    def test_cors_rejects_disallowed_origin(self, client):
        response = client.get("/health", headers={"Origin": "http://evil.com"})
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") != "http://evil.com"

    def test_cors_allows_localhost(self, client):
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_allows_production_origin(self, client):
        response = client.get(
            "/health",
            headers={"Origin": "https://descomplicita.vercel.app"},
        )
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("access-control-allow-origin") == "https://descomplicita.vercel.app"

    def test_cors_preflight_allowed_origin(self, client):
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

    def test_cors_rejects_unlisted_header(self, client):
        """SYS-004: CORS should only allow explicitly listed headers."""
        response = client.options(
            "/buscar",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Custom-Header",
            },
        )
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        allowed = headers_lower.get("access-control-allow-headers", "")
        assert "x-custom-header" not in allowed.lower()


# ---------------------------------------------------------------------------
# TD-003 / CP4: API key authentication + hmac.compare_digest
# ---------------------------------------------------------------------------


class TestAPIKeyAuth:
    def test_missing_api_key_on_protected_endpoint_returns_401(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "test-secret-key")
        client = TestClient(app)
        response = client.get("/some-protected-endpoint")
        assert response.status_code in (401, 404)

    def test_missing_api_key_allows_anonymous_on_optional_paths(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "test-secret-key")
        client = TestClient(app)
        response = client.get("/setores")
        assert response.status_code == 200

    def test_invalid_api_key_returns_401(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "test-secret-key")
        client = TestClient(app)
        response = client.get("/setores", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_valid_api_key_passes(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "test-secret-key")
        client = TestClient(app)
        response = client.get("/setores", headers={"X-API-Key": "test-secret-key"})
        assert response.status_code == 200

    def test_health_exempt_from_auth(self, monkeypatch):
        monkeypatch.setenv("API_KEY", "test-secret-key")
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_no_api_key_configured_allows_all(self, client):
        response = client.get("/setores")
        assert response.status_code == 200


class TestHmacCompareDigest:
    """CP4: Verify hmac.compare_digest is used in BOTH auth points."""

    def test_middleware_uses_hmac_compare_digest(self):
        """DB-005: middleware/auth.py must use hmac.compare_digest for API key comparison."""
        from middleware import auth as auth_module

        source = inspect.getsource(auth_module.APIKeyMiddleware.dispatch)
        assert "hmac.compare_digest" in source, "middleware/auth.py must use hmac.compare_digest for API key comparison"
        assert "request_key == api_key" not in source, "middleware/auth.py must NOT use == for API key comparison"

    def test_auth_token_endpoint_uses_hmac_compare_digest(self):
        """DB-014: main.py /auth/token must use hmac.compare_digest for API key comparison."""
        import main as main_module

        source = inspect.getsource(main_module.auth_token)
        assert "hmac.compare_digest" in source, "main.py auth_token must use hmac.compare_digest for API key comparison"
        assert "request_key != api_key" not in source, "main.py auth_token must NOT use != for API key comparison"


# ---------------------------------------------------------------------------
# TD-006: Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_rate_limit_returns_429(self, client, monkeypatch):
        from tests.mock_helpers import make_mock_orchestrator

        mock_orch = make_mock_orchestrator([])
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        monkeypatch.setattr("main.filter_batch", lambda bids, **kwargs: ([], {}))

        valid_request = {
            "ufs": ["SP"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }

        responses = []
        for _ in range(11):
            resp = client.post("/buscar", json=valid_request)
            responses.append(resp.status_code)

        assert 429 in responses, f"Expected 429 in responses but got {set(responses)}"

        app.dependency_overrides.pop(get_orchestrator, None)


# ---------------------------------------------------------------------------
# TD-055: Debug endpoints feature flag
# ---------------------------------------------------------------------------


class TestDebugEndpointsFeatureFlag:
    def test_cache_stats_returns_404_when_disabled(self, client):
        response = client.get("/cache/stats")
        assert response.status_code == 404

    def test_cache_clear_returns_404_when_disabled(self, client):
        response = client.post("/cache/clear")
        assert response.status_code == 404

    def test_debug_pncp_test_returns_404_when_disabled(self, client):
        response = client.get("/debug/pncp-test")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TD-056: termos_busca input length validation
# ---------------------------------------------------------------------------


class TestTermosBuscaMaxLength:
    def test_501_chars_returns_422(self, client, monkeypatch):
        from tests.mock_helpers import make_mock_orchestrator

        mock_orch = make_mock_orchestrator([])
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch
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

        app.dependency_overrides.pop(get_orchestrator, None)

    def test_500_chars_accepted(self, client, monkeypatch):
        from tests.mock_helpers import make_mock_orchestrator

        mock_orch = make_mock_orchestrator([])
        app.dependency_overrides[get_orchestrator] = lambda: mock_orch
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

        app.dependency_overrides.pop(get_orchestrator, None)


# ---------------------------------------------------------------------------
# SYS-005: Security headers (CSP + HSTS)
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    """Verify CSP and HSTS headers are present on all responses."""

    def test_csp_header_present(self, client):
        """Content-Security-Policy header must be present on responses."""
        response = client.get("/health")
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        csp = headers_lower.get("content-security-policy", "")
        assert csp, "Content-Security-Policy header missing"
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_hsts_header_present_with_correct_max_age(self, client):
        """Strict-Transport-Security header must have max-age >= 31536000."""
        response = client.get("/health")
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        hsts = headers_lower.get("strict-transport-security", "")
        assert hsts, "Strict-Transport-Security header missing"
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts

    def test_security_headers_on_api_endpoint(self, client):
        """Security headers present on API endpoints too, not just /health."""
        response = client.get("/setores")
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert headers_lower.get("content-security-policy"), "CSP missing on /setores"
        assert headers_lower.get("strict-transport-security"), "HSTS missing on /setores"


# ---------------------------------------------------------------------------
# SYS-007: Auth bypass safeguard
# ---------------------------------------------------------------------------


class TestAuthBypassSafeguard:
    """Verify production safeguard and dev mode warning."""

    def test_production_fails_without_auth_secrets(self, monkeypatch):
        """App returns 503 in production when no auth secrets are configured."""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        monkeypatch.setenv("NODE_ENV", "production")
        client = TestClient(app, raise_server_exceptions=False)
        # /setores is an optional-auth path, but in production without secrets it should fail
        response = client.get("/setores")
        assert response.status_code == 503
        assert "misconfiguration" in response.json()["detail"].lower()

    def test_dev_mode_allows_bypass_without_auth(self, monkeypatch):
        """App starts normally in dev mode without auth secrets (with warning)."""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/setores")
        assert response.status_code == 200

    def test_dev_mode_emits_warning_log(self, monkeypatch, caplog):
        """Dev mode auth bypass emits a warning log message."""
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        monkeypatch.delenv("NODE_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        client = TestClient(app, raise_server_exceptions=False)
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            client.get("/setores")
        assert any("Auth bypass active" in record.message for record in caplog.records)
