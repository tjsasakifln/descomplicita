"""Multi-source procurement data integration package."""

from sources.base import DataSourceClient, NormalizedRecord, SearchQuery
from sources.orchestrator import (
    MultiSourceOrchestrator,
    OrchestratorResult,
    SourceStats,
    get_enabled_source_names,
)
from sources.transparencia_source import TransparenciaSource

__all__ = [
    "DataSourceClient",
    "NormalizedRecord",
    "SearchQuery",
    "MultiSourceOrchestrator",
    "OrchestratorResult",
    "SourceStats",
    "TransparenciaSource",
    "get_enabled_source_names",
]
