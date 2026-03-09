"""
LLM integration module for generating executive summaries of procurement bids.

This module uses OpenAI's GPT-4.1-nano model with structured output to create
actionable summaries of filtered procurement opportunities. It includes:
- Token-optimized input preparation (max 50 bids)
- Structured output using Pydantic schemas
- Async native client (TD-H03: no run_in_executor)
- Error handling for API failures
- Empty input handling

Usage:
    from llm import gerar_resumo

    licitacoes = [...]  # List of filtered bids
    resumo = await gerar_resumo(licitacoes)
    print(resumo.resumo_executivo)
"""

from datetime import datetime
from typing import Any
import json
import os

from openai import AsyncOpenAI

from schemas import ResumoLicitacoes
from excel import parse_datetime


async def gerar_resumo(licitacoes: list[dict[str, Any]], sector_name: str = "uniformes e fardamentos") -> ResumoLicitacoes:
    """
    Generate AI-powered executive summary of procurement bids using GPT-4.1-nano.

    Uses AsyncOpenAI client natively (TD-H03) — no thread pool executor needed.

    Args:
        licitacoes: List of filtered procurement bid dictionaries from PNCP API.
        sector_name: Name of the procurement sector for context.

    Returns:
        ResumoLicitacoes: Structured summary.

    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set.
        openai.APIError: Network issues, rate limits, auth failures.
    """
    # Handle empty input
    if not licitacoes:
        return ResumoLicitacoes(
            resumo_executivo="Nenhuma licitação de uniformes encontrada no período selecionado.",
            total_oportunidades=0,
            valor_total=0.0,
            destaques=[],
            alerta_urgencia=None,
        )

    # Validate API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Please configure your OpenAI API key."
        )

    # Prepare data for LLM (limit to 50 bids to avoid token overflow)
    dados_resumidos = []
    for lic in licitacoes[:50]:
        dados_resumidos.append(
            {
                "objeto": (lic.get("objetoCompra") or "")[
                    :200
                ],  # Truncate to 200 chars
                "orgao": lic.get("nomeOrgao") or "",
                "uf": lic.get("uf") or "",
                "municipio": lic.get("municipio") or "",
                "valor": lic.get("valorTotalEstimado") or 0,
                "abertura": lic.get("dataAberturaProposta") or "",
            }
        )

    # Initialize async OpenAI client (TD-H03)
    client = AsyncOpenAI(api_key=api_key)

    # System prompt with expert persona and rules
    system_prompt = f"""Você é um analista de licitações especializado em {sector_name}.
Analise as licitações fornecidas e gere um resumo executivo.

REGRAS:
- Seja direto e objetivo
- Destaque as maiores oportunidades por valor
- Alerte sobre prazos próximos (< 7 dias)
- Mencione a distribuição geográfica
- Use linguagem profissional, não técnica demais
- Valores sempre em reais (R$) formatados
"""

    # User prompt with context
    user_prompt = f"""Analise estas {len(licitacoes)} licitações de {sector_name} e gere um resumo:

{json.dumps(dados_resumidos, ensure_ascii=False, indent=2)}

Data atual: {datetime.now().strftime("%d/%m/%Y")}
"""

    # Call OpenAI API with structured output (async)
    response = await client.beta.chat.completions.parse(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=ResumoLicitacoes,
        temperature=0.3,
        max_tokens=500,
    )

    # Extract parsed response
    resumo = response.choices[0].message.parsed

    if not resumo:
        raise ValueError("OpenAI API returned empty response")

    return resumo


def format_resumo_html(resumo: ResumoLicitacoes) -> str:
    """
    Format executive summary as HTML for frontend display.

    Converts the structured ResumoLicitacoes object into styled HTML with:
    - Executive summary paragraph
    - Statistics cards (count and total value)
    - Urgency alert (if present)
    - Highlights list

    Args:
        resumo: Structured summary from gerar_resumo()

    Returns:
        str: HTML string ready for frontend rendering
    """
    # Build urgency alert HTML if present
    alerta_html = ""
    if resumo.alerta_urgencia:
        alerta_html = f'<div class="alerta-urgencia">⚠️ {resumo.alerta_urgencia}</div>'

    # Build highlights list HTML
    destaques_html = ""
    if resumo.destaques:
        destaques_items = "".join(f"<li>{d}</li>" for d in resumo.destaques)
        destaques_html = f"""
        <div class="destaques">
            <h4>Destaques:</h4>
            <ul>
                {destaques_items}
            </ul>
        </div>
        """

    # Assemble complete HTML
    html = f"""
    <div class="resumo-container">
        <p class="resumo-executivo">{resumo.resumo_executivo}</p>

        <div class="resumo-stats">
            <div class="stat">
                <span class="stat-value">{resumo.total_oportunidades}</span>
                <span class="stat-label">Licitações</span>
            </div>
            <div class="stat">
                <span class="stat-value">R$ {resumo.valor_total:,.2f}</span>
                <span class="stat-label">Valor Total</span>
            </div>
        </div>

        {alerta_html}

        {destaques_html}
    </div>
    """

    return html


def gerar_resumo_fallback(licitacoes: list[dict[str, Any]], sector_name: str = "uniformes") -> ResumoLicitacoes:
    """
    Generate basic executive summary without using LLM (fallback for OpenAI failures).

    This is a sync function (no external API calls) used as fallback when
    AsyncOpenAI is unavailable.

    Args:
        licitacoes: List of filtered procurement bid dictionaries.
        sector_name: Sector name for the summary text.

    Returns:
        ResumoLicitacoes: Statistical summary (no AI).
    """
    # Handle empty input
    if not licitacoes:
        return ResumoLicitacoes(
            resumo_executivo="Nenhuma licitação encontrada.",
            total_oportunidades=0,
            valor_total=0.0,
            destaques=[],
            alerta_urgencia=None,
        )

    # Calculate basic statistics
    total = len(licitacoes)
    valor_total = sum(lic.get("valorTotalEstimado", 0) or 0 for lic in licitacoes)

    # Compute UF distribution (state-wise breakdown)
    dist_uf: dict[str, int] = {}
    for lic in licitacoes:
        uf = lic.get("uf", "N/A")
        dist_uf[uf] = dist_uf.get(uf, 0) + 1

    # Find top 3 bids by value
    top_valor = sorted(
        licitacoes, key=lambda x: x.get("valorTotalEstimado", 0) or 0, reverse=True
    )[:3]

    destaques = [
        f"{lic.get('nomeOrgao', 'N/A')}: R$ {(lic.get('valorTotalEstimado') or 0):,.2f}"
        for lic in top_valor
    ]

    # Check for urgency (deadline < 7 days)
    alerta = None
    hoje = datetime.now()
    for lic in licitacoes:
        data_abertura_str = lic.get("dataAberturaProposta")
        if not data_abertura_str:
            continue

        abertura = parse_datetime(data_abertura_str)
        if abertura:
            dias_restantes = (abertura - hoje).days
            if dias_restantes < 7:
                orgao = lic.get("nomeOrgao", "Órgão não informado")
                alerta = f"Licitação com prazo em menos de 7 dias: {orgao}"
                break  # First urgent bid found

    return ResumoLicitacoes(
        resumo_executivo=(
            f"Encontradas {total} licitações de {sector_name} "
            f"totalizando R$ {valor_total:,.2f}."
        ),
        total_oportunidades=total,
        valor_total=valor_total,
        destaques=destaques,
        alerta_urgencia=alerta,
    )
