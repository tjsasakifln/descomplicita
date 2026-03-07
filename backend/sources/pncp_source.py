"""PNCP data source adapter — wraps PNCPClient behind the DataSourceClient ABC."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from config import RetryConfig, MAX_PAGES_PER_COMBO
from pncp_client import PNCPClient
from sources.base import DataSourceClient, NormalizedRecord, SearchQuery

logger = logging.getLogger(__name__)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse a PNCP datetime string into a naive datetime object."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except (ValueError, AttributeError):
        pass
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    except (ValueError, AttributeError):
        pass
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


class PNCPSource(DataSourceClient):
    """PNCP data source adapter.

    Wraps the existing PNCPClient (with its retry, rate-limiting, caching,
    and pagination logic) behind the DataSourceClient interface.
    """

    @property
    def source_name(self) -> str:
        return "PNCP"

    def __init__(self, config: RetryConfig | None = None):
        self._client = PNCPClient(config)
        # Partial results buffer — survives orchestrator timeout/cancellation
        self._partial_results: List[dict] = []

    @property
    def client(self) -> PNCPClient:
        """Expose underlying PNCPClient for cache/debug operations."""
        return self._client

    def normalize(self, raw: dict) -> NormalizedRecord:
        """Convert a flat PNCP dict (already processed by _normalize_item) to NormalizedRecord."""
        cnpj = raw.get("cnpj", "")
        ano = raw.get("anoCompra", "")
        seq = raw.get("sequencialCompra", "")

        url_edital = raw.get("linkPncp") or (
            f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"
            if cnpj and ano and seq
            else None
        )

        return NormalizedRecord(
            id=raw.get("numeroControlePNCP", ""),
            source="PNCP",
            sources=["PNCP"],
            numero_licitacao=raw.get("numeroControlePNCP", ""),
            objeto=raw.get("objetoCompra", ""),
            orgao=raw.get("nomeOrgao", ""),
            cnpj_orgao=cnpj,
            uf=raw.get("uf", ""),
            municipio=raw.get("municipio", ""),
            valor_estimado=raw.get("valorTotalEstimado"),
            modalidade=raw.get("modalidadeNome", ""),
            modalidade_codigo=raw.get("codigoModalidadeContratacao"),
            data_publicacao=_parse_datetime(raw.get("dataPublicacaoPncp")),
            data_abertura=_parse_datetime(raw.get("dataAberturaProposta")),
            status=raw.get("situacaoCompraNome"),
            url_edital=url_edital,
            url_fonte=None,
            raw_data=raw,
        )

    async def fetch_records(
        self,
        query: SearchQuery,
        on_progress: Callable[[int, int, int], None] | None = None,
    ) -> List[NormalizedRecord]:
        """Fetch PNCP records matching the query.

        Delegates to PNCPClient.fetch_all() (sync, threaded) via
        run_in_executor to avoid blocking the async event loop.

        Uses MAX_PAGES_PER_COMBO to cap pagination per UF×modalidade combo,
        preventing timeouts on high-volume combinations (e.g., SP×Pregão
        with 228+ pages). Partial results are collected incrementally so
        that if an unexpected timeout occurs, whatever was fetched is
        returned rather than discarded.
        """
        loop = asyncio.get_event_loop()

        # Reset partial results buffer (instance variable so orchestrator
        # can recover data even if asyncio.wait_for cancels our task)
        self._partial_results = []

        def _fetch() -> None:
            for item in self._client.fetch_all(
                data_inicial=query.data_inicial,
                data_final=query.data_final,
                ufs=query.ufs,
                modalidades=query.modalidades,
                on_progress=on_progress,
                max_pages=MAX_PAGES_PER_COMBO,
            ):
                self._partial_results.append(item)

        try:
            await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.warning(
                "PNCP fetch interrupted (%s), returning %d partial results",
                type(e).__name__, len(self._partial_results),
            )

        return [self.normalize(item) for item in self._partial_results]

    def get_partial_results(self) -> List[NormalizedRecord]:
        """Return whatever was collected so far (for timeout recovery)."""
        return [self.normalize(item) for item in self._partial_results]

    @property
    def truncated_combos(self) -> int:
        """Number of UF×modalidade combos truncated by max_pages."""
        return self._client.truncated_combos

    def is_healthy(self) -> bool:
        """Quick health check — verifies the HTTP session is open."""
        try:
            return self._client.session is not None
        except Exception:
            return False

    # --- Cache delegation ---

    def cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics from the underlying PNCPClient."""
        return self._client.cache_stats()

    def cache_clear(self) -> int:
        """Clear cache in the underlying PNCPClient."""
        return self._client.cache_clear()

    def close(self) -> None:
        """Close the underlying PNCPClient session."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
