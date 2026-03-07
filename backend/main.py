"""
Descomplicita POC - Backend API

FastAPI application for searching and analyzing uniform procurement bids
from Brazil's PNCP (Portal Nacional de Contratações Públicas).
"""

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import setup_logging
from middleware.auth import APIKeyMiddleware
from schemas import (
    BuscaRequest,
    JobCreatedResponse,
    JobStatusResponse,
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

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
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
    version="0.3.0",
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
        content={"detail": "Rate limit exceeded. Try again later."},
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

# API key authentication middleware
app.add_middleware(APIKeyMiddleware)

logger.info(
    "FastAPI application initialized — PORT=%s",
    os.getenv("PORT", "8000"),
)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "Descomplicita API",
        "version": "0.3.0",
        "description": "API para busca de licitações de uniformes no PNCP",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "openapi": "/openapi.json",
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
        "timestamp": datetime.utcnow().isoformat(),
        "version": app.version,
        "redis": redis_status,
    }


@app.get("/setores")
async def listar_setores():
    """Return available procurement sectors for frontend dropdown."""
    return {"setores": list_sectors()}


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
# Async job-based search (SP-001.3)
# ---------------------------------------------------------------------------

@app.post("/buscar", response_model=JobCreatedResponse)
@limiter.limit("10/minute")
async def buscar_licitacoes(
    request: Request,
    body: BuscaRequest,
    job_store=Depends(get_job_store),
    orchestrator=Depends(get_orchestrator),
):
    """Start an asynchronous procurement search job."""
    await job_store.cleanup_expired()

    if job_store.is_full:
        raise HTTPException(
            status_code=429,
            detail="Muitas buscas simultâneas. Aguarde a conclusão de uma busca anterior.",
        )

    job_id = str(uuid.uuid4())
    await job_store.create(job_id)

    asyncio.create_task(run_search_job(job_id, body, job_store, orchestrator))

    logger.info(
        "Search job created",
        extra={"job_id": job_id, "ufs": body.ufs},
    )

    return JobCreatedResponse(job_id=job_id, status="queued")


