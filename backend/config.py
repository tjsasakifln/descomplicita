"""Configuration models for PNCP client."""

from dataclasses import dataclass, field
from typing import Tuple, Type, List
import logging
import sys


# PNCP Modality Codes (codigoModalidadeContratacao)
# Source: https://pncp.gov.br/api/pncp/v1/modalidades
MODALIDADES_PNCP = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
    14: "Inaplicabilidade da Licitação",
    15: "Chamada pública",
}

# Default modalities for BidIQ search
# Competitive procurement + high-volume modalities for uniforms, medicines, food
DEFAULT_MODALIDADES: List[int] = [
    4,   # Concorrência - Eletrônica
    5,   # Concorrência - Presencial
    6,   # Pregão - Eletrônico (most common for uniforms)
    7,   # Pregão - Presencial
    8,   # Dispensa
    13,  # Leilão - Presencial (SE-001.3: Ata de Registro de Preços)
    15,  # Chamada pública (SE-001.3: agricultura familiar, medicamentos)
]

# Maximum pages to fetch per UF×modalidade combination.
# PNCP page size is 50 items, so 10 pages = 500 items per combo.
# With 3 UFs × 7 modalidades = 21 combos, this yields up to 10,500 raw items
# before filtering — more than enough for keyword-based sector filtering.
# Without this cap, large combos (e.g., SP×Pregão = 228 pages) overwhelm the
# PNCP server with concurrent requests, causing cascading timeouts.
MAX_PAGES_PER_COMBO: int = 10


@dataclass
class RetryConfig:
    """Configuration for HTTP retry logic."""

    max_retries: int = 2
    base_delay: float = 1.0  # seconds
    max_delay: float = 10.0  # seconds
    exponential_base: int = 2
    jitter: bool = True
    timeout: int = 25  # HTTP timeout per individual request (seconds)

    # HTTP status codes that should trigger retry
    retryable_status_codes: Tuple[int, ...] = field(
        default_factory=lambda: (408, 429, 500, 502, 503, 504)
    )

    # Exception types that should trigger retry
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (
            ConnectionError,
            TimeoutError,
        )
    )


# ---------------------------------------------------------------------------
# Multi-source configuration (MS-001.1)
# ---------------------------------------------------------------------------

SOURCES_CONFIG = {
    # timeout = orchestrator timeout for the full source operation (seconds),
    # NOT the HTTP timeout per individual request (see RetryConfig.timeout).
    "pncp": {
        "enabled": True,
        "base_url": "https://pncp.gov.br/api/consulta/v1",
        "auth": None,
        "rate_limit_rps": 10,
        "timeout": 300,  # 7 UFs x 7 modalidades = 49 combos; with max_pages cap, ~120-180s typical
        "priority": 1,
    },
    # Disabled 2026-03-07: licitacoes/v1 endpoint returns 404.
    # API migrated to compras.dados.gov.br (contracts only, no licitacoes).
    # Licitacoes data consolidated into PNCP. See story SR-001.3.
    "comprasgov": {
        "enabled": False,
        "base_url": "https://dadosabertos.compras.gov.br",
        "auth": None,
        "rate_limit_rps": 5,
        "timeout": 60,
        "priority": 2,
    },
    "transparencia": {
        "enabled": True,
        "base_url": "https://api.portaldatransparencia.gov.br",
        "auth": {"type": "api_key", "header": "chave-api-dados", "env_var": "TRANSPARENCIA_API_KEY"},
        "rate_limit_rps": 3,
        "timeout": 90,
        "priority": 3,
    },
    "querido_diario": {
        "enabled": False,  # SR-001.4: API returns HTML instead of JSON since ~2026-03; endpoint deprecated
        "base_url": "https://queridodiario.ok.org.br/api/",
        "auth": None,
        "rate_limit_rps": 5,
        "timeout": 60,
        "priority": 4,
    },
    # SR-001.5: API endpoint /api/v1/compras-diretas returns 404 since ~2026-03; endpoint deprecated
    "tce_rj": {
        "enabled": False,
        "base_url": "https://dados.tcerj.tc.br",
        "auth": None,
        "rate_limit_rps": 3,
        "timeout": 90,
        "priority": 5,
    },
}


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application.

    Sets up a consistent logging format across all modules with proper
    level filtering and suppression of verbose third-party libraries.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to INFO.

    Example:
        >>> setup_logging("DEBUG")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
        2026-01-25 23:00:00 | INFO     | __main__ | Application started
    """
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(handler)

    # Silence verbose logs from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
