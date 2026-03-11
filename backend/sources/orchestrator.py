"""Multi-Source Orchestrator — Parallel search + deduplication (MS-001.6)."""

import asyncio
import hashlib
import logging
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Optional

from config import SOURCES_CONFIG
from sources.base import DataSourceClient, NormalizedRecord, SearchQuery

logger = logging.getLogger(__name__)

# Source priority (lower = higher priority). PNCP is canonical.
_SOURCE_PRIORITY = {name: cfg["priority"] for name, cfg in SOURCES_CONFIG.items()}


@dataclass
class SourceStats:
    """Per-source statistics from an orchestrated search."""

    total_fetched: int = 0
    after_dedup: int = 0
    elapsed_ms: int = 0
    status: str = "success"  # "success" | "error" | "timeout"
    error_message: Optional[str] = None


@dataclass
class OrchestratorResult:
    """Unified result from a multi-source parallel search."""

    records: list[NormalizedRecord] = field(default_factory=list)
    source_stats: dict[str, SourceStats] = field(default_factory=dict)
    dedup_removed: int = 0
    sources_used: list[str] = field(default_factory=list)
    truncated_combos: int = 0


def get_enabled_source_names() -> list[str]:
    """Return list of enabled source names, respecting ENABLED_SOURCES env override.

    If ENABLED_SOURCES env var is set (comma-separated), use it as override.
    Otherwise, return sources where SOURCES_CONFIG[name]["enabled"] is True.
    Default when neither is set: only "pncp".
    """
    env_override = os.environ.get("ENABLED_SOURCES", "").strip()
    if env_override:
        return [s.strip() for s in env_override.split(",") if s.strip()]
    return [name for name, cfg in SOURCES_CONFIG.items() if cfg.get("enabled", False)]


# ---------------------------------------------------------------------------
# Normalization helpers for dedup keys
# ---------------------------------------------------------------------------

_RE_NON_ALNUM = re.compile(r"[^a-z0-9]")


def _normalize_str(value: Optional[str]) -> str:
    """Lowercase, strip, and remove non-alphanumeric chars."""
    if not value:
        return ""
    return _RE_NON_ALNUM.sub("", value.lower().strip())


def _extract_year(record: NormalizedRecord) -> str:
    """Extract year from numero_licitacao or data_publicacao."""
    # Try extracting year from numero (e.g., "00012/2025")
    if record.numero_licitacao:
        match = re.search(r"(\d{4})", record.numero_licitacao)
        if match:
            year = match.group(1)
            if 2000 <= int(year) <= 2099:
                return year
    # Fallback to data_publicacao
    if record.data_publicacao:
        return str(record.data_publicacao.year)
    return ""


def _dedup_key_primary(record: NormalizedRecord) -> Optional[str]:
    """Primary dedup key: hash(normalize(cnpj_orgao) + normalize(numero_licitacao) + ano)."""
    cnpj = _normalize_str(record.cnpj_orgao)
    numero = _normalize_str(record.numero_licitacao)
    if not cnpj or not numero:
        return None
    ano = _extract_year(record)
    raw_key = f"{cnpj}|{numero}|{ano}"
    return hashlib.md5(raw_key.encode()).hexdigest()


def _dedup_key_fallback(record: NormalizedRecord) -> Optional[str]:
    """Fallback dedup key: hash(normalize(objeto[:100]) + uf + data_publicacao)."""
    objeto = _normalize_str((record.objeto or "")[:100])
    uf = _normalize_str(record.uf)
    data = ""
    if record.data_publicacao:
        data = record.data_publicacao.strftime("%Y-%m-%d")
    if not objeto:
        return None
    raw_key = f"{objeto}|{uf}|{data}"
    return hashlib.md5(raw_key.encode()).hexdigest()


def _dedup_key(record: NormalizedRecord) -> str:
    """Compute dedup key with primary strategy, falling back if needed."""
    key = _dedup_key_primary(record)
    if key:
        return key
    key = _dedup_key_fallback(record)
    if key:
        return "fb_" + key  # prefix to avoid collisions with primary keys
    # Absolute fallback: use record's own id
    return "id_" + record.id


def _count_filled_fields(record: NormalizedRecord) -> int:
    """Count non-None, non-empty fields for completeness comparison."""
    count = 0
    for fld in (
        record.numero_licitacao,
        record.objeto,
        record.orgao,
        record.cnpj_orgao,
        record.uf,
        record.municipio,
        record.modalidade,
        record.status,
        record.url_edital,
        record.url_fonte,
    ):
        if fld:
            count += 1
    for fld in (record.valor_estimado, record.modalidade_codigo):
        if fld is not None:
            count += 1
    for fld in (record.data_publicacao, record.data_abertura):
        if fld is not None:
            count += 1
    return count


