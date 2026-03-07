"""Unit tests for sources/comprasgov_source.py — ComprasGovSource adapter."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

import httpx

from sources.comprasgov_source import (
    ComprasGovSource,
    _format_date_comprasgov,
    _parse_comprasgov_date,
    _generate_id,
    MODALIDADES_COMPRASGOV,
    MODALIDADE_TO_PNCP,
    COMPRASGOV_PAGE_SIZE,
)
from sources.base import SearchQuery, NormalizedRecord
from config import RetryConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def source():
    """A ComprasGovSource with default config."""
    return ComprasGovSource()


@pytest.fixture
def raw_comprasgov_item():
    """A raw dict as returned by the Compras.gov.br API."""
    return {
        "numero": "00012/2025",
        "objeto": "Aquisição de uniformes para a Polícia Federal",
        "orgao": "Ministério da Justiça e Segurança Pública",
        "cnpj": "00394494000148",
        "uasg": "200331",
        "uf": "DF",
        "municipio": "Brasília",
        "valor_estimado": 1250000.00,
        "modalidade_licitacao": 5,
        "data_publicacao": "15/01/2025",
        "data_abertura": "15/02/2025",
        "situacao_licitacao": "Aberto",
    }


@pytest.fixture
def raw_minimal_item():
    """Minimal raw dict with very few fields."""
    return {
        "numero": "001/2024",
        "objeto": "Material de escritório",
    }


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestFormatDateComprasGov:
    """Tests for _format_date_comprasgov."""

    def test_iso_to_br(self):
        assert _format_date_comprasgov("2025-01-15") == "15/01/2025"

    def test_iso_to_br_end_of_year(self):
        assert _format_date_comprasgov("2025-12-31") == "31/12/2025"

    def test_invalid_returns_input(self):
        assert _format_date_comprasgov("not-a-date") == "not-a-date"

    def test_none_returns_none(self):
        assert _format_date_comprasgov(None) is None


class TestParseComprasGovDate:
    """Tests for _parse_comprasgov_date."""

    def test_br_format(self):
        dt = _parse_comprasgov_date("15/01/2025")
        assert dt == datetime(2025, 1, 15)

    def test_iso_with_time(self):
        dt = _parse_comprasgov_date("2025-01-15T10:30:00")
        assert dt == datetime(2025, 1, 15, 10, 30, 0)

    def test_iso_date_only(self):
        dt = _parse_comprasgov_date("2025-01-15")
        assert dt == datetime(2025, 1, 15)

    def test_none_returns_none(self):
        assert _parse_comprasgov_date(None) is None

    def test_empty_returns_none(self):
        assert _parse_comprasgov_date("") is None

    def test_invalid_returns_none(self):
        assert _parse_comprasgov_date("garbage") is None


class TestGenerateId:
    """Tests for _generate_id."""

    def test_deterministic(self):
        raw = {"numero": "001", "uasg": "123"}
        assert _generate_id(raw) == _generate_id(raw)

    def test_different_records_different_ids(self):
        r1 = {"numero": "001", "uasg": "123"}
        r2 = {"numero": "002", "uasg": "123"}
        assert _generate_id(r1) != _generate_id(r2)

    def test_missing_fields(self):
        r = {}
        id_val = _generate_id(r)
        assert isinstance(id_val, str)
        assert len(id_val) == 16


# ---------------------------------------------------------------------------
# ComprasGovSource init & properties
# ---------------------------------------------------------------------------

class TestComprasGovSourceInit:
    """Tests for ComprasGovSource initialization and properties."""

    def test_source_name(self, source):
        assert source.source_name == "comprasgov"

    def test_default_config(self, source):
        assert source._config.timeout == 20
        assert source._config.max_retries == 3

    def test_custom_config(self):
        config = RetryConfig(max_retries=1, timeout=5)
        s = ComprasGovSource(config=config)
        assert s._config.max_retries == 1
        assert s._config.timeout == 5

    def test_rate_limit_from_config(self, source):
        assert source._rate_limit_rps == 5


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------

class TestComprasGovSourceNormalize:
    """Tests for ComprasGovSource.normalize() field mapping."""

    def test_produces_normalized_record(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert isinstance(record, NormalizedRecord)

    def test_source_is_comprasgov(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.source == "comprasgov"
        assert record.sources == ["comprasgov"]

    def test_numero_licitacao(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.numero_licitacao == "00012/2025"

    def test_objeto(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.objeto == "Aquisição de uniformes para a Polícia Federal"

    def test_orgao(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.orgao == "Ministério da Justiça e Segurança Pública"

    def test_cnpj(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.cnpj_orgao == "00394494000148"

    def test_location(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.uf == "DF"
        assert record.municipio == "Brasília"

    def test_valor_estimado(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.valor_estimado == 1250000.00

    def test_valor_estimado_string(self, source):
        raw = {"valor_estimado": "500000.50", "numero": "x"}
        record = source.normalize(raw)
        assert record.valor_estimado == 500000.50

    def test_valor_estimado_invalid(self, source):
        raw = {"valor_estimado": "N/A", "numero": "x"}
        record = source.normalize(raw)
        assert record.valor_estimado is None

    def test_modalidade_mapping(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.modalidade == "Pregão"
        # Pregão (5) maps to PNCP code 6
        assert record.modalidade_codigo == 6

    def test_modalidade_unknown_code(self, source):
        raw = {"modalidade_licitacao": 99, "numero": "x"}
        record = source.normalize(raw)
        assert record.modalidade == "Modalidade 99"

    def test_modalidade_none(self, source):
        raw = {"numero": "x"}
        record = source.normalize(raw)
        assert record.modalidade == ""
        assert record.modalidade_codigo is None

    def test_data_publicacao(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.data_publicacao == datetime(2025, 1, 15)

    def test_data_abertura(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.data_abertura == datetime(2025, 2, 15)

    def test_status(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.status == "Aberto"

    def test_url_fonte_generated(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.url_fonte == (
            "https://compras.dados.gov.br/licitacoes/doc/licitacao/200331/00012/2025"
        )

    def test_url_fonte_missing_fields(self, source, raw_minimal_item):
        record = source.normalize(raw_minimal_item)
        assert record.url_fonte is None

    def test_url_edital_always_none(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.url_edital is None

    def test_raw_data_preserved(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        assert record.raw_data is raw_comprasgov_item
        assert record.raw_data["uasg"] == "200331"

    def test_minimal_item_no_crash(self, source, raw_minimal_item):
        record = source.normalize(raw_minimal_item)
        assert record.objeto == "Material de escritório"
        assert record.orgao == ""
        assert record.valor_estimado is None
        assert record.status is None

    def test_empty_dict_no_crash(self, source):
        record = source.normalize({})
        assert record.id != ""
        assert record.objeto == ""
        assert record.source == "comprasgov"

    def test_id_is_deterministic(self, source, raw_comprasgov_item):
        r1 = source.normalize(raw_comprasgov_item)
        r2 = source.normalize(raw_comprasgov_item)
        assert r1.id == r2.id

    def test_to_legacy_dict_contains_normalized_fields(self, source, raw_comprasgov_item):
        record = source.normalize(raw_comprasgov_item)
        legacy = record.to_legacy_dict()
        assert legacy["objeto"] == raw_comprasgov_item["objeto"]
        assert legacy["valor_estimado"] == 1250000.00
        assert legacy["source"] == "comprasgov"
        assert legacy["uasg"] == "200331"


# ---------------------------------------------------------------------------
# Fetch records tests (with mocked HTTP)
# ---------------------------------------------------------------------------

class TestComprasGovSourceFetchRecords:
    """Tests for ComprasGovSource.fetch_records() with mocked API responses."""

    @pytest.fixture
    def mock_response_success(self):
        """Mock response with 2 items (less than page size = end of data)."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.raise_for_status = Mock()
        response.json.return_value = [
            {
                "numero": "001/2025",
                "objeto": "Uniformes escolares",
                "orgao": "MEC",
                "uf": "SP",
                "municipio": "São Paulo",
                "valor_estimado": 100000.0,
                "modalidade_licitacao": 5,
                "data_publicacao": "10/01/2025",
                "situacao_licitacao": "Aberto",
                "uasg": "150001",
            },
            {
                "numero": "002/2025",
                "objeto": "Material hospitalar",
                "orgao": "MS",
                "uf": "RJ",
                "municipio": "Rio de Janeiro",
                "valor_estimado": 250000.0,
                "modalidade_licitacao": 12,
                "data_publicacao": "12/01/2025",
                "situacao_licitacao": "Fechado",
                "uasg": "250005",
            },
        ]
        return response

    @pytest.fixture
    def mock_response_empty(self):
        """Mock response with empty results."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.raise_for_status = Mock()
        response.json.return_value = []
        return response

    @pytest.mark.asyncio
    async def test_fetch_success_returns_records(self, source, mock_response_success):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_success
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31", ufs=["SP"])
        records = await source.fetch_records(query)

        assert len(records) == 2
        assert all(isinstance(r, NormalizedRecord) for r in records)
        assert records[0].objeto == "Uniformes escolares"
        assert records[0].source == "comprasgov"
        assert records[1].objeto == "Material hospitalar"

    @pytest.mark.asyncio
    async def test_fetch_empty_results(self, source, mock_response_empty):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_api_error_returns_empty(self, source):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = httpx.ConnectError("Connection refused")
        source._get_client.return_value = client_mock
        source._config = RetryConfig(max_retries=0, timeout=5)

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_pagination(self, source):
        """Test that pagination fetches multiple pages."""
        page1_items = [
            {"numero": f"{i:03d}/2025", "objeto": f"Item {i}", "uasg": "100"}
            for i in range(COMPRASGOV_PAGE_SIZE)
        ]
        page2_items = [
            {"numero": "999/2025", "objeto": "Last item", "uasg": "100"}
        ]

        resp1 = AsyncMock(spec=httpx.Response)
        resp1.status_code = 200
        resp1.raise_for_status = Mock()
        resp1.json.return_value = page1_items

        resp2 = AsyncMock(spec=httpx.Response)
        resp2.status_code = 200
        resp2.raise_for_status = Mock()
        resp2.json.return_value = page2_items

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [resp1, resp2]
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        records = await source.fetch_records(query)

        assert len(records) == COMPRASGOV_PAGE_SIZE + 1
        assert records[-1].objeto == "Last item"

    @pytest.mark.asyncio
    async def test_fetch_passes_date_params(self, source, mock_response_empty):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2025-03-01", data_final="2025-03-31")
        await source.fetch_records(query)

        call_args = client_mock.get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params["data_publicacao_min"] == "01/03/2025"
        assert params["data_publicacao_max"] == "31/03/2025"

    @pytest.mark.asyncio
    async def test_fetch_multiple_ufs(self, source, mock_response_empty):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31", ufs=["SP", "RJ"])
        await source.fetch_records(query)

        # Should make separate requests for each UF
        assert client_mock.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_with_progress_callback(self, source, mock_response_success):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_success
        source._get_client.return_value = client_mock

        progress_calls = []
        def on_progress(page, total, _):
            progress_calls.append((page, total))

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        await source.fetch_records(query, on_progress=on_progress)

        assert len(progress_calls) > 0
        assert progress_calls[0][0] == 1  # page 1


# ---------------------------------------------------------------------------
# Retry / resilience tests
# ---------------------------------------------------------------------------

class TestComprasGovSourceRetry:
    """Tests for retry and rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_500(self, source):
        source._config = RetryConfig(max_retries=2, timeout=5, base_delay=0.01, max_delay=0.05)

        resp_500 = AsyncMock(spec=httpx.Response)
        resp_500.status_code = 500
        resp_500.raise_for_status = Mock()

        resp_ok = AsyncMock(spec=httpx.Response)
        resp_ok.status_code = 200
        resp_ok.raise_for_status = Mock()
        resp_ok.json.return_value = [{"numero": "001", "objeto": "Test"}]

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [resp_500, resp_ok]
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        records = await source.fetch_records(query)

        assert len(records) == 1
        assert client_mock.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, source):
        source._config = RetryConfig(max_retries=1, timeout=5, base_delay=0.01, max_delay=0.05)

        resp_ok = AsyncMock(spec=httpx.Response)
        resp_ok.status_code = 200
        resp_ok.raise_for_status = Mock()
        resp_ok.json.return_value = []

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [httpx.TimeoutException("timeout"), resp_ok]
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        records = await source.fetch_records(query)

        assert records == []
        assert client_mock.get.call_count == 2


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------

