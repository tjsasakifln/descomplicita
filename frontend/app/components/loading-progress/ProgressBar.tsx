interface ProgressBarProps {
  progress: number;
  statusMessage: string;
  eta: string | null;
  timeDisplay: string;
  phase: string;
  itemsFetched: number;
  itemsFiltered: number;
}

export function ProgressBar({
  progress,
  statusMessage,
  eta,
  timeDisplay,
  phase,
  itemsFetched,
  itemsFiltered,
}: ProgressBarProps) {
  return (
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
  );
}
