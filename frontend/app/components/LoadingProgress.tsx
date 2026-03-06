"use client";

import { useState, useEffect, useRef } from "react";
import { useAnalytics } from "../../hooks/useAnalytics";
import type { SearchPhase } from "../types";

const CURIOSIDADES = [
  { texto: "A Lei 14.133/2021 substituiu a Lei 8.666/93 após 28 anos de vigência, modernizando as contratações públicas.", fonte: "Nova Lei de Licitações" },
  { texto: "A Nova Lei de Licitações trouxe o diálogo competitivo como nova modalidade de contratação.", fonte: "Lei 14.133/2021, Art. 32" },
  { texto: "A fase de habilitação agora pode ocorrer após o julgamento das propostas na Nova Lei.", fonte: "Lei 14.133/2021, Art. 17" },
  { texto: "A garantia contratual pode ser exigida em até 5% do valor do contrato, ou 10% para obras de grande vulto.", fonte: "Lei 14.133/2021, Art. 96" },
  { texto: "A Nova Lei permite o uso de seguro-garantia com cláusula de retomada, protegendo a Administração em obras.", fonte: "Lei 14.133/2021, Art. 102" },
  { texto: "O critério de julgamento por maior desconto substitui o antigo menor preço global em muitos casos.", fonte: "Lei 14.133/2021, Art. 33" },
  { texto: "A Lei 14.133 exige que todo processo licitatório tenha um agente de contratação designado.", fonte: "Lei 14.133/2021, Art. 8" },
  { texto: "A nova lei criou o Portal Nacional de Contratações Públicas (PNCP) como fonte única de publicidade oficial.", fonte: "Lei 14.133/2021, Art. 174" },
  { texto: "Contratos podem ser prorrogados por até 10 anos para serviços continuados, sem necessidade de nova licitação.", fonte: "Lei 14.133/2021, Art. 107" },
  { texto: "A Lei 14.133 prevê sanções como multa, impedimento e declaração de inidoneidade para licitantes.", fonte: "Lei 14.133/2021, Art. 155" },
  { texto: "O PNCP centraliza todas as licitações do Brasil desde 2023, abrangendo União, estados e municípios.", fonte: "Governo Federal" },
  { texto: "Qualquer cidadão pode consultar licitações em andamento no PNCP sem necessidade de cadastro.", fonte: "Portal PNCP" },
  { texto: "O PNCP disponibiliza uma API pública que permite consultas automatizadas de contratações.", fonte: "PNCP API Docs" },
  { texto: "Até 2025, o PNCP já acumulou mais de 3 milhões de publicações de contratações de todo o Brasil.", fonte: "Estatísticas PNCP" },
  { texto: "O Brasil realiza mais de 40 mil licitações por mês, movimentando bilhões em contratações públicas.", fonte: "Portal de Compras do Governo" },
  { texto: "O pregão eletrônico representa cerca de 80% de todas as licitações realizadas no país.", fonte: "Estatísticas PNCP" },
  { texto: "Compras públicas representam aproximadamente 12% do PIB brasileiro.", fonte: "OCDE / Governo Federal" },
  { texto: "Uniformes escolares movimentam cerca de R$ 2 bilhões por ano em licitações públicas.", fonte: "Estimativa de Mercado" },
  { texto: "Microempresas e EPPs têm tratamento diferenciado com preferência em licitações até R$ 80 mil.", fonte: "LC 123/2006, Art. 47-49" },
  { texto: "Monitorar licitações diariamente aumenta em até 3x as chances de encontrar oportunidades relevantes.", fonte: "Melhores Práticas de Mercado" },
];

type StageId = "queued" | "fetching" | "filtering" | "summarizing" | "generating_excel";

const STAGES: { id: StageId; label: string; icon: string }[] = [
  { id: "queued", label: "Iniciando busca", icon: "🔍" },
  { id: "fetching", label: "Buscando licitações", icon: "📥" },
  { id: "filtering", label: "Filtrando resultados", icon: "🎯" },
  { id: "summarizing", label: "Gerando resumo IA", icon: "🤖" },
  { id: "generating_excel", label: "Preparando planilha", icon: "✅" },
];

interface LoadingProgressProps {
  phase: SearchPhase;
  ufsCompleted: number;
  ufsTotal: number;
  itemsFetched: number;
  itemsFiltered: number;
  elapsedSeconds: number;
  onCancel: () => void;
}

export function LoadingProgress({
  phase,
  ufsCompleted,
  ufsTotal,
  itemsFetched,
  itemsFiltered,
  elapsedSeconds,
  onCancel,
}: LoadingProgressProps) {
  const [curiosidadeIndex, setCuriosidadeIndex] = useState(0);
  const { trackEvent } = useAnalytics();
  const stagesReachedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const interval = setInterval(() => {
      setCuriosidadeIndex((prev) => (prev + 1) % CURIOSIDADES.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const curiosidade = CURIOSIDADES[curiosidadeIndex];

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
    // Phase weight distribution: queued=5%, fetching=50%, filtering=15%, summarizing=20%, excel=10%
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
        return "Buscando licitações...";
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
          <span className="text-sm tabular-nums font-data text-ink-muted">
            {timeDisplay}
          </span>
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

      {/* UF Progress during fetching phase */}
      {phase === "fetching" && ufsTotal > 0 && (
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
                  <span className="text-base" aria-hidden="true">{stage.icon}</span>
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
          <span className="text-xl" aria-hidden="true">{stageConfig.icon}</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-ink">{stageConfig.label}</p>
            <p className="text-xs text-ink-muted">{statusMessage}</p>
          </div>
        </div>
      </div>

      {/* Curiosity Card */}
      <div className="p-4 bg-surface-0 rounded-card border transition-all duration-300">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 bg-brand-blue-subtle rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-brand-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink-muted mb-1">Você sabia?</p>
            <p className="text-base text-ink leading-relaxed">{curiosidade.texto}</p>
            <p className="text-xs text-ink-muted mt-2">Fonte: {curiosidade.fonte}</p>
          </div>
        </div>
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
