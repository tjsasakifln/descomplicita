"""
Descomplicita Backend API (v3-story-2.0: Supabase Migration)

FastAPI application for searching and analyzing uniform procurement bids
from Brazil's PNCP (Portal Nacional de Contratações Públicas).

v3-story-2.0 changes:
- Supabase Auth integration (signup, login, token refresh)
- user_id attached to all search operations (DB-001 multi-tenant isolation)
- Legacy auth (custom JWT, API key) still supported during transition
"""

import asyncio
import csv
import io
import logging
import os
import signal
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from auth.jwt import JWTError, generate_token, validate_token
from auth.supabase_auth import SupabaseAuthError
from config import setup_logging, MAX_DATE_RANGE_DAYS, MAX_DOWNLOAD_SIZE
from error_codes import ErrorCode, error_response
from middleware.auth import APIKeyMiddleware
from middleware.correlation_id import CorrelationIdMiddleware
from schemas import (
    BuscaRequest,
    JobCreatedResponse,
    JobStatusResponse,
    JobResultResponse,
    JobProgress,
)
from dependencies import (
    init_dependencies,
    shutdown_dependencies,
    get_job_store,
    get_orchestrator,
    get_pncp_source,
    get_redis,
    get_redis_cache,
    get_task_runner,
    get_database,
)
from sources.base import SearchQuery
from exceptions import PNCPAPIError, PNCPRateLimitError
from filter import filter_batch
from excel import create_excel
from llm import gerar_resumo, gerar_resumo_fallback
from sectors import get_sector, list_sectors

# Configure structured logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Feature flag: streaming download (TD-C01/XD-PERF-01)
ENABLE_STREAMING_DOWNLOAD = os.getenv("ENABLE_STREAMING_DOWNLOAD", "true").lower() == "true"

# TD-L06: Dedicated thread pool for CPU-bound filter_batch, separated from default
# executor used by other tasks. Prevents thread pool starvation under load.
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
        "API para busca e análise de licitações de uniformes no PNCP. "
        "Permite filtrar oportunidades por estado, valor e keywords, "
        "gerando relatórios Excel e resumos executivos via IA."
    ),
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
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
    allow_headers=["*"],
)

# Authentication middleware (JWT + API key fallback)
app.add_middleware(APIKeyMiddleware)

# Correlation ID middleware (TD-017)
app.add_middleware(CorrelationIdMiddleware)

logger.info(
    "FastAPI application initialized — PORT=%s",
    os.getenv("PORT", "8000"),
)


# ---------------------------------------------------------------------------
# Multi-word term parsing (UXD-001)
# ---------------------------------------------------------------------------

def parse_multi_word_terms(raw: str) -> list[str]:
    """Parse search terms supporting quoted multi-word phrases and comma delimiters.

    Supports:
    - Quoted terms: "camisa polo" → camisa polo
    - Comma-separated: "camisa polo", uniforme → [camisa polo, uniforme]
    - Mixed: "camisa polo", uniforme, "calça social" → 3 terms
    - Simple space-separated (backward compat): jaleco avental → [jaleco, avental]

    Args:
        raw: Raw search terms string from user input.

    Returns:
        List of parsed terms (lowercase, stripped).
    """
    if not raw or not raw.strip():
        return []

    raw = raw.strip()

    # If input contains quotes or commas, use CSV-style parsing
    if '"' in raw or "," in raw:
        terms = []
        reader = csv.reader(io.StringIO(raw), skipinitialspace=True)
        for row in reader:
            for term in row:
                cleaned = term.strip().lower()
                if cleaned:
                    terms.append(cleaned)
        return terms

    # Fallback: space-separated (backward compatibility)
    return [t.strip().lower() for t in raw.split() if t.strip()]


# ---------------------------------------------------------------------------
# User identity helper (v3-story-2.0 / DB-001)
# ---------------------------------------------------------------------------

def get_user_id(request: Request) -> Optional[str]:
    """Extract user_id from request state (set by auth middleware).

    Returns the Supabase user UUID if authenticated via Supabase Auth,
    or None for legacy auth methods (custom JWT, API key).
    """
    return getattr(request.state, "user_id", None)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "Descomplicita API",
        "version": "0.4.0",
        "description": "API para busca de licitações de uniformes no PNCP",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "openapi": "/openapi.json",
            "auth_token": "/auth/token",
        },
        "status": "operational",
    }


