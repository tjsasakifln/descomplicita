"""Unit tests for sources/querido_diario_source.py — QueridoDiarioSource adapter."""

import re
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

import httpx

from sources.querido_diario_source import (
    QueridoDiarioSource,
    _generate_id,
    REGEX_NUMERO,
    REGEX_VALOR,
    REGEX_MODALIDADE,
    QUERIDO_DIARIO_PAGE_SIZE,
    UF_TO_IBGE_PREFIX,
)
from sources.base import SearchQuery, NormalizedRecord
from config import RetryConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def source():
    """A QueridoDiarioSource with default config."""
    return QueridoDiarioSource()


@pytest.fixture
def raw_gazette():
    """A raw gazette dict as returned by the Querido Diario API."""
    return {
        "territory_id": "3550308",
        "territory_name": "São Paulo",
        "date": "2026-02-15",
        "url": "https://queridodiario.ok.org.br/gazettes/3550308/2026-02-15",
        "excerpts": [
            "PREGÃO ELETRÔNICO Nº 001/2026 - Objeto: aquisição de uniformes escolares "
            "para a rede municipal de ensino. Valor estimado: R$ 250.000,00."
        ],
    }


@pytest.fixture
def raw_gazette_multi_excerpts():
    """Gazette with multiple procurement excerpts."""
    return {
        "territory_id": "3304557",
        "territory_name": "Rio de Janeiro",
        "date": "2026-02-20",
        "url": "https://queridodiario.ok.org.br/gazettes/3304557/2026-02-20",
        "excerpts": [
            "Pregão Eletrônico Nº 010/2026 aquisição de material hospitalar R$ 100.000,00",
            "Concorrência nº 002/2026 contratação de obras R$ 500.000,00",
            "Dispensa Nº 005/2026 manutenção predial R$ 45.000,00",
        ],
    }


@pytest.fixture
def raw_gazette_empty_excerpts():
    """Gazette with no excerpts."""
    return {
        "territory_id": "3550308",
        "territory_name": "São Paulo",
        "date": "2026-02-15",
        "url": "https://queridodiario.ok.org.br/gazettes/3550308/2026-02-15",
        "excerpts": [],
    }


# ---------------------------------------------------------------------------
# TestGenerateId
# ---------------------------------------------------------------------------

class TestGenerateId:
    """Tests for _generate_id."""

    def test_deterministic(self):
        gazette = {"territory_id": "3550308", "date": "2026-02-15", "url": "http://example.com"}
        assert _generate_id(gazette, 0) == _generate_id(gazette, 0)

    def test_different_excerpts_different_ids(self):
        gazette = {"territory_id": "3550308", "date": "2026-02-15", "url": "http://example.com"}
        id0 = _generate_id(gazette, 0)
        id1 = _generate_id(gazette, 1)
        assert id0 != id1

    def test_missing_fields(self):
        id_val = _generate_id({}, 0)
        assert isinstance(id_val, str)
        assert len(id_val) == 16


# ---------------------------------------------------------------------------
# TestRegexPatterns
# ---------------------------------------------------------------------------

