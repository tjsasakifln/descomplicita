"""Integration tests for Supabase database layer (v3-story-2.0 / Task 11).

Tests the Database class that replaced SQLite with Supabase PostgreSQL.
Uses mocking to avoid requiring a live Supabase instance in CI.

Test coverage:
- CRUD operations for search history (with user_id isolation)
- User preferences (per-user key-value store)
- RLS validation: user A cannot see user B data
- Graceful degradation when Supabase is unavailable
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from database import Database


# ============================================================================
# Fixtures
# ============================================================================

class MockSupabaseResponse:
    """Mock Supabase API response."""
    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error


class MockTableQuery:
    """Mock Supabase table query builder (fluent API)."""

    def __init__(self, data=None):
        self._data = data or []

    def select(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def upsert(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return MockSupabaseResponse(data=self._data)


def make_mock_client(table_data=None):
    """Create a mock Supabase client with configurable table responses."""
    client = Mock()
    table_data = table_data or {}

    def mock_table(name):
        data = table_data.get(name, [])
        return MockTableQuery(data=data)

    client.table = mock_table
    return client


@pytest.fixture
def db_connected():
    """Database with a mock Supabase client (connected state)."""
    db = Database(supabase_url="https://test.supabase.co", supabase_key="test-key")
    db._client = make_mock_client()
    return db


@pytest.fixture
def db_disconnected():
    """Database without a client (disconnected state)."""
    db = Database(supabase_url="", supabase_key="")
    return db


# ============================================================================
# Connection tests
# ============================================================================

class TestDatabaseConnection:
    """Test database connection and disconnection."""

    @pytest.mark.asyncio
    async def test_connect_without_credentials_disables_persistence(self):
        """Database should gracefully disable when credentials are missing."""
        db = Database(supabase_url="", supabase_key="")
        await db.connect()
        assert db._client is None
        assert not db.is_connected

    @pytest.mark.asyncio
    async def test_close_releases_client(self, db_connected):
        """Close should release the client reference."""
        assert db_connected.is_connected
        await db_connected.close()
        assert not db_connected.is_connected

    @pytest.mark.asyncio
    async def test_is_connected_property(self, db_connected, db_disconnected):
        """is_connected should reflect client availability."""
        assert db_connected.is_connected is True
        assert db_disconnected.is_connected is False


# ============================================================================
# Search History CRUD tests
# ============================================================================

class TestSearchHistory:
    """Test search history operations with user_id isolation."""

    USER_A = "user-a-uuid"
    USER_B = "user-b-uuid"

    @pytest.mark.asyncio
    async def test_record_search_with_user_id(self, db_connected):
        """record_search should include user_id in the insert."""
        calls = []
        original_table = db_connected._client.table

        class TrackingQuery(MockTableQuery):
            def insert(self, data, **kwargs):
                calls.append(("insert", data))
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.record_search(
            job_id="job-123",
            ufs=["SP", "RJ"],
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            setor_id="vestuario",
            termos_busca="uniforme",
            user_id=self.USER_A,
        )

        assert len(calls) == 1
        insert_data = calls[0][1]
        assert insert_data["user_id"] == self.USER_A
        assert insert_data["job_id"] == "job-123"
        assert insert_data["ufs"] == ["SP", "RJ"]
        assert insert_data["setor_id"] == "vestuario"

    @pytest.mark.asyncio
    async def test_record_search_without_user_id_skips(self, db_connected):
        """record_search should skip when no user_id is provided."""
        calls = []

        class TrackingQuery(MockTableQuery):
            def insert(self, data, **kwargs):
                calls.append(data)
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.record_search(
            job_id="job-456",
            ufs=["SP"],
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            setor_id="vestuario",
            user_id=None,
        )

        assert len(calls) == 0

    @pytest.mark.asyncio
    async def test_complete_search(self, db_connected):
        """complete_search should update status and metrics."""
        calls = []

        class TrackingQuery(MockTableQuery):
            def update(self, data, **kwargs):
                calls.append(("update", data))
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.complete_search(
            job_id="job-123",
            total_raw=500,
            total_filtrado=15,
            elapsed_seconds=42.5,
        )

        assert len(calls) == 1
        update_data = calls[0][1]
        assert update_data["status"] == "completed"
        assert update_data["total_raw"] == 500
        assert update_data["total_filtrado"] == 15
        assert update_data["elapsed_seconds"] == 42.5

    @pytest.mark.asyncio
    async def test_fail_search(self, db_connected):
        """fail_search should update status to failed."""
        calls = []

        class TrackingQuery(MockTableQuery):
            def update(self, data, **kwargs):
                calls.append(("update", data))
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.fail_search(job_id="job-789")

        assert len(calls) == 1
        assert calls[0][1]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_cancel_search(self, db_connected):
        """cancel_search should update status to cancelled (TD-DB-017)."""
        calls = []

        class TrackingQuery(MockTableQuery):
            def update(self, data, **kwargs):
                calls.append(("update", data))
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.cancel_search(job_id="job-cancelled")

        assert len(calls) == 1
        assert calls[0][1]["status"] == "cancelled"
        assert "completed_at" in calls[0][1]

    @pytest.mark.asyncio
    async def test_get_recent_searches_with_user_id(self):
        """get_recent_searches should filter by user_id (multi-tenant isolation)."""
        user_a_searches = [
            {
                "job_id": "job-a1",
                "ufs": ["SP"],
                "data_inicial": "2025-01-01",
                "data_final": "2025-01-31",
                "setor_id": "vestuario",
                "termos_busca": None,
                "total_raw": 100,
                "total_filtrado": 10,
                "status": "completed",
                "created_at": "2025-01-15T12:00:00Z",
                "elapsed_seconds": 30.0,
            }
        ]

        db = Database(supabase_url="https://test.supabase.co", supabase_key="test-key")

        class UserFilteredQuery(MockTableQuery):
            def __init__(self):
                super().__init__()
                self._filters = {}

            def eq(self, field, value):
                self._filters[field] = value
                return self

            def execute(self):
                if self._filters.get("user_id") == "user-a":
                    return MockSupabaseResponse(data=user_a_searches)
                return MockSupabaseResponse(data=[])

        db._client = Mock()
        db._client.table = lambda name: UserFilteredQuery()

        # User A sees their searches
        results_a = await db.get_recent_searches(user_id="user-a")
        assert len(results_a) == 1
        assert results_a[0]["job_id"] == "job-a1"

        # User B sees nothing (RLS isolation)
        results_b = await db.get_recent_searches(user_id="user-b")
        assert len(results_b) == 0

    @pytest.mark.asyncio
    async def test_get_recent_searches_without_user_id_returns_empty(self, db_connected):
        """get_recent_searches should return empty when no user_id is provided."""
        results = await db_connected.get_recent_searches(user_id=None)
        assert results == []


# ============================================================================
# User Preferences tests
# ============================================================================

class TestUserPreferences:
    """Test user preferences operations."""

    USER_ID = "user-pref-uuid"

    @pytest.mark.asyncio
    async def test_set_preference(self, db_connected):
        """set_preference should upsert with user_id."""
        calls = []

        class TrackingQuery(MockTableQuery):
            def upsert(self, data, **kwargs):
                calls.append(("upsert", data, kwargs))
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.set_preference(
            key="theme",
            value="dark",
            user_id=self.USER_ID,
        )

        assert len(calls) == 1
        assert calls[0][1]["user_id"] == self.USER_ID
        assert calls[0][1]["key"] == "theme"

    @pytest.mark.asyncio
    async def test_set_preference_without_user_id_skips(self, db_connected):
        """set_preference should skip when no user_id."""
        calls = []

        class TrackingQuery(MockTableQuery):
            def upsert(self, data, **kwargs):
                calls.append(data)
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.set_preference(key="theme", value="dark", user_id=None)
        assert len(calls) == 0

    @pytest.mark.asyncio
    async def test_get_preference(self):
        """get_preference should return the value for a specific key."""
        db = Database(supabase_url="https://test.supabase.co", supabase_key="test-key")

        class PrefQuery(MockTableQuery):
            def __init__(self):
                super().__init__()
                self._filters = {}

            def eq(self, field, value):
                self._filters[field] = value
                return self

            def execute(self):
                if self._filters.get("key") == "theme":
                    return MockSupabaseResponse(data=[{"value": '"dark"'}])
                return MockSupabaseResponse(data=[])

        db._client = Mock()
        db._client.table = lambda name: PrefQuery()

        result = await db.get_preference(key="theme", user_id="user-123")
        assert result == "dark"

        result = await db.get_preference(key="nonexistent", user_id="user-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_preferences(self):
        """get_all_preferences should return all prefs as a dict."""
        db = Database(supabase_url="https://test.supabase.co", supabase_key="test-key")
        db._client = make_mock_client({
            "user_preferences": [
                {"key": "theme", "value": '"dark"'},
                {"key": "language", "value": '"pt-BR"'},
            ]
        })

        result = await db.get_all_preferences(user_id="user-123")
        assert result == {"theme": "dark", "language": "pt-BR"}


# ============================================================================
# Graceful degradation tests
# ============================================================================

class TestGracefulDegradation:
    """Test that all operations degrade gracefully when Supabase is unavailable."""

    @pytest.mark.asyncio
    async def test_record_search_without_client(self, db_disconnected):
        """record_search should silently skip when disconnected."""
        await db_disconnected.record_search(
            job_id="job-1",
            ufs=["SP"],
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            setor_id="vestuario",
            user_id="user-1",
        )
        # No exception raised

    @pytest.mark.asyncio
    async def test_complete_search_without_client(self, db_disconnected):
        await db_disconnected.complete_search("job-1", 100, 10, 5.0)

    @pytest.mark.asyncio
    async def test_fail_search_without_client(self, db_disconnected):
        await db_disconnected.fail_search("job-1")

    @pytest.mark.asyncio
    async def test_cancel_search_without_client(self, db_disconnected):
        await db_disconnected.cancel_search("job-1")

    @pytest.mark.asyncio
    async def test_get_recent_searches_without_client(self, db_disconnected):
        result = await db_disconnected.get_recent_searches(user_id="user-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_set_preference_without_client(self, db_disconnected):
        await db_disconnected.set_preference("key", "value", user_id="user-1")

    @pytest.mark.asyncio
    async def test_get_preference_without_client(self, db_disconnected):
        result = await db_disconnected.get_preference("key", user_id="user-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_preferences_without_client(self, db_disconnected):
        result = await db_disconnected.get_all_preferences(user_id="user-1")
        assert result == {}

    @pytest.mark.asyncio
    async def test_operations_handle_exceptions_gracefully(self, db_connected):
        """Operations should catch and log errors, not raise."""
        # Make the table method raise
        db_connected._client.table = Mock(side_effect=Exception("Connection lost"))

        await db_connected.record_search(
            job_id="job-err",
            ufs=["SP"],
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            setor_id="vestuario",
            user_id="user-1",
        )
        # No exception — error is logged

        result = await db_connected.get_recent_searches(user_id="user-1")
        assert result == []


# ============================================================================
# Auth middleware integration tests
# ============================================================================

class TestAuthMiddleware:
    """Test authentication middleware with Supabase JWT support."""

    @pytest.mark.asyncio
    async def test_supabase_jwt_validation(self):
        """Supabase JWT should be validated and user_id extracted."""
        from auth.supabase_auth import validate_supabase_token, SupabaseAuthError

        # Valid token payload structure
        mock_payload = {
            "sub": "user-uuid-123",
            "email": "test@example.com",
            "role": "authenticated",
            "exp": 9999999999,
        }

        with patch("auth.supabase_auth.SUPABASE_JWT_SECRET", "test-secret"):
            with patch("auth.supabase_auth.pyjwt.decode", return_value=mock_payload):
                result = validate_supabase_token("mock.jwt.token")
                assert result["sub"] == "user-uuid-123"
                assert result["role"] == "authenticated"

    @pytest.mark.asyncio
    async def test_supabase_jwt_invalid_role_rejected(self):
        """Tokens with non-authenticated role should be rejected."""
        from auth.supabase_auth import validate_supabase_token, SupabaseAuthError

        mock_payload = {
            "sub": "user-uuid-123",
            "role": "anon",
            "exp": 9999999999,
        }

        with patch("auth.supabase_auth.SUPABASE_JWT_SECRET", "test-secret"):
            with patch("auth.supabase_auth.pyjwt.decode", return_value=mock_payload):
                with pytest.raises(SupabaseAuthError, match="Invalid role"):
                    validate_supabase_token("mock.jwt.token")

    @pytest.mark.asyncio
    async def test_supabase_jwt_missing_sub_rejected(self):
        """Tokens without 'sub' claim should be rejected."""
        from auth.supabase_auth import validate_supabase_token, SupabaseAuthError

        mock_payload = {
            "role": "authenticated",
            "exp": 9999999999,
        }

        with patch("auth.supabase_auth.SUPABASE_JWT_SECRET", "test-secret"):
            with patch("auth.supabase_auth.pyjwt.decode", return_value=mock_payload):
                with pytest.raises(SupabaseAuthError, match="missing 'sub'"):
                    validate_supabase_token("mock.jwt.token")

    @pytest.mark.asyncio
    async def test_no_supabase_secret_raises_error(self):
        """Missing SUPABASE_JWT_SECRET should raise SupabaseAuthError."""
        from auth.supabase_auth import validate_supabase_token, SupabaseAuthError

        with patch("auth.supabase_auth.SUPABASE_JWT_SECRET", ""):
            with pytest.raises(SupabaseAuthError, match="not configured"):
                validate_supabase_token("any.token.here")


# ============================================================================
# PostgreSQL compatibility tests
# ============================================================================

class TestPostgreSQLCompatibility:
    """Verify that data types are PostgreSQL-compatible."""

    @pytest.mark.asyncio
    async def test_ufs_stored_as_array(self, db_connected):
        """UFs should be stored as a native PostgreSQL array, not JSON string."""
        calls = []

        class TrackingQuery(MockTableQuery):
            def insert(self, data, **kwargs):
                calls.append(data)
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.record_search(
            job_id="job-pg-1",
            ufs=["SP", "RJ", "MG"],
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            setor_id="vestuario",
            user_id="user-pg",
        )

        # ufs should be a list (PostgreSQL array), not a JSON string
        assert isinstance(calls[0]["ufs"], list)
        assert calls[0]["ufs"] == ["SP", "RJ", "MG"]

    @pytest.mark.asyncio
    async def test_dates_as_strings(self, db_connected):
        """Dates should be stored as ISO strings (PostgreSQL DATE compatible)."""
        calls = []

        class TrackingQuery(MockTableQuery):
            def insert(self, data, **kwargs):
                calls.append(data)
                return self

        db_connected._client.table = lambda name: TrackingQuery()

        await db_connected.record_search(
            job_id="job-pg-2",
            ufs=["SP"],
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            setor_id="vestuario",
            user_id="user-pg",
        )

        assert calls[0]["data_inicial"] == "2025-01-01"
        assert calls[0]["data_final"] == "2025-01-31"