@app.get("/health")
async def health(redis=Depends(get_redis)):
    """Health check endpoint with Redis status."""
    redis_status = "disconnected"
    if redis:
        try:
            await redis.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "error"

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": app.version,
        "redis": redis_status,
    }


@app.get("/setores")
async def listar_setores():
    """Return available procurement sectors for frontend dropdown."""
    return {"setores": list_sectors()}


# ---------------------------------------------------------------------------
# JWT token endpoint (TD-C02/XD-SEC-02)
# ---------------------------------------------------------------------------

@app.post("/auth/token")
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

    if api_key and request_key != api_key:
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

@app.post("/auth/signup")
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
            ErrorCode.VALIDATION_ERROR, status_code=400,
            message="Email and password are required",
        )

    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        result = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"display_name": display_name or email.split("@")[0]},
            },
        })

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
                } if result.session else None,
                "message": "Signup successful" + (
                    ". Check your email for confirmation." if not result.session else ""
                ),
            }
        else:
            raise error_response(
                ErrorCode.AUTH_INVALID_KEY, status_code=400,
                message="Signup failed",
            )
    except error_response.__class__:
        raise
    except Exception as e:
        logger.warning("Signup failed: %s", e)
        raise error_response(
            ErrorCode.INTERNAL_ERROR, status_code=500,
            message=f"Signup failed: {e}",
        )


@app.post("/auth/login")
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
            ErrorCode.VALIDATION_ERROR, status_code=400,
            message="Email and password are required",
        )

    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        result = client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })

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
                ErrorCode.AUTH_INVALID_KEY, status_code=401,
                message="Invalid credentials",
            )
    except error_response.__class__:
        raise
    except Exception as e:
        logger.warning("Login failed: %s", e)
        raise error_response(
            ErrorCode.AUTH_INVALID_KEY, status_code=401,
            message="Invalid credentials",
        )


@app.post("/auth/refresh")
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
            ErrorCode.VALIDATION_ERROR, status_code=400,
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
                ErrorCode.AUTH_INVALID_KEY, status_code=401,
                message="Invalid refresh token",
            )
    except error_response.__class__:
        raise
    except Exception as e:
        logger.warning("Token refresh failed: %s", e)
        raise error_response(
            ErrorCode.AUTH_INVALID_KEY, status_code=401,
            message="Invalid refresh token",
        )


# ---------------------------------------------------------------------------
# Debug endpoints
# ---------------------------------------------------------------------------

_debug_enabled = os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true"


@app.get("/cache/stats")
async def cache_stats(pncp_source=Depends(get_pncp_source)):
    if not _debug_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    return await pncp_source.cache_stats()


@app.post("/cache/clear")
async def cache_clear(pncp_source=Depends(get_pncp_source)):
    if not _debug_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    removed = await pncp_source.cache_clear()
    return {"cleared": removed}


@app.get("/debug/pncp-test")
async def debug_pncp_test(pncp_source=Depends(get_pncp_source)):
    if not _debug_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    import time as t
    from datetime import date, timedelta

    start = t.time()
    try:
        client = pncp_source.client
        hoje = date.today()
        tres_dias = hoje - timedelta(days=3)
        response = await client.fetch_page(
            data_inicial=tres_dias.strftime("%Y-%m-%d"),
            data_final=hoje.strftime("%Y-%m-%d"),
            modalidade=6,
            pagina=1,
            tamanho=10,
        )
        elapsed = int((t.time() - start) * 1000)
        return {
            "success": True,
            "total_registros": response.get("totalRegistros", 0),
            "items_returned": len(response.get("data", [])),
            "elapsed_ms": elapsed,
        }
    except Exception as e:
        elapsed = int((t.time() - start) * 1000)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "elapsed_ms": elapsed,
        }


# ---------------------------------------------------------------------------
# Async job-based search (SP-001.3 + TD-H02)
# ---------------------------------------------------------------------------

