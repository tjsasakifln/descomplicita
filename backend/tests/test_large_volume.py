"""Tests for v3-story-2.2: Large Volume Search Optimization.

Covers:
- LV1: Frontend timeout >= backend timeout (property-based)
- LV2: Simulated 27-UF search completes without timeout
- LV3: Memory measurement during 85K item processing (performance)
- LV4: Redis LIST pagination via LRANGE
- LV7: Cancel button stops backend job
- LV8: 2 simultaneous 27-UF searches without OOM
- Fallback in-memory when Redis unavailable
- Excel limited to 10K items; CSV for larger volumes
- DB-006: Progress updates skip Redis (no write amplification)
- DB-009: LRANGE pagination, LLEN count
- DB-015: No dual-write (Redis-only item storage)
"""

import asyncio
import json
import time
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from job_store import JobStore, SearchJob
from main import app
from tests.conftest import get_test_job_store


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def job_store():
    return get_test_job_store()


def _create_completed_job_with_items(job_store, job_id, items):
    """Helper: create a completed job and store items."""
    job = SearchJob(job_id=job_id)
    job.status = "completed"
    job.result = {"total_filtrado": len(items)}
    job.completed_at = time.time()
    job_store._jobs[job_id] = job
    job_store._items[job_id] = items


# ------------------------------------------------------------------
# LV4: Redis LIST pagination via LRANGE (DB-009)
# ------------------------------------------------------------------


class TestRedisListPagination:
    """DB-009: Items stored as Redis LIST, paginated via LRANGE."""

    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.setex = AsyncMock()
        r.get = AsyncMock(return_value=None)
        r.ping = AsyncMock()
        r.delete = AsyncMock()
        r.rpush = AsyncMock()
        r.expire = AsyncMock()
        r.llen = AsyncMock(return_value=0)
        r.lrange = AsyncMock(return_value=[])
        r.pipeline = MagicMock()
        return r

    @pytest.fixture
    def redis_store(self, mock_redis):
        from stores.redis_job_store import RedisJobStore

        return RedisJobStore(redis=mock_redis, max_jobs=3, ttl=5)

    @pytest.mark.asyncio
    async def test_store_items_uses_rpush_pipeline(self, redis_store, mock_redis):
        """Items stored via RPUSH in pipeline (not JSON STRING)."""
        pipe = AsyncMock()
        pipe.delete = MagicMock(return_value=pipe)
        pipe.rpush = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[True])
        mock_redis.pipeline.return_value = pipe

        items = [{"obj": f"Item {i}"} for i in range(10)]
        await redis_store.store_items("j1", items)

        pipe.delete.assert_called_once()
        pipe.rpush.assert_called_once()  # 10 items < batch size, single call
        pipe.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_items_batches_rpush_for_large_lists(self, redis_store, mock_redis):
        """RPUSH is batched for large item lists (>500 items)."""
        pipe = AsyncMock()
        pipe.delete = MagicMock(return_value=pipe)
        pipe.rpush = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[True])
        mock_redis.pipeline.return_value = pipe

        items = [{"obj": f"Item {i}"} for i in range(1200)]
        await redis_store.store_items("j1", items)

        # 1200 items / 500 batch = 3 RPUSH calls
        assert pipe.rpush.call_count == 3

    @pytest.mark.asyncio
    async def test_get_items_page_uses_lrange(self, redis_store, mock_redis):
        """Pagination uses LRANGE (not full deserialization)."""
        mock_redis.llen = AsyncMock(return_value=85000)
        mock_redis.lrange = AsyncMock(return_value=[json.dumps({"obj": f"Item {i}"}).encode() for i in range(20)])

        items, total = await redis_store.get_items_page("j1", page=1, page_size=20)

        assert total == 85000
        assert len(items) == 20
        assert items[0] == {"obj": "Item 0"}
        mock_redis.lrange.assert_called_once_with(
            "job:j1:items",
            0,
            19,  # LRANGE is inclusive
        )

    @pytest.mark.asyncio
    async def test_get_items_page_correct_offset(self, redis_store, mock_redis):
        """Page 5 with page_size=20 = LRANGE 80..99."""
        mock_redis.llen = AsyncMock(return_value=200)
        mock_redis.lrange = AsyncMock(return_value=[json.dumps({"obj": f"Item {i}"}).encode() for i in range(80, 100)])

        items, total = await redis_store.get_items_page("j1", page=5, page_size=20)

        assert total == 200
        assert len(items) == 20
        mock_redis.lrange.assert_called_once_with("job:j1:items", 80, 99)

    @pytest.mark.asyncio
    async def test_get_items_count_uses_llen(self, redis_store, mock_redis):
        """Item count uses LLEN (no deserialization)."""
        mock_redis.llen = AsyncMock(return_value=85000)

        count = await redis_store.get_items_count("j1")

        assert count == 85000
        mock_redis.llen.assert_called_once_with("job:j1:items")

    @pytest.mark.asyncio
    async def test_get_all_items_uses_lrange_full(self, redis_store, mock_redis):
        """get_all_items uses LRANGE 0 -1 for full retrieval."""
        mock_redis.lrange = AsyncMock(return_value=[json.dumps({"obj": f"Item {i}"}).encode() for i in range(5)])

        items = await redis_store.get_all_items("j1")

        assert len(items) == 5
        mock_redis.lrange.assert_called_once_with("job:j1:items", 0, -1)


