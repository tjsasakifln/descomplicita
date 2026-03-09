interface UfGridProps {
  phase: string;
  ufsTotal: number;
  ufsCompleted: number;
  selectedUfs: string[];
}

export function UfGrid({ phase, ufsTotal, ufsCompleted, selectedUfs }: UfGridProps) {
  if (phase !== "fetching" || ufsTotal <= 0) return null;

  if (selectedUfs.length > 0) {
    return (
      <div className="mb-4 p-3 bg-surface-0 rounded-lg border border-accent">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="font-medium text-ink">Estados processados</span>
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
    );
  }

  return (
    <div className="mb-4 p-3 bg-surface-0 rounded-lg border border-accent">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-ink">Estados processados</span>
        <span className="tabular-nums font-data text-brand-navy font-semibold">
          {ufsCompleted} / {ufsTotal}
        </span>
      </div>
    </div>
  );
}
