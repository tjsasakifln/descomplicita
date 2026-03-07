"""TCE-RJ data source adapter — Tribunal de Contas do Estado do Rio de Janeiro.

Implements the DataSourceClient interface for the TCE-RJ open data API,
providing access to procurement records (licitações and compras diretas)
from all 92 municipalities in Rio de Janeiro state.

API docs: https://dados.tcerj.tc.br/api/v1/docs
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

TCE_RJ_PAGE_SIZE = 100

# Mapping of TCE-RJ modalidade strings to normalized labels
MODALIDADE_MAP: Dict[str, str] = {
    "pregao_eletronico": "Pregão Eletrônico",
    "pregao_presencial": "Pregão Presencial",
    "concorrencia": "Concorrência",
    "tomada_de_precos": "Tomada de Preços",
    "convite": "Convite",
    "concurso": "Concurso",
    "leilao": "Leilão",
    "dispensa": "Dispensa",
    "inexigibilidade": "Inexigibilidade",
    "adesao_ata": "Adesão a Ata",
    "chamada_publica": "Chamada Pública",
    "dialogo_competitivo": "Diálogo Competitivo",
}


def _parse_tce_rj_date(value: Optional[str]) -> Optional[datetime]:
    """Parse a TCE-RJ date string into a datetime object."""
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _generate_id(record_type: str, raw: dict) -> str:
    """Generate a deterministic unique ID for a TCE-RJ record."""
    key_parts = [
        "tce_rj",
        record_type,
        str(raw.get("numero", "")),
        str(raw.get("orgao", {}).get("cnpj", "") if isinstance(raw.get("orgao"), dict) else ""),
        str(raw.get("data_publicacao", "")),
    ]
    key = "-".join(key_parts)
    return hashlib.md5(key.encode()).hexdigest()[:16]


def _normalize_modalidade(raw_modalidade: Optional[str]) -> str:
    """Normalize a TCE-RJ modalidade string."""
    if not raw_modalidade:
        return ""
    normalized = raw_modalidade.strip().lower().replace(" ", "_")
    return MODALIDADE_MAP.get(normalized, raw_modalidade.strip())


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


class TCERJSource(DataSourceClient):
    """TCE-RJ data source adapter.

    Provides access to procurement data from the Tribunal de Contas do Estado
    do Rio de Janeiro open data API. Covers all 92 municipalities in RJ state
    plus state-level agencies.

    Endpoints:
    - /licitacoes — public procurement tenders
    - /compras-diretas — direct purchases (dispensa, inexigibilidade, adesão)

    No authentication required. Rate limited to 3 req/s.
    """

    @property
    def source_name(self) -> str:
        return "tce_rj"

    def __init__(self, config: RetryConfig | None = None):
        source_cfg = SOURCES_CONFIG["tce_rj"]
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
                        "TCE-RJ API returned %d on attempt %d",
                        response.status_code,
                        attempt + 1,
                        extra={"source": "tce_rj"},
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
                    "TCE-RJ request failed on attempt %d: %s",
                    attempt + 1,
                    str(exc),
                    extra={"source": "tce_rj"},
                )
                if attempt < self._config.max_retries:
                    delay = self._config.base_delay * (
                        self._config.exponential_base ** attempt
                    )
                    delay = min(delay, self._config.max_delay)
                    await asyncio.sleep(delay)

        raise last_exception or httpx.ConnectError("Max retries exceeded")

    def normalize(self, raw: dict, record_type: str = "licitacao") -> NormalizedRecord:
        """Convert a raw TCE-RJ API record into a NormalizedRecord.

        Args:
            raw: Raw dict from the TCE-RJ API.
            record_type: Either 'licitacao' or 'compra_direta'.

        Returns:
            Normalized record.
        """
        orgao_data = raw.get("orgao", {})
        if isinstance(orgao_data, dict):
            orgao_nome = orgao_data.get("nome", "")
            cnpj = orgao_data.get("cnpj", "")
            municipio = orgao_data.get("municipio", "")
        else:
            orgao_nome = str(orgao_data) if orgao_data else ""
            cnpj = ""
            municipio = ""

        # For compras diretas, derive modalidade from tipo_compra
        if record_type == "compra_direta":
            tipo = raw.get("tipo_compra", raw.get("tipo", ""))
            if isinstance(tipo, str):
                tipo_lower = tipo.strip().lower()
                if "inexigibilidade" in tipo_lower:
                    modalidade = "Inexigibilidade"
                elif "adesao" in tipo_lower or "adesão" in tipo_lower:
                    modalidade = "Adesão a Ata"
                else:
                    modalidade = "Dispensa"
            else:
                modalidade = "Dispensa"
        else:
            modalidade = _normalize_modalidade(raw.get("modalidade"))

        return NormalizedRecord(
            id=_generate_id(record_type, raw),
            source="tce_rj",
            sources=["tce_rj"],
            numero_licitacao=str(raw.get("numero", "")),
            objeto=str(raw.get("objeto", "")),
            orgao=orgao_nome,
            cnpj_orgao=cnpj,
            uf="RJ",
            municipio=municipio or raw.get("municipio", ""),
            valor_estimado=_safe_float(raw.get("valor_estimado", raw.get("valor"))),
            modalidade=modalidade,
            data_publicacao=_parse_tce_rj_date(raw.get("data_publicacao")),
            status=raw.get("situacao", raw.get("status", "")),
            url_fonte=raw.get("url"),
            raw_data=raw,
        )

    async def _fetch_endpoint(
        self,
        endpoint: str,
        record_type: str,
        query: SearchQuery,
    ) -> List[NormalizedRecord]:
        """Fetch all records from a single TCE-RJ endpoint with pagination."""
        url = f"{self._base_url}/api/v1/{endpoint}"
        params: Dict[str, Any] = {
            "limit": TCE_RJ_PAGE_SIZE,
            "offset": 0,
        }

        if query.data_inicial:
            params["data_inicio"] = query.data_inicial
        if query.data_final:
            params["data_fim"] = query.data_final

        all_records: List[NormalizedRecord] = []
        offset = 0

        while True:
            params["offset"] = offset
            try:
                response = await self._request_with_retry(url, params)
                data = response.json()
            except Exception as exc:
                logger.error(
                    "TCE-RJ %s pagination error at offset %d: %s",
                    endpoint,
                    offset,
                    str(exc),
                    extra={"source": "tce_rj"},
                )
                break

            items: List[dict] = data if isinstance(data, list) else data.get("items", data.get("results", []))
            if not items:
                break

            for item in items:
                record = self.normalize(item, record_type)
                all_records.append(record)

            if len(items) < TCE_RJ_PAGE_SIZE:
                break

            offset += TCE_RJ_PAGE_SIZE

        return all_records

    async def fetch_records(
        self,
        query: SearchQuery,
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> List[NormalizedRecord]:
        """Fetch TCE-RJ procurement records (licitações + compras diretas).

        Only activates when 'RJ' is in the query UFs. Returns empty list
        immediately for queries that don't include RJ, avoiding any overhead.
        """
        # UF filter: only activate for RJ
        if query.ufs and "RJ" not in query.ufs:
            logger.debug(
                "TCE-RJ skipped: UFs %s do not include RJ",
                query.ufs,
                extra={"source": "tce_rj"},
            )
            return []

        # Fetch both endpoints concurrently
        licitacoes_task = self._fetch_endpoint("licitacoes", "licitacao", query)
        compras_task = self._fetch_endpoint("compras-diretas", "compra_direta", query)

        licitacoes, compras = await asyncio.gather(licitacoes_task, compras_task)

        all_records = licitacoes + compras

        if on_progress:
            on_progress(1, len(all_records), len(all_records))

        logger.info(
            "TCE-RJ fetch complete: %d licitações + %d compras diretas = %d total",
            len(licitacoes),
            len(compras),
            len(all_records),
            extra={"source": "tce_rj"},
        )
        return all_records

    def is_healthy(self) -> bool:
        """Check if the TCE-RJ API is reachable."""
        try:
            response = httpx.get(
                f"{self._base_url}/api/v1/licitacoes",
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
