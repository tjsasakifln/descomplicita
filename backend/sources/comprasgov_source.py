"""Compras.gov.br data source adapter — federal procurement historical data (SIASG).

Implements the DataSourceClient interface for the Compras.gov.br open data API,
providing access to federal procurement records with CATMAT/CATSER categorization.

API docs: https://dadosabertos.compras.gov.br/swagger-ui/index.html

NOTE (2026-03-07): The licitacoes/v1 endpoint has been deprecated and returns 404.
The API migrated to compras.dados.gov.br which only exposes contract data
(comprasContratos), not standalone licitacoes. Licitacoes data has been
consolidated into PNCP. This source is disabled in config.py. See SR-001.3.
"""

import asyncio
import hashlib
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

from config import RetryConfig, SOURCES_CONFIG
from sources.base import DataSourceClient, NormalizedRecord, SearchQuery

logger = logging.getLogger(__name__)

# Compras.gov.br API page size (max 500 per API docs)
COMPRASGOV_PAGE_SIZE = 500

# Modalidade mapping: Compras.gov code -> human-readable name
MODALIDADES_COMPRASGOV = {
    1: "Convite",
    2: "Tomada de Preços",
    3: "Concorrência",
    4: "Concurso",
    5: "Pregão",
    6: "Dispensa de Licitação",
    7: "Inexigibilidade de Licitação",
    8: "Regime Diferenciado de Contratação",
    12: "Pregão Eletrônico",
    22: "Concorrência Internacional",
}

# Mapping Compras.gov modalidade -> PNCP equivalent codes
MODALIDADE_TO_PNCP = {
    1: None,   # Convite — not in PNCP
    2: None,   # Tomada de Preços — not in PNCP
    3: 4,      # Concorrência -> 4 (Concorrência Eletrônica)
    5: 6,      # Pregão -> 6 (Pregão Eletrônico)
    6: 8,      # Dispensa -> 8
    12: 6,     # Pregão Eletrônico -> 6
}


def _format_date_comprasgov(iso_date: Optional[str]) -> Optional[str]:
    """Convert ISO date (YYYY-MM-DD) to Compras.gov.br format (DD/MM/YYYY)."""
    if not iso_date:
        return iso_date
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except (ValueError, AttributeError):
        return iso_date


def _parse_comprasgov_date(value: Optional[str]) -> Optional[datetime]:
    """Parse a Compras.gov.br date string into a datetime object."""
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _generate_id(raw: dict) -> str:
    """Generate a deterministic unique ID for a Compras.gov record."""
    key = f"comprasgov-{raw.get('numero', '')}-{raw.get('uasg', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


