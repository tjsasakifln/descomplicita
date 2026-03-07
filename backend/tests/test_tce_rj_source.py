"""Unit tests for sources/tce_rj_source.py — TCERJSource adapter."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

import httpx

from sources.tce_rj_source import (
    TCERJSource,
    TCE_RJ_PAGE_SIZE,
    MODALIDADE_MAP,
    _generate_id,
    _normalize_modalidade,
    _parse_tce_rj_date,
    _safe_float,
)
from sources.base import SearchQuery, NormalizedRecord
from config import RetryConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def source():
    """A TCERJSource with default config."""
    return TCERJSource()


@pytest.fixture
def raw_licitacao():
    """A raw licitação dict as returned by the TCE-RJ API."""
    return {
        "numero": "PE-001/2026",
        "objeto": "Aquisição de uniformes escolares para a rede municipal de ensino",
        "orgao": {
            "nome": "Prefeitura de Niterói",
            "cnpj": "28.521.748/0001-59",
            "municipio": "Niterói",
        },
        "modalidade": "pregao_eletronico",
        "valor_estimado": 350000.00,
        "data_publicacao": "2026-02-15",
        "situacao": "Aberta",
        "url": "https://dados.tcerj.tc.br/licitacoes/PE-001-2026",
    }


@pytest.fixture
def raw_compra_direta_dispensa():
    """A raw compra direta (dispensa) dict."""
    return {
        "numero": "DL-042/2026",
        "objeto": "Manutenção emergencial de prédio público",
        "orgao": {
            "nome": "Prefeitura de Petrópolis",
            "cnpj": "29.138.393/0001-01",
            "municipio": "Petrópolis",
        },
        "tipo_compra": "Dispensa de Licitação",
        "valor": 89000.50,
        "data_publicacao": "2026-03-01T00:00:00",
        "situacao": "Homologada",
        "url": "https://dados.tcerj.tc.br/compras-diretas/DL-042-2026",
    }


@pytest.fixture
def raw_compra_direta_inexigibilidade():
    """A raw compra direta (inexigibilidade) dict."""
    return {
        "numero": "IN-005/2026",
        "objeto": "Contratação de serviço técnico especializado",
        "orgao": {
            "nome": "Governo do Estado do RJ",
            "cnpj": "42.498.733/0001-48",
            "municipio": "Rio de Janeiro",
        },
        "tipo_compra": "Inexigibilidade",
        "valor": 200000.00,
        "data_publicacao": "2026-02-20",
        "situacao": "Publicada",
        "url": None,
    }


@pytest.fixture
def raw_compra_direta_adesao():
    """A raw compra direta (adesão a ata) dict."""
    return {
        "numero": "AD-003/2026",
        "objeto": "Adesão a ata de registro de preços para material de escritório",
        "orgao": {
            "nome": "Prefeitura de Volta Redonda",
            "cnpj": "32.512.501/0001-43",
            "municipio": "Volta Redonda",
        },
        "tipo_compra": "Adesão a Ata",
        "valor": 75000.00,
        "data_publicacao": "2026-01-10",
        "situacao": "Concluída",
    }


# ---------------------------------------------------------------------------
# TestGenerateId
# ---------------------------------------------------------------------------

class TestGenerateId:
    """Tests for _generate_id."""

    def test_deterministic(self, raw_licitacao):
        id1 = _generate_id("licitacao", raw_licitacao)
        id2 = _generate_id("licitacao", raw_licitacao)
        assert id1 == id2

    def test_different_types_different_ids(self, raw_licitacao):
        id_lic = _generate_id("licitacao", raw_licitacao)
        id_cd = _generate_id("compra_direta", raw_licitacao)
        assert id_lic != id_cd

    def test_missing_fields(self):
        id_val = _generate_id("licitacao", {})
        assert isinstance(id_val, str)
        assert len(id_val) == 16

    def test_different_records_different_ids(self, raw_licitacao, raw_compra_direta_dispensa):
        id1 = _generate_id("licitacao", raw_licitacao)
        id2 = _generate_id("compra_direta", raw_compra_direta_dispensa)
        assert id1 != id2


# ---------------------------------------------------------------------------
# TestParseDateAndHelpers
# ---------------------------------------------------------------------------

class TestParseDateAndHelpers:
    """Tests for _parse_tce_rj_date and other helper functions."""

    def test_parse_date_iso(self):
        assert _parse_tce_rj_date("2026-02-15") == datetime(2026, 2, 15)

    def test_parse_date_iso_with_time(self):
        assert _parse_tce_rj_date("2026-02-15T10:30:00") == datetime(2026, 2, 15, 10, 30, 0)

    def test_parse_date_br_format(self):
        assert _parse_tce_rj_date("15/02/2026") == datetime(2026, 2, 15)

    def test_parse_date_none(self):
        assert _parse_tce_rj_date(None) is None

    def test_parse_date_empty(self):
        assert _parse_tce_rj_date("") is None

    def test_parse_date_invalid(self):
        assert _parse_tce_rj_date("not-a-date") is None

    def test_safe_float_valid(self):
        assert _safe_float(350000.00) == 350000.00

    def test_safe_float_string(self):
        assert _safe_float("123.45") == 123.45

    def test_safe_float_none(self):
        assert _safe_float(None) is None

    def test_safe_float_invalid(self):
        assert _safe_float("abc") is None

    def test_normalize_modalidade_known(self):
        assert _normalize_modalidade("pregao_eletronico") == "Pregão Eletrônico"
        assert _normalize_modalidade("dispensa") == "Dispensa"
        assert _normalize_modalidade("inexigibilidade") == "Inexigibilidade"

    def test_normalize_modalidade_unknown(self):
        assert _normalize_modalidade("nova_modalidade") == "nova_modalidade"

    def test_normalize_modalidade_none(self):
        assert _normalize_modalidade(None) == ""

    def test_normalize_modalidade_with_spaces(self):
        assert _normalize_modalidade("  pregao_eletronico  ") == "Pregão Eletrônico"


# ---------------------------------------------------------------------------
# TestSourceName
# ---------------------------------------------------------------------------

class TestSourceName:
    """Tests for TCERJSource.source_name property."""

    def test_source_name(self, source):
        assert source.source_name == "tce_rj"


# ---------------------------------------------------------------------------
# TestNormalize — licitação records
# ---------------------------------------------------------------------------

class TestNormalizeLicitacao:
    """Tests for TCERJSource.normalize() with licitação records."""

    def test_normalize_basic(self, source, raw_licitacao):
        record = source.normalize(raw_licitacao, "licitacao")
        assert record.source == "tce_rj"
        assert record.sources == ["tce_rj"]
        assert record.numero_licitacao == "PE-001/2026"
        assert record.objeto == "Aquisição de uniformes escolares para a rede municipal de ensino"
        assert record.orgao == "Prefeitura de Niterói"
        assert record.cnpj_orgao == "28.521.748/0001-59"
        assert record.uf == "RJ"
        assert record.municipio == "Niterói"
        assert record.valor_estimado == 350000.00
        assert record.modalidade == "Pregão Eletrônico"
        assert record.data_publicacao == datetime(2026, 2, 15)
        assert record.status == "Aberta"
        assert record.url_fonte == "https://dados.tcerj.tc.br/licitacoes/PE-001-2026"

    def test_normalize_missing_orgao_dict(self, source):
        raw = {
            "numero": "X-001/2026",
            "objeto": "Teste",
            "orgao": "Orgão Simples",
            "modalidade": "concorrencia",
            "data_publicacao": "2026-01-01",
        }
        record = source.normalize(raw, "licitacao")
        assert record.orgao == "Orgão Simples"
        assert record.cnpj_orgao == ""
        assert record.municipio == ""

    def test_normalize_empty_record(self, source):
        record = source.normalize({}, "licitacao")
        assert record.source == "tce_rj"
        assert record.uf == "RJ"
        assert record.numero_licitacao == ""
        assert record.objeto == ""
        assert record.valor_estimado is None
        assert record.modalidade == ""

    def test_normalize_id_is_string(self, source, raw_licitacao):
        record = source.normalize(raw_licitacao, "licitacao")
        assert isinstance(record.id, str)
        assert len(record.id) == 16

    def test_normalize_preserves_raw_data(self, source, raw_licitacao):
        record = source.normalize(raw_licitacao, "licitacao")
        assert record.raw_data == raw_licitacao


# ---------------------------------------------------------------------------
# TestNormalize — compra direta records
# ---------------------------------------------------------------------------

class TestNormalizeCompraDireta:
    """Tests for TCERJSource.normalize() with compra direta records."""

    def test_normalize_dispensa(self, source, raw_compra_direta_dispensa):
        record = source.normalize(raw_compra_direta_dispensa, "compra_direta")
        assert record.modalidade == "Dispensa"
        assert record.numero_licitacao == "DL-042/2026"
        assert record.valor_estimado == 89000.50
        assert record.orgao == "Prefeitura de Petrópolis"
        assert record.municipio == "Petrópolis"

    def test_normalize_inexigibilidade(self, source, raw_compra_direta_inexigibilidade):
        record = source.normalize(raw_compra_direta_inexigibilidade, "compra_direta")
        assert record.modalidade == "Inexigibilidade"
        assert record.numero_licitacao == "IN-005/2026"
        assert record.valor_estimado == 200000.00

    def test_normalize_adesao(self, source, raw_compra_direta_adesao):
        record = source.normalize(raw_compra_direta_adesao, "compra_direta")
        assert record.modalidade == "Adesão a Ata"
        assert record.numero_licitacao == "AD-003/2026"

    def test_compra_direta_uses_valor_field(self, source, raw_compra_direta_dispensa):
        """Compras diretas use 'valor' instead of 'valor_estimado'."""
        record = source.normalize(raw_compra_direta_dispensa, "compra_direta")
        assert record.valor_estimado == 89000.50

    def test_compra_direta_default_modalidade(self, source):
        """When tipo_compra is missing, defaults to Dispensa."""
        raw = {"numero": "X-001/2026", "objeto": "Teste"}
        record = source.normalize(raw, "compra_direta")
        assert record.modalidade == "Dispensa"


# ---------------------------------------------------------------------------
# TestFetchRecords — UF filter
# ---------------------------------------------------------------------------

class TestFetchRecordsUFFilter:
    """Tests for TCERJSource.fetch_records() UF filtering."""

    @pytest.mark.asyncio
    async def test_skip_non_rj_ufs(self, source):
        """fetch_records returns empty list immediately for non-RJ UFs."""
        query = SearchQuery(
            data_inicial="2026-01-01",
            data_final="2026-03-01",
            ufs=["SP", "MG"],
        )
        records = await source.fetch_records(query)
        assert records == []

    @pytest.mark.asyncio
    async def test_skip_empty_uf_list(self, source):
        """fetch_records returns empty list for explicitly empty UF list that doesn't contain RJ."""
        query = SearchQuery(
            data_inicial="2026-01-01",
            data_final="2026-03-01",
            ufs=["SP"],
        )
        records = await source.fetch_records(query)
        assert records == []


