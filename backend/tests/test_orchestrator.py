"""Unit tests for sources/orchestrator.py — MultiSourceOrchestrator (MS-001.6)."""

import asyncio
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sources.base import DataSourceClient, NormalizedRecord, SearchQuery
from sources.orchestrator import (
    MultiSourceOrchestrator,
    OrchestratorResult,
    SourceStats,
    _count_filled_fields,
    _dedup_key,
    _dedup_key_fallback,
    _dedup_key_primary,
    _normalize_str,
    get_enabled_source_names,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    source: str = "pncp",
    numero: str = "001/2025",
    cnpj: str = "12345678000190",
    objeto: str = "Aquisicao de uniformes",
    uf: str = "SP",
    valor: float = 100000.0,
    data_pub: datetime = None,
    municipio: str = "Sao Paulo",
    modalidade: str = "Pregao Eletronico",
    record_id: str = None,
    status: str = None,
    url_edital: str = None,
    url_fonte: str = None,
) -> NormalizedRecord:
    """Create a NormalizedRecord for testing."""
    if record_id is None:
        record_id = hashlib.md5(
            f"{source}-{numero}-{cnpj}".encode()
        ).hexdigest()[:16]
    return NormalizedRecord(
        id=record_id,
        source=source,
        sources=[source],
        numero_licitacao=numero,
        objeto=objeto,
        orgao="Orgao Teste",
        cnpj_orgao=cnpj,
        uf=uf,
        municipio=municipio,
        valor_estimado=valor,
        modalidade=modalidade,
        data_publicacao=data_pub,
        status=status,
        url_edital=url_edital,
        url_fonte=url_fonte,
    )


class FakeSource(DataSourceClient):
    """A fake DataSourceClient for testing."""

    def __init__(self, name: str, records: List[NormalizedRecord] = None, delay: float = 0, error: Exception = None):
        self._name = name
        self._records = records or []
        self._delay = delay
        self._error = error

    @property
    def source_name(self) -> str:
        return self._name

    async def fetch_records(self, query: SearchQuery) -> List[NormalizedRecord]:
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        return list(self._records)

    def normalize(self, raw: dict) -> NormalizedRecord:
        return _make_record(source=self._name)

    def is_healthy(self) -> bool:
        return self._error is None


@pytest.fixture
def query():
    """Standard search query for tests."""
    return SearchQuery(
        data_inicial="2025-01-01",
        data_final="2025-01-31",
        ufs=["SP", "RJ"],
    )


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


class TestNormalizeStr:
    def test_basic(self):
        assert _normalize_str("ABC-123") == "abc123"

    def test_none(self):
        assert _normalize_str(None) == ""

    def test_empty(self):
        assert _normalize_str("") == ""

    def test_special_chars(self):
        assert _normalize_str("12.345.678/0001-90") == "12345678000190"


class TestDedupKeyPrimary:
    def test_with_cnpj_and_numero(self):
        record = _make_record(cnpj="12345678000190", numero="001/2025")
        key = _dedup_key_primary(record)
        assert key is not None
        assert len(key) == 32  # MD5 hex

    def test_deterministic(self):
        r1 = _make_record(cnpj="12345678000190", numero="001/2025")
        r2 = _make_record(cnpj="12345678000190", numero="001/2025", source="comprasgov")
        assert _dedup_key_primary(r1) == _dedup_key_primary(r2)

    def test_different_cnpj_different_key(self):
        r1 = _make_record(cnpj="12345678000190", numero="001/2025")
        r2 = _make_record(cnpj="99999999000199", numero="001/2025")
        assert _dedup_key_primary(r1) != _dedup_key_primary(r2)

    def test_missing_cnpj_returns_none(self):
        record = _make_record(cnpj="", numero="001/2025")
        assert _dedup_key_primary(record) is None

    def test_missing_numero_returns_none(self):
        record = _make_record(cnpj="12345678000190", numero="")
        assert _dedup_key_primary(record) is None


class TestDedupKeyFallback:
    def test_with_objeto_and_uf(self):
        record = _make_record(objeto="Compra de materiais", uf="SP")
        key = _dedup_key_fallback(record)
        assert key is not None

    def test_deterministic(self):
        r1 = _make_record(cnpj="", numero="", objeto="Compra xyz", uf="RJ",
                          data_pub=datetime(2025, 1, 15))
        r2 = _make_record(cnpj="", numero="", objeto="Compra xyz", uf="RJ",
                          data_pub=datetime(2025, 1, 15), source="comprasgov")
        assert _dedup_key_fallback(r1) == _dedup_key_fallback(r2)

    def test_empty_objeto_returns_none(self):
        record = _make_record(objeto="", cnpj="", numero="")
        assert _dedup_key_fallback(record) is None


