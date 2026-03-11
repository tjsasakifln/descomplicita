"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useAnalytics } from "../../../hooks/useAnalytics";
import { SearchHeader } from "../../components/SearchHeader";
import { SearchSummary } from "../../components/SearchSummary";
import { SearchActions } from "../../components/SearchActions";
import { ErrorBoundary } from "../../components/ErrorBoundary";
import { Button } from "../../components/Button";
import { Spinner } from "../../components/Spinner";
import { Footer } from "../../components/Footer";
import type { BuscaResult } from "../../types";
import { correlationHeaders, logger } from "../../../lib/logger";

const ItemsList = dynamic(
  () => import("../../components/ItemsList").then(mod => ({ default: mod.ItemsList })),
  { loading: () => <div className="mt-4 p-6 bg-surface-1 rounded-card border animate-fade-in text-center text-ink-muted text-sm">Carregando lista...</div> },
);

const EmptyState = dynamic(
  () => import("../../components/EmptyState").then(mod => ({ default: mod.EmptyState })),
  { loading: () => <div className="mt-6 p-6 bg-surface-1 rounded-card border animate-fade-in text-center text-ink-muted text-sm">Carregando...</div> },
);

type PageState = "loading" | "completed" | "expired" | "not_found" | "error" | "in_progress";

