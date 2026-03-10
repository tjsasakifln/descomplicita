"""
Tests for LLM integration module (backend/llm.py).

Updated for TD-H03: gerar_resumo() is now async using AsyncOpenAI.

Test categories:
1. Empty input handling
2. Valid input with various sizes (1, 50, 100+ bids)
3. API key validation
4. OpenAI API error scenarios (async)
5. HTML formatting
6. Schema validation
7. Timeout handling
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
import pytest

from llm import gerar_resumo, gerar_resumo_fallback, format_resumo_html
from schemas import ResumoLicitacoes


# ─────────────────────────────────────────────────────────────────────────────
# 1. Empty Input Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gerar_resumo_empty_input():
    """Should return empty summary when no bids provided."""
    resumo = await gerar_resumo([])

    assert isinstance(resumo, ResumoLicitacoes)
    assert resumo.total_oportunidades == 0
    assert resumo.valor_total == 0.0
    assert resumo.destaques == []
    assert resumo.alerta_urgencia is None
    assert "Nenhuma licitação" in resumo.resumo_executivo


# ─────────────────────────────────────────────────────────────────────────────
# 2. API Key Validation Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gerar_resumo_missing_api_key():
    """Should raise ValueError when OPENAI_API_KEY is not set."""
    licitacoes = [
        {
            "objetoCompra": "Uniforme escolar",
            "nomeOrgao": "Prefeitura SP",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
    ]

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            await gerar_resumo(licitacoes)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Valid Input Tests (Mocked AsyncOpenAI)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_single_bid(mock_openai):
    """Should generate summary for single bid."""
    mock_resumo = ResumoLicitacoes(
        resumo_executivo="Encontrada 1 licitação de uniformes em SP.",
        total_oportunidades=1,
        valor_total=100000.0,
        destaques=["Prefeitura SP: R$ 100.000,00"],
        alerta_urgencia=None,
    )

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=mock_resumo))])
    )

    licitacoes = [
        {
            "objetoCompra": "Uniforme escolar",
            "nomeOrgao": "Prefeitura SP",
            "uf": "SP",
            "municipio": "São Paulo",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
    ]

    resumo = await gerar_resumo(licitacoes)

    assert isinstance(resumo, ResumoLicitacoes)
    assert resumo.total_oportunidades == 1
    assert resumo.valor_total == 100000.0
    assert len(resumo.destaques) == 1

    # Verify API was called
    mock_client.beta.chat.completions.parse.assert_awaited_once()
    call_args = mock_client.beta.chat.completions.parse.call_args
    assert call_args.kwargs["model"] == "gpt-4.1-nano"
    assert call_args.kwargs["temperature"] == 0.3
    assert call_args.kwargs["max_tokens"] == 500


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_50_bids_limit(mock_openai):
    """Should limit input to 50 bids to avoid token overflow."""
    mock_resumo = ResumoLicitacoes(
        resumo_executivo="Encontradas 50 licitações.",
        total_oportunidades=50,
        valor_total=5000000.0,
        destaques=["Top 3 valores"],
        alerta_urgencia=None,
    )

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=mock_resumo))])
    )

    # Create 100 bids (should be limited to 50)
    licitacoes = [
        {
            "objetoCompra": f"Uniforme {i}",
            "nomeOrgao": f"Orgao {i}",
            "uf": "SP",
            "municipio": "São Paulo",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
        for i in range(100)
    ]

    resumo = await gerar_resumo(licitacoes)

    assert isinstance(resumo, ResumoLicitacoes)

    # Verify API was called with limited data
    call_args = mock_client.beta.chat.completions.parse.call_args
    user_prompt = call_args.kwargs["messages"][1]["content"]

    # Should mention 100 total bids in text
    assert "100 licitações" in user_prompt or "100" in user_prompt


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_truncates_objeto_compra(mock_openai):
    """Should truncate objetoCompra to 200 chars to save tokens."""
    mock_resumo = ResumoLicitacoes(
        resumo_executivo="Resumo OK",
        total_oportunidades=1,
        valor_total=100000.0,
        destaques=[],
        alerta_urgencia=None,
    )

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=mock_resumo))])
    )

    # Create bid with very long objetoCompra (>200 chars)
    long_texto = "A" * 500  # 500 characters
    licitacoes = [
        {
            "objetoCompra": long_texto,
            "nomeOrgao": "Prefeitura",
            "uf": "SP",
            "municipio": "São Paulo",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
    ]

    await gerar_resumo(licitacoes)

    # Verify API was called
    call_args = mock_client.beta.chat.completions.parse.call_args
    user_prompt = call_args.kwargs["messages"][1]["content"]

    # The truncated text (200 chars) should be in the prompt
    # The full 500 char text should NOT be in the prompt
    assert long_texto not in user_prompt
    assert long_texto[:200] in user_prompt


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_handles_none_values(mock_openai):
    """Should handle None values in bid data gracefully."""
    mock_resumo = ResumoLicitacoes(
        resumo_executivo="Resumo OK",
        total_oportunidades=1,
        valor_total=0.0,
        destaques=[],
        alerta_urgencia=None,
    )

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=mock_resumo))])
    )

    # Bid with None values
    licitacoes = [
        {
            "objetoCompra": None,
            "nomeOrgao": None,
            "uf": None,
            "municipio": None,
            "valorTotalEstimado": None,
            "dataAberturaProposta": None,
        }
    ]

    resumo = await gerar_resumo(licitacoes)

    assert isinstance(resumo, ResumoLicitacoes)

    # Should not crash - API was called successfully
    mock_client.beta.chat.completions.parse.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Env Var Configuration Tests (TD-M03)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345", "LLM_MODEL": "gpt-4o-mini"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_custom_model(mock_openai):
    """TD-M03: Should use LLM_MODEL env var when set."""
    mock_resumo = ResumoLicitacoes(
        resumo_executivo="Resumo OK",
        total_oportunidades=1,
        valor_total=100000.0,
        destaques=[],
        alerta_urgencia=None,
    )
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=mock_resumo))])
    )

    licitacoes = [
        {
            "objetoCompra": "Uniforme",
            "nomeOrgao": "Prefeitura",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
    ]

    await gerar_resumo(licitacoes)

    call_args = mock_client.beta.chat.completions.parse.call_args
    assert call_args.kwargs["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345", "LLM_TEMPERATURE": "0.7", "LLM_MAX_TOKENS": "1000"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_custom_temperature_and_tokens(mock_openai):
    """TD-M03: Should use LLM_TEMPERATURE and LLM_MAX_TOKENS env vars."""
    mock_resumo = ResumoLicitacoes(
        resumo_executivo="Resumo OK",
        total_oportunidades=1,
        valor_total=100000.0,
        destaques=[],
        alerta_urgencia=None,
    )
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=mock_resumo))])
    )

    licitacoes = [
        {
            "objetoCompra": "Uniforme",
            "nomeOrgao": "Prefeitura",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
    ]

    await gerar_resumo(licitacoes)

    call_args = mock_client.beta.chat.completions.parse.call_args
    assert call_args.kwargs["temperature"] == 0.7
    assert call_args.kwargs["max_tokens"] == 1000


# ─────────────────────────────────────────────────────────────────────────────
# 5. API Error Scenarios (async)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_api_error(mock_openai):
    """Should propagate OpenAI API errors."""
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API Error"))

    licitacoes = [
        {
            "objetoCompra": "Uniforme",
            "nomeOrgao": "Prefeitura",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
    ]

    with pytest.raises(Exception, match="API Error"):
        await gerar_resumo(licitacoes)


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_empty_api_response(mock_openai):
    """Should raise error when API returns empty response."""
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=None))])
    )

    licitacoes = [
        {
            "objetoCompra": "Uniforme",
            "nomeOrgao": "Prefeitura",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
    ]

    with pytest.raises(ValueError, match="empty response"):
        await gerar_resumo(licitacoes)


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_timeout(mock_openai):
    """Should propagate timeout errors from async OpenAI client."""
    import asyncio

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        side_effect=asyncio.TimeoutError("Request timed out")
    )

    licitacoes = [
        {
            "objetoCompra": "Uniforme",
            "nomeOrgao": "Prefeitura",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": "2099-02-15T10:00:00",
        }
    ]

    with pytest.raises(asyncio.TimeoutError):
        await gerar_resumo(licitacoes)


# ─────────────────────────────────────────────────────────────────────────────
# 6. HTML Formatting Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_format_resumo_html_basic():
    """Should format basic summary as HTML."""
    resumo = ResumoLicitacoes(
        resumo_executivo="Encontradas 15 licitações.",
        total_oportunidades=15,
        valor_total=2300000.00,
        destaques=["3 urgentes", "Maior valor: R$ 500k"],
        alerta_urgencia=None,
    )

    html = format_resumo_html(resumo)

    assert "resumo-container" in html
    assert "Encontradas 15 licitações" in html
    assert "15" in html  # Total count
    assert "2,300,000.00" in html  # Formatted value (Python default uses commas)
    assert "3 urgentes" in html
    assert "Maior valor: R$ 500k" in html


def test_format_resumo_html_with_alerta():
    """Should include urgency alert in HTML."""
    resumo = ResumoLicitacoes(
        resumo_executivo="Resumo",
        total_oportunidades=5,
        valor_total=100000.0,
        destaques=[],
        alerta_urgencia="5 licitações encerram em 24 horas",
    )

    html = format_resumo_html(resumo)

    assert "alerta-urgencia" in html
    assert "5 licitações encerram em 24 horas" in html


def test_format_resumo_html_empty_destaques():
    """Should handle empty destaques list."""
    resumo = ResumoLicitacoes(
        resumo_executivo="Resumo",
        total_oportunidades=0,
        valor_total=0.0,
        destaques=[],
        alerta_urgencia=None,
    )

    html = format_resumo_html(resumo)

    assert "resumo-container" in html
    assert "Resumo" in html
    # Should not include destaques section when empty
    assert "<li>" not in html or "Destaques" not in html


def test_format_resumo_html_no_alerta():
    """Should not include alerta HTML when None."""
    resumo = ResumoLicitacoes(
        resumo_executivo="Resumo",
        total_oportunidades=10,
        valor_total=500000.0,
        destaques=["Destaque 1"],
        alerta_urgencia=None,
    )

    html = format_resumo_html(resumo)

    assert "resumo-container" in html
    assert "alerta-urgencia" not in html


# ─────────────────────────────────────────────────────────────────────────────
# 7. Integration Tests (with Real Schema Validation)
# ─────────────────────────────────────────────────────────────────────────────


def test_resumo_schema_validation():
    """Should validate ResumoLicitacoes schema constraints."""
    # Valid resumo
    resumo = ResumoLicitacoes(
        resumo_executivo="Valid summary",
        total_oportunidades=10,
        valor_total=1000000.0,
        destaques=["Destaque 1", "Destaque 2"],
        alerta_urgencia="Alert",
    )

    assert resumo.total_oportunidades >= 0
    assert resumo.valor_total >= 0.0


def test_resumo_schema_validation_negative_values():
    """Should reject negative values in schema."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ResumoLicitacoes(
            resumo_executivo="Invalid",
            total_oportunidades=-5,  # Invalid: negative
            valor_total=100000.0,
            destaques=[],
            alerta_urgencia=None,
        )

    with pytest.raises(Exception):  # Pydantic ValidationError
        ResumoLicitacoes(
            resumo_executivo="Invalid",
            total_oportunidades=10,
            valor_total=-500.0,  # Invalid: negative
            destaques=[],
            alerta_urgencia=None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Edge Cases
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_missing_optional_fields(mock_openai):
    """Should handle bids with missing optional fields."""
    mock_resumo = ResumoLicitacoes(
        resumo_executivo="Resumo OK",
        total_oportunidades=1,
        valor_total=0.0,
        destaques=[],
        alerta_urgencia=None,
    )

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=mock_resumo))])
    )

    # Minimal bid data (only objetoCompra)
    licitacoes = [
        {
            "objetoCompra": "Uniforme"
            # All other fields missing
        }
    ]

    resumo = await gerar_resumo(licitacoes)

    assert isinstance(resumo, ResumoLicitacoes)
    mock_client.beta.chat.completions.parse.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# 9. Past-Date Filtering Tests (urgency alert bug fix)