async def run_search_job(
    job_id: str,
    request: BuscaRequest,
    job_store,
    orchestrator,
) -> None:
    """Execute the full search pipeline as a background async task."""
    loop = asyncio.get_event_loop()

    try:
        # --- Validate sector ---
        try:
            sector = get_sector(request.setor_id)
        except KeyError as e:
            await job_store.fail(job_id, f"Setor inválido: {e}")
            return

        logger.info(
            f"[job={job_id}] Using sector: {sector.name} "
            f"({len(sector.keywords)} keywords)"
        )

        custom_terms: list[str] = []
        if request.termos_busca and request.termos_busca.strip():
            custom_terms = [
                t.strip().lower()
                for t in request.termos_busca.strip().split()
                if t.strip()
            ]

        if custom_terms:
            active_keywords = set(custom_terms)
            logger.info(
                f"[job={job_id}] Using {len(custom_terms)} custom search terms: "
                f"{custom_terms}"
            )
        else:
            active_keywords = set(sector.keywords)
            logger.info(
                f"[job={job_id}] Using sector keywords ({len(active_keywords)} terms)"
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
            f"[job={job_id}] Fetching bids from {sources_total} sources: {source_names}"
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
            f"[job={job_id}] Fetched {len(licitacoes_raw)} records from "
            f"{len(orch_result.sources_used)} sources "
            f"({orch_result.dedup_removed} duplicates removed)"
        )

        # --- Phase: filtering ---
        await job_store.update_progress(
            job_id, phase="filtering", items_fetched=len(licitacoes_raw)
        )

        logger.info(f"[job={job_id}] Applying filters to raw bids")

        licitacoes_filtradas, stats = await loop.run_in_executor(
            None,
            lambda: filter_batch(
                licitacoes_raw,
                ufs_selecionadas=set(request.ufs),
                valor_min=sector.valor_min,
                valor_max=sector.valor_max,
                keywords=active_keywords,
                exclusions=sector.exclusions if not custom_terms else set(),
                keywords_a=sector.keywords_a if not custom_terms else None,
                keywords_b=sector.keywords_b if not custom_terms else None,
                keywords_c=sector.keywords_c if not custom_terms else None,
                threshold=sector.threshold if not custom_terms else 0.6,
            ),
        )

        logger.info(
            f"[job={job_id}] Filtering complete: "
            f"{len(licitacoes_filtradas)}/{len(licitacoes_raw)} bids passed"
        )
        if stats:
            logger.info(f"[job={job_id}]   - Total processadas: {stats.get('total', len(licitacoes_raw))}")
            logger.info(f"[job={job_id}]   - Aprovadas: {stats.get('aprovadas', len(licitacoes_filtradas))}")
            logger.info(f"[job={job_id}]   - Rejeitadas (UF): {stats.get('rejeitadas_uf', 0)}")
            logger.info(f"[job={job_id}]   - Rejeitadas (Valor): {stats.get('rejeitadas_valor', 0)}")
            logger.info(f"[job={job_id}]   - Rejeitadas (Keyword): {stats.get('rejeitadas_keyword', 0)}")
            logger.info(f"[job={job_id}]   - Rejeitadas (Prazo): {stats.get('rejeitadas_prazo', 0)}")
            logger.info(f"[job={job_id}]   - Rejeitadas (Outros): {stats.get('rejeitadas_outros', 0)}")

        if stats.get('rejeitadas_keyword', 0) > 0:
            keyword_rejected_sample = []
            for lic in licitacoes_raw[:200]:
                obj = lic.get("objetoCompra", "")
                from filter import match_keywords, KEYWORDS_UNIFORMES, KEYWORDS_EXCLUSAO
                matched, _, _score = match_keywords(obj, KEYWORDS_UNIFORMES, KEYWORDS_EXCLUSAO)
                if not matched:
                    keyword_rejected_sample.append(obj[:120])
                    if len(keyword_rejected_sample) >= 3:
                        break
            if keyword_rejected_sample:
                logger.debug(
                    f"[job={job_id}]   - Sample keyword-rejected objects: "
                    f"{keyword_rejected_sample}"
                )

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
                f"[job={job_id}] No bids passed filters — skipping LLM and Excel"
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
                "excel_bytes": b"",
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
            }
            await job_store.complete(job_id, result)
            logger.info(
                f"[job={job_id}] Search completed with 0 results",
                extra={"total_raw": len(licitacoes_raw), "total_filtrado": 0},
            )
            return

        def _generate_resumo():
            try:
                r = gerar_resumo(licitacoes_filtradas, sector_name=sector.name)
                logger.info(f"[job={job_id}] LLM summary generated successfully")
                return r
            except Exception as e:
                logger.warning(
                    f"[job={job_id}] LLM generation failed, using fallback: {e}",
                    exc_info=True,
                )
                r = gerar_resumo_fallback(licitacoes_filtradas, sector_name=sector.name)
                logger.info(f"[job={job_id}] Fallback summary generated successfully")
                return r

        def _generate_excel():
            buf = create_excel(licitacoes_filtradas)
            excel_bytes = buf.read()
            logger.info(f"[job={job_id}] Excel report generated ({len(excel_bytes)} bytes)")
            return excel_bytes

        logger.info(f"[job={job_id}] Generating LLM summary + Excel report in parallel")

        await job_store.update_progress(job_id, phase="generating_excel")

        resumo_future = loop.run_in_executor(None, _generate_resumo)
        excel_future = loop.run_in_executor(None, _generate_excel)
        resumo, excel_bytes = await asyncio.gather(resumo_future, excel_future)

        actual_total = len(licitacoes_filtradas)
        actual_valor = sum(
            lic.get("valorTotalEstimado", 0) or 0 for lic in licitacoes_filtradas
        )
        if resumo.total_oportunidades != actual_total:
            logger.warning(
                f"[job={job_id}] LLM returned total_oportunidades="
                f"{resumo.total_oportunidades}, overriding with actual={actual_total}"
            )
        resumo.total_oportunidades = actual_total
        resumo.valor_total = actual_valor

        resumo_dict = resumo.model_dump()

        result = {
            "resumo": resumo_dict,
            "excel_bytes": excel_bytes,
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
        }
        await job_store.complete(job_id, result)

        logger.info(
            f"[job={job_id}] Search completed successfully",
            extra={
                "total_raw": len(licitacoes_raw),
                "total_filtrado": len(licitacoes_filtradas),
                "valor_total": actual_valor,
            },
        )

    except PNCPRateLimitError as e:
        logger.error(f"[job={job_id}] PNCP rate limit exceeded: {e}", exc_info=True)
        retry_after = getattr(e, "retry_after", 60)
        await job_store.fail(
            job_id,
            f"O PNCP está limitando requisições. "
            f"Aguarde {retry_after} segundos e tente novamente.",
        )

    except PNCPAPIError as e:
        logger.error(f"[job={job_id}] PNCP API error: {e}", exc_info=True)
        await job_store.fail(
            job_id,
            "O Portal Nacional de Contratações (PNCP) está temporariamente "
            "indisponível ou retornou um erro. Tente novamente em alguns "
            "instantes ou reduza o número de estados selecionados.",
        )

    except Exception:
        logger.exception(f"[job={job_id}] Internal server error during search")
        await job_store.fail(
            job_id,
            "Erro interno do servidor. Tente novamente em alguns instantes.",
        )


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
        raise HTTPException(status_code=404, detail="Job not found")

    elapsed = time.time() - job.created_at
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=JobProgress(**job.progress),
        created_at=datetime.fromtimestamp(job.created_at, tz=timezone.utc).isoformat(),
        elapsed_seconds=round(elapsed, 1),
    )


@app.get("/buscar/{job_id}/result")
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
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == "completed":
        # Return result WITHOUT excel_bytes (use download endpoint)
        result_data = {k: v for k, v in job.result.items() if k != "excel_bytes"}
        return JSONResponse(content={"job_id": job_id, "status": "completed", **result_data})
    elif job.status == "failed":
        return JSONResponse(
            content={"job_id": job_id, "status": "failed", "error": job.error},
            status_code=500,
        )
    else:
        return JSONResponse(
            content={"job_id": job_id, "status": job.status},
            status_code=202,
        )


@app.get("/buscar/{job_id}/download")
@limiter.limit("10/minute")
async def job_download(
    job_id: str,
    request: Request,
    job_store=Depends(get_job_store),
):
    """Download the Excel file for a completed search job as a streaming response."""
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Job not yet completed")

    excel_bytes = job.result.get("excel_bytes", b"")
    if not excel_bytes:
        raise HTTPException(status_code=404, detail="No Excel data available")

    filename = f"descomplicita_{job_id[:8]}.xlsx"

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(excel_bytes)),
        },
    )