export default function ResultadoPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const { trackEvent } = useAnalytics();

  const [pageState, setPageState] = useState<PageState>("loading");
  const [result, setResult] = useState<BuscaResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const fetchResult = useCallback(async () => {
    const corrHeaders = correlationHeaders();
    const correlationId = corrHeaders["X-Correlation-Id"];
    logger.info("Fetching deep-link result", { jobId }, correlationId);

    try {
      // First check job status
      const statusRes = await fetch(`/api/buscar/status?job_id=${jobId}`, {
        headers: corrHeaders,
      });

      if (statusRes.status === 404) {
        setPageState("expired");
        trackEvent("deeplink_expired", { job_id: jobId });
        return;
      }

      if (!statusRes.ok) {
        setPageState("error");
        setErrorMessage("Erro ao verificar status da busca");
        return;
      }

      const status = await statusRes.json();

      if (status.status === "completed") {
        // Fetch full result
        const resultRes = await fetch(`/api/buscar/result?job_id=${jobId}`, {
          headers: corrHeaders,
        });

        if (resultRes.status === 404) {
          setPageState("expired");
          return;
        }

        if (!resultRes.ok) {
          setPageState("error");
          setErrorMessage("Erro ao carregar resultados");
          return;
        }

        const data = await resultRes.json();
        setResult(data);
        setPageState("completed");
        trackEvent("deeplink_loaded", { job_id: jobId, total: data.resumo?.total_oportunidades });
      } else if (status.status === "failed") {
        setPageState("error");
        setErrorMessage(status.error || "A busca falhou");
      } else if (status.status === "cancelled") {
        setPageState("expired");
      } else {
        // Still running
        setPageState("in_progress");
      }
    } catch (_e) {
      void _e;
      setPageState("error");
      setErrorMessage("Não foi possível conectar ao servidor");
    }
  }, [jobId, trackEvent]);

  useEffect(() => {
    if (jobId) fetchResult();
  }, [jobId, fetchResult]);

  const handleDownload = useCallback(async () => {
    if (!jobId) return;
    setDownloadLoading(true);
    setDownloadError(null);
    try {
      const res = await fetch(`/api/download?id=${jobId}`, {
        headers: correlationHeaders(),
      });
      if (!res.ok) throw new Error("Download falhou");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `licitacoes-${jobId.slice(0, 8)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      trackEvent("deeplink_download", { job_id: jobId });
    } catch (_e) {
      void _e;
      setDownloadError("Falha no download. Tente novamente.");
    } finally {
      setDownloadLoading(false);
    }
  }, [jobId, trackEvent]);

  const handleDownloadCsv = useCallback(async () => {
    if (!jobId) return;
    setDownloadLoading(true);
    setDownloadError(null);
    try {
      const res = await fetch(`/api/download?id=${jobId}&format=csv`, {
        headers: correlationHeaders(),
      });
      if (!res.ok) throw new Error("Download falhou");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `licitacoes-${jobId.slice(0, 8)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (_e) {
      void _e;
      setDownloadError("Falha no download. Tente novamente.");
    } finally {
      setDownloadLoading(false);
    }
  }, [jobId]);

  const hasResults = result && result.resumo.total_oportunidades > 0;
  const isEmpty = result && result.resumo.total_oportunidades === 0;

  return (
    <div className="min-h-screen">
      <SearchHeader onLoadSearch={() => {}} onAnalyticsEvent={trackEvent} />

      <main id="main-content" className="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        <div className="mb-6 animate-fade-in-up">
          <h1 className="text-2xl sm:text-3xl font-bold font-display text-ink">
            Resultado da Busca
          </h1>
          <p className="text-ink-muted text-sm mt-1 font-mono">{jobId}</p>
        </div>

        {pageState === "loading" && (
          <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
            <Spinner size="lg" />
            <p className="text-ink-muted mt-4">Carregando resultados...</p>
          </div>
        )}

        {pageState === "in_progress" && (
          <div className="p-6 bg-surface-1 rounded-card border animate-fade-in-up text-center">
            <Spinner size="md" className="mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-ink mb-2">Busca em andamento</h2>
            <p className="text-ink-secondary mb-4">
              Esta busca ainda está sendo processada. Volte em alguns instantes.
            </p>
            <Button onClick={fetchResult} variant="secondary" size="sm">
              Verificar novamente
            </Button>
          </div>
        )}

        {pageState === "expired" && (
          <div className="p-8 bg-surface-1 rounded-card border animate-fade-in-up text-center">
            <div className="text-4xl mb-4">⏰</div>
            <h2 className="text-lg font-semibold text-ink mb-2">Resultado expirado</h2>
            <p className="text-ink-secondary mb-6">
              Este resultado não está mais disponível. Os resultados de busca são mantidos temporariamente
              e expiram após um período para economizar recursos.
            </p>
            <Button onClick={() => window.location.href = "/"} variant="primary" size="md">
              Fazer nova busca
            </Button>
          </div>
        )}

        {pageState === "not_found" && (
          <div className="p-8 bg-surface-1 rounded-card border animate-fade-in-up text-center">
            <div className="text-4xl mb-4">🔍</div>
            <h2 className="text-lg font-semibold text-ink mb-2">Resultado não encontrado</h2>
            <p className="text-ink-secondary mb-6">
              Não foi possível encontrar uma busca com este identificador.
            </p>
            <Button onClick={() => window.location.href = "/"} variant="primary" size="md">
              Fazer nova busca
            </Button>
          </div>
        )}

        {pageState === "error" && (
          <div className="p-6 bg-error-subtle border border-error/20 rounded-card animate-fade-in-up" role="alert">
            <p className="text-sm sm:text-base font-medium text-error mb-3">
              {errorMessage || "Erro ao carregar resultados"}
            </p>
            <div className="flex gap-3">
              <Button onClick={fetchResult} variant="danger" size="sm">
                Tentar novamente
              </Button>
              <Button onClick={() => window.location.href = "/"} variant="ghost" size="sm">
                Nova busca
              </Button>
            </div>
          </div>
        )}

        <ErrorBoundary>
          {isEmpty && (
            <EmptyState
              onAdjustSearch={() => window.location.href = "/"}
              rawCount={result!.total_raw || 0}
              stateCount={0}
              filterStats={result!.filter_stats}
              sectorName="Licitações"
            />
          )}

          {hasResults && (
            <div className="mt-6 sm:mt-8 space-y-4 sm:space-y-6 animate-fade-in-up">
              <SearchSummary result={result!} />
              <ItemsList jobId={result!.download_id} totalFiltered={result!.total_filtrado} />
              <SearchActions
                result={result!}
                rawCount={result!.total_raw || 0}
                sectorName="Licitações"
                downloadLoading={downloadLoading}
                downloadError={downloadError}
                isMaxCapacity={false}
                onDownload={handleDownload}
                onDownloadCsv={handleDownloadCsv}
                onSaveSearch={() => {}}
              />
            </div>
          )}
        </ErrorBoundary>
      </main>

      <Footer />
    </div>
  );
}
