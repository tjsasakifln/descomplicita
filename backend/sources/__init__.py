"""Multi-source procurement data integration package."""

from sources.base import DataSourceClient, NormalizedRecord, SearchQuery
from sources.comprasgov_source import ComprasGovSource

__all__ = ["DataSourceClient", "NormalizedRecord", "SearchQuery", "ComprasGovSource"]
