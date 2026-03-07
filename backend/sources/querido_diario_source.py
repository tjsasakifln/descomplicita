"""Querido Diario data source adapter — municipal gazette procurement extraction.

Implements the DataSourceClient interface for the Querido Diario API,
providing access to procurement notices extracted from Brazilian municipal
official gazettes via NLP-assisted text parsing.

API docs: https://queridodiario.ok.org.br/api/docs
"""

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

from config import RetryConfig, SOURCES_CONFIG
from sources.base import DataSourceClient, NormalizedRecord, SearchQuery

logger = logging.getLogger(__name__)

# Querido Diario API page size
QUERIDO_DIARIO_PAGE_SIZE = 50

# IBGE state prefix (first 2 digits of municipality code) -> UF code
UF_TO_IBGE_PREFIX: Dict[str, str] = {
    "RO": "11",
    "AC": "12",
    "AM": "13",
    "RR": "14",
    "PA": "15",
    "AP": "16",
    "TO": "17",
    "MA": "21",
    "PI": "22",
    "CE": "23",
    "RN": "24",
    "PB": "25",
    "PE": "26",
    "AL": "27",
    "SE": "28",
    "BA": "29",
    "MG": "31",
    "ES": "32",
    "RJ": "33",
    "SP": "35",
    "PR": "41",
    "SC": "42",
    "RS": "43",
    "MS": "50",
    "MT": "51",
    "GO": "52",
    "DF": "53",
}

# Reverse lookup: IBGE 2-digit prefix -> UF code
IBGE_PREFIX_TO_UF: Dict[str, str] = {v: k for k, v in UF_TO_IBGE_PREFIX.items()}

# Module-level regex patterns for procurement text extraction (case-insensitive)
REGEX_NUMERO = re.compile(
    r'(?:Pregão|Concorrência|Tomada|Dispensa|Edital)\s*(?:Eletrônico|Presencial)?\s*[Nn]?[ºo.]?\s*(\d{1,5}[/-]\d{4})',
    re.IGNORECASE,
)
REGEX_VALOR = re.compile(r'R\$\s*([\d.,]+)')
REGEX_MODALIDADE = re.compile(
    r'(Pregão\s*Eletrônico|Pregão\s*Presencial|Concorrência|Tomada\s*de\s*Preços?|Dispensa)',
    re.IGNORECASE,
)


