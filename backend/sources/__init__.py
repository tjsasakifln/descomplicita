"""Multi-source procurement data integration package."""

from sources.base import DataSourceClient, NormalizedRecord, SearchQuery
from sources.comprasgov_source import ComprasGovSource
from sources.querido_diario_source import QueridoDiarioSource
from sources.tce_rj_source import TCERJSource
from sources.transparencia_source import TransparenciaSource

__all__ = [
    "DataSourceClient",
    "NormalizedRecord",
    "SearchQuery",
    "ComprasGovSource",
    "QueridoDiarioSource",
    "TCERJSource",
    "TransparenciaSource",
]