class TestCountFilledFields:
    def test_full_record(self):
        record = _make_record(
            status="Aberto",
            url_edital="http://example.com",
            url_fonte="http://example.com/fonte",
        )
        assert _count_filled_fields(record) >= 10

    def test_minimal_record(self):
        record = NormalizedRecord(
            id="x", source="test", sources=["test"],
            numero_licitacao="", objeto="", orgao="", cnpj_orgao="",
            uf="", municipio="", valor_estimado=None, modalidade="",
        )
        assert _count_filled_fields(record) == 0


# ---------------------------------------------------------------------------
# get_enabled_source_names
# ---------------------------------------------------------------------------


class TestGetEnabledSourceNames:
    def test_default_from_config(self):
        names = get_enabled_source_names()
        assert isinstance(names, list)
        assert "pncp" in names

    @patch.dict("os.environ", {"ENABLED_SOURCES": "pncp,comprasgov"})
    def test_env_override(self):
        names = get_enabled_source_names()
        assert names == ["pncp", "comprasgov"]

    @patch.dict("os.environ", {"ENABLED_SOURCES": " pncp , tce_rj "})
    def test_env_override_strips_whitespace(self):
        names = get_enabled_source_names()
        assert names == ["pncp", "tce_rj"]

    @patch.dict("os.environ", {"ENABLED_SOURCES": ""})
    def test_empty_env_uses_config(self):
        names = get_enabled_source_names()
        assert len(names) > 0


# ---------------------------------------------------------------------------
# MultiSourceOrchestrator — Parallel execution
# ---------------------------------------------------------------------------


class TestOrchestratorParallel:
    """Test parallel search across multiple sources."""

    @pytest.mark.asyncio
    async def test_all_sources_succeed(self, query):
        """AC3: search_all executes all sources in parallel and returns unified result."""
        r1 = _make_record(source="pncp", numero="001/2025", cnpj="11111111000111")
        r2 = _make_record(source="comprasgov", numero="002/2025", cnpj="22222222000122")

        src1 = FakeSource("pncp", [r1])
        src2 = FakeSource("comprasgov", [r2])

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp", "comprasgov"]):
            result = await orch.search_all(query)

        assert len(result.records) == 2
        assert "pncp" in result.sources_used
        assert "comprasgov" in result.sources_used
        assert result.dedup_removed == 0
        assert result.source_stats["pncp"].status == "success"
        assert result.source_stats["comprasgov"].status == "success"

    @pytest.mark.asyncio
    async def test_parallel_execution_is_concurrent(self, query):
        """Verify sources run concurrently (total time ~ max(delays), not sum)."""
        r1 = _make_record(source="src1", numero="001/2025", cnpj="11111111000111")
        r2 = _make_record(source="src2", numero="002/2025", cnpj="22222222000122")

        src1 = FakeSource("src1", [r1], delay=0.1)
        src2 = FakeSource("src2", [r2], delay=0.1)

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["src1", "src2"]):
            start = time.monotonic()
            result = await orch.search_all(query)
            elapsed = time.monotonic() - start

        assert len(result.records) == 2
        # If truly parallel, elapsed should be ~0.1s, not ~0.2s
        assert elapsed < 0.18, f"Expected concurrent execution but took {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# MultiSourceOrchestrator — Timeout
# ---------------------------------------------------------------------------


class TestOrchestratorTimeout:
    """Test per-source timeout handling."""

    @pytest.mark.asyncio
    async def test_slow_source_times_out(self, query):
        """AC4+5: Slow source times out, others continue normally."""
        r1 = _make_record(source="fast", numero="001/2025", cnpj="11111111000111")

        fast = FakeSource("fast", [r1], delay=0)
        slow = FakeSource("slow", [], delay=5.0)  # Will timeout

        orch = MultiSourceOrchestrator(sources=[fast, slow])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["fast", "slow"]):
            with patch.dict(
                "sources.orchestrator.SOURCES_CONFIG",
                {"fast": {"timeout": 30, "priority": 1}, "slow": {"timeout": 0.1, "priority": 2}},
            ):
                result = await orch.search_all(query)

        assert len(result.records) == 1
        assert result.records[0].source == "fast"
        assert "fast" in result.sources_used
        assert "slow" not in result.sources_used
        assert result.source_stats["slow"].status == "timeout"
        assert result.source_stats["fast"].status == "success"


