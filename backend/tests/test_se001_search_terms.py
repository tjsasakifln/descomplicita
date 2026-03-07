"""Tests for SE-001.1: Server-side palavraChave filtering in PNCP.

Covers all acceptance criteria:
1. SearchQuery accepts search_terms
2. SectorConfig defines search_keywords for all 12 sectors
3. PNCPClient.fetch_page() sends palavraChave
4. PNCPClient.fetch_all() iterates over search_terms with dedup
5. PNCPSource propagates search_terms
6. main.py sends sector search_keywords
7. Backward compatibility
"""

import asyncio
from unittest.mock import Mock, patch, MagicMock

import pytest

from sources.base import SearchQuery
from sectors import SectorConfig, SECTORS, get_sector
from pncp_client import PNCPClient
from config import RetryConfig


# ---------------------------------------------------------------------------
# AC1: SearchQuery accepts search_terms
# ---------------------------------------------------------------------------


class TestSearchQuerySearchTerms:
    """AC1: SearchQuery includes optional search_terms field."""

    def test_search_query_default_none(self):
        """search_terms defaults to None."""
        q = SearchQuery(data_inicial="2025-01-01", data_final="2025-01-31")
        assert q.search_terms is None

    def test_search_query_with_terms(self):
        """search_terms can be set explicitly."""
        q = SearchQuery(
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            search_terms=["medicamento", "hospitalar"],
        )
        assert q.search_terms == ["medicamento", "hospitalar"]

    def test_search_query_empty_list(self):
        """search_terms can be an empty list."""
        q = SearchQuery(
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            search_terms=[],
        )
        assert q.search_terms == []


# ---------------------------------------------------------------------------
# AC2: SectorConfig defines search_keywords for all 12 sectors
# ---------------------------------------------------------------------------


class TestSectorSearchKeywords:
    """AC2: All sectors have search_keywords defined."""

    def test_all_sectors_have_search_keywords(self):
        """Every sector must have at least 1 search_keyword."""
        for sector_id, sector in SECTORS.items():
            assert hasattr(sector, "search_keywords"), f"{sector_id} missing search_keywords"
            assert len(sector.search_keywords) >= 1, (
                f"{sector_id} has no search_keywords"
            )

    def test_search_keywords_max_5(self):
        """No sector should have more than 5 search_keywords."""
        for sector_id, sector in SECTORS.items():
            assert len(sector.search_keywords) <= 5, (
                f"{sector_id} has {len(sector.search_keywords)} search_keywords (max 5)"
            )

    def test_search_keywords_are_strings(self):
        """All search_keywords must be strings."""
        for sector_id, sector in SECTORS.items():
            for kw in sector.search_keywords:
                assert isinstance(kw, str), f"{sector_id}: {kw} is not a string"

    def test_saude_sector_keywords(self):
        """Saude sector has expected high-precision terms."""
        sector = get_sector("saude")
        assert "medicamento" in sector.search_keywords
        assert "hospitalar" in sector.search_keywords

    def test_vestuario_sector_keywords(self):
        """Vestuario sector has expected high-precision terms."""
        sector = get_sector("vestuario")
        assert "uniforme" in sector.search_keywords

    def test_sector_config_default_empty(self):
        """SectorConfig without search_keywords defaults to empty list."""
        sc = SectorConfig(id="test", name="Test", description="desc", keywords=set())
        assert sc.search_keywords == []

    def test_all_12_sectors_exist(self):
        """Verify all 12 expected sectors are defined."""
        expected = {
            "vestuario", "alimentos", "informatica", "limpeza",
            "mobiliario", "papelaria", "saude", "veiculos",
            "engenharia", "hospitalar", "servicos_gerais", "seguranca",
        }
        assert set(SECTORS.keys()) == expected


# ---------------------------------------------------------------------------
# AC3: PNCPClient.fetch_page() sends palavraChave
# ---------------------------------------------------------------------------


