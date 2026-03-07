"""PNCP data source adapter — wraps PNCPClient behind the DataSourceClient ABC."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from config import RetryConfig
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

    @property
    def client(self) -> PNCPClient:
        """Expose underlying PNCPClient for cache/debug operations."""
        return self._client

    def normalize(self, raw: dict) -> NormalizedRecord:
        """Convert a flat PNCP dict (already processed by _normalize_item) to NormalizedRecord."""
        cnpj = raw.get("cnpj", "")
        ano = raw.get("anoCompra", "")
        seq = raw.get("sequencialCompra", "")
        is_ata = raw.get("_tipo") == "ata_registro_preco"

        url_edital = raw.get("linkPncp") or (
            f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"
            if cnpj and ano and seq
            else None
        )

        return NormalizedRecord(
            id=raw.get("numeroControlePNCP", "") or raw.get("numeroAta", ""),
            source="PNCP",
            sources=["PNCP"],
            tipo="ata_registro_preco" if is_ata else "licitacao",
            numero_licitacao=raw.get("numeroControlePNCP", "") or raw.get("numeroAta", ""),
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
        """Fetch all PNCP records matching the query.

        Fetches both /contratacoes/publicacao and /atas endpoints in parallel,
        then combines and deduplicates results.
        """
        loop = asyncio.get_event_loop()

        # Fetch contratacoes and atas in parallel
        contratacoes_future = loop.run_in_executor(
            None,
            lambda: list(
                self._client.fetch_all(
                    data_inicial=query.data_inicial,
                    data_final=query.data_final,
                    ufs=query.ufs,
                    modalidades=query.modalidades,
                    on_progress=on_progress,
                    search_terms=query.search_terms,
                )
            ),
        )

        atas_future = loop.run_in_executor(
            None,
            lambda: list(
                self._client.fetch_all_atas(
                    data_inicial=query.data_inicial,
                    data_final=query.data_final,
                    ufs=query.ufs,
                    on_progress=on_progress,
                    search_terms=query.search_terms,
                )
            ),
        )

        contratacoes_raw, atas_raw = await asyncio.gather(
            contratacoes_future, atas_future
        )

        logger.info(
            f"PNCP fetched {len(contratacoes_raw)} contratacoes + "
            f"{len(atas_raw)} atas de registro de preco"
        )

        # Combine and deduplicate by id
        all_items = contratacoes_raw + atas_raw
        seen_ids: set[str] = set()
        unique_items: List[dict] = []
        for item in all_items:
            item_id = item.get("numeroControlePNCP", "") or item.get("codigoCompra", "")
            if item_id and item_id in seen_ids:
                continue
            if item_id:
                seen_ids.add(item_id)
            unique_items.append(item)

        return [self.normalize(item) for item in unique_items]

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