@app.post("/buscar", response_model=JobCreatedResponse)
@limiter.limit("10/minute")
async def buscar_licitacoes(
    request: Request,
    body: BuscaRequest,
    job_store=Depends(get_job_store),
    orchestrator=Depends(get_orchestrator),
    task_runner=Depends(get_task_runner),
    database=Depends(get_database),
):
    """Start an asynchronous procurement search job."""
    await job_store.cleanup_expired()

    if job_store.is_full:
        raise error_response(ErrorCode.TOO_MANY_JOBS, status_code=429)

    job_id = str(uuid.uuid4())
    await job_store.create(job_id)

    # v3-story-2.0: Extract user_id for multi-tenant isolation (DB-001)
    user_id = get_user_id(request)

    # TD-H04: Record search in persistent history (now with user_id)
    if database:
        await database.record_search(
            job_id=job_id,
            ufs=body.ufs,
            data_inicial=body.data_inicial,
            data_final=body.data_final,
            setor_id=body.setor_id,
            termos_busca=body.termos_busca,
            user_id=user_id,
        )

    # Enqueue via durable task runner (TD-H02) instead of asyncio.create_task
    await task_runner.enqueue(
        job_id=job_id,
        params={
            "ufs": body.ufs,
            "data_inicial": body.data_inicial,
            "data_final": body.data_final,
            "setor_id": body.setor_id,
            "termos_busca": body.termos_busca,
        },
        coro_factory=lambda: run_search_job(job_id, body, job_store, orchestrator, database),
    )

    logger.info(
        "Search job created",
        extra={"job_id": job_id, "ufs": body.ufs},
    )

    # Calculate expected duration for frontend timeout alignment
    expected_seconds = 300 + max(0, len(body.ufs) - 5) * 15

    return JSONResponse(
        content={"job_id": job_id, "status": "queued"},
        headers={"X-Expected-Duration": str(expected_seconds)},
    )


