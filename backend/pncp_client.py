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

    def _create_session(self) -> requests.Session:
        """
        Create HTTP session with automatic retry strategy.

        Returns:
            Configured requests.Session with retry adapter
        """
        session = requests.Session()

        # Configure retry strategy using urllib3
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.base_delay,
            status_forcelist=self.config.retryable_status_codes,
            allowed_methods=["GET"],
            raise_on_status=False,  # We'll handle status codes manually
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set default headers
        session.headers.update({
            "User-Agent": "BidIQ/1.0 (procurement-search; contact@bidiq.com.br)",
            "Accept": "application/json",
        })

        return session

    def _rate_limit(self) -> None:
        """
        Enforce rate limiting: maximum 10 requests per second (thread-safe).

        Sleeps if necessary to maintain minimum interval between requests.
        """
        MIN_INTERVAL = 0.1  # 100ms = 10 requests/second

        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < MIN_INTERVAL:
                sleep_time = MIN_INTERVAL - elapsed
                logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s")
                time.sleep(sleep_time)

            self._last_request_time = time.time()
            self._request_count += 1

    def fetch_page(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: int,
        uf: str | None = None,
        pagina: int = 1,
        tamanho: int = PNCP_PAGE_SIZE,
        palavra_chave: str | None = None,
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

        if palavra_chave:
            params["palavraChave"] = palavra_chave

        url = f"{self.BASE_URL}/contratacoes/publicacao"

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(
                    f"Request {url} params={params} attempt={attempt + 1}/"
                    f"{self.config.max_retries + 1}"
                )

                response = self.session.get(
                    url, params=params, timeout=self.config.timeout
                )

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

    def fetch_atas_page(
        self,
        data_inicial: str,
        data_final: str,
        uf: str | None = None,
        pagina: int = 1,
        tamanho: int = PNCP_PAGE_SIZE,
        palavra_chave: str | None = None,
    ) -> Dict[str, Any]:
        """
        Fetch a single page of Atas de Registro de Preco from PNCP API.

        Uses the /atas endpoint instead of /contratacoes/publicacao.
        Shares the same rate limiting, retry, and session as fetch_page.

        Args:
            data_inicial: Start date in YYYY-MM-DD format
            data_final: End date in YYYY-MM-DD format
            uf: Optional state code (e.g., "SP", "RJ")
            pagina: Page number (1-indexed)
            tamanho: Page size (default 50)
            palavra_chave: Optional keyword filter

        Returns:
            API response as dictionary (same structure as fetch_page)

        Raises:
            PNCPAPIError: On non-retryable errors or after max retries
        """
        self._rate_limit()

        data_inicial_fmt = data_inicial.replace("-", "")
        data_final_fmt = data_final.replace("-", "")

        params = {
            "dataInicial": data_inicial_fmt,
            "dataFinal": data_final_fmt,
            "pagina": pagina,
            "tamanhoPagina": tamanho,
        }

        if uf:
            params["uf"] = uf

        if palavra_chave:
            params["palavraChave"] = palavra_chave

        url = f"{self.BASE_URL}/atas"

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(
                    f"Request {url} params={params} attempt={attempt + 1}/"
                    f"{self.config.max_retries + 1}"
                )

                response = self.session.get(
                    url, params=params, timeout=self.config.timeout
                )

                with self._lock:
                    self._total_fetch_count += 1

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

                if response.status_code == 200:
                    logger.debug(
                        f"Success: fetched atas page {pagina} "
                        f"({len(response.json().get('data', []))} items)"
                    )
                    return response.json()

                if response.status_code == 204:
                    logger.debug(f"No content (204) for atas page {pagina} - no results")
                    return {
                        "data": [],
                        "totalRegistros": 0,
                        "totalPaginas": 0,
                        "paginaAtual": pagina,
                        "temProximaPagina": False,
                    }

                if response.status_code not in self.config.retryable_status_codes:
                    logger.error(
                        f"PNCP Atas API error: status={response.status_code} "
                        f"url={url} params={params} "
                        f"body={response.text[:500]}"
                    )
                    error_msg = (
                        f"API returned non-retryable status {response.status_code}: "
                        f"{response.text[:200]}"
                    )
                    raise PNCPAPIError(error_msg)

                if attempt < self.config.max_retries:
                    delay = calculate_delay(attempt, self.config)
                    logger.warning(
                        f"Error {response.status_code}. "
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                else:
                    error_msg = (
                        f"Failed after {self.config.max_retries + 1} attempts. "
                        f"Last status: {response.status_code}"
                    )
                    logger.error(error_msg)
                    raise PNCPAPIError(error_msg)

            except self.config.retryable_exceptions as e:
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

        raise PNCPAPIError("Unexpected: exhausted retries without raising exception")

    def _fetch_atas_by_uf(
        self,
        data_inicial: str,
        data_final: str,
        uf: str | None,
        on_progress: Callable[[int, int, int], None] | None,
        palavra_chave: str | None = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Fetch all pages of atas for a specific UF. Identical pagination to _fetch_by_uf."""
        pagina = 1
        items_fetched = 0

        while True:
            logger.debug(
                f"Fetching atas page {pagina} for UF={uf or 'ALL'} "
                f"(date range: {data_inicial} to {data_final})"
            )

            response = self.fetch_atas_page(
                data_inicial=data_inicial,
                data_final=data_final,
                uf=uf,
                pagina=pagina,
                palavra_chave=palavra_chave,
            )

            data = response.get("data", [])
            total_pages = response.get("totalPaginas", 1)
            total_registros = response.get("totalRegistros", 0)
            paginas_restantes = response.get("paginasRestantes", 0)
            tem_proxima = paginas_restantes > 0

            logger.info(
                f"Atas page {pagina}/{total_pages}: {len(data)} items "
                f"(total records: {total_registros})"
            )

            if on_progress:
                on_progress(pagina, total_pages, items_fetched + len(data))

            for item in data:
                yield item
                items_fetched += 1

            if not tem_proxima:
                logger.info(
                    f"Finished fetching atas UF={uf or 'ALL'}: "
                    f"{items_fetched} total items across {pagina} pages"
                )
                break

            pagina += 1

    def _fetch_uf_atas(
        self,
        data_inicial: str,
        data_final: str,
        uf: str | None,
        on_progress: Callable[[int, int, int], None] | None = None,
        palavra_chave: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all atas pages for a single UF. Thread-safe wrapper for parallel execution."""
        kw_label = f", palavraChave={palavra_chave}" if palavra_chave else ""
        label = f"atas, UF={uf or 'ALL'}{kw_label}"
        cache_key = f"atas:{uf or 'ALL'}:{data_inicial}:{data_final}" + (f":{palavra_chave}" if palavra_chave else "")

        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for atas {uf or 'ALL'} ({len(cached)} items)")
            return cached

        logger.info(f"Fetching {label}")
        try:
            items = list(self._fetch_atas_by_uf(data_inicial, data_final, uf, on_progress, palavra_chave=palavra_chave))
            logger.info(f"Completed {label}: {len(items)} items")
            self._cache_put(cache_key, items)
            return items
        except PNCPAPIError as e:
            logger.warning(f"Skipping {label}: {e}")
            return []

    def fetch_all_atas(
        self,
        data_inicial: str,
        data_final: str,
        ufs: list[str] | None = None,
        on_progress: Callable[[int, int, int], None] | None = None,
        search_terms: list[str] | None = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch all Atas de Registro de Preco with parallel UF fetching.

        Similar to fetch_all() but targets the /atas endpoint.
        Atas don't have modalidade, so parallelism is over UF × search_terms.

        Yields:
            Dict[str, Any]: Individual ata record with _tipo='ata_registro_preco' tag
        """
        date_chunks = self._chunk_date_range(data_inicial, data_final)
        if len(date_chunks) > 1:
            logger.info(
                f"Atas date range {data_inicial} to {data_final} split into "
                f"{len(date_chunks)} chunks"
            )

        seen_ids: set[str] = set()

        for chunk_idx, (chunk_start, chunk_end) in enumerate(date_chunks):
            if len(date_chunks) > 1:
                logger.info(
                    f"Processing atas chunk {chunk_idx + 1}/{len(date_chunks)}: "
                    f"{chunk_start} to {chunk_end}"
                )

            terms_to_use = search_terms if search_terms else [None]
            tasks: list[tuple[str | None, str | None]] = []
            if ufs:
                for uf in ufs:
                    for term in terms_to_use:
                        tasks.append((uf, term))
            else:
                for term in terms_to_use:
                    tasks.append((None, term))

            terms_info = f" x {len(search_terms)} terms" if search_terms else ""
            logger.info(
                f"Launching {len(tasks)} parallel atas fetches "
                f"({len(ufs or ['ALL'])} UFs{terms_info})"
            )

            max_workers = min(len(tasks), 12)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {
                    executor.submit(
                        self._fetch_uf_atas,
                        chunk_start, chunk_end, uf, on_progress, term,
                    ): uf
                    for uf, term in tasks
                }

                for future in as_completed(future_to_task):
                    uf = future_to_task[future]
                    try:
                        items = future.result()
                    except Exception as e:
                        logger.warning(
                            f"Unexpected error fetching atas UF={uf or 'ALL'}: {e}"
                        )
                        continue

                    for item in items:
                        normalized = self._normalize_ata_item(item)
                        item_id = normalized.get("numeroControlePNCP", "") or normalized.get("numeroAta", "")
                        if item_id and item_id not in seen_ids:
                            seen_ids.add(item_id)
                            yield normalized

        logger.info(
            f"Atas fetch complete: {len(seen_ids)} unique atas across "
            f"{len(date_chunks)} date chunks"
        )

    @staticmethod
    def _normalize_ata_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an ata record to a flat format compatible with the pipeline.

        Maps ata-specific fields to the same flat structure used by contratacoes,
        adding _tipo='ata_registro_preco' to distinguish from regular licitacoes.
        """
        unidade = item.get("unidadeOrgao") or {}
        orgao = item.get("orgaoEntidade") or {}

        item["uf"] = unidade.get("ufSigla", "") or item.get("uf", "")
        item["municipio"] = unidade.get("municipioNome", "") or item.get("municipio", "")
        item["nomeOrgao"] = orgao.get("razaoSocial", "") or unidade.get("nomeUnidade", "") or item.get("nomeOrgao", "")
        item["cnpj"] = orgao.get("cnpj", "") or item.get("cnpj", "")

        # Map ata-specific fields to standard pipeline fields
        item["codigoCompra"] = item.get("numeroControlePNCP", "") or item.get("numeroAta", "")
        item["objetoCompra"] = item.get("objetoCompra", "") or item.get("objeto", "") or item.get("descricao", "")
        item["valorTotalEstimado"] = item.get("valorTotalEstimado") or item.get("valorTotal") or item.get("valor")

        # Ata-specific: use vigencia dates if standard dates missing
        if not item.get("dataPublicacaoPncp"):
            item["dataPublicacaoPncp"] = item.get("dataPublicacao") or item.get("dataVigenciaInicio")
        if not item.get("dataAberturaProposta"):
            item["dataAberturaProposta"] = item.get("dataVigenciaFim")

        item["modalidadeNome"] = item.get("modalidadeNome", "Ata de Registro de Precos")
        item["situacaoCompraNome"] = item.get("situacaoCompraNome", "") or item.get("situacao", "")

        # Tag to distinguish from regular licitacoes
        item["_tipo"] = "ata_registro_preco"

        return item

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
        palavra_chave: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all pages for a single UF+modalidade combination.

        Thread-safe wrapper around _fetch_by_uf that collects results into a list.
        Used by ThreadPoolExecutor in fetch_all for parallel fetching.
        """
        kw_label = f", palavraChave={palavra_chave}" if palavra_chave else ""
        label = f"modalidade={modalidade}, UF={uf or 'ALL'}{kw_label}"
        cache_key = self._cache_key(uf, modalidade, data_inicial, data_final) + (f":{palavra_chave}" if palavra_chave else "")

        # Check cache first
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for {uf or 'ALL'}:{modalidade} ({len(cached)} items)")
            return cached

        logger.info(f"Fetching {label}")
        try:
            items = list(self._fetch_by_uf(data_inicial, data_final, modalidade, uf, on_progress, palavra_chave=palavra_chave))
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
        search_terms: list[str] | None = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch all procurement records with parallel UF×modalidade fetching.

        Uses ThreadPoolExecutor to fetch all UF+modalidade combinations in parallel,
        dramatically reducing total fetch time (from ~10min to ~2min for 3 UFs × 5 modalities).

        Automatically splits date ranges > 30 days into 30-day chunks to avoid
        PNCP API limitations with large ranges.

        Args:
            data_inicial: Start date in YYYY-MM-DD format
            data_final: End date in YYYY-MM-DD format
            ufs: Optional list of state codes (e.g., ["SP", "RJ"])
            modalidades: Optional list of modality codes
            on_progress: Optional callback(current_page, total_pages, items_fetched)

        Yields:
            Dict[str, Any]: Individual procurement record
        """
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

            # Build list of (modalidade, uf, palavra_chave) tasks to run in parallel
            # When search_terms are provided, run one query per term for each UF×modalidade
            terms_to_use = search_terms if search_terms else [None]
            tasks: list[tuple[int, str | None, str | None]] = []
            for modalidade in modalidades_to_fetch:
                if ufs:
                    for uf in ufs:
                        for term in terms_to_use:
                            tasks.append((modalidade, uf, term))
                else:
                    for term in terms_to_use:
                        tasks.append((modalidade, None, term))

            terms_info = f" × {len(search_terms)} terms" if search_terms else ""
            logger.info(
                f"Launching {len(tasks)} parallel fetches "
                f"({len(modalidades_to_fetch)} modalities × {len(ufs or ['ALL'])} UFs{terms_info})"
            )

            # Parallel fetch: each UF×modalidade×term runs in its own thread
            # Max 12 workers for better throughput on multi-UF searches
            max_workers = min(len(tasks), 12)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {
                    executor.submit(
                        self._fetch_uf_modalidade,
                        chunk_start, chunk_end, modalidade, uf, on_progress, term,
                    ): (modalidade, uf)
                    for modalidade, uf, term in tasks
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
        palavra_chave: str | None = None,
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
                palavra_chave=palavra_chave,
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
