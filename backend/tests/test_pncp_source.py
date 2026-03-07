"""Unit tests for sources/pncp_source.py — PNCPSource adapter."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sources.pncp_source import PNCPSource, _parse_datetime
from sources.base import SearchQuery, NormalizedRecord


class TestParseDatetime:
    """Tests for the _parse_datetime helper."""

    def test_iso_with_z(self):
        dt = _parse_datetime("2025-02-15T10:30:00Z")
        assert dt == datetime(2025, 2, 15, 10, 30, 0)
        assert dt.tzinfo is None

    def test_iso_with_timezone(self):
        dt = _parse_datetime("2025-02-15T10:30:00-03:00")
        assert dt.year == 2025
        assert dt.tzinfo is None

    def test_iso_without_timezone(self):
        dt = _parse_datetime("2025-02-15T10:30:00")
        assert dt == datetime(2025, 2, 15, 10, 30, 0)

    def test_date_only(self):
        dt = _parse_datetime("2025-02-15")
        assert dt == datetime(2025, 2, 15, 0, 0, 0)

    def test_none_returns_none(self):
        assert _parse_datetime(None) is None

    def test_empty_returns_none(self):
        assert _parse_datetime("") is None

    def test_invalid_returns_none(self):
        assert _parse_datetime("not-a-date") is None


class TestPNCPSourceInit:
    """Tests for PNCPSource initialization."""

    def test_default_init(self):
        source = PNCPSource()
        assert source.source_name == "PNCP"
        assert source.client is not None
        assert source.is_healthy() is True

    def test_custom_config(self):
        from config import RetryConfig
        config = RetryConfig(max_retries=1, timeout=5)
        source = PNCPSource(config=config)
        assert source.client.config.max_retries == 1
        assert source.client.config.timeout == 5

    def test_context_manager(self):
        with PNCPSource() as source:
            assert source.is_healthy() is True


class TestPNCPSourceNormalize:
    """Tests for PNCPSource.normalize()."""

    @pytest.fixture
    def source(self):
        return PNCPSource()

    @pytest.fixture
    def raw_pncp_item(self):
        """A flat PNCP dict as produced by PNCPClient._normalize_item."""
        return {
            "numeroControlePNCP": "00012345678900-2025-000001",
            "objetoCompra": "Aquisição de uniformes escolares para rede municipal",
            "nomeOrgao": "Prefeitura Municipal de São Paulo",
            "uf": "SP",
            "municipio": "São Paulo",
            "valorTotalEstimado": 287500.0,
            "codigoCompra": "00012345678900-2025-000001",
            "cnpj": "00012345678900",
            "anoCompra": "2025",
            "sequencialCompra": "000001",
            "modalidadeNome": "Pregão - Eletrônico",
            "codigoModalidadeContratacao": 6,
            "dataPublicacaoPncp": "2025-01-15",
            "dataAberturaProposta": "2025-02-15T10:00:00Z",
            "situacaoCompraNome": "Aberto",
            "linkPncp": None,
            "unidadeOrgao": {"ufSigla": "SP", "municipioNome": "São Paulo"},
            "orgaoEntidade": {"razaoSocial": "Pref SP", "cnpj": "00012345678900"},
        }

    def test_normalize_produces_normalized_record(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert isinstance(record, NormalizedRecord)

    def test_normalize_id(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.id == "00012345678900-2025-000001"

    def test_normalize_source(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.source == "PNCP"
        assert record.sources == ["PNCP"]

    def test_normalize_objeto(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.objeto == "Aquisição de uniformes escolares para rede municipal"

    def test_normalize_orgao(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.orgao == "Prefeitura Municipal de São Paulo"

    def test_normalize_location(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.uf == "SP"
        assert record.municipio == "São Paulo"

    def test_normalize_valor(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.valor_estimado == 287500.0

    def test_normalize_modalidade(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.modalidade == "Pregão - Eletrônico"
        assert record.modalidade_codigo == 6

    def test_normalize_dates(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.data_publicacao == datetime(2025, 1, 15)
        assert record.data_abertura == datetime(2025, 2, 15, 10, 0, 0)

    def test_normalize_status(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.status == "Aberto"

    def test_normalize_url_edital_from_parts(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.url_edital == "https://pncp.gov.br/app/editais/00012345678900/2025/000001"

    def test_normalize_url_edital_from_link_pncp(self, source, raw_pncp_item):
        raw_pncp_item["linkPncp"] = "https://custom-link.gov.br/edital/123"
        record = source.normalize(raw_pncp_item)
        assert record.url_edital == "https://custom-link.gov.br/edital/123"

    def test_normalize_raw_data_preserved(self, source, raw_pncp_item):
        record = source.normalize(raw_pncp_item)
        assert record.raw_data is raw_pncp_item
        assert record.raw_data["valorTotalEstimado"] == 287500.0

    def test_normalize_missing_fields(self, source):
        """Normalize should handle minimal dicts gracefully."""
        record = source.normalize({})
        assert record.id == ""
        assert record.objeto == ""
        assert record.valor_estimado is None
        assert record.data_abertura is None

    def test_normalize_to_legacy_dict_roundtrip(self, source, raw_pncp_item):
        """to_legacy_dict should contain all original PNCP fields."""
        record = source.normalize(raw_pncp_item)
        legacy = record.to_legacy_dict()

        # PNCP-specific fields used by excel.py / llm.py
        assert legacy["objetoCompra"] == raw_pncp_item["objetoCompra"]
        assert legacy["valorTotalEstimado"] == raw_pncp_item["valorTotalEstimado"]
        assert legacy["codigoCompra"] == raw_pncp_item["codigoCompra"]
        assert legacy["nomeOrgao"] == raw_pncp_item["nomeOrgao"]
        assert legacy["uf"] == "SP"
        assert legacy["municipio"] == "São Paulo"

        # Normalized fields also present
        assert legacy["objeto"] == record.objeto
        assert legacy["valor_estimado"] == record.valor_estimado


class TestPNCPSourceFetchRecords:
    """Tests for PNCPSource.fetch_records() async method."""

    @pytest.fixture
    def source_with_mock_client(self):
        source = PNCPSource()
        source._client = Mock()
        return source

    @pytest.mark.asyncio
    async def test_fetch_records_returns_normalized_records(self, source_with_mock_client):
        source = source_with_mock_client
        source._client.fetch_all.return_value = iter([
            {
                "numeroControlePNCP": "001",
                "objetoCompra": "Uniformes",
                "nomeOrgao": "Prefeitura Test",
                "uf": "SP",
                "municipio": "São Paulo",
                "valorTotalEstimado": 100000.0,
                "codigoCompra": "001",
                "cnpj": "123",
                "anoCompra": "2025",
                "sequencialCompra": "1",
            }
        ])
        source._client.fetch_all_atas.return_value = iter([])

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31", ufs=["SP"])
        records = await source.fetch_records(query)

        assert len(records) == 1
        assert isinstance(records[0], NormalizedRecord)
        assert records[0].id == "001"
        assert records[0].source == "PNCP"
        assert records[0].objeto == "Uniformes"
        assert records[0].uf == "SP"
        assert records[0].valor_estimado == 100000.0

    @pytest.mark.asyncio
    async def test_fetch_records_passes_query_params(self, source_with_mock_client):
        source = source_with_mock_client
        source._client.fetch_all.return_value = iter([])
        source._client.fetch_all_atas.return_value = iter([])

        query = SearchQuery(
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            ufs=["SP", "RJ"],
            modalidades=[6, 8],
        )
        await source.fetch_records(query)

        source._client.fetch_all.assert_called_once_with(
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            ufs=["SP", "RJ"],
            modalidades=[6, 8],
            on_progress=None,
            search_terms=None,
        )

    @pytest.mark.asyncio
    async def test_fetch_records_empty_results(self, source_with_mock_client):
        source = source_with_mock_client
        source._client.fetch_all.return_value = iter([])
        source._client.fetch_all_atas.return_value = iter([])

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        records = await source.fetch_records(query)

        assert records == []

    @pytest.mark.asyncio
    async def test_fetch_records_multiple_items(self, source_with_mock_client):
        source = source_with_mock_client
        source._client.fetch_all.return_value = iter([
            {"numeroControlePNCP": "001", "objetoCompra": "Item 1", "uf": "SP",
             "municipio": "", "nomeOrgao": "", "valorTotalEstimado": 50000.0,
             "codigoCompra": "001", "cnpj": "", "anoCompra": "", "sequencialCompra": ""},
            {"numeroControlePNCP": "002", "objetoCompra": "Item 2", "uf": "RJ",
             "municipio": "", "nomeOrgao": "", "valorTotalEstimado": 75000.0,
             "codigoCompra": "002", "cnpj": "", "anoCompra": "", "sequencialCompra": ""},
        ])
        source._client.fetch_all_atas.return_value = iter([])

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        records = await source.fetch_records(query)

        assert len(records) == 2
        assert records[0].id == "001"
        assert records[1].id == "002"

    @pytest.mark.asyncio
    async def test_fetch_records_combines_contratacoes_and_atas(self, source_with_mock_client):
        """SE-001.5: fetch_records should combine licitacoes and atas."""
        source = source_with_mock_client
        source._client.fetch_all.return_value = iter([
            {"numeroControlePNCP": "LIC-001", "objetoCompra": "Uniformes", "uf": "SP",
             "municipio": "", "nomeOrgao": "", "valorTotalEstimado": 50000.0,
             "codigoCompra": "LIC-001", "cnpj": "", "anoCompra": "", "sequencialCompra": ""},
        ])
        source._client.fetch_all_atas.return_value = iter([
            {"numeroControlePNCP": "ATA-001", "objetoCompra": "Medicamentos", "uf": "RJ",
             "municipio": "", "nomeOrgao": "", "valorTotalEstimado": 75000.0,
             "codigoCompra": "ATA-001", "cnpj": "", "anoCompra": "", "sequencialCompra": "",
             "_tipo": "ata_registro_preco"},
        ])

        query = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        records = await source.fetch_records(query)

        assert len(records) == 2
        tipos = {r.tipo for r in records}
        assert "licitacao" in tipos
        assert "ata_registro_preco" in tipos


class TestPNCPSourceCacheDelegation:
    """Tests for cache operation delegation to underlying PNCPClient."""

    def test_cache_stats(self):
        source = PNCPSource()
        stats = source.cache_stats()
        assert "entries" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_ratio" in stats

    def test_cache_clear(self):
        source = PNCPSource()
        cleared = source.cache_clear()
        assert cleared == 0  # Empty cache


class TestPNCPSourceHealthCheck:
    """Tests for PNCPSource.is_healthy()."""

    def test_healthy_when_session_exists(self):
        source = PNCPSource()
        assert source.is_healthy() is True

    def test_unhealthy_when_session_none(self):
        source = PNCPSource()
        source._client.session = None
        assert source.is_healthy() is False