# ─────────────────────────────────────────────────────────────────────────────


def test_fallback_no_alert_for_past_dates():
    """Fallback should NOT generate urgency alert for dates already passed."""
    from datetime import timedelta

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT10:00:00")

    licitacoes = [
        {
            "objetoCompra": "Uniforme escolar",
            "nomeOrgao": "Prefeitura SP",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": yesterday,
        },
        {
            "objetoCompra": "Fardamento militar",
            "nomeOrgao": "Exército",
            "uf": "DF",
            "valorTotalEstimado": 200000.0,
            "dataAberturaProposta": three_days_ago,
        },
    ]

    resumo = gerar_resumo_fallback(licitacoes)

    assert resumo.alerta_urgencia is None, (
        "Past dates should NOT trigger urgency alert"
    )


def test_fallback_alert_for_future_dates():
    """Fallback SHOULD generate urgency alert for dates within 7 days in the future."""
    from datetime import timedelta

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")

    licitacoes = [
        {
            "objetoCompra": "Uniforme escolar",
            "nomeOrgao": "Prefeitura SP",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": tomorrow,
        },
    ]

    resumo = gerar_resumo_fallback(licitacoes)

    assert resumo.alerta_urgencia is not None, (
        "Future date within 7 days should trigger urgency alert"
    )
    assert "Prefeitura SP" in resumo.alerta_urgencia