async def run_search_job(
    job_id: str,
    request: BuscaRequest,
    job_store,
    orchestrator,
    database=None,
) -> None:
    """Execute the full search pipeline as a background async task."""
    loop = asyncio.get_running_loop()
    _search_start = time.time()

    try:
        # --- Validate sector ---
        try:
            sector = get_sector(request.setor_id)
        except KeyError as e:
            await job_store.fail(job_id, f"Setor inválido: {e}")
            return

        logger.info(
            "[job=%s] Using sector: %s (%s keywords)",
            job_id, sector.name, len(sector.keywords),
        )

        # --- Parse search terms (UXD-001: multi-word support) ---
        custom_terms: list[str] = []
        if request.termos_busca and request.termos_busca.strip():
            custom_terms = parse_multi_word_terms(request.termos_busca)

        if custom_terms:
            active_keywords = set(custom_terms)
            logger.info(
                "[job=%s] Using %s custom search terms: %s",
                job_id, len(custom_terms), custom_terms,
            )
        else:
            active_keywords = set(sector.keywords)
            logger.info(
                "[job=%s] Using sector keywords (%s terms)",
                job_id, len(active_keywords),
            )

        # --- Phase: fetching ---
        enabled = orchestrator.enabled_sources
        sources_total = len(enabled)

        await job_store.update_progress(
            job_id,
            phase="fetching",
            ufs_total=len(request.ufs),
            sources_total=sources_total,
        )

        source_names = [s.source_name for s in enabled]
        logger.info(
            "[job=%s] Fetching bids from %s sources: %s",
            job_id, sources_total, source_names,
        )

        query = SearchQuery(
            data_inicial=request.data_inicial,
            data_final=request.data_final,
            ufs=request.ufs,
        )

        orch_result = await orchestrator.search_all(
            query,
            on_progress=lambda c, t: asyncio.ensure_future(
                job_store.update_progress(
                    job_id, sources_completed=c, sources_total=t,
                )
            ),
        )

        licitacoes_raw = [r.to_legacy_dict() for r in orch_result.records]

        logger.info(
            "[job=%s] Fetched %s records from %s sources (%s duplicates removed)",
            job_id, len(licitacoes_raw), len(orch_result.sources_used),
            orch_result.dedup_removed,
        )

        # --- Phase: filtering ---
        await job_store.update_progress(
            job_id, phase="filtering", items_fetched=len(licitacoes_raw)
        )

        logger.info("[job=%s] Applying filters to raw bids", job_id)

        # TD-L06: Use dedicated executor for CPU-bound filtering
        licitacoes_filtradas, stats = await loop.run_in_executor(
            _filter_executor,
            lambda: filter_batch(
                licitacoes_raw,
                ufs_selecionadas=set(request.ufs),
                valor_min=sector.valor_min,
                valor_max=sector.valor_max,
                keywords=active_keywords,
                exclusions=sector.exclusions,
                keywords_a=sector.keywords_a if not custom_terms else None,
                keywords_b=sector.keywords_b if not custom_terms else None,
                keywords_c=sector.keywords_c if not custom_terms else None,
                threshold=sector.threshold if not custom_terms else 0.6,
            ),
        )

        # Store filtered items for paginated retrieval (TD-M02)
        await job_store.store_items(job_id, licitacoes_filtradas)

        logger.info(
            "[job=%s] Filtering complete: %s/%s bids passed",
            job_id, len(licitacoes_filtradas), len(licitacoes_raw),
        )
        if stats:
            logger.info("[job=%s]   - Total processadas: %s", job_id, stats.get("total", len(licitacoes_raw)))
            logger.info("[job=%s]   - Aprovadas: %s", job_id, stats.get("aprovadas", len(licitacoes_filtradas)))
            logger.info("[job=%s]   - Rejeitadas (UF): %s", job_id, stats.get("rejeitadas_uf", 0))
            logger.info("[job=%s]   - Rejeitadas (Valor): %s", job_id, stats.get("rejeitadas_valor", 0))
            logger.info("[job=%s]   - Rejeitadas (Keyword): %s", job_id, stats.get("rejeitadas_keyword", 0))
            logger.info("[job=%s]   - Rejeitadas (Prazo): %s", job_id, stats.get("rejeitadas_prazo", 0))
            logger.info("[job=%s]   - Rejeitadas (Outros): %s", job_id, stats.get("rejeitadas_outros", 0))

        fs = {
            "rejeitadas_uf": stats.get("rejeitadas_uf", 0),
            "rejeitadas_valor": stats.get("rejeitadas_valor", 0),
            "rejeitadas_keyword": stats.get("rejeitadas_keyword", 0),
            "rejeitadas_prazo": stats.get("rejeitadas_prazo", 0),
            "rejeitadas_outros": stats.get("rejeitadas_outros", 0),
        }

        total_atas = sum(
            1 for lic in licitacoes_filtradas
            if lic.get("tipo") == "ata_registro_preco"
        )
        total_licitacoes = len(licitacoes_filtradas) - total_atas

        # --- Phase: summarizing ---
        await job_store.update_progress(
            job_id, phase="summarizing", items_filtered=len(licitacoes_filtradas)
        )

        if not licitacoes_filtradas:
            logger.info(
                "[job=%s] No bids passed filters — skipping LLM and Excel", job_id,
            )
            resumo_dict = {
                "resumo_executivo": (
                    f"Nenhuma licitação de {sector.name.lower()} encontrada "
                    f"nos estados selecionados para o período informado."
                ),
                "total_oportunidades": 0,
                "valor_total": 0.0,
                "destaques": [],
                "alerta_urgencia": None,
            }
            result = {
                "resumo": resumo_dict,
                "total_raw": len(licitacoes_raw),
                "total_filtrado": 0,
                "total_atas": 0,
                "total_licitacoes": 0,
                "filter_stats": fs,
                "sources_used": orch_result.sources_used,
                "source_stats": {
                    k: {
                        "total_fetched": v.total_fetched,
                        "after_dedup": v.after_dedup,
                        "elapsed_ms": v.elapsed_ms,
                        "status": v.status,
                        "error_message": v.error_message,
                    }
                    for k, v in orch_result.source_stats.items()
                },
                "dedup_removed": orch_result.dedup_removed,
                "truncated_combos": orch_result.truncated_combos,
                "export_limited": False,
                "excel_item_limit": None,
            }
            await job_store.complete(job_id, result)
            logger.info(
                "[job=%s] Search completed with 0 results", job_id,
                extra={"total_raw": len(licitacoes_raw), "total_filtrado": 0},
            )
            return

        # TD-H03: gerar_resumo is now async (uses AsyncOpenAI natively)
        async def _generate_resumo():
            try:
                r = await gerar_resumo(licitacoes_filtradas, sector_name=sector.name)
                logger.info("[job=%s] LLM summary generated successfully", job_id)
                return r
            except Exception as e:
                logger.warning(
                    "[job=%s] LLM generation failed, using fallback: %s",
                    job_id, e, exc_info=True,
                )
                r = gerar_resumo_fallback(licitacoes_filtradas, sector_name=sector.name)
                logger.info("[job=%s] Fallback summary generated successfully", job_id)
                return r

        # v3-story-2.2: Limit Excel to 10K items for memory safety
        from excel import EXCEL_ITEM_LIMIT
        excel_items = licitacoes_filtradas[:EXCEL_ITEM_LIMIT]
        export_limited = len(licitacoes_filtradas) > EXCEL_ITEM_LIMIT

        if export_limited:
            logger.info(
                "[job=%s] Excel limited to %d items (total: %d) — CSV available for full dataset",
                job_id, EXCEL_ITEM_LIMIT, len(licitacoes_filtradas),
            )

        def _generate_excel():
            buf = create_excel(excel_items)
            excel_bytes = buf.read()
            logger.info("[job=%s] Excel report generated (%s bytes)", job_id, len(excel_bytes))
            return excel_bytes

        logger.info("[job=%s] Generating LLM summary + Excel report in parallel", job_id)

        await job_store.update_progress(job_id, phase="generating_excel")

        # TD-H03: LLM is now fully async, Excel still runs in executor
        resumo_coro = _generate_resumo()
        excel_future = loop.run_in_executor(_filter_executor, _generate_excel)
        resumo, excel_bytes = await asyncio.gather(resumo_coro, excel_future)

        actual_total = len(licitacoes_filtradas)
        actual_valor = sum(
            lic.get("valorTotalEstimado", 0) or 0 for lic in licitacoes_filtradas
        )
        if resumo.total_oportunidades != actual_total:
            logger.warning(
                "[job=%s] LLM returned total_oportunidades=%s, overriding with actual=%s",
                job_id, resumo.total_oportunidades, actual_total,
            )
        resumo.total_oportunidades = actual_total
        resumo.valor_total = actual_valor

        resumo_dict = resumo.model_dump()

        # TD-C01/XD-PERF-01: Store Excel bytes separately to avoid memory duplication
        # Excel bytes are stored directly in Redis (not base64-encoded in JSON)
        if ENABLE_STREAMING_DOWNLOAD:
            await job_store.store_excel(job_id, excel_bytes)
        else:
            # Legacy: store in result dict (feature flag rollback)
            pass

        result = {
            "resumo": resumo_dict,
            "total_raw": len(licitacoes_raw),
            "total_filtrado": len(licitacoes_filtradas),
            "total_atas": total_atas,
            "total_licitacoes": total_licitacoes,
            "filter_stats": fs,
            "sources_used": orch_result.sources_used,
            "source_stats": {
                k: {
                    "total_fetched": v.total_fetched,
                    "after_dedup": v.after_dedup,
                    "elapsed_ms": v.elapsed_ms,
                    "status": v.status,
                    "error_message": v.error_message,
                }
                for k, v in orch_result.source_stats.items()
            },
            "dedup_removed": orch_result.dedup_removed,
            "truncated_combos": orch_result.truncated_combos,
            "export_limited": export_limited,
            "excel_item_limit": EXCEL_ITEM_LIMIT if export_limited else None,
        }

        # Legacy fallback: include excel_bytes in result if streaming is disabled
        if not ENABLE_STREAMING_DOWNLOAD:
            result["excel_bytes"] = excel_bytes

        await job_store.complete(job_id, result)

        # TD-H04: Record completion in persistent database
        if database:
            await database.complete_search(
                job_id=job_id,
                total_raw=len(licitacoes_raw),
                total_filtrado=len(licitacoes_filtradas),
                elapsed_seconds=time.time() - _search_start,
            )

        logger.info(
            "[job=%s] Search completed successfully", job_id,
            extra={
                "total_raw": len(licitacoes_raw),
                "total_filtrado": len(licitacoes_filtradas),
                "valor_total": actual_valor,
            },
        )

    except PNCPRateLimitError as e:
        logger.error("[job=%s] PNCP rate limit exceeded: %s", job_id, e, exc_info=True)
        retry_after = getattr(e, "retry_after", 60)
        err = ErrorCode.PNCP_RATE_LIMITED.to_dict(
            message=f"O PNCP está limitando requisições. Aguarde {retry_after} segundos e tente novamente.",
            details={"retry_after": retry_after},
        )
        await job_store.fail(job_id, err["error"]["message"])
        if database:
            await database.fail_search(job_id)

    except PNCPAPIError as e:
        logger.error("[job=%s] PNCP API error: %s", job_id, e, exc_info=True)
        err = ErrorCode.PNCP_UNAVAILABLE.to_dict()
        await job_store.fail(job_id, err["error"]["message"])
        if database:
            await database.fail_search(job_id)

    except Exception:
        logger.exception("[job=%s] Internal server error during search", job_id)
        err = ErrorCode.INTERNAL_ERROR.to_dict()
        await job_store.fail(job_id, err["error"]["message"])
        if database:
            await database.fail_search(job_id)


