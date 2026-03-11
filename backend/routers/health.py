"""Health, root, and utility endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from dependencies import get_pncp_source, get_redis
from sectors import list_sectors

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.get("/")
async def root(request: Request):
    return {
        "name": "Descomplicita API",
        "version": request.app.version,
        "description": "API para busca de licitacoes de uniformes no PNCP",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "openapi": "/openapi.json",
            "auth_token": "/auth/token",
        },
        "status": "operational",
    }


@router.get("/health")
async def health(request: Request, redis=Depends(get_redis)):
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
        "version": request.app.version,
        "redis": redis_status,
    }


@router.get("/setores")
async def listar_setores():
    """Return available procurement sectors for frontend dropdown."""
    return {"setores": list_sectors()}


# ---------------------------------------------------------------------------
# Debug endpoints
# ---------------------------------------------------------------------------


@router.get("/cache/stats")
async def cache_stats(pncp_source=Depends(get_pncp_source)):
    import main as _main

    if not _main._debug_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    return await pncp_source.cache_stats()


@router.post("/cache/clear")
async def cache_clear(pncp_source=Depends(get_pncp_source)):
    import main as _main

    if not _main._debug_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    removed = await pncp_source.cache_clear()
    return {"cleared": removed}


@router.get("/debug/pncp-test")
async def debug_pncp_test(pncp_source=Depends(get_pncp_source)):
    import main as _main

    if not _main._debug_enabled:
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
