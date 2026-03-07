"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { BuscaResult, ValidationErrors, Setor, SearchPhase } from "./types";
import { LoadingProgress } from "./components/LoadingProgress";
import { EmptyState } from "./components/EmptyState";
import { ThemeToggle } from "./components/ThemeToggle";
import { RegionSelector } from "./components/RegionSelector";
import { SavedSearchesDropdown } from "./components/SavedSearchesDropdown";
import { SourceBadges } from "./components/SourceBadges";
import { useAnalytics } from "../hooks/useAnalytics";
import { useSavedSearches } from "../hooks/useSavedSearches";
import type { SavedSearch } from "../lib/savedSearches";

const LOGO_URL = "https://static.wixstatic.com/media/d47bcc_9fc901ffe70149ae93fad0f461ff9565~mv2.png/v1/crop/x_0,y_301,w_5000,h_2398/fill/w_198,h_95,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Descomplicita%20-%20Azul.png";

const UFS = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
  "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
  "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
];

const UF_NAMES: Record<string, string> = {
  AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia",
  CE: "Ceará", DF: "Distrito Federal", ES: "Espírito Santo", GO: "Goiás",
  MA: "Maranhão", MT: "Mato Grosso", MS: "Mato Grosso do Sul", MG: "Minas Gerais",
  PA: "Pará", PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí",
  RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RS: "Rio Grande do Sul",
  RO: "Rondônia", RR: "Roraima", SC: "Santa Catarina", SP: "São Paulo",
  SE: "Sergipe", TO: "Tocantins",
};

