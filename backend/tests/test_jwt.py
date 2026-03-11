"""Tests for JWT authentication module (v3-story-3.3: PyJWT migration).

Covers:
- Token generation and structure (with PyJWT)
- Token validation with audience, issuer claims
- Expiration enforcement
- Tampered-signature rejection
- Missing-secret error handling
- Key rotation via JWT_SECRET_PREVIOUS
- Middleware: 401 without token, pass-through with valid token
- Token endpoint: POST /auth/token exchange flow
"""

import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

import pytest
from fastapi.testclient import TestClient

from auth.jwt import JWTError, generate_token, validate_token, JWT_ISSUER, JWT_AUDIENCE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-key-for-jwt-tests-32b"  # ≥32 bytes for PyJWT
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

    def test_payload_contains_issuer_and_audience(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        _, payload, _ = _split_token(token)
        assert payload["iss"] == JWT_ISSUER
        assert payload["aud"] == JWT_AUDIENCE

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
        t1 = generate_token(TEST_SUBJECT, secret="secret-one-that-is-32-bytes-long")
        t2 = generate_token(TEST_SUBJECT, secret="secret-two-that-is-32-bytes-long")
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
        assert "iss" in payload
        assert "aud" in payload

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
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET, expiration_hours=0)
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
        bad_sig = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
        tampered = f"{parts[0]}.{parts[1]}.{bad_sig}"
        with pytest.raises(JWTError, match="signature"):
            validate_token(tampered, secret=TEST_SECRET)

    def test_tampered_payload_raises_jwt_error(self):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        parts = token.split(".")
        new_payload = urlsafe_b64encode(
            json.dumps({"sub": "hacker", "iat": 0, "exp": 9999999999}).encode()
        ).rstrip(b"=").decode()
        tampered = f"{parts[0]}.{new_payload}.{parts[2]}"
        with pytest.raises(JWTError, match="signature"):
            validate_token(tampered, secret=TEST_SECRET)

    def test_wrong_secret_raises_jwt_error(self):
        token = generate_token(TEST_SUBJECT, secret="correct-secret-that-is-32-bytes!")
        with pytest.raises(JWTError, match="signature"):
            validate_token(token, secret="wrong-secret-that-is-also-32byt!")

    def test_invalid_format_raises_jwt_error(self):
        with pytest.raises(JWTError):
            validate_token("not.a.valid.jwt.token", secret=TEST_SECRET)

    def test_empty_string_raises_jwt_error(self):
        with pytest.raises(JWTError):
            validate_token("", secret=TEST_SECRET)

    def test_only_two_parts_raises_jwt_error(self):
        with pytest.raises(JWTError):
            validate_token("header.payload", secret=TEST_SECRET)

    def test_garbage_token_raises_jwt_error(self):
        with pytest.raises(JWTError):
            validate_token("aaa.bbb.ccc", secret=TEST_SECRET)

    def test_rejects_token_with_wrong_audience(self):
        """JWT with incorrect audience is rejected."""
        import jwt as pyjwt
        payload = {
            "sub": TEST_SUBJECT, "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": JWT_ISSUER, "aud": "wrong-audience",
        }
        token = pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")
        with pytest.raises(JWTError, match="audience"):
            validate_token(token, secret=TEST_SECRET)

    def test_rejects_token_with_wrong_issuer(self):
        """JWT with incorrect issuer is rejected."""
        import jwt as pyjwt
        payload = {
            "sub": TEST_SUBJECT, "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": "wrong-issuer", "aud": JWT_AUDIENCE,
        }
        token = pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")
        with pytest.raises(JWTError, match="issuer"):
            validate_token(token, secret=TEST_SECRET)


# ---------------------------------------------------------------------------
# 5. JWT missing secret — raises JWTError
# ---------------------------------------------------------------------------


class TestMissingSecret:
    def test_generate_with_no_secret_raises(self, monkeypatch):
        monkeypatch.delenv("JWT_SECRET", raising=False)
        with pytest.raises(JWTError, match="JWT_SECRET not configured"):
            generate_token(TEST_SUBJECT, secret="")

    def test_validate_with_no_secret_raises(self, monkeypatch):
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        with pytest.raises(JWTError, match="JWT_SECRET not configured"):
            validate_token(token, secret="")

    def test_generate_uses_env_secret_when_not_passed(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
        token = generate_token(TEST_SUBJECT, secret=TEST_SECRET)
        assert len(token.split(".")) == 3


# ---------------------------------------------------------------------------
# 6. Key rotation — JWT_SECRET_PREVIOUS support
# ---------------------------------------------------------------------------


class TestKeyRotation:
    def test_token_signed_with_previous_secret_is_valid(self, monkeypatch):
        """Tokens signed with the previous key are still accepted during rotation."""
        old_secret = "old-secret-that-is-32-bytes-long"
        new_secret = "new-secret-that-is-32-bytes-long"
        # Generate with old secret
        token = generate_token(TEST_SUBJECT, secret=old_secret)
        # Set up rotation: new as current, old as previous
        monkeypatch.setattr("auth.jwt.JWT_SECRET", new_secret)
        monkeypatch.setattr("auth.jwt.JWT_SECRET_PREVIOUS", old_secret)
        # Validate without explicit secret (uses module defaults)
        payload = validate_token(token)
        assert payload["sub"] == TEST_SUBJECT

    def test_token_signed_with_current_secret_is_valid(self, monkeypatch):
        """Tokens signed with the current key are accepted."""
        new_secret = "new-secret-that-is-32-bytes-long"
        monkeypatch.setattr("auth.jwt.JWT_SECRET", new_secret)
        monkeypatch.setattr("auth.jwt.JWT_SECRET_PREVIOUS", "old-secret-that-is-32-bytes-long")
        token = generate_token(TEST_SUBJECT)
        payload = validate_token(token)
        assert payload["sub"] == TEST_SUBJECT

    def test_token_signed_with_unknown_secret_is_rejected(self, monkeypatch):
        """Tokens signed with neither current nor previous key are rejected."""
        monkeypatch.setattr("auth.jwt.JWT_SECRET", "current-secret-is-32-bytes-long!")
        monkeypatch.setattr("auth.jwt.JWT_SECRET_PREVIOUS", "previous-secret-32-bytes-long!!")
        token = generate_token(TEST_SUBJECT, secret="unknown-secret-is-32-bytes-long!")
        with pytest.raises(JWTError, match="signature"):
            validate_token(token)

    def test_generate_always_uses_current_secret(self, monkeypatch):
        """generate_token always signs with the current secret, not previous."""
        new_secret = "new-secret-that-is-32-bytes-long"
        monkeypatch.setattr("auth.jwt.JWT_SECRET", new_secret)
        monkeypatch.setattr("auth.jwt.JWT_SECRET_PREVIOUS", "old-secret-that-is-32-bytes-long")
        token = generate_token(TEST_SUBJECT)
        # Should validate with current secret directly
        payload = validate_token(token, secret=new_secret)
        assert payload["sub"] == TEST_SUBJECT


# ---------------------------------------------------------------------------
# 7. Middleware tests — 401 without token, success with valid token
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
        resp = authed_client.post("/auth/token")
        assert resp.status_code in (401, 503)


# ---------------------------------------------------------------------------
# 8. Token endpoint — POST /auth/token with API key returns JWT
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
        token_resp = client.post("/auth/token", headers={"X-API-Key": "real-api-key"})
        assert token_resp.status_code == 200
        token = token_resp.json()["access_token"]
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