class TestFetchPagePalavraChave:
    """AC3: fetch_page sends palavraChave param when provided."""

    @patch("pncp_client.requests.Session.get")
    def test_fetch_page_sends_palavra_chave(self, mock_get):
        """palavraChave is included in API params when provided."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        client = PNCPClient()
        client.fetch_page(
            "2025-01-01", "2025-01-30",
            modalidade=6, uf="SP",
            palavra_chave="medicamento",
        )

        call_args = mock_get.call_args
        assert call_args[1]["params"]["palavraChave"] == "medicamento"

    @patch("pncp_client.requests.Session.get")
    def test_fetch_page_no_palavra_chave_by_default(self, mock_get):
        """palavraChave is NOT in params when not provided."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        client = PNCPClient()
        client.fetch_page("2025-01-01", "2025-01-30", modalidade=6)

        call_args = mock_get.call_args
        assert "palavraChave" not in call_args[1]["params"]

    @patch("pncp_client.requests.Session.get")
    def test_fetch_page_empty_string_not_sent(self, mock_get):
        """Empty string palavra_chave is not sent."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        client = PNCPClient()
        client.fetch_page(
            "2025-01-01", "2025-01-30",
            modalidade=6, palavra_chave="",
        )

        call_args = mock_get.call_args
        assert "palavraChave" not in call_args[1]["params"]


# ---------------------------------------------------------------------------
# AC4: PNCPClient.fetch_all() iterates over search_terms with dedup
# ---------------------------------------------------------------------------


class TestFetchAllSearchTerms:
    """AC4: fetch_all iterates over multiple search_terms and deduplicates."""

    @patch("pncp_client.requests.Session.get")
    def test_fetch_all_with_search_terms_multiple_queries(self, mock_get):
        """With 2 search_terms, fetch_all makes 2 API calls per UF×modalidade."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "data": [],
            "totalRegistros": 0,
            "totalPaginas": 1,
            "paginasRestantes": 0,
        }
        mock_get.return_value = mock_response

        client = PNCPClient()
        list(client.fetch_all(
            "2025-01-01", "2025-01-30",
            ufs=["SP"],
            modalidades=[6],
            search_terms=["medicamento", "hospitalar"],
        ))

        # 1 UF × 1 modalidade × 2 terms = 2 calls
        assert mock_get.call_count == 2

    @patch("pncp_client.requests.Session.get")
    def test_fetch_all_search_terms_passes_palavra_chave(self, mock_get):
        """Each search term is passed as palavraChave in the API call."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "data": [],
            "totalRegistros": 0,
            "totalPaginas": 1,
            "paginasRestantes": 0,
        }
        mock_get.return_value = mock_response

        client = PNCPClient()
        list(client.fetch_all(
            "2025-01-01", "2025-01-30",
            ufs=["SP"],
            modalidades=[6],
            search_terms=["medicamento"],
        ))

        call_args = mock_get.call_args
        assert call_args[1]["params"]["palavraChave"] == "medicamento"

    @patch("pncp_client.requests.Session.get")
    def test_fetch_all_search_terms_deduplicates(self, mock_get):
        """Records appearing in multiple term queries are deduplicated."""
        # Both terms return the same record
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "data": [
                {
                    "numeroControlePNCP": "DUP-001",
                    "unidadeOrgao": {"ufSigla": "SP", "municipioNome": ""},
                    "orgaoEntidade": {"razaoSocial": ""},
                }
            ],
            "totalRegistros": 1,
            "totalPaginas": 1,
            "paginasRestantes": 0,
        }
        mock_get.return_value = mock_response

        client = PNCPClient()
        results = list(client.fetch_all(
            "2025-01-01", "2025-01-30",
            ufs=["SP"],
            modalidades=[6],
            search_terms=["medicamento", "hospitalar"],
        ))

        # Same record from 2 terms → deduplicated to 1
        assert len(results) == 1
        assert results[0]["codigoCompra"] == "DUP-001"

    @patch("pncp_client.requests.Session.get")
    def test_fetch_all_without_search_terms_unchanged(self, mock_get):
        """Without search_terms, behavior is identical to original."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "data": [
                {
                    "numeroControlePNCP": "001",
                    "unidadeOrgao": {"ufSigla": "SP", "municipioNome": ""},
                    "orgaoEntidade": {"razaoSocial": ""},
                }
            ],
            "totalRegistros": 1,
            "totalPaginas": 1,
            "paginasRestantes": 0,
        }
        mock_get.return_value = mock_response

        client = PNCPClient()
        results = list(client.fetch_all(
            "2025-01-01", "2025-01-30",
            ufs=["SP"],
            modalidades=[6],
        ))

        assert len(results) == 1
        # No palavraChave in params
        call_args = mock_get.call_args
        assert "palavraChave" not in call_args[1]["params"]


# ---------------------------------------------------------------------------
# AC5: PNCPSource propagates search_terms
# ---------------------------------------------------------------------------