function dateDiffInDays(date1: string, date2: string): number {
  const d1 = new Date(date1);
  const d2 = new Date(date2);
  const diffTime = Math.abs(d2.getTime() - d1.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

export default function HomePage() {
  // Analytics tracking
  const { trackEvent } = useAnalytics();

  // Saved searches
  const { saveNewSearch, isMaxCapacity } = useSavedSearches();
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveSearchName, setSaveSearchName] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);

  const [setores, setSetores] = useState<Setor[]>([]);
  const [setorId, setSetorId] = useState("vestuario");
  const [searchMode, setSearchMode] = useState<"setor" | "termos">("setor");
  const [termosArray, setTermosArray] = useState<string[]>([]);
  const [termoInput, setTermoInput] = useState("");

  const [ufsSelecionadas, setUfsSelecionadas] = useState<Set<string>>(
    new Set(["SC", "PR", "RS"])
  );
  const [dataInicial, setDataInicial] = useState(() => {
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Sao_Paulo" }));
    now.setDate(now.getDate() - 7);
    return now.toISOString().split("T")[0];
  });
  const [dataFinal, setDataFinal] = useState(() => {
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Sao_Paulo" }));
    return now.toISOString().split("T")[0];
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [result, setResult] = useState<BuscaResult | null>(null);
  const [rawCount, setRawCount] = useState(0);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});

  // Polling state
  const [searchPhase, setSearchPhase] = useState<SearchPhase>("idle");
  const [ufsCompleted, setUfsCompleted] = useState(0);
  const [ufsTotal, setUfsTotal] = useState(0);
  const [itemsFetched, setItemsFetched] = useState(0);
  const [itemsFiltered, setItemsFiltered] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const searchStartTimeRef = useRef<number>(0);

  useEffect(() => {
    fetch("/api/setores")
      .then(res => res.json())
      .then(data => {
        if (data.setores) setSetores(data.setores);
      })
      .catch(() => {
        setSetores([
          { id: "vestuario", name: "Vestuário e Uniformes", description: "" },
          { id: "alimentos", name: "Alimentos e Merenda", description: "" },
          { id: "informatica", name: "Informática e Tecnologia", description: "" },
          { id: "limpeza", name: "Produtos de Limpeza", description: "" },
          { id: "mobiliario", name: "Mobiliário", description: "" },
          { id: "papelaria", name: "Papelaria e Material de Escritório", description: "" },
          { id: "engenharia", name: "Engenharia e Construção", description: "" },
        ]);
      });
  }, []);

  function validateForm(): ValidationErrors {
    const errors: ValidationErrors = {};
    if (ufsSelecionadas.size === 0) {
      errors.ufs = "Selecione pelo menos um estado";
    }
    if (dataFinal < dataInicial) {
      errors.date_range = "Data final deve ser maior ou igual à data inicial";
    }
    return errors;
  }

  const canSearch = Object.keys(validateForm()).length === 0
    && (searchMode === "setor" || termosArray.length > 0);

  useEffect(() => {
    setValidationErrors(validateForm());
  }, [ufsSelecionadas, dataInicial, dataFinal]);

  const toggleUf = (uf: string) => {
    const newSet = new Set(ufsSelecionadas);
    if (newSet.has(uf)) {
      newSet.delete(uf);
    } else {
      newSet.add(uf);
    }
    setUfsSelecionadas(newSet);
    setResult(null);
  };

  const toggleRegion = (regionUfs: string[]) => {
    const allSelected = regionUfs.every(uf => ufsSelecionadas.has(uf));
    const newSet = new Set(ufsSelecionadas);
    if (allSelected) {
      regionUfs.forEach(uf => newSet.delete(uf));
    } else {
      regionUfs.forEach(uf => newSet.add(uf));
    }
    setUfsSelecionadas(newSet);
    setResult(null);
  };

  const selecionarTodos = () => { setUfsSelecionadas(new Set(UFS)); setResult(null); };
  const limparSelecao = () => { setUfsSelecionadas(new Set()); setResult(null); };

  const sectorName = searchMode === "setor"
    ? (setores.find(s => s.id === setorId)?.name || "Licitações")
    : "Licitações";

  const searchLabel = searchMode === "setor"
    ? sectorName
    : termosArray.length > 0
      ? `"${termosArray.join('", "')}"`
      : "Licitações";

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
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
    stopPolling();
    setLoading(false);
    resetProgressState();
    trackEvent("search_cancelled", {
      elapsed_time_ms: Date.now() - searchStartTimeRef.current,
      last_phase: searchPhase,
    });
  }, [stopPolling, resetProgressState, trackEvent, searchPhase]);

  const fetchResult = useCallback(async (jobId: string) => {
    const response = await fetch(`/api/buscar/result?job_id=${jobId}`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.message || "Erro ao obter resultado da busca");
    }

    const data = await response.json();

    if (data.status === "running") {
      return null; // still running
    }

    return data as BuscaResult;
  }, []);

  const startPolling = useCallback((jobId: string) => {
    const POLL_INTERVAL = 2000;
    const POLL_TIMEOUT = 10 * 60 * 1000; // 10 min
    const deadline = Date.now() + POLL_TIMEOUT;

    pollingRef.current = setInterval(async () => {
      if (Date.now() > deadline) {
        stopPolling();
        setError("A consulta excedeu o tempo limite. Tente com menos estados ou um período menor.");
        setLoading(false);
        resetProgressState();
        return;
      }

      try {
        // Poll status
        const statusRes = await fetch(`/api/buscar/status?job_id=${jobId}`);
        if (!statusRes.ok) return; // silently retry next interval

        const statusData = await statusRes.json();
        const progress = statusData.progress || {};

        setSearchPhase(progress.phase || statusData.status || "queued");
        setUfsCompleted(progress.ufs_completed || 0);
        setUfsTotal(progress.ufs_total || 0);
        setItemsFetched(progress.items_fetched || 0);
        setItemsFiltered(progress.items_filtered || 0);
        setElapsedSeconds(Math.round(statusData.elapsed_seconds || 0));

        // Check if done
        if (statusData.status === "completed" || statusData.status === "failed") {
          stopPolling();

          try {
            const resultData = await fetchResult(jobId);

            if (resultData) {
              setResult(resultData);
              setRawCount(resultData.total_raw || 0);

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
              });
            }
          } catch (e) {
            const errorMessage = e instanceof Error ? e.message : "Erro ao obter resultado";
            setError(errorMessage);
            trackEvent("search_failed", {
              error_message: errorMessage,
              time_elapsed_ms: Date.now() - searchStartTimeRef.current,
            });
          }

          setLoading(false);
          resetProgressState();
        }
      } catch {
        // Network error — silently retry next interval
      }
    }, POLL_INTERVAL);
  }, [stopPolling, resetProgressState, fetchResult, trackEvent]);

  const buscar = async () => {
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    stopPolling();
    setLoading(true);
    setError(null);
    setResult(null);
    setRawCount(0);
    resetProgressState();
    setSearchPhase("queued");

    searchStartTimeRef.current = Date.now();

    // Track search_started event
    trackEvent("search_started", {
      ufs: Array.from(ufsSelecionadas),
      uf_count: ufsSelecionadas.size,
      date_range: {
        inicial: dataInicial,
        final: dataFinal,
        days: dateDiffInDays(dataInicial, dataFinal),
      },
      search_mode: searchMode,
      setor_id: searchMode === "setor" ? setorId : null,
      termos_busca: searchMode === "termos" ? termosArray.join(" ") : null,
      termos_count: termosArray.length,
    });

    try {
      const response = await fetch("/api/buscar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ufs: Array.from(ufsSelecionadas),
          data_inicial: dataInicial,
          data_final: dataFinal,
          setor_id: searchMode === "setor" ? setorId : null,
          termos_busca: searchMode === "termos" ? termosArray.join(" ") : null,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || "Erro ao buscar licitações");
      }

      const data = await response.json();
      const jobId = data.job_id;

      if (!jobId) {
        throw new Error("Erro: job_id não retornado pelo servidor");
      }

      jobIdRef.current = jobId;
      startPolling(jobId);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "Erro desconhecido";
      setError(errorMessage);
      setLoading(false);
      resetProgressState();

      trackEvent("search_failed", {
        error_message: errorMessage,
        error_type: e instanceof Error ? e.constructor.name : "unknown",
        time_elapsed_ms: Date.now() - searchStartTimeRef.current,
        ufs: Array.from(ufsSelecionadas),
        uf_count: ufsSelecionadas.size,
        search_mode: searchMode,
      });
    }
  };

  const handleDownload = async () => {
    if (!result?.download_id) return;
    setDownloadError(null);
    setDownloadLoading(true);

    const downloadStartTime = Date.now();

    // Track download_started event
    trackEvent('download_started', {
      download_id: result.download_id,
      total_filtered: result.total_filtrado || 0,
      valor_total: result.resumo?.valor_total || 0,
      search_mode: searchMode,
      ufs: Array.from(ufsSelecionadas),
      uf_count: ufsSelecionadas.size,
    });

    try {
      const downloadUrl = `/api/download?id=${result.download_id}`;
      const response = await fetch(downloadUrl);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Arquivo expirado. Faça uma nova busca para gerar o Excel.');
        }
        throw new Error('Não foi possível baixar o arquivo. Tente novamente.');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const setorLabel = sectorName.replace(/\s+/g, '_');
      const filename = `DescompLicita_${setorLabel}_${dataInicial}_a_${dataFinal}.xlsx`;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      const downloadEndTime = Date.now();
      const timeElapsed = downloadEndTime - downloadStartTime;

      // Track download_completed event
      trackEvent('download_completed', {
        download_id: result.download_id,
        time_elapsed_ms: timeElapsed,
        time_elapsed_readable: `${Math.floor(timeElapsed / 1000)}s`,
        file_size_bytes: blob.size,
        file_size_readable: `${(blob.size / 1024).toFixed(2)} KB`,
        filename: filename,
        total_filtered: result.total_filtrado || 0,
        valor_total: result.resumo?.valor_total || 0,
      });
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Não foi possível baixar o arquivo.';
      setDownloadError(errorMessage);

      // Track download_failed event
      trackEvent('download_failed', {
        download_id: result.download_id,
        error_message: errorMessage,
        error_type: e instanceof Error ? e.constructor.name : 'unknown',
        time_elapsed_ms: Date.now() - downloadStartTime,
        total_filtered: result.total_filtrado || 0,
      });
    } finally {
      setDownloadLoading(false);
    }
  };

  const handleSaveSearch = () => {
    if (!result) return;

    const defaultName = searchMode === "setor"
      ? (setores.find(s => s.id === setorId)?.name || "Busca personalizada")
      : termosArray.length > 0
        ? `Busca: "${termosArray.join(', ')}"`
        : "Busca personalizada";

    setSaveSearchName(defaultName);
    setSaveError(null);
    setShowSaveDialog(true);
  };

  const confirmSaveSearch = () => {
    try {
      saveNewSearch(saveSearchName || "Busca sem nome", {
        ufs: Array.from(ufsSelecionadas),
        dataInicial,
        dataFinal,
        searchMode,
        setorId: searchMode === "setor" ? setorId : undefined,
        termosBusca: searchMode === "termos" ? termosArray.join(" ") : undefined,
      });

      // Track analytics
      trackEvent('saved_search_created', {
        search_name: saveSearchName,
        search_mode: searchMode,
        ufs: Array.from(ufsSelecionadas),
        uf_count: ufsSelecionadas.size,
        setor_id: searchMode === "setor" ? setorId : null,
        termos_count: termosArray.length,
      });

      setShowSaveDialog(false);
      setSaveSearchName("");
      setSaveError(null);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Erro ao salvar busca");
    }
  };

  const handleLoadSearch = (search: SavedSearch) => {
    // Load search parameters into form
    setUfsSelecionadas(new Set(search.searchParams.ufs));
    setDataInicial(search.searchParams.dataInicial);
    setDataFinal(search.searchParams.dataFinal);
    setSearchMode(search.searchParams.searchMode);

    if (search.searchParams.searchMode === "setor" && search.searchParams.setorId) {
      setSetorId(search.searchParams.setorId);
    } else if (search.searchParams.searchMode === "termos" && search.searchParams.termosBusca) {
      setTermosArray(search.searchParams.termosBusca.split(" "));
    }

    // Clear current result to show updated form
    setResult(null);
  };

  const isFormValid = Object.keys(validationErrors).length === 0;

  return (
    <div className="min-h-screen">
      {/* Navigation Header */}
      <header className="border-b border-strong bg-surface-0 sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={LOGO_URL}
              alt="DescompLicita"
              width={140}
              height={67}
              className="h-10 w-auto"
            />
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden sm:block text-xs text-ink-muted font-medium">
              Busca Inteligente de Licitações
            </span>
            <SavedSearchesDropdown
              onLoadSearch={handleLoadSearch}
              onAnalyticsEvent={trackEvent}
            />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        {/* Page Title */}
        <div className="mb-8 animate-fade-in-up">
          <h1 className="text-2xl sm:text-3xl font-bold font-display text-ink">
            Busca de Licitações
          </h1>
          <p className="text-ink-secondary mt-1 text-sm sm:text-base">
            Encontre oportunidades de contratação pública em fontes oficiais
          </p>
        </div>

        {/* Search Mode Toggle */}
        <section className="mb-6 animate-fade-in-up stagger-1">
          <label className="block text-base font-semibold text-ink mb-3">
            Buscar por:
          </label>
          <div className="flex rounded-button border border-strong overflow-hidden mb-4">
            <button
              type="button"
              onClick={() => { setSearchMode("setor"); setResult(null); }}
              className={`flex-1 py-2.5 text-sm sm:text-base font-medium transition-all duration-200 ${
                searchMode === "setor"
                  ? "bg-brand-navy text-white"
                  : "bg-surface-0 text-ink-secondary hover:bg-surface-1"
              }`}
            >
              Setor
            </button>
            <button
              type="button"
              onClick={() => { setSearchMode("termos"); setResult(null); }}
              className={`flex-1 py-2.5 text-sm sm:text-base font-medium transition-all duration-200 ${
                searchMode === "termos"
                  ? "bg-brand-navy text-white"
                  : "bg-surface-0 text-ink-secondary hover:bg-surface-1"
              }`}
            >
              Termos Específicos
            </button>
          </div>

          {/* Sector Selector */}
          {searchMode === "setor" && (
            <div>
              <select
                id="setor"
                value={setorId}
                onChange={e => { setSetorId(e.target.value); setResult(null); }}
                className="w-full border border-strong rounded-input px-4 py-3 text-base
                           bg-surface-0 text-ink
                           focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue
                           transition-colors"
              >
                {setores.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Custom Terms Input with Tags */}
          {searchMode === "termos" && (
            <div>
              <div className="border border-strong rounded-input bg-surface-0 px-3 py-2 flex flex-wrap gap-2 items-center
                              focus-within:ring-2 focus-within:ring-brand-blue focus-within:border-brand-blue
                              transition-colors min-h-[48px]">
                {termosArray.map((termo, i) => (
                  <span
                    key={`${termo}-${i}`}
                    className="inline-flex items-center gap-1 bg-brand-blue-subtle text-brand-navy
                               px-2.5 py-1 rounded-full text-sm font-medium border border-brand-blue/20
                               animate-fade-in-up"
                  >
                    {termo}
                    <button
                      type="button"
                      onClick={() => {
                        setTermosArray(prev => prev.filter((_, idx) => idx !== i));
                        setResult(null);
                      }}
                      className="ml-0.5 hover:text-error transition-colors"
                      aria-label={`Remover termo ${termo}`}
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
                <input
                  id="termos-busca"
                  type="text"
                  value={termoInput}
                  onChange={e => {
                    const val = e.target.value;
                    // When user types a space, commit the word as a tag
                    if (val.endsWith(" ")) {
                      const word = val.trim().toLowerCase();
                      if (word && !termosArray.includes(word)) {
                        setTermosArray(prev => [...prev, word]);
                        setResult(null);
                      }
                      setTermoInput("");
                    } else {
                      setTermoInput(val);
                    }
                  }}
                  onKeyDown={e => {
                    // Backspace on empty input removes last tag
                    if (e.key === "Backspace" && termoInput === "" && termosArray.length > 0) {
                      setTermosArray(prev => prev.slice(0, -1));
                      setResult(null);
                    }
                    // Enter also commits the current word
                    if (e.key === "Enter") {
                      e.preventDefault();
                      const word = termoInput.trim().toLowerCase();
                      if (word && !termosArray.includes(word)) {
                        setTermosArray(prev => [...prev, word]);
                        setResult(null);
                      }
                      setTermoInput("");
                    }
                  }}
                  placeholder={termosArray.length === 0 ? "Digite um termo e pressione espaço..." : "Adicionar mais..."}
                  className="flex-1 min-w-[120px] outline-none bg-transparent text-base text-ink
                             placeholder:text-ink-faint py-1"
                />
              </div>
              <p className="text-sm text-ink-muted mt-1.5">
                Digite cada termo e pressione <kbd className="px-1.5 py-0.5 bg-surface-2 rounded text-xs font-mono border">espaço</kbd> para confirmar.
                {termosArray.length > 0 && (
                  <span className="text-brand-blue font-medium">
                    {" "}{termosArray.length} termo{termosArray.length > 1 ? "s" : ""} selecionado{termosArray.length > 1 ? "s" : ""}
                  </span>
                )}
              </p>
            </div>
          )}
        </section>

        {/* UF Selection Section */}
        <section className="mb-6 animate-fade-in-up stagger-2">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 mb-3">
            <label className="text-base sm:text-lg font-semibold text-ink">
              Estados (UFs):
            </label>
            <div className="flex gap-3">
              <button
                onClick={selecionarTodos}
                className="text-sm sm:text-base font-medium text-brand-blue hover:text-brand-blue-hover hover:underline transition-colors"
                type="button"
              >
                Selecionar todos
              </button>
              <button
                onClick={limparSelecao}
                className="text-sm sm:text-base font-medium text-ink-muted hover:text-ink transition-colors"
                type="button"
              >
                Limpar
              </button>
            </div>
          </div>

          {/* Region quick-select */}
          <RegionSelector selected={ufsSelecionadas} onToggleRegion={toggleRegion} />

          {/* UF Grid */}
          <div className="grid grid-cols-5 sm:grid-cols-7 md:grid-cols-9 gap-2">
            {UFS.map(uf => (
              <button
                key={uf}
                onClick={() => toggleUf(uf)}
                type="button"
                title={UF_NAMES[uf]}
                aria-pressed={ufsSelecionadas.has(uf)}
                className={`px-2 py-2 sm:px-4 rounded-button border text-sm sm:text-base font-medium transition-all duration-200 ${
                  ufsSelecionadas.has(uf)
                    ? "bg-brand-navy text-white border-brand-navy hover:bg-brand-blue-hover"
                    : "bg-surface-0 text-ink-secondary border hover:border-accent hover:text-brand-blue hover:bg-brand-blue-subtle"
                }`}
              >
                {uf}
              </button>
            ))}
          </div>

          <p className="text-sm sm:text-base text-ink-muted mt-2">
            {ufsSelecionadas.size === 1 ? '1 estado selecionado' : `${ufsSelecionadas.size} estados selecionados`}
          </p>

          {validationErrors.ufs && (
            <p className="text-sm sm:text-base text-error mt-2 font-medium" role="alert">
              {validationErrors.ufs}
            </p>
          )}
        </section>

        {/* Date Range Section */}
        <section className="mb-6 animate-fade-in-up stagger-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="data-inicial" className="block text-base font-semibold text-ink mb-2">
                Data inicial:
              </label>
              <input
                id="data-inicial"
                type="date"
                value={dataInicial}
                onChange={e => { setDataInicial(e.target.value); setResult(null); }}
                className="w-full border border-strong rounded-input px-4 py-3 text-base
                           bg-surface-0 text-ink
                           focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue
                           transition-colors"
              />
            </div>
            <div>
              <label htmlFor="data-final" className="block text-base font-semibold text-ink mb-2">
                Data final:
              </label>
              <input
                id="data-final"
                type="date"
                value={dataFinal}
                onChange={e => { setDataFinal(e.target.value); setResult(null); }}
                className="w-full border border-strong rounded-input px-4 py-3 text-base
                           bg-surface-0 text-ink
                           focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue
                           transition-colors"
              />
            </div>
          </div>

          {validationErrors.date_range && (
            <p className="text-sm sm:text-base text-error mt-3 font-medium" role="alert">
              {validationErrors.date_range}
            </p>
          )}
        </section>

        {/* Search Buttons */}
        <div className="space-y-3">
          <button
            onClick={buscar}
            disabled={loading || !canSearch}
            type="button"
            aria-busy={loading}
            className="w-full bg-brand-navy text-white py-3 sm:py-4 rounded-button text-base sm:text-lg font-semibold
                       hover:bg-brand-blue-hover active:bg-brand-blue
                       disabled:bg-ink-faint disabled:text-ink-muted disabled:cursor-not-allowed
                       transition-all duration-200"
          >
            {loading ? "Buscando..." : `Buscar ${searchLabel}`}
          </button>

          {/* Save Search Button - Only show if there's a result */}
          {result && result.resumo.total_oportunidades > 0 && (
            <button
              onClick={handleSaveSearch}
              disabled={isMaxCapacity}
              type="button"
              className="w-full bg-surface-0 text-brand-navy py-2.5 sm:py-3 rounded-button text-sm sm:text-base font-medium
                         border border-brand-navy hover:bg-brand-blue-subtle
                         disabled:bg-surface-0 disabled:text-ink-muted disabled:border-ink-faint disabled:cursor-not-allowed
                         transition-all duration-200 flex items-center justify-center gap-2"
              title={isMaxCapacity ? "Máximo de 10 buscas salvas atingido" : "Salvar esta busca"}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
              {isMaxCapacity ? "Limite de buscas atingido" : "Salvar Busca"}
            </button>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div aria-live="polite">
            <LoadingProgress
              phase={searchPhase}
              ufsCompleted={ufsCompleted}
              ufsTotal={ufsTotal}
              itemsFetched={itemsFetched}
              itemsFiltered={itemsFiltered}
              elapsedSeconds={elapsedSeconds}
              onCancel={handleCancel}
            />
          </div>
        )}

        {/* Error Display with Retry */}
        {error && (
          <div className="mt-6 sm:mt-8 p-4 sm:p-5 bg-error-subtle border border-error/20 rounded-card animate-fade-in-up" role="alert">
            <p className="text-sm sm:text-base font-medium text-error mb-3">{error}</p>
            <button
              onClick={buscar}
              disabled={loading}
              className="px-4 py-2 bg-error text-white rounded-button text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {/* Empty State */}
        {result && result.resumo.total_oportunidades === 0 && (
          <EmptyState
            onAdjustSearch={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            rawCount={rawCount}
            stateCount={ufsSelecionadas.size}
            filterStats={result.filter_stats}
            sectorName={sectorName}
          />
        )}

        {/* Result Display */}
        {result && result.resumo.total_oportunidades > 0 && (
          <div className="mt-6 sm:mt-8 space-y-4 sm:space-y-6 animate-fade-in-up">
            {/* Summary Card */}
            <div className="p-4 sm:p-6 bg-brand-blue-subtle border border-accent rounded-card">
              <p className="text-base sm:text-lg leading-relaxed text-ink">
                {result.resumo.resumo_executivo}
              </p>

              <div className="flex flex-col sm:flex-row flex-wrap gap-4 sm:gap-8 mt-4 sm:mt-6">
                <div>
                  <span className="text-3xl sm:text-4xl font-bold font-data tabular-nums text-brand-navy dark:text-brand-blue">
                    {result.resumo.total_oportunidades}
                  </span>
                  <span className="text-sm sm:text-base text-ink-secondary block mt-1">oportunidades</span>
                  {(result.total_atas > 0 || result.total_licitacoes > 0) && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {result.total_licitacoes > 0 && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800">
                          {result.total_licitacoes} Licitacoes
                        </span>
                      )}
                      {result.total_atas > 0 && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-800 border border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800">
                          {result.total_atas} Atas RP
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div>
                  <span className="text-3xl sm:text-4xl font-bold font-data tabular-nums text-brand-navy dark:text-brand-blue">
                    R$ {result.resumo.valor_total.toLocaleString("pt-BR")}
                  </span>
                  <span className="text-sm sm:text-base text-ink-secondary block mt-1">valor total</span>
                </div>
              </div>

              {result.resumo.alerta_urgencia && (
                <div className="mt-4 sm:mt-6 p-3 sm:p-4 bg-warning-subtle border border-warning/20 rounded-card" role="alert">
                  <p className="text-sm sm:text-base font-medium text-warning">
                    <span aria-hidden="true">Atenção: </span>
                    {result.resumo.alerta_urgencia}
                  </p>
                </div>
              )}

              {result.resumo.destaques.length > 0 && (
                <div className="mt-4 sm:mt-6">
                  <h4 className="text-base sm:text-lg font-semibold font-display text-ink mb-2 sm:mb-3">Destaques:</h4>
                  <ul className="list-disc list-inside text-sm sm:text-base space-y-2 text-ink-secondary">
                    {result.resumo.destaques.map((d, i) => (
                      <li key={i} className="animate-fade-in-up" style={{ animationDelay: `${i * 60}ms` }}>{d}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.sources_used && result.sources_used.length > 0 && (
                <SourceBadges
                  sources={result.sources_used}
                  stats={result.source_stats}
                  dedupRemoved={result.dedup_removed}
                />
              )}
            </div>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              disabled={downloadLoading}
              aria-label={`Baixar Excel com ${result.resumo.total_oportunidades} licitações`}
              className="w-full bg-brand-navy text-white py-3 sm:py-4 rounded-button text-base sm:text-lg font-semibold
                         hover:bg-brand-blue-hover active:bg-brand-blue
                         disabled:bg-ink-faint disabled:text-ink-muted disabled:cursor-not-allowed
                         transition-all duration-200
                         flex items-center justify-center gap-3"
            >
              {downloadLoading ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Preparando download...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Baixar Excel ({result.resumo.total_oportunidades} licitações)
                </>
              )}
            </button>

            {/* Download Error */}
            {downloadError && (
              <div className="p-4 sm:p-5 bg-error-subtle border border-error/20 rounded-card" role="alert">
                <p className="text-sm sm:text-base font-medium text-error">{downloadError}</p>
              </div>
            )}

            {/* Stats */}
            <div className="text-xs sm:text-sm text-ink-muted text-center">
              {rawCount > 0 && (
                <p>
                  Encontradas {result.resumo.total_oportunidades} de {rawCount.toLocaleString("pt-BR")} licitações
                  ({((result.resumo.total_oportunidades / rawCount) * 100).toFixed(1)}% do setor {sectorName.toLowerCase()})
                </p>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Save Search Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 animate-fade-in">
          <div className="bg-surface-0 rounded-card shadow-xl max-w-md w-full p-6 animate-fade-in-up">
            <h3 className="text-lg font-semibold text-ink mb-4">Salvar Busca</h3>

            <div className="mb-4">
              <label htmlFor="save-search-name" className="block text-sm font-medium text-ink-secondary mb-2">
                Nome da busca:
              </label>
              <input
                id="save-search-name"
                type="text"
                value={saveSearchName}
                onChange={(e) => setSaveSearchName(e.target.value)}
                placeholder="Ex: Uniformes Sul do Brasil"
                className="w-full border border-strong rounded-input px-4 py-2.5 text-base
                           bg-surface-0 text-ink
                           focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-brand-blue
                           transition-colors"
                maxLength={50}
                autoFocus
              />
              <p className="text-xs text-ink-muted mt-1">
                {saveSearchName.length}/50 caracteres
              </p>
            </div>

            {saveError && (
              <div className="mb-4 p-3 bg-error-subtle border border-error/20 rounded text-sm text-error" role="alert">
                {saveError}
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowSaveDialog(false);
                  setSaveSearchName("");
                  setSaveError(null);
                }}
                type="button"
                className="px-4 py-2 text-sm font-medium text-ink-secondary hover:text-ink
                           hover:bg-surface-1 rounded-button transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={confirmSaveSearch}
                disabled={!saveSearchName.trim()}
                type="button"
                className="px-4 py-2 text-sm font-medium text-white bg-brand-navy
                           hover:bg-brand-blue-hover rounded-button transition-colors
                           disabled:bg-ink-faint disabled:cursor-not-allowed"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t mt-12 py-6 text-center text-xs text-ink-muted">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          DescompLicita &mdash; Licitações e Contratos de Forma Descomplicada
        </div>
      </footer>
    </div>
  );
}
