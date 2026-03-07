"""API key authentication middleware for Descomplicita backend."""

import os
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths that bypass authentication
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate X-API-Key header on all requests except public paths."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        api_key = os.getenv("API_KEY")

        # If no API_KEY configured, skip auth (development mode)
        if not api_key:
            return await call_next(request)

        request_key = request.headers.get("X-API-Key")

        if not request_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key. Provide X-API-Key header."},
            )

        if request_key != api_key:
            logger.warning(
                "Invalid API key attempt from %s", request.client.host if request.client else "unknown"
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key."},
            )

        return await call_next(request)
