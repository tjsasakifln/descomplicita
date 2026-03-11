"""Authentication middleware for Descomplicita backend (v3-story-2.0).

Supports three authentication methods (checked in order):
1. Supabase JWT (preferred) — validates via SUPABASE_JWT_SECRET, extracts user_id
2. Custom JWT (legacy) — stateless validation via HMAC-SHA256
3. API key (legacy fallback) — shared key via X-API-Key header

During the transition period, all three methods are accepted.
Supabase auth sets request.state.user_id for multi-tenant isolation.
"""

import hmac
import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth.jwt import JWTError, validate_token
from auth.supabase_auth import SupabaseAuthError, validate_supabase_token

logger = logging.getLogger(__name__)

# Paths that bypass authentication entirely (no request.state setup)
PUBLIC_PATHS = {
    "/health", "/docs", "/redoc", "/openapi.json",
    "/auth/token", "/auth/signup", "/auth/login", "/auth/refresh",
}

# Paths that allow anonymous access (auth is optional, user_id=None if unauthenticated)
OPTIONAL_AUTH_PATHS = {
    "/buscar", "/setores", "/search-history", "/exportar",
}

# Path prefixes that allow anonymous access (for sub-routes like /buscar/{job_id}/status)
OPTIONAL_AUTH_PREFIXES = (
    "/buscar/",
    "/search-history/",
)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate authentication on all requests except public paths.

    Checks (in order):
    1. Supabase JWT (Authorization: Bearer <supabase-token>)
    2. Custom JWT (Authorization: Bearer <custom-token>)
    3. X-API-Key header (legacy fallback)
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        path = request.url.path
        # Strip /api/v1 prefix for matching
        clean_path = path.replace("/api/v1", "") if path.startswith("/api/v1") else path
        if clean_path in PUBLIC_PATHS or clean_path == "/":
            return await call_next(request)

        # Skip auth for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        api_key = os.getenv("API_KEY")
        jwt_secret = os.getenv("JWT_SECRET")
        supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")

        # If no auth method is configured...
        if not api_key and not jwt_secret and not supabase_jwt_secret:
            # SYS-007: Fail in production if no auth is configured
            env = os.getenv("NODE_ENV", os.getenv("ENVIRONMENT", "development"))
            if env == "production":
                logger.error(
                    "FATAL: No authentication configured in production. "
                    "Set API_KEY, JWT_SECRET, or SUPABASE_JWT_SECRET."
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "Server misconfiguration: authentication not configured. "
                        "Contact system administrator."
                    },
                )

            # Dev mode: allow bypass with warning
            logger.warning("Auth bypass active — development mode only")
            request.state.user_id = None
            request.state.user_sub = "anonymous"
            request.state.auth_method = "none"
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

            # 1. Try Supabase JWT first
            if supabase_jwt_secret:
                try:
                    payload = validate_supabase_token(token)
                    request.state.user_id = payload.get("sub")
                    request.state.user_sub = payload.get("sub", "unknown")
                    request.state.user_email = payload.get("email", "")
                    request.state.auth_method = "supabase"
                    return await call_next(request)
                except SupabaseAuthError:
                    pass  # Fall through to custom JWT

            # 2. Try custom JWT
            if jwt_secret:
                try:
                    payload = validate_token(token, secret=jwt_secret)
                    request.state.user_id = None  # Custom JWT has no user_id
                    request.state.user_sub = payload.get("sub", "unknown")
                    request.state.auth_method = "jwt"
                    return await call_next(request)
                except JWTError as e:
                    # If Supabase also failed, report the error
                    if not supabase_jwt_secret:
                        logger.warning("JWT validation failed: %s", e)
                        return JSONResponse(
                            status_code=401,
                            content={"detail": f"Invalid JWT token: {e}"},
                        )

        # 3. Try API key (legacy fallback)
        request_key = request.headers.get("X-API-Key")

        if api_key and request_key:
            if hmac.compare_digest(request_key, api_key):
                request.state.user_id = None
                request.state.user_sub = "api_key_user"
                request.state.auth_method = "api_key"
                return await call_next(request)
            else:
                logger.warning(
                    "Invalid API key attempt from %s",
                    request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid API key."},
                )

        # No valid auth provided — allow anonymous for optional-auth paths
        if clean_path in OPTIONAL_AUTH_PATHS or clean_path.startswith(OPTIONAL_AUTH_PREFIXES):
            request.state.user_id = None
            request.state.user_sub = "anonymous"
            request.state.auth_method = "none"
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={
                "detail": "Authentication required. Provide Authorization: Bearer <token> or X-API-Key header."
            },
        )
