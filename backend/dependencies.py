"""FastAPI dependency injection providers (TD-013)."""

import asyncio
import logging
import os
from typing import Optional

from clients.async_pncp_client import AsyncPNCPClient
from sources.pncp_source import PNCPSource
from sources.transparencia_source import TransparenciaSource
from sources.orchestrator import MultiSourceOrchestrator
from task_queue import DurableTaskRunner

logger = logging.getLogger(__name__)

# Application state — initialized in lifespan, accessed via dependency functions
_redis = None
_job_store = None
_pncp_client = None
_pncp_source = None
_orchestrator = None
_redis_cache = None
_task_runner = None


async def init_dependencies() -> None:
    """Initialize all application dependencies. Called from lifespan startup."""
    global _redis, _job_store, _pncp_client, _pncp_source, _orchestrator, _redis_cache, _task_runner

    # --- Redis ---
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        await asyncio.wait_for(_redis.ping(), timeout=10)
        logger.info("Redis connected: %s", redis_url)
    except Exception as e:
        logger.warning("Redis unavailable (%s), using in-memory fallback", e)
        _redis = None

    # --- Job Store ---
    if _redis:
        from stores.redis_job_store import RedisJobStore
        _job_store = RedisJobStore(redis=_redis)
        logger.info("Using RedisJobStore")
    else:
        from job_store import JobStore
        _job_store = JobStore()
        logger.info("Using in-memory JobStore (no Redis)")

    # --- Redis Cache ---
    if _redis:
        from app_cache.redis_cache import RedisCache
        _redis_cache = RedisCache(redis=_redis)
        logger.info("Using RedisCache for PNCP responses")
    else:
        _redis_cache = None
        logger.info("Using no shared cache (no Redis)")

    # --- Async PNCP Client ---
    _pncp_client = AsyncPNCPClient()

    # --- PNCP Source ---
    _pncp_source = PNCPSource(async_client=_pncp_client, cache=_redis_cache)

    # --- Orchestrator (only active sources: PNCP + Transparencia) ---
    sources = [
        _pncp_source,
        TransparenciaSource(),
    ]
    _orchestrator = MultiSourceOrchestrator(sources=sources)

    # --- Durable Task Runner (TD-H02) ---
    _task_runner = DurableTaskRunner(redis=_redis)

    logger.info("All dependencies initialized")


async def shutdown_dependencies() -> None:
    """Cleanup all dependencies. Called from lifespan shutdown."""
    global _redis, _pncp_client

    if _pncp_client:
        await _pncp_client.close()
        logger.info("AsyncPNCPClient closed")

    if _redis:
        await _redis.aclose()
        logger.info("Redis connection closed")


def get_job_store():
    """Dependency: get the job store instance."""
    return _job_store


def get_orchestrator():
    """Dependency: get the multi-source orchestrator."""
    return _orchestrator


def get_pncp_source():
    """Dependency: get the PNCP source."""
    return _pncp_source


def get_pncp_client():
    """Dependency: get the async PNCP client."""
    return _pncp_client


def get_redis():
    """Dependency: get the Redis client (may be None)."""
    return _redis


def get_redis_cache():
    """Dependency: get the Redis cache (may be None)."""
    return _redis_cache


def get_task_runner():
    """Dependency: get the durable task runner."""
    return _task_runner