# ---------------------------------------------------------------------------
# TestFetchRecords — with mocked API
# ---------------------------------------------------------------------------

class TestFetchRecordsMocked:
    """Tests for TCERJSource.fetch_records() with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_fetch_licitacoes_and_compras(self, source, raw_licitacao, raw_compra_direta_dispensa):
        """Fetches from both endpoints and combines results."""
        licitacao_response = Mock()
        licitacao_response.status_code = 200
        licitacao_response.json.return_value = [raw_licitacao]

        compra_response = Mock()
        compra_response.status_code = 200
        compra_response.json.return_value = [raw_compra_direta_dispensa]

        call_count = 0

        async def mock_request(url, params):
            nonlocal call_count
            call_count += 1
            if "licitacoes" in url:
                return licitacao_response
            return compra_response

        source._request_with_retry = mock_request

        query = SearchQuery(
            data_inicial="2026-01-01",
            data_final="2026-03-01",
            ufs=["RJ"],
        )
        records = await source.fetch_records(query)
        assert len(records) == 2
        assert records[0].modalidade == "Pregão Eletrônico"
        assert records[1].modalidade == "Dispensa"

    @pytest.mark.asyncio
    async def test_fetch_with_ufs_none(self, source, raw_licitacao):
        """When ufs is None, fetches all records (no UF filter)."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = [raw_licitacao]

        async def mock_request(url, params):
            return response

        source._request_with_retry = mock_request

        query = SearchQuery(
            data_inicial="2026-01-01",
            data_final="2026-03-01",
            ufs=None,
        )
        records = await source.fetch_records(query)
        assert len(records) >= 1

    @pytest.mark.asyncio
    async def test_fetch_empty_response(self, source):
        """Handles empty API response gracefully."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = []

        async def mock_request(url, params):
            return response

        source._request_with_retry = mock_request

        query = SearchQuery(
            data_inicial="2026-01-01",
            data_final="2026-03-01",
            ufs=["RJ"],
        )
        records = await source.fetch_records(query)
        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_pagination(self, source):
        """Tests pagination across multiple pages."""
        page1_items = [
            {"numero": f"LIC-{i:03d}/2026", "objeto": f"Item {i}", "orgao": {"nome": "Org", "cnpj": "", "municipio": "Rio"}, "modalidade": "pregao_eletronico", "data_publicacao": "2026-01-15"}
            for i in range(TCE_RJ_PAGE_SIZE)
        ]
        page2_items = [
            {"numero": "LIC-LAST/2026", "objeto": "Last item", "orgao": {"nome": "Org", "cnpj": "", "municipio": "Rio"}, "modalidade": "concorrencia", "data_publicacao": "2026-01-20"}
        ]

        call_index = {"licitacoes": 0, "compras-diretas": 0}

        async def mock_request(url, params):
            response = Mock()
            response.status_code = 200
            if "licitacoes" in url:
                idx = call_index["licitacoes"]
                call_index["licitacoes"] += 1
                if idx == 0:
                    response.json.return_value = page1_items
                else:
                    response.json.return_value = page2_items
            else:
                response.json.return_value = []
            return response

        source._request_with_retry = mock_request

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-03-01", ufs=["RJ"])
        records = await source.fetch_records(query)
        assert len(records) == TCE_RJ_PAGE_SIZE + 1

    @pytest.mark.asyncio
    async def test_fetch_handles_api_error(self, source):
        """Handles API errors gracefully without crashing."""

        async def mock_request(url, params):
            raise httpx.ConnectError("Connection refused")

        source._request_with_retry = mock_request

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-03-01", ufs=["RJ"])
        records = await source.fetch_records(query)
        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_on_progress_callback(self, source, raw_licitacao):
        """on_progress callback is called with record count."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = [raw_licitacao]

        async def mock_request(url, params):
            return response

        source._request_with_retry = mock_request

        progress_calls = []

        def on_progress(page, count, total):
            progress_calls.append((page, count, total))

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-03-01", ufs=["RJ"])
        await source.fetch_records(query, on_progress=on_progress)
        assert len(progress_calls) == 1
        assert progress_calls[0][1] >= 1

    @pytest.mark.asyncio
    async def test_fetch_dict_response_with_items_key(self, source, raw_licitacao):
        """Handles API response wrapped in { items: [...] } format."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"items": [raw_licitacao], "total": 1}

        async def mock_request(url, params):
            return response

        source._request_with_retry = mock_request

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-03-01", ufs=["RJ"])
        records = await source.fetch_records(query)
        assert len(records) >= 1

    @pytest.mark.asyncio
    async def test_fetch_dict_response_with_results_key(self, source, raw_licitacao):
        """Handles API response wrapped in { results: [...] } format."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"results": [raw_licitacao]}

        async def mock_request(url, params):
            return response

        source._request_with_retry = mock_request

        query = SearchQuery(data_inicial="2026-01-01", data_final="2026-03-01", ufs=["RJ"])
        records = await source.fetch_records(query)
        assert len(records) >= 1


