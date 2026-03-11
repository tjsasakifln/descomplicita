"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { useAnalytics } from "../../hooks/useAnalytics";
import type { SearchPhase } from "../types";
import { CURIOSIDADES, shuffleBalanced } from "./carouselData";
import { ProgressBar, UfGrid, StageList, STAGES, CuriosityCarousel, SkeletonCards } from "./loading-progress";
import { Button } from "./Button";

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

const PHASE_TO_INDEX: Record<string, number> = {
  queued: 0, fetching: 1, filtering: 2, summarizing: 3, generating_excel: 4,
};

const PROGRESS_MAP: Partial<Record<SearchPhase, number>> = {
  queued: 3, summarizing: 75, generating_excel: 90,
};

function calculateProgress(phase: SearchPhase, ufsCompleted: number, ufsTotal: number, itemsFetched: number, itemsFiltered: number): number {
  if (phase === "fetching") {
    const ufProgress = ufsTotal > 0 ? ufsCompleted / ufsTotal : 0;
    return Math.round(5 + ufProgress * 50);
  }
  // Task 6: Interpolate 60-90% during filtering based on filtered/fetched ratio
  if (phase === "filtering") {
    if (itemsFetched > 0 && itemsFiltered > 0) {
      const filterRatio = Math.min(itemsFiltered / itemsFetched, 1);
      return Math.round(60 + filterRatio * 15);
    }
    return 60;
  }
  return PROGRESS_MAP[phase] ?? 3;
}

function formatETA(remaining: number): string | null {
  if (remaining <= 0) return null;
  const m = Math.floor(remaining / 60), s = remaining % 60;
  return m > 0 ? `~${m}min ${s.toString().padStart(2, "0")}s restantes` : `~${s}s restantes`;
}

function getETA(phase: SearchPhase, ufsCompleted: number, ufsTotal: number, elapsedSeconds: number, itemsFetched: number): string | null {
  if (phase === "queued") return null;
  if (phase === "fetching" && ufsCompleted > 0 && ufsTotal > 0) {
    const remaining = Math.max(0, Math.round((ufsTotal - ufsCompleted) * (elapsedSeconds / ufsCompleted) + 20));
    return formatETA(remaining);
  }
  // Dynamic ETAs based on volume (Task 5: multiply base by ceil(itemsFetched / 5000))
  const volumeMultiplier = itemsFetched > 0 ? Math.ceil(itemsFetched / 5000) : 1;
  if (phase === "filtering") return formatETA(15 * volumeMultiplier);
  if (phase === "summarizing") return formatETA(10 * volumeMultiplier);
  if (phase === "generating_excel") return formatETA(5 * volumeMultiplier);
  return null;
}

const STATUS_MAP: Partial<Record<SearchPhase, string>> = {
  queued: "Iniciando busca...", summarizing: "Gerando resumo inteligente...", generating_excel: "Preparando planilha...",
};

function getStatusMessage(phase: SearchPhase, ufsCompleted: number, ufsTotal: number, itemsFetched: number): string {
  if (phase === "fetching") {
    if (ufsTotal > 0) return `Buscando em ${ufsCompleted}/${ufsTotal} estados... ${itemsFetched > 0 ? `(${itemsFetched.toLocaleString("pt-BR")} licitações encontradas)` : ""}`;
    return "Buscando em fontes oficiais...";
  }
  if (phase === "filtering") return `Filtrando resultados...${itemsFetched > 0 ? ` (${itemsFetched.toLocaleString("pt-BR")} licitações)` : ""}`;
  return STATUS_MAP[phase] ?? "Processando...";
}

export function LoadingProgress({
  phase, ufsCompleted, ufsTotal, itemsFetched, itemsFiltered,
  elapsedSeconds, onCancel, selectedUfs = [], sectorId,
}: LoadingProgressProps) {
  const shuffledItems = useMemo(() => {
    if (!sectorId) return shuffleBalanced([...CURIOSIDADES]);
    const sector = CURIOSIDADES.filter(c => c.setores?.includes(sectorId));
    const generic = CURIOSIDADES.filter(c => !c.setores);
    return [...shuffleBalanced([...sector]), ...shuffleBalanced([...generic])];
  }, [sectorId]);

  const [curiosidadeIndex, setCuriosidadeIndex] = useState(0);
  const [isFading, setIsFading] = useState(false);
  const { trackEvent } = useAnalytics();
  const stagesReachedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const interval = setInterval(() => {
      setIsFading(true);
      setTimeout(() => {
        setCuriosidadeIndex(prev => (prev + 1) % shuffledItems.length);
        setIsFading(false);
      }, 300);
    }, 6000);
    return () => clearInterval(interval);
  }, [shuffledItems.length]);

  const currentStageIndex = PHASE_TO_INDEX[phase] ?? 0;
  const progress = calculateProgress(phase, ufsCompleted, ufsTotal, itemsFetched, itemsFiltered);
  const eta = getETA(phase, ufsCompleted, ufsTotal, elapsedSeconds, itemsFetched);
  const statusMessage = getStatusMessage(phase, ufsCompleted, ufsTotal, itemsFetched);
  const stageConfig = STAGES[currentStageIndex] || STAGES[0];

  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const timeDisplay = minutes > 0 ? `${minutes}min ${seconds.toString().padStart(2, "0")}s` : `${seconds}s`;

  // Track stage progression
  useEffect(() => {
    if (!stagesReachedRef.current.has(phase)) {
      stagesReachedRef.current.add(phase);
      trackEvent("loading_stage_reached", {
        stage: phase, stage_index: currentStageIndex, elapsed_time_s: elapsedSeconds,
        progress_percent: progress, ufs_completed: ufsCompleted, ufs_total: ufsTotal, items_fetched: itemsFetched,
      });
    }
  }, [phase, currentStageIndex, elapsedSeconds, progress, ufsCompleted, ufsTotal, itemsFetched, trackEvent]);

  // Track loading abandonment
  useEffect(() => {
    const handleBeforeUnload = () => {
      trackEvent("loading_abandoned", { last_stage: phase, elapsed_time_s: elapsedSeconds, progress_percent: progress, items_fetched: itemsFetched });
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [phase, elapsedSeconds, progress, itemsFetched, trackEvent]);

  return (
    <div className="mt-8 p-6 bg-surface-1 rounded-card border animate-fade-in-up">
      <ProgressBar progress={progress} statusMessage={statusMessage} eta={eta} timeDisplay={timeDisplay}
        phase={phase} itemsFetched={itemsFetched} itemsFiltered={itemsFiltered} />
      <UfGrid phase={phase} ufsTotal={ufsTotal} ufsCompleted={ufsCompleted} selectedUfs={selectedUfs} />
      <StageList currentStageIndex={currentStageIndex} statusMessage={statusMessage} stageConfig={stageConfig} />
      <CuriosityCarousel curiosidade={shuffledItems[curiosidadeIndex]} isFading={isFading} />
      <SkeletonCards />
      <div className="mt-4 flex justify-center">
        <Button type="button" onClick={onCancel} variant="ghost" size="sm"
          className="text-ink-muted hover:text-error hover:bg-error-subtle">
          Cancelar busca
        </Button>
      </div>
    </div>
  );
}

export default LoadingProgress;
