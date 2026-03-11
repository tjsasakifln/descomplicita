"""Tests for Story 1.2 — Quick Wins: Backend e Infraestrutura.

Covers:
- Rate limiting on auth endpoints (TD-SYS-015)
- Transparencia API key validation (TD-SYS-023)
- saved_searches.name CHECK constraint (TD-DB-008)
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from main import app, limiter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Rate Limiting on Auth Endpoints (TD-SYS-015)
# ---------------------------------------------------------------------------


class TestAuthRateLimiting:
    """Burst of 15+ requests in /auth/login within 1 minute returns 429."""

    def _reset_limiter(self):
        """Force-clear the in-memory rate limiter storage."""
        try:
            limiter.reset()
        except Exception:
            if hasattr(limiter, "_storage") and hasattr(limiter._storage, "storage"):
                limiter._storage.storage.clear()

    def test_login_rate_limit_burst_returns_429(self, client):
        """Burst of 20 requests to /auth/login — should get 429 after limit."""
        self._reset_limiter()
        statuses = []
        for _ in range(20):
            resp = client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
            statuses.append(resp.status_code)

        assert 429 in statuses, "Expected 429 (Too Many Requests) after burst"
        # First 10 should be non-429 (they may be 400/422/500 due to missing Supabase, but not 429)
        assert 429 not in statuses[:10], "First 10 requests should not be rate-limited"

    def test_signup_rate_limit_burst_returns_429(self, client):
        """Burst of 15 requests to /auth/signup — should get 429."""
        self._reset_limiter()
        statuses = []
        for _ in range(15):
            resp = client.post("/auth/signup", json={"email": "a@b.com", "password": "x", "display_name": "Test"})
            statuses.append(resp.status_code)

        assert 429 in statuses, "Expected 429 on /auth/signup after burst"

    def test_refresh_rate_limit_burst_returns_429(self, client):
        """Burst of 15 requests to /auth/refresh — should get 429."""
        self._reset_limiter()
        statuses = []
        for _ in range(15):
            resp = client.post("/auth/refresh", json={"refresh_token": "fake-token"})
            statuses.append(resp.status_code)

        assert 429 in statuses, "Expected 429 on /auth/refresh after burst"

    def test_token_rate_limit_burst_returns_429(self, client):
        """Burst of 15 requests to /auth/token — should get 429."""
        self._reset_limiter()
        statuses = []
        for _ in range(15):
            resp = client.post("/auth/token", headers={"X-API-Key": "wrong"})
            statuses.append(resp.status_code)

        assert 429 in statuses, "Expected 429 on /auth/token after burst"

    def test_rate_limit_is_per_ip(self, client):
        """Rate limit uses get_remote_address (per-IP), not global."""
        # TestClient sends from 'testclient' — just verify the limiter key_func
        from slowapi import _rate_limit_exceeded_handler

        assert limiter._key_func.__name__ == "get_remote_address"

    def test_normal_request_within_limit_succeeds(self, client):
        """A single request within the limit should NOT get 429."""
        self._reset_limiter()
        resp = client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
        assert resp.status_code != 429

    def test_rate_limit_returns_429_status_code(self, client):
        """Verify the 429 response is proper HTTP 429."""
        self._reset_limiter()
        for _ in range(11):
            resp = client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
        # The 11th request should be rate limited
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Transparencia API Key Validation (TD-SYS-023)
# ---------------------------------------------------------------------------


class TestTransparenciaApiKeyValidation:
    """TransparenciaSource must fail explicitly when API key is absent."""

    def test_source_without_key_sets_flag_false(self):
        """Creating source without API key sets _api_key_configured=False."""
        import os

        from sources.transparencia_source import TransparenciaSource

        # Ensure env var is not set
        env_key = os.environ.pop("TRANSPARENCIA_API_KEY", None)
        try:
            source = TransparenciaSource(api_key="")
            assert source._api_key_configured is False
        finally:
            if env_key:
                os.environ["TRANSPARENCIA_API_KEY"] = env_key

    def test_source_with_key_sets_flag_true(self):
        """Creating source with API key sets _api_key_configured=True."""
        from sources.transparencia_source import TransparenciaSource

        source = TransparenciaSource(api_key="my-valid-key")
        assert source._api_key_configured is True

    @pytest.mark.asyncio
    async def test_fetch_records_raises_without_key(self):
        """fetch_records raises PermissionError when API key is absent."""
        import os

        from sources.base import SearchQuery
        from sources.transparencia_source import TransparenciaSource

        env_key = os.environ.pop("TRANSPARENCIA_API_KEY", None)
        try:
            source = TransparenciaSource(api_key="")
            query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
            with pytest.raises(PermissionError, match="TRANSPARENCIA_API_KEY"):
                await source.fetch_records(query)
        finally:
            if env_key:
                os.environ["TRANSPARENCIA_API_KEY"] = env_key

    @pytest.mark.asyncio
    async def test_check_sanctions_raises_without_key(self):
        """check_sanctions raises PermissionError when API key is absent."""
        import os

        from sources.transparencia_source import TransparenciaSource

        env_key = os.environ.pop("TRANSPARENCIA_API_KEY", None)
        try:
            source = TransparenciaSource(api_key="")
            with pytest.raises(PermissionError, match="TRANSPARENCIA_API_KEY"):
                await source.check_sanctions("12345678000199")
        finally:
            if env_key:
                os.environ["TRANSPARENCIA_API_KEY"] = env_key

    @pytest.mark.asyncio
    async def test_fetch_records_works_with_key(self):
        """fetch_records does NOT raise when API key is present."""
        import httpx

        from sources.base import SearchQuery
        from sources.transparencia_source import TransparenciaSource

        source = TransparenciaSource(api_key="valid-key-123")

        # Mock the HTTP client to avoid real requests
        resp = AsyncMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = Mock()
        resp.json.return_value = []

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = resp
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
        records = await source.fetch_records(query)
        assert records == []  # No PermissionError raised


# ---------------------------------------------------------------------------
# saved_searches.name CHECK Constraint (TD-DB-008)
# ---------------------------------------------------------------------------


class TestSavedSearchesNameConstraint:
    """Verify migration 005 adds length constraint on saved_searches.name."""

    def test_migration_file_exists(self):
        """Migration 005 SQL file exists."""
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "supabase",
            "migrations",
            "005_saved_searches_name_length.sql",
        )
        assert os.path.exists(path), f"Migration file not found at {path}"

    def test_migration_contains_check_constraint(self):
        """Migration SQL contains the CHECK constraint."""
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "supabase",
            "migrations",
            "005_saved_searches_name_length.sql",
        )
        with open(path) as f:
            sql = f.read()
        assert "CHECK" in sql
        assert "length(name)" in sql
        assert "200" in sql
        assert "saved_searches" in sql

    def test_migration_constraint_name(self):
        """Constraint has a descriptive name."""
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "supabase",
            "migrations",
            "005_saved_searches_name_length.sql",
        )
        with open(path) as f:
            sql = f.read()
        assert "saved_searches_name_length_check" in sql