# ---------------------------------------------------------------------------
# MultiSourceOrchestrator — Graceful degradation
# ---------------------------------------------------------------------------


class TestOrchestratorGracefulDegradation:
    """Test that failed sources don't block others."""

    @pytest.mark.asyncio
    async def test_one_source_fails_others_continue(self, query):
        """AC5+6: If one source raises, the rest return normally."""
        r1 = _make_record(source="good", numero="001/2025", cnpj="11111111000111")

        good = FakeSource("good", [r1])
        bad = FakeSource("bad", error=ConnectionError("API down"))

        orch = MultiSourceOrchestrator(sources=[good, bad])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["good", "bad"]):
            result = await orch.search_all(query)

        assert len(result.records) == 1
        assert "good" in result.sources_used
        assert "bad" not in result.sources_used
        assert result.source_stats["bad"].status == "error"
        assert "API down" in result.source_stats["bad"].error_message

    @pytest.mark.asyncio
    async def test_all_sources_fail(self, query):
        """Edge case: all sources fail — returns empty result gracefully."""
        bad1 = FakeSource("src1", error=ConnectionError("fail1"))
        bad2 = FakeSource("src2", error=RuntimeError("fail2"))

        orch = MultiSourceOrchestrator(sources=[bad1, bad2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["src1", "src2"]):
            result = await orch.search_all(query)

        assert len(result.records) == 0
        assert len(result.sources_used) == 0
        assert result.source_stats["src1"].status == "error"
        assert result.source_stats["src2"].status == "error"


# ---------------------------------------------------------------------------
# MultiSourceOrchestrator — Deduplication
# ---------------------------------------------------------------------------


class TestOrchestratorDedup:
    """Test composite-key deduplication."""

    @pytest.mark.asyncio
    async def test_duplicate_records_merged(self, query):
        """AC8: Same CNPJ+numero from two sources -> merged into one."""
        r_pncp = _make_record(
            source="pncp", numero="001/2025", cnpj="12345678000190",
            status="Aberto",
        )
        r_compras = _make_record(
            source="comprasgov", numero="001/2025", cnpj="12345678000190",
            url_edital="http://edital.gov.br",
        )

        src1 = FakeSource("pncp", [r_pncp])
        src2 = FakeSource("comprasgov", [r_compras])

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp", "comprasgov"]):
            result = await orch.search_all(query)

        assert len(result.records) == 1
        assert result.dedup_removed == 1
        merged = result.records[0]
        # Sources aggregated
        assert "pncp" in merged.sources
        assert "comprasgov" in merged.sources
        # PNCP preferred as primary source
        assert merged.source == "pncp"
        # Fields merged from both
        assert merged.status == "Aberto"  # from PNCP
        assert merged.url_edital == "http://edital.gov.br"  # from comprasgov

    @pytest.mark.asyncio
    async def test_dedup_prefers_pncp_as_primary(self, query):
        """AC9: Even if comprasgov is more complete, source stays 'pncp'."""
        # PNCP record with fewer fields
        r_pncp = _make_record(
            source="pncp", numero="001/2025", cnpj="12345678000190",
        )
        # Comprasgov with more fields filled
        r_compras = _make_record(
            source="comprasgov", numero="001/2025", cnpj="12345678000190",
            status="Aberto", url_edital="http://edital.gov.br",
            url_fonte="http://compras.gov.br/001",
        )

        src1 = FakeSource("pncp", [r_pncp])
        src2 = FakeSource("comprasgov", [r_compras])

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp", "comprasgov"]):
            result = await orch.search_all(query)

        assert result.records[0].source == "pncp"
        # But fields are enriched from comprasgov
        assert result.records[0].status == "Aberto"
        assert result.records[0].url_edital == "http://edital.gov.br"

    @pytest.mark.asyncio
    async def test_dedup_fallback_key(self, query):
        """AC10: When CNPJ/numero missing, fallback to objeto+uf+data."""
        pub_date = datetime(2025, 1, 15)
        r1 = _make_record(
            source="pncp", numero="", cnpj="",
            objeto="Aquisicao de uniformes para escola",
            uf="SP", data_pub=pub_date, record_id="pncp1",
        )
        r2 = _make_record(
            source="querido_diario", numero="", cnpj="",
            objeto="Aquisicao de uniformes para escola",
            uf="SP", data_pub=pub_date, record_id="qd1",
        )

        src1 = FakeSource("pncp", [r1])
        src2 = FakeSource("querido_diario", [r2])

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp", "querido_diario"]):
            result = await orch.search_all(query)

        assert len(result.records) == 1
        assert result.dedup_removed == 1

    @pytest.mark.asyncio
    async def test_no_duplicates_no_removal(self, query):
        """Distinct records are not deduplicated."""
        r1 = _make_record(source="pncp", numero="001/2025", cnpj="11111111000111")
        r2 = _make_record(source="comprasgov", numero="002/2025", cnpj="22222222000122")

        src1 = FakeSource("pncp", [r1])
        src2 = FakeSource("comprasgov", [r2])

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp", "comprasgov"]):
            result = await orch.search_all(query)

        assert len(result.records) == 2
        assert result.dedup_removed == 0


# ---------------------------------------------------------------------------
# Dedup performance
# ---------------------------------------------------------------------------


class TestDedupPerformance:
    """AC11: Dedup must complete in < 50ms for 10,000 records."""

    def test_dedup_10k_records_under_50ms(self):
        """Generate 10k records (5k unique + 5k duplicates) and verify < 50ms."""
        records = []
        # 5000 unique records
        for i in range(5000):
            records.append(_make_record(
                source="pncp",
                numero=f"{i:05d}/2025",
                cnpj=f"{i:014d}",
                record_id=f"pncp_{i}",
            ))
        # 5000 duplicates from different source
        for i in range(5000):
            records.append(_make_record(
                source="comprasgov",
                numero=f"{i:05d}/2025",
                cnpj=f"{i:014d}",
                record_id=f"compras_{i}",
            ))

        orch = MultiSourceOrchestrator(sources=[])

        start = time.monotonic()
        deduped, removed = orch._deduplicate(records)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert len(deduped) == 5000
        assert removed == 5000
        assert elapsed_ms < 50, f"Dedup took {elapsed_ms:.1f}ms (limit: 50ms)"


# ---------------------------------------------------------------------------
# Single source mode
# ---------------------------------------------------------------------------


class TestOrchestratorSingleSource:
    """Test with only one source enabled (default rollout config)."""

    @pytest.mark.asyncio
    async def test_single_source_pncp_only(self, query):
        """AC20: Default config with only PNCP enabled."""
        r1 = _make_record(source="pncp")
        src = FakeSource("pncp", [r1])

        orch = MultiSourceOrchestrator(sources=[src])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp"]):
            result = await orch.search_all(query)

        assert len(result.records) == 1
        assert result.sources_used == ["pncp"]
        assert result.dedup_removed == 0
        assert result.source_stats["pncp"].status == "success"


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------


class TestOrchestratorFeatureFlags:
    """Test source enable/disable via config and env var."""

    @pytest.mark.asyncio
    async def test_disabled_source_not_queried(self, query):
        """AC18: Disabled source is skipped."""
        r1 = _make_record(source="pncp")
        r2 = _make_record(source="disabled_src", numero="999/2025", cnpj="99999999000199")

        src1 = FakeSource("pncp", [r1])
        src2 = FakeSource("disabled_src", [r2])

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        # Only pncp is enabled
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp"]):
            result = await orch.search_all(query)

        assert len(result.records) == 1
        assert "disabled_src" not in result.sources_used
        assert "disabled_src" not in result.source_stats

    @pytest.mark.asyncio
    async def test_env_override_enables_specific_sources(self, query):
        """AC19: ENABLED_SOURCES env var overrides config."""
        r1 = _make_record(source="pncp")
        r2 = _make_record(source="tce_rj", numero="777/2025", cnpj="77777777000177")

        src1 = FakeSource("pncp", [r1])
        src2 = FakeSource("tce_rj", [r2])
        src3 = FakeSource("comprasgov", [_make_record(source="comprasgov")])

        orch = MultiSourceOrchestrator(sources=[src1, src2, src3])
        # Only pncp and tce_rj enabled via env
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp", "tce_rj"]):
            result = await orch.search_all(query)

        assert len(result.records) == 2
        assert "pncp" in result.sources_used
        assert "tce_rj" in result.sources_used
        assert "comprasgov" not in result.sources_used


# ---------------------------------------------------------------------------
# No sources enabled
# ---------------------------------------------------------------------------


class TestOrchestratorNoSources:
    @pytest.mark.asyncio
    async def test_no_sources_returns_empty(self, query):
        """Edge: No sources enabled returns empty OrchestratorResult."""
        orch = MultiSourceOrchestrator(sources=[])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=[]):
            result = await orch.search_all(query)

        assert len(result.records) == 0
        assert len(result.sources_used) == 0
        assert result.dedup_removed == 0