# ---------------------------------------------------------------------------
# Job polling endpoints
# ---------------------------------------------------------------------------

@app.get("/buscar/{job_id}/status", response_model=JobStatusResponse)
@limiter.limit("30/minute")
async def job_status(
    job_id: str,
    request: Request,
    job_store=Depends(get_job_store),
):
    """Return current status and progress of a search job."""
    job = await job_store.get(job_id)
    if not job:
        raise error_response(ErrorCode.JOB_NOT_FOUND, status_code=404)

    elapsed = time.time() - job.created_at
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=JobProgress(**job.progress),
        created_at=datetime.fromtimestamp(job.created_at, tz=timezone.utc).isoformat(),
        elapsed_seconds=round(elapsed, 1),
    )


@app.delete("/buscar/{job_id}")
@limiter.limit("10/minute")
async def cancel_job(
    job_id: str,
    request: Request,
    job_store=Depends(get_job_store),
    task_runner=Depends(get_task_runner),
):
    """Cancel a running search job.

    Returns 200 {"status": "cancelled"} on success.
    Returns 404 if the job does not exist.
    Returns 409 if the job has already completed or failed.
    """
    job = await job_store.get(job_id)
    if not job:
        raise error_response(ErrorCode.JOB_NOT_FOUND, status_code=404)

    if job.status in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Job already {job.status} and cannot be cancelled.",
        )

    # Cancel the asyncio task if still running
    if task_runner:
        await task_runner.cancel_job(job_id)

    # Mark job as failed with cancellation message
    await job_store.fail(job_id, "Busca cancelada pelo usuário.")

    return {"status": "cancelled"}


