"""PNCP data source adapter — wraps AsyncPNCPClient behind the DataSourceClient ABC."""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from config import RetryConfig, MAX_PAGES_PER_COMBO
from clients.async_pncp_client import AsyncPNCPClient
from app_cache.redis_cache import RedisCache
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

    Wraps the AsyncPNCPClient (httpx-based) behind the DataSourceClient interface.
    Optionally uses RedisCache for caching PNCP responses.
    """

    @property
    def source_name(self) -> str:
        return "PNCP"

    def __init__(
        self,
        async_client: AsyncPNCPClient | None = None,
        config: RetryConfig | None = None,
        cache: RedisCache | None = None,
    ):
        self._client = async_client or AsyncPNCPClient(config)
        self._cache = cache
        self._partial_results: List[dict] = []

    @property
    def client(self) -> AsyncPNCPClient:
        """Expose underlying AsyncPNCPClient for cache/debug operations."""
        return self._client

    def normalize(self, raw: dict) -> NormalizedRecord:
        """Convert a flat PNCP dict to NormalizedRecord."""
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
        """Fetch PNCP records matching the query using async httpx client."""
        self._partial_results = []

        try:
            items = await self._client.fetch_all(
                data_inicial=query.data_inicial,
                data_final=query.data_final,
                ufs=query.ufs,
                modalidades=query.modalidades,
                on_progress=on_progress,
                max_pages=MAX_PAGES_PER_COMBO,
            )
            self._partial_results = items
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
        """Number of UF x modalidade combos truncated by max_pages."""
        return self._client.truncated_combos

    def is_healthy(self) -> bool:
        """Quick health check."""
        return self._client is not None

    async def cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        if self._cache:
            stats = self._cache.stats()
            stats["entries"] = await self._cache.entry_count()
            return stats
        return {"entries": 0, "hits": 0, "misses": 0, "hit_ratio": 0.0}

    async def cache_clear(self) -> int:
        """Clear cache."""
        if self._cache:
            return await self._cache.clear()
        return 0

    async def close(self) -> None:
        """Close the underlying client."""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
