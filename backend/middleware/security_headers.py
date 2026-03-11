"""Security headers middleware for Descomplicita backend (v3-story-3.3).

Adds Content-Security-Policy and Strict-Transport-Security headers
to all HTTP responses.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Content-Security-Policy (SYS-005)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Strict-Transport-Security (SYS-005) — 1 year + includeSubDomains
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
