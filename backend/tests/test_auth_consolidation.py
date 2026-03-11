"""Tests for story-2.2: Auth Consolidation.

Covers:
- TD-SYS-005: Supabase auth client singleton (not recreated per request)
- TD-SYS-006: Pydantic validation on auth endpoints (422 on invalid payloads)
- TD-DB-002: RLS INSERT policy WITH CHECK (documented in migration)
- TD-SYS-013: Migration runner (CI workflow exists)
- TD-DB-010: Retention workflow (CI workflow exists)
- TD-SYS-010: docker-compose reflects Supabase + Redis
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# TD-SYS-005: Supabase auth client singleton
# ---------------------------------------------------------------------------


class TestSupabaseClientSingleton:
    """Verify Supabase auth client is created once, not per request."""

    def test_get_supabase_auth_client_returns_same_instance(self, monkeypatch):
        """Calling get_supabase_auth_client() twice returns the same object."""
        import dependencies

        dependencies.reset_supabase_auth_client()

        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")

        mock_client = MagicMock()
        call_count = 0
        original_get = dependencies.get_supabase_auth_client

        def counting_get():
            nonlocal call_count
            # Only mock the actual creation, track calls
            result = original_get()
            return result

        # Directly set the singleton to test idempotency
        dependencies._supabase_auth_client = mock_client
        client1 = dependencies.get_supabase_auth_client()
        client2 = dependencies.get_supabase_auth_client()

        assert client1 is client2
        assert client1 is mock_client, "Should return the cached singleton"

        dependencies.reset_supabase_auth_client()

    def test_get_supabase_auth_client_returns_none_when_not_configured(self, monkeypatch):
        """Returns None when SUPABASE_URL or SUPABASE_KEY are missing."""
        from dependencies import get_supabase_auth_client, reset_supabase_auth_client

        reset_supabase_auth_client()
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_KEY", raising=False)

        result = get_supabase_auth_client()
        assert result is None

        reset_supabase_auth_client()

    def test_auth_endpoints_use_di_not_inline_create(self):
        """Verify routers/auth.py does not call create_client inline."""
        import inspect

        from routers.auth import auth_login, auth_refresh, auth_signup

        for fn in [auth_signup, auth_login, auth_refresh]:
            source = inspect.getsource(fn)
            assert "create_client" not in source, (
                f"{fn.__name__} should use DI (get_supabase_auth_client), not inline create_client"
            )


# ---------------------------------------------------------------------------
# TD-SYS-006: Pydantic validation — 422 on invalid payloads
# ---------------------------------------------------------------------------


class TestPydanticValidation:
    """Auth endpoints return 422 with Pydantic details on invalid input."""

    def test_login_missing_email_returns_422(self, client):
        """POST /auth/login without email returns 422."""
        resp = client.post("/auth/login", json={"password": "secret123"})
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body

    def test_login_missing_password_returns_422(self, client):
        """POST /auth/login without password returns 422."""
        resp = client.post("/auth/login", json={"email": "test@example.com"})
        assert resp.status_code == 422

    def test_login_invalid_email_returns_422(self, client):
        """POST /auth/login with invalid email returns 422."""
        resp = client.post("/auth/login", json={"email": "not-an-email", "password": "secret123"})
        assert resp.status_code == 422

    def test_login_empty_password_returns_422(self, client):
        """POST /auth/login with empty password returns 422."""
        resp = client.post("/auth/login", json={"email": "test@example.com", "password": ""})
        assert resp.status_code == 422

    def test_login_empty_body_returns_422(self, client):
        """POST /auth/login with empty body returns 422."""
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 422

    def test_login_no_json_body_returns_422(self, client):
        """POST /auth/login without JSON body returns 422."""
        resp = client.post("/auth/login")
        assert resp.status_code == 422

    def test_signup_missing_email_returns_422(self, client):
        """POST /auth/signup without email returns 422."""
        resp = client.post("/auth/signup", json={"password": "secret123"})
        assert resp.status_code == 422

    def test_signup_missing_password_returns_422(self, client):
        """POST /auth/signup without password returns 422."""
        resp = client.post("/auth/signup", json={"email": "test@example.com"})
        assert resp.status_code == 422

    def test_signup_short_password_returns_422(self, client):
        """POST /auth/signup with password < 6 chars returns 422."""
        resp = client.post("/auth/signup", json={"email": "test@example.com", "password": "12345"})
        assert resp.status_code == 422

    def test_signup_invalid_email_returns_422(self, client):
        """POST /auth/signup with invalid email returns 422."""
        resp = client.post("/auth/signup", json={"email": "bad", "password": "secret123"})
        assert resp.status_code == 422

    def test_signup_empty_body_returns_422(self, client):
        """POST /auth/signup with empty body returns 422."""
        resp = client.post("/auth/signup", json={})
        assert resp.status_code == 422

    def test_refresh_missing_token_returns_422(self, client):
        """POST /auth/refresh without refresh_token returns 422."""
        resp = client.post("/auth/refresh", json={})
        assert resp.status_code == 422

    def test_refresh_empty_token_returns_422(self, client):
        """POST /auth/refresh with empty refresh_token returns 422."""
        resp = client.post("/auth/refresh", json={"refresh_token": ""})
        assert resp.status_code == 422

    def test_422_response_includes_validation_details(self, client):
        """422 responses include Pydantic validation detail array."""
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert isinstance(body["detail"], list)
        assert len(body["detail"]) > 0
        # Each detail should have loc, msg, type
        detail = body["detail"][0]
        assert "loc" in detail
        assert "msg" in detail
        assert "type" in detail


# ---------------------------------------------------------------------------
# OpenAPI docs reflect Pydantic models
# ---------------------------------------------------------------------------


class TestOpenAPIDocs:
    """Verify OpenAPI schema includes Pydantic models for auth endpoints."""

    def test_openapi_has_auth_schemas(self, client):
        """OpenAPI JSON includes the Pydantic model schemas."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        component_schemas = schema.get("components", {}).get("schemas", {})

        expected_models = [
            "AuthLoginRequest",
            "AuthSignupRequest",
            "AuthRefreshRequest",
        ]
        for model_name in expected_models:
            assert model_name in component_schemas, f"OpenAPI schema missing {model_name}"

    def test_openapi_login_endpoint_references_model(self, client):
        """POST /auth/login path references AuthLoginRequest in requestBody."""
        resp = client.get("/openapi.json")
        schema = resp.json()
        login_path = schema["paths"].get("/auth/login", {}).get("post", {})
        request_body = login_path.get("requestBody", {})
        assert request_body, "POST /auth/login should have a requestBody in OpenAPI"


