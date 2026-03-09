"""FastAPI dependency injection providers (TD-013 / TD-M05).

Refactored from module-level globals to a centralized AppState class.
All state is encapsulated; dependency functions access it through
get_app_state() which is overridable via FastAPI's dependency_overrides
for clean test injection.
"""

import asyncio
import logging
import os
from typing import Optional

from clients.async_pncp_client import AsyncPNCPClient
from database import Database
from sources.pncp_source import PNCPSource
from sources.transparencia_source import TransparenciaSource
from sources.orchestrator import MultiSourceOrchestrator
from task_queue import DurableTaskRunner

logger = logging.getLogger(__name__)


class AppState:
    """Encapsulated application state for dependency injection (TD-M05).

    All mutable application state lives here instead of module-level globals.
    This enables clean test isolation via dependency_overrides.
    """

    def __init__(self) -> None:
        self.redis = None
        self.job_store = None
        self.pncp_client: Optional[AsyncPNCPClient] = None
        self.pncp_source: Optional[PNCPSource] = None
        self.orchestrator: Optional[MultiSourceOrchestrator] = None
        self.redis_cache = None
        self.task_runner: Optional[DurableTaskRunner] = None
        self.database: Optional[Database] = None

    async def init(self) -> None:
        """Initialize all dependencies. Called from lifespan startup."""
        # --- Redis ---
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await asyncio.wait_for(self.redis.ping(), timeout=10)
            logger.info("Redis connected: %s", redis_url)
        except Exception as e:
            logger.warning("Redis unavailable (%s), using in-memory fallback", e)
            self.redis = None

        # --- Job Store ---
        if self.redis:
            from stores.redis_job_store import RedisJobStore
            self.job_store = RedisJobStore(redis=self.redis)
            logger.info("Using RedisJobStore")
        else:
            from job_store import JobStore
            self.job_store = JobStore()
            logger.info("Using in-memory JobStore (no Redis)")

        # --- Redis Cache ---
        if self.redis:
            from app_cache.redis_cache import RedisCache
            self.redis_cache = RedisCache(redis=self.redis)
            logger.info("Using RedisCache for PNCP responses")
        else:
            self.redis_cache = None
            logger.info("Using no shared cache (no Redis)")

        # --- Async PNCP Client ---
        self.pncp_client = AsyncPNCPClient()

        # --- PNCP Source ---
        self.pncp_source = PNCPSource(async_client=self.pncp_client, cache=self.redis_cache)

        # --- Orchestrator (only active sources: PNCP + Transparencia) ---
        sources = [
            self.pncp_source,
            TransparenciaSource(),
        ]
        self.orchestrator = MultiSourceOrchestrator(sources=sources)

        # --- Durable Task Runner (TD-H02) ---
        self.task_runner = DurableTaskRunner(redis=self.redis)

        # --- Database (TD-H04) ---
        try:
            self.database = Database()
            await self.database.connect()
        except Exception as e:
            logger.warning("Database unavailable (%s), persistence disabled", e)
            self.database = None

        logger.info("All dependencies initialized")

    async def shutdown(self) -> None:
        """Cleanup all dependencies. Called from lifespan shutdown."""
        if self.database:
            await self.database.close()
            logger.info("Database closed")

        if self.pncp_client:
            await self.pncp_client.close()
            logger.info("AsyncPNCPClient closed")

        if self.redis:
            await self.redis.aclose()
            logger.info("Redis connection closed")


# Singleton instance — created once, used throughout the app lifetime
_app_state = AppState()


async def init_dependencies() -> None:
    """Initialize all application dependencies. Called from lifespan startup."""
    await _app_state.init()


async def shutdown_dependencies() -> None:
    """Cleanup all dependencies. Called from lifespan shutdown."""
    await _app_state.shutdown()


def get_app_state() -> AppState:
    """Return the application state instance.

    Override this in tests via app.dependency_overrides[get_app_state].
    """
    return _app_state


def get_job_store():
    """Dependency: get the job store instance."""
    return _app_state.job_store


def get_orchestrator():
    """Dependency: get the multi-source orchestrator."""
    return _app_state.orchestrator


def get_pncp_source():
    """Dependency: get the PNCP source."""
    return _app_state.pncp_source


def get_pncp_client():
    """Dependency: get the async PNCP client."""
    return _app_state.pncp_client


def get_redis():
    """Dependency: get the Redis client (may be None)."""
    return _app_state.redis


def get_redis_cache():
    """Dependency: get the Redis cache (may be None)."""
    return _app_state.redis_cache


def get_task_runner():
    """Dependency: get the durable task runner."""
    return _app_state.task_runner


def get_database():
    """Dependency: get the database (may be None)."""
    return _app_state.database
