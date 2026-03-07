"""Portal da Transparencia data source adapter — CGU sanctions & federal procurement.

Implements the DataSourceClient interface for the Portal da Transparencia API,
providing access to federal procurement records and sanctions lists (CEIS, CNEP).

API docs: https://portaldatransparencia.gov.br/api-de-dados
Auth: API key via header 'chave-api-dados'
"""

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

from config import RetryConfig, SOURCES_CONFIG
from sources.base import DataSourceClient, NormalizedRecord, SearchQuery

logger = logging.getLogger(__name__)

# Portal da Transparencia page size (API default)
TRANSPARENCIA_PAGE_SIZE = 15

# Mapping of UF abbreviations to IBGE numeric codes.
# The Portal da Transparencia API expects numeric IBGE codes for the codigoUF
# parameter, not state abbreviations (siglas).
UF_TO_IBGE: Dict[str, int] = {
    "AC": 12, "AL": 27, "AM": 13, "AP": 16, "BA": 29,
    "CE": 23, "DF": 53, "ES": 32, "GO": 52, "MA": 21,
    "MG": 31, "MS": 50, "MT": 51, "PA": 15, "PB": 25,
    "PE": 26, "PI": 22, "PR": 41, "RJ": 33, "RN": 24,
    "RO": 11, "RR": 14, "RS": 43, "SC": 42, "SE": 28,
    "SP": 35, "TO": 17,
}


@dataclass
class SanctionResult:
    """Result of a sanctions check against CEIS and CNEP lists."""

    is_sanctioned: bool
    sanctions: List[dict] = field(default_factory=list)


def _parse_transparencia_date(value: Optional[str]) -> Optional[datetime]:
    """Parse a Portal da Transparencia date string into a datetime object."""
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _format_date_transparencia(iso_date: Optional[str]) -> Optional[str]:
    """Convert ISO date (YYYY-MM-DD) to Portal da Transparencia format (DD/MM/YYYY)."""
    if not iso_date:
        return iso_date
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except (ValueError, AttributeError):
        return iso_date


def _generate_id(raw: dict) -> str:
    """Generate a deterministic unique ID for a Transparencia record."""
    orgao = raw.get("orgaoVinculado") or {}
    key = f"transparencia-{raw.get('numero', '')}-{orgao.get('cnpj', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