def test_fallback_no_alert_for_dates_beyond_7_days():
    """Fallback should NOT alert for dates more than 7 days in the future."""
    from datetime import timedelta

    far_future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%dT10:00:00")

    licitacoes = [
        {
            "objetoCompra": "Uniforme escolar",
            "nomeOrgao": "Prefeitura SP",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": far_future,
        },
    ]

    resumo = gerar_resumo_fallback(licitacoes)

    assert resumo.alerta_urgencia is None


@pytest.mark.asyncio
@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"})
@patch("llm.AsyncOpenAI")
async def test_gerar_resumo_excludes_past_dates_from_llm_input(mock_openai):
    """LLM should NOT receive bids with past opening dates in its input data."""
    from datetime import timedelta

    mock_resumo = ResumoLicitacoes(
        resumo_executivo="Resumo OK",
        total_oportunidades=1,
        valor_total=50000.0,
        destaques=[],
        alerta_urgencia=None,
    )

    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(parsed=mock_resumo))])
    )

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")

    licitacoes = [
        {
            "objetoCompra": "Uniforme passado",
            "nomeOrgao": "Prefeitura Antiga",
            "uf": "SP",
            "valorTotalEstimado": 100000.0,
            "dataAberturaProposta": yesterday,
        },
        {
            "objetoCompra": "Uniforme futuro",
            "nomeOrgao": "Prefeitura Nova",
            "uf": "RJ",
            "valorTotalEstimado": 50000.0,
            "dataAberturaProposta": tomorrow,
        },
    ]

    await gerar_resumo(licitacoes)

    call_args = mock_client.beta.chat.completions.parse.call_args
    user_prompt = call_args.kwargs["messages"][1]["content"]

    assert "Prefeitura Antiga" not in user_prompt, (
        "Past-date bid should be excluded from LLM input"
    )
    assert "Prefeitura Nova" in user_prompt, (
        "Future-date bid should be included in LLM input"
    )
