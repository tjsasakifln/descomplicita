type StageId = "queued" | "fetching" | "filtering" | "summarizing" | "generating_excel";

type IconId = "search" | "download" | "filter" | "ai" | "done";

const ICON_SVG_PATHS: Record<IconId, string> = {
  search: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  download: "M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2m-4-4l-4 4m0 0l-4-4m4 4V4",
  filter: "M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z",
  ai: "M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-1.5 4.5H6.5L5 14.5m14 0H5",
  done: "M5 13l4 4L19 7",
};

function StageIcon({ icon, className }: { icon: string; className?: string }) {
  const path = ICON_SVG_PATHS[icon as IconId];
  if (!path) return null;
  return (
    <svg className={className || "w-4 h-4"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  );
}

export const STAGES: { id: StageId; label: string; icon: string }[] = [
  { id: "queued", label: "Iniciando busca", icon: "search" },
  { id: "fetching", label: "Buscando licitações", icon: "download" },
  { id: "filtering", label: "Filtrando resultados", icon: "filter" },
  { id: "summarizing", label: "Gerando resumo IA", icon: "ai" },
  { id: "generating_excel", label: "Preparando planilha", icon: "done" },
];

interface StageListProps {
  currentStageIndex: number;
  statusMessage: string;
  stageConfig: { label: string; icon: string };
}

export function StageList({ currentStageIndex, statusMessage, stageConfig }: StageListProps) {
  return (
    <>
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
    </>
  );
}