class TestRegexPatterns:
    """Tests for the module-level regex pattern constants."""

    def test_regex_numero_pregao(self):
        text = "Pregão Eletrônico Nº 001/2026"
        match = REGEX_NUMERO.search(text)
        assert match is not None
        assert "001/2026" in match.group(0)

    def test_regex_numero_concorrencia(self):
        text = "Concorrência nº 15/2025"
        match = REGEX_NUMERO.search(text)
        assert match is not None
        assert "15/2025" in match.group(0)

    def test_regex_numero_dispensa(self):
        text = "Dispensa Nº 003/2026"
        match = REGEX_NUMERO.search(text)
        assert match is not None
        assert "003/2026" in match.group(0)

    def test_regex_valor(self):
        text = "Valor estimado: R$ 250.000,00."
        match = REGEX_VALOR.search(text)
        assert match is not None
        # The captured group should contain the numeric part
        assert "250.000,00" in match.group(0)

    def test_regex_valor_simple(self):
        text = "total de R$ 1500,00 para o exercício"
        match = REGEX_VALOR.search(text)
        assert match is not None
        assert "1500,00" in match.group(0)

    def test_regex_modalidade_pregao_eletronico(self):
        text = "Pregão Eletrônico Nº 001/2026"
        match = REGEX_MODALIDADE.search(text)
        assert match is not None
        assert "Pregão Eletrônico" in match.group(0) or "pregão eletrônico" in match.group(0).lower()

    def test_regex_modalidade_tomada(self):
        text = "Tomada de Preços nº 003/2026"
        match = REGEX_MODALIDADE.search(text)
        assert match is not None

    def test_regex_modalidade_dispensa(self):
        text = "Dispensa de licitação nº 007/2026"
        match = REGEX_MODALIDADE.search(text)
        assert match is not None

    def test_regex_no_match(self):
        text = "Nomeação de servidor público João da Silva para o cargo de assessor."
        assert REGEX_NUMERO.search(text) is None
        assert REGEX_VALOR.search(text) is None
        assert REGEX_MODALIDADE.search(text) is None


# ---------------------------------------------------------------------------
# TestQueridoDiarioSourceInit
# ---------------------------------------------------------------------------

class TestQueridoDiarioSourceInit:
    """Tests for QueridoDiarioSource initialization and properties."""

    def test_source_name(self, source):
        assert source.source_name == "querido_diario"

    def test_default_config(self, source):
        from config import SOURCES_CONFIG
        expected_timeout = SOURCES_CONFIG["querido_diario"]["timeout"]
        assert source._config.timeout == expected_timeout

    def test_custom_config(self):
        config = RetryConfig(max_retries=1, timeout=5)
        s = QueridoDiarioSource(config=config)
        assert s._config.max_retries == 1
        assert s._config.timeout == 5

    def test_rate_limit_from_config(self, source):
        assert source._rate_limit_rps == 5


# ---------------------------------------------------------------------------
# TestQueridoDiarioSourceNormalize
# ---------------------------------------------------------------------------

class TestQueridoDiarioSourceNormalize:
    """Tests for QueridoDiarioSource.normalize() field mapping."""

    def test_produces_normalized_record(self, source, raw_gazette):
        record = source.normalize(raw_gazette)
        assert isinstance(record, NormalizedRecord)

    def test_source_is_querido_diario(self, source, raw_gazette):
        record = source.normalize(raw_gazette)
        assert record.source == "querido_diario"
        assert record.sources == ["querido_diario"]

    def test_territory_name_mapped_to_municipio(self, source, raw_gazette):
        record = source.normalize(raw_gazette)
        assert record.municipio == "São Paulo"

    def test_uf_derived_from_territory_id(self, source, raw_gazette):
        # territory_id "3550308" starts with "35" -> "SP"
        record = source.normalize(raw_gazette)
        assert record.uf == "SP"

    def test_data_publicacao_parsed(self, source, raw_gazette):
        record = source.normalize(raw_gazette)
        assert record.data_publicacao == datetime(2026, 2, 15)

    def test_url_fonte_from_gazette_url(self, source, raw_gazette):
        record = source.normalize(raw_gazette)
        assert record.url_fonte == raw_gazette["url"]

    def test_objeto_from_excerpt(self, source):
        long_text = "A" * 300
        gazette = {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "date": "2026-02-15",
            "url": "http://example.com/g1",
            "excerpts": [long_text],
        }
        record = source.normalize(gazette)
        # objeto should be first 200 chars when no specific match found
        assert len(record.objeto) <= 200

    def test_empty_excerpts_handled(self, source, raw_gazette_empty_excerpts):
        record = source.normalize(raw_gazette_empty_excerpts)
        assert isinstance(record, NormalizedRecord)
        assert record.objeto == ""


# ---------------------------------------------------------------------------
# TestExtractFromGazette
# ---------------------------------------------------------------------------

