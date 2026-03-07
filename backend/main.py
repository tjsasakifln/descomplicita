"""
BidIQ Uniformes POC - Backend API

FastAPI application for searching and analyzing uniform procurement bids
from Brazil's PNCP (Portal Nacional de Contratações Públicas).

This API provides endpoints for:
- Searching procurement opportunities by state and date range
- Filtering results by keywords and value thresholds
- Generating Excel reports with formatted data
- Creating AI-powered executive summaries (GPT-4.1-nano)
"""

import asyncio
import base64
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import setup_logging
from schemas import (
    BuscaRequest,
    BuscaResponse,
    FilterStats,
    ResumoLicitacoes,
    JobCreatedResponse,
    JobStatusResponse,
    JobResultResponse,
    JobProgress,
)
from job_store import JobStore, SearchJob
from pncp_client import PNCPClient
from sources.pncp_source import PNCPSource
from sources.base import SearchQuery
from sources.orchestrator import (
    MultiSourceOrchestrator,
    get_enabled_source_names,
)
from sources.comprasgov_source import ComprasGovSource
from sources.transparencia_source import TransparenciaSource
from sources.querido_diario_source import QueridoDiarioSource
from sources.tce_rj_source import TCERJSource
from exceptions import PNCPAPIError, PNCPRateLimitError
from filter import filter_batch
from excel import create_excel
from llm import gerar_resumo, gerar_resumo_fallback
from sectors import get_sector, list_sectors

# Configure structured logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="BidIQ Uniformes API",
    description=(
        "API para busca e análise de licitações de uniformes no PNCP. "
        "Permite filtrar oportunidades por estado, valor e keywords, "
        "gerando relatórios Excel e resumos executivos via IA."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Configuration
# NOTE: In production, restrict allow_origins to specific domains
# Example: allow_origins=["https://bidiq-uniformes.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for POC (TODO: restrict in production)
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only methods we use
    allow_headers=["*"],  # Allow all headers for development
)

logger.info(
    "FastAPI application initialized — PORT=%s",
    os.getenv("PORT", "8000"),
)


@app.get("/")
async def root():
    """
    API root endpoint - provides navigation to documentation.

    Returns:
        dict: API information and links to documentation endpoints
    """
    return {
        "name": "BidIQ Uniformes API",
        "version": "0.2.0",
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
async def health():
    """
    Health check endpoint for monitoring and load balancers.

    Provides lightweight service health verification without triggering
    heavy operations (PNCP API calls, LLM processing, etc.). Designed
    for use by orchestrators (Docker, Kubernetes), load balancers, and
    uptime monitoring tools.

    Returns:
        dict: Service health status with timestamp and version

    Response Schema:
        - status (str): "healthy" when service is operational
        - timestamp (str): Current server time in ISO 8601 format
        - version (str): API version from app configuration

    Example:
        >>> response = await health()
        >>> response
        {
            'status': 'healthy',
            'timestamp': '2026-01-25T23:15:42.123456',
            'version': '0.2.0'
        }

    HTTP Status Codes:
        - 200: Service is healthy and operational
        - 503: Service is degraded (future: dependency checks fail)
    """
    from datetime import datetime

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": app.version,
    }


# Shared PNCPSource instance for cache persistence across requests
_pncp_source: PNCPSource | None = None


def _get_pncp_source() -> PNCPSource:
    """Get or create the shared PNCPSource instance."""
    global _pncp_source
    if _pncp_source is None:
        _pncp_source = PNCPSource()
    return _pncp_source


# Backward-compatible alias used by tests and internal endpoints
def _get_pncp_client() -> PNCPClient:
    """Get the underlying PNCPClient (for cache/debug endpoints)."""
    return _get_pncp_source().client


# Shared orchestrator instance
_orchestrator: MultiSourceOrchestrator | None = None