class ComprasGovSource(DataSourceClient):
    """Compras.gov.br (SIASG) data source adapter.

    Provides access to federal procurement records from the Compras.gov.br
    open data API, including historical data predating PNCP (pre-2023)
    and CATMAT/CATSER categorization.
    """

    @property
    def source_name(self) -> str:
        return "comprasgov"

    def __init__(self, config: RetryConfig | None = None):
        self._config = config or RetryConfig(
            timeout=SOURCES_CONFIG["comprasgov"]["timeout"],
            max_retries=3,
        )
        source_cfg = SOURCES_CONFIG["comprasgov"]
        self._base_url = source_cfg["base_url"].rstrip("/")
        self._rate_limit_rps = source_cfg["rate_limit_rps"]
        self._last_request_time: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._config.timeout),
                headers={"Accept": "application/json"},
            )
        return self._client

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._rate_limit_rps <= 0:
            return
        min_interval = 1.0 / self._rate_limit_rps
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def _request_with_retry(self, url: str, params: dict) -> httpx.Response:
        """Make an HTTP GET request with exponential backoff retry."""
        client = self._get_client()
        last_exception: Optional[Exception] = None

        for attempt in range(self._config.max_retries + 1):
            await self._rate_limit()
            try:
                response = await client.get(url, params=params)
                if response.status_code in self._config.retryable_status_codes:
                    logger.warning(
                        "Compras.gov.br API returned %d on attempt %d",
                        response.status_code,
                        attempt + 1,
                        extra={"source": "comprasgov"},
                    )
                    if attempt < self._config.max_retries:
                        delay = self._config.base_delay * (
                            self._config.exponential_base ** attempt
                        )
                        delay = min(delay, self._config.max_delay)
                        await asyncio.sleep(delay)
                        continue
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exception = exc
                logger.warning(
                    "Compras.gov.br request failed on attempt %d: %s",
                    attempt + 1,
                    str(exc),
                    extra={"source": "comprasgov"},
                )
                if attempt < self._config.max_retries:
                    delay = self._config.base_delay * (
                        self._config.exponential_base ** attempt
                    )
                    delay = min(delay, self._config.max_delay)
                    await asyncio.sleep(delay)

        raise last_exception or httpx.ConnectError("Max retries exceeded")

    def normalize(self, raw: dict) -> NormalizedRecord:
        """Convert a raw Compras.gov.br API response item into a NormalizedRecord.

        Field mapping:
            numero              -> numero_licitacao
            objeto              -> objeto
            orgao               -> orgao
            uasg                -> raw_data (additional context)
            valor_estimado      -> valor_estimado
            modalidade_licitacao -> modalidade
            data_publicacao     -> data_publicacao
            situacao_licitacao  -> status
        """
        modalidade_code = raw.get("modalidade_licitacao")
        modalidade_name = ""
        if modalidade_code is not None:
            try:
                modalidade_code = int(modalidade_code)
                modalidade_name = MODALIDADES_COMPRASGOV.get(
                    modalidade_code, f"Modalidade {modalidade_code}"
                )
            except (ValueError, TypeError):
                modalidade_name = str(modalidade_code)
                modalidade_code = None

        valor = raw.get("valor_estimado")
        if valor is not None:
            try:
                valor = float(valor)
            except (ValueError, TypeError):
                valor = None

        numero = raw.get("numero", "")
        uasg = raw.get("uasg", "")

        # Build URL to the procurement page on Compras.gov.br
        url_fonte = None
        if numero and uasg:
            url_fonte = (
                f"https://compras.dados.gov.br/licitacoes/doc/licitacao/{uasg}/{numero}"
            )

        return NormalizedRecord(
            id=_generate_id(raw),
            source="comprasgov",
            sources=["comprasgov"],
            numero_licitacao=str(numero),
            objeto=raw.get("objeto", ""),
            orgao=raw.get("orgao", ""),
            cnpj_orgao=raw.get("cnpj", ""),
            uf=raw.get("uf", ""),
            municipio=raw.get("municipio", ""),
            valor_estimado=valor,
            modalidade=modalidade_name,
            modalidade_codigo=MODALIDADE_TO_PNCP.get(modalidade_code) if modalidade_code else None,
            data_publicacao=_parse_comprasgov_date(raw.get("data_publicacao")),
            data_abertura=_parse_comprasgov_date(raw.get("data_abertura")),
            status=raw.get("situacao_licitacao"),
            url_edital=None,
            url_fonte=url_fonte,
            raw_data=raw,
        )

    async def fetch_records(
        self,
        query: SearchQuery,
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> List[NormalizedRecord]:
        """Fetch all Compras.gov.br records matching the query.

        Handles pagination via offset-based API parameters.
        """
        url = f"{self._base_url}/licitacoes/v1/licitacoes.json"

        params: Dict[str, Any] = {
            "limit": COMPRASGOV_PAGE_SIZE,
            "offset": 0,
        }

        # Date filtering
        if query.data_inicial:
            params["data_publicacao_min"] = _format_date_comprasgov(query.data_inicial)
        if query.data_final:
            params["data_publicacao_max"] = _format_date_comprasgov(query.data_final)

        # UF filtering — API supports single UF, so we loop if multiple
        target_ufs = query.ufs or [None]

        all_records: List[NormalizedRecord] = []

        for uf in target_ufs:
            uf_params = dict(params)
            if uf:
                uf_params["uf"] = uf

            # Modalidade filtering
            if query.modalidades:
                # Convert PNCP modalidade codes to Compras.gov equivalents
                comprasgov_modalidades = set()
                for pncp_code in query.modalidades:
                    for cg_code, pncp_equiv in MODALIDADE_TO_PNCP.items():
                        if pncp_equiv == pncp_code:
                            comprasgov_modalidades.add(cg_code)
                # If no mapping found, skip modalidade filter
                if comprasgov_modalidades:
                    # API supports single modalidade per request
                    for mod in comprasgov_modalidades:
                        mod_params = dict(uf_params)
                        mod_params["modalidade"] = mod
                        records = await self._fetch_paginated(url, mod_params, on_progress)
                        all_records.extend(records)
                    continue

            records = await self._fetch_paginated(url, uf_params, on_progress)
            all_records.extend(records)

        logger.info(
            "Compras.gov.br fetch complete: %d records",
            len(all_records),
            extra={"source": "comprasgov"},
        )
        return all_records

    async def _fetch_paginated(
        self,
        url: str,
        params: Dict[str, Any],
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> List[NormalizedRecord]:
        """Fetch all pages from a paginated endpoint."""
        records: List[NormalizedRecord] = []
        offset = 0
        page = 0

        while True:
            params["offset"] = offset
            try:
                response = await self._request_with_retry(url, params)
                data = response.json()
            except Exception as exc:
                logger.error(
                    "Compras.gov.br pagination error at offset %d: %s",
                    offset,
                    str(exc),
                    extra={"source": "comprasgov"},
                )
                break

            # API returns list directly or nested under a key
            items = data if isinstance(data, list) else data.get("_embedded", data.get("results", []))
            if not items or not isinstance(items, list):
                break

            for item in items:
                records.append(self.normalize(item))

            page += 1
            if on_progress:
                on_progress(page, len(records), 0)

            if len(items) < COMPRASGOV_PAGE_SIZE:
                break

            offset += COMPRASGOV_PAGE_SIZE

        return records

    def is_healthy(self) -> bool:
        """Check if the Compras.gov.br API is reachable."""
        try:
            import httpx as httpx_sync
            response = httpx_sync.get(
                f"{self._base_url}/licitacoes/v1/licitacoes.json",
                params={"limit": 1, "offset": 0},
                timeout=10,
                headers={"Accept": "application/json"},
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
