"""Unit tests for sources/transparencia_source.py — TransparenciaSource adapter."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

import httpx

from sources.transparencia_source import (
    TransparenciaSource,
    SanctionResult,
    _format_date_transparencia,
    _parse_transparencia_date,
    _generate_id,
    TRANSPARENCIA_PAGE_SIZE,
)
from sources.base import SearchQuery, NormalizedRecord
from config import RetryConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def source():
    """A TransparenciaSource with a test API key."""
    return TransparenciaSource(api_key="test-api-key-123")


@pytest.fixture
def raw_transparencia_item():
    """A raw dict as returned by the Portal da Transparencia API."""
    return {
        "numero": "00045/2026",
        "objeto": "Contratacao de servicos de vigilancia armada",
        "orgaoVinculado": {
            "nome": "Ministerio da Justica e Seguranca Publica",
            "cnpj": "00394494000148",
        },
        "uf": "DF",
        "municipio": "Brasilia",
        "valorLicitacao": 2500000.00,
        "modalidadeLicitacao": "Pregao Eletronico",
        "dataAbertura": "15/03/2026",
        "situacaoLicitacao": "Aberta",
    }


@pytest.fixture
def raw_minimal_item():
    """Minimal raw dict with very few fields."""
    return {
        "numero": "001/2026",
        "objeto": "Material de escritorio",
    }


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestFormatDateTransparencia:
    """Tests for _format_date_transparencia."""

    def test_iso_to_br(self):
        assert _format_date_transparencia("2026-03-15") == "15/03/2026"

    def test_invalid_returns_input(self):
        assert _format_date_transparencia("not-a-date") == "not-a-date"

    def test_none_returns_none(self):
        assert _format_date_transparencia(None) is None


class TestParseTransparenciaDate:
    """Tests for _parse_transparencia_date."""

    def test_br_format(self):
        dt = _parse_transparencia_date("15/03/2026")
        assert dt == datetime(2026, 3, 15)

    def test_iso_with_time(self):
        dt = _parse_transparencia_date("2026-03-15T10:30:00")
        assert dt == datetime(2026, 3, 15, 10, 30, 0)

    def test_iso_date_only(self):
        dt = _parse_transparencia_date("2026-03-15")
        assert dt == datetime(2026, 3, 15)

    def test_none_returns_none(self):
        assert _parse_transparencia_date(None) is None

    def test_empty_returns_none(self):
        assert _parse_transparencia_date("") is None

    def test_invalid_returns_none(self):
        assert _parse_transparencia_date("garbage") is None


class TestGenerateId:
    """Tests for _generate_id."""

    def test_deterministic(self):
        raw = {"numero": "001", "orgaoVinculado": {"cnpj": "123"}}
        assert _generate_id(raw) == _generate_id(raw)

    def test_different_records_different_ids(self):
        r1 = {"numero": "001", "orgaoVinculado": {"cnpj": "123"}}
        r2 = {"numero": "002", "orgaoVinculado": {"cnpj": "123"}}
        assert _generate_id(r1) != _generate_id(r2)

    def test_missing_fields(self):
        r = {}
        id_val = _generate_id(r)
        assert isinstance(id_val, str)
        assert len(id_val) == 16


# ---------------------------------------------------------------------------
# TransparenciaSource init & properties
# ---------------------------------------------------------------------------

class TestTransparenciaSourceInit:
    """Tests for TransparenciaSource initialization and properties."""

    def test_source_name(self, source):
        assert source.source_name == "transparencia"

    def test_api_key_from_param(self, source):
        assert source._api_key == "test-api-key-123"

    @patch.dict("os.environ", {"TRANSPARENCIA_API_KEY": "env-key-456"})
    def test_api_key_from_env(self):
        s = TransparenciaSource()
        assert s._api_key == "env-key-456"

    def test_default_config(self, source):
        assert source._config.timeout == 30
        assert source._config.max_retries == 3

    def test_custom_config(self):
        config = RetryConfig(max_retries=1, timeout=5)
        s = TransparenciaSource(config=config, api_key="key")
        assert s._config.max_retries == 1
        assert s._config.timeout == 5

    def test_rate_limit_from_config(self, source):
        assert source._rate_limit_rps == 3

    def test_client_has_auth_header(self, source):
        client = source._get_client()
        assert client.headers["chave-api-dados"] == "test-api-key-123"
        assert client.headers["accept"] == "application/json"


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------

class TestTransparenciaSourceNormalize:
    """Tests for TransparenciaSource.normalize() field mapping."""

    def test_produces_normalized_record(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert isinstance(record, NormalizedRecord)

    def test_source_is_transparencia(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.source == "transparencia"
        assert record.sources == ["transparencia"]

    def test_numero_licitacao(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.numero_licitacao == "00045/2026"

    def test_objeto(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.objeto == "Contratacao de servicos de vigilancia armada"

    def test_orgao_from_orgao_vinculado(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.orgao == "Ministerio da Justica e Seguranca Publica"

    def test_cnpj_from_orgao_vinculado(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.cnpj_orgao == "00394494000148"

    def test_location(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.uf == "DF"
        assert record.municipio == "Brasilia"

    def test_valor_estimado(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.valor_estimado == 2500000.00

    def test_valor_estimado_string(self, source):
        raw = {"valorLicitacao": "750000.50", "numero": "x"}
        record = source.normalize(raw)
        assert record.valor_estimado == 750000.50

    def test_valor_estimado_invalid(self, source):
        raw = {"valorLicitacao": "N/A", "numero": "x"}
        record = source.normalize(raw)
        assert record.valor_estimado is None

    def test_modalidade(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.modalidade == "Pregao Eletronico"

    def test_data_abertura(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.data_abertura == datetime(2026, 3, 15)

    def test_status(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.status == "Aberta"

    def test_raw_data_preserved(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        assert record.raw_data is raw_transparencia_item

    def test_minimal_item_no_crash(self, source, raw_minimal_item):
        record = source.normalize(raw_minimal_item)
        assert record.objeto == "Material de escritorio"
        assert record.orgao == ""
        assert record.cnpj_orgao == ""
        assert record.valor_estimado is None
        assert record.status is None

    def test_empty_dict_no_crash(self, source):
        record = source.normalize({})
        assert record.id != ""
        assert record.objeto == ""
        assert record.source == "transparencia"

    def test_id_is_deterministic(self, source, raw_transparencia_item):
        r1 = source.normalize(raw_transparencia_item)
        r2 = source.normalize(raw_transparencia_item)
        assert r1.id == r2.id

    def test_orgao_vinculado_none(self, source):
        """When orgaoVinculado is None, orgao and cnpj should default to empty."""
        raw = {"numero": "x", "orgaoVinculado": None}
        record = source.normalize(raw)
        assert record.orgao == ""
        assert record.cnpj_orgao == ""

    def test_to_legacy_dict(self, source, raw_transparencia_item):
        record = source.normalize(raw_transparencia_item)
        legacy = record.to_legacy_dict()
        assert legacy["source"] == "transparencia"
        assert legacy["valor_estimado"] == 2500000.00


# ---------------------------------------------------------------------------
# Sanctions check tests (CEIS + CNEP)
# ---------------------------------------------------------------------------

class TestTransparenciaSourceSanctions:
    """Tests for check_sanctions() against CEIS and CNEP lists."""

    @pytest.mark.asyncio
    async def test_sanction_found(self, source):
        """Scenario: CNPJ found in CEIS list — is_sanctioned=True."""
        ceis_response = AsyncMock(spec=httpx.Response)
        ceis_response.status_code = 200
        ceis_response.raise_for_status = Mock()
        ceis_response.json.return_value = [
            {
                "cnpjSancionado": "12345678000199",
                "nomeSancionado": "Empresa Impedida Ltda",
                "orgaoSancionador": "CGU",
                "dataInicioSancao": "01/01/2025",
                "dataFimSancao": "31/12/2026",
            }
        ]

        cnep_response = AsyncMock(spec=httpx.Response)
        cnep_response.status_code = 200
        cnep_response.raise_for_status = Mock()
        cnep_response.json.return_value = []

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [ceis_response, cnep_response]
        source._get_client.return_value = client_mock

        result = await source.check_sanctions("12345678000199")

        assert isinstance(result, SanctionResult)
        assert result.is_sanctioned is True
        assert len(result.sanctions) == 1
        assert result.sanctions[0]["_lista"] == "CEIS"
        assert result.sanctions[0]["nomeSancionado"] == "Empresa Impedida Ltda"

    @pytest.mark.asyncio
    async def test_sanction_clean(self, source):
        """Scenario: CNPJ not found in any sanctions list — is_sanctioned=False."""
        empty_response = AsyncMock(spec=httpx.Response)
        empty_response.status_code = 200
        empty_response.raise_for_status = Mock()
        empty_response.json.return_value = []

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = empty_response
        source._get_client.return_value = client_mock

        result = await source.check_sanctions("99999999000100")

        assert result.is_sanctioned is False
        assert result.sanctions == []

    @pytest.mark.asyncio
    async def test_sanction_in_both_lists(self, source):
        """Scenario: CNPJ found in both CEIS and CNEP."""
        ceis_response = AsyncMock(spec=httpx.Response)
        ceis_response.status_code = 200
        ceis_response.raise_for_status = Mock()
        ceis_response.json.return_value = [{"cnpjSancionado": "111", "tipo": "CEIS"}]

        cnep_response = AsyncMock(spec=httpx.Response)
        cnep_response.status_code = 200
        cnep_response.raise_for_status = Mock()
        cnep_response.json.return_value = [{"cnpjSancionado": "111", "tipo": "CNEP"}]

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = [ceis_response, cnep_response]
        source._get_client.return_value = client_mock

        result = await source.check_sanctions("111")

        assert result.is_sanctioned is True
        assert len(result.sanctions) == 2
        lists_found = {s["_lista"] for s in result.sanctions}
        assert lists_found == {"CEIS", "CNEP"}

    @pytest.mark.asyncio
    async def test_sanction_api_error_graceful(self, source):
        """Scenario: API error during sanctions check — returns clean result."""
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = httpx.ConnectError("Connection refused")
        source._get_client.return_value = client_mock
        source._config = RetryConfig(max_retries=0, timeout=5)

        result = await source.check_sanctions("12345678000199")

        assert result.is_sanctioned is False
        assert result.sanctions == []


# ---------------------------------------------------------------------------
# Fetch records tests (with mocked HTTP)
# ---------------------------------------------------------------------------

class TestTransparenciaSourceFetchRecords:
    """Tests for TransparenciaSource.fetch_records() with mocked API responses."""

    @pytest.fixture
    def mock_response_success(self):
        """Mock response with 2 items (less than page size = end of data)."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.raise_for_status = Mock()
        response.json.return_value = [
            {
                "numero": "001/2026",
                "objeto": "Uniformes para a Policia Federal",
                "orgaoVinculado": {"nome": "MJ", "cnpj": "00394494000148"},
                "uf": "SP",
                "municipio": "Sao Paulo",
                "valorLicitacao": 100000.0,
                "modalidadeLicitacao": "Pregao Eletronico",
                "dataAbertura": "10/01/2026",
                "situacaoLicitacao": "Aberta",
            },
            {
                "numero": "002/2026",
                "objeto": "Material hospitalar para UBS",
                "orgaoVinculado": {"nome": "MS", "cnpj": "00530493000171"},
                "uf": "RJ",
                "municipio": "Rio de Janeiro",
                "valorLicitacao": 250000.0,
                "modalidadeLicitacao": "Concorrencia",
                "dataAbertura": "12/01/2026",
                "situacaoLicitacao": "Fechada",
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

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31", ufs=["SP"])
        records = await source.fetch_records(query)

        assert len(records) == 2
        assert all(isinstance(r, NormalizedRecord) for r in records)
        assert records[0].objeto == "Uniformes para a Policia Federal"
        assert records[0].source == "transparencia"
        assert records[1].objeto == "Material hospitalar para UBS"

    @pytest.mark.asyncio
    async def test_fetch_empty_results(self, source, mock_response_empty):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_api_error_returns_empty(self, source):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.side_effect = httpx.ConnectError("Connection refused")
        source._get_client.return_value = client_mock
        source._config = RetryConfig(max_retries=0, timeout=5)

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_auth_failure(self, source):
        """Scenario: API returns 401 — auth failure, no retry."""
        resp_401 = AsyncMock(spec=httpx.Response)
        resp_401.status_code = 401
        resp_401.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "401 Unauthorized",
                request=httpx.Request("GET", "http://test"),
                response=resp_401,
            )
        )

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = resp_401
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
        records = await source.fetch_records(query)

        assert records == []
        # Should NOT retry on auth failure
        assert client_mock.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_passes_date_params(self, source, mock_response_empty):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-03-01", data_final="2026-03-31")
        await source.fetch_records(query)

        call_args = client_mock.get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params["dataInicial"] == "01/03/2026"
        assert params["dataFinal"] == "31/03/2026"

    @pytest.mark.asyncio
    async def test_fetch_passes_uf_param(self, source, mock_response_empty):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31", ufs=["RJ"])
        await source.fetch_records(query)

        call_args = client_mock.get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params["codigoUF"] == "RJ"

    @pytest.mark.asyncio
    async def test_fetch_multiple_ufs(self, source, mock_response_empty):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_empty
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31", ufs=["SP", "RJ"])
        await source.fetch_records(query)

        assert client_mock.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_pagination(self, source):
        """Test that pagination fetches multiple pages (1-indexed)."""
        page1_items = [
            {"numero": f"{i:03d}/2026", "objeto": f"Item {i}"}
            for i in range(TRANSPARENCIA_PAGE_SIZE)
        ]
        page2_items = [
            {"numero": "999/2026", "objeto": "Last item"}
        ]

        resp1 = AsyncMock(spec=httpx.Response)
        resp1.status_code = 200
        resp1.raise_for_status = Mock()
        resp1.json.return_value = page1_items

        resp2 = AsyncMock(spec=httpx.Response)
        resp2.status_code = 200
        resp2.raise_for_status = Mock()
        resp2.json.return_value = page2_items

        # Capture page numbers as they are called (params dict is mutated)
        captured_pages = []
        original_get = AsyncMock(side_effect=[resp1, resp2])

        async def capture_get(url, params=None):
            if params:
                captured_pages.append(params.get("pagina"))
            return await original_get(url, params=params)

        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get = capture_get
        source._get_client.return_value = client_mock

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
        records = await source.fetch_records(query)

        assert len(records) == TRANSPARENCIA_PAGE_SIZE + 1
        assert records[-1].objeto == "Last item"

        # Verify page numbers are 1-indexed
        assert captured_pages == [1, 2]

    @pytest.mark.asyncio
    async def test_fetch_with_progress_callback(self, source, mock_response_success):
        source._get_client = Mock()
        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response_success
        source._get_client.return_value = client_mock

        progress_calls = []
        def on_progress(page, total, _):
            progress_calls.append((page, total))

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
        await source.fetch_records(query, on_progress=on_progress)

        assert len(progress_calls) > 0
        assert progress_calls[0][0] == 1