class TestComprasGovSourceHealthCheck:
    """Tests for ComprasGovSource.is_healthy()."""

    @patch("sources.comprasgov_source.httpx.get")
    def test_healthy_when_api_returns_200(self, mock_get, source):
        mock_get.return_value = Mock(status_code=200)
        assert source.is_healthy() is True

    @patch("sources.comprasgov_source.httpx.get")
    def test_unhealthy_when_api_returns_500(self, mock_get, source):
        mock_get.return_value = Mock(status_code=500)
        assert source.is_healthy() is False

    @patch("sources.comprasgov_source.httpx.get")
    def test_unhealthy_on_connection_error(self, mock_get, source):
        mock_get.side_effect = Exception("Connection refused")
        assert source.is_healthy() is False


# ---------------------------------------------------------------------------
# Config integration tests
# ---------------------------------------------------------------------------

class TestComprasGovConfig:
    """Tests for Compras.gov.br entry in SOURCES_CONFIG."""

    def test_comprasgov_in_sources_config(self):
        from config import SOURCES_CONFIG
        assert "comprasgov" in SOURCES_CONFIG

    def test_comprasgov_enabled(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["comprasgov"]["enabled"] is True

    def test_comprasgov_base_url(self):
        from config import SOURCES_CONFIG
        assert "compras" in SOURCES_CONFIG["comprasgov"]["base_url"]

    def test_comprasgov_rate_limit(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["comprasgov"]["rate_limit_rps"] == 5

    def test_comprasgov_timeout(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["comprasgov"]["timeout"] == 20

    def test_comprasgov_no_auth(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["comprasgov"]["auth"] is None


# ---------------------------------------------------------------------------
# Modalidade mapping tests
# ---------------------------------------------------------------------------

class TestModalidadeMapping:
    """Tests for modalidade code mappings."""

    def test_pregao_maps_to_pncp_6(self):
        assert MODALIDADE_TO_PNCP[5] == 6

    def test_dispensa_maps_to_pncp_8(self):
        assert MODALIDADE_TO_PNCP[6] == 8

    def test_concorrencia_maps_to_pncp_4(self):
        assert MODALIDADE_TO_PNCP[3] == 4

    def test_convite_has_no_pncp_equivalent(self):
        assert MODALIDADE_TO_PNCP[1] is None

    def test_all_modalidades_have_names(self):
        for code in MODALIDADES_COMPRASGOV:
            assert isinstance(MODALIDADES_COMPRASGOV[code], str)
            assert len(MODALIDADES_COMPRASGOV[code]) > 0
