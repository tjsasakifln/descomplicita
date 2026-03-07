"""Unit tests for PNCP cache layer (SP-001.2)."""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from config import RetryConfig
from pncp_client import PNCPClient, CacheEntry


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_not_expired_within_ttl(self):
        entry = CacheEntry(data=[{"id": 1}], created_at=time.time(), ttl=3600)
        assert not entry.is_expired

    def test_expired_after_ttl(self):
        entry = CacheEntry(data=[{"id": 1}], created_at=time.time() - 100, ttl=50)
        assert entry.is_expired

    def test_last_accessed_defaults_to_created_at(self):
        now = time.time()
        entry = CacheEntry(data=[], created_at=now, ttl=3600)
        assert entry.last_accessed == now


class TestCacheHit:
    """Test cache hit behavior."""

    def test_cache_hit_returns_data(self):
        client = PNCPClient()
        client._cache_put("SP:6:2024-01-01:2024-01-30", [{"id": 1}, {"id": 2}])

        result = client._cache_get("SP:6:2024-01-01:2024-01-30")
        assert result == [{"id": 1}, {"id": 2}]

    def test_cache_hit_increments_counter(self):
        client = PNCPClient()
        client._cache_put("key1", [{"id": 1}])

        client._cache_get("key1")
        assert client._cache_hits == 1

    def test_cache_hit_updates_last_accessed(self):
        client = PNCPClient()
        client._cache_put("key1", [{"id": 1}])
        original_accessed = client._cache["key1"].last_accessed

        time.sleep(0.01)
        client._cache_get("key1")
        assert client._cache["key1"].last_accessed > original_accessed


class TestCacheMiss:
    """Test cache miss behavior."""

    def test_cache_miss_returns_none(self):
        client = PNCPClient()
        result = client._cache_get("nonexistent")
        assert result is None

    def test_cache_miss_increments_counter(self):
        client = PNCPClient()
        client._cache_get("nonexistent")
        assert client._cache_misses == 1

    def test_expired_entry_is_miss(self):
        client = PNCPClient()
        client._cache["key1"] = CacheEntry(
            data=[{"id": 1}], created_at=time.time() - 20000, ttl=10
        )
        result = client._cache_get("key1")
        assert result is None
        assert client._cache_misses == 1
        assert "key1" not in client._cache


class TestCacheTTLExpiration:
    """Test TTL-based cache expiration."""

    def test_ttl_default_is_4_hours(self):
        client = PNCPClient()
        assert client.cache_ttl == 4 * 3600

    def test_cache_entry_expires_after_ttl(self):
        client = PNCPClient()
        client.cache_ttl = 0.05  # 50ms for fast testing
        client._cache_put("key1", [{"id": 1}])

        # Should be a hit immediately
        assert client._cache_get("key1") is not None

        # Wait for expiry
        time.sleep(0.06)
        assert client._cache_get("key1") is None

    def test_expired_entries_cleaned_on_put(self):
        client = PNCPClient()
        # Insert expired entry
        client._cache["old"] = CacheEntry(
            data=[], created_at=time.time() - 20000, ttl=10
        )
        assert "old" in client._cache

        # Put new entry triggers cleanup
        client._cache_put("new", [{"id": 1}])
        assert "old" not in client._cache
        assert "new" in client._cache


class TestLRUEviction:
    """Test LRU eviction when cache exceeds max_cache_entries."""

    def test_lru_eviction_at_capacity(self):
        client = PNCPClient()
        client.max_cache_entries = 3

        client._cache_put("key1", [{"id": 1}])
        time.sleep(0.01)
        client._cache_put("key2", [{"id": 2}])
        time.sleep(0.01)
        client._cache_put("key3", [{"id": 3}])

        # Cache is full. Adding key4 should evict key1 (least recently accessed)
        client._cache_put("key4", [{"id": 4}])

        assert "key1" not in client._cache
        assert "key4" in client._cache
        assert len(client._cache) == 3

    def test_lru_evicts_least_recently_accessed(self):
        client = PNCPClient()
        client.max_cache_entries = 3

        client._cache_put("key1", [{"id": 1}])
        time.sleep(0.01)
        client._cache_put("key2", [{"id": 2}])
        time.sleep(0.01)
        client._cache_put("key3", [{"id": 3}])

        # Access key1 to make it recent
        time.sleep(0.01)
        client._cache_get("key1")

        # Now key2 is least recently accessed
        client._cache_put("key4", [{"id": 4}])
        assert "key2" not in client._cache
        assert "key1" in client._cache

    def test_max_entries_default_is_500(self):
        client = PNCPClient()
        assert client.max_cache_entries == 500