# ---------------------------------------------------------------------------
# Source stats
# ---------------------------------------------------------------------------


class TestSourceStats:
    @pytest.mark.asyncio
    async def test_elapsed_ms_populated(self, query):
        """Verify elapsed_ms is tracked per source."""
        r1 = _make_record(source="pncp")
        src = FakeSource("pncp", [r1], delay=0.05)

        orch = MultiSourceOrchestrator(sources=[src])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp"]):
            result = await orch.search_all(query)

        stats = result.source_stats["pncp"]
        assert stats.elapsed_ms >= 40  # at least ~50ms delay
        assert stats.total_fetched == 1
        assert stats.status == "success"

    @pytest.mark.asyncio
    async def test_after_dedup_counts(self, query):
        """Verify after_dedup counts reflect final record ownership."""
        # 2 records from pncp, 1 is duplicate with comprasgov
        r_pncp_1 = _make_record(source="pncp", numero="001/2025", cnpj="11111111000111")
        r_pncp_2 = _make_record(source="pncp", numero="002/2025", cnpj="22222222000122")
        r_compras = _make_record(source="comprasgov", numero="001/2025", cnpj="11111111000111")

        src1 = FakeSource("pncp", [r_pncp_1, r_pncp_2])
        src2 = FakeSource("comprasgov", [r_compras])

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp", "comprasgov"]):
            result = await orch.search_all(query)

        assert len(result.records) == 2
        assert result.dedup_removed == 1
        # pncp should appear in 2 records (one is merged with comprasgov)
        assert result.source_stats["pncp"].after_dedup == 2
        # comprasgov appears in 1 merged record
        assert result.source_stats["comprasgov"].after_dedup == 1


