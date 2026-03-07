"""Abstract base classes and schemas for multi-source procurement integration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SearchQuery:
    """Unified search query parameters for all data sources."""

    data_inicial: str
    data_final: str
    ufs: Optional[List[str]] = None
    modalidades: Optional[List[int]] = None


@dataclass
class NormalizedRecord:
    """Unified procurement record schema across all data sources.

    Every source adapter normalizes its raw API response into this schema,
    enabling the downstream pipeline (filter, excel, llm) to operate
    source-agnostically.
    """

    id: str
    source: str
    sources: List[str]
    numero_licitacao: str
    objeto: str
    orgao: str
    cnpj_orgao: str
    uf: str
    municipio: str
    valor_estimado: Optional[float]
    modalidade: str
    modalidade_codigo: Optional[int] = None
    data_publicacao: Optional[datetime] = None
    data_abertura: Optional[datetime] = None
    status: Optional[str] = None
    url_edital: Optional[str] = None
    url_fonte: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Return a dict compatible with the existing pipeline (filter, excel, llm).

        Merges raw_data (which contains all original API fields) with the
        normalized field names, so both old (PNCP-specific) and new
        (NormalizedRecord) field names are accessible.
        """
        result = dict(self.raw_data)
        result.update({
            "id": self.id,
            "source": self.source,
            "sources": self.sources,
            "numero_licitacao": self.numero_licitacao,
            "objeto": self.objeto,
            "orgao": self.orgao,
            "cnpj_orgao": self.cnpj_orgao,
            "uf": self.uf,
            "municipio": self.municipio,
            "valor_estimado": self.valor_estimado,
            "modalidade": self.modalidade,
            "modalidade_codigo": self.modalidade_codigo,
            "data_publicacao": self.data_publicacao,
            "data_abertura": self.data_abertura,
            "status": self.status,
            "url_edital": self.url_edital,
            "url_fonte": self.url_fonte,
        })
        return result


class DataSourceClient(ABC):
    """Abstract base class for procurement data source adapters.

    Each data source (PNCP, Compras.gov.br, Portal da Transparencia, etc.)
    implements this interface to provide a unified API for fetching and
    normalizing procurement records.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name of this data source."""
        ...

    @abstractmethod
    async def fetch_records(self, query: SearchQuery) -> List[NormalizedRecord]:
        """Fetch and normalize procurement records matching the query.

        Args:
            query: Search parameters (dates, UFs, modalidades).

        Returns:
            List of normalized procurement records.
        """
        ...

    @abstractmethod
    def normalize(self, raw: dict) -> NormalizedRecord:
        """Convert a single raw API response item into a NormalizedRecord.

        Args:
            raw: Raw dict from the source API.

        Returns:
            Normalized record.
        """
        ...

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if this data source is reachable and functional."""
        ...
