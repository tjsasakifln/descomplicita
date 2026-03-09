"""Structured error codes for API responses (TD-L02/XD-API-03).

Provides standardized error responses with machine-readable codes,
human-readable messages, and optional details for debugging.

Usage:
    from error_codes import ErrorCode, error_response

    # In a route handler:
    raise error_response(ErrorCode.SEARCH_TIMEOUT, details={"job_id": "abc"})

    # Or build a dict for job store:
    err = ErrorCode.PNCP_RATE_LIMITED.to_dict(details={"retry_after": 60})
"""

from enum import Enum
from typing import Any, Optional

from fastapi import HTTPException


class ErrorCode(str, Enum):
    """Machine-readable error codes for all API error responses."""

    # --- Search errors ---
    SEARCH_TIMEOUT = "SEARCH_TIMEOUT"
    SEARCH_FAILED = "SEARCH_FAILED"
    SEARCH_NO_RESULTS = "SEARCH_NO_RESULTS"
    SEARCH_INVALID_SECTOR = "SEARCH_INVALID_SECTOR"

    # --- PNCP source errors ---
    PNCP_RATE_LIMITED = "PNCP_RATE_LIMITED"
    PNCP_UNAVAILABLE = "PNCP_UNAVAILABLE"
    PNCP_TIMEOUT = "PNCP_TIMEOUT"
    PNCP_SERVER_ERROR = "PNCP_SERVER_ERROR"

    # --- Job errors ---
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_NOT_COMPLETED = "JOB_NOT_COMPLETED"
    JOB_EXPIRED = "JOB_EXPIRED"
    TOO_MANY_JOBS = "TOO_MANY_JOBS"

    # --- Validation errors ---
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    INVALID_UFS = "INVALID_UFS"

    # --- Download errors ---
    DOWNLOAD_NOT_AVAILABLE = "DOWNLOAD_NOT_AVAILABLE"
    DOWNLOAD_TOO_LARGE = "DOWNLOAD_TOO_LARGE"

    # --- Auth errors ---
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID_KEY = "AUTH_INVALID_KEY"
    AUTH_JWT_EXPIRED = "AUTH_JWT_EXPIRED"
    AUTH_JWT_INVALID = "AUTH_JWT_INVALID"
    JWT_NOT_CONFIGURED = "JWT_NOT_CONFIGURED"

    # --- Rate limiting ---
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # --- Server errors ---
    INTERNAL_ERROR = "INTERNAL_ERROR"
    LLM_GENERATION_FAILED = "LLM_GENERATION_FAILED"

    def to_dict(
        self,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Build a structured error dict for JSON responses."""
        return {
            "error": {
                "code": self.value,
                "message": message or _DEFAULT_MESSAGES.get(self, "An error occurred."),
                **({"details": details} if details else {}),
            }
        }


# Default human-readable messages for each error code
_DEFAULT_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.SEARCH_TIMEOUT: "A consulta excedeu o tempo limite.",
    ErrorCode.SEARCH_FAILED: "Erro interno durante a busca.",
    ErrorCode.SEARCH_NO_RESULTS: "Nenhum resultado encontrado para os filtros selecionados.",
    ErrorCode.SEARCH_INVALID_SECTOR: "Setor de busca inválido.",
    ErrorCode.PNCP_RATE_LIMITED: "O PNCP está limitando requisições. Aguarde e tente novamente.",
    ErrorCode.PNCP_UNAVAILABLE: (
        "O Portal Nacional de Contratações (PNCP) está temporariamente "
        "indisponível. Tente novamente em alguns instantes."
    ),
    ErrorCode.PNCP_TIMEOUT: "A requisição ao PNCP excedeu o tempo limite.",
    ErrorCode.PNCP_SERVER_ERROR: "O PNCP retornou um erro interno.",
    ErrorCode.JOB_NOT_FOUND: "Busca não encontrada ou expirada.",
    ErrorCode.JOB_NOT_COMPLETED: "A busca ainda não foi concluída.",
    ErrorCode.JOB_EXPIRED: "Os resultados desta busca expiraram.",
    ErrorCode.TOO_MANY_JOBS: "Muitas buscas simultâneas. Aguarde a conclusão de uma busca anterior.",
    ErrorCode.VALIDATION_ERROR: "Dados de entrada inválidos.",
    ErrorCode.INVALID_DATE_RANGE: "Intervalo de datas inválido.",
    ErrorCode.INVALID_UFS: "Estados (UFs) inválidos.",
    ErrorCode.DOWNLOAD_NOT_AVAILABLE: "Arquivo Excel não disponível.",
    ErrorCode.DOWNLOAD_TOO_LARGE: "Arquivo excede o tamanho máximo permitido.",
    ErrorCode.AUTH_REQUIRED: "Autenticação necessária.",
    ErrorCode.AUTH_INVALID_KEY: "Chave de API inválida.",
    ErrorCode.AUTH_JWT_EXPIRED: "Token JWT expirado.",
    ErrorCode.AUTH_JWT_INVALID: "Token JWT inválido.",
    ErrorCode.JWT_NOT_CONFIGURED: "Autenticação JWT não configurada no servidor.",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Limite de requisições excedido. Tente novamente mais tarde.",
    ErrorCode.INTERNAL_ERROR: "Erro interno do servidor.",
    ErrorCode.LLM_GENERATION_FAILED: "Falha na geração do resumo executivo.",
}


def error_response(
    code: ErrorCode,
    status_code: int = 400,
    message: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> HTTPException:
    """Create an HTTPException with structured error body."""
    return HTTPException(
        status_code=status_code,
        detail=code.to_dict(message=message, details=details),
    )
