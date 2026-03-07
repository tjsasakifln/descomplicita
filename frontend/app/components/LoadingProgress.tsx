"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useAnalytics } from "../../hooks/useAnalytics";
import type { SearchPhase } from "../types";
import { CURIOSIDADES, CATEGORIA_CONFIG, shuffleBalanced } from "./carouselData";

type StageId = "queued" | "fetching" | "filtering" | "summarizing" | "generating_excel";

type IconId = "search" | "download" | "filter" | "ai" | "done";

const ICON_SVG_PATHS: Record<IconId, string> = {
  search: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  download: "M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2m-4-4l-4 4m0 0l-4-4m4 4V4",
  filter: "M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z",
  ai: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-1.5 4.5H6.5L5 14.5m14 0H5",
  done: "M5 13l4 4L19 7",
};

const CATEGORIA_ICON_SVG_PATHS: Record<string, string> = {
  scale: "M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l3 9a5.002 5.002 0 006.001 0M18 7l-3 9m3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3",
  target: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  chart: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  bulb: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z",
};

function CategoriaIcon({ icon, className }: { icon: string; className?: string }) {
  const path = CATEGORIA_ICON_SVG_PATHS[icon];
  if (!path) return null;
  return (
    <svg className={className || "w-4 h-4"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}

function StageIcon({ icon, className }: { icon: string; className?: string }) {
  const path = ICON_SVG_PATHS[icon as IconId];
  if (!path) return null;
  return (
    <svg className={className || "w-4 h-4"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}

const STAGES: { id: StageId; label: string; icon: string }[] = [
  { id: "queued", label: "Iniciando busca", icon: "search" },
  { id: "fetching", label: "Buscando licitações", icon: "download" },
  { id: "filtering", label: "Filtrando resultados", icon: "filter" },
  { id: "summarizing", label: "Gerando resumo IA", icon: "ai" },
  { id: "generating_excel", label: "Preparando planilha", icon: "done" },
];

interface LoadingProgressProps {
  phase: SearchPhase;
  ufsCompleted: number;
  ufsTotal: number;
  itemsFetched: number;
  itemsFiltered: number;
  elapsedSeconds: number;
  onCancel: () => void;
  selectedUfs?: string[];
  sectorId?: string;
}

export function LoadingProgress({
  phase,
  ufsCompleted,
  ufsTotal,
  itemsFetched,
  itemsFiltered,
  elapsedSeconds,
  onCancel,
  selectedUfs = [],
  sectorId,
}: LoadingProgressProps) {
  // Sector-aware curiosidades: prioritize sector-specific items, then generic
  const shuffledItems = useMemo(() => {
    if (!sectorId) return shuffleBalanced([...CURIOSIDADES]);

    const sectorItems = CURIOSIDADES.filter(
      (c) => c.setores && c.setores.includes(sectorId)
    );
    const genericItems = CURIOSIDADES.filter((c) => !c.setores);

    // Put sector items first, then generic, both shuffled
    return [
      ...shuffleBalanced([...sectorItems]),
      ...shuffleBalanced([...genericItems]),
    ];
  }, [sectorId]);

  const [curiosidadeIndex, setCuriosidadeIndex] = useState(0);
  const [isFading, setIsFading] = useState(false);
  const { trackEvent } = useAnalytics();
  const stagesReachedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const interval = setInterval(() => {
      setIsFading(true);
      setTimeout(() => {
        setCuriosidadeIndex((prev) => (prev + 1) % shuffledItems.length);
        setIsFading(false);
      }, 300);
    }, 6000);
    return () => clearInterval(interval);
  }, [shuffledItems.length]);

  const curiosidade = shuffledItems[curiosidadeIndex];
  const categoriaConfig = CATEGORIA_CONFIG[curiosidade.categoria];

  // Map phase to stage index
  const phaseToStageIndex = (p: SearchPhase): number => {
    switch (p) {
      case "queued": return 0;
      case "fetching": return 1;
      case "filtering": return 2;
      case "summarizing": return 3;
      case "generating_excel": return 4;
      default: return 0;
    }
  };

  const currentStageIndex = phaseToStageIndex(phase);
  const stageConfig = STAGES[currentStageIndex] || STAGES[0];

  // Calculate real progress percentage based on phase and UF completion
  const calculateProgress = (): number => {
    switch (phase) {
      case "queued":
        return 3;
      case "fetching": {
        const ufProgress = ufsTotal > 0 ? ufsCompleted / ufsTotal : 0;
        return Math.round(5 + ufProgress * 50);
      }
      case "filtering":
        return 60;
      case "summarizing":
        return 75;
      case "generating_excel":
        return 90;
      default:
        return 3;
    }
  };

  const progress = calculateProgress();

  // ETA calculation
  const getETA = (): string | null => {
    if (phase === "queued") return null;

    if (phase === "fetching" && ufsCompleted > 0 && ufsTotal > 0) {
      const avgTimePerUf = elapsedSeconds / ufsCompleted;
      const remainingUfs = ufsTotal - ufsCompleted;
      const fetchRemaining = remainingUfs * avgTimePerUf;
      // Estimate post-fetch phases (~20s for filtering + summarizing + excel)
      const postFetchEstimate = 20;
      const totalRemaining = Math.max(0, Math.round(fetchRemaining + postFetchEstimate));

      if (totalRemaining <= 0) return null;
      const mins = Math.floor(totalRemaining / 60);
      const secs = totalRemaining % 60;
      return mins > 0
        ? `~${mins}min ${secs.toString().padStart(2, "0")}s restantes`
        : `~${secs}s restantes`;
    }

    if (phase === "filtering") return "~15s restantes";
    if (phase === "summarizing") return "~10s restantes";
    if (phase === "generating_excel") return "~5s restantes";

    return null;
  };

  const eta = getETA();

  // Track stage progression (analytics)
  useEffect(() => {
    if (!stagesReachedRef.current.has(phase)) {
      stagesReachedRef.current.add(phase);
      trackEvent("loading_stage_reached", {
        stage: phase,
        stage_index: currentStageIndex,
        elapsed_time_s: elapsedSeconds,
        progress_percent: progress,
        ufs_completed: ufsCompleted,
        ufs_total: ufsTotal,
        items_fetched: itemsFetched,
      });
    }
  }, [phase, currentStageIndex, elapsedSeconds, progress, ufsCompleted, ufsTotal, itemsFetched, trackEvent]);

  // Track loading abandonment
  useEffect(() => {
    const handleBeforeUnload = () => {
      trackEvent("loading_abandoned", {
        last_stage: phase,
        elapsed_time_s: elapsedSeconds,
        progress_percent: progress,
        items_fetched: itemsFetched,
      });
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [phase, elapsedSeconds, progress, itemsFetched, trackEvent]);

  // Dynamic status message from real data
  const getStatusMessage = (): string => {
    switch (phase) {
      case "queued":
        return "Iniciando busca...";
      case "fetching":
        if (ufsTotal > 0) {
          return `Buscando em ${ufsCompleted}/${ufsTotal} estados... ${itemsFetched > 0 ? `(${itemsFetched.toLocaleString("pt-BR")} licitações encontradas)` : ""}`;
        }
        return "Buscando em fontes oficiais...";
      case "filtering":
        return `Filtrando resultados...${itemsFetched > 0 ? ` (${itemsFetched.toLocaleString("pt-BR")} licitações)` : ""}`;
      case "summarizing":
        return "Gerando resumo inteligente...";
      case "generating_excel":
        return "Preparando planilha...";
      default:
        return "Processando...";
    }
  };

  const statusMessage = getStatusMessage();

  // Format elapsed time
  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const timeDisplay = minutes > 0
    ? `${minutes}min ${seconds.toString().padStart(2, "0")}s`
    : `${seconds}s`;

  return (
    <div className="mt-8 p-6 bg-surface-1 rounded-card border animate-fade-in-up">
      {/* Progress Header */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-brand-blue">
            {statusMessage}
          </span>
          <div className="flex items-center gap-3 text-sm tabular-nums font-data text-ink-muted">
            {eta && (
              <span className="text-brand-navy dark:text-brand-blue font-medium">
                {eta}
              </span>
            )}
            <span>{timeDisplay}</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-2 bg-surface-2 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-brand-blue to-brand-navy rounded-full transition-all duration-1000 ease-out"
            style={{ width: `${Math.max(progress, 3)}%` }}
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        <div className="flex justify-between items-center mt-1.5">
          {/* Items counter during fetching */}
          <span className="text-xs text-ink-muted">
            {phase === "fetching" && itemsFetched > 0
              ? `${itemsFetched.toLocaleString("pt-BR")} licitações encontradas até agora`
              : phase === "filtering" && itemsFiltered > 0
                ? `${itemsFiltered.toLocaleString("pt-BR")} licitações filtradas`
                : "\u00A0"}
          </span>
          <span className="text-xs tabular-nums font-data text-ink-muted">{progress}%</span>
        </div>
      </div>

      {/* UF Visual Progress Grid */}
      {phase === "fetching" && ufsTotal > 0 && selectedUfs.length > 0 && (
        <div className="mb-4 p-3 bg-surface-0 rounded-lg border border-accent">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="font-medium text-ink">
              Estados processados
            </span>
            <span className="tabular-nums font-data text-brand-navy dark:text-brand-blue font-semibold">
              {ufsCompleted} / {ufsTotal}
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {selectedUfs.map((uf, i) => {
              const isCompleted = i < ufsCompleted;
              const isCurrent = i === ufsCompleted;
              return (
                <span
                  key={uf}
                  className={`
                    inline-flex items-center justify-center w-9 h-7 rounded text-xs font-semibold
                    transition-all duration-300
                    ${isCompleted
                      ? "bg-brand-navy text-white"
                      : isCurrent
                        ? "bg-brand-blue text-white animate-pulse"
                        : "bg-surface-2 text-ink-muted"
                    }
                  `}
                >
                  {uf}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Fallback: simple counter when no selectedUfs provided */}
      {phase === "fetching" && ufsTotal > 0 && selectedUfs.length === 0 && (
        <div className="mb-4 p-3 bg-surface-0 rounded-lg border border-accent">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-ink">
              Estados processados
            </span>
            <span className="tabular-nums font-data text-brand-navy font-semibold">
              {ufsCompleted} / {ufsTotal}
            </span>
          </div>
        </div>
      )}

      {/* 5-Stage Indicators */}
      <div className="flex items-center justify-between mb-6 px-2">
        {STAGES.map((stage, i) => {
          const isPast = i < currentStageIndex;
          const isCurrent = i === currentStageIndex;

          return (
            <div key={stage.id} className="flex items-center gap-1.5">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300 ${
                isPast
                  ? "bg-brand-navy text-white"
                  : isCurrent
                    ? "bg-brand-blue text-white animate-pulse shadow-lg"
                    : "bg-surface-2 text-ink-muted"
              }`}>
                {isPast ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <StageIcon icon={stage.icon} className="w-4 h-4" />
                )}
              </div>
              <div className="flex flex-col hidden sm:block">
                <span className={`text-xs font-medium ${
                  isPast || isCurrent ? "text-ink" : "text-ink-muted"
                }`}>
                  {stage.label}
                </span>
              </div>
              {i < STAGES.length - 1 && (
                <div className={`w-3 sm:w-6 h-0.5 mx-1 transition-colors duration-300 ${
                  isPast ? "bg-brand-navy" : "bg-surface-2"
                }`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Current Stage Detail (Mobile-friendly) */}
      <div className="sm:hidden mb-4 p-3 bg-surface-0 rounded-lg border border-accent">
        <div className="flex items-center gap-2">
          <StageIcon icon={stageConfig.icon} className="w-5 h-5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-ink">{stageConfig.label}</p>
            <p className="text-xs text-ink-muted">{statusMessage}</p>
          </div>
        </div>
      </div>

      {/* Curiosity Card — Category-aware, sector-prioritized */}
      <div
        className={`p-4 rounded-card border transition-all duration-300 ${categoriaConfig.bgClass} ${isFading ? "opacity-0" : "opacity-100"}`}
      >
        <div className="flex items-start gap-3">
          <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${categoriaConfig.iconBgClass}`}>
            <CategoriaIcon icon={categoriaConfig.icon} className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-sm font-medium text-ink-muted">{categoriaConfig.header}</p>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${categoriaConfig.iconBgClass} ${categoriaConfig.iconTextClass}`}>
                {categoriaConfig.label}
              </span>
            </div>
            <p className="text-base text-ink leading-relaxed">{curiosidade.texto}</p>
            <p className="text-xs text-ink-muted mt-2">Fonte: {curiosidade.fonte}</p>
          </div>
        </div>
      </div>

      {/* Skeleton Result Cards — preview of what's coming */}
      <div className="mt-4 space-y-3">
        <p className="text-xs font-medium text-ink-muted">Preparando seus resultados...</p>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="p-4 bg-surface-0 rounded-card border"
            style={{ opacity: 1 - i * 0.2 }}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 space-y-2.5">
                {/* Title skeleton */}
                <div className="h-4 rounded animate-shimmer" style={{ width: `${75 - i * 10}%` }} />
                {/* Org name skeleton */}
                <div className="h-3 rounded animate-shimmer" style={{ width: `${50 - i * 5}%` }} />
                {/* Details row skeleton */}
                <div className="flex gap-3">
                  <div className="h-3 w-16 rounded animate-shimmer" />
                  <div className="h-3 w-20 rounded animate-shimmer" />
                  <div className="h-3 w-12 rounded animate-shimmer" />
                </div>
              </div>
              {/* Value skeleton */}
              <div className="flex-shrink-0 text-right space-y-2">
                <div className="h-5 w-24 rounded animate-shimmer" />
                <div className="h-3 w-14 rounded animate-shimmer ml-auto" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Cancel button */}
      <div className="mt-4 flex justify-center">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-ink-muted hover:text-error
                     hover:bg-error-subtle border border-transparent hover:border-error/20
                     rounded-button transition-all duration-200"
        >
          Cancelar busca
        </button>
      </div>
    </div>
  );
}

export default LoadingProgress;
