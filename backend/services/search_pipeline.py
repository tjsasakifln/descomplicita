"""Search pipeline execution logic (extracted from main.py)."""

import asyncio
import logging
import time

from error_codes import ErrorCode
from exceptions import PNCPAPIError, PNCPRateLimitError
from sectors import get_sector
from sources.base import SearchQuery

logger = logging.getLogger(__name__)


async def execute_search_pipeline(
    job_id,
    request,
    job_store,
    orchestrator,
    database,
    *,
    filter_batch_fn,
    gerar_resumo_fn,
    gerar_resumo_fallback_fn,
    create_excel_fn,
    parse_multi_word_terms_fn,
    filter_executor,
    enable_streaming_download,
):
    """Execute the full search pipeline as a background async task.

    Dependencies are passed as parameters to allow monkeypatching from tests
    via the thin wrapper in main.py.
    """
    loop = asyncio.get_running_loop()
    _search_start = time.time()

    try:
        # --- Validate sector ---
        try:
            sector = get_sector(request.setor_id)
        except KeyError as e:
            await job_store.fail(job_id, f"Setor invalido: {e}")
            return

        logger.info(
            "[job=%s] Using sector: %s (%s keywords)",
            job_id,
            sector.name,
            len(sector.keywords),
        )

        # --- Parse search terms (UXD-001: multi-word support) ---
        custom_terms: list[str] = []
        if request.termos_busca and request.termos_busca.strip():
            custom_terms = parse_multi_word_terms_fn(request.termos_busca)

        if custom_terms:
            active_keywords = set(custom_terms)
            logger.info(
                "[job=%s] Using %s custom search terms: %s",
                job_id,
                len(custom_terms),
                custom_terms,
            )
        else:
            active_keywords = set(sector.keywords)
            logger.info(
                "[job=%s] Using sector keywords (%s terms)",
                job_id,
                len(active_keywords),
            )

        # --- Phase: fetching ---
        enabled = orchestrator.enabled_sources
        sources_total = len(enabled)

        await job_store.update_progress(
            job_id,
            phase="fetching",
            ufs_total=len(request.ufs),
            sources_total=sources_total,
        )

        source_names = [s.source_name for s in enabled]
        logger.info(
            "[job=%s] Fetching bids from %s sources: %s",
            job_id,
            sources_total,
            source_names,
        )

        query = SearchQuery(
            data_inicial=request.data_inicial,
            data_final=request.data_final,
            ufs=request.ufs,
        )

        orch_result = await orchestrator.search_all(
            query,
            on_progress=lambda c, t: asyncio.ensure_future(
                job_store.update_progress(
                    job_id,
                    sources_completed=c,
                    sources_total=t,
                )
            ),
        )

        licitacoes_raw = [r.to_legacy_dict() for r in orch_result.records]

        logger.info(
            "[job=%s] Fetched %s records from %s sources (%s duplicates removed)",
            job_id,
            len(licitacoes_raw),
            len(orch_result.sources_used),
            orch_result.dedup_removed,
        )

        # --- Phase: filtering ---
        await job_store.update_progress(job_id, phase="filtering", items_fetched=len(licitacoes_raw))

        logger.info("[job=%s] Applying filters to raw bids", job_id)

        # TD-L06: Use dedicated executor for CPU-bound filtering
        licitacoes_filtradas, stats = await loop.run_in_executor(
            filter_executor,
            lambda: filter_batch_fn(
                licitacoes_raw,
                ufs_selecionadas=set(request.ufs),
                valor_min=sector.valor_min,
                valor_max=sector.valor_max,
                keywords=active_keywords,
                exclusions=sector.exclusions,
                keywords_a=sector.keywords_a if not custom_terms else None,
                keywords_b=sector.keywords_b if not custom_terms else None,
                keywords_c=sector.keywords_c if not custom_terms else None,
                threshold=sector.threshold if not custom_terms else 0.6,
            ),
        )

        # Store filtered items for paginated retrieval (TD-M02)
        await job_store.store_items(job_id, licitacoes_filtradas)

        logger.info(
            "[job=%s] Filtering complete: %s/%s bids passed",
            job_id,
            len(licitacoes_filtradas),
            len(licitacoes_raw),
        )
        if stats:
            logger.info("[job=%s]   - Total processadas: %s", job_id, stats.get("total", len(licitacoes_raw)))
            logger.info("[job=%s]   - Aprovadas: %s", job_id, stats.get("aprovadas", len(licitacoes_filtradas)))
            logger.info("[job=%s]   - Rejeitadas (UF): %s", job_id, stats.get("rejeitadas_uf", 0))
            logger.info("[job=%s]   - Rejeitadas (Valor): %s", job_id, stats.get("rejeitadas_valor", 0))
            logger.info("[job=%s]   - Rejeitadas (Keyword): %s", job_id, stats.get("rejeitadas_keyword", 0))
            logger.info("[job=%s]   - Rejeitadas (Prazo): %s", job_id, stats.get("rejeitadas_prazo", 0))
            logger.info("[job=%s]   - Rejeitadas (Outros): %s", job_id, stats.get("rejeitadas_outros", 0))

        fs = {
            "rejeitadas_uf": stats.get("rejeitadas_uf", 0),
            "rejeitadas_valor": stats.get("rejeitadas_valor", 0),
            "rejeitadas_keyword": stats.get("rejeitadas_keyword", 0),
            "rejeitadas_prazo": stats.get("rejeitadas_prazo", 0),
            "rejeitadas_outros": stats.get("rejeitadas_outros", 0),
        }

        total_atas = sum(1 for lic in licitacoes_filtradas if lic.get("tipo") == "ata_registro_preco")
        total_licitacoes = len(licitacoes_filtradas) - total_atas

        # --- Phase: summarizing ---
        await job_store.update_progress(job_id, phase="summarizing", items_filtered=len(licitacoes_filtradas))

        if not licitacoes_filtradas:
            logger.info(
                "[job=%s] No bids passed filters -- skipping LLM and Excel",
                job_id,
            )
            resumo_dict = {
                "resumo_executivo": (
                    f"Nenhuma licitacao de {sector.name.lower()} encontrada "
                    f"nos estados selecionados para o periodo informado."
                ),
                "total_oportunidades": 0,
                "valor_total": 0.0,
                "destaques": [],
                "alerta_urgencia": None,
            }
            result = {
                "resumo": resumo_dict,
                "total_raw": len(licitacoes_raw),
                "total_filtrado": 0,
                "total_atas": 0,
                "total_licitacoes": 0,
                "filter_stats": fs,
                "sources_used": orch_result.sources_used,
                "source_stats": {
                    k: {
                        "total_fetched": v.total_fetched,
                        "after_dedup": v.after_dedup,
                        "elapsed_ms": v.elapsed_ms,
                        "status": v.status,
                        "error_message": v.error_message,
                    }
                    for k, v in orch_result.source_stats.items()
                },
                "dedup_removed": orch_result.dedup_removed,
                "truncated_combos": orch_result.truncated_combos,
                "export_limited": False,
                "excel_item_limit": None,
            }
            await job_store.complete(job_id, result)
            logger.info(
                "[job=%s] Search completed with 0 results",
                job_id,
                extra={"total_raw": len(licitacoes_raw), "total_filtrado": 0},
            )
            return

        # TD-H03: gerar_resumo is now async (uses AsyncOpenAI natively)
        async def _generate_resumo():
            try:
                r = await gerar_resumo_fn(licitacoes_filtradas, sector_name=sector.name)
                logger.info("[job=%s] LLM summary generated successfully", job_id)
                return r
            except Exception as e:
                logger.warning(
                    "[job=%s] LLM generation failed, using fallback: %s",
                    job_id,
                    e,
                    exc_info=True,
                )
                r = gerar_resumo_fallback_fn(licitacoes_filtradas, sector_name=sector.name)
                logger.info("[job=%s] Fallback summary generated successfully", job_id)
                return r

        # v3-story-2.2: Limit Excel to 10K items for memory safety
        from excel import EXCEL_ITEM_LIMIT

        excel_items = licitacoes_filtradas[:EXCEL_ITEM_LIMIT]
        export_limited = len(licitacoes_filtradas) > EXCEL_ITEM_LIMIT

        if export_limited:
            logger.info(
                "[job=%s] Excel limited to %d items (total: %d) -- CSV available for full dataset",
                job_id,
                EXCEL_ITEM_LIMIT,
                len(licitacoes_filtradas),
            )

        def _generate_excel():
            buf = create_excel_fn(excel_items)
            excel_bytes = buf.read()
            logger.info("[job=%s] Excel report generated (%s bytes)", job_id, len(excel_bytes))
            return excel_bytes

        logger.info("[job=%s] Generating LLM summary + Excel report in parallel", job_id)

        await job_store.update_progress(job_id, phase="generating_excel")

        # TD-H03: LLM is now fully async, Excel still runs in executor
        resumo_coro = _generate_resumo()
        excel_future = loop.run_in_executor(filter_executor, _generate_excel)
        resumo, excel_bytes = await asyncio.gather(resumo_coro, excel_future)

        actual_total = len(licitacoes_filtradas)
        actual_valor = sum(lic.get("valorTotalEstimado", 0) or 0 for lic in licitacoes_filtradas)
        if resumo.total_oportunidades != actual_total:
            logger.warning(
                "[job=%s] LLM returned total_oportunidades=%s, overriding with actual=%s",
                job_id,
                resumo.total_oportunidades,
                actual_total,
            )
        resumo.total_oportunidades = actual_total
        resumo.valor_total = actual_valor

        # Defensive: if LLM resumo_executivo contradicts actual results, use fallback
        if actual_total > 0 and "nenhuma" in resumo.resumo_executivo.lower():
            logger.warning(
                "[job=%s] LLM resumo_executivo says 'nenhuma' but %s results exist, replacing with fallback",
                job_id,
                actual_total,
            )
            fallback = gerar_resumo_fallback_fn(licitacoes_filtradas, sector_name=sector.name)
            resumo.resumo_executivo = fallback.resumo_executivo
            resumo.destaques = fallback.destaques
            resumo.alerta_urgencia = fallback.alerta_urgencia

        resumo_dict = resumo.model_dump()

        # TD-C01/XD-PERF-01: Store Excel bytes separately to avoid memory duplication
        if enable_streaming_download:
            await job_store.store_excel(job_id, excel_bytes)

        result = {
            "resumo": resumo_dict,
            "total_raw": len(licitacoes_raw),
            "total_filtrado": len(licitacoes_filtradas),
            "total_atas": total_atas,
            "total_licitacoes": total_licitacoes,
            "filter_stats": fs,
            "sources_used": orch_result.sources_used,
            "source_stats": {
                k: {
                    "total_fetched": v.total_fetched,
                    "after_dedup": v.after_dedup,
                    "elapsed_ms": v.elapsed_ms,
                    "status": v.status,
                    "error_message": v.error_message,
                }
                for k, v in orch_result.source_stats.items()
            },
            "dedup_removed": orch_result.dedup_removed,
            "truncated_combos": orch_result.truncated_combos,
            "export_limited": export_limited,
            "excel_item_limit": EXCEL_ITEM_LIMIT if export_limited else None,
        }

        # Legacy fallback: include excel_bytes in result if streaming is disabled
        if not enable_streaming_download:
            result["excel_bytes"] = excel_bytes

        await job_store.complete(job_id, result)

        # TD-H04: Record completion in persistent database
        if database:
            await database.complete_search(
                job_id=job_id,
                total_raw=len(licitacoes_raw),
                total_filtrado=len(licitacoes_filtradas),
                elapsed_seconds=time.time() - _search_start,
            )

        logger.info(
            "[job=%s] Search completed successfully",
            job_id,
            extra={
                "total_raw": len(licitacoes_raw),
                "total_filtrado": len(licitacoes_filtradas),
                "valor_total": actual_valor,
            },
        )

    except PNCPRateLimitError as e:
        logger.error("[job=%s] PNCP rate limit exceeded: %s", job_id, e, exc_info=True)
        retry_after = getattr(e, "retry_after", 60)
        err = ErrorCode.PNCP_RATE_LIMITED.to_dict(
            message=f"O PNCP esta limitando requisicoes. Aguarde {retry_after} segundos e tente novamente.",
            details={"retry_after": retry_after},
        )
        await job_store.fail(job_id, err["error"]["message"])
        if database:
            await database.fail_search(job_id)

    except PNCPAPIError as e:
        logger.error("[job=%s] PNCP API error: %s", job_id, e, exc_info=True)
        err = ErrorCode.PNCP_UNAVAILABLE.to_dict()
        await job_store.fail(job_id, err["error"]["message"])
        if database:
            await database.fail_search(job_id)

    except Exception:
        logger.exception("[job=%s] Internal server error during search", job_id)
        err = ErrorCode.INTERNAL_ERROR.to_dict()
        await job_store.fail(job_id, err["error"]["message"])
        if database:
            await database.fail_search(job_id)