def _source_priority(source_name: str) -> int:
    """Return numeric priority for a source (lower = higher priority)."""
    return _SOURCE_PRIORITY.get(source_name.lower(), _SOURCE_PRIORITY.get(source_name, 999))


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class MultiSourceOrchestrator:
    """Orchestrates parallel search across multiple DataSourceClient instances.

    Features:
    - Parallel fetch with per-source timeout
    - Graceful degradation (failed sources don't block others)
    - Composite-key deduplication with source aggregation
    - Feature flags via SOURCES_CONFIG and ENABLED_SOURCES env var
    """

    def __init__(
        self,
        sources: list[DataSourceClient],
        default_timeout: float = 30.0,
        on_source_complete: Optional[Callable[[str, str], Any]] = None,
    ) -> None:
        self.sources = sources
        self.default_timeout = default_timeout
        self._on_source_complete = on_source_complete

    @property
    def enabled_sources(self) -> list[DataSourceClient]:
        """Return sources filtered by enabled config."""
        enabled_names = {n.lower() for n in get_enabled_source_names()}
        return [s for s in self.sources if s.source_name.lower() in enabled_names]

    async def search_all(
        self,
        query: SearchQuery,
        on_progress: Optional[Callable[[int, int], Any]] = None,
    ) -> OrchestratorResult:
        """Execute parallel search across all enabled sources.

        Args:
            query: Unified search parameters.
            on_progress: Optional callback(sources_completed, sources_total).

        Returns:
            OrchestratorResult with deduplicated records and per-source stats.
        """
        sources = self.enabled_sources
        if not sources:
            logger.warning("No sources enabled — returning empty result")
            return OrchestratorResult()

        sources_total = len(sources)
        logger.info(
            "Starting parallel search across %d sources: %s",
            sources_total,
            [s.source_name for s in sources],
        )

        # Launch all sources in parallel
        tasks = []
        num_ufs = len(query.ufs) if query.ufs else 1
        for source in sources:
            base_timeout = SOURCES_CONFIG.get(source.source_name.lower(), {}).get("timeout", self.default_timeout)
            # Scale timeout for PNCP when many UFs are selected:
            # base 300s is sized for ~3 UFs; add 10s per extra UF beyond 5
            timeout = base_timeout
            if source.source_name.lower() == "pncp" and num_ufs > 5:
                timeout = base_timeout + (num_ufs - 5) * 15
                logger.info(
                    "PNCP timeout scaled %ds → %ds for %d UFs",
                    base_timeout,
                    timeout,
                    num_ufs,
                )
            task = asyncio.create_task(self._fetch_with_timeout(source, query, timeout))
            tasks.append((source.source_name, task))

        # Gather results (return_exceptions=True for graceful degradation)
        results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)

        # Process results
        all_records: list[NormalizedRecord] = []
        source_stats: dict[str, SourceStats] = {}
        sources_used: list[str] = []
        sources_completed = 0

        # Build source lookup for partial result recovery
        source_by_name = {s.source_name: s for s in sources}

        for (name, _), result in zip(tasks, results):
            sources_completed += 1

            if isinstance(result, (asyncio.TimeoutError, asyncio.CancelledError)):
                # Recover partial results from sources that support it
                source = source_by_name.get(name)
                partial = []
                if source and hasattr(source, "get_partial_results"):
                    partial = source.get_partial_results()
                if partial:
                    logger.warning(
                        "Source %s timed out but recovered %d partial results",
                        name,
                        len(partial),
                    )
                    source_stats[name] = SourceStats(
                        total_fetched=len(partial),
                        status="timeout",
                        error_message=f"Timeout — {len(partial)} partial results recovered",
                    )
                    all_records.extend(partial)
                    sources_used.append(name)
                else:
                    logger.error("Source %s timed out with 0 results", name)
                    source_stats[name] = SourceStats(
                        status="timeout",
                        error_message="Timeout after configured limit",
                    )
            elif isinstance(result, Exception):
                logger.error("Source %s failed: %s", name, result)
                source_stats[name] = SourceStats(
                    status="error",
                    error_message=str(result),
                )
            else:
                records, elapsed_ms = result
                logger.info(
                    "Source %s returned %d records in %dms",
                    name,
                    len(records),
                    elapsed_ms,
                )
                source_stats[name] = SourceStats(
                    total_fetched=len(records),
                    elapsed_ms=elapsed_ms,
                    status="success",
                )
                all_records.extend(records)
                sources_used.append(name)

            if on_progress:
                on_progress(sources_completed, sources_total)
            if self._on_source_complete:
                self._on_source_complete(name, source_stats[name].status)

        # Deduplicate
        deduped, dedup_removed = self._deduplicate(all_records)

        # Update after_dedup counts per source
        source_record_counts: dict[str, int] = {}
        for record in deduped:
            for src in record.sources:
                source_record_counts[src] = source_record_counts.get(src, 0) + 1
        for name, stats in source_stats.items():
            stats.after_dedup = source_record_counts.get(name, 0)

        # Collect truncation stats from PNCP source
        truncated = 0
        for source in sources:
            if hasattr(source, "truncated_combos"):
                truncated += source.truncated_combos

        logger.info(
            "Orchestrator complete: %d records from %d sources, %d duplicates removed, %d combos truncated",
            len(deduped),
            len(sources_used),
            dedup_removed,
            truncated,
        )

        return OrchestratorResult(
            records=deduped,
            source_stats=source_stats,
            dedup_removed=dedup_removed,
            sources_used=sources_used,
            truncated_combos=truncated,
        )

    async def _fetch_with_timeout(
        self,
        source: DataSourceClient,
        query: SearchQuery,
        timeout: float,
    ) -> tuple[list[NormalizedRecord], int]:
        """Fetch from a single source with timeout.

        Returns:
            Tuple of (records, elapsed_ms).

        Raises:
            asyncio.TimeoutError: If the source exceeds its timeout.
            Exception: Any error from the source.
        """
        start = time.monotonic()
        records = await asyncio.wait_for(
            source.fetch_records(query),
            timeout=timeout,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return records, elapsed_ms

    def _deduplicate(self, records: list[NormalizedRecord]) -> tuple[list[NormalizedRecord], int]:
        """Deduplicate records by composite key.

        Strategy:
        1. Sort by source priority (PNCP first = canonical).
        2. For each record, compute dedup key.
        3. If key seen: merge sources, keep more complete record.
        4. Prefer PNCP as primary source.

        Returns:
            Tuple of (deduplicated_records, duplicates_removed_count).
        """
        # Sort by priority so PNCP records are processed first
        records.sort(key=lambda r: _source_priority(r.source))

        seen: dict[str, NormalizedRecord] = {}
        duplicates = 0

        for record in records:
            key = _dedup_key(record)
            if key in seen:
                existing = seen[key]
                # Aggregate sources
                for src in record.sources:
                    if src not in existing.sources:
                        existing.sources.append(src)
                # If new record is more complete, swap fields but keep PNCP as primary source
                if _count_filled_fields(record) > _count_filled_fields(existing):
                    primary_source = existing.source  # preserve primary
                    primary_sources = list(existing.sources)  # preserve aggregated sources
                    self._merge_fields(existing, record)
                    existing.source = primary_source
                    existing.sources = primary_sources
                else:
                    # Still fill in any missing fields from the new record
                    self._merge_fields(existing, record)
                duplicates += 1
            else:
                seen[key] = record

        return list(seen.values()), duplicates

    @staticmethod
    def _merge_fields(target: NormalizedRecord, donor: NormalizedRecord) -> None:
        """Fill empty fields in target from donor (does not overwrite existing)."""
        if not target.numero_licitacao and donor.numero_licitacao:
            target.numero_licitacao = donor.numero_licitacao
        if not target.objeto and donor.objeto:
            target.objeto = donor.objeto
        if not target.orgao and donor.orgao:
            target.orgao = donor.orgao
        if not target.cnpj_orgao and donor.cnpj_orgao:
            target.cnpj_orgao = donor.cnpj_orgao
        if not target.uf and donor.uf:
            target.uf = donor.uf
        if not target.municipio and donor.municipio:
            target.municipio = donor.municipio
        if target.valor_estimado is None and donor.valor_estimado is not None:
            target.valor_estimado = donor.valor_estimado
        if not target.modalidade and donor.modalidade:
            target.modalidade = donor.modalidade
        if target.modalidade_codigo is None and donor.modalidade_codigo is not None:
            target.modalidade_codigo = donor.modalidade_codigo
        if target.data_publicacao is None and donor.data_publicacao is not None:
            target.data_publicacao = donor.data_publicacao
        if target.data_abertura is None and donor.data_abertura is not None:
            target.data_abertura = donor.data_abertura
        if not target.status and donor.status:
            target.status = donor.status
        if not target.url_edital and donor.url_edital:
            target.url_edital = donor.url_edital
        if not target.url_fonte and donor.url_fonte:
            target.url_fonte = donor.url_fonte