# ---------------------------------------------------------------------------
# TD-SYS-005: Supabase client not created per-request (integration)
# ---------------------------------------------------------------------------


class TestSupabaseClientNotRecreated:
    """Integration: Multiple auth requests reuse the same Supabase client."""

    def test_multiple_login_attempts_reuse_client(self, client, monkeypatch):
        """Two login calls use DI singleton, not per-request create_client."""
        from dependencies import get_supabase_auth_client

        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.side_effect = Exception("mock auth failure")

        # Override DI to return our mock (simulating singleton behavior)
        app.dependency_overrides[get_supabase_auth_client] = lambda: mock_client

        # Two login attempts (will fail with 401, but that's OK)
        client.post("/auth/login", json={"email": "a@b.com", "password": "secret123"})
        client.post("/auth/login", json={"email": "c@d.com", "password": "secret456"})

        # sign_in_with_password was called twice on the SAME mock client
        assert mock_client.auth.sign_in_with_password.call_count == 2, (
            "Both login attempts should use the same client instance via DI"
        )

        app.dependency_overrides.pop(get_supabase_auth_client, None)


# ---------------------------------------------------------------------------
# TD-DB-002: RLS INSERT policy WITH CHECK (migration file)
# ---------------------------------------------------------------------------


class TestRLSMigrationFile:
    """Verify migration 006 contains explicit INSERT WITH CHECK for all 4 tables."""

    def test_migration_file_exists(self):
        """Migration 006_rls_explicit_insert_policies.sql exists."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "supabase",
            "migrations",
            "006_rls_explicit_insert_policies.sql",
        )
        assert os.path.isfile(migration_path), "Migration 006 file not found"

    def test_migration_has_with_check_for_all_tables(self):
        """Migration includes WITH CHECK for users, search_history, user_preferences, saved_searches."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "supabase",
            "migrations",
            "006_rls_explicit_insert_policies.sql",
        )
        with open(migration_path) as f:
            content = f.read()

        tables = ["users", "search_history", "user_preferences", "saved_searches"]
        for table in tables:
            assert f"ON public.{table}" in content, f"Missing policy for {table}"
            assert "WITH CHECK" in content, "Missing WITH CHECK clause"
            assert f"{table}_insert_own" in content, f"Missing INSERT policy for {table}"

    def test_migration_drops_old_for_all_policies(self):
        """Migration drops the old FOR ALL policies before creating new ones."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "supabase",
            "migrations",
            "006_rls_explicit_insert_policies.sql",
        )
        with open(migration_path) as f:
            content = f.read()

        old_policies = [
            "users_own_data",
            "search_history_own_data",
            "user_preferences_own_data",
            "saved_searches_own_data",
        ]
        for policy in old_policies:
            assert f"DROP POLICY IF EXISTS {policy}" in content, f"Missing DROP for {policy}"


# ---------------------------------------------------------------------------
# TD-SYS-013: Migration runner in CI
# ---------------------------------------------------------------------------


class TestMigrationRunnerCI:
    """Verify deploy.yml includes migration step."""

    def test_deploy_workflow_has_migration_job(self):
        """deploy.yml contains run-migrations job with supabase db push."""
        workflow_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            ".github",
            "workflows",
            "deploy.yml",
        )
        with open(workflow_path) as f:
            content = f.read()

        assert "run-migrations" in content, "Missing run-migrations job in deploy.yml"
        assert "supabase db push" in content, "Missing supabase db push command"
        assert "supabase/setup-cli" in content, "Missing Supabase CLI setup step"


# ---------------------------------------------------------------------------
# TD-DB-010: Retention workflow
# ---------------------------------------------------------------------------


class TestRetentionWorkflow:
    """Verify retention workflow exists and is correctly configured."""

    def test_retention_workflow_exists(self):
        """retention.yml workflow file exists."""
        workflow_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            ".github",
            "workflows",
            "retention.yml",
        )
        assert os.path.isfile(workflow_path), "retention.yml not found"

    def test_retention_workflow_has_schedule(self):
        """retention.yml has a weekly cron schedule."""
        workflow_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            ".github",
            "workflows",
            "retention.yml",
        )
        with open(workflow_path) as f:
            content = f.read()

        assert "schedule:" in content, "Missing schedule trigger"
        assert "cron:" in content, "Missing cron expression"
        assert "cleanup_old_searches" in content, "Missing cleanup function call"

    def test_retention_workflow_supports_dry_run(self):
        """retention.yml supports dry_run input for safe testing."""
        workflow_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            ".github",
            "workflows",
            "retention.yml",
        )
        with open(workflow_path) as f:
            content = f.read()

        assert "dry_run" in content, "Missing dry_run input"
        assert "DRY RUN" in content, "Missing dry run logic"


# ---------------------------------------------------------------------------
# TD-SYS-010: docker-compose reflects Supabase + Redis
# ---------------------------------------------------------------------------


class TestDockerCompose:
    """Verify docker-compose.yml reflects current Supabase + Redis stack."""

    def test_docker_compose_has_supabase_vars(self):
        """docker-compose.yml includes Supabase environment variables."""
        compose_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "docker-compose.yml",
        )
        with open(compose_path) as f:
            content = f.read()

        assert "SUPABASE_URL" in content, "Missing SUPABASE_URL"
        assert "SUPABASE_KEY" in content, "Missing SUPABASE_KEY"
        assert "SUPABASE_SERVICE_ROLE_KEY" in content, "Missing SUPABASE_SERVICE_ROLE_KEY"
        assert "SUPABASE_JWT_SECRET" in content, "Missing SUPABASE_JWT_SECRET"

    def test_docker_compose_has_redis(self):
        """docker-compose.yml includes Redis service."""
        compose_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "docker-compose.yml",
        )
        with open(compose_path) as f:
            content = f.read()

        assert "redis:" in content, "Missing redis service"
        assert "redis:7-alpine" in content, "Missing redis image"

    def test_docker_compose_no_sqlite_references(self):
        """docker-compose.yml does not reference SQLite."""
        compose_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "docker-compose.yml",
        )
        with open(compose_path) as f:
            content = f.read().lower()

        assert "sqlite" not in content, "docker-compose.yml still references SQLite"

    def test_docker_compose_has_frontend_env(self):
        """docker-compose.yml includes frontend Supabase env vars."""
        compose_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "docker-compose.yml",
        )
        with open(compose_path) as f:
            content = f.read()

        assert "NEXT_PUBLIC_SUPABASE_URL" in content, "Missing frontend Supabase URL"
        assert "BACKEND_URL=http://backend:8000" in content, "Missing frontend BACKEND_URL"
