"""Authentication endpoints (v3-story-2.0: Supabase Auth)."""

import hmac
import logging
import os

from fastapi import APIRouter, Depends, Request

from auth.jwt import generate_token
from dependencies import get_database
from error_codes import ErrorCode, error_response
from rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# JWT token endpoint (TD-C02/XD-SEC-02)
# ---------------------------------------------------------------------------


@router.post("/auth/token")
@limiter.limit("10/minute")
async def auth_token(request: Request):
    """Exchange API key for a JWT token.

    Send X-API-Key header to receive a stateless JWT Bearer token.
    The JWT can then be used for all subsequent API requests.
    """
    api_key = os.getenv("API_KEY")
    jwt_secret = os.getenv("JWT_SECRET")

    if not jwt_secret:
        raise error_response(ErrorCode.JWT_NOT_CONFIGURED, status_code=503)

    # Validate API key
    request_key = request.headers.get("X-API-Key")
    if not request_key:
        raise error_response(ErrorCode.AUTH_REQUIRED, status_code=401)

    if api_key and not hmac.compare_digest(request_key, api_key):
        raise error_response(ErrorCode.AUTH_INVALID_KEY, status_code=401)

    # Generate JWT
    subject = "api_client"
    exp_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    token = generate_token(subject=subject, secret=jwt_secret, expiration_hours=exp_hours)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": exp_hours * 3600,
    }


# ---------------------------------------------------------------------------
# Supabase Auth endpoints (v3-story-2.0 / Task 6)
# ---------------------------------------------------------------------------


@router.post("/auth/signup")
@limiter.limit("10/minute")
async def auth_signup(request: Request, database=Depends(get_database)):
    """Register a new user via Supabase Auth."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise error_response(ErrorCode.JWT_NOT_CONFIGURED, status_code=503)

    body = await request.json()
    email = body.get("email", "")
    password = body.get("password", "")
    display_name = body.get("display_name", "")

    if not email or not password:
        raise error_response(
            ErrorCode.VALIDATION_ERROR,
            status_code=400,
            message="Email and password are required",
        )

    try:
        from supabase import create_client

        client = create_client(supabase_url, supabase_key)
        result = client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {"display_name": display_name or email.split("@")[0]},
                },
            }
        )

        if result.user:
            return {
                "user": {
                    "id": str(result.user.id),
                    "email": result.user.email,
                },
                "session": {
                    "access_token": result.session.access_token if result.session else None,
                    "refresh_token": result.session.refresh_token if result.session else None,
                    "expires_in": result.session.expires_in if result.session else None,
                }
                if result.session
                else None,
                "message": "Signup successful" + (". Check your email for confirmation." if not result.session else ""),
            }
        else:
            raise error_response(
                ErrorCode.AUTH_INVALID_KEY,
                status_code=400,
                message="Signup failed",
            )
    except error_response.__class__:
        raise
    except Exception as e:
        logger.warning("Signup failed: %s", e)
        raise error_response(
            ErrorCode.INTERNAL_ERROR,
            status_code=500,
            message=f"Signup failed: {e}",
        )


@router.post("/auth/login")
@limiter.limit("10/minute")
async def auth_login(request: Request):
    """Authenticate user via Supabase Auth (email/password)."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise error_response(ErrorCode.JWT_NOT_CONFIGURED, status_code=503)

    body = await request.json()
    email = body.get("email", "")
    password = body.get("password", "")

    if not email or not password:
        raise error_response(
            ErrorCode.VALIDATION_ERROR,
            status_code=400,
            message="Email and password are required",
        )

    try:
        from supabase import create_client

        client = create_client(supabase_url, supabase_key)
        result = client.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        if result.session:
            return {
                "user": {
                    "id": str(result.user.id),
                    "email": result.user.email,
                },
                "session": {
                    "access_token": result.session.access_token,
                    "refresh_token": result.session.refresh_token,
                    "expires_in": result.session.expires_in,
                    "token_type": "bearer",
                },
            }
        else:
            raise error_response(
                ErrorCode.AUTH_INVALID_KEY,
                status_code=401,
                message="Invalid credentials",
            )
    except error_response.__class__:
        raise
    except Exception as e:
        logger.warning("Login failed: %s", e)
        raise error_response(
            ErrorCode.AUTH_INVALID_KEY,
            status_code=401,
            message="Invalid credentials",
        )


@router.post("/auth/refresh")
@limiter.limit("10/minute")
async def auth_refresh(request: Request):
    """Refresh an expired Supabase Auth session."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise error_response(ErrorCode.JWT_NOT_CONFIGURED, status_code=503)

    body = await request.json()
    refresh_token = body.get("refresh_token", "")

    if not refresh_token:
        raise error_response(
            ErrorCode.VALIDATION_ERROR,
            status_code=400,
            message="refresh_token is required",
        )

    try:
        from supabase import create_client

        client = create_client(supabase_url, supabase_key)
        result = client.auth.refresh_session(refresh_token)

        if result.session:
            return {
                "session": {
                    "access_token": result.session.access_token,
                    "refresh_token": result.session.refresh_token,
                    "expires_in": result.session.expires_in,
                    "token_type": "bearer",
                },
            }
        else:
            raise error_response(
                ErrorCode.AUTH_INVALID_KEY,
                status_code=401,
                message="Invalid refresh token",
            )
    except error_response.__class__:
        raise
    except Exception as e:
        logger.warning("Token refresh failed: %s", e)
        raise error_response(
            ErrorCode.AUTH_INVALID_KEY,
            status_code=401,
            message="Invalid refresh token",
        )
