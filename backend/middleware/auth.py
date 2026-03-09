"""Authentication middleware for Descomplicita backend.

Supports two authentication methods:
1. JWT Bearer token (preferred) — stateless validation via HMAC-SHA256
2. API key (legacy fallback) — shared key via X-API-Key header

During the transition period, both methods are accepted.
"""

import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth.jwt import JWTError, validate_token

logger = logging.getLogger(__name__)

# Paths that bypass authentication
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/auth/token"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate authentication on all requests except public paths.

    Checks (in order):
    1. Authorization: Bearer <JWT> header
    2. X-API-Key header (legacy fallback)
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        path = request.url.path
        if path in PUBLIC_PATHS or path == "/":
            return await call_next(request)

        # Skip auth for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        api_key = os.getenv("API_KEY")
        jwt_secret = os.getenv("JWT_SECRET")

        # If neither auth method is configured, skip auth (development mode)
        if not api_key and not jwt_secret:
            return await call_next(request)

        # 1. Try JWT Bearer token first
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = validate_token(token, secret=jwt_secret)
                # Store user info in request state for downstream use
                request.state.user_sub = payload.get("sub", "unknown")
                request.state.auth_method = "jwt"
                return await call_next(request)
            except JWTError as e:
                logger.warning("JWT validation failed: %s", e)
                return JSONResponse(
                    status_code=401,
                    content={"detail": f"Invalid JWT token: {e}"},
                )

        # 2. Try API key (legacy fallback)
        request_key = request.headers.get("X-API-Key")

        if api_key and request_key:
            if request_key == api_key:
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

        # No valid auth provided
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Authentication required. Provide Authorization: Bearer <token> or X-API-Key header."
            },
        )