class TestExtractFromGazette:
    """Tests for QueridoDiarioSource._extract_from_gazette() method."""

    def test_extracts_numero_from_excerpt(self, source):
        gazette = {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "date": "2026-02-15",
            "url": "http://example.com/g1",
            "excerpts": ["Pregão Eletrônico Nº 001/2026 aquisição de uniformes"],
        }
        records = source._extract_from_gazette(gazette)
        assert len(records) >= 1
        assert records[0].numero_licitacao == "001/2026"

    def test_extracts_valor_from_excerpt(self, source):
        gazette = {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "date": "2026-02-15",
            "url": "http://example.com/g1",
            "excerpts": ["Pregão Nº 002/2026 aquisição de materiais R$ 250.000,00"],
        }
        records = source._extract_from_gazette(gazette)
        assert len(records) >= 1
        assert records[0].valor_estimado == 250000.00

    def test_extracts_modalidade(self, source):
        gazette = {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "date": "2026-02-15",
            "url": "http://example.com/g1",
            "excerpts": ["Pregão Eletrônico Nº 001/2026 aquisição de uniformes"],
        }
        records = source._extract_from_gazette(gazette)
        assert len(records) >= 1
        assert records[0].modalidade is not None
        assert len(records[0].modalidade) > 0

    def test_multiple_excerpts_multiple_records(self, source, raw_gazette_multi_excerpts):
        records = source._extract_from_gazette(raw_gazette_multi_excerpts)
        assert len(records) == 3

    def test_no_match_still_creates_record(self, source):
        gazette = {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "date": "2026-02-15",
            "url": "http://example.com/g1",
            "excerpts": ["Texto sem termos de licitação apenas notícia municipal"],
        }
        records = source._extract_from_gazette(gazette)
        assert len(records) == 1
        # objeto should be populated with excerpt text (up to 200 chars)
        assert records[0].objeto != ""
        assert records[0].numero_licitacao is None or records[0].numero_licitacao == ""

    def test_empty_excerpts_list(self, source, raw_gazette_empty_excerpts):
        records = source._extract_from_gazette(raw_gazette_empty_excerpts)
        assert records == []


# ---------------------------------------------------------------------------
# TestUfToIbgePrefix
# ---------------------------------------------------------------------------

class TestUfToIbgePrefix:
    """Tests for the UF_TO_IBGE_PREFIX mapping dictionary."""

    def test_sp_prefix(self):
        assert UF_TO_IBGE_PREFIX["SP"] == "35"

    def test_rj_prefix(self):
        assert UF_TO_IBGE_PREFIX["RJ"] == "33"

    def test_all_states_covered(self):
        all_ufs = {
            "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
            "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
            "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
        }
        for uf in all_ufs:
            assert uf in UF_TO_IBGE_PREFIX, f"Missing UF: {uf}"
        assert len(UF_TO_IBGE_PREFIX) == 27

    def test_uf_derivation_from_territory(self, source):
        # territory_id "3550308" starts with prefix "35" which maps to "SP"
        gazette = {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "date": "2026-02-15",
            "url": "http://example.com",
            "excerpts": [],
        }
        record = source.normalize(gazette)
        assert record.uf == "SP"


# ---------------------------------------------------------------------------
# TestQueridoDiarioSourceFetchRecords
# ---------------------------------------------------------------------------

