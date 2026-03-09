"""Generate JSON Schema from Pydantic models for contract testing (XD-API-02).

Run this script to export JSON schemas that can be validated against
TypeScript type definitions in the frontend.

Usage:
    python schemas_contract.py > contracts/backend_schemas.json
"""

import json

from schemas import (
    BuscaRequest,
    ResumoLicitacoes,
    FilterStats,
    BuscaResponse,
    JobCreatedResponse,
    JobProgress,
    JobStatusResponse,
    JobResultResponse,
)
from error_codes import ErrorCode


def generate_contract_schemas() -> dict:
    """Generate JSON schemas for all API models."""
    schemas = {
        "BuscaRequest": BuscaRequest.model_json_schema(),
        "ResumoLicitacoes": ResumoLicitacoes.model_json_schema(),
        "FilterStats": FilterStats.model_json_schema(),
        "BuscaResponse": BuscaResponse.model_json_schema(),
        "JobCreatedResponse": JobCreatedResponse.model_json_schema(),
        "JobProgress": JobProgress.model_json_schema(),
        "JobStatusResponse": JobStatusResponse.model_json_schema(),
        "JobResultResponse": JobResultResponse.model_json_schema(),
        "ErrorCodes": [code.value for code in ErrorCode],
    }
    return schemas


if __name__ == "__main__":
    print(json.dumps(generate_contract_schemas(), indent=2, ensure_ascii=False))