# ---------------------------------------------------------------------------
# Retry / resilience tests
# ---------------------------------------------------------------------------

class TestTransparenciaSourceRetry:
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

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
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

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-01-31")
        records = await source.fetch_records(query)

        assert records == []
        assert client_mock.get.call_count == 2


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------

class TestTransparenciaSourceHealthCheck:
    """Tests for TransparenciaSource.is_healthy()."""

    @patch("sources.transparencia_source.httpx.get")
    def test_healthy_when_api_returns_200(self, mock_get, source):
        mock_get.return_value = Mock(status_code=200)
        assert source.is_healthy() is True

    @patch("sources.transparencia_source.httpx.get")
    def test_unhealthy_when_api_returns_500(self, mock_get, source):
        mock_get.return_value = Mock(status_code=500)
        assert source.is_healthy() is False

    @patch("sources.transparencia_source.httpx.get")
    def test_unhealthy_on_connection_error(self, mock_get, source):
        mock_get.side_effect = Exception("Connection refused")
        assert source.is_healthy() is False

    @patch("sources.transparencia_source.httpx.get")
    def test_health_check_sends_auth_header(self, mock_get, source):
        mock_get.return_value = Mock(status_code=200)
        source.is_healthy()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["headers"]["chave-api-dados"] == "test-api-key-123"


# ---------------------------------------------------------------------------
# Config integration tests
# ---------------------------------------------------------------------------

class TestTransparenciaConfig:
    """Tests for Transparencia entry in SOURCES_CONFIG."""

    def test_transparencia_in_sources_config(self):
        from config import SOURCES_CONFIG
        assert "transparencia" in SOURCES_CONFIG

    def test_transparencia_enabled(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["transparencia"]["enabled"] is True

    def test_transparencia_base_url(self):
        from config import SOURCES_CONFIG
        assert "portaldatransparencia" in SOURCES_CONFIG["transparencia"]["base_url"]

    def test_transparencia_rate_limit(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["transparencia"]["rate_limit_rps"] == 3

    def test_transparencia_timeout(self):
        from config import SOURCES_CONFIG
        assert SOURCES_CONFIG["transparencia"]["timeout"] == 30

    def test_transparencia_auth_configured(self):
        from config import SOURCES_CONFIG
        auth = SOURCES_CONFIG["transparencia"]["auth"]
        assert auth is not None
        assert auth["type"] == "api_key"
        assert auth["header"] == "chave-api-dados"
        assert auth["env_var"] == "TRANSPARENCIA_API_KEY"