class TestQueridoDiarioSourceFetchRecords:
    """Tests for QueridoDiarioSource.fetch_records() with mocked API responses."""

    @pytest.fixture
    def mock_response_success(self):
        """Mock response with 2 gazettes (less than page size = end of data)."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.raise_for_status = Mock()
        response.json.return_value = {
            "total_gazettes": 2,
            "gazettes": [
                {
                    "territory_id": "3550308",
                    "territory_name": "São Paulo",
                    "date": "2026-02-15",
                    "url": "https://example.com/gazette1",
                    "excerpts": [
                        "PREGÃO ELETRÔNICO Nº 001/2026 aquisição de uniformes "
                        "escolares R$ 250.000,00"
                    ],
                },
                {
                    "territory_id": "3550308",
                    "territory_name": "São Paulo",
                    "date": "2026-02-16",
                    "url": "https://example.com/gazette2",
                    "excerpts": [
                        "Dispensa Nº 012/2026 manutenção predial R$ 45.000,00"
                    ],
                },
            ],
        }
        return response

    @pytest.fixture
    def mock_response_empty(self):
        """Mock response with empty results."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.raise_for_status = Mock()
        response.json.return_value = {"total_gazettes": 0, "gazettes": []}
        return response

    @pytest.mark.asyncio
    async def test_fetch_success_returns_records(self, source, mock_response_success):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_success
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28", ufs=["SP"])
        records = await source.fetch_records(query)

        assert len(records) >= 1
        assert all(isinstance(r, NormalizedRecord) for r in records)
        assert all(r.source == "querido_diario" for r in records)

    @pytest.mark.asyncio
    async def test_fetch_empty_results(self, source, mock_response_empty):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_api_error_returns_empty(self, source):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = httpx.ConnectError("Connection refused")
        source._get_client.return_value = client_mock
        source._config = RetryConfig(max_retries=0, timeout=5)

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_filters_by_uf(self, source):
        """Query with ufs=["SP"] should only return records with territory_id starting with "35"."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.raise_for_status = Mock()
        response.json.return_value = {
            "total_gazettes": 2,
            "gazettes": [
                {
                    "territory_id": "3550308",   # SP prefix "35"
                    "territory_name": "São Paulo",
                    "date": "2026-02-15",
                    "url": "https://example.com/sp",
                    "excerpts": ["Pregão Nº 001/2026 compras"],
                },
                {
                    "territory_id": "3304557",   # RJ prefix "33"
                    "territory_name": "Rio de Janeiro",
                    "date": "2026-02-15",
                    "url": "https://example.com/rj",
                    "excerpts": ["Pregão Nº 002/2026 compras"],
                },
            ],
        }

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = response
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28", ufs=["SP"])
        records = await source.fetch_records(query)

        for record in records:
            assert record.uf == "SP"

    @pytest.mark.asyncio
    async def test_fetch_uf_without_coverage_returns_empty(self, source, mock_response_empty):
        """Query with an unknown UF code should return empty list."""
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28", ufs=["XX"])
        records = await source.fetch_records(query)

        assert records == []


# ---------------------------------------------------------------------------
# TestQueridoDiarioSourceRetry
# ---------------------------------------------------------------------------

class TestQueridoDiarioSourceRetry:
    """Tests for retry and rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_500(self, source):
        source._config = RetryConfig(max_retries=2, timeout=5, base_delay=0.01, max_delay=0.05)

        resp_500 = AsyncMock(spec=httpx.Response)
        resp_500.status_code = 500
        resp_500.headers = {"content-type": "application/json"}
        resp_500.raise_for_status = Mock()

        resp_ok = AsyncMock(spec=httpx.Response)
        resp_ok.status_code = 200
        resp_ok.headers = {"content-type": "application/json"}
        resp_ok.raise_for_status = Mock()
        resp_ok.json.return_value = {
            "total_gazettes": 1,
            "gazettes": [
                {
                    "territory_id": "3550308",
                    "territory_name": "São Paulo",
                    "date": "2026-02-15",
                    "url": "https://example.com/g1",
                    "excerpts": ["Pregão Nº 001/2026 teste"],
                }
            ],
        }

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [resp_500, resp_ok]
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")
        records = await source.fetch_records(query)

        assert len(records) >= 1
        assert client_mock.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, source):
        source._config = RetryConfig(max_retries=1, timeout=5, base_delay=0.01, max_delay=0.05)

        resp_ok = AsyncMock(spec=httpx.Response)
        resp_ok.status_code = 200
        resp_ok.headers = {"content-type": "application/json"}
        resp_ok.raise_for_status = Mock()
        resp_ok.json.return_value = {"total_gazettes": 0, "gazettes": []}

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [httpx.TimeoutException("timeout"), resp_ok]
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")
        records = await source.fetch_records(query)

        assert records == []
        assert client_mock.get.call_count == 2