@app.get("/buscar/{job_id}/result", response_model=JobResultResponse)
@limiter.limit("5/minute")
async def job_result(
    job_id: str,
    request: Request,
    job_store=Depends(get_job_store),
):
    """Return the result of a completed (or failed) search job.

    Excel data is NOT included — use GET /buscar/{job_id}/download instead.
    """
    job = await job_store.get(job_id)
    if not job:
        raise error_response(ErrorCode.JOB_NOT_FOUND, status_code=404)

    if job.status == "completed":
        # Return result WITHOUT excel_bytes (use download endpoint)
        result_data = {k: v for k, v in job.result.items() if k != "excel_bytes"}
        return JSONResponse(content={"job_id": job_id, "status": "completed", **result_data})
    elif job.status == "failed":
        return JSONResponse(
            content={
                "job_id": job_id,
                "status": "failed",
                **ErrorCode.SEARCH_FAILED.to_dict(message=job.error),
            },
            status_code=500,
        )
    else:
        return JSONResponse(
            content={"job_id": job_id, "status": job.status},
            status_code=202,
        )


@app.get("/buscar/{job_id}/items")
@limiter.limit("30/minute")
async def job_items(
    job_id: str,
    request: Request,
    page: int = 1,
    page_size: int = 20,
    job_store=Depends(get_job_store),
):
    """Return paginated items from a completed search job (TD-M02)."""
    if page < 1:
        raise error_response(
            ErrorCode.VALIDATION_ERROR, status_code=400,
            message="page must be >= 1",
        )
    if page_size < 1 or page_size > 100:
        raise error_response(
            ErrorCode.VALIDATION_ERROR, status_code=400,
            message="page_size must be between 1 and 100",
        )

    job = await job_store.get(job_id)
    if not job:
        raise error_response(ErrorCode.JOB_NOT_FOUND, status_code=404)
    if job.status != "completed":
        raise error_response(ErrorCode.JOB_NOT_COMPLETED, status_code=409)

    items, total = await job_store.get_items_page(job_id, page, page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": total_pages,
    }


