"""Unit tests for sources/base.py — DataSourceClient ABC, NormalizedRecord, SearchQuery."""

from datetime import datetime

import pytest

from sources.base import DataSourceClient, NormalizedRecord, SearchQuery


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_minimal_query(self):
        q = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        assert q.data_inicial == "2025-01-01"
        assert q.data_final == "2025-01-31"
        assert q.ufs is None
        assert q.modalidades is None

    def test_full_query(self):
        q = SearchQuery(
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            ufs=["SP", "RJ"],
            modalidades=[6, 8],
        )
        assert q.ufs == ["SP", "RJ"]
        assert q.modalidades == [6, 8]


class TestNormalizedRecord:
    """Tests for NormalizedRecord dataclass."""

    @pytest.fixture
    def sample_record(self):
        return NormalizedRecord(
            id="PNCP-001",
            source="PNCP",
            sources=["PNCP"],
            numero_licitacao="PNCP-001",
            objeto="Aquisição de uniformes escolares",
            orgao="Prefeitura Municipal de São Paulo",
            cnpj_orgao="12345678000199",
            uf="SP",
            municipio="São Paulo",
            valor_estimado=150000.0,
            modalidade="Pregão - Eletrônico",
            modalidade_codigo=6,
            data_publicacao=datetime(2025, 1, 15),
            data_abertura=datetime(2025, 2, 15, 10, 0),
            status="Aberto",
            url_edital="https://pncp.gov.br/app/editais/12345678000199/2025/1",
            url_fonte=None,
            raw_data={
                "numeroControlePNCP": "PNCP-001",
                "objetoCompra": "Aquisição de uniformes escolares",
                "nomeOrgao": "Prefeitura Municipal de São Paulo",
                "uf": "SP",
                "municipio": "São Paulo",
                "valorTotalEstimado": 150000.0,
                "codigoCompra": "PNCP-001",
                "cnpj": "12345678000199",
                "anoCompra": "2025",
                "sequencialCompra": "1",
            },
        )

    def test_required_fields(self, sample_record):
        assert sample_record.id == "PNCP-001"
        assert sample_record.source == "PNCP"
        assert sample_record.sources == ["PNCP"]
        assert sample_record.objeto == "Aquisição de uniformes escolares"
        assert sample_record.uf == "SP"
        assert sample_record.valor_estimado == 150000.0

    def test_optional_fields_default_none(self):
        r = NormalizedRecord(
            id="X",
            source="TEST",
            sources=["TEST"],
            numero_licitacao="X",
            objeto="Test",
            orgao="Org",
            cnpj_orgao="",
            uf="SP",
            municipio="SP",
            valor_estimado=None,
            modalidade="",
        )
        assert r.modalidade_codigo is None
        assert r.data_publicacao is None
        assert r.data_abertura is None
        assert r.status is None
        assert r.url_edital is None
        assert r.url_fonte is None
        assert r.raw_data == {}

    def test_to_legacy_dict_contains_raw_data(self, sample_record):
        d = sample_record.to_legacy_dict()
        # Original PNCP fields should be present
        assert d["objetoCompra"] == "Aquisição de uniformes escolares"
        assert d["valorTotalEstimado"] == 150000.0
        assert d["codigoCompra"] == "PNCP-001"
        assert d["nomeOrgao"] == "Prefeitura Municipal de São Paulo"

    def test_to_legacy_dict_contains_normalized_fields(self, sample_record):
        d = sample_record.to_legacy_dict()
        # Normalized field names should also be present
        assert d["objeto"] == "Aquisição de uniformes escolares"
        assert d["valor_estimado"] == 150000.0
        assert d["orgao"] == "Prefeitura Municipal de São Paulo"
        assert d["cnpj_orgao"] == "12345678000199"
        assert d["source"] == "PNCP"
        assert d["sources"] == ["PNCP"]

    def test_to_legacy_dict_preserves_all_raw_keys(self, sample_record):
        d = sample_record.to_legacy_dict()
        for key in sample_record.raw_data:
            assert key in d

    def test_to_legacy_dict_does_not_mutate_raw_data(self, sample_record):
        raw_before = dict(sample_record.raw_data)
        sample_record.to_legacy_dict()
        assert sample_record.raw_data == raw_before


class TestDataSourceClientABC:
    """Tests for DataSourceClient abstract base class."""

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            DataSourceClient()

    def test_concrete_subclass_must_implement_methods(self):
        class IncompleteSource(DataSourceClient):
            pass

        with pytest.raises(TypeError):
            IncompleteSource()

    def test_concrete_subclass_works(self):
        class TestSource(DataSourceClient):
            @property
            def source_name(self):
                return "test"

            async def fetch_records(self, query):
                return []

            def normalize(self, raw):
                return NormalizedRecord(
                    id="1",
                    source="test",
                    sources=["test"],
                    numero_licitacao="1",
                    objeto="",
                    orgao="",
                    cnpj_orgao="",
                    uf="",
                    municipio="",
                    valor_estimado=None,
                    modalidade="",
                )

            def is_healthy(self):
                return True

        source = TestSource()
        assert source.source_name == "test"
        assert source.is_healthy() is True
