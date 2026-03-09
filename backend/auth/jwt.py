"""Stateless JWT authentication for Descomplicita backend (TD-C02/XD-SEC-02).

Provides JWT token generation and validation using HMAC-SHA256.
Tokens are stateless — no database lookup required for validation.

Environment variables:
    JWT_SECRET: Secret key for signing tokens (required in production).
    JWT_EXPIRATION_HOURS: Token validity period in hours (default: 24).
    JWT_ALGORITHM: Signing algorithm (default: HS256).
"""

import hashlib
import hmac
import json
import logging
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration from environment
JWT_SECRET: str = os.getenv("JWT_SECRET", "")
JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
JWT_ALGORITHM: str = "HS256"


class JWTError(Exception):
    """Raised when JWT validation fails."""

    pass


def _b64_encode(data: bytes) -> str:
    """URL-safe base64 encode without padding."""
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64_decode(s: str) -> bytes:
    """URL-safe base64 decode with padding restoration."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return urlsafe_b64decode(s)


def _hmac_sign(message: str, secret: str) -> str:
    """Create HMAC-SHA256 signature."""
    return _b64_encode(
        hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    )


def generate_token(
    subject: str,
    secret: Optional[str] = None,
    expiration_hours: Optional[int] = None,
) -> str:
    """Generate a signed JWT token.

    Args:
        subject: The token subject (client ID or user identifier).
        secret: Signing secret (defaults to JWT_SECRET env var).
        expiration_hours: Token validity in hours (defaults to JWT_EXPIRATION_HOURS).

    Returns:
        Signed JWT token string.

    Raises:
        JWTError: If no secret is configured.
    """
    secret = secret or JWT_SECRET
    if not secret:
        raise JWTError("JWT_SECRET not configured")

    exp_hours = expiration_hours if expiration_hours is not None else JWT_EXPIRATION_HOURS
    now = int(time.time())

    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + (exp_hours * 3600),
    }

    header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    message = f"{header_b64}.{payload_b64}"
    signature = _hmac_sign(message, secret)

    return f"{message}.{signature}"


def validate_token(
    token: str,
    secret: Optional[str] = None,
) -> dict:
    """Validate and decode a JWT token.

    Args:
        token: The JWT token string.
        secret: Signing secret (defaults to JWT_SECRET env var).

    Returns:
        Decoded payload dict with 'sub', 'iat', 'exp' fields.

    Raises:
        JWTError: If token is invalid, expired, or signature doesn't match.
    """
    secret = secret or JWT_SECRET
    if not secret:
        raise JWTError("JWT_SECRET not configured")

    parts = token.split(".")
    if len(parts) != 3:
        raise JWTError("Invalid token format")

    header_b64, payload_b64, signature = parts

    # Verify signature
    message = f"{header_b64}.{payload_b64}"
    expected_sig = _hmac_sign(message, secret)
    if not hmac.compare_digest(signature, expected_sig):
        raise JWTError("Invalid token signature")

    # Decode header
    try:
        header = json.loads(_b64_decode(header_b64))
    except (json.JSONDecodeError, Exception) as e:
        raise JWTError(f"Invalid token header: {e}")

    if header.get("alg") != JWT_ALGORITHM:
        raise JWTError(f"Unsupported algorithm: {header.get('alg')}")

    # Decode payload
    try:
        payload = json.loads(_b64_decode(payload_b64))
    except (json.JSONDecodeError, Exception) as e:
        raise JWTError(f"Invalid token payload: {e}")

    # Check expiration
    exp = payload.get("exp")
    if exp is None:
        raise JWTError("Token missing expiration")

    if time.time() > exp:
        raise JWTError("Token expired")

    return payload