# ---------------------------------------------------------------------------
# TestQueridoDiarioSourceHealthCheck
# ---------------------------------------------------------------------------

class TestQueridoDiarioSourceHealthCheck:
    """Tests for QueridoDiarioSource.is_healthy()."""

    @patch("sources.querido_diario_source.httpx.get")
    def test_healthy_when_api_returns_200_json(self, mock_get, source):
        mock_get.return_value = Mock(
            status_code=200,
            headers={"content-type": "application/json"},
        )
        assert source.is_healthy() is True

    @patch("sources.querido_diario_source.httpx.get")
    def test_unhealthy_when_api_returns_html(self, mock_get, source):
        mock_get.return_value = Mock(
            status_code=200,
            headers={"content-type": "text/html; charset=UTF-8"},
        )
        assert source.is_healthy() is False

    @patch("sources.querido_diario_source.httpx.get")
    def test_unhealthy_when_api_returns_500(self, mock_get, source):
        mock_get.return_value = Mock(
            status_code=500,
            headers={"content-type": "application/json"},
        )
        assert source.is_healthy() is False

    @patch("sources.querido_diario_source.httpx.get")
    def test_unhealthy_on_connection_error(self, mock_get, source):
        mock_get.side_effect = Exception("Connection refused")
        assert source.is_healthy() is False


# ---------------------------------------------------------------------------
# TestQueridoDiarioConfig
# ---------------------------------------------------------------------------