@app.get("/buscar/{job_id}/download")
@limiter.limit("10/minute")
async def job_download(
    job_id: str,
    request: Request,
    format: str = "xlsx",
    job_store=Depends(get_job_store),
):
    """Download the Excel/CSV file for a completed search job.

    Query params:
        format: "xlsx" (default) or "csv". CSV includes all items even
                when Excel is limited to 10K (v3-story-2.2).
    """
    job = await job_store.get(job_id)
    if not job:
        raise error_response(ErrorCode.JOB_NOT_FOUND, status_code=404)

    if job.status != "completed":
        raise error_response(ErrorCode.JOB_NOT_COMPLETED, status_code=409)

    # v3-story-2.2: CSV download — generated on-demand from Redis LIST
    if format == "csv":
        from excel import create_csv
        all_items = await job_store.get_all_items(job_id)
        if not all_items:
            raise error_response(ErrorCode.DOWNLOAD_NOT_AVAILABLE, status_code=404)
        csv_bytes = create_csv(all_items)
        filename = f"descomplicita_{job_id[:8]}.csv"

        async def _stream_csv():
            stream = BytesIO(csv_bytes)
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                yield chunk

        return StreamingResponse(
            _stream_csv(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(csv_bytes)),
            },
        )

    # Default: Excel download
    # TD-C01/XD-PERF-01: Retrieve Excel from dedicated storage (no memory duplication)
    if ENABLE_STREAMING_DOWNLOAD:
        excel_bytes = await job_store.get_excel(job_id)
    else:
        # Legacy fallback
        excel_bytes = job.result.get("excel_bytes", b"")

    if not excel_bytes:
        raise error_response(ErrorCode.DOWNLOAD_NOT_AVAILABLE, status_code=404)

    if len(excel_bytes) > MAX_DOWNLOAD_SIZE:
        raise error_response(
            ErrorCode.DOWNLOAD_TOO_LARGE, status_code=413,
            details={"max_size_mb": MAX_DOWNLOAD_SIZE // (1024 * 1024)},
        )

    filename = f"descomplicita_{job_id[:8]}.xlsx"

    # TD-H06: Chunked streaming to avoid Vercel timeout on large files.
    async def _stream_chunks():
        stream = BytesIO(excel_bytes)
        while True:
            chunk = stream.read(65536)  # 64KB chunks
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        _stream_chunks(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(excel_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# Search history endpoint (TD-H04)
# ---------------------------------------------------------------------------

@app.get("/search-history")
async def search_history(
    request: Request,
    limit: int = 20,
    database=Depends(get_database),
):
    """Return recent search history from persistent database (per-user)."""
    if not database:
        return {"searches": [], "message": "Database not configured"}
    user_id = get_user_id(request)
    searches = await database.get_recent_searches(limit=min(limit, 100), user_id=user_id)
    return {"searches": searches}


# ---------------------------------------------------------------------------
# API Versioning (TD-M06/XD-API-01)
# ---------------------------------------------------------------------------
# All routes above are mounted directly on the app for backward compatibility.
# Additionally, mount them under /api/v1/ for versioned access.
# Both /buscar and /api/v1/buscar resolve to the same handler.

v1_router = APIRouter(prefix="/api/v1")

v1_router.add_api_route("/buscar", buscar_licitacoes, methods=["POST"], response_model=JobCreatedResponse)
v1_router.add_api_route("/buscar/{job_id}/status", job_status, methods=["GET"], response_model=JobStatusResponse)
v1_router.add_api_route("/buscar/{job_id}/result", job_result, methods=["GET"], response_model=JobResultResponse)
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
