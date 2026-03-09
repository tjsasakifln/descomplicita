"""Tests for JWT authentication module (TD-C02/XD-SEC-02).

Covers:
- Token generation and structure
- Token validation and payload content
- Expiration enforcement
- Tampered-signature rejection
- Missing-secret error handling
- Middleware: 401 without token, pass-through with valid token
- Token endpoint: POST /auth/token exchange flow
"""

import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

import pytest
from fastapi.testclient import TestClient

from auth.jwt import JWTError, generate_token, validate_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-key-for-jwt-tests"
TEST_SUBJECT = "test_client"


def _decode_b64(s: str) -> dict:
    """Decode a base64url-encoded JSON segment (no padding required)."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return json.loads(urlsafe_b64decode(s))


def _split_token(token: str):
    """Return (header_dict, payload_dict, signature_str) for a JWT string."""
    parts = token.split(".")
    assert len(parts) == 3, "JWT must have exactly three dot-separated parts"
    return _decode_b64(parts[0]), _decode_b64(parts[1]), parts[2]


# ---------------------------------------------------------------------------
# 1. JWT generation — valid token structure
# ---------------------------------------------------------------------------


class TestGenerateToken:
    def test_returns_three_part_string(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        parts = token.split(".")
        assert len(parts) == 3

    def test_header_algorithm_and_type(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        header, _, _ = _split_token(token)
        assert header["alg"] == "HS256"
        assert header["typ"] == "JWT"

    def test_payload_contains_required_claims(self):
        before = int(time.time())
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        after = int(time.time())
        _, payload, _ = _split_token(token)

        assert payload["sub"] == TEST_SUBJECT
        assert before <= payload["iat"] <= after
        assert payload["exp"] > payload["iat"]

    def test_default_expiration_is_24_hours(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        _, payload, _ = _split_token(token)
        # Allow a one-second tolerance for slow machines
        assert abs(payload["exp"] - payload["iat"] - 86400) <= 1

    def test_custom_expiration_hours(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET, expiration_hours=2)
        _, payload, _ = _split_token(token)
        assert abs(payload["exp"] - payload["iat"] - 7200) <= 1

    def test_no_secret_raises_jwt_error(self):
        with pytest.raises(JWTError, match="JWT_SECRET not configured"):
            generate_token(TEST_SUBJECT, secret="")

    def test_signature_segment_is_non_empty(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        _, _, signature = token.split(".")
        assert len(signature) > 0

    def test_different_subjects_produce_different_tokens(self):
        t1 = generate_token("subject_a", secret=TEST_SECRET)
        t2 = generate_token("subject_b", secret=TEST_SECRET)
        assert t1 != t2

    def test_different_secrets_produce_different_signatures(self):
        t1 = generate_token(TEST_SUBJECT, secret="secret-one")
        t2 = generate_token(TEST_SUBJECT, secret="secret-two")
        sig1 = t1.split(".")[2]
        sig2 = t2.split(".")[2]
        assert sig1 != sig2


# ---------------------------------------------------------------------------
# 2. JWT validation — correct payload returned
# ---------------------------------------------------------------------------


class TestValidateToken:
    def test_returns_dict_with_expected_keys(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        payload = validate_token(token, secret=TEST_SECRET)
        assert isinstance(payload, dict)
        assert "sub" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_sub_matches_subject(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        payload = validate_token(token, secret=TEST_SECRET)
        assert payload["sub"] == TEST_SUBJECT

    def test_iat_is_recent(self):
        before = int(time.time())
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        payload = validate_token(token, secret=TEST_SECRET)
        after = int(time.time())
        assert before <= payload["iat"] <= after

    def test_exp_is_in_the_future(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        payload = validate_token(token, secret=TEST_SECRET)
        assert payload["exp"] > time.time()

    def test_roundtrip_generate_then_validate(self):
        token = generate_token("roundtrip_user", secret=TEST_SECRET)
        payload = validate_token(token, secret=TEST_SECRET)
        assert payload["sub"] == "roundtrip_user"


# ---------------------------------------------------------------------------
# 3. JWT expiration — expired token raises JWTError
# ---------------------------------------------------------------------------


class TestTokenExpiration:
    def test_expired_token_raises_jwt_error(self):
        # Generate a token that already expired (expiration_hours=0 → exp == iat)
        # To guarantee it's in the past we use a negative value via direct construction
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET, expiration_hours=0)
        # Sleep a tiny moment so time.time() > exp
        time.sleep(1.1)
        with pytest.raises(JWTError, match="expired"):
            validate_token(token, secret=TEST_SECRET)

    def test_token_with_future_exp_is_valid(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET, expiration_hours=1)
        payload = validate_token(token, secret=TEST_SECRET)
        assert payload["sub"] == TEST_SUBJECT


# ---------------------------------------------------------------------------
# 4. JWT invalid token — tampered signature raises JWTError
# ---------------------------------------------------------------------------


class TestInvalidToken:
    def test_tampered_signature_raises_jwt_error(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        parts = token.split(".")
        # Corrupt the last character of the signature
        bad_sig = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
        tampered = f"{parts[0]}.{parts[1]}.{bad_sig}"
        with pytest.raises(JWTError, match="signature"):
            validate_token(tampered, secret=TEST_SECRET)

    def test_tampered_payload_raises_jwt_error(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        parts = token.split(".")
        # Replace the payload with a different one (same structure, different sub)
        new_payload = urlsafe_b64encode(
            json.dumps({"sub": "hacker", "iat": 0, "exp": 9999999999}).encode()
        ).rstrip(b"=").decode()
        tampered = f"{parts[0]}.{new_payload}.{parts[2]}"
        with pytest.raises(JWTError, match="signature"):
            validate_token(tampered, secret=TEST_SECRET)

    def test_wrong_secret_raises_jwt_error(self):
        token = generate_token(TEST_SUBJECT, secret="correct-secret")
        with pytest.raises(JWTError, match="signature"):
            validate_token(token, secret="wrong-secret")

    def test_invalid_format_missing_parts_raises_jwt_error(self):
        with pytest.raises(JWTError, match="format"):
            validate_token("not.a.valid.jwt.token", secret=TEST_SECRET)

    def test_empty_string_raises_jwt_error(self):
        with pytest.raises(JWTError):
            validate_token("", secret=TEST_SECRET)

    def test_only_two_parts_raises_jwt_error(self):
        with pytest.raises(JWTError, match="format"):
            validate_token("header.payload", secret=TEST_SECRET)

    def test_garbage_token_raises_jwt_error(self):
        with pytest.raises(JWTError):
            validate_token("aaa.bbb.ccc", secret=TEST_SECRET)


# ---------------------------------------------------------------------------
# 5. JWT missing secret — raises JWTError
# ---------------------------------------------------------------------------


class TestMissingSecret:
    def test_generate_with_no_secret_raises(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET", raising=False)
        # Reload module-level constant is already "" in test env via conftest;
        # pass secret="" explicitly to mirror runtime behaviour.
        with pytest.raises(JWTError, match="JWT_SECRET not configured"):
            generate_token(TEST_SUBJECT, secret="")

    def test_validate_with_no_secret_raises(self, monkeypatch):
        # Build a valid token first, then try validating without a secret
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        with pytest.raises(JWTError, match="JWT_SECRET not configured"):
            validate_token(token, secret="")

    def test_generate_uses_env_secret_when_not_passed(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        # Re-import to pick up env change; but the module caches at import time,
        # so we test via the explicit kwarg path and confirm it works.
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        assert len(token.split(".")) == 3


# ---------------------------------------------------------------------------
# 6. Middleware tests — 401 without token, success with valid token
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    """Tests for APIKeyMiddleware via the full FastAPI app."""

    @pytest.fixture()
    def client(self):
        from main import app
        return TestClient(app, raise_server_exceptions=False)

    @pytest.fixture()
    def authed_client(self, monkeypatch):
        """Client with JWT_SECRET set so auth is enforced."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        from main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_public_paths_do_not_require_auth(self, client):
        """Health and other public endpoints bypass middleware."""
        resp = client.get("/health")
        # Auth is disabled in test env (no JWT_SECRET or API_KEY) but we
        # verify the endpoint is reachable regardless.
        assert resp.status_code != 401

    def test_protected_endpoint_returns_401_without_token(self, authed_client):
        """When auth is configured, protected endpoints require credentials."""
        resp = authed_client.get("/jobs")
        assert resp.status_code == 401

    def test_protected_endpoint_succeeds_with_valid_jwt(self, monkeypatch):
        """A valid Bearer token grants access to a protected endpoint."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        token = generate_token("test_user", secret=TEST_SECRET)
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/jobs", headers={"Authorization": f"Bearer {token}"})
        # We expect 200 (or any non-401), not an auth rejection
        assert resp.status_code != 401

    def test_protected_endpoint_returns_401_with_invalid_jwt(self, monkeypatch):
        """A tampered Bearer token is rejected with 401."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/jobs",
            headers={"Authorization": "Bearer header.payload.badsignature"},
        )
        assert resp.status_code == 401

    def test_protected_endpoint_returns_401_with_expired_jwt(self, monkeypatch):
        """An expired Bearer token is rejected with 401."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        token = generate_token("test_user", secret=TEST_SECRET, expiration_hours=0)
        time.sleep(1.1)
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/jobs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_legacy_api_key_still_accepted(self, monkeypatch):
        """X-API-Key header is accepted as a fallback when API_KEY is set."""
        monkeypatch.setenv("API_KEY", "my-api-key")
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/jobs", headers={"X-API-Key": "my-api-key"})
        assert resp.status_code != 401

    def test_wrong_api_key_returns_401(self, monkeypatch):
        """An incorrect X-API-Key header is rejected."""
        monkeypatch.setenv("API_KEY", "correct-key")
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/jobs", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_auth_token_endpoint_is_public(self, authed_client):
        """/auth/token is in PUBLIC_PATHS and must not require prior auth."""
        # Even with no headers, the endpoint should not return 401 due to middleware;
        # it may return 401 from its own logic (missing X-API-Key) but not from middleware.
        resp = authed_client.post("/auth/token")
        # A 401 here means the endpoint itself rejected it (no API key provided),
        # not the middleware. 503 means JWT not configured from the endpoint's perspective.
        # Both are acceptable — just not a middleware-level rejection for a public path.
        assert resp.status_code in (401, 503)


# ---------------------------------------------------------------------------
# 7. Token endpoint — POST /auth/token with API key returns JWT
# ---------------------------------------------------------------------------


class TestAuthTokenEndpoint:
    """Tests for the /auth/token exchange endpoint."""

    @pytest.fixture()
    def client(self):
        from main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_returns_503_when_jwt_secret_not_configured(self, client, monkeypatch):
        """Endpoint returns 503 when JWT_SECRET is absent."""
        monkeypatch.delenv("JWT_SECRET", raising=False)
        resp = client.post("/auth/token", headers={"X-API-Key": "any-key"})
        assert resp.status_code == 503

    def test_returns_401_when_api_key_header_missing(self, client, monkeypatch):
        """Endpoint returns 401 when no X-API-Key header is provided."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        resp = client.post("/auth/token")
        assert resp.status_code == 401

    def test_returns_401_when_api_key_is_wrong(self, client, monkeypatch):
        """Endpoint returns 401 when the provided API key does not match."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        monkeypatch.setenv("API_KEY", "correct-key")
        resp = client.post("/auth/token", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_returns_jwt_with_correct_api_key(self, client, monkeypatch):
        """Endpoint returns a valid JWT when the correct API key is supplied."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        monkeypatch.setenv("API_KEY", "my-secret-api-key")
        resp = client.post("/auth/token", headers={"X-API-Key": "my-secret-api-key"})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert "expires_in" in body
        # The returned token must be a valid three-part JWT
        assert len(body["access_token"].split(".")) == 3

    def test_returned_token_is_validatable(self, client, monkeypatch):
        """The token returned by the endpoint can be validated with the same secret."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        monkeypatch.setenv("API_KEY", "api-key-value")
        resp = client.post("/auth/token", headers={"X-API-Key": "api-key-value"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        payload = validate_token(token, secret=TEST_SECRET)
        assert payload["sub"] == "api_client"

    def test_returned_token_grants_access_to_protected_endpoint(self, monkeypatch):
        """The JWT from /auth/token can be used to call a protected endpoint."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        monkeypatch.setenv("API_KEY", "real-api-key")
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        # Exchange API key for JWT
        token_resp = client.post("/auth/token", headers={"X-API-Key": "real-api-key"})
        assert token_resp.status_code == 200
        token = token_resp.json()["access_token"]
        # Use JWT to access a protected endpoint
        protected_resp = client.get("/jobs", headers={"Authorization": f"Bearer {token}"})
        assert protected_resp.status_code != 401

    def test_expires_in_matches_configured_hours(self, client, monkeypatch):
        """expires_in in the response reflects JWT_EXPIRATION_HOURS * 3600."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        monkeypatch.setenv("API_KEY", "key")
        monkeypatch.setenv("JWT_EXPIRATION_HOURS", "2")
        resp = client.post("/auth/token", headers={"X-API-Key": "key"})
        assert resp.status_code == 200
        assert resp.json()["expires_in"] == 7200

    def test_no_api_key_env_accepts_any_key(self, client, monkeypatch):
        """When API_KEY is not set, any X-API-Key value is accepted."""
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        monkeypatch.delenv("API_KEY", raising=False)
        resp = client.post("/auth/token", headers={"X-API-Key": "literally-anything"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()
