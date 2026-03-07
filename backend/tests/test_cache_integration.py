"""
Integration tests for cache behavior via API endpoints (SP-001.5).

These tests verify that the /cache/stats and /cache/clear debug endpoints
work correctly through the DI system.

Note: Full cache hit/miss integration tests require Redis and are covered
by test_cache.py (unit tests with mock Redis).
"""

import pytest
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from main import app
from dependencies import get_pncp_source


@pytest.fixture
def http_client():
    return TestClient(app)


class TestCacheEndpointsIntegration:
    """Test cache debug endpoints via HTTP."""

    def test_cache_stats_returns_200_when_enabled(self, http_client, monkeypatch):
        """GET /cache/stats should return 200 when debug is enabled."""
        monkeypatch.setattr("main._debug_enabled", True)

        mock_source = Mock()
        mock_source.cache_stats = AsyncMock(return_value={
            "entries": 5, "hits": 10, "misses": 3, "hit_ratio": 0.77,
        })
        app.dependency_overrides[get_pncp_source] = lambda: mock_source

        response = http_client.get("/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["hits"] == 10
        assert data["misses"] == 3

        app.dependency_overrides.pop(get_pncp_source, None)

    def test_cache_clear_returns_200_when_enabled(self, http_client, monkeypatch):
        """POST /cache/clear should return 200 when debug is enabled."""
        monkeypatch.setattr("main._debug_enabled", True)

        mock_source = Mock()
        mock_source.cache_clear = AsyncMock(return_value=5)
        app.dependency_overrides[get_pncp_source] = lambda: mock_source

        response = http_client.post("/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["cleared"] == 5

        app.dependency_overrides.pop(get_pncp_source, None)

    def test_cache_stats_returns_404_when_disabled(self, http_client):
        """GET /cache/stats should return 404 when debug is disabled."""
        response = http_client.get("/cache/stats")
        assert response.status_code == 404

    def test_cache_clear_returns_404_when_disabled(self, http_client):
        """POST /cache/clear should return 404 when debug is disabled."""
        response = http_client.post("/cache/clear")
        assert response.status_code == 404