def _get_orchestrator() -> MultiSourceOrchestrator:
    """Get or create the shared MultiSourceOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        sources = [
            _get_pncp_source(),
            ComprasGovSource(),
            TransparenciaSource(),
            QueridoDiarioSource(),
            TCERJSource(),
        ]
        _orchestrator = MultiSourceOrchestrator(sources=sources)
    return _orchestrator


# Global job store for async search jobs
_job_store = JobStore()


@app.on_event("startup")
async def startup_cleanup_task():
    """Launch periodic cleanup of expired jobs."""
    async def _periodic_cleanup():
        while True:
            await asyncio.sleep(60)
            await _job_store.cleanup_expired()
    asyncio.create_task(_periodic_cleanup())


@app.get("/setores")
async def listar_setores():
    """Return available procurement sectors for frontend dropdown."""
    return {"setores": list_sectors()}


@app.get("/cache/stats")
async def cache_stats():
    """Return cache statistics: entries, hits, misses, hit ratio."""
    client = _get_pncp_client()
    return client.cache_stats()


@app.post("/cache/clear")
async def cache_clear():
    """Clear all cache entries manually (for debug/deploy)."""
    client = _get_pncp_client()
    removed = client.cache_clear()
    return {"cleared": removed}


@app.get("/debug/pncp-test")
async def debug_pncp_test():
    """Diagnostic: test if PNCP API is reachable from this server."""
    import time as t
    from datetime import date, timedelta

    start = t.time()
    try:
        client = _get_pncp_client()
        hoje = date.today()
        tres_dias = hoje - timedelta(days=3)
        response = client.fetch_page(
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
async def buscar_licitacoes(request: BuscaRequest):
    """
    Start an asynchronous procurement search job.

    Creates a background job that executes the full search pipeline:
        1. Fetch bids from PNCP API (with automatic pagination)
        2. Apply sequential filters (UF, value, keywords, status)
        3. Generate executive summary via GPT-4.1-nano (with fallback)
        4. Create formatted Excel report

    Poll GET /buscar/{job_id}/status for progress.
    Retrieve results from GET /buscar/{job_id}/result when completed.

    Args:
        request: BuscaRequest with ufs, data_inicial, data_final

    Returns:
        JobCreatedResponse with job_id and status="queued"

    Raises:
        HTTPException 429: Too many concurrent jobs
    """
    # Run cleanup of expired jobs
    await _job_store.cleanup_expired()

    # Check capacity
    if _job_store.is_full:
        raise HTTPException(
            status_code=429,
            detail="Muitas buscas simultâneas. Aguarde a conclusão de uma busca anterior.",
        )

    # Create job
    job_id = str(uuid.uuid4())
    await _job_store.create(job_id)

    # Launch background task
    asyncio.create_task(run_search_job(job_id, request))

    logger.info(
        "Search job created",
        extra={"job_id": job_id, "ufs": request.ufs},
    )

    return JobCreatedResponse(job_id=job_id, status="queued")


async def run_search_job(job_id: str, request: BuscaRequest) -> None:
    """
    Execute the full search pipeline as a background async task.

    Mirrors the original synchronous POST /buscar logic but updates
    job progress at each phase boundary and stores the result (or error)
    in the job store.

    Phases: fetching -> filtering -> summarizing -> generating_excel -> done
    """
    loop = asyncio.get_event_loop()

    try:
        # --- Validate sector ---
        try:
            sector = get_sector(request.setor_id)
        except KeyError as e:
            await _job_store.fail(job_id, f"Setor inválido: {e}")
            return

        logger.info(
            f"[job={job_id}] Using sector: {sector.name} "
            f"({len(sector.keywords)} keywords)"
        )

        # Determine keywords: custom terms REPLACE sector keywords
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

        # --- Phase: fetching (multi-source orchestrator) ---
        orchestrator = _get_orchestrator()
        enabled = orchestrator.enabled_sources
        sources_total = len(enabled)

        await _job_store.update_progress(
            job_id,
            phase="fetching",
            ufs_total=len(request.ufs),
            sources_total=sources_total,
        )

        source_names = [s.source_name for s in enabled]
        logger.info(
            f"[job={job_id}] Fetching bids from {sources_total} sources: {source_names}"
        )

        # Use custom terms as search_terms if provided, otherwise sector's search_keywords
        if custom_terms:
            api_search_terms = custom_terms[:5]
        else:
            api_search_terms = sector.search_keywords if sector.search_keywords else None

        query = SearchQuery(
            data_inicial=request.data_inicial,
            data_final=request.data_final,
            ufs=request.ufs,
            search_terms=api_search_terms or None,
        )

        async def _on_progress(completed: int, total: int):
            await _job_store.update_progress(
                job_id,
                sources_completed=completed,
                sources_total=total,
            )

        orch_result = await orchestrator.search_all(
            query,
            on_progress=lambda c, t: asyncio.ensure_future(
                _job_store.update_progress(
                    job_id, sources_completed=c, sources_total=t,
                )
            ),
        )

        # Convert NormalizedRecords to legacy dicts for filter_batch compatibility
        licitacoes_raw = [r.to_legacy_dict() for r in orch_result.records]

        logger.info(
            f"[job={job_id}] Fetched {len(licitacoes_raw)} records from "
            f"{len(orch_result.sources_used)} sources "
            f"({orch_result.dedup_removed} duplicates removed)"
        )

        # --- Phase: filtering ---
        await _job_store.update_progress(
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

        # Diagnostic: sample of keyword-rejected items for debugging
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

        # Build filter stats dict for result
        fs = {
            "rejeitadas_uf": stats.get("rejeitadas_uf", 0),
            "rejeitadas_valor": stats.get("rejeitadas_valor", 0),
            "rejeitadas_keyword": stats.get("rejeitadas_keyword", 0),
            "rejeitadas_prazo": stats.get("rejeitadas_prazo", 0),
            "rejeitadas_outros": stats.get("rejeitadas_outros", 0),
        }

        # Count atas vs licitacoes for frontend badge
        total_atas = sum(
            1 for lic in licitacoes_filtradas
            if lic.get("tipo") == "ata_registro_preco"
        )
        total_licitacoes = len(licitacoes_filtradas) - total_atas

        # --- Phase: summarizing ---
        await _job_store.update_progress(
            job_id, phase="summarizing", items_filtered=len(licitacoes_filtradas)
        )

        # Early return if no results passed filters — skip LLM and Excel
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
                "excel_base64": "",
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
            }
            await _job_store.complete(job_id, result)
            logger.info(
                f"[job={job_id}] Search completed with 0 results",
                extra={"total_raw": len(licitacoes_raw), "total_filtrado": 0},
            )
            return

        # Steps 3+4: Generate LLM summary and Excel report in parallel
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
            b64 = base64.b64encode(buf.read()).decode("utf-8")
            logger.info(f"[job={job_id}] Excel report generated ({len(b64)} base64 chars)")
            return b64

        logger.info(f"[job={job_id}] Generating LLM summary + Excel report in parallel")

        # --- Phase: generating_excel (covers both LLM + Excel generation) ---
        await _job_store.update_progress(job_id, phase="generating_excel")

        resumo_future = loop.run_in_executor(None, _generate_resumo)
        excel_future = loop.run_in_executor(None, _generate_excel)
        resumo, excel_base64 = await asyncio.gather(resumo_future, excel_future)

        # CRITICAL: Override LLM-generated counts with actual computed values.
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

        # Convert Pydantic model to plain dict for serialization
        resumo_dict = resumo.model_dump()

        # --- Phase: done ---
        result = {
            "resumo": resumo_dict,
            "excel_base64": excel_base64,
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
        }
        await _job_store.complete(job_id, result)

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
        await _job_store.fail(
            job_id,
            f"O PNCP está limitando requisições. "
            f"Aguarde {retry_after} segundos e tente novamente.",
        )

    except PNCPAPIError as e:
        logger.error(f"[job={job_id}] PNCP API error: {e}", exc_info=True)
        await _job_store.fail(
            job_id,
            "O Portal Nacional de Contratações (PNCP) está temporariamente "
            "indisponível ou retornou um erro. Tente novamente em alguns "
            "instantes ou reduza o número de estados selecionados.",
        )

    except Exception as e:
        logger.exception(f"[job={job_id}] Internal server error during search")
        await _job_store.fail(
            job_id,
            "Erro interno do servidor. Tente novamente em alguns instantes.",
        )


# ---------------------------------------------------------------------------
# Job polling endpoints
# ---------------------------------------------------------------------------


@app.get("/buscar/{job_id}/status", response_model=JobStatusResponse)
async def job_status(job_id: str):
    """Return current status and progress of a search job."""
    job = await _job_store.get(job_id)
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
async def job_result(job_id: str):
    """Return the result of a completed (or failed) search job.

    Returns HTTP 202 if the job is still in progress.
    """
    job = await _job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == "completed":
        return JSONResponse(content={"job_id": job_id, "status": "completed", **job.result})
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