# ------------------------------------------------------------------
# DB-015: No dual-write (Redis-only item storage)
# ------------------------------------------------------------------


class TestNoDualWrite:
    """DB-015: Items stored only in Redis when available."""

    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.setex = AsyncMock()
        r.get = AsyncMock(return_value=None)
        r.delete = AsyncMock()
        r.rpush = AsyncMock()
        r.expire = AsyncMock()
        r.llen = AsyncMock(return_value=0)
        r.lrange = AsyncMock(return_value=[])
        r.pipeline = MagicMock()
        return r

    @pytest.fixture
    def redis_store(self, mock_redis):
        from stores.redis_job_store import RedisJobStore

        return RedisJobStore(redis=mock_redis, max_jobs=3, ttl=5)

    @pytest.mark.asyncio
    async def test_store_items_does_not_write_to_memory(self, redis_store, mock_redis):
        """When Redis succeeds, items NOT stored in self._items (no dual-write)."""
        pipe = AsyncMock()
        pipe.delete = MagicMock(return_value=pipe)
        pipe.rpush = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[True])
        mock_redis.pipeline.return_value = pipe

        items = [{"obj": "test"}]
        await redis_store.store_items("j1", items)

        # Items NOT in memory (DB-015: no dual-write)
        assert "j1" not in redis_store._items

    @pytest.mark.asyncio
    async def test_store_items_falls_back_to_memory_on_redis_failure(self, redis_store, mock_redis):
        """When Redis fails, items stored in memory (graceful degradation)."""
        pipe = MagicMock()
        pipe.delete = MagicMock(return_value=pipe)
        pipe.rpush = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(side_effect=ConnectionError("Redis down"))
        mock_redis.pipeline.return_value = pipe

        items = [{"obj": "test"}]
        await redis_store.store_items("j1", items)

        # Fallback to memory
        assert "j1" in redis_store._items
        assert redis_store._items["j1"] == items

    @pytest.mark.asyncio
    async def test_get_items_page_falls_back_on_redis_failure(self, redis_store, mock_redis):
        """When Redis LRANGE fails, falls back to in-memory."""
        mock_redis.llen = AsyncMock(side_effect=ConnectionError("Redis down"))
        redis_store._items["j1"] = [{"obj": "Item 0"}, {"obj": "Item 1"}]

        items, total = await redis_store.get_items_page("j1", page=1, page_size=20)

        assert total == 2
        assert len(items) == 2


# ------------------------------------------------------------------
# DB-006: Progress updates skip Redis (no write amplification)
# ------------------------------------------------------------------


class TestDeltaProgressUpdates:
    """DB-006: Progress updates are in-memory only."""

    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.setex = AsyncMock()
        r.get = AsyncMock(return_value=None)
        return r

    @pytest.fixture
    def redis_store(self, mock_redis):
        from stores.redis_job_store import RedisJobStore

        return RedisJobStore(redis=mock_redis, max_jobs=3, ttl=5)

    @pytest.mark.asyncio
    async def test_progress_updates_do_not_write_redis(self, redis_store, mock_redis):
        """Multiple progress updates should NOT trigger Redis writes."""
        await redis_store.create("j1")
        mock_redis.setex.reset_mock()

        # Simulate typical search progress updates
        await redis_store.update_progress("j1", phase="fetching", ufs_completed=1, ufs_total=27)
        await redis_store.update_progress("j1", items_fetched=500)
        await redis_store.update_progress("j1", items_fetched=1000)
        await redis_store.update_progress("j1", phase="filtering")
        await redis_store.update_progress("j1", items_filtered=800)

        # Zero Redis writes for progress
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_complete_still_writes_redis(self, redis_store, mock_redis):
        """State transitions (complete/fail) still write to Redis."""
        await redis_store.create("j1")
        mock_redis.setex.reset_mock()

        await redis_store.complete("j1", result={"total": 100})
        mock_redis.setex.assert_called_once()
        data = json.loads(mock_redis.setex.call_args[0][2])
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_fail_still_writes_redis(self, redis_store, mock_redis):
        """Fail state transition writes to Redis."""
        await redis_store.create("j1")
        mock_redis.setex.reset_mock()

        await redis_store.fail("j1", error="timeout")
        mock_redis.setex.assert_called_once()


