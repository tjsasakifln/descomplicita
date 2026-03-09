export function SkeletonCards() {
  return (
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
              <div className="h-4 rounded animate-shimmer" style={{ width: `${75 - i * 10}%` }} />
              <div className="h-3 rounded animate-shimmer" style={{ width: `${50 - i * 5}%` }} />
              <div className="flex gap-3">
                <div className="h-3 w-16 rounded animate-shimmer" />
                <div className="h-3 w-20 rounded animate-shimmer" />
                <div className="h-3 w-12 rounded animate-shimmer" />
              </div>
            </div>
            <div className="flex-shrink-0 text-right space-y-2">
              <div className="h-5 w-24 rounded animate-shimmer" />
              <div className="h-3 w-14 rounded animate-shimmer ml-auto" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
