"""API deprecation and versioning headers middleware (TD-SYS-012).

Adds standard deprecation headers (RFC 8594) and API version info
to all responses. When an endpoint is deprecated, the middleware
injects `Deprecation`, `Sunset`, and `Link` headers.
"""

import logging
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Current API version
API_VERSION = "1.0"

# Registry of deprecated endpoints.
# Format: {path_prefix: {"sunset": ISO date, "successor": new path, "link": docs URL}}
# When deprecating an endpoint, add it here.
DEPRECATED_ENDPOINTS: dict[str, dict] = {
    # Example (uncomment when actually deprecating):
    # "/auth/token": {
    #     "sunset": "2026-12-31T23:59:59Z",
    #     "successor": "/api/v1/auth/token",
    #     "link": "https://docs.descomplicita.com.br/api/migration-guide",
    # },
}


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Adds API version and deprecation headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Always include API version header
        response.headers["X-API-Version"] = API_VERSION

        # Check if this endpoint is deprecated
        path = request.url.path
        for prefix, info in DEPRECATED_ENDPOINTS.items():
            if path.startswith(prefix):
                response.headers["Deprecation"] = "true"
                if info.get("sunset"):
                    # Format as HTTP-date (RFC 7231)
                    sunset_dt = datetime.fromisoformat(info["sunset"].replace("Z", "+00:00"))
                    response.headers["Sunset"] = sunset_dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
                if info.get("link"):
                    response.headers["Link"] = f'<{info["link"]}>; rel="deprecation"'
                if info.get("successor"):
                    response.headers["X-Deprecated-Use"] = info["successor"]
                break

        return response