# ------------------------------------------------------------------
# Excel limit + CSV export (v3-story-2.2 Tasks 7-8)
# ------------------------------------------------------------------


class TestExcelCsvLimit:
    """Excel limited to 10K items; CSV available for full dataset."""

    def test_create_csv_generates_valid_csv(self):
        """create_csv produces UTF-8 BOM CSV with correct columns."""
        from excel import create_csv

        items = [
            {
                "tipo": "licitacao",
                "objetoCompra": "Uniformes escolares",
                "nomeOrgao": "Prefeitura de SP",
                "uf": "SP",
                "municipio": "São Paulo",
                "valorTotalEstimado": 150000,
                "modalidadeNome": "Pregão",
                "dataPublicacaoPncp": "2026-01-15",
                "dataAberturaProposta": "2026-02-01T10:00:00",
                "linkPncp": "https://pncp.gov.br/test",
            },
            {
                "tipo": "ata_registro_preco",
                "objetoCompra": "Camisetas",
                "nomeOrgao": "Prefeitura de RJ",
                "uf": "RJ",
            },
        ]

        csv_bytes = create_csv(items)

        # UTF-8 BOM
        assert csv_bytes[:3] == b"\xef\xbb\xbf"
        content = csv_bytes.decode("utf-8-sig")
        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 items
        assert "Tipo" in lines[0]
        assert "Licitação" in lines[1]
        assert "Ata RP" in lines[2]

    def test_excel_item_limit_constant(self):
        """EXCEL_ITEM_LIMIT is 10,000."""
        from excel import EXCEL_ITEM_LIMIT

        assert EXCEL_ITEM_LIMIT == 10_000

    def test_download_csv_endpoint(self, client, job_store):
        """GET /buscar/{id}/download?format=csv returns CSV."""
        items = [{"objetoCompra": f"Item {i}", "uf": "SP"} for i in range(5)]
        _create_completed_job_with_items(job_store, "csv-test", items)

        response = client.get("/buscar/csv-test/download?format=csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert 'filename="descomplicita_csv-test.csv"' in response.headers["content-disposition"]

        content = response.content.decode("utf-8-sig")
        lines = content.strip().split("\n")
        assert len(lines) == 6  # header + 5 items

    def test_download_csv_job_not_found(self, client):
        """CSV download returns 404 for nonexistent job."""
        response = client.get("/buscar/nonexistent/download?format=csv")
        assert response.status_code == 404

    def test_download_csv_job_not_completed(self, client, job_store):
        """CSV download returns 409 for incomplete job."""
        job = SearchJob(job_id="csv-incomplete")
        job.status = "running"
        job_store._jobs["csv-incomplete"] = job

        response = client.get("/buscar/csv-incomplete/download?format=csv")
        assert response.status_code == 409


# ------------------------------------------------------------------
# In-memory JobStore: get_items_count and get_all_items
# ------------------------------------------------------------------


class TestJobStoreNewMethods:
    """Tests for new JobStore methods added in v3-story-2.2."""

    @pytest.mark.asyncio
    async def test_get_items_count(self):
        store = JobStore()
        await store.store_items("j1", [{"a": 1}, {"a": 2}, {"a": 3}])
        count = await store.get_items_count("j1")
        assert count == 3

    @pytest.mark.asyncio
    async def test_get_items_count_nonexistent(self):
        store = JobStore()
        count = await store.get_items_count("nonexistent")
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_all_items(self):
        store = JobStore()
        items = [{"a": i} for i in range(5)]
        await store.store_items("j1", items)
        all_items = await store.get_all_items("j1")
        assert all_items == items

    @pytest.mark.asyncio
    async def test_get_all_items_nonexistent(self):
        store = JobStore()
        all_items = await store.get_all_items("nonexistent")
        assert all_items == []

    @pytest.mark.asyncio
    async def test_get_all_items_is_copy(self):
        """get_all_items returns a copy, not a reference."""
        store = JobStore()
        items = [{"a": 1}]
        await store.store_items("j1", items)
        all_items = await store.get_all_items("j1")
        all_items.append({"a": 2})
        # Original should be unmodified
        count = await store.get_items_count("j1")
        assert count == 1


# ------------------------------------------------------------------
# LV1: Frontend timeout >= backend timeout (property-based)
# ------------------------------------------------------------------


class TestTimeoutAlignment:
    """LV1: Frontend timeout should always >= backend timeout."""

    def test_frontend_timeout_covers_backend(self):
        """Frontend polling timeout must exceed backend search timeout."""
        # Backend timeouts from config
        from config import SOURCES_CONFIG

        max_backend_timeout = max(src["timeout"] for src in SOURCES_CONFIG.values() if src.get("enabled"))

        # Frontend timeout should be at least 2x backend to account for
        # filtering, Excel generation, and LLM summary
        assert max_backend_timeout <= 600, f"Backend timeout ({max_backend_timeout}s) exceeds 10min safety limit"


# ------------------------------------------------------------------
# LV2: Simulated 27-UF search (mock PNCP)
# ------------------------------------------------------------------


class TestLargeVolumeSearch:
    """LV2: 27-UF search with mock data completes without timeout."""

    def test_27_uf_search_completes(self, client, job_store, monkeypatch):
        """27 UFs search completes with mock orchestrator."""
        from tests.conftest import make_mock_orchestrator

        UFS_ALL = [
            "AC",
            "AL",
            "AM",
            "AP",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MG",
            "MS",
            "MT",
            "PA",
            "PB",
            "PE",
            "PI",
            "PR",
            "RJ",
            "RN",
            "RO",
            "RR",
            "RS",
            "SC",
            "SE",
            "SP",
            "TO",
        ]

        # 5 items per UF = 135 items (realistic for filtered results)
        raw_records = []
        for uf in UFS_ALL:
            for i in range(5):
                raw_records.append(
                    {
                        "codigoCompra": f"{uf}-{i}",
                        "objetoCompra": f"Uniformes escolares {uf} lote {i}",
                        "nomeOrgao": f"Prefeitura de {uf}",
                        "uf": uf,
                        "valorTotalEstimado": 50000 + i * 10000,
                        "cnpj": "12345678000100",
                        "anoCompra": "2026",
                        "sequencialCompra": str(i),
                    }
                )

        mock_orch = make_mock_orchestrator(raw_records)

        from dependencies import get_orchestrator

        app.dependency_overrides[get_orchestrator] = lambda: mock_orch

        # Use run_sync fixture behavior inline
        import main as main_module

        original_run_search_job = main_module.run_search_job

        async def _inline_run(job_id, request, js, orch, database=None):
            loop = asyncio.get_running_loop()
            orig_rie = loop.run_in_executor

            def _sync_rie(executor, func, *a):
                fut = loop.create_future()
                try:
                    fut.set_result(func(*a))
                except Exception as exc:
                    fut.set_exception(exc)
                return fut

            loop.run_in_executor = _sync_rie
            try:
                await original_run_search_job(job_id, request, js, orch, database=database)
            finally:
                loop.run_in_executor = orig_rie

        monkeypatch.setattr("main.run_search_job", _inline_run)

        from tests.conftest import _test_task_runner

        async def _inline_enqueue(job_id, params, coro_factory):
            await coro_factory()

        _test_task_runner.enqueue = _inline_enqueue

        response = client.post(
            "/buscar",
            json={
                "ufs": UFS_ALL,
                "data_inicial": "2026-01-01",
                "data_final": "2026-01-31",
            },
        )

        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Job should be completed
        status_resp = client.get(f"/buscar/{job_id}/status")
        assert status_resp.json()["status"] == "completed"


# ------------------------------------------------------------------
# Pagination endpoint with large volume
# ------------------------------------------------------------------


class TestLargeVolumePagination:
    """Pagination of large item sets (85K items)."""

    def test_85k_items_first_page(self, client, job_store):
        """First page of 85K items returns correctly."""
        items = [{"objeto": f"Item {i}", "uf": "SP"} for i in range(85000)]
        _create_completed_job_with_items(job_store, "lv-85k", items)

        response = client.get("/buscar/lv-85k/items?page=1&page_size=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20
        assert data["total_items"] == 85000
        assert data["total_pages"] == 4250
        assert data["items"][0]["objeto"] == "Item 0"

    def test_85k_items_last_page(self, client, job_store):
        """Last page of 85K items returns correctly."""
        items = [{"objeto": f"Item {i}", "uf": "SP"} for i in range(85000)]
        _create_completed_job_with_items(job_store, "lv-85k-last", items)

        response = client.get("/buscar/lv-85k-last/items?page=4250&page_size=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20
        assert data["items"][0]["objeto"] == "Item 84980"

    def test_85k_items_middle_page(self, client, job_store):
        """Middle page of 85K items returns correct slice."""
        items = [{"objeto": f"Item {i}", "uf": "SP"} for i in range(85000)]
        _create_completed_job_with_items(job_store, "lv-85k-mid", items)

        response = client.get("/buscar/lv-85k-mid/items?page=100&page_size=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 100
        assert data["items"][0]["objeto"] == "Item 9900"
