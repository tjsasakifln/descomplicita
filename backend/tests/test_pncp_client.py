"""Unit tests for async PNCP client with retry logic and rate limiting."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import httpx
import pytest

from config import RetryConfig, DEFAULT_MODALIDADES
from exceptions import PNCPAPIError
from clients.async_pncp_client import AsyncPNCPClient, calculate_delay

DEFAULT_MODALIDADE = 6


class TestCalculateDelay:
    """Test exponential backoff delay calculation."""

    def test_exponential_growth_without_jitter(self):
        config = RetryConfig(base_delay=2.0, exponential_base=2, max_delay=60.0, jitter=False)
        assert calculate_delay(0, config) == 2.0
        assert calculate_delay(1, config) == 4.0
        assert calculate_delay(2, config) == 8.0
        assert calculate_delay(3, config) == 16.0
        assert calculate_delay(4, config) == 32.0

    def test_max_delay_cap(self):
        config = RetryConfig(base_delay=2.0, exponential_base=2, max_delay=15.0, jitter=False)
        assert calculate_delay(3, config) == 15.0
        assert calculate_delay(10, config) == 15.0

    def test_jitter_adds_randomness(self):
        config = RetryConfig(base_delay=10.0, exponential_base=1, jitter=True)
        delays = [calculate_delay(0, config) for _ in range(100)]
        assert all(5.0 <= d <= 15.0 for d in delays)
        assert len(set(delays)) > 10


class TestAsyncPNCPClient:
    """Test AsyncPNCPClient initialization."""

    def test_client_initialization_default_config(self):
        client = AsyncPNCPClient()
        assert client.config.max_retries == 2
        assert client.config.base_delay == 1.0
        assert client._request_count == 0

    def test_client_initialization_custom_config(self):
        custom_config = RetryConfig(max_retries=3, base_delay=1.0)
        client = AsyncPNCPClient(config=custom_config)
        assert client.config.max_retries == 3
        assert client.config.base_delay == 1.0


class TestAsyncFetchPage:
    """Test async fetch_page scenarios."""

    @pytest.mark.asyncio
    async def test_fetch_page_success(self):
        client = AsyncPNCPClient()
        mock_response = httpx.Response(
            200,
            json={
                "data": [{"id": 1}, {"id": 2}],
                "totalRegistros": 2,
                "totalPaginas": 1,
                "paginaAtual": 1,
                "paginasRestantes": 0,
            },
            request=httpx.Request("GET", "https://test.com"),
        )

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.fetch_page("2024-01-01", "2024-01-30", modalidade=DEFAULT_MODALIDADE)
            assert result["data"] == [{"id": 1}, {"id": 2}]
            assert result["totalRegistros"] == 2

    @pytest.mark.asyncio
    async def test_fetch_page_204_no_content(self):
        client = AsyncPNCPClient()
        mock_response = httpx.Response(
            204,
            request=httpx.Request("GET", "https://test.com"),
        )

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.fetch_page("2024-01-01", "2024-01-30", modalidade=DEFAULT_MODALIDADE)
            assert result["data"] == []
            assert result["totalRegistros"] == 0

    @pytest.mark.asyncio
    async def test_fetch_page_400_fails_immediately(self):
        client = AsyncPNCPClient()
        mock_response = httpx.Response(
            400,
            text="Bad Request",
            request=httpx.Request("GET", "https://test.com"),
        )

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            with pytest.raises(PNCPAPIError, match="non-retryable status 400"):
                await client.fetch_page("2024-01-01", "2024-01-30", modalidade=DEFAULT_MODALIDADE)
            assert mock_http.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_page_retry_on_500(self):
        client = AsyncPNCPClient(config=RetryConfig(max_retries=1))

        fail_response = httpx.Response(500, text="Server Error", request=httpx.Request("GET", "https://test.com"))
        success_response = httpx.Response(200, json={"data": []}, request=httpx.Request("GET", "https://test.com"))

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=[fail_response, success_response])
            mock_get_client.return_value = mock_http

            with patch("clients.async_pncp_client.asyncio.sleep", new_callable=AsyncMock):
                result = await client.fetch_page("2024-01-01", "2024-01-30", modalidade=DEFAULT_MODALIDADE)
                assert result["data"] == []
                assert mock_http.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_page_max_retries_exceeded(self):
        client = AsyncPNCPClient(config=RetryConfig(max_retries=1))
        fail_response = httpx.Response(500, text="Server Error", request=httpx.Request("GET", "https://test.com"))

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=fail_response)
            mock_get_client.return_value = mock_http

            with patch("clients.async_pncp_client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(PNCPAPIError, match="Failed after 2 attempts"):
                    await client.fetch_page("2024-01-01", "2024-01-30", modalidade=DEFAULT_MODALIDADE)


class TestAsyncFetchAll:
    """Test fetch_all async functionality."""

    @pytest.mark.asyncio
    async def test_fetch_all_single_page(self):
        client = AsyncPNCPClient()
        mock_response = httpx.Response(
            200,
            json={
                "data": [
                    {"numeroControlePNCP": "001", "unidadeOrgao": {"ufSigla": "SP", "municipioNome": ""}, "orgaoEntidade": {"razaoSocial": ""}},
                    {"numeroControlePNCP": "002", "unidadeOrgao": {"ufSigla": "SP", "municipioNome": ""}, "orgaoEntidade": {"razaoSocial": ""}},
                ],
                "totalRegistros": 2,
                "totalPaginas": 1,
                "paginasRestantes": 0,
            },
            request=httpx.Request("GET", "https://test.com"),
        )

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            results = await client.fetch_all("2024-01-01", "2024-01-30", ufs=["SP"], modalidades=[6])
            assert len(results) == 2
            assert results[0]["codigoCompra"] == "001"

    @pytest.mark.asyncio
    async def test_fetch_all_deduplicates(self):
        client = AsyncPNCPClient()

        response_mod6 = httpx.Response(
            200,
            json={
                "data": [{"numeroControlePNCP": "001"}, {"numeroControlePNCP": "002"}],
                "totalRegistros": 2,
                "totalPaginas": 1,
                "paginasRestantes": 0,
            },
            request=httpx.Request("GET", "https://test.com"),
        )
        response_mod7 = httpx.Response(
            200,
            json={
                "data": [{"numeroControlePNCP": "001"}, {"numeroControlePNCP": "003"}],
                "totalRegistros": 2,
                "totalPaginas": 1,
                "paginasRestantes": 0,
            },
            request=httpx.Request("GET", "https://test.com"),
        )

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return response_mod6
            return response_mod7

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=mock_get)
            mock_get_client.return_value = mock_http

            results = await client.fetch_all("2024-01-01", "2024-01-30", ufs=["SP"], modalidades=[6, 7])
            assert len(results) == 3  # 001 deduplicated

    @pytest.mark.asyncio
    async def test_fetch_all_empty_results(self):
        client = AsyncPNCPClient()
        mock_response = httpx.Response(
            200,
            json={
                "data": [],
                "totalRegistros": 0,
                "totalPaginas": 1,
                "paginasRestantes": 0,
            },
            request=httpx.Request("GET", "https://test.com"),
        )

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            results = await client.fetch_all("2024-01-01", "2024-01-30", ufs=["SP"], modalidades=[6])
            assert len(results) == 0


class TestDateRangeChunking:
    """Test _chunk_date_range() date splitting logic."""

    def test_short_range_single_chunk(self):
        chunks = AsyncPNCPClient._chunk_date_range("2024-01-01", "2024-01-30")
        assert len(chunks) == 1
        assert chunks[0] == ("2024-01-01", "2024-01-30")

    def test_31_days_produces_two_chunks(self):
        chunks = AsyncPNCPClient._chunk_date_range("2024-01-01", "2024-01-31")
        assert len(chunks) == 2
        assert chunks[0] == ("2024-01-01", "2024-01-30")
        assert chunks[1] == ("2024-01-31", "2024-01-31")

    def test_single_day_range(self):
        chunks = AsyncPNCPClient._chunk_date_range("2024-06-15", "2024-06-15")
        assert len(chunks) == 1
        assert chunks[0] == ("2024-06-15", "2024-06-15")

    def test_six_month_range(self):
        chunks = AsyncPNCPClient._chunk_date_range("2025-08-01", "2026-01-28")
        assert len(chunks) >= 6
        assert chunks[0][0] == "2025-08-01"
        assert chunks[-1][1] == "2026-01-28"
        from datetime import date, timedelta
        for i in range(len(chunks) - 1):
            end = date.fromisoformat(chunks[i][1])
            next_start = date.fromisoformat(chunks[i + 1][0])
            assert next_start - end == timedelta(days=1)
