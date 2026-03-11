"use client";

import { useCallback, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import { useAnalytics } from "../hooks/useAnalytics";
import { useSavedSearches } from "../hooks/useSavedSearches";
import { useSearchForm } from "./hooks/useSearchForm";
import { useSearchJob } from "./hooks/useSearchJob";
import { useSaveDialog } from "./hooks/useSaveDialog";
import { SearchHeader } from "./components/SearchHeader";
import { SearchForm } from "./components/SearchForm";
import { UfSelector } from "./components/UfSelector";
import { DateRangeSelector } from "./components/DateRangeSelector";
import { LargeVolumeWarning } from "./components/LargeVolumeWarning";
import { SearchSummary } from "./components/SearchSummary";
import { SearchActions } from "./components/SearchActions";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Button } from "./components/Button";
import { Footer } from "./components/Footer";
import type { SavedSearch } from "../lib/savedSearches";
import { dateDiffInDays } from "../lib/utils";

// Task 15 (TD-042): Dynamic imports for heavy components
const SaveSearchDialog = dynamic(
  () => import("./components/SaveSearchDialog").then(mod => ({ default: mod.SaveSearchDialog })),
  { ssr: false }
);

const LoadingProgress = dynamic(
  () => import("./components/LoadingProgress").then(mod => ({ default: mod.LoadingProgress })),
  { loading: () => (
    <div className="mt-8 p-6 bg-surface-1 rounded-card border animate-fade-in-up">
      <div className="h-2 bg-surface-2 rounded-full overflow-hidden">
        <div className="h-full w-1/4 bg-gradient-to-r from-brand-blue to-brand-navy rounded-full animate-pulse" />
      </div>
      <p className="text-sm text-ink-muted mt-3">Carregando...</p>
    </div>
  )}
);

const EmptyState = dynamic(
  () => import("./components/EmptyState").then(mod => ({ default: mod.EmptyState })),
  { loading: () => <div className="mt-6 p-6 bg-surface-1 rounded-card border animate-fade-in text-center text-ink-muted text-sm">Carregando...</div> }
);

const ItemsList = dynamic(
  () => import("./components/ItemsList").then(mod => ({ default: mod.ItemsList })),
  { loading: () => <div className="mt-4 p-6 bg-surface-1 rounded-card border animate-fade-in text-center text-ink-muted text-sm">Carregando lista...</div> }
);