class TestQueridoDiarioConfig:
    """Tests for querido_diario entry in SOURCES_CONFIG."""

    def test_querido_diario_in_sources_config(self):
        from config import SOURCES_CONFIG
        assert "querido_diario" in SOURCES_CONFIG

    def test_querido_diario_disabled(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["querido_diario"]["enabled"] is False

    def test_querido_diario_base_url(self):
        from config import SOURCES_CONFIG
        assert "queridodiario" in SOURCES_CONFIG["querido_diario"]["base_url"]

    def test_querido_diario_rate_limit(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["querido_diario"]["rate_limit_rps"] == 5

    def test_querido_diario_timeout(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["querido_diario"]["timeout"] == 60

    def test_querido_diario_no_auth(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["querido_diario"]["auth"] is None


# ---------------------------------------------------------------------------
# TestParsingRealExamples
# ---------------------------------------------------------------------------

class TestParsingRealExamples:
    """Tests using realistic gazette text snippets from Brazilian municipal gazettes."""

    def test_parse_real_pregao_excerpt(self, source):
        excerpt = (
            "SECRETARIA MUNICIPAL DE EDUCAÇÃO - PREGÃO ELETRÔNICO Nº 045/2026 - "
            "Objeto: aquisição de uniformes escolares para a rede municipal de ensino. "
            "Valor estimado: R$ 1.500.000,00. Data de abertura: 20/03/2026."
        )
        gazette = {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "date": "2026-03-01",
            "url": "https://queridodiario.ok.org.br/gazettes/3550308/2026-03-01",
            "excerpts": [excerpt],
        }
        records = source._extract_from_gazette(gazette)
        assert len(records) == 1
        record = records[0]
        assert "045/2026" in (record.numero_licitacao or "")
        assert record.valor_estimado == 1500000.00
        assert record.modalidade is not None
        assert "Pregão" in record.modalidade or "pregão" in record.modalidade.lower()
        assert record.uf == "SP"
        assert record.municipio == "São Paulo"

    def test_parse_real_dispensa_excerpt(self, source):
        excerpt = (
            "DISPENSA Nº 012/2026 - Contratação emergencial de serviços de manutenção "
            "predial. Valor: R$ 45.000,00"
        )
        gazette = {
            "territory_id": "3304557",
            "territory_name": "Rio de Janeiro",
            "date": "2026-03-01",
            "url": "https://queridodiario.ok.org.br/gazettes/3304557/2026-03-01",
            "excerpts": [excerpt],
        }
        records = source._extract_from_gazette(gazette)
        assert len(records) == 1
        record = records[0]
        assert "012/2026" in (record.numero_licitacao or "")
        assert record.valor_estimado == 45000.00
        assert record.uf == "RJ"
        assert record.municipio == "Rio de Janeiro"

    def test_parse_gazette_without_procurement(self, source):
        excerpt = (
            "Nomeação de servidor público João da Silva para o cargo de assessor "
            "especial da Secretaria Municipal de Administração, conforme portaria nº 123."
        )
        gazette = {
            "territory_id": "3550308",
            "territory_name": "São Paulo",
            "date": "2026-03-01",
            "url": "https://queridodiario.ok.org.br/gazettes/3550308/2026-03-01",
            "excerpts": [excerpt],
        }
        records = source._extract_from_gazette(gazette)
        # Should still produce a record but without structured procurement fields
        assert len(records) == 1
        record = records[0]
        # objeto should be a truncated version of the excerpt
        assert record.objeto != ""
        assert len(record.objeto) <= 200
        # No valor extracted
        assert record.valor_estimado is None


# ---------------------------------------------------------------------------
# TestDefensiveContentTypeParsing (SR-001.4)
# ---------------------------------------------------------------------------

class TestDefensiveContentTypeParsing:
    """Tests for content-type validation before JSON parsing (SR-001.4)."""

    @pytest.mark.asyncio
    async def test_html_response_returns_empty_list(self, source):
        """When API returns HTML instead of JSON, fetch_records returns [] gracefully."""
        html_response = AsyncMock(spec=httpx.Response)
        html_response.status_code = 200
        html_response.headers = {"content-type": "text/html; charset=UTF-8"}
        html_response.text = "<!DOCTYPE html><html><head><title>Querido Diario</title></head></html>"
        html_response.raise_for_status = Mock()

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = html_response
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_html_response_logs_body_preview(self, source, caplog):
        """When API returns HTML, log includes first 200 chars of body for debug."""
        html_body = "<html>" + "x" * 300 + "</html>"
        html_response = AsyncMock(spec=httpx.Response)
        html_response.status_code = 200
        html_response.headers = {"content-type": "text/html; charset=UTF-8"}
        html_response.text = html_body
        html_response.raise_for_status = Mock()

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = html_response
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")

        import logging
        with caplog.at_level(logging.ERROR):
            records = await source.fetch_records(query)

        assert records == []
        assert any("unexpected content-type" in msg.lower() for msg in caplog.messages)

    @pytest.mark.asyncio
    async def test_empty_body_returns_empty_list(self, source):
        """When API returns empty body, fetch_records returns [] gracefully."""
        empty_response = AsyncMock(spec=httpx.Response)
        empty_response.status_code = 200
        empty_response.headers = {"content-type": "text/plain"}
        empty_response.text = ""
        empty_response.raise_for_status = Mock()

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = empty_response
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_json_content_type_proceeds_normally(self, source):
        """When API returns proper JSON content-type, parsing proceeds normally."""
        json_response = AsyncMock(spec=httpx.Response)
        json_response.status_code = 200
        json_response.headers = {"content-type": "application/json; charset=utf-8"}
        json_response.raise_for_status = Mock()
        json_response.json.return_value = {
            "total_gazettes": 1,
            "gazettes": [
                {
                    "territory_id": "3550308",
                    "territory_name": "São Paulo",
                    "date": "2026-02-15",
                    "url": "https://example.com/g1",
                    "excerpts": ["Pregão Nº 001/2026 teste"],
                }
            ],
        }

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = json_response
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")
        records = await source.fetch_records(query)

        assert len(records) >= 1
        assert records[0].source == "querido_diario"

    @pytest.mark.asyncio
    async def test_missing_content_type_header_returns_empty(self, source):
        """When response has no content-type header, treat as invalid."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {}
        response.text = "some random text"
        response.raise_for_status = Mock()

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = response
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-02-01", data_final="2026-02-28")
        records = await source.fetch_records(query)

        assert records == []
