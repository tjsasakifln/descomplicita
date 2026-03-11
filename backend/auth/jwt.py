"""Stateless JWT authentication for Descomplicita backend (v3-story-3.3).

Provides JWT token generation and validation using PyJWT with HMAC-SHA256.
Supports key rotation via JWT_SECRET_PREVIOUS for zero-downtime rotations.

Environment variables:
    JWT_SECRET: Secret key for signing tokens (required in production).
    JWT_SECRET_PREVIOUS: Previous secret for key rotation (optional).
    JWT_EXPIRATION_HOURS: Token validity period in hours (default: 24).
"""

import logging
import os
from typing import Optional

import jwt as pyjwt

logger = logging.getLogger(__name__)

# Configuration from environment
JWT_SECRET: str = os.getenv("JWT_SECRET", "")
JWT_SECRET_PREVIOUS: str = os.getenv("JWT_SECRET_PREVIOUS", "")
JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
JWT_ALGORITHM: str = "HS256"
JWT_ISSUER: str = "descomplicita-api"
JWT_AUDIENCE: str = "descomplicita-client"


class JWTError(Exception):
    """Raised when JWT validation fails."""

    pass


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

    import time

    now = int(time.time())

    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + (exp_hours * 3600),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }

    try:
        return pyjwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    except Exception as e:
        raise JWTError(f"Token generation failed: {e}")


def validate_token(
    token: str,
    secret: Optional[str] = None,
) -> dict:
    """Validate and decode a JWT token.

    Supports key rotation: tries current secret first, then previous secret.

    Args:
        token: The JWT token string.
        secret: Signing secret (defaults to JWT_SECRET env var).

    Returns:
        Decoded payload dict with 'sub', 'iat', 'exp', 'iss', 'aud' fields.

    Raises:
        JWTError: If token is invalid, expired, or signature doesn't match.
    """
    secret = secret or JWT_SECRET
    if not secret:
        raise JWTError("JWT_SECRET not configured")

    secrets_to_try = [secret]
    # Add previous secret for key rotation (only when using default secret)
    if secret == JWT_SECRET and JWT_SECRET_PREVIOUS:
        secrets_to_try.append(JWT_SECRET_PREVIOUS)

    for s in secrets_to_try:
        try:
            payload = pyjwt.decode(
                token,
                s,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
            )
            return payload
        except pyjwt.ExpiredSignatureError:
            raise JWTError("Token expired")
        except pyjwt.InvalidIssuerError:
            raise JWTError("Invalid token issuer")
        except pyjwt.InvalidAudienceError:
            raise JWTError("Invalid token audience")
        except pyjwt.InvalidTokenError:
            continue

    raise JWTError("Invalid token signature")
