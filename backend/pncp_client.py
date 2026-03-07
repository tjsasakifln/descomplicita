"""Resilient HTTP client for PNCP API."""

import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable, Dict, Generator, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import RetryConfig, DEFAULT_MODALIDADES
from exceptions import PNCPAPIError

# PNCP consulta API max page size is 50 (despite manual claiming 500)
# Tested: 100/200/500 all return HTTP 400 "Tamanho de página inválido"
PNCP_PAGE_SIZE = 50

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry with TTL support."""
    data: list
    created_at: float
    ttl: float
    last_accessed: float = 0.0

    def __post_init__(self):
        self.last_accessed = self.created_at

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Args:
        attempt: Current retry attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds

    Example:
        With base_delay=2, exponential_base=2, max_delay=60:
        - Attempt 0: 2s
        - Attempt 1: 4s
        - Attempt 2: 8s
        - Attempt 3: 16s
        - Attempt 4: 32s
        - Attempt 5: 60s (capped)
    """
    delay = min(
        config.base_delay * (config.exponential_base**attempt), config.max_delay
    )

    if config.jitter:
        # Add ±50% jitter to prevent thundering herd
        delay *= random.uniform(0.5, 1.5)

    return delay


class PNCPClient:
    """Resilient HTTP client for PNCP API with retry logic and rate limiting."""

    BASE_URL = "https://pncp.gov.br/api/consulta/v1"

    def __init__(self, config: RetryConfig | None = None):
        """
        Initialize PNCP client.

        Args:
            config: Retry configuration (uses defaults if not provided)
        """
        self.config = config or RetryConfig()
        self.session = self._create_session()
        self._request_count = 0
        self._last_request_time = 0.0
        self._lock = threading.Lock()
        # 429 rate limit monitoring
        self._rate_limit_count = 0
        self._total_fetch_count = 0
        # Circuit breaker: consecutive timeout counter (shared across threads)
        self._consecutive_timeouts = 0
        self._circuit_breaker_threshold = 3
        # Adaptive rate limiting: dynamic interval based on response times
        self._base_interval = 0.3  # 300ms default
        self._adaptive_interval = 0.3
        # Truncation tracking: combos that hit max_pages with more data available
        self._truncated_combos = 0
        self._truncated_lock = threading.Lock()
        # Cache layer (SP-001.2)
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_lock = threading.Lock()
        self._cache_hits = 0
        self._cache_misses = 0
        self.cache_ttl = 4 * 3600  # 4 hours
        self.max_cache_entries = 500

    @staticmethod
    def _cache_key(uf: str | None, modalidade: int, data_inicial: str, data_final: str) -> str:
        """Generate cache key from query parameters."""
        return f"{uf or 'ALL'}:{modalidade}:{data_inicial}:{data_final}"

    def _cache_get(self, key: str) -> list | None:
        """Get data from cache if present and not expired (thread-safe)."""
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                self._cache_misses += 1
                return None
            if entry.is_expired:
                del self._cache[key]
                self._cache_misses += 1
                return None
            entry.last_accessed = time.time()
            self._cache_hits += 1
            return entry.data

    def _cache_put(self, key: str, data: list) -> None:
        """Store data in cache with LRU eviction (thread-safe)."""
        with self._cache_lock:
            # Evict expired entries first
            now = time.time()
            expired = [k for k, v in self._cache.items() if v.is_expired]
            for k in expired:
                del self._cache[k]
            # LRU eviction if at capacity
            while len(self._cache) >= self.max_cache_entries:
                lru_key = min(self._cache, key=lambda k: self._cache[k].last_accessed)
                del self._cache[lru_key]
            self._cache[key] = CacheEntry(
                data=data, created_at=now, ttl=self.cache_ttl
            )

    def cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        with self._cache_lock:
            total = self._cache_hits + self._cache_misses
            return {
                "entries": len(self._cache),
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_ratio": round(self._cache_hits / total, 3) if total > 0 else 0.0,
            }

    def cache_clear(self) -> int:
        """Clear all cache entries. Returns number of entries removed."""
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            return count

    @property
    def truncated_combos(self) -> int:
        """Number of UF×modalidade combos that were truncated by max_pages."""
        with self._truncated_lock:
            return self._truncated_combos

    def _create_session(self) -> requests.Session:
        """
        Create HTTP session with automatic retry strategy.

        Returns:
            Configured requests.Session with retry adapter
        """
        session = requests.Session()

        # Configure retry strategy using urllib3.
        # Use only 1 urllib3-level retry (for transient connection errors).
        # Application-level retry in fetch_page() handles status-code retries
        # separately. Using both at full count causes compounding delays
        # (e.g., 3 urllib3 × 3 app retries = 9 attempts per page).
        retry_strategy = Retry(
            total=1,
            backoff_factor=1.0,
            status_forcelist=(),  # Let fetch_page() handle status codes
            allowed_methods=["GET"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set default headers
        session.headers.update({
            "User-Agent": "Descomplicita/1.0 (procurement-search)",
            "Accept": "application/json",
        })

        return session

    def _rate_limit(self) -> None:
        """
        Enforce adaptive rate limiting (thread-safe).

        Uses a dynamic interval that increases when the PNCP server is slow
        (avg response > 5s or consecutive timeouts) and decreases back to
        baseline when the server is responsive.
        """
        with self._lock:
            interval = self._adaptive_interval
            elapsed = time.time() - self._last_request_time
            if elapsed < interval:
                sleep_time = interval - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s")
                time.sleep(sleep_time)

            self._last_request_time = time.time()
            self._request_count += 1

    def _adjust_rate(self, response_time: float, was_timeout: bool = False) -> None:
        """Adapt rate limit interval based on server responsiveness."""
        with self._lock:
            if was_timeout or response_time > 5.0:
                # Server is struggling — double the interval (max 2s)
                self._adaptive_interval = min(2.0, self._adaptive_interval * 2)
                logger.debug(f"Rate limit increased to {self._adaptive_interval:.1f}s")
            elif response_time < 2.0 and self._adaptive_interval > self._base_interval:
                # Server is responsive — decay back toward baseline
                self._adaptive_interval = max(
                    self._base_interval,
                    self._adaptive_interval * 0.8,
                )
                logger.debug(f"Rate limit decreased to {self._adaptive_interval:.1f}s")

    def fetch_page(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: int,
        uf: str | None = None,
        pagina: int = 1,
        tamanho: int = PNCP_PAGE_SIZE,
    ) -> Dict[str, Any]:
        """
        Fetch a single page of procurement data from PNCP API.

        Args:
            data_inicial: Start date in YYYY-MM-DD format
            data_final: End date in YYYY-MM-DD format
            modalidade: Modality code (codigoModalidadeContratacao), e.g., 6 for Pregão Eletrônico
            uf: Optional state code (e.g., "SP", "RJ")
            pagina: Page number (1-indexed)
            tamanho: Page size (default 500, PNCP API max)

        Returns:
            API response as dictionary containing:
                - data: List of procurement records
                - totalRegistros: Total number of records
                - totalPaginas: Total number of pages
                - paginaAtual: Current page number
                - temProximaPagina: Boolean indicating if more pages exist

        Raises:
            PNCPAPIError: On non-retryable errors or after max retries
            PNCPRateLimitError: If rate limit persists after retries
        """
        self._rate_limit()

        # Convert dates from YYYY-MM-DD to yyyyMMdd (PNCP API format)
        data_inicial_fmt = data_inicial.replace("-", "")
        data_final_fmt = data_final.replace("-", "")

        params = {
            "dataInicial": data_inicial_fmt,
            "dataFinal": data_final_fmt,
            "codigoModalidadeContratacao": modalidade,
            "pagina": pagina,
            "tamanhoPagina": tamanho,
        }

        if uf:
            params["uf"] = uf

        url = f"{self.BASE_URL}/contratacoes/publicacao"

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(
                    f"Request {url} params={params} attempt={attempt + 1}/"
                    f"{self.config.max_retries + 1}"
                )

                req_start = time.time()
                response = self.session.get(
                    url, params=params, timeout=self.config.timeout
                )
                req_elapsed = time.time() - req_start

                # Adaptive rate + circuit breaker: reset on success
                self._adjust_rate(req_elapsed)
                with self._lock:
                    self._consecutive_timeouts = 0

                # Track total fetches for 429 monitoring
                with self._lock:
                    self._total_fetch_count += 1

                # Handle rate limiting specifically
                if response.status_code == 429:
                    with self._lock:
                        self._rate_limit_count += 1
                        ratio = self._rate_limit_count / self._total_fetch_count
                        if ratio > 0.20:
                            logger.warning(
                                f"High 429 rate: {self._rate_limit_count}/{self._total_fetch_count} "
                                f"({ratio:.0%}) requests rate-limited"
                            )
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"Rate limited (429). Waiting {retry_after}s "
                        f"(Retry-After header)"
                    )
                    time.sleep(retry_after)
                    continue

                # Success case
                if response.status_code == 200:
                    logger.debug(
                        f"Success: fetched page {pagina} "
                        f"({len(response.json().get('data', []))} items)"
                    )
                    return response.json()

                # No content - empty results (valid response)
                if response.status_code == 204:
                    logger.debug(f"No content (204) for page {pagina} - no results")
                    return {
                        "data": [],
                        "totalRegistros": 0,
                        "totalPaginas": 0,
                        "paginaAtual": pagina,
                        "temProximaPagina": False,
                    }

                # Non-retryable errors - fail immediately
                if response.status_code not in self.config.retryable_status_codes:
                    logger.error(
                        f"PNCP API error: status={response.status_code} "
                        f"url={url} params={params} "
                        f"body={response.text[:500]}"
                    )
                    error_msg = (
                        f"API returned non-retryable status {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    raise PNCPAPIError(error_msg)

                # Retryable errors - wait and retry
                if attempt < self.config.max_retries:
                    delay = calculate_delay(attempt, self.config)
                    logger.warning(
                        f"Error {response.status_code}. "
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                else:
                    # Last attempt failed
                    error_msg = (
                        f"Failed after {self.config.max_retries + 1} attempts. "
                        f"Last status: {response.status_code}"
                    )
                    logger.error(error_msg)
                    raise PNCPAPIError(error_msg)

            except self.config.retryable_exceptions as e:
                # Circuit breaker: track consecutive timeouts
                self._adjust_rate(0, was_timeout=True)
                with self._lock:
                    self._consecutive_timeouts += 1
                    ct = self._consecutive_timeouts
                if ct >= self._circuit_breaker_threshold:
                    pause = 15 * (ct // self._circuit_breaker_threshold)
                    pause = min(pause, 60)
                    logger.warning(
                        f"Circuit breaker: {ct} consecutive timeouts, "
                        f"pausing {pause}s to let PNCP recover"
                    )
                    time.sleep(pause)

                if attempt < self.config.max_retries:
                    delay = calculate_delay(attempt, self.config)
                    logger.warning(
                        f"Exception {type(e).__name__}: {e}. "
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                else:
                    error_msg = (
                        f"Failed after {self.config.max_retries + 1} attempts. "
                        f"Last exception: {type(e).__name__}: {e}"
                    )
                    logger.error(error_msg)
                    raise PNCPAPIError(error_msg) from e

        # Should never reach here, but just in case
        raise PNCPAPIError("Unexpected: exhausted retries without raising exception")

    @staticmethod
    def _chunk_date_range(
        data_inicial: str, data_final: str, max_days: int = 30
    ) -> list[tuple[str, str]]:
        """
        Split a date range into chunks of max_days.

        The PNCP API may return incomplete results for large date ranges.
        This method splits the range into smaller windows to ensure
        complete data retrieval.

        Args:
            data_inicial: Start date YYYY-MM-DD
            data_final: End date YYYY-MM-DD
            max_days: Maximum days per chunk (default 30)

        Returns:
            List of (start, end) date string tuples
        """
        d_start = date.fromisoformat(data_inicial)
        d_end = date.fromisoformat(data_final)
        chunks: list[tuple[str, str]] = []

        current = d_start
        while current <= d_end:
            chunk_end = min(current + timedelta(days=max_days - 1), d_end)
            chunks.append((current.isoformat(), chunk_end.isoformat()))
            current = chunk_end + timedelta(days=1)

        return chunks

    def _fetch_uf_modalidade(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: int,
        uf: str | None,
        on_progress: Callable[[int, int, int], None] | None = None,
        max_pages: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all pages for a single UF+modalidade combination.

        Thread-safe wrapper around _fetch_by_uf that collects results into a list.
        Used by ThreadPoolExecutor in fetch_all for parallel fetching.
        """
        label = f"modalidade={modalidade}, UF={uf or 'ALL'}"
        cache_key = self._cache_key(uf, modalidade, data_inicial, data_final)

        # Check cache first
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for {uf or 'ALL'}:{modalidade} ({len(cached)} items)")
            return cached

        logger.info(f"Fetching {label}")
        try:
            items = list(self._fetch_by_uf(data_inicial, data_final, modalidade, uf, on_progress, max_pages))
            logger.info(f"Completed {label}: {len(items)} items")
            # Store raw results in cache
            self._cache_put(cache_key, items)
            return items
        except PNCPAPIError as e:
            logger.warning(f"Skipping {label}: {e}")
            return []

    def fetch_all(
        self,
        data_inicial: str,
        data_final: str,
        ufs: list[str] | None = None,
        modalidades: list[int] | None = None,
        on_progress: Callable[[int, int, int], None] | None = None,
        max_pages: int = 0,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch all procurement records with parallel UF×modalidade fetching.

        Uses ThreadPoolExecutor to fetch all UF+modalidade combinations in parallel,
        dramatically reducing total fetch time (from ~10min to ~2min for 3 UFs × 5 modalities).

        Automatically splits date ranges > 30 days into 30-day chunks to avoid
        PNCP API limitations with large ranges.

        NOTE: The PNCP consulta API does NOT support server-side keyword filtering.
        The `palavraChave` parameter is silently ignored (verified 2026-03-07).
        Sector-specific filtering is done client-side by filter_batch().

        Args:
            data_inicial: Start date in YYYY-MM-DD format
            data_final: End date in YYYY-MM-DD format
            ufs: Optional list of state codes (e.g., ["SP", "RJ"])
            modalidades: Optional list of modality codes
            on_progress: Optional callback(current_page, total_pages, items_fetched)

        Yields:
            Dict[str, Any]: Individual procurement record
        """
        # Reset truncation counter for this search
        with self._truncated_lock:
            self._truncated_combos = 0
            self._consecutive_timeouts = 0
            self._adaptive_interval = self._base_interval

        date_chunks = self._chunk_date_range(data_inicial, data_final)
        if len(date_chunks) > 1:
            logger.info(
                f"Date range {data_inicial} to {data_final} split into "
                f"{len(date_chunks)} chunks of up to 30 days"
            )

        modalidades_to_fetch = modalidades or DEFAULT_MODALIDADES
        seen_ids: set[str] = set()

        for chunk_idx, (chunk_start, chunk_end) in enumerate(date_chunks):
            if len(date_chunks) > 1:
                logger.info(
                    f"Processing date chunk {chunk_idx + 1}/{len(date_chunks)}: "
                    f"{chunk_start} to {chunk_end}"
                )

            # Build list of (modalidade, uf) tasks to run in parallel
            # NOTE: palavraChave parameter is NOT supported by the PNCP consulta API
            # (tested 2026-03-07: API silently ignores it, returns unfiltered results).
            # Sector filtering is done client-side by filter_batch() using sector keywords.
            tasks: list[tuple[int, str | None]] = []
            for modalidade in modalidades_to_fetch:
                if ufs:
                    for uf in ufs:
                        tasks.append((modalidade, uf))
                else:
                    tasks.append((modalidade, None))

            # Dynamically reduce max_pages when task count is high to cap
            # total requests at ~600.  This prevents cascading timeouts when
            # the user selects many UFs (e.g., 27 UFs × 7 mod = 189 combos).
            # Formula: 600 / num_tasks, clamped to [2, max_pages].
            effective_max_pages = max_pages
            if max_pages > 0 and len(tasks) > 0:
                effective_max_pages = min(max_pages, max(2, 600 // len(tasks)))
                if effective_max_pages != max_pages:
                    logger.info(
                        f"Reduced max_pages {max_pages} → {effective_max_pages} "
                        f"for {len(tasks)} tasks (cap ~600 total pages)"
                    )

            logger.info(
                f"Launching {len(tasks)} parallel fetches "
                f"({len(modalidades_to_fetch)} modalities × {len(ufs or ['ALL'])} UFs), "
                f"max_pages={effective_max_pages}"
            )

            # Parallel fetch: each UF×modalidade runs in its own thread.
            # Limit to 3 workers to avoid overwhelming the PNCP API server.
            # The government server can't handle many concurrent connections
            # from the same IP — higher concurrency causes ReadTimeoutError
            # cascades that compound with retries and waste the entire budget.
            max_workers = min(len(tasks), 3)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {
                    executor.submit(
                        self._fetch_uf_modalidade,
                        chunk_start, chunk_end, modalidade, uf, on_progress, effective_max_pages,
                    ): (modalidade, uf)
                    for modalidade, uf in tasks
                }

                for future in as_completed(future_to_task):
                    modalidade, uf = future_to_task[future]
                    try:
                        items = future.result()
                    except Exception as e:
                        logger.warning(
                            f"Unexpected error fetching modalidade={modalidade}, "
                            f"UF={uf or 'ALL'}: {e}"
                        )
                        continue

                    for item in items:
                        normalized = self._normalize_item(item)
                        item_id = normalized.get("numeroControlePNCP", "")
                        if item_id and item_id not in seen_ids:
                            seen_ids.add(item_id)
                            yield normalized

        logger.info(
            f"Fetch complete: {len(seen_ids)} unique records across "
            f"{len(modalidades_to_fetch)} modalities and {len(date_chunks)} date chunks"
        )

    @staticmethod
    def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested PNCP API response into the flat format expected by
        filter.py, excel.py and llm.py.

        The PNCP API nests org/location data inside ``orgaoEntidade`` and
        ``unidadeOrgao`` objects.  The rest of the codebase expects flat
        top-level keys: ``uf``, ``municipio``, ``nomeOrgao``, ``codigoCompra``.
        """
        unidade = item.get("unidadeOrgao") or {}
        orgao = item.get("orgaoEntidade") or {}

        item["uf"] = unidade.get("ufSigla", "")
        item["municipio"] = unidade.get("municipioNome", "")
        item["nomeOrgao"] = orgao.get("razaoSocial", "") or unidade.get("nomeUnidade", "")
        item["codigoCompra"] = item.get("numeroControlePNCP", "")
        item["cnpj"] = orgao.get("cnpj", "")

        return item

    def _fetch_by_uf(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: int,
        uf: str | None,
        on_progress: Callable[[int, int, int], None] | None,
        max_pages: int = 0,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch all pages for a specific modality and UF combination.

        This helper method handles pagination for a single modality/UF by following
        the API's `temProximaPagina` flag. It continues fetching pages
        until no more pages are available.

        Args:
            data_inicial: Start date in YYYY-MM-DD format
            data_final: End date in YYYY-MM-DD format
            modalidade: Modality code (codigoModalidadeContratacao)
            uf: State code (e.g., "SP") or None for all states
            on_progress: Optional progress callback

        Yields:
            Dict[str, Any]: Individual procurement record
        """
        pagina = 1
        items_fetched = 0
        total_pages = None

        while True:
            logger.debug(
                f"Fetching page {pagina} for modalidade={modalidade}, UF={uf or 'ALL'} "
                f"(date range: {data_inicial} to {data_final})"
            )

            response = self.fetch_page(
                data_inicial=data_inicial,
                data_final=data_final,
                modalidade=modalidade,
                uf=uf,
                pagina=pagina,
            )

            # Extract pagination metadata
            # PNCP API uses: numeroPagina, totalPaginas, paginasRestantes, empty
            data = response.get("data", [])
            total_pages = response.get("totalPaginas", 1)
            total_registros = response.get("totalRegistros", 0)
            paginas_restantes = response.get("paginasRestantes", 0)
            tem_proxima = paginas_restantes > 0

            # Log page info
            logger.info(
                f"Page {pagina}/{total_pages}: {len(data)} items "
                f"(total records: {total_registros})"
            )

            # Call progress callback if provided
            if on_progress:
                on_progress(pagina, total_pages, items_fetched + len(data))

            # Yield individual items
            for item in data:
                yield item
                items_fetched += 1

            # Check if there are more pages
            if not tem_proxima:
                logger.info(
                    f"Finished fetching modalidade={modalidade}, UF={uf or 'ALL'}: "
                    f"{items_fetched} total items across {pagina} pages"
                )
                break

            # Stop if we've reached the max pages limit
            if max_pages > 0 and pagina >= max_pages:
                logger.info(
                    f"Reached max_pages={max_pages} for modalidade={modalidade}, "
                    f"UF={uf or 'ALL'}: {items_fetched} items fetched "
                    f"(total available: {total_registros})"
                )
                # Track truncation for user transparency
                with self._truncated_lock:
                    self._truncated_combos += 1
                break

            # Move to next page
            pagina += 1

    def close(self) -> None:
        """Close the HTTP session and cleanup resources."""
        self.session.close()
        logger.debug(f"Session closed. Total requests made: {self._request_count}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
