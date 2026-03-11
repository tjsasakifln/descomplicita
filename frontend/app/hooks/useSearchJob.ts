import { useState, useEffect, useRef, useCallback } from "react";
import type { BuscaResult, SearchPhase } from "../types";

function dateDiffInDays(date1: string, date2: string): number {
  const d1 = new Date(date1);
  const d2 = new Date(date2);
  const diffTime = Math.abs(d2.getTime() - d1.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

export interface SearchSubmitParams {
  ufs: string[];
  dataInicial: string;
  dataFinal: string;
  searchMode: "setor" | "termos";
  setorId: string;
  termosArray: string[];
}

export interface UseSearchJobReturn {
  loading: boolean;
  error: string | null;
  result: BuscaResult | null;
  rawCount: number;
  searchPhase: SearchPhase;
  ufsCompleted: number;
  ufsTotal: number;
  itemsFetched: number;
  itemsFiltered: number;
  elapsedSeconds: number;
  downloadLoading: boolean;
  downloadError: string | null;
  completedAt: Date | null;
  buscar: (params: SearchSubmitParams) => Promise<void>;
  handleCancel: () => void;
  handleDownload: (params: { downloadId: string; sectorName: string; dataInicial: string; dataFinal: string }) => Promise<void>;
  handleDownloadCsv: (params: { downloadId: string; sectorName: string; dataInicial: string; dataFinal: string }) => Promise<void>;
  clearResult: () => void;
}

export function useSearchJob(
  trackEvent: (name: string, props?: Record<string, any>) => void,
): UseSearchJobReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BuscaResult | null>(null);
  const [rawCount, setRawCount] = useState(0);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [completedAt, setCompletedAt] = useState<Date | null>(null);

  const [searchPhase, setSearchPhase] = useState<SearchPhase>("idle");
  const [ufsCompleted, setUfsCompleted] = useState(0);
  const [ufsTotal, setUfsTotal] = useState(0);
  const [itemsFetched, setItemsFetched] = useState(0);
  const [itemsFiltered, setItemsFiltered] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const searchStartTimeRef = useRef<number>(0);
  const pollCountRef = useRef<number>(0);
  const originalTitleRef = useRef<string>("");
  const searchContextRef = useRef<{ ufCount: number; days: number }>({ ufCount: 0, days: 0 });

  useEffect(() => {
    originalTitleRef.current = document.title;
  }, []);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearTimeout(pollingRef.current);
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
    jobIdRef.current = null;
  }, []);

  const resetProgressState = useCallback(() => {
    setSearchPhase("idle");
    setUfsCompleted(0);
    setUfsTotal(0);
    setItemsFetched(0);
    setItemsFiltered(0);
    setElapsedSeconds(0);
  }, []);

  const handleCancel = useCallback(() => {
    const currentJobId = jobIdRef.current;
    stopPolling();
    setLoading(false);
    resetProgressState();
    trackEvent("search_cancelled", {
      elapsed_time_ms: Date.now() - searchStartTimeRef.current,
      last_phase: searchPhase,
    });
    // Cancel the backend job (fire-and-forget)
    if (currentJobId) {
      try { fetch(`/api/buscar/cancel?job_id=${currentJobId}`, { method: "DELETE" }).catch(() => {}); } catch (_e) { void _e; }
    }
  }, [stopPolling, resetProgressState, trackEvent, searchPhase]);

  const notifyCompletion = useCallback((totalOps: number) => {
    if (document.hidden) {
      document.title = `\u2705 ${totalOps} licita\u00e7\u00f5es encontradas \u2014 DescompLicita`;
      const handleVisibility = () => {
        if (!document.hidden) {
          document.title = originalTitleRef.current;
          document.removeEventListener("visibilitychange", handleVisibility);
        }
      };
      document.addEventListener("visibilitychange", handleVisibility);

      if (typeof Notification !== "undefined" && Notification.permission === "granted") {
        new Notification("DescompLicita", {
          body: `Busca conclu\u00edda! ${totalOps} licita\u00e7\u00f5es encontradas.`,
          icon: "/favicon.ico",
        });
      }
    }
  }, []);

  const requestNotificationPermission = useCallback(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  const fetchResult = useCallback(async (jobId: string) => {
    const response = await fetch(`/api/buscar/result?job_id=${jobId}`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.message || "Erro ao obter resultado da busca");
    }
    const data = await response.json();
    if (data.status === "running") return null;
    return data as BuscaResult;
  }, []);

  /**
   * Exponential backoff polling strategy:
   * - Initial interval: 1000ms (1s)
   * - Growth factor: 1.5x each poll
   * - Maximum interval: 15000ms (15s)
   * - Pattern: 1s, 1.5s, 2.25s, 3.375s, 5.06s, 7.59s, 11.39s, 15s, 15s...
   * - Timeout: 10 minutes
   *
   * This reduces total poll requests by ~60-80% compared to a fixed 2s interval.
   *
   * Future optimization: Replace polling with Server-Sent Events (SSE) for
   * real-time push-based progress updates from the backend. SSE would eliminate
   * polling entirely and provide instant status updates.
   */
  const startPolling = useCallback((jobId: string, ufCount: number) => {
    const INITIAL_INTERVAL = 1000;
    const MAX_INTERVAL = 15000;
    const BACKOFF_FACTOR = 1.5;
    const expectedSeconds = 300 + Math.max(0, ufCount - 5) * 15;
    const POLL_TIMEOUT = (expectedSeconds + 60) * 1000;
    const deadline = Date.now() + POLL_TIMEOUT;

    let currentInterval = INITIAL_INTERVAL;
    pollCountRef.current = 0;

    const poll = async () => {
      if (Date.now() > deadline) {
        stopPolling();
        const ctx = searchContextRef.current;
        setError(
          `A consulta excedeu o tempo limite. Você selecionou ${ctx.ufCount} estados e ${ctx.days} dias. ` +
          "Tente com menos de 10 estados ou período de 30 dias."
        );
        setLoading(false);
        resetProgressState();
        return;
      }

      pollCountRef.current++;

      try {
        const statusRes = await fetch(`/api/buscar/status?job_id=${jobId}`);
        if (!statusRes.ok) {
          // Schedule next poll even on error
          currentInterval = Math.min(currentInterval * BACKOFF_FACTOR, MAX_INTERVAL);
          pollingRef.current = setTimeout(poll, currentInterval);
          return;
        }

        const statusData = await statusRes.json();
        const progress = statusData.progress || {};

        setSearchPhase(progress.phase || statusData.status || "queued");
        setUfsCompleted(progress.ufs_completed || 0);
        setUfsTotal(progress.ufs_total || 0);
        setItemsFetched(progress.items_fetched || 0);
        setItemsFiltered(progress.items_filtered || 0);
        setElapsedSeconds(Math.round(statusData.elapsed_seconds || 0));

        if (statusData.status === "completed" || statusData.status === "failed") {
          stopPolling();

          try {
            const resultData = await fetchResult(jobId);
            if (resultData) {
              setResult(resultData);
              setRawCount(resultData.total_raw || 0);
              setCompletedAt(new Date());

              const totalOps = resultData.resumo?.total_oportunidades || 0;
              notifyCompletion(totalOps);
              requestNotificationPermission();

              const timeElapsed = Date.now() - searchStartTimeRef.current;
              trackEvent("search_completed", {
                time_elapsed_ms: timeElapsed,
                time_elapsed_readable: `${Math.floor(timeElapsed / 1000)}s`,
                total_raw: resultData.total_raw || 0,
                total_filtered: resultData.total_filtrado || 0,
                filter_ratio: resultData.total_raw > 0
                  ? ((resultData.total_filtrado / resultData.total_raw) * 100).toFixed(1) + "%"
                  : "0%",
                valor_total: resultData.resumo?.valor_total || 0,
                has_summary: !!resultData.resumo?.resumo_executivo,
                poll_count: pollCountRef.current,
              });
            }
          } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Erro ao obter resultado";
            setError(errorMessage);
            trackEvent("search_failed", {
              error_message: errorMessage,
              time_elapsed_ms: Date.now() - searchStartTimeRef.current,
              poll_count: pollCountRef.current,
            });
          }

          setLoading(false);
          resetProgressState();
          return;
        }

        // Schedule next poll with backoff
        currentInterval = Math.min(currentInterval * BACKOFF_FACTOR, MAX_INTERVAL);
        pollingRef.current = setTimeout(poll, currentInterval);

      } catch {
        // Network error — retry with backoff
        currentInterval = Math.min(currentInterval * BACKOFF_FACTOR, MAX_INTERVAL);
        pollingRef.current = setTimeout(poll, currentInterval);
      }
    };

    // Start first poll
    pollingRef.current = setTimeout(poll, currentInterval);
  }, [stopPolling, resetProgressState, fetchResult, trackEvent, notifyCompletion, requestNotificationPermission]);

  const buscar = useCallback(async (params: SearchSubmitParams) => {
    stopPolling();
    setLoading(true);
    setError(null);
    setResult(null);
    setRawCount(0);
    setCompletedAt(null);
    resetProgressState();
    setSearchPhase("queued");

    searchStartTimeRef.current = Date.now();
    searchContextRef.current = {
      ufCount: params.ufs.length,
      days: dateDiffInDays(params.dataInicial, params.dataFinal),
    };

    trackEvent("search_started", {
      ufs: params.ufs,
      uf_count: params.ufs.length,
      date_range: {
        inicial: params.dataInicial,
        final: params.dataFinal,
        days: dateDiffInDays(params.dataInicial, params.dataFinal),
      },
      search_mode: params.searchMode,
      setor_id: params.searchMode === "setor" ? params.setorId : null,
      termos_busca: params.searchMode === "termos" ? params.termosArray.join(" ") : null,
      termos_count: params.termosArray.length,
    });

    try {
      const response = await fetch("/api/buscar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ufs: params.ufs,
          data_inicial: params.dataInicial,
          data_final: params.dataFinal,
          setor_id: params.searchMode === "setor" ? params.setorId : null,
          termos_busca: params.searchMode === "termos"
            ? params.termosArray.map(t => t.includes(" ") ? `"${t}"` : t).join(", ")
            : null,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || "Erro ao buscar licitacoes");
      }

      const data = await response.json();
      const jobId = data.job_id;

      if (!jobId) {
        throw new Error("Erro: job_id nao retornado pelo servidor");
      }

      jobIdRef.current = jobId;
      startPolling(jobId, params.ufs.length);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Erro desconhecido";
      setError(errorMessage);
      setLoading(false);
      resetProgressState();

      trackEvent("search_failed", {
        error_message: errorMessage,
        error_type: e instanceof Error ? e.constructor.name : "unknown",
        time_elapsed_ms: Date.now() - searchStartTimeRef.current,
        ufs: params.ufs,
        uf_count: params.ufs.length,
        search_mode: params.searchMode,
      });
    }
  }, [stopPolling, resetProgressState, startPolling, trackEvent]);

  const handleDownload = useCallback(async (params: {
    downloadId: string;
    sectorName: string;
    dataInicial: string;
    dataFinal: string;
  }) => {
    setDownloadError(null);
    setDownloadLoading(true);

    const downloadStartTime = Date.now();

    trackEvent("download_started", {
      download_id: params.downloadId,
      total_filtered: result?.total_filtrado || 0,
      valor_total: result?.resumo?.valor_total || 0,
    });

    try {
      const response = await fetch(`/api/download?id=${params.downloadId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("Arquivo expirado. Faca uma nova busca para gerar o Excel.");
        }
        throw new Error("Nao foi possivel baixar o arquivo. Tente novamente.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const setorLabel = params.sectorName.replace(/\s+/g, "_");
      const filename = `DescompLicita_${setorLabel}_${params.dataInicial}_a_${params.dataFinal}.xlsx`;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      const timeElapsed = Date.now() - downloadStartTime;
      trackEvent("download_completed", {
        download_id: params.downloadId,
        time_elapsed_ms: timeElapsed,
        time_elapsed_readable: `${Math.floor(timeElapsed / 1000)}s`,
        file_size_bytes: blob.size,
        file_size_readable: `${(blob.size / 1024).toFixed(2)} KB`,
        filename,
        total_filtered: result?.total_filtrado || 0,
        valor_total: result?.resumo?.valor_total || 0,
      });
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Nao foi possivel baixar o arquivo.";
      setDownloadError(errorMessage);
      trackEvent("download_failed", {
        download_id: params.downloadId,
        error_message: errorMessage,
        error_type: e instanceof Error ? e.constructor.name : "unknown",
        time_elapsed_ms: Date.now() - downloadStartTime,
        total_filtered: result?.total_filtrado || 0,
      });
    } finally {
      setDownloadLoading(false);
    }
  }, [trackEvent, result]);

  const handleDownloadCsv = useCallback(async (params: {
    downloadId: string;
    sectorName: string;
    dataInicial: string;
    dataFinal: string;
  }) => {
    setDownloadError(null);
    setDownloadLoading(true);

    trackEvent("csv_download_started", {
      download_id: params.downloadId,
      total_filtered: result?.total_filtrado || 0,
    });

    try {
      const response = await fetch(`/api/download?id=${params.downloadId}&format=csv`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("Arquivo expirado. Faca uma nova busca para gerar o CSV.");
        }
        throw new Error("Nao foi possivel baixar o arquivo. Tente novamente.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const setorLabel = params.sectorName.replace(/\s+/g, "_");
      const filename = `DescompLicita_${setorLabel}_${params.dataInicial}_a_${params.dataFinal}.csv`;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      trackEvent("csv_download_completed", {
        download_id: params.downloadId,
        file_size_bytes: blob.size,
        total_filtered: result?.total_filtrado || 0,
      });
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Nao foi possivel baixar o arquivo.";
      setDownloadError(errorMessage);
      trackEvent("csv_download_failed", {
        download_id: params.downloadId,
        error_message: errorMessage,
      });
    } finally {
      setDownloadLoading(false);
    }
  }, [trackEvent, result]);

  const clearResult = useCallback(() => {
    setResult(null);
    setRawCount(0);
  }, []);

  return {
    loading,
    error,
    result,
    rawCount,
    searchPhase,
    ufsCompleted,
    ufsTotal,
    itemsFetched,
    itemsFiltered,
    elapsedSeconds,
    downloadLoading,
    downloadError,
    completedAt,
    buscar,
    handleCancel,
    handleDownload,
    handleDownloadCsv,
    clearResult,
  };
}