# ---------------------------------------------------------------------------
# OrchestratorResult / SourceStats dataclasses
# ---------------------------------------------------------------------------


class TestDataclasses:
    def test_source_stats_defaults(self):
        stats = SourceStats()
        assert stats.total_fetched == 0
        assert stats.after_dedup == 0
        assert stats.elapsed_ms == 0
        assert stats.status == "success"
        assert stats.error_message is None

    def test_orchestrator_result_defaults(self):
        result = OrchestratorResult()
        assert result.records == []
        assert result.source_stats == {}
        assert result.dedup_removed == 0
        assert result.sources_used == []


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------


class TestProgressCallback:
    @pytest.mark.asyncio
    async def test_on_progress_called(self, query):
        """AC16: Progress callback receives sources_completed/sources_total."""
        r1 = _make_record(source="pncp")

        src = FakeSource("pncp", [r1])
        progress_calls = []

        def on_progress(completed, total):
            progress_calls.append((completed, total))

        orch = MultiSourceOrchestrator(sources=[src])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp"]):
            await orch.search_all(query, on_progress=on_progress)

        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1)

    @pytest.mark.asyncio
    async def test_on_progress_multiple_sources(self, query):
        """Progress callback called once per source."""
        src1 = FakeSource("pncp", [_make_record(source="pncp")])
        src2 = FakeSource("comprasgov", [_make_record(source="comprasgov", numero="002/2025", cnpj="22222222000122")])

        progress_calls = []

        def on_progress(completed, total):
            progress_calls.append((completed, total))

        orch = MultiSourceOrchestrator(sources=[src1, src2])
        with patch("sources.orchestrator.get_enabled_source_names", return_value=["pncp", "comprasgov"]):
            await orch.search_all(query, on_progress=on_progress)

        assert len(progress_calls) == 2
        totals = [t for _, t in progress_calls]
        assert all(t == 2 for t in totals)


# ---------------------------------------------------------------------------
# Merge fields
# ---------------------------------------------------------------------------


class TestMergeFields:
    def test_fills_missing_fields(self):
        target = _make_record(source="pncp", status=None, url_edital=None)
        donor = _make_record(source="comprasgov", status="Aberto", url_edital="http://x.com")

        MultiSourceOrchestrator._merge_fields(target, donor)

        assert target.status == "Aberto"
        assert target.url_edital == "http://x.com"

    def test_does_not_overwrite_existing(self):
        target = _make_record(source="pncp", status="Encerrado")
        donor = _make_record(source="comprasgov", status="Aberto")

        MultiSourceOrchestrator._merge_fields(target, donor)

        assert target.status == "Encerrado"  # Not overwritten

    def test_fills_valor_when_none(self):
        target = _make_record(source="pncp", valor=None)
        donor = _make_record(source="comprasgov", valor=50000.0)

        MultiSourceOrchestrator._merge_fields(target, donor)

        assert target.valor_estimado == 50000.0
