"""Search and job management endpoints (SP-001.3 + TD-H02)."""

import logging
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from config import ENABLE_STREAMING_DOWNLOAD, MAX_DOWNLOAD_SIZE
from dependencies import (
    get_database,
    get_job_store,
    get_orchestrator,
    get_task_runner,
)
from error_codes import ErrorCode, error_response
from rate_limit import limiter
from schemas import (
    BuscaRequest,
    JobCreatedResponse,
    JobProgress,
    JobResultResponse,
    JobStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


# ---------------------------------------------------------------------------
# User identity helper (v3-story-2.0 / DB-001)
# ---------------------------------------------------------------------------


def get_user_id(request: Request) -> Optional[str]:
    """Extract user_id from request state (set by auth middleware)."""
    return getattr(request.state, "user_id", None)


# ---------------------------------------------------------------------------
# Async job-based search (SP-001.3 + TD-H02)
# ---------------------------------------------------------------------------


@router.post("/buscar", response_model=JobCreatedResponse)
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
    import main as _main  # Deferred import for monkeypatch compatibility

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
        coro_factory=lambda: _main.run_search_job(job_id, body, job_store, orchestrator, database),
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


# ---------------------------------------------------------------------------
# Job polling endpoints
# ---------------------------------------------------------------------------


@router.get("/buscar/{job_id}/status", response_model=JobStatusResponse)
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


@router.delete("/buscar/{job_id}")
@limiter.limit("10/minute")
async def cancel_job(
    job_id: str,
    request: Request,
    job_store=Depends(get_job_store),
    task_runner=Depends(get_task_runner),
    database=Depends(get_database),
):
    """Cancel a running search job.

    Returns 200 {"status": "cancelled"} on success.
    Returns 404 if the job does not exist.
    Returns 409 if the job has already completed or failed.
    """
    job = await job_store.get(job_id)
    if not job:
        raise error_response(ErrorCode.JOB_NOT_FOUND, status_code=404)

    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"Job already {job.status} and cannot be cancelled.",
        )

    # Cancel the asyncio task if still running
    if task_runner:
        await task_runner.cancel_job(job_id)

    # Mark job as cancelled (distinct from failed -- TD-DB-017)
    await job_store.cancel(job_id)

    # Propagate cancelled status to persistent DB
    if database:
        await database.cancel_search(job_id)

    return {"status": "cancelled"}


@router.get("/buscar/{job_id}/result", response_model=JobResultResponse)
@limiter.limit("5/minute")
async def job_result(
    job_id: str,
    request: Request,
    job_store=Depends(get_job_store),
):
    """Return the result of a completed (or failed) search job.

    Excel data is NOT included -- use GET /buscar/{job_id}/download instead.
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


@router.get("/buscar/{job_id}/items")
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
            ErrorCode.VALIDATION_ERROR,
            status_code=400,
            message="page must be >= 1",
        )
    if page_size < 1 or page_size > 100:
        raise error_response(
            ErrorCode.VALIDATION_ERROR,
            status_code=400,
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


@router.get("/buscar/{job_id}/download")
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

    # v3-story-2.2: CSV download -- generated on-demand from Redis LIST
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
            ErrorCode.DOWNLOAD_TOO_LARGE,
            status_code=413,
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


@router.get("/search-history")
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