def _parse_querido_diario_date(value: Optional[str]) -> Optional[datetime]:
    """Parse a Querido Diario date string (YYYY-MM-DD) into a datetime object."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _parse_valor(raw_valor: str) -> Optional[float]:
    """Parse a Brazilian-formatted currency string into a float.

    Removes thousands separators (dots) and converts decimal comma to dot.
    Example: '1.234.567,89' -> 1234567.89
    """
    try:
        # Remove thousands separators (dots before groups of digits)
        cleaned = raw_valor.replace(".", "")
        # Replace decimal comma with dot
        cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def _derive_uf_from_territory_id(territory_id: str) -> str:
    """Derive the UF code from an IBGE territory ID using the 2-digit state prefix."""
    if territory_id and len(territory_id) >= 2:
        prefix = territory_id[:2]
        return IBGE_PREFIX_TO_UF.get(prefix, "")
    return ""


def _generate_id(gazette: dict, excerpt_idx: int) -> str:
    """Generate a deterministic unique ID for a Querido Diario gazette excerpt."""
    territory_id = gazette.get("territory_id", "")
    date = gazette.get("date", "")
    key = f"querido_diario-{territory_id}-{date}-{excerpt_idx}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


class QueridoDiarioSource(DataSourceClient):
    """Querido Diario data source adapter.

    Provides access to procurement notices extracted from Brazilian municipal
    official gazettes. Uses regex-based text parsing to identify procurement
    numbers, values, and modalities from gazette excerpts returned by the
    Querido Diario full-text search API.

    No authentication required. Rate limited to 5 req/s.
    """

    @property
    def source_name(self) -> str:
        return "querido_diario"

    def __init__(self, config: RetryConfig | None = None):
        source_cfg = SOURCES_CONFIG["querido_diario"]
        self._config = config or RetryConfig(
            timeout=source_cfg["timeout"],
            max_retries=3,
        )
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
                        "Querido Diario API returned %d on attempt %d",
                        response.status_code,
                        attempt + 1,
                        extra={"source": "querido_diario"},
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
                    "Querido Diario request failed on attempt %d: %s",
                    attempt + 1,
                    str(exc),
                    extra={"source": "querido_diario"},
                )
                if attempt < self._config.max_retries:
                    delay = self._config.base_delay * (
                        self._config.exponential_base ** attempt
                    )
                    delay = min(delay, self._config.max_delay)
                    await asyncio.sleep(delay)

        raise last_exception or httpx.ConnectError("Max retries exceeded")

    def get_territory_ids(self, uf: str) -> List[str]:
        """Return territory IDs for a given UF code.

        Currently returns an empty list — we do not maintain a full list of
        IBGE municipality codes per state. Instead, post-filtering is applied
        on the territory_id prefix in fetch_records().
        """
        return []

    def _extract_from_gazette(self, gazette: dict) -> List[NormalizedRecord]:
        """Extract NormalizedRecord entries from a single gazette dict.

        Iterates over each excerpt and applies regex patterns to identify
        procurement number, estimated value, and modality. A record is
        produced for every excerpt regardless of regex match success.
        """
        records: List[NormalizedRecord] = []
        excerpts: List[str] = gazette.get("excerpts", [])
        territory_id: str = gazette.get("territory_id", "")
        territory_name: str = gazette.get("territory_name", "")
        date_str: str = gazette.get("date", "")
        url_fonte: Optional[str] = gazette.get("url") or gazette.get("txt_url")
        uf = _derive_uf_from_territory_id(territory_id)
        data_publicacao = _parse_querido_diario_date(date_str)

        if not excerpts:
            return records

        for idx, excerpt in enumerate(excerpts):
            # Extract numero
            numero_match = REGEX_NUMERO.search(excerpt)
            numero = numero_match.group(1) if numero_match else None

            # Extract valor
            valor: Optional[float] = None
            valor_match = REGEX_VALOR.search(excerpt)
            if valor_match:
                valor = _parse_valor(valor_match.group(1))

            # Extract modalidade
            modalidade_match = REGEX_MODALIDADE.search(excerpt)
            modalidade = modalidade_match.group(1) if modalidade_match else None

            # Use excerpt as objeto (truncated to 200 chars if no structured data)
            objeto = excerpt[:200] if not numero else excerpt[:500]

            records.append(
                NormalizedRecord(
                    id=_generate_id(gazette, idx),
                    source="querido_diario",
                    sources=["querido_diario"],
                    numero_licitacao=numero or "",
                    objeto=objeto,
                    orgao=territory_name,
                    cnpj_orgao="",
                    uf=uf,
                    municipio=territory_name,
                    valor_estimado=valor,
                    modalidade=modalidade or "",
                    data_publicacao=data_publicacao,
                    url_fonte=url_fonte,
                    raw_data=gazette,
                )
            )

        return records

    def normalize(self, raw: dict) -> NormalizedRecord:
        """Convert a raw Querido Diario gazette dict into a NormalizedRecord.

        Returns the first extracted record from the gazette, or a basic stub
        record if no excerpts are present. This method satisfies the abstract
        interface; use _extract_from_gazette() directly to get all records
        from a gazette with multiple excerpts.
        """
        extracted = self._extract_from_gazette(raw)
        if extracted:
            return extracted[0]

        # Fallback: build a minimal record
        territory_name = raw.get("territory_name", "")
        territory_id = raw.get("territory_id", "")
        return NormalizedRecord(
            id=_generate_id(raw, 0),
            source="querido_diario",
            sources=["querido_diario"],
            numero_licitacao="",
            objeto="",
            orgao=territory_name,
            cnpj_orgao="",
            uf=_derive_uf_from_territory_id(territory_id),
            municipio=territory_name,
            valor_estimado=None,
            modalidade="",
            data_publicacao=_parse_querido_diario_date(raw.get("date")),
            url_fonte=raw.get("url") or raw.get("txt_url"),
            raw_data=raw,
        )

    async def fetch_records(
        self,
        query: SearchQuery,
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> List[NormalizedRecord]:
        """Fetch all Querido Diario gazette records matching the query.

        Searches using generic procurement terms and paginates via offset.
        Post-filters by UF if query.ufs is specified, using the IBGE territory_id
        prefix to identify the state (no territory_ids param sent to API).
        """
        url = f"{self._base_url}/gazettes"

        params: Dict[str, Any] = {
            "querystring": "licitação pregão edital",
            "size": QUERIDO_DIARIO_PAGE_SIZE,
            "offset": 0,
        }

        if query.data_inicial:
            params["published_since"] = query.data_inicial
        if query.data_final:
            params["published_until"] = query.data_final

        # Determine IBGE prefixes for UF post-filtering
        target_prefixes: Optional[List[str]] = None
        if query.ufs:
            target_prefixes = [
                UF_TO_IBGE_PREFIX[uf]
                for uf in query.ufs
                if uf in UF_TO_IBGE_PREFIX
            ]

        all_records: List[NormalizedRecord] = []
        offset = 0
        page = 0

        while True:
            params["offset"] = offset
            try:
                response = await self._request_with_retry(url, params)
                data = response.json()
            except Exception as exc:
                logger.error(
                    "Querido Diario pagination error at offset %d: %s",
                    offset,
                    str(exc),
                    extra={"source": "querido_diario"},
                )
                break

            gazettes: List[dict] = data.get("gazettes", [])
            if not gazettes:
                break

            for gazette in gazettes:
                territory_id = gazette.get("territory_id", "")

                # Post-filter by UF if requested
                if target_prefixes is not None:
                    prefix = territory_id[:2] if territory_id else ""
                    if prefix not in target_prefixes:
                        continue

                extracted = self._extract_from_gazette(gazette)
                all_records.extend(extracted)

            page += 1
            if on_progress:
                on_progress(page, len(all_records), data.get("total_gazettes", 0))

            if len(gazettes) < QUERIDO_DIARIO_PAGE_SIZE:
                break

            offset += QUERIDO_DIARIO_PAGE_SIZE

        logger.info(
            "Querido Diario fetch complete: %d records from %d pages",
            len(all_records),
            page,
            extra={"source": "querido_diario"},
        )
        return all_records

    def is_healthy(self) -> bool:
        """Check if the Querido Diario API is reachable."""
        try:
            response = httpx.get(
                f"{self._base_url}/gazettes",
                params={"querystring": "licitação", "size": 1, "offset": 0},
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