class TransparenciaSource(DataSourceClient):
    """Portal da Transparencia (CGU) data source adapter.

    Provides access to federal procurement records and sanctions lists
    (CEIS — empresas impedidas, CNEP — penalidades) from the CGU API.
    """

    @property
    def source_name(self) -> str:
        return "transparencia"

    def __init__(self, config: RetryConfig | None = None, api_key: str | None = None):
        source_cfg = SOURCES_CONFIG["transparencia"]
        self._config = config or RetryConfig(
            timeout=source_cfg["timeout"],
            max_retries=3,
        )
        self._base_url = source_cfg["base_url"].rstrip("/")
        self._rate_limit_rps = source_cfg["rate_limit_rps"]
        self._api_key = api_key or os.environ.get("TRANSPARENCIA_API_KEY", "")
        self._last_request_time: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init the async HTTP client with auth headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._config.timeout),
                headers={
                    "chave-api-dados": self._api_key,
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests (3 req/s)."""
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

                # 401/403 = auth failure, do not retry
                if response.status_code in (401, 403):
                    logger.error(
                        "Transparencia API auth failure: %d",
                        response.status_code,
                        extra={"source": "transparencia"},
                    )
                    response.raise_for_status()

                if response.status_code in self._config.retryable_status_codes:
                    logger.warning(
                        "Transparencia API returned %d on attempt %d",
                        response.status_code,
                        attempt + 1,
                        extra={"source": "transparencia"},
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
                    "Transparencia request failed on attempt %d: %s",
                    attempt + 1,
                    str(exc),
                    extra={"source": "transparencia"},
                )
                if attempt < self._config.max_retries:
                    delay = self._config.base_delay * (
                        self._config.exponential_base ** attempt
                    )
                    delay = min(delay, self._config.max_delay)
                    await asyncio.sleep(delay)

        raise last_exception or httpx.ConnectError("Max retries exceeded")

    def normalize(self, raw: dict) -> NormalizedRecord:
        """Convert a raw Portal da Transparencia API response item into a NormalizedRecord.

        Field mapping:
            numero                  -> numero_licitacao
            objeto                  -> objeto
            orgaoVinculado.nome     -> orgao
            orgaoVinculado.cnpj     -> cnpj_orgao
            uf                      -> uf
            municipio               -> municipio
            valorLicitacao          -> valor_estimado
            modalidadeLicitacao     -> modalidade
            dataAbertura            -> data_abertura
            situacaoLicitacao       -> status
        """
        orgao_vinculado = raw.get("orgaoVinculado") or {}

        valor = raw.get("valorLicitacao")
        if valor is not None:
            try:
                valor = float(valor)
            except (ValueError, TypeError):
                valor = None

        return NormalizedRecord(
            id=_generate_id(raw),
            source="transparencia",
            sources=["transparencia"],
            numero_licitacao=str(raw.get("numero", "")),
            objeto=raw.get("objeto", ""),
            orgao=orgao_vinculado.get("nome", ""),
            cnpj_orgao=orgao_vinculado.get("cnpj", ""),
            uf=raw.get("uf", ""),
            municipio=raw.get("municipio", ""),
            valor_estimado=valor,
            modalidade=raw.get("modalidadeLicitacao", ""),
            data_abertura=_parse_transparencia_date(raw.get("dataAbertura")),
            status=raw.get("situacaoLicitacao"),
            url_edital=None,
            url_fonte=None,
            raw_data=raw,
        )

    async def check_sanctions(self, cnpj: str) -> SanctionResult:
        """Check if a CNPJ appears in CEIS or CNEP sanctions lists.

        Args:
            cnpj: CNPJ to check (digits only or formatted).

        Returns:
            SanctionResult with is_sanctioned flag and list of sanctions found.
        """
        sanctions: List[dict] = []

        for list_name, endpoint in [("CEIS", "ceis"), ("CNEP", "cnep")]:
            url = f"{self._base_url}/api-de-dados/{endpoint}"
            params = {"cnpjSancionado": cnpj, "pagina": 1}
            try:
                response = await self._request_with_retry(url, params)
                data = response.json()
                items = data if isinstance(data, list) else []
                for item in items:
                    item["_lista"] = list_name
                    sanctions.append(item)
            except Exception as exc:
                logger.warning(
                    "Sanctions check (%s) failed for CNPJ %s: %s",
                    list_name,
                    cnpj,
                    str(exc),
                    extra={"source": "transparencia"},
                )

        return SanctionResult(
            is_sanctioned=len(sanctions) > 0,
            sanctions=sanctions,
        )

    async def fetch_records(
        self,
        query: SearchQuery,
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> List[NormalizedRecord]:
        """Fetch all Portal da Transparencia records matching the query.

        Handles pagination via 1-indexed page parameter.
        """
        url = f"{self._base_url}/api-de-dados/licitacoes"

        params: Dict[str, Any] = {"pagina": 1}

        if query.data_inicial:
            params["dataInicial"] = _format_date_transparencia(query.data_inicial)
        if query.data_final:
            params["dataFinal"] = _format_date_transparencia(query.data_final)

        target_ufs = query.ufs or [None]
        all_records: List[NormalizedRecord] = []

        for uf in target_ufs:
            uf_params = dict(params)
            if uf:
                ibge_code = UF_TO_IBGE.get(uf.upper())
                if ibge_code is not None:
                    uf_params["codigoUF"] = ibge_code
                    logger.debug(
                        "Transparencia: UF '%s' mapped to IBGE code %d",
                        uf, ibge_code,
                        extra={"source": "transparencia"},
                    )
                else:
                    logger.warning(
                        "Transparencia: unknown UF '%s', skipping codigoUF parameter",
                        uf,
                        extra={"source": "transparencia"},
                    )

            if query.modalidades:
                for mod in query.modalidades:
                    mod_params = dict(uf_params)
                    mod_params["modalidadeLicitacao"] = mod
                    records = await self._fetch_paginated(url, mod_params, on_progress)
                    all_records.extend(records)
                continue

            records = await self._fetch_paginated(url, uf_params, on_progress)
            all_records.extend(records)

        logger.info(
            "Transparencia fetch complete: %d records",
            len(all_records),
            extra={"source": "transparencia"},
        )
        return all_records

    async def _fetch_paginated(
        self,
        url: str,
        params: Dict[str, Any],
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> List[NormalizedRecord]:
        """Fetch all pages from a paginated endpoint (1-indexed pages)."""
        records: List[NormalizedRecord] = []
        page = 1

        while True:
            params["pagina"] = page
            try:
                response = await self._request_with_retry(url, params)
                data = response.json()
            except Exception as exc:
                logger.error(
                    "Transparencia pagination error at page %d: %s",
                    page,
                    str(exc),
                    extra={"source": "transparencia"},
                )
                break

            items = data if isinstance(data, list) else []
            if not items:
                break

            for item in items:
                records.append(self.normalize(item))

            if on_progress:
                on_progress(page, len(records), 0)

            if len(items) < TRANSPARENCIA_PAGE_SIZE:
                break

            page += 1

        return records

    def is_healthy(self) -> bool:
        """Check if the Portal da Transparencia API is reachable."""
        try:
            response = httpx.get(
                f"{self._base_url}/api-de-dados/licitacoes",
                params={"pagina": 1},
                timeout=10,
                headers={
                    "chave-api-dados": self._api_key,
                    "Accept": "application/json",
                },
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
