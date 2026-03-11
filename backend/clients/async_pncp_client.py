"""Async HTTP client for PNCP API using httpx."""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import httpx

from config import (
    DEFAULT_MODALIDADES,
    MODALIDADE_REDUCTION_UF_THRESHOLD,
    PNCP_BASE_URL,
    PRIORITY_MODALIDADES,
    RetryConfig,
)
from exceptions import PNCPAPIError

PNCP_PAGE_SIZE = 50

logger = logging.getLogger(__name__)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate exponential backoff delay with optional jitter."""
    delay = min(config.base_delay * (config.exponential_base**attempt), config.max_delay)
    if config.jitter:
        delay *= random.uniform(0.5, 1.5)
    return delay


class AsyncPNCPClient:
    """Async HTTP client for PNCP API with retry logic, rate limiting, and caching."""

    def __init__(self, config: RetryConfig | None = None, base_url: str | None = None) -> None:
        self.config = config or RetryConfig()
        self.BASE_URL = base_url or PNCP_BASE_URL
        self._client: httpx.AsyncClient | None = None
        self._request_count = 0
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
        # 429 rate limit monitoring
        self._rate_limit_count = 0
        self._total_fetch_count = 0
        # Circuit breaker
        self._consecutive_timeouts = 0
        self._circuit_breaker_threshold = 3
        # Adaptive rate limiting
        self._base_interval = 0.3
        self._adaptive_interval = 0.3
        # Truncation tracking
        self._truncated_combos = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx async client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout, connect=10.0),
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                ),
                headers={
                    "User-Agent": "Descomplicita/1.0",
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self._client

    @property
    def truncated_combos(self) -> int:
        return self._truncated_combos

    async def _rate_limit(self) -> None:
        """Enforce adaptive rate limiting (async-safe)."""
        async with self._lock:
            interval = self._adaptive_interval
            elapsed = time.time() - self._last_request_time
            if elapsed < interval:
                sleep_time = interval - elapsed
                logger.debug("Rate limiting: sleeping %.3fs", sleep_time)
                await asyncio.sleep(sleep_time)
            self._last_request_time = time.time()
            self._request_count += 1

    async def _adjust_rate(self, response_time: float, was_timeout: bool = False) -> None:
        """Adapt rate limit interval based on server responsiveness."""
        async with self._lock:
            if was_timeout or response_time > 5.0:
                self._adaptive_interval = min(2.0, self._adaptive_interval * 2)
                logger.debug("Rate limit increased to %.1fs", self._adaptive_interval)
            elif response_time < 2.0 and self._adaptive_interval > self._base_interval:
                self._adaptive_interval = max(
                    self._base_interval,
                    self._adaptive_interval * 0.8,
                )
                logger.debug("Rate limit decreased to %.1fs", self._adaptive_interval)

    async def fetch_page(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: int,
        uf: str | None = None,
        pagina: int = 1,
        tamanho: int = PNCP_PAGE_SIZE,
    ) -> dict[str, Any]:
        """Fetch a single page of procurement data from PNCP API."""
        await self._rate_limit()

        data_inicial_fmt = data_inicial.replace("-", "")
        data_final_fmt = data_final.replace("-", "")

        params: dict[str, Any] = {
            "dataInicial": data_inicial_fmt,
            "dataFinal": data_final_fmt,
            "codigoModalidadeContratacao": modalidade,
            "pagina": pagina,
            "tamanhoPagina": tamanho,
        }

        if uf:
            params["uf"] = uf

        url = f"{self.BASE_URL}/contratacoes/publicacao"
        client = await self._get_client()

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(
                    "Request %s params=%s attempt=%s/%s",
                    url,
                    params,
                    attempt + 1,
                    self.config.max_retries + 1,
                )

                req_start = time.time()
                response = await client.get(url, params=params)
                req_elapsed = time.time() - req_start

                await self._adjust_rate(req_elapsed)
                async with self._lock:
                    self._consecutive_timeouts = 0
                    self._total_fetch_count += 1

                if response.status_code == 429:
                    async with self._lock:
                        self._rate_limit_count += 1
                        ratio = self._rate_limit_count / self._total_fetch_count
                        if ratio > 0.20:
                            logger.warning(
                                "High 429 rate: %s/%s (%.0f%%) requests rate-limited",
                                self._rate_limit_count,
                                self._total_fetch_count,
                                ratio * 100,
                            )
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning("Rate limited (429). Waiting %ss", retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code == 200:
                    logger.debug(
                        "Success: fetched page %s (%s items)",
                        pagina,
                        len(response.json().get("data", [])),
                    )
                    return response.json()

                if response.status_code == 204:
                    logger.debug("No content (204) for page %s", pagina)
                    return {
                        "data": [],
                        "totalRegistros": 0,
                        "totalPaginas": 0,
                        "paginaAtual": pagina,
                        "temProximaPagina": False,
                    }

                if response.status_code not in self.config.retryable_status_codes:
                    error_msg = f"API returned non-retryable status {response.status_code}: {response.text[:200]}"
                    raise PNCPAPIError(error_msg)

                if attempt < self.config.max_retries:
                    delay = calculate_delay(attempt, self.config)
                    logger.warning(
                        "Error %s. Attempt %s/%s. Retrying in %.1fs",
                        response.status_code,
                        attempt + 1,
                        self.config.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise PNCPAPIError(
                        f"Failed after {self.config.max_retries + 1} attempts. Last status: {response.status_code}"
                    )

            except httpx.TimeoutException as e:
                await self._adjust_rate(0, was_timeout=True)
                async with self._lock:
                    self._consecutive_timeouts += 1
                    ct = self._consecutive_timeouts
                if ct >= self._circuit_breaker_threshold:
                    pause = min(60, 15 * (ct // self._circuit_breaker_threshold))
                    logger.warning(
                        "Circuit breaker: %s consecutive timeouts, pausing %ss",
                        ct,
                        pause,
                    )
                    await asyncio.sleep(pause)

                if attempt < self.config.max_retries:
                    delay = calculate_delay(attempt, self.config)
                    logger.warning(
                        "Timeout: %s. Attempt %s/%s. Retrying in %.1fs",
                        e,
                        attempt + 1,
                        self.config.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise PNCPAPIError(
                        f"Failed after {self.config.max_retries + 1} attempts. Last exception: {type(e).__name__}: {e}"
                    ) from e

            except (httpx.ConnectError, httpx.ReadError, ConnectionError, TimeoutError) as e:
                await self._adjust_rate(0, was_timeout=True)
                async with self._lock:
                    self._consecutive_timeouts += 1
                    ct = self._consecutive_timeouts
                if ct >= self._circuit_breaker_threshold:
                    pause = min(60, 15 * (ct // self._circuit_breaker_threshold))
                    logger.warning(
                        "Circuit breaker: %s consecutive timeouts, pausing %ss",
                        ct,
                        pause,
                    )
                    await asyncio.sleep(pause)

                if attempt < self.config.max_retries:
                    delay = calculate_delay(attempt, self.config)
                    logger.warning(
                        "Exception %s: %s. Attempt %s/%s. Retrying in %.1fs",
                        type(e).__name__,
                        e,
                        attempt + 1,
                        self.config.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise PNCPAPIError(
                        f"Failed after {self.config.max_retries + 1} attempts. Last exception: {type(e).__name__}: {e}"
                    ) from e

        raise PNCPAPIError("Unexpected: exhausted retries without raising exception")

    @staticmethod
    def _chunk_date_range(data_inicial: str, data_final: str, max_days: int = 30) -> list[tuple[str, str]]:
        """Split a date range into chunks of max_days."""
        d_start = date.fromisoformat(data_inicial)
        d_end = date.fromisoformat(data_final)
        chunks: list[tuple[str, str]] = []
        current = d_start
        while current <= d_end:
            chunk_end = min(current + timedelta(days=max_days - 1), d_end)
            chunks.append((current.isoformat(), chunk_end.isoformat()))
            current = chunk_end + timedelta(days=1)
        return chunks

    async def _fetch_by_uf(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: int,
        uf: str | None,
        on_progress: Callable[[int, int, int], None] | None,
        max_pages: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch all pages for a specific modality and UF combination."""
        pagina = 1
        items_fetched = 0
        results: list[dict[str, Any]] = []

        while True:
            response = await self.fetch_page(
                data_inicial=data_inicial,
                data_final=data_final,
                modalidade=modalidade,
                uf=uf,
                pagina=pagina,
            )

            data = response.get("data", [])
            total_pages = response.get("totalPaginas", 1)
            total_registros = response.get("totalRegistros", 0)
            paginas_restantes = response.get("paginasRestantes", 0)
            tem_proxima = paginas_restantes > 0

            logger.info(
                "Page %s/%s: %s items (total records: %s)",
                pagina,
                total_pages,
                len(data),
                total_registros,
            )

            if on_progress:
                on_progress(pagina, total_pages, items_fetched + len(data))

            for item in data:
                results.append(item)
                items_fetched += 1

            if not tem_proxima:
                logger.info(
                    "Finished fetching modalidade=%s, UF=%s: %s total items across %s pages",
                    modalidade,
                    uf or "ALL",
                    items_fetched,
                    pagina,
                )
                break

            if max_pages > 0 and pagina >= max_pages:
                logger.info(
                    "Reached max_pages=%s for modalidade=%s, UF=%s: %s items fetched (total available: %s)",
                    max_pages,
                    modalidade,
                    uf or "ALL",
                    items_fetched,
                    total_registros,
                )
                self._truncated_combos += 1
                break

            pagina += 1

        return results

    async def _fetch_uf_modalidade(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: int,
        uf: str | None,
        on_progress: Callable[[int, int, int], None] | None = None,
        max_pages: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch all pages for a single UF+modalidade combination with caching."""
        label = f"modalidade={modalidade}, UF={uf or 'ALL'}"
        logger.info("Fetching %s", label)
        try:
            items = await self._fetch_by_uf(data_inicial, data_final, modalidade, uf, on_progress, max_pages)
            logger.info("Completed %s: %s items", label, len(items))
            return items
        except PNCPAPIError as e:
            logger.warning("Skipping %s: %s", label, e)
            return []

    async def fetch_all(
        self,
        data_inicial: str,
        data_final: str,
        ufs: list[str] | None = None,
        modalidades: list[int] | None = None,
        on_progress: Callable[[int, int, int], None] | None = None,
        max_pages: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch all procurement records with concurrent UF x modalidade fetching."""
        self._truncated_combos = 0
        self._consecutive_timeouts = 0
        self._adaptive_interval = self._base_interval

        date_chunks = self._chunk_date_range(data_inicial, data_final)
        if len(date_chunks) > 1:
            logger.info(
                "Date range %s to %s split into %s chunks of up to 30 days",
                data_inicial,
                data_final,
                len(date_chunks),
            )

        num_ufs = len(ufs) if ufs else 1
        if modalidades:
            modalidades_to_fetch = modalidades
        elif num_ufs > MODALIDADE_REDUCTION_UF_THRESHOLD:
            modalidades_to_fetch = PRIORITY_MODALIDADES
            logger.info(
                "Using %s priority modalidades (reduced from %s) for %s UFs",
                len(modalidades_to_fetch),
                len(DEFAULT_MODALIDADES),
                num_ufs,
            )
        else:
            modalidades_to_fetch = DEFAULT_MODALIDADES

        seen_ids: set[str] = set()
        all_results: list[dict[str, Any]] = []

        for chunk_idx, (chunk_start, chunk_end) in enumerate(date_chunks):
            if len(date_chunks) > 1:
                logger.info(
                    "Processing date chunk %s/%s: %s to %s",
                    chunk_idx + 1,
                    len(date_chunks),
                    chunk_start,
                    chunk_end,
                )

            tasks: list[tuple[int, str | None]] = []
            for modalidade in modalidades_to_fetch:
                if ufs:
                    for uf in ufs:
                        tasks.append((modalidade, uf))
                else:
                    tasks.append((modalidade, None))

            effective_max_pages = max_pages
            if max_pages > 0 and len(tasks) > 0:
                effective_max_pages = min(max_pages, max(2, 600 // len(tasks)))
                if effective_max_pages != max_pages:
                    logger.info(
                        "Reduced max_pages %s -> %s for %s tasks (cap ~600 total pages)",
                        max_pages,
                        effective_max_pages,
                        len(tasks),
                    )

            logger.info(
                "Launching %s concurrent fetches (%s modalities x %s UFs), max_pages=%s",
                len(tasks),
                len(modalidades_to_fetch),
                len(ufs or ["ALL"]),
                effective_max_pages,
            )

            # Use semaphore to limit concurrency to 3 (same as old ThreadPoolExecutor)
            sem = asyncio.Semaphore(3)

            async def _fetch_with_sem(mod: int, u: str | None) -> list[dict[str, Any]]:
                async with sem:
                    return await self._fetch_uf_modalidade(
                        chunk_start, chunk_end, mod, u, on_progress, effective_max_pages
                    )

            coros = [_fetch_with_sem(mod, u) for mod, u in tasks]
            results = await asyncio.gather(*coros, return_exceptions=True)

            for (modalidade, uf), result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.warning(
                        "Unexpected error fetching modalidade=%s, UF=%s: %s",
                        modalidade,
                        uf or "ALL",
                        result,
                    )
                    continue
                for item in result:
                    normalized = self._normalize_item(item)
                    item_id = normalized.get("numeroControlePNCP", "")
                    if item_id and item_id not in seen_ids:
                        seen_ids.add(item_id)
                        all_results.append(normalized)

        logger.info(
            "Fetch complete: %s unique records across %s modalities and %s date chunks",
            len(seen_ids),
            len(modalidades_to_fetch),
            len(date_chunks),
        )
        return all_results

    @staticmethod
    def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
        """Flatten nested PNCP API response into the flat format expected downstream."""
        unidade = item.get("unidadeOrgao") or {}
        orgao = item.get("orgaoEntidade") or {}
        item["uf"] = unidade.get("ufSigla", "")
        item["municipio"] = unidade.get("municipioNome", "")
        item["nomeOrgao"] = orgao.get("razaoSocial", "") or unidade.get("nomeUnidade", "")
        item["codigoCompra"] = item.get("numeroControlePNCP", "")
        item["cnpj"] = orgao.get("cnpj", "")
        return item

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("Client closed. Total requests made: %s", self._request_count)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
