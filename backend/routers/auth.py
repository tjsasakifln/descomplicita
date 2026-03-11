"""Authentication endpoints (v3-story-2.0: Supabase Auth, story-2.2: Pydantic + DI).

TD-SYS-005: Supabase client via DI singleton (no per-request creation).
TD-SYS-006: Pydantic request models on all /auth/* endpoints — 422 on invalid payloads.
"""

import hmac
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from auth.jwt import generate_token
from dependencies import get_database, get_supabase_auth_client
from error_codes import ErrorCode, error_response
from rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Pydantic request/response models (TD-SYS-006 / story-2.2)
# ---------------------------------------------------------------------------


class AuthSignupRequest(BaseModel):
    """Request body for POST /auth/signup."""

    email: EmailStr
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    display_name: str = Field("", description="Display name (optional)")


class AuthLoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1, description="Password")


class AuthRefreshRequest(BaseModel):
    """Request body for POST /auth/refresh."""

    refresh_token: str = Field(..., min_length=1, description="Refresh token from login/signup")


class AuthUserResponse(BaseModel):
    """User data returned in auth responses."""

    id: str
    email: str


class AuthSessionResponse(BaseModel):
    """Session data returned in auth responses."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: str = "bearer"


class AuthSignupResponse(BaseModel):
    """Response body for POST /auth/signup."""

    user: AuthUserResponse
    session: Optional[AuthSessionResponse] = None
    message: str


class AuthLoginResponse(BaseModel):
    """Response body for POST /auth/login."""

    user: AuthUserResponse
    session: AuthSessionResponse


class AuthRefreshResponse(BaseModel):
    """Response body for POST /auth/refresh."""

    session: AuthSessionResponse


class AuthTokenResponse(BaseModel):
    """Response body for POST /auth/token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# JWT token endpoint (TD-C02/XD-SEC-02)
# ---------------------------------------------------------------------------


@router.post("/auth/token", response_model=AuthTokenResponse)
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
# Supabase Auth endpoints (v3-story-2.0 / Task 6, story-2.2: Pydantic + DI)
# ---------------------------------------------------------------------------


@router.post("/auth/signup", response_model=AuthSignupResponse)
@limiter.limit("10/minute")
async def auth_signup(
    request: Request,
    body: AuthSignupRequest,
    database=Depends(get_database),
    supabase=Depends(get_supabase_auth_client),
):
    """Register a new user via Supabase Auth."""
    if not supabase:
        raise error_response(ErrorCode.JWT_NOT_CONFIGURED, status_code=503)

    try:
        result = supabase.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
                "options": {
                    "data": {"display_name": body.display_name or body.email.split("@")[0]},
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


@router.post("/auth/login", response_model=AuthLoginResponse)
@limiter.limit("10/minute")
async def auth_login(
    request: Request,
    body: AuthLoginRequest,
    supabase=Depends(get_supabase_auth_client),
):
    """Authenticate user via Supabase Auth (email/password)."""
    if not supabase:
        raise error_response(ErrorCode.JWT_NOT_CONFIGURED, status_code=503)

    try:
        result = supabase.auth.sign_in_with_password(
            {
                "email": body.email,
                "password": body.password,
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


@router.post("/auth/refresh", response_model=AuthRefreshResponse)
@limiter.limit("10/minute")
async def auth_refresh(
    request: Request,
    body: AuthRefreshRequest,
    supabase=Depends(get_supabase_auth_client),
):
    """Refresh an expired Supabase Auth session."""
    if not supabase:
        raise error_response(ErrorCode.JWT_NOT_CONFIGURED, status_code=503)

    try:
        result = supabase.auth.refresh_session(body.refresh_token)

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
