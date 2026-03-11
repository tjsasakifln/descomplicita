"""Unit tests for DI provider functions (TD-013)."""

from unittest.mock import AsyncMock, patch

import pytest

import dependencies


class TestDIProviders:
    """Test DI provider functions return correct instances."""

    @pytest.mark.asyncio
    async def test_init_without_redis(self):
        """init_dependencies should work without Redis (graceful fallback)."""
        with patch.dict("os.environ", {"REDIS_URL": "redis://nonexistent:9999/0"}):
            await dependencies.init_dependencies()

        # Should have in-memory fallback
        from job_store import JobStore

        store = dependencies.get_job_store()
        assert isinstance(store, JobStore)

        # Redis should be None
        assert dependencies.get_redis() is None

        # Cache should be None
        assert dependencies.get_redis_cache() is None

        # Orchestrator should exist
        orch = dependencies.get_orchestrator()
        assert orch is not None

        # PNCP source should exist
        source = dependencies.get_pncp_source()
        assert source is not None

        # Task runner should exist (TD-H02)
        from task_queue import DurableTaskRunner

        runner = dependencies.get_task_runner()
        assert isinstance(runner, DurableTaskRunner)

        # Cleanup
        await dependencies.shutdown_dependencies()

    @pytest.mark.asyncio
    async def test_shutdown_cleans_up(self):
        """shutdown_dependencies should close client."""
        with patch.dict("os.environ", {"REDIS_URL": "redis://nonexistent:9999/0"}):
            await dependencies.init_dependencies()
            await dependencies.shutdown_dependencies()
        # Should not raise


class TestLifespan:
    """Test lifespan context manager starts and stops cleanly."""

    @pytest.mark.asyncio
    async def test_lifespan_context(self):
        """Lifespan should initialize and cleanup without errors."""
        import asyncio

        from main import app, lifespan

        async with lifespan(app):
            # Dependencies should be initialized
            store = dependencies.get_job_store()
            assert store is not None
        # After context exit, dependencies are cleaned up
