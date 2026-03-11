"""Supabase Auth integration for Descomplicita backend (v3-story-2.0 / Task 6).

Validates Supabase-issued JWTs and extracts user identity.
Supports both Supabase Auth tokens and legacy custom JWT/API key auth.

The Supabase JWT contains:
- sub: user UUID (auth.users.id)
- email: user email
- role: 'authenticated' or 'anon'
- exp: expiration timestamp
"""

import logging
import os
from typing import Optional

import jwt as pyjwt

logger = logging.getLogger(__name__)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


class SupabaseAuthError(Exception):
    """Raised when Supabase JWT validation fails."""

    pass


def validate_supabase_token(token: str) -> dict:
    """Validate a Supabase-issued JWT and return the payload.

    Args:
        token: JWT token string from Supabase Auth.

    Returns:
        Decoded payload dict with 'sub' (user_id), 'email', 'role', etc.

    Raises:
        SupabaseAuthError: If token is invalid, expired, or not a Supabase token.
    """
    secret = SUPABASE_JWT_SECRET
    if not secret:
        raise SupabaseAuthError("SUPABASE_JWT_SECRET not configured")

    try:
        payload = pyjwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except pyjwt.ExpiredSignatureError:
        raise SupabaseAuthError("Supabase token expired")
    except pyjwt.InvalidAudienceError:
        raise SupabaseAuthError("Invalid token audience (expected 'authenticated')")
    except pyjwt.InvalidTokenError as e:
        raise SupabaseAuthError(f"Invalid Supabase token: {e}")
    except Exception as e:
        raise SupabaseAuthError(f"Token decode error: {e}")

    # Validate required claims
    if not payload.get("sub"):
        raise SupabaseAuthError("Token missing 'sub' claim (user ID)")

    role = payload.get("role", "")
    if role not in ("authenticated", "service_role"):
        raise SupabaseAuthError(f"Invalid role: {role}")

    return payload


def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user_id from a Supabase JWT. Returns None on failure."""
    try:
        payload = validate_supabase_token(token)
        return payload.get("sub")
    except SupabaseAuthError:
        return None