class TestThreadSafety:
    """Test cache thread safety with concurrent access."""

    def test_concurrent_reads_and_writes(self):
        client = PNCPClient()
        errors = []

        def writer(n):
            try:
                for i in range(50):
                    client._cache_put(f"thread{n}:key{i}", [{"id": i}])
            except Exception as e:
                errors.append(e)

        def reader(n):
            try:
                for i in range(50):
                    client._cache_get(f"thread{n}:key{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for n in range(4):
            threads.append(threading.Thread(target=writer, args=(n,)))
            threads.append(threading.Thread(target=reader, args=(n,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0

    def test_concurrent_cache_stats(self):
        client = PNCPClient()
        errors = []

        def worker():
            try:
                for i in range(20):
                    client._cache_put(f"k{i}", [])
                    client._cache_get(f"k{i}")
                    client.cache_stats()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0


class TestCacheStats:
    """Test cache_stats() method."""

    def test_empty_cache_stats(self):
        client = PNCPClient()
        stats = client.cache_stats()
        assert stats == {"entries": 0, "hits": 0, "misses": 0, "hit_ratio": 0.0}

    def test_stats_after_hits_and_misses(self):
        client = PNCPClient()
        client._cache_put("key1", [{"id": 1}])

        client._cache_get("key1")  # hit
        client._cache_get("key1")  # hit
        client._cache_get("missing")  # miss

        stats = client.cache_stats()
        assert stats["entries"] == 1
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == pytest.approx(0.667, abs=0.001)


class TestCacheClear:
    """Test cache_clear() method."""

    def test_clear_removes_all_entries(self):
        client = PNCPClient()
        client._cache_put("key1", [{"id": 1}])
        client._cache_put("key2", [{"id": 2}])

        removed = client.cache_clear()
        assert removed == 2
        assert len(client._cache) == 0

    def test_clear_resets_counters(self):
        client = PNCPClient()
        client._cache_put("key1", [{"id": 1}])
        client._cache_get("key1")
        client._cache_get("missing")

        client.cache_clear()
        stats = client.cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_clear_empty_cache(self):
        client = PNCPClient()
        removed = client.cache_clear()
        assert removed == 0


class TestCacheKey:
    """Test cache key generation."""

    def test_cache_key_with_uf(self):
        key = PNCPClient._cache_key("SP", 6, "2024-01-01", "2024-01-30")
        assert key == "SP:6:2024-01-01:2024-01-30"

    def test_cache_key_without_uf(self):
        key = PNCPClient._cache_key(None, 6, "2024-01-01", "2024-01-30")
        assert key == "ALL:6:2024-01-01:2024-01-30"

    def test_different_params_different_keys(self):
        key1 = PNCPClient._cache_key("SP", 6, "2024-01-01", "2024-01-30")
        key2 = PNCPClient._cache_key("RJ", 6, "2024-01-01", "2024-01-30")
        key3 = PNCPClient._cache_key("SP", 7, "2024-01-01", "2024-01-30")
        assert key1 != key2
        assert key1 != key3


class TestCacheIntegrationWithFetchAll:
    """Test cache integration with fetch_all pipeline."""

    @patch("pncp_client.requests.Session.get")
    def test_second_fetch_uses_cache(self, mock_get):
        """Repeated fetch_all with same params should use cache."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "data": [
                {"numeroControlePNCP": "001", "unidadeOrgao": {"ufSigla": "SP", "municipioNome": ""}, "orgaoEntidade": {"razaoSocial": ""}},
            ],
            "totalRegistros": 1,
            "totalPaginas": 1,
            "paginasRestantes": 0,
        }
        mock_get.return_value = mock_response

        client = PNCPClient()
        # First call — cache miss
        results1 = list(client.fetch_all("2024-01-01", "2024-01-30", ufs=["SP"], modalidades=[6]))
        call_count_after_first = mock_get.call_count

        # Second call — should be cache hit, no new HTTP calls
        results2 = list(client.fetch_all("2024-01-01", "2024-01-30", ufs=["SP"], modalidades=[6]))

        assert len(results1) == 1
        assert len(results2) == 1
        assert mock_get.call_count == call_count_after_first  # No new calls
        assert client._cache_hits >= 1

    @patch("pncp_client.requests.Session.get")
    def test_different_params_no_cache_hit(self, mock_get):
        """Different UFs should not share cache."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "data": [
                {"numeroControlePNCP": "001", "unidadeOrgao": {"ufSigla": "SP", "municipioNome": ""}, "orgaoEntidade": {"razaoSocial": ""}},
            ],
            "totalRegistros": 1,
            "totalPaginas": 1,
            "paginasRestantes": 0,
        }
        mock_get.return_value = mock_response

        client = PNCPClient()
        list(client.fetch_all("2024-01-01", "2024-01-30", ufs=["SP"], modalidades=[6]))
        list(client.fetch_all("2024-01-01", "2024-01-30", ufs=["RJ"], modalidades=[6]))

        # Both should make HTTP calls (different cache keys)
        assert mock_get.call_count == 2


class TestCacheEndpoints:
    """Test /cache/stats and /cache/clear API endpoints."""

    def test_cache_stats_endpoint(self, monkeypatch):
        monkeypatch.setattr("main._debug_enabled", True)
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.get("/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "hits" in data
        assert "misses" in data
        assert "hit_ratio" in data

    def test_cache_clear_endpoint(self, monkeypatch):
        monkeypatch.setattr("main._debug_enabled", True)
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.post("/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert "cleared" in data


class TestRateLimitMonitoring:
    """Test 429 rate limit monitoring (SP-001.1)."""

    @patch("pncp_client.requests.Session.get")
    @patch("time.sleep")
    def test_429_count_tracked(self, mock_sleep, mock_get):
        """Test that 429 responses are tracked."""
        mock_responses = [
            Mock(status_code=429, headers={"Retry-After": "1"}),
            Mock(status_code=200),
        ]
        mock_responses[1].json.return_value = {"data": []}
        mock_get.side_effect = mock_responses

        client = PNCPClient()
        client.fetch_page("2024-01-01", "2024-01-30", modalidade=6)

        assert client._rate_limit_count == 1
        assert client._total_fetch_count >= 1