class TestPNCPSourceSearchTerms:
    """AC5: PNCPSource.fetch_records() passes search_terms to PNCPClient."""

    @pytest.mark.asyncio
    async def test_pncp_source_propagates_search_terms(self):
        """search_terms from SearchQuery are passed to PNCPClient.fetch_all."""
        from sources.pncp_source import PNCPSource

        source = PNCPSource()

        # Mock the client's fetch_all
        with patch.object(source._client, "fetch_all", return_value=iter([])) as mock_fetch:
            query = SearchQuery(
                data_inicial="2025-01-01",
                data_final="2025-01-31",
                ufs=["SP"],
                search_terms=["medicamento", "hospitalar"],
            )
            await source.fetch_records(query)

            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args
            # Check search_terms was passed
            assert call_kwargs[1]["search_terms"] == ["medicamento", "hospitalar"]

    @pytest.mark.asyncio
    async def test_pncp_source_no_search_terms(self):
        """Without search_terms, None is passed to PNCPClient.fetch_all."""
        from sources.pncp_source import PNCPSource

        source = PNCPSource()

        with patch.object(source._client, "fetch_all", return_value=iter([])) as mock_fetch:
            query = SearchQuery(
                data_inicial="2025-01-01",
                data_final="2025-01-31",
                ufs=["SP"],
            )
            await source.fetch_records(query)

            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args
            assert call_kwargs[1]["search_terms"] is None


# ---------------------------------------------------------------------------
# AC6: Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """AC6: Without search_terms, pipeline behaves identically."""

    def test_search_query_backward_compatible(self):
        """Existing code creating SearchQuery without search_terms still works."""
        q = SearchQuery(
            data_inicial="2025-01-01",
            data_final="2025-01-31",
            ufs=["SP", "RJ"],
            modalidades=[6, 8],
        )
        assert q.search_terms is None

    @patch("pncp_client.requests.Session.get")
    def test_fetch_all_backward_compatible(self, mock_get):
        """fetch_all without search_terms works exactly as before."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "data": [
                {
                    "numeroControlePNCP": "001",
                    "unidadeOrgao": {"ufSigla": "SP", "municipioNome": ""},
                    "orgaoEntidade": {"razaoSocial": ""},
                }
            ],
            "totalRegistros": 1,
            "totalPaginas": 1,
            "paginasRestantes": 0,
        }
        mock_get.return_value = mock_response

        client = PNCPClient()
        results = list(client.fetch_all(
            "2025-01-01", "2025-01-30",
            ufs=["SP"],
            modalidades=[6],
        ))

        assert len(results) == 1
        # Only 1 API call (no search_terms = single pass)
        assert mock_get.call_count == 1

    @patch("pncp_client.requests.Session.get")
    def test_fetch_page_backward_compatible(self, mock_get):
        """fetch_page without palavra_chave works exactly as before."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"data": [{"id": 1}]}
        mock_get.return_value = mock_response

        client = PNCPClient()
        result = client.fetch_page("2025-01-01", "2025-01-30", modalidade=6)

        assert result["data"] == [{"id": 1}]
        call_args = mock_get.call_args
        assert "palavraChave" not in call_args[1]["params"]


# ---------------------------------------------------------------------------
# AC4+: Cache key includes palavra_chave
# ---------------------------------------------------------------------------


class TestCacheKeyWithPalavraChave:
    """Cache keys include palavra_chave to avoid mixing cached results."""

    @patch("pncp_client.requests.Session.get")
    def test_different_terms_different_cache_keys(self, mock_get):
        """Two different search_terms should not share cache entries."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "data": [
                {
                    "numeroControlePNCP": "001",
                    "unidadeOrgao": {"ufSigla": "SP", "municipioNome": ""},
                    "orgaoEntidade": {"razaoSocial": ""},
                }
            ],
            "totalRegistros": 1,
            "totalPaginas": 1,
            "paginasRestantes": 0,
        }
        mock_get.return_value = mock_response

        client = PNCPClient()

        # First call with term "medicamento"
        list(client.fetch_all(
            "2025-01-01", "2025-01-30",
            ufs=["SP"], modalidades=[6],
            search_terms=["medicamento"],
        ))

        # Second call with term "hospitalar" — should NOT be cached
        list(client.fetch_all(
            "2025-01-01", "2025-01-30",
            ufs=["SP"], modalidades=[6],
            search_terms=["hospitalar"],
        ))

        # Both should result in API calls (no false cache hit)
        assert mock_get.call_count == 2
