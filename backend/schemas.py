"""Pydantic schemas for API request/response validation."""

from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Optional

from config import MAX_DATE_RANGE_DAYS


class BuscaRequest(BaseModel):
    """
    Request schema for /buscar endpoint.

    Validates user input for procurement search:
    - At least 1 Brazilian state (UF) must be selected
    - Dates must be in YYYY-MM-DD format
    - data_inicial must be <= data_final
    - Date range cannot exceed 30 days
    - data_final cannot be in the future

    Examples:
        >>> request = BuscaRequest(
        ...     ufs=["SP", "RJ"],
        ...     data_inicial="2025-01-01",
        ...     data_final="2025-01-31"
        ... )
        >>> request.ufs
        ['SP', 'RJ']
    """

    ufs: List[str] = Field(
        ...,
        min_length=1,
        description="List of Brazilian state codes (e.g., ['SP', 'RJ', 'MG'])",
        examples=[["SP", "RJ"]],
    )
    data_inicial: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Start date in YYYY-MM-DD format",
        examples=["2025-01-01"],
    )
    data_final: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="End date in YYYY-MM-DD format",
        examples=["2025-01-31"],
    )
    setor_id: str = Field(
        default="vestuario",
        description="Sector ID for keyword filtering (e.g., 'vestuario', 'alimentos', 'informatica')",
        examples=["vestuario"],
    )
    termos_busca: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Custom search terms separated by spaces (e.g., 'jaleco avental'). "
                    "Each space-separated word is treated as an additional keyword.",
        examples=["jaleco avental"],
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "BuscaRequest":
        """Validate date business logic before hitting PNCP API."""
        try:
            d_ini = date.fromisoformat(self.data_inicial)
            d_fin = date.fromisoformat(self.data_final)
        except ValueError as e:
            raise ValueError(f"Data inválida: {e}")

        if d_ini > d_fin:
            raise ValueError(
                "Data inicial deve ser anterior ou igual à data final"
            )

        date_range = (d_fin - d_ini).days
        if date_range > MAX_DATE_RANGE_DAYS:
            raise ValueError(
                f"Intervalo de datas excede o máximo permitido de {MAX_DATE_RANGE_DAYS} dias "
                f"(solicitado: {date_range} dias)"
            )

        return self

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ufs": ["SP", "RJ"],
            "data_inicial": "2025-01-01",
            "data_final": "2025-01-31",
        }
    })


class ResumoLicitacoes(BaseModel):
    """
    Executive summary schema for procurement search results.

    This schema will be populated by GPT-4.1-nano (Issue #14) or
    fallback mechanism (Issue #15). For now, it defines the structure
    that the LLM module must adhere to.

    Fields:
        resumo_executivo: Brief 1-2 sentence summary
        total_oportunidades: Count of filtered procurement opportunities
        valor_total: Sum of all bid values in BRL
        destaques: List of 2-5 key highlights (e.g., "3 urgente opportunities")
        alerta_urgencia: Optional alert for time-sensitive bids
    """

    resumo_executivo: str = Field(
        ...,
        description="1-2 sentence executive summary",
        examples=[
            "Encontradas 15 licitações de uniformes em SP e RJ, totalizando R$ 2.3M."
        ],
    )
    total_oportunidades: int = Field(
        ..., ge=0, description="Number of procurement opportunities found"
    )
    valor_total: float = Field(
        ..., ge=0.0, description="Total value of all opportunities in BRL"
    )
    destaques: List[str] = Field(
        default_factory=list,
        description="Key highlights (2-5 bullet points)",
        examples=[["3 licitações com prazo até 48h", "Maior valor: R$ 500k em SP"]],
    )
    alerta_urgencia: Optional[str] = Field(
        default=None,
        description="Optional urgency alert for time-sensitive opportunities",
        examples=["⚠️ 5 licitações encerram em 24 horas"],
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "resumo_executivo": "Encontradas 15 licitações de uniformes em SP e RJ.",
            "total_oportunidades": 15,
            "valor_total": 2300000.00,
            "destaques": [
                "3 licitações com prazo até 48h",
                "Maior valor: R$ 500k em SP",
            ],
            "alerta_urgencia": None,
        }
    })


class FilterStats(BaseModel):
    """Statistics about filter rejection reasons."""

    rejeitadas_uf: int = Field(default=0, description="Rejected by UF filter")
    rejeitadas_valor: int = Field(default=0, description="Rejected by value range")
    rejeitadas_keyword: int = Field(default=0, description="Rejected by keyword match")
    rejeitadas_prazo: int = Field(default=0, description="Rejected by deadline")
    rejeitadas_outros: int = Field(default=0, description="Rejected by other reasons")


class BuscaResponse(BaseModel):
    """
    Response schema for /buscar endpoint (v0.3.0+).

    Returns the complete search results including:
    - AI-generated executive summary
    - Statistics about raw vs filtered results
    - Multi-source metadata (sources used, dedup stats)

    Excel download is available via GET /buscar/{job_id}/download (StreamingResponse).
    """

    resumo: ResumoLicitacoes = Field(
        ..., description="Executive summary (AI-generated or fallback)"
    )
    total_raw: int = Field(
        ..., ge=0, description="Total records fetched from all sources (before filtering)"
    )
    total_filtrado: int = Field(
        ...,
        ge=0,
        description="Records after applying filters (UF, value, keywords, deadline)",
    )
    filter_stats: Optional[FilterStats] = Field(
        default=None, description="Breakdown of filter rejection reasons"
    )
    sources_used: Optional[List[str]] = Field(
        default=None, description="Data sources that returned results successfully"
    )
    source_stats: Optional[dict] = Field(
        default=None, description="Per-source statistics (fetched, dedup, elapsed, status)"
    )
    dedup_removed: Optional[int] = Field(
        default=None, description="Number of duplicate records removed across sources"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "resumo": {
                "resumo_executivo": "Encontradas 15 licitações.",
                "total_oportunidades": 15,
                "valor_total": 2300000.00,
                "destaques": ["3 urgentes"],
                "alerta_urgencia": None,
            },
            "total_raw": 523,
            "total_filtrado": 15,
        }
    })


# ---------------------------------------------------------------------------
# Async job schemas (SP-001.3)
# ---------------------------------------------------------------------------


class JobCreatedResponse(BaseModel):
    """Response returned when an async search job is created."""

    job_id: str
    status: str = "queued"


class JobProgress(BaseModel):
    """Progress information for a running search job."""

    phase: str = "queued"
    ufs_completed: int = 0
    ufs_total: int = 0
    items_fetched: int = 0
    items_filtered: int = 0
    sources_completed: int = 0
    sources_total: int = 0


class JobStatusResponse(BaseModel):
    """Polling response with current job status and progress."""

    job_id: str
    status: str
    progress: JobProgress
    created_at: str
    elapsed_seconds: float


class JobResultResponse(BaseModel):
    """Final result of a completed (or failed) search job."""

    job_id: str
    status: str
    resumo: Optional[ResumoLicitacoes] = None
    total_raw: Optional[int] = None
    total_filtrado: Optional[int] = None
    filter_stats: Optional[FilterStats] = None
    error: Optional[str] = None