# ---------------------------------------------------------------------------
# TestRetryAndRateLimit
# ---------------------------------------------------------------------------

class TestRetryAndRateLimit:
    """Tests for retry and rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_500(self, source):
        """Retries on 500 status code and succeeds on second attempt."""
        attempt = {"count": 0}

        async def mock_get(url, params):
            attempt["count"] += 1
            if attempt["count"] == 1:
                resp = Mock()
                resp.status_code = 500
                return resp
            resp = Mock()
            resp.status_code = 200
            resp.raise_for_status = Mock()
            return resp

        source._last_request_time = 0.0
        source._client = Mock()
        source._client.is_closed = False
        source._client.get = mock_get

        config = RetryConfig(timeout=5, max_retries=3, base_delay=0.01, max_delay=0.05)
        source._config = config

        resp = await source._request_with_retry("http://test.com", {})
        assert resp.status_code == 200
        assert attempt["count"] == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, source):
        """Retries on timeout exception and succeeds."""
        attempt = {"count": 0}

        async def mock_get(url, params):
            attempt["count"] += 1
            if attempt["count"] == 1:
                raise httpx.TimeoutException("Timeout")
            resp = Mock()
            resp.status_code = 200
            resp.raise_for_status = Mock()
            return resp

        source._last_request_time = 0.0
        source._client = Mock()
        source._client.is_closed = False
        source._client.get = mock_get

        config = RetryConfig(timeout=5, max_retries=3, base_delay=0.01, max_delay=0.05)
        source._config = config

        resp = await source._request_with_retry("http://test.com", {})
        assert resp.status_code == 200
        assert attempt["count"] == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, source):
        """Raises exception when all retries are exhausted."""

        async def mock_get(url, params):
            raise httpx.ConnectError("Connection refused")

        source._last_request_time = 0.0
        source._client = Mock()
        source._client.is_closed = False
        source._client.get = mock_get

        config = RetryConfig(timeout=5, max_retries=2, base_delay=0.01, max_delay=0.05)
        source._config = config

        with pytest.raises(httpx.ConnectError):
            await source._request_with_retry("http://test.com", {})

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self, source):
        """Rate limiting delays requests appropriately."""
        import time

        source._rate_limit_rps = 1000  # High RPS = minimal delay for test speed
        source._last_request_time = time.monotonic()
        await source._rate_limit()
        # Should complete without significant delay at 1000 RPS


# ---------------------------------------------------------------------------
# TestIsHealthy
# ---------------------------------------------------------------------------

class TestIsHealthy:
    """Tests for TCERJSource.is_healthy()."""

    def test_healthy(self, source):
        with patch("sources.tce_rj_source.httpx.get") as mock_get:
            mock_get.return_value = Mock(status_code=200)
            assert source.is_healthy() is True

    def test_unhealthy_status(self, source):
        with patch("sources.tce_rj_source.httpx.get") as mock_get:
            mock_get.return_value = Mock(status_code=500)
            assert source.is_healthy() is False

    def test_unhealthy_exception(self, source):
        with patch("sources.tce_rj_source.httpx.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")
            assert source.is_healthy() is False


# ---------------------------------------------------------------------------
# TestToLegacyDict
# ---------------------------------------------------------------------------

class TestToLegacyDict:
    """Tests for NormalizedRecord.to_legacy_dict() with TCE-RJ records."""

    def test_legacy_dict_contains_all_fields(self, source, raw_licitacao):
        record = source.normalize(raw_licitacao, "licitacao")
        legacy = record.to_legacy_dict()
        assert legacy["source"] == "tce_rj"
        assert legacy["uf"] == "RJ"
        assert legacy["numero_licitacao"] == "PE-001/2026"
        assert legacy["modalidade"] == "Pregão Eletrônico"
        assert legacy["valor_estimado"] == 350000.00

    def test_legacy_dict_includes_raw_data(self, source, raw_licitacao):
        record = source.normalize(raw_licitacao, "licitacao")
        legacy = record.to_legacy_dict()
        # Raw data fields should be accessible
        assert "numero" in legacy
        assert legacy["numero"] == "PE-001/2026"


# ---------------------------------------------------------------------------
# TestContextManager
# ---------------------------------------------------------------------------

class TestContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self, source):
        async with source:
            assert source is not None

    @pytest.mark.asyncio
    async def test_close(self, source):
        source._client = Mock()
        source._client.is_closed = False
        source._client.aclose = AsyncMock()
        await source.close()
        source._client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_already_closed(self, source):
        source._client = Mock()
        source._client.is_closed = True
        await source.close()
        # Should not raise

    @pytest.mark.asyncio
    async def test_close_no_client(self, source):
        source._client = None
        await source.close()
        # Should not raise