export default function HomePage() {
  const { trackEvent } = useAnalytics();
  const { saveNewSearch, isMaxCapacity } = useSavedSearches();
  const job = useSearchJob(trackEvent);
  const form = useSearchForm(job.clearResult);
  const save = useSaveDialog({ form, saveNewSearch, trackEvent, hasResult: !!job.result });

  // Task 2 (TD-031): Focus management after search
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);
  const prevResultRef = useRef<typeof job.result>(null);

  useEffect(() => {
    // When results arrive (transition from null to having a result), focus the results heading
    if (job.result && !prevResultRef.current) {
      // Small delay to allow DOM to render
      requestAnimationFrame(() => {
        resultsHeadingRef.current?.focus();
        resultsHeadingRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
    prevResultRef.current = job.result;
  }, [job.result]);

  const handleBuscar = useCallback(async () => {
    await job.buscar({
      ufs: Array.from(form.ufsSelecionadas),
      dataInicial: form.dataInicial,
      dataFinal: form.dataFinal,
      searchMode: form.searchMode,
      setorId: form.setorId,
      termosArray: form.termosArray,
    });
  }, [job, form.ufsSelecionadas, form.dataInicial, form.dataFinal, form.searchMode, form.setorId, form.termosArray]);

  // UXD-004: Ctrl+Enter keyboard shortcut to submit search
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && form.canSearch && !job.loading) {
        e.preventDefault();
        handleBuscar();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleBuscar, form.canSearch, job.loading]);

  const handleDownload = useCallback(async () => {
    if (!job.result?.download_id) return;
    await job.handleDownload({
      downloadId: job.result.download_id,
      sectorName: form.sectorName,
      dataInicial: form.dataInicial,
      dataFinal: form.dataFinal,
    });
  }, [job, form.sectorName, form.dataInicial, form.dataFinal]);

  const handleDownloadCsv = useCallback(async () => {
    if (!job.result?.download_id) return;
    await job.handleDownloadCsv({
      downloadId: job.result.download_id,
      sectorName: form.sectorName,
      dataInicial: form.dataInicial,
      dataFinal: form.dataFinal,
    });
  }, [job, form.sectorName, form.dataInicial, form.dataFinal]);

  const handleLoadSearch = useCallback((search: SavedSearch) => {
    form.loadSearchParams(search.searchParams);
  }, [form]);

  const hasResults = job.result && job.result.resumo.total_oportunidades > 0;
  const isEmpty = job.result && job.result.resumo.total_oportunidades === 0;

  // Task 2: Announce result count for screen readers
  const resultAnnouncement = hasResults
    ? `${job.result!.resumo.total_oportunidades} resultados encontrados`
    : isEmpty
      ? "Nenhum resultado encontrado"
      : "";

  return (
    <div className="min-h-screen">
      <SearchHeader onLoadSearch={handleLoadSearch} onAnalyticsEvent={trackEvent} />

      <main id="main-content" className="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        <div className="mb-8 animate-fade-in-up">
          <h1 className="text-2xl sm:text-3xl font-bold font-display text-ink">Busca de Licitações</h1>
          <p className="text-ink-secondary mt-1 text-sm sm:text-base">Encontre oportunidades de contratação pública em fontes oficiais</p>
        </div>

        <h2 className="sr-only">Formulário de Busca</h2>
        <ErrorBoundary>
        <SearchForm searchMode={form.searchMode} onSearchModeChange={form.setSearchMode} setores={form.setores}
          setoresLoading={form.setoresLoading} setorId={form.setorId} onSetorIdChange={form.setSetorId} termosArray={form.termosArray}
          onTermosArrayChange={form.setTermosArray} termoInput={form.termoInput}
          onTermoInputChange={form.setTermoInput} onFormChange={job.clearResult} />

        <UfSelector ufsSelecionadas={form.ufsSelecionadas} onToggleUf={form.toggleUf}
          onToggleRegion={form.toggleRegion} onSelecionarTodos={form.selecionarTodos}
          onLimparSelecao={form.limparSelecao} validationErrors={form.validationErrors} />

        <DateRangeSelector dataInicial={form.dataInicial} dataFinal={form.dataFinal}
          onDataInicialChange={form.setDataInicial} onDataFinalChange={form.setDataFinal}
          validationErrors={form.validationErrors} />

        <LargeVolumeWarning
          ufCount={form.ufsSelecionadas.size}
          dateRangeDays={dateDiffInDays(form.dataInicial, form.dataFinal)}
        />
        </ErrorBoundary>

        <Button onClick={handleBuscar} disabled={!form.canSearch} loading={job.loading} type="button"
          size="lg" className="w-full sm:py-4 text-base sm:text-lg font-semibold" aria-busy={job.loading}>
          {job.loading ? "Buscando..." : `Buscar ${form.searchLabel}`}
        </Button>

        {job.loading && (
          <div aria-live="polite">
            <LoadingProgress phase={job.searchPhase} ufsCompleted={job.ufsCompleted} ufsTotal={job.ufsTotal}
              itemsFetched={job.itemsFetched} itemsFiltered={job.itemsFiltered} elapsedSeconds={job.elapsedSeconds}
              onCancel={job.handleCancel} selectedUfs={Array.from(form.ufsSelecionadas)}
              sectorId={form.searchMode === "setor" ? form.setorId : undefined} />
          </div>
        )}

        {job.error && (
          <div className="mt-6 sm:mt-8 p-4 sm:p-5 bg-error-subtle border border-error/20 rounded-card animate-fade-in-up" role="alert">
            <p className="text-sm sm:text-base font-medium text-error mb-3">{job.error}</p>
            <Button onClick={handleBuscar} disabled={job.loading} variant="danger" size="sm">
              Tentar novamente
            </Button>
          </div>
        )}

        {/* Task 2 (TD-031): aria-live region for result announcements */}
        <div aria-live="polite" className="sr-only" role="status">
          {resultAnnouncement}
        </div>

        <h2
          ref={resultsHeadingRef}
          tabIndex={-1}
          className="sr-only outline-none"
        >
          Resultados
        </h2>

        <ErrorBoundary>
        {isEmpty && (
          <EmptyState onAdjustSearch={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            rawCount={job.rawCount} stateCount={form.ufsSelecionadas.size}
            filterStats={job.result!.filter_stats} sectorName={form.sectorName} />
        )}

        {hasResults && (
          <div className="mt-6 sm:mt-8 space-y-4 sm:space-y-6 animate-fade-in-up">
            <SearchSummary result={job.result!} completedAt={job.completedAt ?? undefined} />
            <ItemsList jobId={job.result!.download_id} totalFiltered={job.result!.total_filtrado} />
            <SearchActions result={job.result!} rawCount={job.rawCount} sectorName={form.sectorName}
              downloadLoading={job.downloadLoading} downloadError={job.downloadError}
              isMaxCapacity={isMaxCapacity} onDownload={handleDownload} onDownloadCsv={handleDownloadCsv}
              onSaveSearch={save.handleSaveSearch} />
          </div>
        )}
        </ErrorBoundary>
      </main>

      {save.showSaveDialog && (
        <SaveSearchDialog saveSearchName={save.saveSearchName} onNameChange={save.setSaveSearchName}
          onConfirm={save.confirmSaveSearch} onCancel={save.cancelSaveDialog} saveError={save.saveError} />
      )}

      <Footer />
    </div>
  );
}
