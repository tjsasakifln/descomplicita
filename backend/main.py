"""Descomplicita Backend API — FastAPI application entry point.

Slim orchestration layer: app creation, middleware, lifespan, and router
registration. Business logic lives in routers/ and services/.

v3-story-2.1: Decomposed from monolithic 1238-line main.py into modular
architecture with routers (auth, health, search) and services (term_parser,
search_pipeline).
"""

import asyncio
import logging
import os
import signal
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from config import ENABLE_STREAMING_DOWNLOAD, setup_logging
from dependencies import (
    get_job_store,
    get_task_runner,
    init_dependencies,
    shutdown_dependencies,
)
from error_codes import ErrorCode
from excel import create_excel

# Re-exports for backward compatibility with test monkeypatches.
# Tests use monkeypatch.setattr("main.<name>", ...) to mock these.
from filter import filter_batch
from llm import gerar_resumo, gerar_resumo_fallback
from middleware.auth import APIKeyMiddleware
from middleware.correlation_id import CorrelationIdMiddleware
from middleware.deprecation import APIVersionMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from rate_limit import limiter
from routers.auth import auth_login, auth_refresh, auth_signup, auth_token

# Router imports
from routers.auth import router as auth_router
from routers.health import health, listar_setores
from routers.health import router as health_router
from routers.search import (
    buscar_licitacoes,
    cancel_job,
    job_download,
    job_items,
    job_result,
    job_status,
    search_history,
)
from routers.search import router as search_router
from services.search_pipeline import execute_search_pipeline
from services.term_parser import parse_multi_word_terms

# ---------------------------------------------------------------------------
# Logging, feature flags, thread pool
# ---------------------------------------------------------------------------

setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Debug endpoints flag (monkeypatched in tests)
_debug_enabled = os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true"

# TD-L06: Dedicated thread pool for CPU-bound filter_batch
_filter_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="filter")

# ---------------------------------------------------------------------------
# Sentry integration (TD-057)
# ---------------------------------------------------------------------------

_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
            ],
        )
        logger.info("Sentry initialized successfully")
    except Exception:
        logger.warning("Failed to initialize Sentry", exc_info=True)


# ---------------------------------------------------------------------------
# Lifespan context manager (TD-014)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and cleanup dependencies."""
    # Startup
    await init_dependencies()

    # Launch periodic cleanup
    job_store = get_job_store()

    async def _periodic_cleanup():
        while True:
            await asyncio.sleep(60)
            await job_store.cleanup_expired()

    cleanup_task = asyncio.create_task(_periodic_cleanup())
    logger.info("Periodic job cleanup task started")

    # --- SIGTERM graceful shutdown handler (TD-025 + TD-H02) ---
    _shutdown_event = asyncio.Event()

    def _sigterm_handler():
        logger.info("SIGTERM received — initiating graceful shutdown")
        _shutdown_event.set()

    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGTERM, _sigterm_handler)
    except NotImplementedError:
        pass  # Windows doesn't support add_signal_handler

    yield

    # Shutdown — interrupt running search jobs (TD-H02)
    task_runner = get_task_runner()
    if task_runner:
        await task_runner.shutdown(job_store=job_store)

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Flush Sentry events before exit
    if _sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.flush(timeout=5)
            logger.info("Sentry events flushed")
        except Exception:
            pass

    await shutdown_dependencies()
    logger.info("Application shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Descomplicita API",
    description=(
        "API para busca e analise de licitacoes de uniformes no PNCP. "
        "Permite filtrar oportunidades por estado, valor e keywords, "
        "gerando relatorios Excel e resumos executivos via IA."
    ),
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content=ErrorCode.RATE_LIMIT_EXCEEDED.to_dict(),
    )


# CORS Configuration
_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "https://descomplicita.vercel.app,http://localhost:3000",
)
_allowed_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Security headers (CSP + HSTS) — v3-story-3.3
app.add_middleware(SecurityHeadersMiddleware)

# API versioning and deprecation headers (TD-SYS-012)
app.add_middleware(APIVersionMiddleware)

# Authentication middleware (JWT + API key fallback)
app.add_middleware(APIKeyMiddleware)

# Correlation ID middleware (TD-017)
app.add_middleware(CorrelationIdMiddleware)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(search_router)

logger.info(
    "FastAPI application initialized — PORT=%s",
    os.getenv("PORT", "8000"),
)


# ---------------------------------------------------------------------------
# Search pipeline wrapper (monkeypatch-compatible)
# ---------------------------------------------------------------------------


async def run_search_job(
    job_id,
    request,
    job_store,
    orchestrator,
    database=None,
):
    """Thin wrapper that delegates to execute_search_pipeline.

    Resolves filter_batch, gerar_resumo, create_excel etc. from this module's
    globals at call time, so test monkeypatches on main.* take effect.
    """
    await execute_search_pipeline(
        job_id=job_id,
        request=request,
        job_store=job_store,
        orchestrator=orchestrator,
        database=database,
        filter_batch_fn=filter_batch,
        gerar_resumo_fn=gerar_resumo,
        gerar_resumo_fallback_fn=gerar_resumo_fallback,
        create_excel_fn=create_excel,
        parse_multi_word_terms_fn=parse_multi_word_terms,
        filter_executor=_filter_executor,
        enable_streaming_download=ENABLE_STREAMING_DOWNLOAD,
    )


# ---------------------------------------------------------------------------
# API Versioning (TD-M06/XD-API-01)
# ---------------------------------------------------------------------------
# All routes above are mounted directly on the app for backward compatibility.
# Additionally, mount them under /api/v1/ for versioned access.

v1_router = APIRouter(prefix="/api/v1")

v1_router.add_api_route("/buscar", buscar_licitacoes, methods=["POST"])
v1_router.add_api_route("/buscar/{job_id}/status", job_status, methods=["GET"])
v1_router.add_api_route("/buscar/{job_id}/result", job_result, methods=["GET"])
v1_router.add_api_route("/buscar/{job_id}/items", job_items, methods=["GET"])
v1_router.add_api_route("/buscar/{job_id}/download", job_download, methods=["GET"])
v1_router.add_api_route("/buscar/{job_id}", cancel_job, methods=["DELETE"])
v1_router.add_api_route("/setores", listar_setores, methods=["GET"])
v1_router.add_api_route("/health", health, methods=["GET"])
v1_router.add_api_route("/auth/token", auth_token, methods=["POST"])
v1_router.add_api_route("/auth/signup", auth_signup, methods=["POST"])
v1_router.add_api_route("/auth/login", auth_login, methods=["POST"])
v1_router.add_api_route("/auth/refresh", auth_refresh, methods=["POST"])
v1_router.add_api_route("/search-history", search_history, methods=["GET"])

app.include_router(v1_router)
