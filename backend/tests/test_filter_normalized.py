"""Tests for filter.py compatibility with NormalizedRecord field names.

Verifies that filter_licitacao and filter_batch work with both:
- Legacy PNCP field names (objetoCompra, valorTotalEstimado)
- NormalizedRecord field names (objeto, valor_estimado)
"""

from datetime import datetime, timezone, timedelta
from filter import filter_licitacao, filter_batch


class TestFilterWithNormalizedFields:
    """Test filter_licitacao with NormalizedRecord-style field names."""

    def test_accepts_normalized_valor_field(self):
        """Should accept 'valor_estimado' as value field."""
        licitacao = {
            "uf": "SP",
            "valor_estimado": 100_000.0,
            "objeto": "Aquisição de uniformes escolares",
        }
        aprovada, motivo, _kw, _sc = filter_licitacao(licitacao, {"SP"})
        assert aprovada is True
        assert motivo is None

    def test_accepts_normalized_objeto_field(self):
        """Should accept 'objeto' as object description field."""
        licitacao = {
            "uf": "SP",
            "valor_estimado": 100_000.0,
            "objeto": "Fornecimento de jalecos hospitalares",
        }
        aprovada, motivo, _kw, _sc = filter_licitacao(licitacao, {"SP"})
        assert aprovada is True
        assert motivo is None

    def test_accepts_valor_none_normalized(self):
        """Items with valor=None should pass (e.g., Atas de Registro de Preço)."""
        licitacao = {
            "uf": "SP",
            "objeto": "Uniformes",
        }
        aprovada, motivo, _kw, _sc = filter_licitacao(licitacao, {"SP"})
        assert aprovada is True
        assert motivo is None

    def test_rejects_valor_below_min_normalized(self):
        """Should reject when valor_estimado is below minimum."""
        licitacao = {
            "uf": "SP",
            "valor_estimado": 30_000.0,
            "objeto": "Uniformes",
        }
        aprovada, motivo, _kw, _sc = filter_licitacao(licitacao, {"SP"})
        assert aprovada is False
        assert "fora da faixa" in motivo

    def test_rejects_missing_keywords_normalized(self):
        """Should reject when objeto has no sector keywords."""
        licitacao = {
            "uf": "SP",
            "valor_estimado": 100_000.0,
            "objeto": "Aquisição de notebooks e impressoras",
        }
        aprovada, motivo, _kw, _sc = filter_licitacao(licitacao, {"SP"})
        assert aprovada is False
        assert "keywords" in motivo.lower() or "setor" in motivo.lower()

    def test_legacy_fields_still_work(self):
        """Legacy PNCP field names should continue to work."""
        licitacao = {
            "uf": "SP",
            "valorTotalEstimado": 100_000.0,
            "objetoCompra": "Uniformes escolares",
        }
        aprovada, motivo, _kw, _sc = filter_licitacao(licitacao, {"SP"})
        assert aprovada is True
        assert motivo is None

    def test_legacy_takes_precedence_over_normalized(self):
        """When both fields present, valorTotalEstimado should take precedence."""
        licitacao = {
            "uf": "SP",
            "valorTotalEstimado": 100_000.0,
            "valor_estimado": 30_000.0,  # Would be rejected if used
            "objetoCompra": "Uniformes escolares",
            "objeto": "Something else",
        }
        aprovada, motivo, _kw, _sc = filter_licitacao(licitacao, {"SP"})
        assert aprovada is True

    def test_to_legacy_dict_works_with_filter(self):
        """A NormalizedRecord.to_legacy_dict() should pass filters correctly."""
        from sources.base import NormalizedRecord

        record = NormalizedRecord(
            id="001",
            source="PNCP",
            sources=["PNCP"],
            numero_licitacao="001",
            objeto="Aquisição de uniformes escolares",
            orgao="Prefeitura Test",
            cnpj_orgao="123",
            uf="SP",
            municipio="São Paulo",
            valor_estimado=150_000.0,
            modalidade="Pregão",
            raw_data={
                "uf": "SP",
                "valorTotalEstimado": 150_000.0,
                "objetoCompra": "Aquisição de uniformes escolares",
                "codigoCompra": "001",
                "nomeOrgao": "Prefeitura Test",
            },
        )

        legacy = record.to_legacy_dict()
        aprovada, motivo, _kw, _sc = filter_licitacao(legacy, {"SP"})
        assert aprovada is True
        assert motivo is None


class TestFilterBatchWithNormalizedFields:
    """Test filter_batch with NormalizedRecord-style dicts."""

    def test_batch_with_normalized_fields(self):
        licitacoes = [
            {
                "uf": "SP",
                "valor_estimado": 100_000.0,
                "objeto": "Uniformes escolares",
            },
            {
                "uf": "RJ",
                "valor_estimado": 80_000.0,
                "objeto": "Jalecos médicos",
            },
        ]
        aprovadas, stats = filter_batch(licitacoes, {"SP"})

        assert len(aprovadas) == 1
        assert stats["aprovadas"] == 1
        assert stats["rejeitadas_uf"] == 1

    def test_batch_mixed_legacy_and_normalized(self):
        """Batch with both field name formats should work."""
        licitacoes = [
            {
                "uf": "SP",
                "valorTotalEstimado": 100_000.0,
                "objetoCompra": "Uniformes",
            },
            {
                "uf": "SP",
                "valor_estimado": 200_000.0,
                "objeto": "Fardamento militar",
            },
        ]
        aprovadas, stats = filter_batch(licitacoes, {"SP"})

        assert len(aprovadas) == 2
        assert stats["aprovadas"] == 2
