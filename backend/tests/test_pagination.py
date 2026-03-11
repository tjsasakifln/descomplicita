"""Tests for paginated items endpoint (TD-M02)."""

import time

import pytest
from fastapi.testclient import TestClient

from job_store import SearchJob
from main import app
from tests.conftest import get_test_job_store


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def job_store():
    """Get the test job store."""
    return get_test_job_store()


def _create_completed_job_with_items(job_store, job_id, items):
    """Helper: create a completed job and store items by manipulating internals."""
    job = SearchJob(job_id=job_id)
    job.status = "completed"
    job.result = {"total_filtrado": len(items)}
    job.completed_at = time.time()
    job_store._jobs[job_id] = job
    job_store._items[job_id] = items


class TestJobItemsEndpoint:
    """Tests for GET /buscar/{job_id}/items."""

    def test_returns_paginated_items(self, client, job_store):
        items = [{"objeto": f"Item {i}", "uf": "SP"} for i in range(50)]
        _create_completed_job_with_items(job_store, "job-pag-1", items)

        response = client.get("/buscar/job-pag-1/items?page=1&page_size=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_items"] == 50
        assert data["total_pages"] == 3

    def test_second_page(self, client, job_store):
        items = [{"objeto": f"Item {i}"} for i in range(50)]
        _create_completed_job_with_items(job_store, "job-pag-2", items)

        response = client.get("/buscar/job-pag-2/items?page=2&page_size=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20
        assert data["items"][0]["objeto"] == "Item 20"

    def test_last_partial_page(self, client, job_store):
        items = [{"objeto": f"Item {i}"} for i in range(25)]
        _create_completed_job_with_items(job_store, "job-pag-3", items)

        response = client.get("/buscar/job-pag-3/items?page=2&page_size=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total_pages"] == 2

    def test_page_zero_returns_400(self, client, job_store):
        items = [{"objeto": "test"}]
        _create_completed_job_with_items(job_store, "job-pag-4", items)

        response = client.get("/buscar/job-pag-4/items?page=0")
        assert response.status_code == 400
        assert "page must be >= 1" in response.json()["detail"]["error"]["message"]

    def test_negative_page_returns_400(self, client, job_store):
        items = [{"objeto": "test"}]
        _create_completed_job_with_items(job_store, "job-pag-neg", items)

        response = client.get("/buscar/job-pag-neg/items?page=-1")
        assert response.status_code == 400

    def test_page_size_zero_returns_400(self, client, job_store):
        items = [{"objeto": "test"}]
        _create_completed_job_with_items(job_store, "job-pag-5", items)

        response = client.get("/buscar/job-pag-5/items?page_size=0")
        assert response.status_code == 400
        assert "page_size must be between 1 and 100" in response.json()["detail"]["error"]["message"]

    def test_page_size_over_100_returns_400(self, client, job_store):
        items = [{"objeto": "test"}]
        _create_completed_job_with_items(job_store, "job-pag-6", items)

        response = client.get("/buscar/job-pag-6/items?page_size=101")
        assert response.status_code == 400
        assert "page_size must be between 1 and 100" in response.json()["detail"]["error"]["message"]

    def test_job_not_found_returns_404(self, client):
        response = client.get("/buscar/nonexistent-job/items")
        assert response.status_code == 404
        assert response.json()["detail"]["error"]["code"] == "JOB_NOT_FOUND"

    def test_incomplete_job_returns_409(self, client, job_store):
        job = SearchJob(job_id="job-pag-7")
        job_store._jobs["job-pag-7"] = job

        response = client.get("/buscar/job-pag-7/items")
        assert response.status_code == 409
        assert response.json()["detail"]["error"]["code"] == "JOB_NOT_COMPLETED"

    def test_running_job_returns_409(self, client, job_store):
        job = SearchJob(job_id="job-pag-running")
        job.status = "running"
        job.progress["phase"] = "fetching"
        job_store._jobs["job-pag-running"] = job

        response = client.get("/buscar/job-pag-running/items")
        assert response.status_code == 409

    def test_default_pagination_params(self, client, job_store):
        items = [{"objeto": f"Item {i}"} for i in range(30)]
        _create_completed_job_with_items(job_store, "job-pag-8", items)

        response = client.get("/buscar/job-pag-8/items")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 20

    def test_custom_page_size(self, client, job_store):
        items = [{"objeto": f"Item {i}"} for i in range(15)]
        _create_completed_job_with_items(job_store, "job-pag-9", items)

        response = client.get("/buscar/job-pag-9/items?page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total_pages"] == 3

    def test_page_beyond_total_returns_empty(self, client, job_store):
        items = [{"objeto": f"Item {i}"} for i in range(5)]
        _create_completed_job_with_items(job_store, "job-pag-10", items)

        response = client.get("/buscar/job-pag-10/items?page=99")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_items"] == 5

    def test_total_pages_calculation_exact(self, client, job_store):
        items = [{"objeto": f"Item {i}"} for i in range(40)]
        _create_completed_job_with_items(job_store, "job-pag-11", items)

        response = client.get("/buscar/job-pag-11/items")
        data = response.json()
        assert data["total_pages"] == 2

    def test_total_pages_zero_for_no_items(self, client, job_store):
        _create_completed_job_with_items(job_store, "job-pag-12", [])

        response = client.get("/buscar/job-pag-12/items")
        data = response.json()
        assert data["total_pages"] == 0
        assert data["total_items"] == 0

    def test_items_contain_expected_fields(self, client, job_store):
        items = [
            {
                "objeto": "Uniformes escolares",
                "orgao": "Prefeitura de SP",
                "uf": "SP",
                "valorTotalEstimado": 150000,
                "link": "https://example.com/lic1",
            }
        ]
        _create_completed_job_with_items(job_store, "job-pag-13", items)

        response = client.get("/buscar/job-pag-13/items")
        data = response.json()
        item = data["items"][0]
        assert item["objeto"] == "Uniformes escolares"
        assert item["orgao"] == "Prefeitura de SP"
        assert item["uf"] == "SP"
        assert item["valorTotalEstimado"] == 150000

    def test_max_page_size_100(self, client, job_store):
        items = [{"objeto": f"Item {i}"} for i in range(200)]
        _create_completed_job_with_items(job_store, "job-pag-max", items)

        response = client.get("/buscar/job-pag-max/items?page_size=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 100


class TestJobStoreItemsMethods:
    """Tests for store_items and get_items_page on the in-memory JobStore."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_items(self):
        from job_store import JobStore

        store = JobStore()
        items = [{"a": 1}, {"a": 2}, {"a": 3}]
        await store.store_items("test-1", items)

        page, total = await store.get_items_page("test-1", page=1, page_size=2)
        assert total == 3
        assert len(page) == 2
        assert page[0] == {"a": 1}

    @pytest.mark.asyncio
    async def test_get_items_page_second_page(self):
        from job_store import JobStore

        store = JobStore()
        items = [{"i": i} for i in range(5)]
        await store.store_items("test-2", items)

        page, total = await store.get_items_page("test-2", page=2, page_size=2)
        assert total == 5
        assert len(page) == 2
        assert page[0] == {"i": 2}

    @pytest.mark.asyncio
    async def test_get_items_page_nonexistent_job(self):
        from job_store import JobStore

        store = JobStore()
        page, total = await store.get_items_page("nonexistent", page=1, page_size=20)
        assert total == 0
        assert page == []

    @pytest.mark.asyncio
    async def test_store_items_overwrites(self):
        from job_store import JobStore

        store = JobStore()
        await store.store_items("test-ow", [{"x": 1}])
        await store.store_items("test-ow", [{"x": 2}, {"x": 3}])

        page, total = await store.get_items_page("test-ow")
        assert total == 2
        assert page[0] == {"x": 2}
